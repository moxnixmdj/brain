import unittest

from canonical.runtime.finite_population_proof import (
    exact_lower_success_count,
    evaluate_binary_population,
    minimum_sample_size_for_all_successes,
)


class FinitePopulationProofTests(unittest.TestCase):
    def test_full_census_is_exact(self):
        self.assertEqual(exact_lower_success_count(100, 100, 73, 0.05), 73)

    def test_zero_success_lower_bound_zero(self):
        self.assertEqual(exact_lower_success_count(100, 20, 0, 0.05), 0)

    def test_all_success_sample_can_clear_moderate_bar(self):
        out = evaluate_binary_population(
            population_size=100,
            sample_size=20,
            sample_successes=20,
            threshold_rate=0.70,
            alpha=0.05,
        )
        self.assertTrue(out["pass_lower_bound"])
        self.assertGreaterEqual(out["lower_rate"], 0.70)

    def test_same_sample_does_not_clear_extreme_bar(self):
        out = evaluate_binary_population(
            population_size=100,
            sample_size=5,
            sample_successes=5,
            threshold_rate=0.95,
            alpha=0.05,
        )
        self.assertFalse(out["pass_lower_bound"])

    def test_monotonic_in_successes(self):
        lows = [exact_lower_success_count(80, 20, x, 0.05) for x in range(21)]
        self.assertEqual(lows, sorted(lows))

    def test_minimum_sample_size_exists(self):
        n = minimum_sample_size_for_all_successes(
            population_size=100, threshold_rate=0.80, alpha=0.05
        )
        self.assertIsInstance(n, int)
        self.assertGreater(n, 0)
        self.assertLessEqual(n, 100)

    def test_invalid_parameters_fail_closed(self):
        with self.assertRaises(ValueError):
            exact_lower_success_count(10, 11, 5)
        with self.assertRaises(ValueError):
            evaluate_binary_population(
                population_size=10,
                sample_size=5,
                sample_successes=6,
                threshold_rate=0.5,
            )


if __name__ == "__main__":
    unittest.main()
