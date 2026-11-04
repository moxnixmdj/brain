"""Three findings from asking the deepest question available: does experience compound?

Measured 2026-11-03. Each test below pins a fact that was not known before this session, and two
of them pin a DEFECT that made an earlier number meaningless.

FINDING 1 — meeting more kinds does not make the next kind cheaper.
    Ten never-before-seen kinds, solved cold and solved after nine prior kinds:
    **byte-identical, 10/10, net saving 0** (1525 acts both arms). The transition model is keyed
    per kind, so it cannot compound by construction. This is the fact that separates a skill
    cache from a creature, and it is now a test rather than an opinion.

FINDING 2 — every lambda goal was the SAME goal.
    `_goal_key` returned `__name__`, and every lambda is named `<lambda>`, so three different
    goals produced one key. "Recall the plan for this goal" was never implemented; only "recall a
    plan for any goal". Fixed to use closure values plus a behavioural probe ladder.

FINDING 3 — learning-to-learn does not work YET, and the benchmark can say so.
    Credit for procedures indexed by a kind-blind feature view was expected to compound. It does
    not: the first feature view collapsed six kinds into one key, and the deepened view still
    puts four of four test kinds in already-trained buckets. The verdict is NO_COMPOUNDING, and
    the benchmark must keep being able to reach that verdict -- a benchmark that cannot fail is
    a demonstration.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import transfer_learning_v1 as tl  # noqa: E402


# ---------------------------------------------------------------- finding 1
def test_more_kinds_does_not_make_the_next_kind_cheaper():
    """The compounding measurement, run for real. Ten kinds, both arms, same instances."""
    from canonical.tools.cross_kind_compounding_benchmark_v1 import run
    doc = run()
    s = doc["summary"]
    assert s["kinds"] == 10
    # The arms must be byte-identical: a saving here would mean the per-kind model started
    # leaking across kinds, which would be a different (and larger) claim than P1's.
    assert s["total_grown_acts"] == s["total_cold_acts"], (
        "meeting prior kinds changed the cost of a new kind: %s" % (s,))
    assert s["kinds_improved_by_more_kinds"] == 0
    assert doc["compounding"].startswith("NO")


def test_grouping_by_goal_identity_does_not_merge_distinct_goals():
    """FINDING 2. Two goals that differ only in a captured value must not share a lesson."""
    target_a, target_b = "abc", "xyz"
    goal_a = (lambda t: (lambda st: st == t))(target_a)
    goal_b = (lambda t: (lambda st: st == t))(target_b)
    goal_a2 = (lambda t: (lambda st: st == t))(target_a)
    assert tl._goal_key(goal_a) != tl._goal_key(goal_b), "distinct goals share a key"
    assert tl._goal_key(goal_a) == tl._goal_key(goal_a2), "the same goal got two keys"


def test_a_named_goal_keeps_its_own_name():
    """The fix must not make named goals unreadable; a caller-chosen name is an identity."""
    def reach_the_top(state):
        return state == "top"

    assert tl._goal_key(reach_the_top) == "reach_the_top"


# ---------------------------------------------------------------- finding 3
def test_the_learning_to_learn_benchmark_can_reach_a_negative_verdict():
    """FINDING 3, and the thing that makes the rest of this file trustworthy.

    If the machinery always said COMPOUNDING_OBSERVED, the positive result would mean nothing.
    It currently says NO, on this machine, with these features -- and that must remain a
    possible output.
    """
    from canonical.tools.cross_kind_learning_to_learn_benchmark_v1 import run as run_l2l
    doc = run_l2l()
    # TEN held-out kinds, not four. The first run was at four and could not distinguish a
    # mechanism that needed data from one that needed a different representation.
    assert doc["summary"]["test_kinds"] == 10
    assert doc["verdict"].split(" --")[0] in {"COMPOUNDING_OBSERVED", "NO_COMPOUNDING"}
    assert doc["policy_vocabulary_is_hand_written"] is True, (
        "the policies are mine, not the system's; the document must say so")


def test_the_measured_answer_is_that_it_does_not_work_yet():
    """The pre-registered experiment, and its actual result, held in place.

    Measured 2026-11-03 on ten held-out kinds: learned solved 5/10, beat the default policy 1/10,
    beat the mean of five random draws 3/10. This test exists so that a future session cannot
    quietly re-tune the features until the number moves, then cite the moved number. If the
    result becomes positive it must be because the MECHANISM changed, and this assertion must be
    updated in the open, with the new benchmark and its random arm.
    """
    from canonical.tools.cross_kind_learning_to_learn_benchmark_v1 import run as run_l2l
    doc = run_l2l()
    s = doc["summary"]
    if doc["verdict"].startswith("NO_COMPOUNDING"):
        assert s["beat_default"] <= 2, s
        assert s["beat_random_mean"] <= 5, s
    else:
        # A positive claim must clear both arms by a real margin before it is believed.
        assert s["beat_default"] >= 8 and s["beat_random_mean"] >= 8, s


def test_the_random_arm_is_part_of_the_measurement():
    """Without a coin-flip baseline, a lucky policy ordering passes for learning."""
    from canonical.tools import cross_kind_learning_to_learn_benchmark_v1 as bench
    src = Path(bench.__file__).read_text(encoding="utf-8")
    assert "beat_random_mean" in src
    doc = bench.run()
    for row in doc["test_rows"]:
        assert len(row["random"]["arms"]) == 5, "the falsifier was sampled once, which proves nothing"


def test_the_held_out_kinds_are_actually_reachable():
    """INSTRUMENT CALIBRATION, pinning a bug that produced a confident false result.

    `stack_pushout` was unsolvable BY CONSTRUCTION (push grew, pop shrank, start and target
    differed by two), and `letter_shift` / `double_dial` raised on every action because of an
    action-parsing typo. Both were then reported as "no policy can solve this kind" -- a fact
    about the terrain that was really a fact about my code. A benchmark whose environments
    cannot be solved measures its own bugs.
    """
    from canonical.tools.cross_kind_learning_to_learn_benchmark_v1 import (
        _heldout_kinds, TEST_KINDS, NODE_BUDGET,
    )
    from canonical.runtime import learn_to_learn_v1 as l2l
    kinds = _heldout_kinds()
    reachable = []
    for name in TEST_KINDS:
        for policy in l2l.POLICIES:
            env, actions, is_goal, _ = kinds[name](1)
            out = l2l.search(env, actions, is_goal=is_goal, policy=policy, max_depth=14,
                             node_budget=NODE_BUDGET, meter={"act_calls": 0})
            if out["pass"]:
                reachable.append(name)
                break
    assert len(reachable) >= 6, (
        "only %d of %d held-out kinds are solvable by any policy; that is an instrument "
        "failure, not a finding: %s" % (len(reachable), len(TEST_KINDS), reachable))
