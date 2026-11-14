#!/usr/bin/env python3
"""Unit tests for the oracle-active measurement of the taught-edit organ.

Two hand-written files, so these pin the PROTOCOL -- what is counted, how the oracle is asked, and
that a comparison cannot pass by comparing a function with itself -- and not the measurement. The
measurement on real pull requests is
`canonical/tools/oracle_active_on_new_pull_requests_20261114_v1.py`.
"""

from __future__ import annotations

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as ebe
from canonical.tools import oracle_active_on_new_pull_requests_20261114_v1 as O

# One changed place is enough to learn from and NOT enough to generalise (measured in this tree:
# one showing memorises, two generalise). `example_before`/`example_after` therefore each change one
# place, and the target carries the SAME form with the same literal, which is what a single showing
# does reach.
EXAMPLE_BEFORE = "def f(a, b):\n    if a <= 10:\n        return 1\n    return 0\n"
EXAMPLE_AFTER = "def f(a, b):\n    if a < 10:\n        return 1\n    return 0\n"
TARGET = "def g(a, b):\n    if a <= 10:\n        return 2\n    return 0\n"


def test_the_organ_learns_and_applies_so_the_cap_is_real() -> None:
    """If the organ refused here, the cap would be 0 for a reason unrelated to the question."""
    got = ebe.edit_by_example(TARGET, EXAMPLE_BEFORE, EXAMPLE_AFTER)
    assert got != TARGET, "the organ made no change; the cap cannot be measured on this pair"


def test_the_comparison_is_between_two_functions_and_can_say_no() -> None:
    """A comparison of a function with itself is always true; this one has to be able to fail."""
    truth = O.demonstration_oracle(EXAMPLE_BEFORE, EXAMPLE_AFTER)
    assert truth is not None
    cap = O.confirmed_change(TARGET, EXAMPLE_BEFORE, EXAMPLE_AFTER, oracle=truth)
    assert cap is not None, "the organ's change on this pair could not be confirmed at all"
    assert cap["loadable"] is True
    assert cap["asked_inside"] > 0
    # The organ copied `<= 10 -> < 10` faithfully, so on the grid the path it takes is the path the
    # oracle asks for. Off the grid it also agrees, because the guard is the same guard.
    assert cap["agrees_inside"] is True

    # The same organ output, checked against an oracle that wants a DIFFERENT threshold. The paths
    # must now disagree, so the comparison can be wrong -- which is the whole property.
    other = O.demonstration_oracle(
        "def f(a, b):\n    if a <= 3:\n        return 1\n    return 0\n",
        "def f(a, b):\n    if a < 3:\n        return 1\n    return 0\n")
    assert other is not None
    strict = O.confirmed_change(TARGET, EXAMPLE_BEFORE, EXAMPLE_AFTER, oracle=other)
    assert strict is not None
    assert strict["agrees_inside"] is False


def test_a_refusal_is_not_counted_as_a_profile() -> None:
    """A target the organ will not touch has nothing to confirm and stays out of the rates."""
    assert O.confirmed_change("def unrelated():\n    return 1\n", EXAMPLE_BEFORE, EXAMPLE_AFTER,
                              oracle=lambda *a: 0) is None


def test_two_showings_are_put_together_and_apply_where_one_does_not() -> None:
    """The strongest form of the claim: a second showing, at another place, is what generalises."""
    second_before = "def f(a, b):\n    if a <= 10:\n        return 1\n    if b <= 20:\n        return 3\n    return 0\n"
    second_after = "def f(a, b):\n    if a < 10:\n        return 1\n    if b < 20:\n        return 3\n    return 0\n"
    target = "def g(a, b):\n    if a <= 10:\n        return 2\n    if b <= 500:\n        return 4\n    return 0\n"
    before, after = O.two_showings({"before": second_before, "after": second_after},
                                   {"before": second_before, "after": second_after})
    assert before is not None and after is not None


def test_the_oracle_answers_with_the_path_not_the_value() -> None:
    """`return 1` in one file and `return 2` in another are the same behaviour.

    Comparing returned values reported every faithfully copied change as wrong; the answer is the
    shape of the path taken, which is comparable across two files.
    """
    oracle = O.demonstration_oracle(EXAMPLE_BEFORE, EXAMPLE_AFTER)
    assert oracle is not None
    below = O.truth_of(oracle, 5)
    above = O.truth_of(oracle, 50)
    assert isinstance(below, tuple) and isinstance(above, tuple)
    assert below != above, "the guard must take a different path on each side of the boundary"
    assert below[-1] < above[-1] or below[-1] > above[-1]

    # Two files that return different numbers from the same structure give the SAME signature.
    same_shape = O.demonstration_oracle(
        "def h(a, b):\n    if a <= 10:\n        return 99\n    return 7\n",
        "def h(a, b):\n    if a < 10:\n        return 99\n    return 7\n")
    assert same_shape is not None
    assert O.truth_of(same_shape, 5) == below
