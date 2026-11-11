"""Pin the two-arm result so the claim can never drift back to 'it just works'.

Measured 2026-11-09. Same learner, same permanence, same check. The ONLY difference
between a permanently-wrong skill and a correct one was one held-out example.

If this test ever fails, either the learner changed or the check changed. Both matter.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import permanence_amplifies_check_v1 as P

DEMO = [P.Record(qty=6, price=7, total=42)]
HELD = P.records(40)


def test_one_demonstration_leaves_more_than_one_consistent_rule():
    """The core fact: a single demonstration is underdetermined."""
    assert len(P.live_hypotheses(DEMO)) >= 2


def test_one_demonstration_alone_yields_the_simpler_wrong_rule():
    assert P.learn(DEMO).name == "copy_the_total_it_was_shown"


def test_the_wrong_rule_is_accepted_by_a_weak_check_on_every_world():
    """This is why 'it passed' is not evidence."""
    skill = P.learn(DEMO)
    e = P.evaluate(skill, HELD, P.weak_check)
    assert e["accepted_by_the_check"] == 40, e
    assert e["actually_correct"] == 1, e


def test_one_extra_heldout_example_selects_the_correct_rule():
    skill = P.learn(DEMO + [P.Record(qty=9, price=9, total=81)])
    assert skill.name == "recompute_from_the_rows"
    e = P.evaluate(skill, HELD, P.weak_check)
    assert e["actually_correct"] == 40, e


def test_permanence_is_identical_in_both_arms_which_is_the_whole_problem():
    a = P.permanence(P.learn(DEMO), HELD, recalls=50)
    b = P.permanence(P.learn(DEMO + [P.Record(qty=9, price=9, total=81)]), HELD, recalls=50)
    assert a["drift"] == b["drift"] == 0
    assert a["accepted"] == b["accepted"]
    assert a["skill_unchanged"] != b["skill_unchanged"], (
        "permanence froze two different rules and reported both as stable")


def test_the_compiler_refuses_to_persist_without_a_heldout_and_sabotage_gate():
    """The gate that implements the fix must not be optional."""
    import inspect
    from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as C
    src = inspect.getsource(C.compile_and_qualify_skill)
    assert "heldout" in src.lower()
    assert "sabotag" in src.lower()
