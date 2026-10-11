from __future__ import annotations

import unittest

from canonical.runtime import aa_briefcase_top_support_collapse_v1 as cut


class Tests(unittest.TestCase):
    def test_singleton(self):
        self.assertEqual(cut.universal_top_elements(["A"]), ["A"])

    def test_two_outcomes_no_common_top(self):
        self.assertEqual(cut.universal_top_elements(["A", "B"]), [])

    def test_three_outcomes_no_common_top(self):
        self.assertEqual(cut.universal_top_elements(["A", "B", "C"]), [])

    def test_distinct_not_universally_above(self):
        self.assertFalse(cut.dominates_under_all_indicators("A", "B", ["A", "B"]))

    def test_reflexive(self):
        self.assertTrue(cut.dominates_under_all_indicators("A", "A", ["A", "B"]))

    def test_current_open_class_collapses(self):
        out = cut.evaluate_aa_top_support_route({
            "benchmark": "AA-Briefcase",
            "version": "1.1",
            "scope_complete_public_superdomain": True,
            "hidden_predicate_class_soundly_restricted": False,
            "material_order_complete": False,
            "brain_global_top_support_proved": False,
            "judge_monotonicity_proved": False,
            "frozen_score_monotonicity_proved": False,
        })
        self.assertEqual(out["status"], "COLLAPSE_TO_OBSERVATIONAL_EQUIVALENCE")
        self.assertFalse(out["pass"])
        self.assertEqual(out["universal_top_elements_in_two_outcome_indicator_class"], [])

    def test_restricted_route_reports_four_slots(self):
        out = cut.evaluate_aa_top_support_route({
            "benchmark": "AA-Briefcase",
            "version": "1.1",
            "scope_complete_public_superdomain": True,
            "hidden_predicate_class_soundly_restricted": True,
            "material_order_complete": False,
            "brain_global_top_support_proved": False,
            "judge_monotonicity_proved": False,
            "frozen_score_monotonicity_proved": False,
        })
        self.assertEqual(len(out["missing"]), 4)

    def test_complete_restricted_route(self):
        out = cut.evaluate_aa_top_support_route({
            "benchmark": "AA-Briefcase",
            "version": "1.1",
            "scope_complete_public_superdomain": True,
            "hidden_predicate_class_soundly_restricted": True,
            "material_order_complete": True,
            "brain_global_top_support_proved": True,
            "judge_monotonicity_proved": True,
            "frozen_score_monotonicity_proved": True,
        })
        self.assertEqual(out["status"], "PASS_TOP_SUPPORT_PREMISES")
        self.assertTrue(out["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
