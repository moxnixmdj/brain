from __future__ import annotations

import unittest
from fractions import Fraction

from canonical.runtime.w4_superdomain_dominance_obstruction_v1 import (
    ObstructionError,
    binary_counterwitness,
    verify_binary_universal_obstruction,
)


class W4SuperdomainDominanceObstructionTests(unittest.TestCase):
    def test_deterministic_y1_brain_is_beaten_by_y0_counterpolicy(self):
        out = binary_counterwitness(Fraction(1, 1))
        self.assertEqual(out["y_star"], "y0")
        self.assertEqual(out["brain_expected_score"], "0")
        self.assertTrue(out["strictly_better"])

    def test_deterministic_y0_brain_is_beaten_by_y1_counterpolicy(self):
        out = binary_counterwitness(Fraction(0, 1))
        self.assertEqual(out["y_star"], "y1")
        self.assertEqual(out["brain_expected_score"], "0")
        self.assertTrue(out["strictly_better"])

    def test_stochastic_brain_is_strictly_beaten(self):
        out = binary_counterwitness(Fraction(999, 1000))
        self.assertEqual(out["y_star"], "y1")
        self.assertEqual(out["brain_expected_score"], "999/1000")
        self.assertTrue(out["strictly_better"])

    def test_invalid_probability_fails_closed(self):
        with self.assertRaises(ObstructionError):
            binary_counterwitness(Fraction(1001, 1000))
        with self.assertRaises(ObstructionError):
            binary_counterwitness(Fraction(-1, 1000))

    def test_universal_algebraic_split_passes(self):
        out = verify_binary_universal_obstruction()
        self.assertEqual(out["status"], "PASS")
        self.assertFalse(out["unrestricted_superdomain_dominance_possible"])
        self.assertTrue(out["requires_target_evaluator_restriction_to_reopen"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["fresh_reality_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
