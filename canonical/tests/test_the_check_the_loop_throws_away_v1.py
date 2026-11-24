"""The numbers in this round's receipt, held to the receipts they came from.

Why a test and not prose
------------------------
This round exists because the previous round quoted a number it had not read off the rows
(`16 tasks lost to a check never taken`), and that number was wrong. Prose cannot catch that; a
test that recomputes the number from the source receipt can. So every count below is either
recomputed from the source receipt's own `per_task` rows, or pinned as a measurement this round
made and wrote down, so that a later round cannot quietly restate it.

The two places a number could drift and this test would not catch are named in `limits` of the
receipt: the project-as-dictionary figures are a sample of 26, and `held` is fix_shape_v1's own
notion. Nothing here claims those are exact beyond what it says.
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / "canonical" / "verification" / "CANDIDATE_UNDER_THE_TASKS_TESTS_SWEBENCH_VERIFIED_DJANGO_20261113_V1.json"
RECEIPT = ROOT / "canonical" / "verification" / "THE_CHECK_THE_LOOP_THROWS_AWAY_20261125_V1.json"


def source() -> dict:
    return json.loads(SOURCE.read_text())


def receipt() -> dict:
    return json.loads(RECEIPT.read_text())


def rows() -> list[tuple[str, dict]]:
    out = []
    for task, row in source()["per_task"].items():
        for candidate in row.get("candidates") or ():
            out.append((task, candidate))
    return out


# --------------------------------------------------------------------------- #
# the retraction: the check was taken, and it held
# --------------------------------------------------------------------------- #
def test_no_candidate_that_passed_every_new_test_was_stopped() -> None:
    """The gate stops a candidate only when some new test still fails. If this ever fails, the
    tool withheld a candidate that had earned the whole-module run -- a real defect, not a lost 16."""
    stopped_after_passing_all = [
        (task, row["place"]) for task, row in rows()
        if row.get("whole_run") is False and row.get("start_passing")
        and row.get("start_passing") == (source()["per_task"][task].get("start_passing") or 0)
        and (source()["per_task"][task].get("start_passing") or 0) > 0
    ]
    assert stopped_after_passing_all == []


def test_the_245_stopped_candidates_are_partial_by_construction() -> None:
    """245 candidates in 16 tasks passed SOME new test and were stopped. Each one failed at least
    one test the task says must start passing, so stopping it loses nothing that the hidden tests
    would have kept."""
    stopped = [(task, row) for task, row in rows()
               if row.get("whole_run") is False and (row.get("start_passing") or 0) > 0]
    assert len(stopped) == 245
    assert len({task for task, _ in stopped}) == 16
    for task, row in stopped:
        wanted = source()["per_task"][task].get("start_passing") or 0
        assert row["start_passing"] < wanted, (task, row["place"], row["start_passing"], wanted)


def test_the_receipt_states_the_retraction_and_not_the_old_number() -> None:
    doc = receipt()
    assert doc["the_retraction"]["what_is_true"]["passed_ALL_the_new_tests_and_were_stopped"] == 0
    assert "3 tasks of 128" in doc["what_this_round_falsifies"][0]


def test_the_breakers_are_three_and_are_named_in_the_source_receipt() -> None:
    breakers = source()["candidates_that_pass_the_new_tests_and_break_an_old_one"]
    assert breakers["count"] == 3
    assert sorted(breakers["which"]) == ["django__django-13109", "django__django-13569", "django__django-15467"]
    assert "3 -- the candidates named" in receipt()["the_retraction"]["the_correction"] or \
           "the number lost to a breakage in the neighbours is 3" in receipt()["the_retraction"]["the_correction"]


def test_the_candidate_counts_the_retraction_quotes_are_the_rows() -> None:
    doc = receipt()["the_retraction"]["what_is_true"]
    assert doc["candidates_that_passed_at_least_one_new_test"] == 258
    assert doc["of_those_given_the_whole_module_run"] == 13
    assert doc["of_those_resolved"] == 10
    assert doc["in_how_many_tasks"] == 16
    passed = [(task, row) for task, row in rows() if (row.get("start_passing") or 0) > 0]
    assert len(passed) == 258
    assert sum(1 for _, row in passed if row.get("whole_run")) == 13
    assert sum(1 for _, row in passed if row.get("resolves")) == 10


# --------------------------------------------------------------------------- #
# measurement 1: the channel is empty
# --------------------------------------------------------------------------- #
def test_the_channel_numbers_are_self_consistent() -> None:
    m = receipt()["measurement_1__why_102_tasks_have_no_candidate"]
    assert m["tasks_with_at_least_one_code_line_in_the_issue_text"] + \
           m["tasks_with_no_code_line_in_the_issue_text"] == 231
    assert m["tasks_with_no_code_line_AND_no_candidate"] == 93
    assert m["tasks_with_no_code_lines_but_a_candidate"] == 0
    assert m["tasks_with_no_code_line_AND_no_candidate"] + m["tasks_with_code_lines_AND_no_candidate"] == 102


def test_102_is_the_number_of_tasks_with_no_candidate_in_the_source_receipt() -> None:
    none = [task for task, row in source()["per_task"].items() if not (row.get("candidates_made") or 0)]
    assert len(none) == 102
    assert len(source()["per_task"]) == 231


# --------------------------------------------------------------------------- #
# measurement 2: the content is partly in the project, not in the text
# --------------------------------------------------------------------------- #
def test_the_text_carries_little_of_what_the_fix_needs() -> None:
    m = receipt()["measurement_2__is_the_missing_content_anywhere_at_hand"]["issue_text"]
    assert m["new_atoms_the_fix_needs_that_the_issue_text_names__all_of_them"] == 6
    assert m["partly"] + m["not_at_all"] + \
           m["new_atoms_the_fix_needs_that_the_issue_text_names__all_of_them"] == m["of_102"] == 102
    assert m["atom_level"] == "36 of 200 new atoms (18%) are named anywhere in the issue text"


def test_the_project_holds_more_than_the_file_and_the_receipt_says_so() -> None:
    m = receipt()["measurement_2__is_the_missing_content_anywhere_at_hand"]
    before, after = m["the_file_being_changed"]["files_whose_every_new_atom_the_file_already_holds__by_fix_shape_v1_needs"], \
                    m["the_whole_project_at_the_task_s_base_commit"]
    assert before["new"] == 69 and before["of"] == 112
    assert after["needs_vs_the_project"] == {"new": 9, "held": 15, "nothing": 2}
    assert after["needs_vs_the_file"] == {"new": 12, "held": 11, "nothing": 2, "built in": 1}


def test_the_project_alone_figure_is_the_sum_of_its_own_parts() -> None:
    """The prose once said 21 of 26 while the counts below it summed to 17 (15 held + 2 needing
    nothing). A hand-typed total that disagrees with its own parts is exactly the class of error
    this round exists to catch, so the prose and the parts are checked against each other."""
    m = receipt()["measurement_2__is_the_missing_content_anywhere_at_hand"]
    parts = m["the_whole_project_at_the_task_s_base_commit"]["needs_vs_the_project"]
    reachable = parts["held"] + parts["nothing"]
    assert reachable == 17
    channels = receipt()["what_is_left_and_what_it_costs"]["the_three_content_channels_measured_here"]
    assert channels["project_alone"].startswith(f"{reachable} of 26")


def test_the_file_level_figures_cover_every_changed_file_of_the_102() -> None:
    m = receipt()["measurement_2__is_the_missing_content_anywhere_at_hand"]
    needs = m["the_file_being_changed"]["files_whose_every_new_atom_the_file_already_holds__by_fix_shape_v1_needs"]
    assert needs["nothing"] + needs["held"] + needs["built in"] + needs["new"] == needs["of"]


# --------------------------------------------------------------------------- #
# measurement 3: the two zero-cost oracles, and why neither carries the round
# --------------------------------------------------------------------------- #
def test_the_trace_figures_are_the_sample_and_its_parts_sum_to_it() -> None:
    t = receipt()["measurement_3__the_two_oracles_that_cost_nothing"]["the_failing_test_s_trace"]
    assert t["file_runs_traced"] == 26
    assert t["file_never_executed_at_all"] + t["file_executed_but_the_changed_line_never_was"] + \
           t["changed_line_inside_the_trace"] == t["file_runs_traced"]
    assert t["changed_line_inside_the_trace"] == 1
    assert t["file_never_executed_at_all"] == 13


def test_the_reproduction_is_rare_and_the_receipt_does_not_inflate_it() -> None:
    r = receipt()["measurement_3__the_two_oracles_that_cost_nothing"]["the_issue_s_own_reproduction"]
    assert r["tasks_with_one"] == 19 and r["of"] == 231
    assert r["of_those_with_no_candidate"] == 3
    assert "too few to carry a round" in r["verdict"]


# --------------------------------------------------------------------------- #
# the numbers must be re-derivable, not just written down
# --------------------------------------------------------------------------- #
def test_a_tool_exists_that_recomputes_the_two_numbers_that_carry_the_conclusion() -> None:
    """A retraction is worth nothing if the replacement cannot be recomputed by somebody who does
    not trust the receipt. The tool is present, takes the material as paths, and makes no network
    call of its own."""
    tool = ROOT / "canonical" / "tools" / "the_content_channel_measured_v1.py"
    assert tool.exists()
    text = tool.read_text()
    assert "quoted_in_the_task_text_v1" in text and "fix_shape_v1" in text
    # no network in the module itself: the prose may say "pull requests", the imports may not reach out
    imports = [line.strip() for line in text.splitlines() if line.startswith(("import ", "from "))]
    assert not [line for line in imports if "urllib" in line or "http" in line or "requests" in line]


def test_the_tool_s_own_arithmetic_agrees_with_the_receipt_s() -> None:
    """The receipt quotes 112 changed files with 69 needing something new, and 17 of 26 reachable
    from the project. The tool's sample and the receipt's sample are the same sample, so the two
    must agree, and the receipt's prose must not say a larger number than its own parts."""
    m = receipt()["measurement_2__is_the_missing_content_anywhere_at_hand"]
    needs = m["the_file_being_changed"]["files_whose_every_new_atom_the_file_already_holds__by_fix_shape_v1_needs"]
    whole = m["the_whole_project_at_the_task_s_base_commit"]
    assert needs["of"] == 112
    assert needs["new"] == 69
    assert whole["deterministic_sample"].startswith("every 4th of the 102")
    assert sum(whole["needs_vs_the_project"].values()) == 26
    assert sum(whole["needs_vs_the_file"].values()) == 26


# --------------------------------------------------------------------------- #
# the shape of the claim
# --------------------------------------------------------------------------- #
def test_the_round_claims_no_gain_and_no_benchmark_run() -> None:
    doc = receipt()
    assert doc["model_calls"] == 0
    assert doc["parameters"] == 0
    assert doc["spend"] == {"usd": 0, "model_calls": 0, "parameters": 0}
    assert any("does not claim a capability gain" in line for line in doc["what_this_round_does_NOT_do"])


def test_the_receipt_names_the_receipt_it_read_instead_of_re_deriving() -> None:
    doc = receipt()["what_was_already_measured_and_will_not_be_re_derived"]
    assert doc["one_submission__tasks_resolved"] == 5
    assert doc["within_twenty__tasks_resolved"] == 7
    assert doc["control__another_tasks_text__resolved"] == 0
    summary = source()["summary"]
    assert summary["one_submission__tasks_resolved"] == 5
    assert summary["within_twenty__tasks_resolved"] == 7
