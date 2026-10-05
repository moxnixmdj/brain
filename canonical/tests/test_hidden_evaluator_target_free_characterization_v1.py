from __future__ import annotations

import unittest

from canonical.runtime.hidden_evaluator_target_free_characterization_v1 import (
    characterize_target_free_monotone_dominance,
)


def chain():
    return {
        "outcomes": ["TOP", "MID", "LOW"],
        "dominance_edges": [["TOP", "MID"], ["MID", "LOW"]],
        "brain_support": ["TOP"],
    }


class Tests(unittest.TestCase):
    def test_unique_greatest_singleton_support_is_exact_target_free_case(self):
        verdict = characterize_target_free_monotone_dominance(chain())
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertEqual(verdict["greatest_element"], "TOP")
        self.assertTrue(verdict["target_free_universal_monotone_dominance"])
        self.assertFalse(verdict["target_distribution_or_additional_evaluator_information_required"])
        self.assertIsNone(verdict["counterexample"])

    def test_non_greatest_support_emits_constructive_upper_set_counterexample(self):
        cert = chain()
        cert["brain_support"] = ["MID"]
        verdict = characterize_target_free_monotone_dominance(cert)
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertFalse(verdict["target_free_universal_monotone_dominance"])
        self.assertEqual(verdict["counterexample"]["target_distribution"], "DELTA:TOP")
        self.assertEqual(verdict["counterexample"]["upper_set"], ["TOP"])
        self.assertEqual(verdict["counterexample"]["brain_support_outside_upper_set"], ["MID"])

    def test_mixture_with_positive_non_greatest_support_fails_target_free_boundary(self):
        cert = chain()
        cert["brain_support"] = ["TOP", "MID"]
        verdict = characterize_target_free_monotone_dominance(cert)
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertFalse(verdict["target_free_universal_monotone_dominance"])
        self.assertIn("MID", verdict["counterexample"]["brain_support_outside_upper_set"])

    def test_incomparable_maxima_have_no_greatest_and_require_information(self):
        cert = {
            "outcomes": ["A", "B", "LOW"],
            "dominance_edges": [["A", "LOW"], ["B", "LOW"]],
            "brain_support": ["A"],
        }
        verdict = characterize_target_free_monotone_dominance(cert)
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertIsNone(verdict["greatest_element"])
        self.assertFalse(verdict["target_free_universal_monotone_dominance"])
        self.assertTrue(verdict["target_distribution_or_additional_evaluator_information_required"])
        self.assertEqual(verdict["counterexample"]["target_distribution"], "DELTA:B")

    def test_transitive_closure_finds_greatest(self):
        verdict = characterize_target_free_monotone_dominance(chain())
        self.assertEqual(verdict["greatest_element"], "TOP")
        self.assertTrue(verdict["target_free_universal_monotone_dominance"])

    def test_singleton_universe_is_trivial_exact_case(self):
        cert = {"outcomes": ["ONLY"], "dominance_edges": [], "brain_support": ["ONLY"]}
        verdict = characterize_target_free_monotone_dominance(cert)
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertTrue(verdict["target_free_universal_monotone_dominance"])

    def test_cycle_fails_closed(self):
        cert = chain()
        cert["dominance_edges"].append(["LOW", "TOP"])
        verdict = characterize_target_free_monotone_dominance(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("DOMINANCE_NOT_ANTISYMMETRIC", verdict["reason"])

    def test_unknown_support_outcome_fails_closed(self):
        cert = chain()
        cert["brain_support"] = ["GHOST"]
        verdict = characterize_target_free_monotone_dominance(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("UNKNOWN_OUTCOME", verdict["reason"])

    def test_duplicate_support_fails_closed(self):
        cert = chain()
        cert["brain_support"] = ["TOP", "TOP"]
        verdict = characterize_target_free_monotone_dominance(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("DUPLICATE", verdict["reason"])

    def test_empty_support_fails_closed(self):
        cert = chain()
        cert["brain_support"] = []
        verdict = characterize_target_free_monotone_dominance(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("EMPTY", verdict["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
