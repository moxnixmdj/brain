"""Tests for THE_CEILING_OF_LEARN_ONCE_V1.

The point of these tests is to make the ceiling FALSIFIABLE rather than rhetorical. Every term is a
fraction taken from a merged receipt; the product is what the claim has to survive. If any term is
later re-measured and changes, these assertions fail loudly and the ceiling moves with it -- which
is the whole reason to state it as a product instead of as prose.
"""
from __future__ import annotations

import json
import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, "/home/user/brain")

from canonical.swe_kernel import the_ceiling_of_learn_once_v1 as C  # noqa: E402


@pytest.fixture(scope="module")
def report():
    return C.compute()


# -- the terms are exact fractions, and they are the receipts' own numbers -------- #


def test_every_term_is_an_exact_fraction_not_a_float(report):
    """A rounded ceiling is not a ceiling.

    Terms are carried as Fractions, not floats. Note that `as_recorded` follows whatever form the
    source receipt used -- one term is recorded as "2.1%" rather than a ratio -- so the exactness
    check is on the Fraction, and the recorded string is only required to be non-empty.
    """
    for name, term in C.TERMS.items():
        assert isinstance(term["value"], Fraction), name
        assert term["as_recorded"], name
    # the percentage-form term must still be exactly 21/1000
    assert C.TERMS["cross_repo_multi_line_strict"]["value"] == Fraction(21, 1000)


def test_end_to_end_is_exactly_31_of_644(report):
    """31 exact replays out of 644 strict sites -- the receipt's own end-to-end number."""
    assert report["terms"]["end_to_end_exact"]["value"] == "31/644"
    assert report["the_ceiling"]["learn_once_serves"] == "31/644"


def test_the_product_is_a_twenty_first(report):
    assert report["the_ceiling"]["percent_of_real_edits"] == 4.814
    assert report["the_ceiling"]["one_in"] == 20.8


def test_advanced_edits_are_served_zero_times(report):
    """The advanced case is not a small fraction of the advanced case; it is zero of fourteen."""
    assert report["terms"]["multi_line_strict_served"]["value"] == "0/14"
    assert "0 of 14" in report["the_ceiling"]["advanced_edits_ceiling"]


def test_recurrence_times_determinacy_equals_the_product(report):
    """The ceiling must be the product of its parts, not a separately quoted figure."""
    recurrence = C.TERMS["recurrence_strict"]["value"]
    determinacy = C.TERMS["replay_determinacy_strict"]["value"]
    assert recurrence * determinacy == C.TERMS["end_to_end_exact"]["value"]


# -- the two checks this session actually ran ------------------------------------ #


def test_verified_skills_still_do_not_compose(report):
    """Reproduced live on the tree's own store: both accepted, sequence FAIL, net change nothing."""
    comp = report["composition_is_a_separate_wall"]
    assert comp["both_accepted"] is True
    assert comp["sequence_verdict"] == "FAIL"
    assert comp["sequence_reason"] == "STEP_REVERTED_EARLIER_STATE:step2"
    assert comp["net_change_is_nothing"] is True
    assert comp["steps"] == ["CHANGED", "REVERTED"]


def test_the_exact_minimum_demonstration_count_is_what_shipped(report):
    """Greedy and exact agree here, and no smaller cover exists -- so acquisition is not the wall."""
    acq = report["acquisition_is_solved"]
    assert acq["task_A"]["exact"] == 4
    assert acq["task_C"]["exact"] == 1
    assert acq["task_A"]["smaller_cover_exists"] is False
    assert acq["task_C"]["smaller_cover_exists"] is False


def test_task_C_leaves_states_no_demonstration_can_licence(report):
    assert report["acquisition_is_solved"]["uncoverable_task_C"] == 28


# -- the answer ---------------------------------------------------------------- #


def test_the_answer_is_that_learning_rate_is_not_the_bottleneck(report):
    ans = report["whether_learning_rate_is_the_bottleneck"]
    assert ans["answer"] == "NO"
    assert "property of the WORK" in ans["why"]


def test_the_split_accounts_for_all_of_real_work(report):
    """MEMORISE + SYNTHESISE must sum to exactly 1; REFUSE is admitted as unmeasured."""
    split = report["three_way_split_of_real_work"]
    mem = Fraction(split["MEMORISE"]["share"])
    syn = Fraction(split["SYNTHESISE"]["share"])
    assert mem + syn == 1
    assert "unmeasured" in split["REFUSE"]["share"]


def test_it_admits_the_unmeasured_term_rather_than_hiding_it(report):
    """The REFUSE share is the least honest number in the tree and is labelled as such."""
    assert "least honest" in report["three_way_split_of_real_work"]["REFUSE"]["share"]


def test_authority_is_none_and_nothing_was_spent(report):
    assert report["authority"].startswith("NONE")
    assert report["incremental_spend_usd"] == 0
    assert report["model_calls"] == 0
    assert report["network_calls"] == 0


def test_it_cites_receipts_rather_than_re_measuring_them(report):
    reused = report["reused_not_rebuilt"]
    assert any("LEARN_ONCE_KEEP_FOREVER" in r for r in reused)
    assert any("ONE_DEMONSTRATION_AMORTISES" in r for r in reused)
    assert any("SKILLS_DONT_COMPOSE" in r for r in reused)


def test_receipt_on_disk_round_trips():
    path = Path("canonical/verification/THE_CEILING_OF_LEARN_ONCE_20261116_V1.json")
    if not path.exists():
        return
    on_disk = json.loads(path.read_text())
    live = C.compute()
    assert on_disk["the_ceiling"] == live["the_ceiling"]
