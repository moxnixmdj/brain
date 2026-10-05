import unittest
from fractions import Fraction

from canonical.runtime.exact_information_gain import (
    compare_information_gain,
    comparison_certificate,
    information_gain_log_terms,
    rank_tests_by_information_gain,
)


class ExactInformationGainTests(unittest.TestCase):
    def test_perfect_observation_strictly_beats_uninformative_test(self):
        prior = {"h0": Fraction(1, 2), "h1": Fraction(1, 2)}
        perfect = {"h0": {"x": 1, "y": 0}, "h1": {"x": 0, "y": 1}}
        useless = {
            "h0": {"x": Fraction(1, 2), "y": Fraction(1, 2)},
            "h1": {"x": Fraction(1, 2), "y": Fraction(1, 2)},
        }
        self.assertEqual(compare_information_gain(prior, perfect, useless), 1)
        cert = comparison_certificate(prior, perfect, useless)
        self.assertEqual(cert["relation"], "GT")
        self.assertGreater(
            cert["rational_ratio_numerator"], cert["rational_ratio_denominator"]
        )

    def test_observation_label_permutation_is_exact_tie(self):
        prior = {"a": "1/3", "b": "2/3"}
        test_a = {
            "a": {"yes": "3/4", "no": "1/4"},
            "b": {"yes": "1/4", "no": "3/4"},
        }
        test_b = {
            "a": {"left": "3/4", "right": "1/4"},
            "b": {"left": "1/4", "right": "3/4"},
        }
        self.assertEqual(compare_information_gain(prior, test_a, test_b), 0)
        self.assertEqual(comparison_certificate(prior, test_a, test_b)["relation"], "EQ")

    def test_deterministic_prior_makes_all_tests_tie_at_zero_information_gain(self):
        prior = {"certain": 1, "impossible": 0}
        a = {"certain": {"x": 1}, "impossible": {"x": 0, "y": 1}}
        b = {"certain": {"z": 1}, "impossible": {"z": 1}}
        self.assertEqual(information_gain_log_terms(prior, a), {})
        self.assertEqual(information_gain_log_terms(prior, b), {})
        self.assertEqual(compare_information_gain(prior, a, b), 0)

    def test_noisier_binary_channel_loses_to_cleaner_binary_channel(self):
        prior = {"h0": "1/2", "h1": "1/2"}
        clean = {
            "h0": {"0": "9/10", "1": "1/10"},
            "h1": {"0": "1/10", "1": "9/10"},
        }
        noisy = {
            "h0": {"0": "3/4", "1": "1/4"},
            "h1": {"0": "1/4", "1": "3/4"},
        }
        self.assertEqual(compare_information_gain(prior, clean, noisy), 1)

    def test_rank_tests_is_exact_and_descending(self):
        prior = {"h0": "1/2", "h1": "1/2"}
        perfect = {"h0": {"0": 1, "1": 0}, "h1": {"0": 0, "1": 1}}
        clean = {
            "h0": {"0": "9/10", "1": "1/10"},
            "h1": {"0": "1/10", "1": "9/10"},
        }
        useless = {
            "h0": {"0": "1/2", "1": "1/2"},
            "h1": {"0": "1/2", "1": "1/2"},
        }
        self.assertEqual(
            rank_tests_by_information_gain(
                prior, {"useless": useless, "clean": clean, "perfect": perfect}
            ),
            ["perfect", "clean", "useless"],
        )

    def test_binary_symmetric_channels_order_monotonically_to_half_noise(self):
        prior = {"h0": "1/2", "h1": "1/2"}

        def channel(error):
            e = Fraction(error)
            return {
                "h0": {"0": 1 - e, "1": e},
                "h1": {"0": e, "1": 1 - e},
            }

        tests = {
            "perfect": channel(Fraction(0, 1)),
            "quarter_noise": channel(Fraction(1, 4)),
            "half_noise": channel(Fraction(1, 2)),
        }
        self.assertEqual(
            rank_tests_by_information_gain(prior, tests),
            ["perfect", "quarter_noise", "half_noise"],
        )

    def test_float_probabilities_are_rejected_to_preserve_exactness(self):
        prior = {"h0": 0.5, "h1": 0.5}
        test = {"h0": {"x": 1}, "h1": {"x": 1}}
        with self.assertRaises(TypeError):
            information_gain_log_terms(prior, test)

    def test_invalid_exact_probability_models_fail_closed(self):
        cases = [
            (
                {"h0": "1/3", "h1": "1/3"},
                {"h0": {"x": 1}, "h1": {"x": 1}},
            ),
            (
                {"h0": "1/2", "h1": "1/2"},
                {"h0": {"x": "2/3"}, "h1": {"x": 1}},
            ),
            (
                {"h0": "1/2", "h1": "1/2"},
                {"h0": {"x": 1}},
            ),
        ]
        for prior, test in cases:
            with self.subTest(prior=prior, test=test):
                with self.assertRaises(ValueError):
                    information_gain_log_terms(prior, test)


if __name__ == "__main__":
    unittest.main()
