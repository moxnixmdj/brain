"""The check mode is the oracle: discovery, read-only, the census, and the traps the checks cannot see.

The round claims something narrow and checkable: a program's own check mode can be *found* from its own
page and the action's own argv, with no hand-written rule anywhere, and it decides the action's
applicability exactly on states the search never saw -- and that it decides the input and not the world.
These tests hold the six declared criteria, the four reader bugs whose fix changed the answer, the absence
of any guard token in the tool's own source, and the census itself. One test re-runs the whole tool and
demands the same guards and the same verdicts.
"""
from __future__ import annotations

import ast
import json
import re
import pathlib
import sys
import tempfile
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(ROOT))

import the_check_mode_is_the_oracle_v1 as round_  # noqa: E402

RECEIPT = (ROOT / "canonical" / "verification" / "THE_CHECK_MODE_IS_THE_ORACLE_20261116_V1.json")
INTENT = (ROOT / "canonical" / "action_intents" / "THE_CHECK_MODE_IS_THE_ORACLE_20261116_V1.json")
TOOL = TOOLS / "the_check_mode_is_the_oracle_v1.py"


def _receipt() -> dict:
    return json.loads(RECEIPT.read_text())


def _row(name: str) -> dict:
    return next(row for row in _receipt()["actions"] if row["action"] == name)


def _guarded() -> list[dict]:
    return [row for row in _receipt()["actions"] if row["class"].startswith("GUARDED")]


# --------------------------------------------------------------------------------------------------
# the round, the criteria, and the zero it claims
# --------------------------------------------------------------------------------------------------

def test_the_receipt_names_the_round_it_answers_and_the_part_it_removed() -> None:
    receipt = _receipt()
    assert receipt["schema"] == "BRAIN_THE_CHECK_MODE_IS_THE_ORACLE_V1"
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"
    why = receipt["why_this_round"]
    assert "sensor vocabulary" in why["the_gap_it_closes"]
    assert "construct the observable" in why["the_pre_registered_next_step"]
    assert "discovered" in why["the_condition_that_makes_it_a_mechanism"]
    assert receipt["criteria_were_declared_after_a_prototype_probe"] is False
    cost = receipt["cost"]
    assert cost["model_calls"] == 0
    assert cost["parameters_stored"] == 0
    assert cost["network_calls_at_run_time"] == 0


def test_every_declared_criterion_is_met() -> None:
    verdict = _receipt()["verdict"]
    assert len(verdict) == 6
    assert all(value["MET"] is True for value in verdict.values()), \
        {key: value["MET"] for key, value in verdict.items()}


# --------------------------------------------------------------------------------------------------
# K1: discovered, not written; and the three actions the previous round could not state
# --------------------------------------------------------------------------------------------------

def test_every_guard_is_selected_by_agreement_from_a_page_the_tool_executed() -> None:
    rows = _guarded()
    assert len(rows) == 5
    for row in rows:
        assert row["selected_by"].startswith("agreement on training states")
        assert row["train_agreement"] == 1.0
        assert row["page_bytes"] > 40
        assert row["page_from"] != "none_answered"
        assert row["candidates"] > 0
        assert row["survivors_that_leave_the_state_alone"] >= 1
        assert row["armed_by"] in (None, "remove_every_regular_file_not_named_in_the_argv",
                                   "set_every_mode_to_0644")


def test_the_three_vocabulary_insufficient_actions_are_now_guarded_and_exact() -> None:
    verdict = _receipt()["verdict"]["K1_the_check_mode_is_discovered_not_written"]
    assert verdict["vocabulary_insufficient_actions"] == ["tar_extract", "gzip_decompress",
                                                          "patch_apply_real"]
    assert sorted(verdict["vocabulary_insufficient_actions_now_guarded"]) == sorted(
        verdict["vocabulary_insufficient_actions"])
    for name in verdict["vocabulary_insufficient_actions"]:
        row = _row(name)
        assert row["class"] == "GUARDED__EXACT"
        assert row["held_out_agreement"] == 1.0
    # and the guards are the programs' own read-only modes, found rather than written
    assert "-tzf" in _row("tar_extract")["guard_argv"]
    assert "-l" in _row("gzip_decompress")["guard_argv"]
    assert "--dry-run" in _row("patch_apply_real")["guard_argv"]


# --------------------------------------------------------------------------------------------------
# K2/K3: an observation, not an effect; and no overfitting
# --------------------------------------------------------------------------------------------------

def test_no_guard_changes_a_byte_while_the_action_changes_the_state() -> None:
    for row in _guarded():
        assert row["held_out_guard_changed"] == 0, row["action"]
        assert row["held_out_action_changed"] == row["held_out_states_action_applied"], row["action"]
        assert row["held_out_states_action_applied"] >= 4, row["action"]


def test_held_out_agreement_equals_training_agreement() -> None:
    for row in _guarded():
        assert row["held_out_agreement"] == row["train_agreement"] == 1.0, row["action"]
        assert row["held_out_disagreements"] == [], row["action"]


# --------------------------------------------------------------------------------------------------
# K4: the census splits, and the two reasons are different reasons
# --------------------------------------------------------------------------------------------------

def test_the_census_splits_ten_actions_into_five_and_five_with_two_distinct_reasons() -> None:
    census = _receipt()["verdict"]["K4_the_census_is_not_all_yes"]
    assert len(census["guarded"]) == 5
    assert sorted(census["unguardable"]) == sorted([
        "git_stash_pop", "git_merge_abort", "git_checkout_feature",
        "git_branch_delete_feature", "chmod_exec"])
    no_candidate = [name for name in census["unguardable"]
                    if _row(name)["class"] == "UNGUARDABLE__NO_CANDIDATE_AGREED"]
    performed = [name for name in census["unguardable"]
                 if _row(name)["class"] == "UNGUARDABLE__EVERY_AGREEING_CANDIDATE_PERFORMED_THE_EFFECT"]
    assert len(no_candidate) == 2
    assert len(performed) == 3
    for name in performed:
        assert _row(name)["survivors_that_change_a_byte"] > 0
        assert _row(name)["survivors_that_leave_the_state_alone"] == 0


def test_the_relabelled_actions_that_scored_one_before_the_read_only_rule_are_not_guards() -> None:
    # the first run of the tool kept these: they agree perfectly because they ARE the action
    spelled = {tuple(row["guard_argv"]) for row in _guarded()}
    for relabelled in (("git", "branch", "-d", "-d", "feature"),
                       ("chmod", "-R", "+x", "script.sh"),
                       ("git", "-P", "rm", "--cached", "-q", "README.rst")):
        assert relabelled not in spelled
    assert all(row["held_out_guard_changed"] == 0 for row in _guarded())


# --------------------------------------------------------------------------------------------------
# K5: the trap, and the trap's own trap (a root sandbox would make it vacuous)
# --------------------------------------------------------------------------------------------------

def test_the_check_is_wrong_in_every_trap_that_could_be_built() -> None:
    k5 = _receipt()["verdict"]["K5_the_check_tests_the_input_and_not_the_world"]
    measured = [row for row in k5["traps"] if row["stage"] == "MEASURED"]
    assert len(measured) == 3
    assert sorted(k5["wrong_in"]) == sorted(row["action"] for row in measured)
    for row in measured:
        assert row["guard_exit"] == 0 and row["action_exit"] != 0, row["action"]
        assert row["guard_wrong"] is True


def test_the_trap_was_effective_so_the_result_is_not_vacuous() -> None:
    measured = [row for row in _receipt()["verdict"][
        "K5_the_check_tests_the_input_and_not_the_world"]["traps"] if row["stage"] == "MEASURED"]
    assert all(row["trap_effective"] is True for row in measured), \
        "the read-only directory was writable: the process is root and the trap proves nothing"


# --------------------------------------------------------------------------------------------------
# the source itself: no guard is written anywhere in the tool
# --------------------------------------------------------------------------------------------------

def _non_docstring_strings(tree: ast.AST) -> list[str]:
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                docstrings.add(id(body[0].value))
    return [node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and id(node) not in docstrings]


def test_no_discovered_guard_token_is_spelled_in_the_tools_source() -> None:
    strings = _non_docstring_strings(ast.parse(TOOL.read_text()))
    for row in _guarded():
        novel = [token for token in row["guard_argv"] if token not in row["action_argv"]]
        assert novel, row["action"]
        for token in novel:
            # a token, not a substring: `-l` occurs inside the prose "name-level"
            pattern = re.compile(r"(?<![\w-])" + re.escape(token) + r"(?![\w-])")
            assert not any(pattern.search(text) for text in strings), (row["action"], token)


def test_the_reader_refuses_an_error_message_and_accepts_a_page() -> None:
    assert round_.looks_like_help("fatal: no man viewer handled the request\n"
                                  "fatal: 'man' died of signal 13\n") is False
    assert round_.looks_like_help("usage: git rm [<options>] [--] <file>...\n"
                                  "    -n, --dry-run         dry run") is True
    assert round_.looks_like_help("") is False


# --------------------------------------------------------------------------------------------------
# the whole machine, re-run
# --------------------------------------------------------------------------------------------------

def test_recompute_reproduces_the_guards_and_every_verdict() -> None:
    where = pathlib.Path(tempfile.mkdtemp(prefix="brain-checkmode-test-"))
    try:
        fresh = round_.measure(where / "root", where / "receipt.json", per_class=8, seed=7)
        kept = _receipt()
        assert {key: value["MET"] for key, value in fresh["verdict"].items()} == \
               {key: value["MET"] for key, value in kept["verdict"].items()}
        assert fresh["verdict"]["K1_the_check_mode_is_discovered_not_written"]["guards"] == \
               kept["verdict"]["K1_the_check_mode_is_discovered_not_written"]["guards"]
        assert [(row["action"], row["class"]) for row in fresh["actions"]] == \
               [(row["action"], row["class"]) for row in kept["actions"]]
        key = "K5_the_check_tests_the_input_and_not_the_world"
        assert sorted(fresh["verdict"][key]["wrong_in"]) == sorted(kept["verdict"][key]["wrong_in"])
    finally:
        shutil.rmtree(where, ignore_errors=True)


def test_the_intent_names_its_evidence_and_claims_no_independent_verification() -> None:
    intent = json.loads(INTENT.read_text())
    assert intent["action_id"] == "THE_CHECK_MODE_IS_THE_ORACLE_20261116_V1"
    assert intent["status"].endswith("INDEPENDENT_VERIFICATION_OPEN")
    assert intent["verification"]["independent_verification_completed"] is False
    assert intent["verification"]["tests_green"] == 14
    assert RECEIPT.relative_to(ROOT).as_posix() in intent["progress_evidence_paths"]
    assert intent["measured_effect"]["guards"]["tar_extract"] == ["tar", "-tzf", "bundle.tgz"]
    assert len(intent["truth"]["what_is_false_in_the_claim"]) >= 4
    assert "check mode" in intent["truth"]["the_law_this_round_adds"]
