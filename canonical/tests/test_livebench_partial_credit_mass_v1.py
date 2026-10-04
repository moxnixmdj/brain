import math
import unittest

from canonical.runtime.livebench_partial_credit_mass_v1 import (
    CaseBound,
    aggregate_certificate,
    case_lower_bound,
)


class LiveBenchPartialCreditMassTests(unittest.TestCase):
    def test_partial_credit_formula(self):
        self.assertTrue(math.isclose(case_lower_bound(3, 1), 1.0 / 6.0))
        self.assertTrue(math.isclose(case_lower_bound(4, 2), 0.25))

    def test_all_followed_gets_full_case_score(self):
        self.assertEqual(case_lower_bound(3, 3, True), 1.0)

    def test_without_all_followed_proof_full_instruction_fraction_only_yields_half(self):
        self.assertEqual(case_lower_bound(2, 2, False), 0.5)

    def test_threshold_mass_matches_frozen_target(self):
        rows = [CaseBound(1, 1, True) for _ in range(132)]
        cert = aggregate_certificate(rows)
        self.assertTrue(cert["forced_pass"])
        self.assertEqual(cert["threshold_mass"], 131.4)

    def test_131_full_cases_do_not_force_pass(self):
        rows = [CaseBound(1, 1, True) for _ in range(131)]
        cert = aggregate_certificate(rows)
        self.assertFalse(cert["forced_pass"])
        self.assertTrue(math.isclose(cert["residual_mass_to_force_pass"], 0.4))

    def test_partial_mass_can_cross_threshold_without_universal_coverage(self):
        rows = [CaseBound(1, 1, True) for _ in range(130)]
        rows += [CaseBound(2, 1, False) for _ in range(6)]
        cert = aggregate_certificate(rows)
        self.assertTrue(cert["forced_pass"])
        self.assertTrue(cert["unresolved_case_count"] > 0)

    def test_lower_bound_zero_does_not_prove_case_score_zero(self):
        rows = [CaseBound(1, 0, False) for _ in range(72)]
        cert = aggregate_certificate(rows)
        self.assertFalse(cert["forced_fail"])
        self.assertEqual(cert["full_population_score_mass_upper_bound"], 200.0)

    def test_forced_fail_requires_explicit_upper_bound_evidence(self):
        rows = [CaseBound(1, 0, False, proved_score_upper_bound=0.0) for _ in range(72)]
        cert = aggregate_certificate(rows)
        self.assertTrue(cert["forced_fail"])
        self.assertEqual(cert["full_population_score_mass_upper_bound"], 128.0)

    def test_upper_bound_cannot_be_below_proved_lower_bound(self):
        with self.assertRaises(ValueError):
            CaseBound(2, 1, False, proved_score_upper_bound=0.1).upper_bound()

    def test_threshold_out_of_range_fails_closed(self):
        with self.assertRaises(ValueError):
            aggregate_certificate([], threshold_percent=100.1)


if __name__ == "__main__":
    unittest.main()
