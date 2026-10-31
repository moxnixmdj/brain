"""Real Git operation routing; task data and ambiguity never authorize another task."""
from pathlib import Path
import uuid
from unittest import mock

import pytest

from canonical.runtime import declared_input_derivation_v1 as derivation
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1 as live
from canonical.runtime import swe_typed_plan_v1 as typed

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("goal,op", [
    ("Show me the diff", "diff"),
    ("Please display the status.", "status"),
    ("Show the history", "log"),
    ("What is the current branch?", "branch"),
    ("Who wrote line 3 of canonical/runtime/swe_typed_plan_v1.py", "blame"),
])
def test_existing_operation_grammar_reaches_operation_contract(goal, op):
    assert typed.stated_family_token(goal) == typed.GIT_FAMILY_TOKEN
    plan = typed.build_plan(goal, ROOT)
    assert plan is not None
    assert plan[2]["selected_capability"] == "git.repository.operate.v1"
    assert plan[2]["inputs"]["op"] == op


@pytest.mark.parametrize("goal", [
    "Show deployment status",
    "Explain the history of sorting algorithms",
    "Branch out the new feature into three modules",
    "Write the text 'git status and diff' to canonical/tmp/message.txt",
])
def test_non_repository_prose_does_not_become_short_git_request(goal):
    assert typed.stated_family_token(goal) is None


@pytest.mark.parametrize("goal", [
    "Show git status and diff",
    "Show the git diff and commit the staged changes",
    "Bisect git history",
])
def test_ambiguous_operations_refuse_without_primary_execution(goal):
    with mock.patch.object(door, "_solve_body", wraps=door._solve_body) as body:
        result = door.solve({"task_id": "GIT_AMBIGUITY_" + uuid.uuid4().hex, "goal": goal})
    assert result["pass"] is False
    assert result["executed"] is False
    assert result["failure_class"] == "STATED_SWE_EFFECT_UNSERVED"
    body.assert_not_called()


def test_versions_and_operation_words_inside_values_are_not_operations():
    assert derivation.stated_git_operations(
        "Show git status with payload 'diff' using canonical/tmp/git-log.txt") == ("status",)


def test_real_competing_bisector_does_not_steal_authorship_operation():
    registry = live.load_verified_registry()
    goal = "Who wrote line 3 of canonical/runtime/swe_typed_plan_v1.py"
    with mock.patch.object(typed.selection, "admit", wraps=typed.selection.admit) as admit:
        resolved = typed._resolve_family(goal, ROOT, registry, typed.selection.declarations(ROOT))
    assert resolved is not None
    assert resolved[0] == "git.repository.operate.v1"
    assert "git.history.bisect_regression.v1" not in [call.args[1] for call in admit.call_args_list]


@pytest.mark.parametrize("goal,op", [("Show me the diff", "diff"), ("Show the status", "status")])
def test_public_read_operation_executes_existing_git_adapter(goal, op):
    result = door.solve({"task_id": "GIT_READ_" + uuid.uuid4().hex, "goal": goal})
    assert result["pass"] is True, result
    assert result["compiled_capability_id"] == "git.repository.operate.v1"
    assert result["typed_swe_plan_first"]["selected_capability"] == "git.repository.operate.v1"
    # Execution itself, rather than a registry-only decision, is required.
    assert result["executed"] is True, result


@pytest.mark.parametrize("message", ["fix diff", "update status", "preserve history"])
def test_commit_message_words_do_not_select_extra_operations(message):
    # Planning only: never create a commit as part of this routing test.
    plan = typed.build_plan("Commit the staged changes with the message '" + message + "'", ROOT)
    assert plan is not None
    assert plan[2]["inputs"]["op"] == "commit"
    assert plan[2]["inputs"]["message"] == message


def test_repository_context_inside_payload_does_not_authorize_commit():
    assert derivation.stated_git_operations("Commit the transaction with payload 'git'") == ()


def test_index_contract_does_not_expand_source_scope_to_unrelated_ancestor_tests():
    import tempfile
    parent = ROOT / "canonical/astra_runtime/tmp"
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="intent-source-scope-", dir=parent) as raw:
        source = Path(raw) / "m.py"
        source.write_text("def f():\n    return 1\n")
        rel = source.relative_to(ROOT).as_posix()
        plan = typed.build_plan("Find every caller of the function f in " + rel, ROOT)
        assert plan is not None
        assert plan[2]["inputs"]["source_root"] == source.parent.relative_to(ROOT).as_posix()
