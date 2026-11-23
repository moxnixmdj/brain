"""The guard that stops a corpus from containing its own answer.

Built after two published numbers (43.6% and 47.0%) turned out to be 11.8% and 9.7% once rows
whose goal shared a stem with the truth were removed. The guard is the reusable part; the
scorers that produced the inflated numbers are not.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import the_goal_must_not_share_a_stem_v1 as G


def test_a_goal_that_is_the_name_is_rejected():
    assert G.stem_free("align", ["Align", "Console"]) is False
    assert G.stem_free("table", ["Table"]) is False
    assert G.stem_free("progress", ["ProgressBar"]) is False


def test_a_goal_that_merely_mentions_a_near_candidate_is_rejected():
    # `tabulate` does NOT collide with "table" (tabl vs tabu); a guard that rejected it would
    assert G.stem_free("table", ["tabulate"]) is True   # 4th char differs
    assert G.stem_free("print", ["pretty_print"]) is False


def test_a_real_sentence_with_no_shared_stem_is_kept():
    """This is the row that actually measures something, and the guard must not throw it away."""
    assert G.stem_free("make this text line up in columns", ["Align"]) is True
    assert G.stem_free("show a progress bar while copying", ["Console", "Live"]) is True


def test_the_guard_is_checked_against_EVERY_candidate_not_only_the_truth():
    """Guarding only the truth lets a leak through a near-miss the goal also names."""
    rows = [{"goal": "table", "truth": "Table"}]
    res = G.audit(rows, lambda r: ["Table", "tabulate"])
    assert res["kept"] == 0 and res["dropped"] == 1


def test_audit_reports_what_it_threw_away():
    rows = [{"goal": "align"}, {"goal": "make the columns line up"}]
    cands = {"align": ["Align"], "make the columns line up": ["Console"]}
    res = G.audit(rows, lambda r: cands[r["goal"]])
    assert res["rows"] == 2 and res["kept"] == 1 and res["dropped"] == 1
    assert res["drop_rate"] == 0.5


def test_a_thin_measurement_is_refused_rather_than_reported():
    assert G.verdict(4, 4)["meaningful"] is False      # 100% of 4 rows is not a result
    assert G.verdict(30, 12)["meaningful"] is True
