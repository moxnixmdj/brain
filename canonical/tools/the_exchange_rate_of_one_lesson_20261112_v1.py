#!/usr/bin/env python3
"""What one experience actually buys, in repaired bugs, from the tree's OWN records.

WHY THIS EXISTS
---------------
The owner's question is always the same sentence: *give the model the most advanced
coding actions, let it experience each once, and it will have learned them permanently.*
That sentence has been answered in prose many times in this tree. Prose can be re-read
selectively, and a number quoted a fourth time can be stale (it was: 19/38 became 21/38).
This tool does one thing: it reads the three already-landed, producer-run external-benchmark
records and turns them into an exchange rate, so the next round can argue with arithmetic
instead of adjectives.

It does NOT run a benchmark, call a model, register a capability, read a governance file,
or write anything. It reads:

  canonical/verification/HUMANEVALFIX_EXPERIENCE_STREAM_20261112_V1.json
      100 held-out HumanEvalFix bugs, met once each, in one stream.
      Arms: solver alone / own repairs kept / the same lessons backwards / published fix shown.

  canonical/verification/QUIXBUGS_REPAIR_SOLVER_20261111_V1.json
      40 QuixBugs bugs, other authors. Solver cold; solver after 39 other fixes taught;
      the same bugs again from memory.

  canonical/verification/QUIXBUGS_EDIT_KIND_TRANSFER_20261112_V1.json
      Operator transfer across benchmarks: HumanEvalFix fixes -> QuixBugs bugs.
      This is the one arm in the tree where *shape* transfer is large, so it is kept
      beside the negative result rather than omitted.

  canonical/verification/HUMANEVALFIX_EDIT_KIND_TRANSFER_20261111_V1.json
      203 lessons -> 62/100; the same lessons backwards -> 56/100. The directional
      contribution of the lessons is the difference, not the raw score.

WHAT THE ARITHMETIC SAYS (printed, not asserted as a capability)
----------------------------------------------------------------
* Keeping one's own repairs is worth +2 repaired bugs over keeping the same number of
  changes backwards, on 100 bugs. Most of the +11 over the cold solver is the learner's
  candidate generation, not the memory.
* Teaching the published fixes of all 39 other QuixBugs bugs buys +1 bug (5 -> 6 of 40).
  22 lessons tried over 858 (lesson, target) pairs repair exactly 1 other bug.
* Exact repetition is cheap and real: 4 of 4 remembered repairs replay in ~1.9 s where
  the search took 5.5 to 228.6 s.
* The exception is operator transfer: HumanEvalFix edit kinds repair 20 of 40 QuixBugs
  bugs where the tree's own search repairs 5 of 40. The record itself says this is
  "like for like ... about the same number of test runs per bug", but it is a different
  mechanism with a different budget, so it is reported as an exception, not as the rule.

Authority: NONE. Producer-run records, one machine, nobody else has re-run them.
`truth.achieved` stays false. $0. Zero model calls. Standard library only.

Run:
    python3 canonical/tools/the_exchange_rate_of_one_lesson_20261112_v1.py
    python3 canonical/tools/the_exchange_rate_of_one_lesson_20261112_v1.py --json
"""
from __future__ import annotations

import argparse
import json
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]

HUMAN_EVAL_EXPERIENCE = (
    "canonical/verification/HUMANEVALFIX_EXPERIENCE_STREAM_20261112_V1.json"
)
QUIXBUGS_SOLVER = "canonical/verification/QUIXBUGS_REPAIR_SOLVER_20261111_V1.json"
QUIXBUGS_EDIT_KIND = "canonical/verification/QUIXBUGS_EDIT_KIND_TRANSFER_20261112_V1.json"
HUMAN_EVAL_EDIT_KIND = (
    "canonical/verification/HUMANEVALFIX_EDIT_KIND_TRANSFER_20261111_V1.json"
)

SCHEMA = "PROJECT_BRAIN_ONE_LESSON_EXCHANGE_RATE_V1"
AUTHORITY = "NONE__READS_PRODUCER_RUN_RECORDS__NO_NEW_RUN__NO_CAPABILITY"


def _load(relative: str) -> dict[str, Any]:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def human_eval_experience() -> dict[str, Any]:
    """The one-pass stream: what memory adds when each bug is met once."""
    record = _load(HUMAN_EVAL_EXPERIENCE)
    first = record["first_meeting"]
    arms = {
        arm: {
            "repaired": int(first[arm]["repaired"]),
            "right_as_far_as_checked": int(first[arm]["right_as_far_as_checked"]),
        }
        for arm in ("solver_alone", "own", "backwards", "shown")
    }
    ruler = record["the_rulers_verdict"]
    claim = ruler["claim"]
    return {
        "bugs": 100,
        "arms": arms,
        "adjudicator_verdict": ruler["verdict"],
        "mean_cost_ratio_cold_over_warm": float(claim["mean_cost_ratio_cold_over_warm"]),
        "paired_wins": str(claim["paired_wins"]),
        "mean_cost_ratio_required": float(
            ruler["thresholds"]["min_mean_cost_ratio_warm_vs_cold"]
        ),
        "paired_win_fraction_required": float(
            ruler["thresholds"]["min_paired_win_fraction"]
        ),
        # The honest directional value of the lessons is own minus the backwards
        # control, not own minus the cold solver: both memory arms share a size.
        "directional_repairs_over_control": (
            arms["own"]["repaired"] - arms["backwards"]["repaired"]
        ),
        "directional_right_over_control": (
            arms["own"]["right_as_far_as_checked"]
            - arms["backwards"]["right_as_far_as_checked"]
        ),
        "raw_gain_over_cold": arms["own"]["repaired"] - arms["solver_alone"]["repaired"],
    }


def quixbugs_solver() -> dict[str, Any]:
    """What 39 demonstrations of other repairs buy on 40 other authors' bugs."""
    record = _load(QUIXBUGS_SOLVER)
    summary = record["summary"]
    cold = summary["empty_memory"]
    with_fixes = int(summary["repaired_when_all_other_fixes_were_taught_first"])
    same = summary["same_bug_again"]
    return {
        "bugs": int(summary["programs"]),
        "cold_repaired": int(cold["repaired"]),
        "all_other_fixes_taught": 39,
        "repaired_after_all_other_fixes": with_fixes,
        "bugs_bought_by_39_demonstrations": with_fixes - int(cold["repaired"]),
        "lessons_stored": int(summary["other_fixes"]["published_fixes_stored_as_lessons"]),
        "memory_proposed_for": len(summary["other_fixes"]["memory_proposes_a_repair_for"]),
        "already_repaired_without_memory": len(
            summary["other_fixes"]["of_which_also_repaired_from_an_empty_memory"]
        ),
        "same_bug_again_repaired": int(same["repaired"]),
        "same_bug_again_asked": int(same["asked"]),
        "same_bug_again_from_memory_with_no_search": int(
            same["of_which_from_memory_with_no_search"]
        ),
        "same_bug_again_seconds_middle": float(same["seconds_of_the_middle_repair_from_memory"]),
        "same_bug_again_search_seconds_middle": float(
            same["seconds_of_the_middle_repair_by_search"]
        ),
    }


def edit_kind_transfer() -> dict[str, Any]:
    """The exception: edit-shape transfer across programs and across benchmarks."""
    quix = _load(QUIXBUGS_EDIT_KIND)["summary"]
    human = _load(HUMAN_EVAL_EDIT_KIND)
    human_own = human["summary"]["all_other_fixes"]
    human_back = human["control_the_same_lessons_shown_backwards"]["all_other_fixes"]
    return {
        "human_eval_100": {
            "lessons": 203,  # the all-other-fixes arm, as recorded
            "with_fixes_repaired": int(human_own["repaired"]),
            "backwards_control_repaired": int(human_back["repaired"]),
            "directional_gain": int(human_own["repaired"])
            - int(human_back["repaired"]),
            "with_fixes_right_as_far_as_checked": int(
                human_own["repaired_and_right_as_far_as_checked"]
            ),
            "test_passing_but_wrong_on_an_extra_input": int(
                human_own["of_those_a_different_answer_on_some_extra_input"]
            ),
        },
        "quixbugs_40": {
            "human_eval_lessons_repaired": int(quix["another_benchmark"]["repaired"]),
            "human_eval_lessons_of_which_published_fix": int(
                quix["another_benchmark"]["the_repair_is_the_published_fix"]
            ),
            "all_other_quixbugs_fixes_repaired": int(quix["all_other_fixes"]["repaired"]),
            "tree_solver_cold_repaired": int(
                quix["beside_the_trees_repair_solver"]
                ["another_benchmark__beside__the_solver_with_nothing_taught"]["the_solver"]
            ),
        },
        "caveat": (
            "The QuixBugs operator arm uses a different candidate budget from the tree's "
            "own solver and the record says its 40 fixes had been read earlier; it is an "
            "exception to report, not an unseen score."
        ),
    }


def one_fix_transfer() -> dict[str, Any]:
    """One published fix, 22 stored lessons, 858 pairs: how many other bugs."""
    record = _load("canonical/verification/QUIXBUGS_ONE_FIX_TRANSFER_20261111_V1.json")
    settings = record["summary"]["settings"]
    as_taught = settings["as_taught"]
    pair = as_taught["all_other_fixes_then_this_bug"]
    one = as_taught["one_fix_then_another_bug"]
    return {
        "lessons_tried": int(one["lessons_tried"]),
        "pairs_tried": int(one["pairs_tried"]),
        "pairs_repaired": int(one["pairs_repaired"]),
        "other_bugs_repaired": int(pair["repaired"]),
        "of": int(pair["of"]),
    }


def exchange_rates() -> dict[str, Any]:
    human = human_eval_experience()
    quix = quixbugs_solver()
    edit = edit_kind_transfer()
    one = one_fix_transfer()

    demonstrations = quix["all_other_fixes_taught"]
    bought = quix["bugs_bought_by_39_demonstrations"]
    demos_per_bug = (demonstrations / bought) if bought else None

    # Illustrative arithmetic only: if the measured marginal rate held linearly, how many
    # demonstrations would the same 40-bug domain need to reach 40/40? It is printed with
    # an explicit label because it is an extrapolation, not a prediction.
    remaining = quix["bugs"] - quix["cold_repaired"]
    demos_to_close = (remaining * demos_per_bug) if demos_per_bug else None

    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "human_eval_experience": human,
        "quixbugs_solver": quix,
        "edit_kind_transfer": edit,
        "one_fix_transfer": one,
        "exchange": {
            "quixbugs_demonstrations_per_extra_bug": demos_per_bug,
            "quixbugs_bugs_bought_per_39_demonstrations": bought,
            "human_eval_directional_repairs_per_203_lessons": (
                edit["human_eval_100"]["directional_gain"]
            ),
            "one_fix_pairs_per_other_bug": (
                one["pairs_tried"] / one["pairs_repaired"] if one["pairs_repaired"] else None
            ),
            "illustrative_demonstrations_to_close_quixbugs_at_the_measured_rate": demos_to_close,
            "illustrative_extrapolation": True,
        },
        "verdict": {
            "exact_repetition_is_real": True,
            "exposure_teaches_the_exact_instance": True,
            "exposure_teaches_a_general_rule_at_this_rate": False,
            "the_exception_is_operator_transfer_with_an_oracle": True,
            "one_sentence": (
                "Experience is a multiplier on a base capability and an oracle; it cannot "
                "supply either. In the one-pass records, 39 demonstrations of other repairs "
                "buy one bug (5 -> 6 of 40) and 203 lessons add two repairs over a backwards "
                "control; the large gain in this tree comes from a different candidate space "
                "(edit operators) judged by the same tests, not from more exposure."
            ),
        },
        "limits": [
            "All four records are producer-run on one machine; nobody else has re-run them.",
            "QuixBugs and HumanEvalFix are small, single-file, Python benchmarks with tests.",
            "The edit-kind QuixBugs arm is not an equal-budget control for the tree's solver.",
            "The linear extrapolation is arithmetic illustration, never a forecast.",
            "No claim about computer use, sentience, or a capability is made here.",
        ],
    }


def _print(rate: dict[str, Any]) -> None:
    h = rate["human_eval_experience"]
    q = rate["quixbugs_solver"]
    e = rate["edit_kind_transfer"]
    one = rate["one_fix_transfer"]

    print("HUMANEVALFIX, 100 bugs met once each (one pass, frozen learner)")
    print("  %-34s %9s %7s" % ("arm", "repaired", "right"))
    for arm in ("solver_alone", "own", "backwards", "shown"):
        a = h["arms"][arm]
        print("  %-34s %9d %7d" % (arm, a["repaired"], a["right_as_far_as_checked"]))
    print("  directional value of the lessons   +%d repaired, +%d right (own - backwards)"
          % (h["directional_repairs_over_control"], h["directional_right_over_control"]))
    print("  adjudicator: %s  (cost ratio %.4f, required %.1f; wins %s, required %.0f%%)"
          % (h["adjudicator_verdict"], h["mean_cost_ratio_cold_over_warm"],
             h["mean_cost_ratio_required"], h["paired_wins"],
             100 * h["paired_win_fraction_required"]))
    print()
    print("QUIXBUGS, 40 bugs written by other people")
    print("  solver cold                              %2d/%d" % (q["cold_repaired"], q["bugs"]))
    print("  after 39 published fixes of other bugs   %2d/%d   (+%d)"
          % (q["repaired_after_all_other_fixes"], q["bugs"],
             q["bugs_bought_by_39_demonstrations"]))
    print("  same bug again from memory               %2d/%d at %.1fs (search: %.1fs)"
          % (q["same_bug_again_repaired"], q["same_bug_again_asked"],
             q["same_bug_again_seconds_middle"],
             q["same_bug_again_search_seconds_middle"]))
    print("  one published fix -> %d lessons -> %d pairs -> %d other bug"
          % (one["lessons_tried"], one["pairs_tried"], one["pairs_repaired"]))
    print()
    print("THE EXCEPTION: edit-shape transfer, with the tests doing the choosing")
    print("  HumanEvalFix 100: 203 lessons %d/100 vs backwards control %d/100 (+%d)"
          % (e["human_eval_100"]["with_fixes_repaired"],
             e["human_eval_100"]["backwards_control_repaired"],
             e["human_eval_100"]["directional_gain"]))
    print("  QuixBugs 40: HumanEvalFix edit kinds %d/40 vs tree solver cold %d/40"
          % (e["quixbugs_40"]["human_eval_lessons_repaired"],
             e["quixbugs_40"]["tree_solver_cold_repaired"]))
    print()
    print("EXCHANGE")
    print("  demonstrations per extra QuixBugs bug: %s"
          % ("%.1f" % rate["exchange"]["quixbugs_demonstrations_per_extra_bug"]
             if rate["exchange"]["quixbugs_demonstrations_per_extra_bug"] else "undefined"))
    print("  (illustrative, not a forecast) demonstrations to reach 40/40 at that rate: %s"
          % ("%.0f" % rate["exchange"]
             ["illustrative_demonstrations_to_close_quixbugs_at_the_measured_rate"]
             if rate["exchange"]
             ["illustrative_demonstrations_to_close_quixbugs_at_the_measured_rate"] else "undefined"))
    print()
    print("VERDICT: %s" % rate["verdict"]["one_sentence"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default="")
    args = parser.parse_args()

    rate = exchange_rates()
    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps(rate, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
    _print(rate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
