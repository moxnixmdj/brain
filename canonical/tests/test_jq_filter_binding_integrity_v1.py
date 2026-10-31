"""A jq program must not silently become a different program at binding."""
from pathlib import Path

import pytest

from canonical.runtime import goal_compiler as gc
from canonical.runtime import goal_front_compiler_v1 as front
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("program", [".items[]", ".users | length", ".foo + .bar", ".a // .b"])
def test_unquoted_complex_jq_program_is_not_truncated(program):
    goal = f"Apply the jq filter {program} to canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    # Until a whole-program grammar establishes the boundary, require quoting.
    with pytest.raises(gc.GoalCompilationFailure):
        front.bind_typed_key(goal, "jq_filter", ROOT)


@pytest.mark.parametrize("program", [".items[]", ".users | length", ".foo + .bar", ".a // .b"])
def test_quoted_jq_program_is_preserved(program):
    goal = f'Apply the jq filter "{program}" to canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json'
    assert front.bind_typed_key(goal, "jq_filter", ROOT) == program


def test_escaped_inner_quote_must_not_truncate_the_filter():
    goal = r'Apply the jq filter ".items | select(.name == \"alice\")" to data.json'
    with pytest.raises(gc.GoalCompilationFailure):
        front.bind_typed_key(goal, "jq_filter", ROOT)


def test_inner_other_quote_is_preserved():
    goal = '''Apply the jq filter '.items | select(.name == "alice")' to data.json'''
    assert front.bind_typed_key(goal, "jq_filter", ROOT) == '.items | select(.name == "alice")'


def test_quoted_fragment_followed_by_filter_operator_is_refused():
    goal = '''Apply the jq filter '.items' | length to data.json'''
    with pytest.raises(gc.GoalCompilationFailure):
        front.bind_typed_key(goal, "jq_filter", ROOT)


def test_simple_unquoted_jq_path_is_preserved():
    goal = "Apply the jq filter .items.name to canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    assert front.bind_typed_key(goal, "jq_filter", ROOT) == ".items.name"


@pytest.mark.parametrize("program,expected", [
    (".items[]", None), (".users | length", None),
    ('".items[]"', ".items[]"), (".items.name", ".items.name"),
])
def test_real_jq_contract_does_not_bind_a_partial_program(program, expected):
    entry = load_verified_registry()["json.query.jq"]
    goal = (f"Apply the jq filter {program} to canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json "
            "and write the output to canonical/astra_runtime/tmp/jq_probe.json.")
    if expected is None:
        with pytest.raises(gc.GoalCompilationFailure):
            front.bind_all_inputs(goal, entry, ROOT, cycle=0, spool=set())
    else:
        result = front.bind_all_inputs(goal, entry, ROOT, cycle=0, spool=set())
        assert result["jq_filter"] == expected
