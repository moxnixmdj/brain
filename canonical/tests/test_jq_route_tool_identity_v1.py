"""A request explicitly applying a jq filter must not route to a Git operation."""
from pathlib import Path
import json
import shutil
import tempfile

import pytest

from canonical.runtime.bound_capabilities import jq_query

from canonical.runtime import goal_compiler as gc
from canonical.runtime import goal_front_compiler_v1 as front
from canonical.runtime import live_brain_route_admission_v1 as admission
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
OUT = "canonical/astra_runtime/tmp/jq_tool_identity_guard.json"


@pytest.fixture(scope="module")
def registry():
    return gc._platform_admissible_registry(dict(load_verified_registry()))


@pytest.mark.parametrize("program", [".items[]", ".users | length", ".foo + .bar", ".a // .b"])
def test_explicit_quoted_jq_filter_routes_to_jq(registry, program):
    goal = f'Apply the jq filter "{program}" to {SOURCE} and write the output to {OUT}.'
    compiled = front.compile_goal(goal, registry, ROOT)
    assert compiled["selected_capability"] == "json.query.jq"
    assert compiled["inputs"]["jq_filter"] == program
    assert compiled["inputs"]["json_path"] == SOURCE
    assert compiled["inputs"]["output_path"] == OUT
    assert admission.route_admission(goal, compiled, registry)["admitted"] is True


@pytest.mark.skipif(shutil.which("jq") is None, reason="jq executable not installed")
@pytest.mark.parametrize("program,expected", [
    (".items[]", "1\n2\n"), (".users | length", "2\n"),
    (".foo + .bar", "5\n"), (".a // .b", "7\n"),
])
def test_bound_filter_runs_with_existing_jq_adapter(registry, program, expected):
    parent = ROOT / "canonical/astra_runtime/tmp"
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="jq-route-guard-", dir=parent) as tmp:
        path = Path(tmp)
        (path / "source.json").write_text(json.dumps({"items": [1, 2], "users": [1, 2],
                                                     "foo": 2, "bar": 3, "a": None, "b": 7}))
        source = (path / "source.json").relative_to(ROOT).as_posix()
        output = (path / "out.json").relative_to(ROOT).as_posix()
        goal = f'Apply the jq filter "{program}" to {source} and write the output to {output}.'
        compiled = front.compile_goal(goal, registry, ROOT)
        assert compiled["selected_capability"] == "json.query.jq"
        assert admission.route_admission(goal, compiled, registry)["admitted"] is True
        inputs = compiled["inputs"]
        result = jq_query.run({"input_path": inputs["json_path"], "output_path": inputs["output_path"],
                               "filter": inputs["jq_filter"]}, ROOT)
        assert result["output_verified"] is True
        assert (path / "out.json").read_text() == expected


@pytest.mark.parametrize("program", [".items[]", ".users | length", ".foo + .bar", ".a // .b"])
def test_complex_unquoted_filter_never_admitted_as_a_different_route(registry, program):
    goal = f'Apply the jq filter {program} to {SOURCE} and write the output to {OUT}.'
    try:
        compiled = front.compile_goal(goal, registry, ROOT)
    except gc.GoalCompilationFailure:
        return
    verdict = admission.route_admission(goal, compiled, registry)
    assert verdict["admitted"] is False, (compiled, verdict)
