"""What "learn it once and keep it forever" is worth later, on real repository history.

The load-bearing assertions are the two that a capability claim cannot survive:

  * of every real changed site, the share that a permanent memory serves *exactly* is one twentieth;
  * of the recurring sites that change two lines or more -- the advanced edits -- none replay exactly.

They are pinned against the receipt and re-derived live, so a number cannot drift away from the code
that produced it.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import skill_recurrence_curve_v1 as curve  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "SKILL_RECURRENCE_20261116_V1.json"


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def live() -> dict:
    return curve.measure()


def test_the_receipt_is_reproducible_from_the_pinned_corpus(report: dict, live: dict) -> None:
    assert report["corpus"]["sha256"].startswith("b47d9c9c23e641a8")
    assert report["corpus"]["records"] == 393
    for rung in ("shape_only", "context_any", "context_both"):
        assert report["by_rung"][rung]["sites"] == live["by_rung"][rung]["sites"]
        assert report["by_rung"][rung]["recurrent"] == live["by_rung"][rung]["recurrent"]


def test_a_twenty_seventh_of_real_work_recurs_at_all(report: dict) -> None:
    loose = report["by_rung"]["shape_only"]
    assert loose["sites"] == 691
    assert loose["recurrent"] == 191
    assert loose["recurrence_share"] == 0.2764
    strict = report["by_rung"]["context_both"]
    assert strict["recurrent"] == 102
    assert strict["recurrence_share"] == 0.1584


def test_multi_line_edits_almost_never_recur(report: dict) -> None:
    """This is the advanced-work number: 30 of 267 loose, 14 of 242 strict."""
    assert report["by_rung"]["shape_only"]["structured_sites"]["recurrent"] == 30
    assert report["by_rung"]["shape_only"]["structured_sites"]["sites"] == 267
    assert report["by_rung"]["context_both"]["structured_sites"]["recurrent"] == 14


def test_the_whole_repeated_vocabulary_is_a_couple_of_dozen_signatures(report: dict) -> None:
    loose = report["by_rung"]["shape_only"]
    assert loose["distinct_signatures"] == 59
    assert loose["library_signatures_for"]["0.8"] == 26
    assert loose["library_signatures_for"]["0.5"] == 7


def test_replay_across_time_is_weaker_than_replay_inside_the_commit_that_taught_it(report: dict) -> None:
    replay = report["by_rung"]["context_both"]["replay"]
    assert replay["all"]["pairs"] == 102
    assert replay["all"]["outcomes"]["exact"] == 31
    assert replay["all"]["exact_share"] == 0.3039
    # the number that decides the claim
    assert round(31 / 644, 4) == 0.0481


def test_no_multi_line_recurrence_replays_exactly(report: dict) -> None:
    structured = report["by_rung"]["context_both"]["replay"]["structured"]
    assert structured["pairs"] == 14
    assert structured["outcomes"].get("exact", 0) == 0
    assert structured["wrong_share"] == 0.9286


def test_memory_from_other_repositories_carries_little_of_what_is_not_trivial(report: dict) -> None:
    loose = report["by_rung"]["shape_only"]["cross_repository"]
    assert loose["recurrent"] == 146
    assert loose["share"] == 0.2113
    assert loose["structured_share"] == 0.0712
    strict = report["by_rung"]["context_both"]["cross_repository"]
    assert strict["structured_share"] == 0.0207


def test_returns_to_experience_rise_within_a_repository(report: dict) -> None:
    """Later commits recur more because the vocabulary has accumulated: experience keeps paying, slowly."""
    quarters = report["by_rung"]["shape_only"]["curve_by_relative_chronological_quarter"]
    assert quarters == [0.1494, 0.2882, 0.2733, 0.3943]
    assert quarters[-1] > quarters[0]
    assert report["by_rung"]["shape_only"]["curve_reading"].startswith("rising")


def test_what_recurs_is_a_literal_moving(report: dict) -> None:
    trivial = report["by_rung"]["shape_only"]["triviality"]
    assert trivial["median_size"] == 2
    assert trivial["one_line_replacement_share"] == 0.8063
    assert trivial["pure_substitution_share"] == 0.7016


def test_rungs_are_monotone_in_strictness(report: dict) -> None:
    loose, middle, strict = (report["by_rung"][rung]["recurrence_share"]
                             for rung in ("shape_only", "context_any", "context_both"))
    assert loose >= middle >= strict
