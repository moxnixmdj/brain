#!/usr/bin/env python3
"""A rule that passes every structural check can still be wrong, and only execution shows it.

These tests hold `rule_generalization_probe_v1` to being able to say BREAKS, because a probe
that can only ever say HOLDS is not a measurement. The decisive case is at the bottom: one
taught edit, two victims, opposite verdicts, and the disagreement lands on the single input the
demonstration never observed.
"""
from __future__ import annotations

import pytest

from canonical.tools import rule_generalization_probe_v1 as P


def _strict(_src, point):
    return point < 100


# ---------------------------------------------------------------------------
# HOLDS and BREAKS must both be reachable, on the same rule shape
# ---------------------------------------------------------------------------
def test_a_rule_that_learned_the_right_direction_holds_on_a_new_victim():
    outcome = P.probe_rule(
        "def classify(x):\n    return x <= 100\n",
        "def classify(x):\n    return x < 100\n",
        oracle=_strict, probes=(0, 99, 100, 101),
        victim_snippet="def tier(a):\n    return a <= 100\n",
    )
    assert outcome["verdict"] == P.HOLDS
    assert outcome["edited"] == "def tier(a):\n    return a < 100\n"
    assert all(p["outcome"] == "AGREES" for p in outcome["probes"])


def test_a_rule_that_learned_the_wrong_direction_breaks_on_a_new_victim():
    outcome = P.probe_rule(
        "def classify(x):\n    return x < 100\n",
        "def classify(x):\n    return x <= 100\n",
        oracle=_strict, probes=(0, 99, 100, 101),
        victim_snippet="def tier(a):\n    return a < 100\n",
    )
    assert outcome["verdict"] == P.BREAKS
    failed = [p for p in outcome["probes"] if p["outcome"] == "DISAGREES"]
    assert len(failed) == 1
    # the error is exactly at the input the single demonstration never covered
    assert failed[0]["probe"] == 100
    assert failed[0]["expected"] is False and failed[0]["actual"] is True


def _inclusive_at_50(_src, point):
    """A different victim whose SPEC says 50 is inclusive: the taught direction is wrong here."""
    return point <= 50


def test_the_same_rule_is_right_on_one_victim_and_wrong_on_another():
    """Correctness of a learned rule is a property of the pair, not of the rule.

    The taught edit proves 100 is exclusive. The rule anti-unifies to "boundary constant `$C`,
    direction `<=`" -- so it carries the direction as a LITERAL and the constant as a HOLE.
    It therefore transfers to every constant, and to no other direction.
    """
    before = "def classify(x):\n    return x <= 100\n"
    after = "def classify(x):\n    return x < 100\n"

    same_convention_new_constant = P.probe_rule(
        before, after, oracle=_strict, probes=(99, 100, 101),
        victim_snippet="def tier(a):\n    return a <= 100\n")
    assert same_convention_new_constant["verdict"] == P.HOLDS

    other_convention = P.probe_rule(
        before, after, oracle=_inclusive_at_50, probes=(49, 50, 51),
        victim_snippet="def tier(a):\n    return a <= 50\n")
    assert other_convention["verdict"] == P.BREAKS
    failed = [p for p in other_convention["probes"] if p["outcome"] == "DISAGREES"]
    assert [p["probe"] for p in failed] == [50]


def test_a_victim_already_in_the_taught_direction_is_NOT_APPLICABLE_not_a_pass():
    """The rule's direction is a literal, so a victim with the other direction is untouched."""
    outcome = P.probe_rule(
        "def classify(x):\n    return x <= 100\n", "def classify(x):\n    return x < 100\n",
        oracle=_strict, probes=(100,),
        victim_snippet="def tier(a):\n    return a < 100\n")
    assert outcome["verdict"] == P.NOT_APPLICABLE


# ---------------------------------------------------------------------------
# a refused probe is not a pass
# ---------------------------------------------------------------------------
def test_no_oracle_is_REFUSED_and_never_HOLDS():
    outcome = P.probe_rule("def f(x):\n    return x <= 1\n", "def f(x):\n    return x < 1\n",
                           oracle=None, probes=(0,))
    assert outcome["verdict"] == P.REFUSED
    assert outcome["note"].startswith("a refused probe is not a pass")


def test_no_probes_is_REFUSED():
    outcome = P.probe_rule("def f(x):\n    return x <= 1\n", "def f(x):\n    return x < 1\n",
                           oracle=_strict, probes=())
    assert outcome["verdict"] == P.REFUSED
    assert outcome["reason"] == "NO_PROBES"


def test_a_rule_that_does_not_fire_is_NOT_APPLICABLE_not_HOLDS():
    """No edit happened, so nothing was verified. Calling that a hold is the recurring bug."""
    outcome = P.probe_rule(
        "def f(x):\n    return x <= 1\n", "def f(x):\n    return x < 1\n",
        oracle=_strict, probes=(0,),
        victim_snippet="def other(a, b):\n    return a + b\n",
    )
    assert outcome["verdict"] == P.NOT_APPLICABLE
    assert outcome["reason"] == "RULE_DOES_NOT_FIRE_ON_VICTIM"


def test_an_empty_rule_is_NO_RULE_not_a_silent_pass():
    outcome = P.probe_rule("def f(x):\n    return x\n", "def f(x):\n    return x\n",
                           oracle=_strict, probes=(0,), rule={})
    assert outcome["verdict"] == P.NO_RULE
    assert outcome["reason"] == "SNIPPET_PAIR_DID_NOT_GENERALIZE"


def test_the_anti_unifier_will_generalize_out_of_garbage_and_the_probe_says_so():
    """Measured, and reported rather than hidden: nonsense in, a rule out, BREAKS on execution.

    This is worth pinning. "The pair generalized" is not a quality signal -- the learner has no
    notion of a well-formed edit, so the executed probe is the only thing standing between
    garbage and a stored rule.
    """
    outcome = P.probe_rule("not python (", "still not python", oracle=_strict, probes=(0,))
    assert outcome["verdict"] == P.BREAKS
    assert outcome["probes"][0]["outcome"] in {"EXECUTION_ERROR", "DISAGREES"}


# ---------------------------------------------------------------------------
# execution
# ---------------------------------------------------------------------------
def test_run_snippet_calls_the_last_top_level_function():
    assert P.run_snippet("def a(x):\n    return 1\n\ndef b(x):\n    return x * 2\n", (4,)) == 8


def test_run_snippet_raises_rather_than_returning_none_when_there_is_nothing_to_call():
    with pytest.raises(SyntaxError):
        P.run_snippet("X = 1\n")


def test_an_execution_error_is_recorded_and_breaks_the_probe():
    outcome = P.probe_rule(
        "def f(x):\n    return x < 100\n", "def f(x):\n    return x[0] < 100\n",
        oracle=_strict, probes=(5,),
    )
    assert outcome["verdict"] == P.BREAKS
    assert outcome["probes"][0]["outcome"] == "EXECUTION_ERROR"


# ---------------------------------------------------------------------------
# the demonstrator reports the finding and the CLI goes red on it
# ---------------------------------------------------------------------------
def test_demonstrate_shows_one_rule_two_verdicts():
    result = P.demonstrate()
    assert result["honest_rule_on_new_victim"]["verdict"] == P.HOLDS
    assert result["overgeneral_rule_on_new_victim"]["verdict"] == P.BREAKS
    assert result["no_oracle"]["verdict"] == P.REFUSED
    assert P.main([]) == 1
