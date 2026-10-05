import unittest
from fractions import Fraction

from canonical.runtime.hidden_evaluator_dominance_boundary_v1 import (
    distinguishing_hidden_utility,
    hidden_evaluator_universal_noninferiority,
)


class HiddenEvaluatorDominanceBoundaryTests(unittest.TestCase):
    def test_identical_distribution_universally_noninferior(self):
        p = {"a": "1/3", "b": "2/3"}
        self.assertTrue(hidden_evaluator_universal_noninferiority(p, p))
        self.assertIsNone(distinguishing_hidden_utility(p, p))

    def test_any_mass_shift_has_indicator_counterexample(self):
        target = {"a": "1/2", "b": "1/2"}
        brain = {"a": "3/4", "b": "1/4"}
        self.assertFalse(hidden_evaluator_universal_noninferiority(target, brain))
        self.assertEqual(distinguishing_hidden_utility(target, brain), "b")

    def test_new_output_mass_still_forces_loss_elsewhere(self):
        target = {"a": 1}
        brain = {"a": "3/4", "c": "1/4"}
        self.assertFalse(hidden_evaluator_universal_noninferiority(target, brain))
        self.assertEqual(distinguishing_hidden_utility(target, brain), "a")

    def test_zero_probability_keys_do_not_change_equality(self):
        target = {"a": 1, "b": 0}
        brain = {"a": 1}
        self.assertTrue(hidden_evaluator_universal_noninferiority(target, brain))

    def test_invalid_distribution_fails_closed(self):
        with self.assertRaises(ValueError):
            hidden_evaluator_universal_noninferiority(
                {"a": Fraction(1, 2)}, {"a": 1}
            )

    def test_float_probabilities_rejected(self):
        with self.assertRaises(TypeError):
            hidden_evaluator_universal_noninferiority(
                {"a": 0.5, "b": 0.5}, {"a": "1/2", "b": "1/2"}
            )


if __name__ == "__main__":
    unittest.main()
