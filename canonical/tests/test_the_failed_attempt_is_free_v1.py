"""The failed attempt is free: free refusal, exact commit, exact undo, and the primitive measured.

The round claims something narrow and checkable: an attempt that fails costs nothing, an attempt that
succeeds is exact and undoable, and the decision no longer needs the action to be readable. These tests hold
the six declared criteria, the two commit primitives (including the `ENOTEMPTY` that the tree's own
publication step never meets because its target is absent), the traps that compare the stage against the
live tree, the declared concurrency boundary, and the absence of any model or network call. One test
re-runs the whole tool and demands the same verdicts and the same commit mechanism.
"""
from __future__ import annotations

import ast
import json
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(ROOT))

import the_failed_attempt_is_free_v1 as round_  # noqa: E402

NAME = "THE_FAILED_ATTEMPT_IS_FREE_20261116_V1"
RECEIPT = ROOT / "canonical" / "verification" / (NAME + ".json")
INTENT = ROOT / "canonical" / "action_intents" / (NAME + ".json")
TOOL = TOOLS / "the_failed_attempt_is_free_v1.py"

UNGUARDABLE = ("git_stash_pop", "git_merge_abort", "git_checkout_feature",
               "git_branch_delete_feature", "chmod_exec")


def _receipt() -> dict:
    return json.loads(RECEIPT.read_text())


def _row(name: str) -> dict:
    return next(row for row in _receipt()["actions"] if row["action"] == name)


def _trap(name: str) -> dict:
    return next(row for row in _receipt()["traps"] if row.get("trap") == name)


def test_the_receipt_names_the_round_the_claim_and_what_it_reused() -> None:
    receipt = _receipt()
    assert receipt["schema"] == "BRAIN_THE_FAILED_ATTEMPT_IS_FREE_V1"
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"
    why = receipt["why_this_round"]
    assert "one trial per action" in why["the_claim"]
    assert "mispredicted" in why["what_the_previous_round_left"]
    assert len(why["reused_not_rebuilt"]) >= 3
    assert receipt["criteria_were_declared_after_a_prototype_probe"] is False
    cost = receipt["cost"]
    assert cost["model_calls"] == 0 and cost["parameters_stored"] == 0
    assert cost["network_calls_at_run_time"] == 0


def test_every_declared_criterion_is_met() -> None:
    verdict = _receipt()["verdict"]
    assert len(verdict) == 6
    for key, value in verdict.items():
        assert value.get("MET", "MEASURED_FOR_A_PRICE") is not False, key


def test_the_staged_decision_is_exact_for_every_action_including_the_five_unreadable_ones() -> None:
    for row in _receipt()["actions"]:
        assert row["staged_decision_agreement"] == 1.0, row["action"]
        assert row["states"] == 16, row["action"]
        assert row["applies"] == 8 and row["does_not_apply"] == 8, row["action"]
    for name in UNGUARDABLE:
        assert _row(name)["staged_decision_agreement"] == 1.0, name


def test_a_refused_attempt_leaves_the_live_tree_byte_identical() -> None:
    k2 = _receipt()["verdict"]["K2_a_refused_attempt_is_free"]
    assert k2["refused_attempts"] == 80
    assert k2["refused_attempts_that_changed_one_byte"] == []
    assert k2["trap_stage_reproduced_the_live_refusal"], "no trap compared stage to live"
    assert all(value is True for value in k2["trap_stage_reproduced_the_live_refusal"].values())
    assert k2["MET"] is True


def test_the_three_input_valid_traps_refuse_in_the_stage_exactly_as_they_refuse_in_the_live_tree() -> None:
    for name in ("tar_extract", "gzip_decompress", "patch_apply_real"):
        trap = _trap(name + ":read_only_target")
        assert trap["trap_effective"] is True, name
        assert trap["staged_exit"] != 0 and trap["live_exit"] != 0, name
        assert trap["stage_reproduced_the_refusal"] is True, name
        assert trap["live_tree_unchanged_by_the_refused_attempt"] is True, name


def test_a_committed_attempt_is_exact_and_undoable() -> None:
    k3 = _receipt()["verdict"]["K3_a_committed_attempt_is_exact_and_undoable"]
    assert k3["committed_attempts"] == 80
    assert k3["live_differs_from_stage"] == []
    assert k3["displaced_differs_from_pre_state"] == []
    assert k3["undo_failures"] == []
    for row in _receipt()["actions"]:
        assert row["committed_attempts"] == 8, row["action"]


def test_the_commit_primitive_is_measured_not_assumed() -> None:
    k4 = _receipt()["verdict"]["K4_the_commit_primitive_measured"]
    assert any("ENOTEMPTY" in value for value in k4["os_replace_on_populated_directory"]), \
        "os.replace replaced a populated directory; the premise is wrong"
    assert k4["exchange_supported_here"] is True
    assert k4["fallback_window"]["live_path_missing_between_renames"] is True
    commit_trap = k4["read_only_parent_at_the_commit"]
    assert commit_trap["commit_refused"] is True
    assert commit_trap["live_unchanged_after_failed_commit"] is True


def test_the_price_of_undo_is_the_tree_and_not_the_edit() -> None:
    k5 = _receipt()["verdict"]["K5_the_price_of_undo"]
    staged = k5["bytes_staged_per_attempt"]
    assert all(value and value > 0 for value in staged.values())
    assert max(staged.values()) / min(staged.values()) < 1.3, "the copy tracks the tree, not the action"
    # a mode-only effect has no content bytes, and the copy is still the whole tree
    assert k5["effect_is_mode_only"]["chmod_exec"] is True
    assert k5["bytes_of_actual_effect"]["chmod_exec"] == 0
    assert k5["amplification_by_content_bytes"]["gzip_decompress"] > 100


def test_the_concurrency_boundary_is_declared_rather_than_claimed_away() -> None:
    boundary = _receipt()["concurrency_boundary"]
    assert "not a compare-and-swap" in boundary["evidence"]
    assert "outside the contract" in boundary["declared"]
    assert "cas" in boundary["consequence"]


def test_the_tool_imports_no_model_and_no_network() -> None:
    tree = ast.parse(TOOL.read_text())
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    forbidden = {"requests", "urllib", "http", "openai", "anthropic", "torch", "numpy", "transformers"}
    assert not (set(imported) & forbidden), sorted(set(imported) & forbidden)


def test_recompute_reproduces_the_verdicts_and_the_commit() -> None:
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-free-test-"))
    try:
        fresh = round_.measure(where / "root", where / "receipt.json", per_class=8, seed=7)
        kept = _receipt()
        assert {key: value.get("MET") for key, value in fresh["verdict"].items()} == \
               {key: value.get("MET") for key, value in kept["verdict"].items()}
        assert {row["action"]: row["staged_decision_agreement"] for row in fresh["actions"]} == \
               {row["action"]: row["staged_decision_agreement"] for row in kept["actions"]}
        assert {row["action"]: row["commit_mechanisms"] for row in fresh["actions"]} == \
               {row["action"]: row["commit_mechanisms"] for row in kept["actions"]}
        assert fresh["verdict"]["K4_the_commit_primitive_measured"][
            "fallback_window"]["live_path_missing_between_renames"] is True
    finally:
        shutil.rmtree(where, ignore_errors=True)


def test_the_intent_names_its_evidence_and_claims_no_independent_verification() -> None:
    intent = json.loads(INTENT.read_text())
    assert intent["action_id"] == NAME
    assert intent["status"].endswith("INDEPENDENT_VERIFICATION_OPEN")
    assert intent["verification"]["independent_verification_completed"] is False
    assert intent["verification"]["tests_green"] == 12
    assert RECEIPT.relative_to(ROOT).as_posix() in intent["progress_evidence_paths"]
    assert "trial-and-error is sound iff failure is free" in \
        intent["truth"]["the_law_this_round_adds"].lower()
    assert len(intent["truth"]["what_is_false_in_the_claim"]) >= 5
    assert "free attempt" in intent["next_step"] or "write-ahead" in intent["next_step"]
