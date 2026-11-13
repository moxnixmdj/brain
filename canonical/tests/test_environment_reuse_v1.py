"""Reuse is only a win because it is checked.

The numbers in these tests are the measurement that justifies the module:

    cold visit, learning from scratch : 1672 interactions
    warm visit, prior replayed        :   18 interactions  (1.08%)
    drifted world, prior replayed     :   refused at once, stale detected

If the warm path ever stops being validated, the third case is what ships: a confident plan executed
on a world that changed, arriving at (7, 8, 9) while the goal was (7, 2, 9).
"""

from __future__ import annotations

import unittest

from canonical.runtime import environment_learning_v1 as el
from canonical.runtime import environment_reuse_v1 as reuse

GOAL = (7, 2, 9)
ACTIONS = ["+0", "+1", "+2"]


class Lock:
    """Three dials, 1000 states. `drift` makes dial 1 run backwards -- a changed world."""

    def __init__(self, drift: bool = False) -> None:
        self.d = [0, 0, 0]
        self.drift = drift
        self.interactions = 0

    def reset(self) -> None:
        self.d = [0, 0, 0]

    def state(self):
        return tuple(self.d)

    def act(self, action) -> None:
        self.interactions += 1
        index = int(str(action)[1])
        step = -1 if (self.drift and index == 1) else 1
        self.d[index] = (self.d[index] + step) % 10

    def snapshot(self):
        return list(self.d)

    def restore(self, snapshot) -> None:
        self.d = list(snapshot)


def aim(state):
    """The distance heuristic. Supplied by the caller -- this is a hand-written aim, not learning."""
    return sum((target - value) % 10 for target, value in zip(GOAL, state))


def learn_once() -> dict:
    env = Lock()
    result = el.drive(env, ACTIONS, is_goal=lambda s: tuple(s) == GOAL,
                      budget=40, max_depth=24, heuristic=aim, seed=0)
    assert result["pass"], result
    learned = result["learned"]
    return {"model": learned["model"], "observations": learned["observations"],
            "state_key_schema": learned["state_key_schema"], "cold_interactions": env.interactions}


class ReuseTests(unittest.TestCase):
    def test_replay_is_dramatically_cheaper_than_relearning(self):
        prior = learn_once()
        env = Lock()
        result = reuse.replay_then_repair(env, ACTIONS, is_goal=lambda s: tuple(s) == GOAL,
                                          prior=prior,
                                          prior_schema=prior["state_key_schema"],
                                          budget=40, heuristic=aim)
        self.assertEqual(result["status"], reuse.PASS_REPLAYED)
        self.assertTrue(result["pass"])
        self.assertFalse(result["prior_was_stale"])
        self.assertEqual(result["plan_length"], 18, "the minimal plan is 7+2+9 = 18 increments")
        # the measured saving: at least 50x fewer interactions than the cold visit
        self.assertLess(result["interactions"] * 50, prior["cold_interactions"])

    def test_drive_alone_gets_no_saving_from_a_prior(self):
        """The documented reason this module exists: `drive()` re-explores even with a prior.

        This is the honest half of claim D. Carrying a model into `drive()` costs the same as
        starting cold, because exploration happens before planning regardless.
        """
        prior = learn_once()
        env = Lock()
        el.drive(env, ACTIONS, is_goal=lambda s: tuple(s) == GOAL, budget=40, max_depth=24,
                 heuristic=aim, prior=prior["model"],
                 prior_schema=prior["state_key_schema"], seed=0)
        self.assertEqual(env.interactions, prior["cold_interactions"])

    def test_a_stale_prior_is_caught_and_never_silently_trusted(self):
        prior = learn_once()
        drifted = Lock(drift=True)
        result = reuse.replay_then_repair(drifted, ACTIONS, is_goal=lambda s: tuple(s) == GOAL,
                                          prior=prior,
                                          prior_schema=prior["state_key_schema"],
                                          budget=40, heuristic=aim)
        self.assertTrue(result["prior_was_stale"], result)
        self.assertNotEqual(result["status"], reuse.PASS_REPLAYED)
        self.assertFalse(result["pass"] or result["status"] == reuse.PASS_REPLAYED)

    def test_an_unvalidated_replay_would_have_been_wrong(self):
        """Execute the stored plan blind on the drifted world: it lands off goal.

        This is the counterfactual that makes validation load-bearing rather than decorative.
        """
        prior = learn_once()
        start = el.state_key((0, 0, 0))
        goal_keys = {k for k, snap in prior["observations"].items() if tuple(snap) == GOAL}
        plan = el.shortest_plan({"model": prior["model"]}, lambda k: k in goal_keys, start=start)
        self.assertIsNotNone(plan)
        drifted = Lock(drift=True)
        for action in plan:
            drifted.act(action)
        self.assertNotEqual(drifted.state(), GOAL)

    def test_schema_mismatch_is_refused_before_any_interaction(self):
        prior = learn_once()
        env = Lock()
        result = reuse.replay_then_repair(env, ACTIONS, is_goal=lambda s: tuple(s) == GOAL,
                                          prior=prior, prior_schema="SOME_OTHER_SCHEMA",
                                          budget=40, heuristic=aim)
        self.assertEqual(result["status"], reuse.FAIL_NO_PRIOR)
        self.assertEqual(result["interactions"], 0)
        self.assertEqual(env.interactions, 0, "no interaction may happen on a refused prior")

    def test_no_prior_is_refused_not_improvised(self):
        env = Lock()
        result = reuse.replay_then_repair(env, ACTIONS, is_goal=lambda s: tuple(s) == GOAL,
                                          prior=None, prior_schema=None)
        self.assertEqual(result["status"], reuse.FAIL_NO_PRIOR)
        self.assertEqual(env.interactions, 0)

    def test_every_outcome_is_a_distinct_status(self):
        statuses = {reuse.PASS_REPLAYED, reuse.REPAIRED, reuse.FAIL_REPAIR, reuse.FAIL_NO_PRIOR}
        self.assertEqual(len(statuses), 4, "a reused, a repaired, and two refusals must stay apart")


if __name__ == "__main__":
    unittest.main()
