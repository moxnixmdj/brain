"""Does one demonstration buy the rule, or only a rule?

WHY THIS EXISTS
---------------
The claim under test is the owner's: "show it once, it learns permanently, therefore it can do
anything on a computer." Every clause is true except that one demonstration determines *which*
rule was learned. These tests pin down what one example buys and what permanence does to the
answer.

The decisive test is `test_one_demonstration_leaves_two_live_rules`: if a single example left only
one possible rule, instant learning would be truth-preserving and there would be nothing to argue
about. It leaves two, and the simpler of the two is the wrong one.
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import permanence_amplifies_check_v1 as P  # noqa: E402


class OneDemonstrationTests(unittest.TestCase):
    def setUp(self):
        self.demo = [P.Record(qty=6, price=7, total=42)]      # 6 * 7 == 42, and also == 42
        self.second = [P.Record(qty=9, price=9, total=81)]   # only recompute survives this one
        self.board = P.records()

    # ------------------------------------------------------- the decisive test

    def test_one_demonstration_leaves_two_live_rules(self):
        live = P.live_hypotheses(self.demo)
        self.assertEqual([s.name for s in live],
                         ["copy_the_total_it_was_shown", "recompute_from_the_rows"])
        # Both reproduce the demonstration exactly. Nothing in it distinguishes them.
        for skill in live:
            self.assertEqual(skill.apply(self.demo[0]), 42)

    def test_it_registers_the_simpler_rule_and_the_simpler_rule_is_wrong(self):
        skill = P.learn(self.demo)
        self.assertEqual(skill.name, "copy_the_total_it_was_shown")
        result = P.evaluate(skill, self.board, P.strong_check)
        self.assertEqual(result["actually_correct"], 1)   # only the record that happens to total 42
        self.assertLess(result["correct_rate"], 0.1)

    def test_a_weak_check_accepts_every_record_the_wrong_skill_produces(self):
        result = P.evaluate(P.learn(self.demo), self.board, P.weak_check)
        self.assertEqual(result["accepted_by_the_check"], result["records"])
        self.assertEqual(result["acceptance_rate"], 1.0)

    def test_the_strong_check_would_have_caught_it(self):
        result = P.evaluate(P.learn(self.demo), self.board, P.strong_check)
        self.assertLessEqual(result["accepted_by_the_check"], 1)

    # ---------------------------------------------------------- what fixes it

    def test_a_second_different_demonstration_kills_the_wrong_rule(self):
        live = P.live_hypotheses(self.demo + self.second)
        self.assertEqual([s.name for s in live], ["recompute_from_the_rows"])
        skill = P.learn(self.demo + self.second)
        self.assertEqual(P.evaluate(skill, self.board, P.strong_check)["actually_correct"],
                         len(self.board))

    def test_a_second_identical_demonstration_fixes_nothing(self):
        """The held-out rule the onboarding factory enforces, seen from the other side: a
        demonstration that repeats the first one adds no information and the wrong rule survives."""
        same_again = [P.Record(qty=6, price=7, total=42)]
        live = P.live_hypotheses(self.demo + same_again)
        self.assertEqual(len(live), 2)
        self.assertEqual(P.learn(self.demo + same_again).name, "copy_the_total_it_was_shown")

    # ------------------------------------------------------------ permanence

    def test_permanence_does_not_decay_the_error(self):
        skill = P.learn(self.demo)
        row = P.permanence(skill, self.board[:5], recalls=200)
        self.assertEqual(row["drift"], 0)
        self.assertEqual(row["accepted"], 200 * 5)   # every single recall, accepted
        self.assertEqual(row["skill_unchanged"], skill.name)

    def test_repetition_never_repairs_a_wrong_rule(self):
        """Doing it a thousand more times teaches it nothing new: the same rule produces the same
        wrong number, and only a check that recomputes can notice."""
        skill = P.learn(self.demo)
        first = [skill.apply(r) for r in self.board]
        for _ in range(1000):
            again = [skill.apply(r) for r in self.board]
        self.assertEqual(first, again)

    # ------------------------------------------------------------- refusals

    def test_nothing_shown_learns_nothing(self):
        """Vacuous truth would otherwise 'confirm' every rule from zero evidence."""
        self.assertEqual(P.live_hypotheses([]), [])
        self.assertIsNone(P.learn([]))

    def test_demonstrations_that_contradict_every_rule_register_nothing(self):
        contradictory = [P.Record(qty=6, price=7, total=42), P.Record(qty=9, price=9, total=100)]
        self.assertEqual(P.live_hypotheses(contradictory), [])
        self.assertIsNone(P.learn(contradictory))

    def test_the_headline_numbers(self):
        row = P.measure()
        one = row["one_demonstration"]
        two = row["two_demonstrations"]
        self.assertEqual(len(one["live_rules_consistent_with_it"]), 2)
        self.assertEqual(len(two["live_rules_consistent_with_them"]), 1)
        self.assertEqual(one["under_weak_check"]["acceptance_rate"], 1.0)
        self.assertLess(one["under_strong_check"]["acceptance_rate"], 0.1)
        self.assertEqual(two["under_strong_check"]["acceptance_rate"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
