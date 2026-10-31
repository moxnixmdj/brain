"""Effect eligibility precedes ambiguity; bindable is not effect-compatible.

Positive cases run the real selector, binder, adapter and filesystem checks.
The admission spy wraps the real application function; it never returns a
substitute verdict. No registry changes are published.
"""
from copy import deepcopy
import json
import pathlib
import tempfile
from unittest import mock
import uuid

import pytest

from canonical.runtime import capability_selection_retrieval_v1 as selection
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1 as live
from canonical.runtime import swe_typed_plan_v1 as typed

ROOT = pathlib.Path(__file__).resolve().parents[2]
INDEX = "python.source.symbols.index.ast"
DISTRACTORS = ("python.refactor.inline_helper.v1", "python.source.change_impact.testselect.v1")


@pytest.fixture
def project():
    parent = ROOT / "canonical/astra_runtime/tmp"
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="effect-family-", dir=parent) as raw:
        path = pathlib.Path(raw)
        source = path / "m.py"
        source.write_text("def add(a, b):\n    return a + b\n"
                          "def first():\n    return add(1, 2)\n"
                          "def second():\n    return add(3, 4)\n")
        goal = f"Find every caller of the function add in {source.relative_to(ROOT)}."
        yield path, goal


def candidates():
    registry = live.load_verified_registry()
    return {cid: registry[cid] for cid in (INDEX, *DISTRACTORS)}


def test_effect_incompatible_candidates_do_not_create_ambiguity(project):
    _, goal = project
    registry = candidates()
    original = deepcopy(registry)
    resolved = typed._resolve_family(goal, ROOT, registry, selection.declarations(ROOT))
    assert resolved is not None
    assert resolved[0] == INDEX
    assert registry == original


def test_effect_filter_avoids_irrelevant_real_contract_binding(project):
    _, goal = project
    with mock.patch.object(selection, "admit", wraps=selection.admit) as observed:
        typed._resolve_family(goal, ROOT, candidates(), selection.declarations(ROOT))
    assert [call.args[1] for call in observed.call_args_list] == [INDEX]


def test_bindable_wrong_effects_alone_are_not_a_solution(project):
    _, goal = project
    registry = candidates()
    del registry[INDEX]
    assert typed._resolve_family(goal, ROOT, registry, selection.declarations(ROOT)) is None


def test_two_effect_eligible_descriptors_still_refuse(project):
    _, goal = project
    registry = candidates()
    # Request-local ambiguity mutation, not a new runnable capability. Both
    # descriptors use the real index contract; neither is executed/registered.
    other = INDEX + ".alternative"
    registry[other] = deepcopy(registry[INDEX])
    assert typed._resolve_family(goal, ROOT, registry, selection.declarations(ROOT)) is None


@pytest.mark.parametrize("name", ["add", "repair", "update", "rename", "remove", "fix"])
def test_real_caller_request_executes_index_without_modifying_source(project, name):
    path, goal = project
    (path / "m.py").write_text((path / "m.py").read_text().replace("add", name))
    goal = goal.replace("function add", "function " + name)
    before = (path / "m.py").read_bytes()
    result = door.solve({"task_id": "EFFECT_FAMILY_" + uuid.uuid4().hex, "goal": goal})
    assert result["pass"] is True, result
    assert result["compiled_capability_id"] == INDEX
    assert (path / "m.py").read_bytes() == before
    reports = list(path.glob("*.json"))
    assert len(reports) == 1
    artifact = json.loads(reports[0].read_bytes())
    assert set(artifact["callers_of"][name]) == {"first", "second"}


def test_actual_empty_caller_set_is_not_invented(project):
    path, goal = project
    (path / "m.py").write_text("def add(a, b):\n    return a + b\n")
    original = (path / "m.py").read_bytes()
    result = door.solve({"task_id": "EFFECT_FAMILY_EMPTY_" + uuid.uuid4().hex, "goal": goal})
    assert result["pass"] is True, result
    artifact = json.loads(next(path.glob("*.json")).read_bytes())
    assert artifact["callers_of"].get("add", []) == []
    assert (path / "m.py").read_bytes() == original


@pytest.mark.parametrize("goal", [
    "Inspect the code at canonical/tmp/caller/m.py",
    "Write the text 'find every caller' to canonical/tmp/out.txt",
])
def test_family_names_inside_values_are_not_intent(goal):
    assert typed._family_terms(goal) is None


@pytest.mark.parametrize("name", ["add", "repair", "update", "rename", "remove", "fix"])
def test_named_symbol_is_not_an_edit_but_a_separate_imperative_remains(project, name):
    path, goal = project
    goal = goal.replace("function add", "function " + name)
    rel = (path / "m.py").relative_to(ROOT).as_posix()
    assert door._promised_source_files(goal) == []
    assert door._promised_source_roots(goal) == []
    assert door._destructive_targets(goal) == set()
    mixed = goal + " Then repair the source file " + rel
    assert door._promised_source_files(mixed) == [rel]
    before = {rel: door._source_digest(rel)}
    assert door.promised_source_change_errors(mixed, before) == ["PROMISED_SOURCE_UNCHANGED:" + rel]
    assert door._destructive_targets("Remove " + rel) == {rel}


@pytest.mark.parametrize("article", ["the function", "function"])
def test_function_role_alone_does_not_hide_a_real_edit(project, article):
    path, goal = project
    rel = (path / "m.py").relative_to(ROOT).as_posix()
    query = goal.replace("the function", article)
    assert door._promised_source_files(query) == []
    result = door.solve({"task_id": "FAMILY_ARTICLE_" + uuid.uuid4().hex, "goal": query})
    assert result["pass"] is True, result
    operation = f"Make {article} add a parameter in {rel}"
    assert door._promised_source_files(operation) == [rel]
