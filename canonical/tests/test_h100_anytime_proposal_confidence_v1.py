from __future__ import annotations

import math
import unittest

from canonical.runtime.h100_anytime_proposal_confidence_v1 import (
    ALPHA,
    AnytimeProposalError,
    lower_bound,
    upper_bound,
    sequence,
)


class H100AnytimeProposalConfidenceTests(unittest.TestCase):
    def test_spending_is_summable(self):
        total = sum((ALPHA / 2.0) / (t * (t + 1)) for t in range(1, 200000))
        self.assertAlmostEqual(total, ALPHA / 2.0, places=6)

    def test_bounds_contain_mle(self):
        for n in (1, 2, 5, 10, 30):
            for s in range(n + 1):
                lo = lower_bound(s, n)
                hi = upper_bound(s, n)
                self.assertLessEqual(lo, s / n)
                self.assertGreaterEqual(hi, s / n)
                self.assertGreaterEqual(lo, 0.0)
                self.assertLessEqual(hi, 1.0)

    def test_all_success_lower_is_exact_spent_alpha_root(self):
        n = 7
        a = (ALPHA / 2.0) / (n * (n + 1))
        self.assertAlmostEqual(lower_bound(n, n), a ** (1.0 / n), places=12)

    def test_all_failure_upper_is_exact(self):
        n = 7
        a = (ALPHA / 2.0) / (n * (n + 1))
        self.assertAlmostEqual(upper_bound(0, n), 1.0 - a ** (1.0 / n), places=12)

    def test_repeated_success_eventually_declares_viable(self):
        out = sequence([True] * 100, viability_p=0.2)
        self.assertEqual(out["status"], "VIABLE")
        self.assertIsNotNone(out["stopping_time"])
        self.assertGreaterEqual(out["p_lower_anytime"], 0.2)

    def test_repeated_failure_eventually_declares_futility(self):
        out = sequence([False] * 100, viability_p=0.2)
        self.assertEqual(out["status"], "FUTILITY")
        self.assertIsNotNone(out["stopping_time"])
        self.assertLess(out["p_upper_anytime"], 0.2)

    def test_decision_is_first_crossing_and_not_rewritten(self):
        out = sequence([True] * 40 + [False] * 40, viability_p=0.1)
        self.assertEqual(out["status"], "VIABLE")
        t = out["stopping_time"]
        self.assertIsNotNone(t)
        crossings = [r for r in out["trace"] if r["decision_if_first_crossing"] != "NONE"]
        self.assertEqual(len(crossings), 1)
        self.assertEqual(crossings[0]["t"], t)

    def test_bad_outcome_fails_closed(self):
        with self.assertRaisesRegex(AnytimeProposalError, "OUTCOME_NOT_BOOL:2"):
            sequence([True, 1], viability_p=0.2)

    def test_bad_viability_threshold_fails_closed(self):
        with self.assertRaisesRegex(AnytimeProposalError, "VIABILITY_P_INVALID"):
            sequence([True], viability_p=0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
