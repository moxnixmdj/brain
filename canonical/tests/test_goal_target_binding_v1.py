"""Binding a sentence to a number, and the refusals that keep it honest.

The dangerous failure here is not a missed target, it is an INVENTED one: a
guessed number would let the chase later declare MET against a target the owner
never set. So the refusal cases matter as much as the binding cases, and every
inference must be labelled as one.
"""
from __future__ import annotations

import unittest

from execution_guard import goal_target_binding_v1 as bind_mod


class GoalTargetBinding(unittest.TestCase):
    # ---------------------------------------------------------------- binds
    def test_explicit_operator_is_bound_and_marked_explicit(self):
        r = bind_mod.bind("Earn at least 1000000 USD")
        self.assertIs(r["pass"], True)
        self.assertEqual(r["target"], 1_000_000.0)
        self.assertEqual(r["direction"], bind_mod.MAXIMIZE)
        self.assertEqual(r["unit"], "USD")
        self.assertEqual(r["relation"], "MIN_INCLUSIVE")
        self.assertEqual(r["relation_source"], "EXPLICIT_OPERATOR")

    def test_at_most_is_a_ceiling(self):
        r = bind_mod.bind("Keep costs at most 250.75 dollars")
        self.assertEqual(r["direction"], bind_mod.MINIMIZE)
        self.assertEqual(r["target"], 250.75)
        self.assertEqual(r["relation_source"], "EXPLICIT_OPERATOR")

    def test_decimals_survive(self):
        r = bind_mod.bind("Reach no less than 1000000.50 USD")
        self.assertEqual(r["target"], 1_000_000.5)

    def test_number_words_are_normalized_then_extracted(self):
        self.assertEqual(
            bind_mod.normalize_number_words("Make me a million dollars"),
            "Make me 1000000 dollars",
        )
        r = bind_mod.bind("Make me a million dollars")
        self.assertEqual(r["target"], 1_000_000.0)
        self.assertEqual(r["unit"], "USD")
        self.assertEqual(r["normalized_goal"], "Make me 1000000 dollars")

    def test_scaled_suffix(self):
        self.assertEqual(bind_mod.bind("Make me $1M")["target"], 1_000_000.0)
        self.assertEqual(bind_mod.bind("Reach 10k followers")["target"], 10_000.0)

    def test_fractional_scale(self):
        r = bind_mod.bind("Get 2.5 million users")
        self.assertEqual(r["target"], 2_500_000.0)
        self.assertEqual(r["unit"], "users")

    def test_inference_is_labelled_as_inference(self):
        """A bare quantity has no relation. It may be inferred, never presented
        as something the extractor actually found."""
        r = bind_mod.bind("Make me a million dollars")
        self.assertEqual(r["relation_source"], "INFERRED_FROM_VERB__NOT_AN_EXTRACTION")
        self.assertIn("warning", r["evidence"])

    # -------------------------------------------------------------- refusals
    def test_a_goal_with_no_number_is_refused(self):
        for goal in ("Make me rich", "Write a report", "Be successful"):
            r = bind_mod.bind(goal)
            self.assertIs(r["pass"], False, goal)
            self.assertEqual(r["status"], bind_mod.NO_TARGET)
            self.assertNotIn("target", r)

    def test_several_undifferentiated_numbers_are_refused(self):
        r = bind_mod.bind("Buy 3 apples and 4 oranges")
        self.assertIs(r["pass"], False)

    def test_both_directions_present_is_refused(self):
        r = bind_mod.bind("Make 1 million but keep costs at 5 dollars")
        self.assertIs(r["pass"], False)

    def test_empty_goal_is_refused(self):
        self.assertIs(bind_mod.bind("").get("pass"), False)
        self.assertIs(bind_mod.bind("   ").get("pass"), False)

    # ------------------------------------------------------------- contract
    def test_binding_claims_no_authority(self):
        r = bind_mod.bind("Earn at least 5 USD")
        self.assertIs(r["terminal_authority"], False)
        self.assertEqual(r["terminal_credit_delta"], 0)

    def test_normalization_does_not_disturb_plain_digits(self):
        self.assertEqual(
            bind_mod.normalize_number_words("at least 1000000.50 USD"),
            "at least 1000000.50 USD",
        )


class BindThenChase(unittest.TestCase):
    """The two pieces compose, and an unreachable target still reports a gap."""

    def test_bound_target_drives_a_chase_that_reports_its_shortfall(self):
        from execution_guard import target_chase_driver_v1 as chase

        bound = bind_mod.bind("Make me a million dollars")
        self.assertIs(bound["pass"], True)

        pot = [0.0]

        def measure():
            return pot[0]

        def act(_ctx):
            pot[0] += 100.0
            return {"status": "EARNED_100"}

        r = chase.run(
            goal=bound["goal"],
            target=bound["target"],
            direction=bound["direction"],
            unit=bound["unit"],
            measure=measure,
            act=act,
            max_rounds=4,
            patience=2,
        )
        # The whole point: it stops short and says so, rather than declaring MET.
        self.assertIs(r["pass"], False)
        self.assertIs(r["goal_reached"], False)
        self.assertEqual(r["best_measurement"], 400.0)
        self.assertEqual(r["remaining_gap"], 999_600.0)


if __name__ == "__main__":
    unittest.main()
