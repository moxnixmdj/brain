"""Pin the exchange rate the owner's plan is priced at, from the landed records."""
from __future__ import annotations

import json
import pathlib

from canonical.tools import the_exchange_rate_of_one_lesson_20261112_v1 as rate


def test_source_records_exist_and_are_producer_run() -> None:
    root = pathlib.Path(__file__).resolve().parents[2]
    for relative in (
        rate.HUMAN_EVAL_EXPERIENCE,
        rate.QUIXBUGS_SOLVER,
        rate.QUIXBUGS_EDIT_KIND,
        rate.HUMAN_EVAL_EDIT_KIND,
    ):
        record = json.loads((root / relative).read_text(encoding="utf-8"))
        assert record["authority"].startswith("NONE"), relative


def test_human_eval_one_pass_stream_numbers() -> None:
    measured = rate.human_eval_experience()
    assert measured["bugs"] == 100
    assert measured["arms"]["solver_alone"] == {
        "repaired": 53, "right_as_far_as_checked": 36,
    }
    assert measured["arms"]["own"] == {
        "repaired": 64, "right_as_far_as_checked": 45,
    }
    assert measured["arms"]["backwards"] == {
        "repaired": 62, "right_as_far_as_checked": 42,
    }
    assert measured["arms"]["shown"] == {
        "repaired": 65, "right_as_far_as_checked": 45,
    }
    assert measured["raw_gain_over_cold"] == 11
    assert measured["directional_repairs_over_control"] == 2
    assert measured["directional_right_over_control"] == 3
    assert measured["adjudicator_verdict"] == "NO_COMPOUNDING"
    assert round(measured["mean_cost_ratio_cold_over_warm"], 4) == 1.0819
    assert measured["paired_wins"] == "31/98"


def test_quixbugs_39_demonstrations_buy_one_bug() -> None:
    measured = rate.quixbugs_solver()
    assert measured["bugs"] == 40
    assert measured["cold_repaired"] == 5
    assert measured["all_other_fixes_taught"] == 39
    assert measured["repaired_after_all_other_fixes"] == 6
    assert measured["bugs_bought_by_39_demonstrations"] == 1
    assert measured["lessons_stored"] == 22
    # Exact repetition is the part that is genuinely cheap.
    assert measured["same_bug_again_asked"] == 4
    assert measured["same_bug_again_repaired"] == 4
    assert measured["same_bug_again_from_memory_with_no_search"] == 4
    assert measured["same_bug_again_seconds_middle"] < measured[
        "same_bug_again_search_seconds_middle"
    ]


def test_one_published_fix_repairs_one_other_bug_in_858_pairs() -> None:
    measured = rate.one_fix_transfer()
    assert measured["lessons_tried"] == 22
    assert measured["pairs_tried"] == 858
    assert measured["pairs_repaired"] == 1
    assert measured["other_bugs_repaired"] == 1


def test_operator_transfer_is_the_exception_not_the_rule() -> None:
    measured = rate.edit_kind_transfer()
    assert measured["human_eval_100"]["with_fixes_repaired"] == 62
    assert measured["human_eval_100"]["backwards_control_repaired"] == 56
    assert measured["human_eval_100"]["directional_gain"] == 6
    assert measured["human_eval_100"]["test_passing_but_wrong_on_an_extra_input"] == 9
    # The cross-benchmark arm is large, and it is explicitly not an equal-budget control.
    assert measured["quixbugs_40"]["human_eval_lessons_repaired"] == 20
    assert measured["quixbugs_40"]["tree_solver_cold_repaired"] == 5
    assert "different candidate budget" in measured["caveat"]


def test_exchange_rate_and_illustrative_extrapolation() -> None:
    measured = rate.exchange_rates()
    exchange = measured["exchange"]
    assert exchange["quixbugs_demonstrations_per_extra_bug"] == 39.0
    assert exchange["quixbugs_bugs_bought_per_39_demonstrations"] == 1
    assert exchange["human_eval_directional_repairs_per_203_lessons"] == 6
    assert exchange["one_fix_pairs_per_other_bug"] == 858.0
    assert exchange["illustrative_demonstrations_to_close_quixbugs_at_the_measured_rate"] == 1365
    assert exchange["illustrative_extrapolation"] is True
    assert measured["verdict"]["exposure_teaches_the_exact_instance"] is True
    assert measured["verdict"]["exposure_teaches_a_general_rule_at_this_rate"] is False
