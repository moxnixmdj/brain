from __future__ import annotations

import unittest

from canonical.runtime.aa_briefcase_internal_only_certification_gate_v1 import (
    evaluate,
)


def proof(name: str):
    return {
        "verified": True,
        "scope_complete": True,
        "path": f"canonical/verification/{name}.json",
        "git_blob_sha": "a" * 40,
    }


class Tests(unittest.TestCase):
    def base(self):
        return {
            "target": "AA-Briefcase v1.1 >= 1822 Elo",
            "external_help_allowed": False,
            "exact_target_identity": proof("target"),
            "observational_equivalence_route": {},
            "top_support_route": {},
        }

    def test_top_support_complete_passes(self):
        x = self.base()
        x["top_support_route"] = {
            "complete_outcome_superdomain": proof("domain"),
            "sound_material_order": proof("order"),
            "brain_support_confined_to_global_top": proof("support"),
            "hidden_evaluator_monotonicity": proof("monotonicity"),
            "frozen_1822_score_monotonicity": proof("score"),
        }
        out = evaluate(x)
        self.assertTrue(out["pass"])
        self.assertEqual(out["accepted_route"], "UNIVERSAL_TOP_SUPPORT")

    def test_observational_equivalence_complete_passes(self):
        x = self.base()
        x["observational_equivalence_route"] = {
            "whole_hidden_scope_equivalence": proof("eq"),
            "frozen_1822_score_implication": proof("score"),
        }
        out = evaluate(x)
        self.assertTrue(out["pass"])
        self.assertEqual(out["accepted_route"], "OBSERVATIONAL_EQUIVALENCE")

    def test_property_truth_without_top_performance_is_open(self):
        x = self.base()
        x["top_support_route"] = {
            "complete_outcome_superdomain": proof("domain"),
            "sound_material_order": proof("order"),
            "brain_support_confined_to_global_top": {},
            "hidden_evaluator_monotonicity": proof("monotonicity"),
            "frozen_1822_score_monotonicity": proof("score"),
        }
        out = evaluate(x)
        self.assertFalse(out["pass"])
        self.assertIn("UNIVERSAL_TOP_SUPPORT_ROUTE", out["missing"])

    def test_local_selected_cell_is_not_global_support(self):
        x = self.base()
        x["top_support_route"] = {
            "complete_outcome_superdomain": proof("domain"),
            "sound_material_order": proof("order"),
            "brain_support_confined_to_global_top": {
                "verified": True,
                "scope_complete": False,
                "path": "canonical/verification/local_30.json",
                "git_blob_sha": "a" * 40,
            },
            "hidden_evaluator_monotonicity": proof("monotonicity"),
            "frozen_1822_score_monotonicity": proof("score"),
        }
        self.assertFalse(evaluate(x)["pass"])

    def test_external_route_is_rejected_by_internal_only_gate(self):
        x = self.base()
        x["external_help_allowed"] = True
        with self.assertRaisesRegex(ValueError, "INTERNAL_ONLY"):
            evaluate(x)


if __name__ == "__main__":
    unittest.main(verbosity=2)
