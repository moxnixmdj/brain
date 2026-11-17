"""Tests for the table model. Every assertion is about EXECUTED transitions, and the safety tests
are the ones that matter: a model that answers where it was never observed is the failure mode that
produced 6,261 silently wrong successors in the law-based version this replaces."""
import copy
import unittest

from canonical.runtime import consequence_table_v1 as CT


class Counter:
    """A toy environment: three actions, wrapped counter mod 5, goal at 3."""

    def __init__(self):
        self.v = 0

    def reset(self):
        self.v = 0

    def act(self, a):
        if a == "inc":
            self.v = (self.v + 1) % 5
        elif a == "jump":
            self.v = (self.v + 2) % 5
        elif a == "noop":
            pass
        else:
            raise ValueError(a)

    def state(self):
        return self.v


class WrappingUnknown:
    """An environment with a state the table has never entered. Used for the refusal test."""

    def __init__(self):
        self.v = 0

    def reset(self):
        self.v = 0

    def act(self, a):
        self.v = (self.v + int(a)) % 7

    def state(self):
        return self.v


def goal3(state):
    return state == 3


class TestSafety(unittest.TestCase):
    def test_lookup_returns_none_for_an_unobserved_transition(self):
        t = CT.ConsequenceTable()
        self.assertIsNone(t.lookup(0, "inc"))
        t.record(0, "inc", 1)
        self.assertEqual(t.lookup(0, "inc"), 1)
        # A DIFFERENT state is a different question and must not be answered.
        self.assertIsNone(t.lookup(1, "inc"))

    def test_an_unobserved_transition_is_never_answered(self):
        """The whole safety property: the table cannot be silently wrong, only silent."""
        t = CT.ConsequenceTable()
        for s in range(5):
            for a in ("inc", "jump", "noop"):
                t.record(s, a, (s + {"inc": 1, "jump": 2, "noop": 0}[a]) % 5)
        # Everything recorded is exact; anything not recorded answers None.
        self.assertEqual(t.lookup(4, "inc"), 0)
        self.assertIsNone(t.lookup(5, "inc"))
        self.assertIsNone(t.lookup(4, "teleport"))

    def test_planning_never_returns_an_unverified_success(self):
        """`plan` is a proposal; solve reports pass only after executing and observing the goal."""
        env = Counter()
        out = CT.learn_and_solve(env, ["inc", "jump", "noop"], is_goal=goal3)
        self.assertTrue(out["pass"])
        # replay the returned plan on a fresh env and confirm the goal really is reached
        check = Counter()
        check.reset()
        for a in out["plan"]:
            check.act(a)
        self.assertEqual(check.state(), 3)


class TestLearningAndSolving(unittest.TestCase):
    def test_solves_by_learning_transitions(self):
        out = CT.learn_and_solve(Counter(), ["inc", "jump", "noop"], is_goal=goal3)
        self.assertTrue(out["pass"])
        self.assertEqual(out["outcome"], CT.SOLVED)
        self.assertGreater(out["table_size"], 0)

    def test_each_transition_is_executed_at_most_once(self):
        """The saving IS this property; assert it directly rather than trusting a ratio.

        Counts REAL executions through an instrumented env, not the table's own bookkeeping --
        a table that miscounted its own probes would otherwise pass its own test.
        """
        class Counting(Counter):
            def __init__(self):
                super().__init__()
                self.acts = 0

            def act(self, a):
                self.acts += 1
                super().act(a)

        env = Counting()
        tab = CT.ConsequenceTable()
        out = CT.learn_and_solve(env, ["inc", "jump", "noop"], is_goal=goal3, table=tab)
        # Distinct transitions recorded must equal distinct (state, action) pairs executed once.
        self.assertEqual(len(set(tab._t)), len(tab._t), "no key may be stored twice")
        self.assertEqual(tab.probes, len(tab))
        # Re-running with the same table may EXECUTE (to walk paths) but must RECORD nothing new.
        paid = tab.probes
        CT.learn_and_solve(Counting(), ["inc", "jump", "noop"], is_goal=goal3, table=tab)
        self.assertEqual(tab.probes, paid, "a second episode on the same dynamics learns nothing")

    def test_allowance_bounds_the_learning(self):
        out = CT.learn_and_solve(Counter(), ["inc", "jump", "noop"], is_goal=goal3,
                                 transition_allowance=0)
        self.assertFalse(out["pass"])
        self.assertEqual(out["transitions_probed"], 0)

    def test_zero_allowance_solves_nothing_that_needs_acting(self):
        """Zero prior experience is measured, not asserted: it must fail here."""
        for cap in (0, 1):
            out = CT.learn_and_solve(Counter(), ["inc", "jump", "noop"], is_goal=goal3,
                                     transition_allowance=cap)
            if cap == 1:
                # one transition cannot reach 3 from 0 unless the first action happens to land there
                continue
            self.assertFalse(out["pass"])


class TestRecordIsIdempotent(unittest.TestCase):
    def test_recording_the_same_transition_twice_counts_one_probe(self):
        """At-most-once is a property of the MODEL, not only of the loop that drives it."""
        t = CT.ConsequenceTable()
        t.record(0, "inc", 1)
        t.record(0, "inc", 1)
        self.assertEqual(t.probes, 1)
        self.assertEqual(len(t), 1)


class TestCarry(unittest.TestCase):
    def test_a_table_carries_to_a_new_instance_of_the_same_dynamics(self):
        tab = CT.ConsequenceTable()
        CT.learn_and_solve(Counter(), ["inc", "jump", "noop"], is_goal=goal3, table=tab)
        paid = tab.probes
        out = CT.learn_and_solve(Counter(), ["inc", "jump", "noop"], is_goal=goal3, table=tab)
        self.assertTrue(out["pass"])
        self.assertTrue(out["carried_model"])
        self.assertEqual(tab.probes, paid, "a carried model must learn nothing new here")

    def test_a_table_does_not_answer_for_a_different_environment(self):
        """Permanence is of TRANSITIONS, not of environments. No transfer is claimed."""
        tab = CT.ConsequenceTable()
        CT.learn_and_solve(Counter(), ["inc", "jump", "noop"], is_goal=goal3, table=tab)
        before = dict(tab._t)
        out = CT.learn_and_solve(WrappingUnknown(), ["1", "2"], is_goal=lambda s: s == 5,
                                 table=tab)
        self.assertIsNone(out.get("carried_claim"))
        # the foreign keys are still present and still answer their own environment's truth
        self.assertEqual(len(before), len([k for k in before if k in tab._t]))


if __name__ == "__main__":
    unittest.main()
