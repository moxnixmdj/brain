"""The chase may only stop on a measurement, never on a belief.

Every case here is about the stop rule, because that is the only thing this
driver adds. A chase that reports success it has not measured is worse than no
chase at all: it would happily stop at $100 and call $1,000,000 reached.

Oracles are deliberately trivial and in-memory. What is under test is the
contract, not the arithmetic.
"""
from __future__ import annotations

import unittest

from execution_guard import target_chase_driver_v1 as chase


class _Counter:
    """A value only `bump` can move, that anyone can read."""

    def __init__(self, start: float = 0.0) -> None:
        self.value = start

    def measure(self) -> float:
        return self.value

    def bump(self, by: float):
        def act(ctx):
            self.value += by
            return {"status": "MOVED"}
        return act

    def stall(self):
        def act(ctx):
            return {"status": "THOUGHT_ABOUT_IT"}
        return act


class TargetChaseStopRule(unittest.TestCase):
    def test_arrives_and_stops_on_the_measurement(self):
        c = _Counter()
        r = chase.run(
            goal="reach 1,000,000", target=1_000_000, direction="maximize", unit="USD",
            measure=c.measure, act=c.bump(250_000), max_rounds=10, patience=2,
        )
        self.assertEqual(r["status"], chase.MET)
        self.assertIs(r["pass"], True)
        self.assertEqual(r["best_measurement"], 1_000_000)
        self.assertEqual(r["remaining_gap"], 0)
        self.assertIs(r["goal_reached"], True)
        self.assertEqual(r["round_count"], 4)

    def test_stopping_short_is_never_success(self):
        """The $100 case. It must say it did not arrive."""
        c = _Counter()
        r = chase.run(
            goal="Make me a million dollars", target=1_000_000,
            direction="maximize", unit="USD",
            measure=c.measure, act=c.bump(100), max_rounds=4, patience=2,
        )
        self.assertIs(r["pass"], False)
        self.assertIs(r["goal_reached"], False)
        self.assertEqual(r["best_measurement"], 400)
        self.assertEqual(r["remaining_gap"], 999_600)
        self.assertEqual(r["status"], chase.BOUND)

    def test_no_measured_progress_is_reported_as_failure(self):
        c = _Counter(start=7.0)
        r = chase.run(
            goal="reach 100", target=100, direction="maximize",
            measure=c.measure, act=c.stall(), max_rounds=10, patience=2,
        )
        self.assertEqual(r["status"], chase.STUCK)
        self.assertIs(r["pass"], False)
        self.assertEqual(r["best_measurement"], 7.0)
        self.assertEqual(r["round_count"], 2, "must stop at the patience bound")

    def test_minimize_direction(self):
        c = _Counter(start=5.0)
        r = chase.run(
            goal="zero defects", target=0, direction="minimize", unit="defects",
            measure=c.measure, act=c.bump(-1.0), max_rounds=10, patience=3,
        )
        self.assertEqual(r["status"], chase.MET)
        self.assertEqual(r["best_measurement"], 0)
        self.assertIs(r["pass"], True)

    def test_already_on_target_acts_zero_times(self):
        c = _Counter(start=1_000_000)
        r = chase.run(
            goal="already there", target=1_000_000,
            measure=c.measure, act=c.bump(1), max_rounds=5,
        )
        self.assertEqual(r["status"], chase.MET)
        self.assertEqual(r["round_count"], 0)

    def test_the_actor_may_not_grade_itself(self):
        c = _Counter()
        with self.assertRaises(chase.TargetChaseError) as ctx:
            chase.run(goal="x", target=1, measure=c.measure, act=c.measure)
        self.assertIn("ACTOR_CANNOT_GRADE_ITSELF", str(ctx.exception))

    def test_an_unmeasurable_target_fails_closed(self):
        r = chase.run(
            goal="x", target=1, measure=lambda: None,
            act=_Counter().stall(), max_rounds=5,
        )
        self.assertEqual(r["status"], chase.NOT_MEASURABLE)
        self.assertIs(r["pass"], False)

    def test_bad_contract_arguments_are_refused(self):
        c = _Counter()
        with self.assertRaises(chase.TargetChaseError):
            chase.run(goal="x", target=1, measure=c.measure, act=c.stall(), direction="sideways")
        with self.assertRaises(chase.TargetChaseError):
            chase.run(goal="x", target="1M", measure=c.measure, act=c.stall())
        with self.assertRaises(chase.TargetChaseError):
            chase.run(goal="x", target=1, measure=c.measure, act=c.stall(), patience=0)

    def test_chase_claims_no_authority(self):
        c = _Counter()
        r = chase.run(goal="x", target=1, measure=c.measure, act=c.bump(1), max_rounds=2)
        self.assertIs(r["execution_authority"], False)
        self.assertIs(r["terminal_authority"], False)
        self.assertEqual(r["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main()
