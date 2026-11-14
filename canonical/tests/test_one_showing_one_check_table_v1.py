"""The table must keep telling the truth, including the row that is bad news.

This tool exists to answer one question clause by clause, so the risk it carries is that a later
change makes a row say something nicer than what was measured. These tests pin the two rows that
could drift: clause 3 (the check cannot see the taught boundary) and clause 5 (nothing is claimed
for computer use).
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import one_showing_one_check_table_20261114_v1 as T  # noqa: E402


@pytest.fixture(scope="module")
def table(tmp_path_factory):
    return T.measure(tmp_path_factory.mktemp("table"))


def _row(table, startswith):
    return next(r for r in table["rows"] if r["clause"].startswith(startswith))


def test_the_demonstration_is_the_tree_s_own_and_not_a_fixture(table):
    from canonical.swe_kernel import lesson_admission_gate_v1 as G
    assert T.BEFORE == G.BEFORE and T.AFTER == G.AFTER and T.POINTS == G.POINTS


def test_one_showing_is_kept(table):
    row = _row(table, "1.")
    assert row["measured"] is True
    assert "rows_in_store=1" in row["evidence"]


def test_it_reaches_an_unseen_function(table):
    row = _row(table, "2.")
    assert row["measured"] is True


def test_the_check_cannot_see_the_taught_boundary_and_the_table_says_so(table):
    """The row that matters. If this ever turns True, the licence changed under it -- check why.

    It is False because the fixture's tests call `at_cap(10)` and `at_cap(100)` and never the
    boundary itself, so `<=` -> `<` changes no passing test. That is the whole finding.
    """
    row = _row(table, "3.")
    assert row["measured"] is False
    assert "NOT among them" in row["evidence"]
    assert "changed no passing test" in row["evidence"]


def test_a_wrong_lesson_is_refused_by_admission(table):
    row = _row(table, "4.")
    assert row["measured"] is True
    assert "rows left in the store: 0" in row["evidence"]


def test_nothing_is_claimed_for_computer_use(table):
    row = _row(table, "5.")
    assert row["measured"] is None
    assert "NOT MEASURED" in row["evidence"]


def test_the_verdict_names_the_failing_clause(table):
    assert "fails at 3" in table["verdict"]
    assert "not measured at all" in table["verdict"]


def test_no_spend_and_no_model_calls(table):
    assert table["spend_usd"] == 0 and table["model_calls"] == 0
    assert table["authority"] == "NONE"
