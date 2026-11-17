"""Tests for the price of a failure.

The claim is an equality, not a heuristic: a failure eliminates exactly 2^k hypotheses where k is
the number of shared candidates it KEPT. Everything else here follows from it, and the tests check
it against the live counter rather than against a restatement of itself.
"""
from __future__ import annotations

import math
import sys

sys.path.insert(0, "/home/user/brain")
from canonical.tools import a_failure_is_worth_two_to_the_keys_kept_v1 as PRICE  # noqa: E402


def test_one_failure_kills_exactly_two_to_the_kept_count():
    facts = PRICE.universe(12)
    for kept in range(1, 12):
        row = PRICE.killed_by_one_failure(facts, kept)
        assert row["killed"] == 2 ** kept, (kept, row)


def test_the_law_holds_at_the_receipts_own_scale():
    facts = PRICE.universe(23)
    for kept in (1, 3, 10, 20):
        row = PRICE.killed_by_one_failure(facts, kept)
        assert row["killed"] == 2 ** kept


def test_a_near_miss_beats_a_dramatic_failure():
    """The counterintuitive consequence: few facts dropped is far MORE informative."""
    facts = PRICE.universe(23)
    near_miss = PRICE.killed_by_one_failure(facts, 20)   # dropped 3
    dramatic = PRICE.killed_by_one_failure(facts, 3)     # dropped 20
    assert near_miss["killed"] > dramatic["killed"] * 100_000
    assert near_miss["dropped"] < dramatic["dropped"]


def test_killing_power_is_exponential_in_kept_and_nothing_else():
    """Doubling the kept count must double the kill, at every scale."""
    facts = PRICE.universe(16)
    rows = {r["kept"]: r["killed"] for r in PRICE.swing(facts)}
    for kept in range(1, 15):
        assert rows[kept + 1] == 2 * rows[kept]


def test_the_receipts_two_failures_were_one_failure_recorded_twice():
    """2^23 - 8 is only reachable if both failures omitted the same three candidates."""
    facts = PRICE.universe(23)
    cmp = PRICE.two_failure_comparison(facts)
    assert cmp["same_failure_twice"]["killed"] == 8
    assert cmp["same_failure_twice"]["survivors"] == 2 ** 23 - 8
    assert cmp["receipt_shape_2_pow_23_minus_8"] is True
    assert cmp["two_distinct_failures"]["killed"] == 15
    assert cmp["second_failure_bought"] == 7


def test_a_repeated_failure_buys_almost_nothing():
    """The measured reason 'fail more' is not a learning strategy."""
    facts = PRICE.universe(23)
    bought = PRICE.two_failure_comparison(facts)["second_failure_bought"]
    assert bought / (2 ** 23) < 1e-6


def test_a_failure_that_keeps_everything_kills_half_the_space():
    """Kept = |A|-1 is the single most informative failure available: it halves the space."""
    facts = PRICE.universe(11)
    row = PRICE.killed_by_one_failure(facts, 10)
    assert row["killed"] == 1024
    assert math.log2(row["total"] / row["survivors"]) == 1.0
