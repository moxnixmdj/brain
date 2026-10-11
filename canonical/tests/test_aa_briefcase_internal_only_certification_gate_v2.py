from __future__ import annotations

import unittest

from canonical.runtime.aa_briefcase_internal_only_certification_gate_v2 import (
    GateError,
    evaluate,
)


def proof(name: str):
    return {
        "verified": True,
        "scope_complete": True,
        "path": f"canonical/verification/{name}.json",
        "git_blob_sha": "a" * 40,
    }


def base():
    return {
        "target": "AA-Briefcase v1.1 >= 1822 Elo",
        "external_help_allowed": False,
        "exact_target_identity": proof("target"),
        "score_trace_substitution_route": {},
        "top_support_route": {},
    }


class Tests(unittest.TestCase):
    def test_score_trace_route_passes_when_complete(self):
        x = base()
        x["score_trace_substitution_route"] = {
            "score_bearing_sufficient_statistic": proof("stat"),
            "complete_reference_candidate_trace_equivalence": proof("trace"),
            "scorer_implementation_equivariance_or_unique_fit": proof("scorer"),
            "frozen_reference_1822": proof("ref"),
        }
        out = evaluate(x)
        self.assertTrue(out["pass"])
        self.assertEqual(out["accepted_route"], "SCORE_TRACE_SUBSTITUTION")

    def test_trace_equivalence_is_individually_visible(self):
        x = base()
        x["score_trace_substitution_route"] = {
            "score_bearing_sufficient_statistic": proof("stat"),
            "scorer_implementation_equivariance_or_unique_fit": proof("scorer"),
            "frozen_reference_1822": proof("ref"),
        }
        out = evaluate(x)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["score_trace_substitution_missing"],
            ["complete_reference_candidate_trace_equivalence"],
        )

    def test_scorer_invariance_is_individually_visible(self):
        x = base()
        x["score_trace_substitution_route"] = {
            "score_bearing_sufficient_statistic": proof("stat"),
            "complete_reference_candidate_trace_equivalence": proof("trace"),
            "frozen_reference_1822": proof("ref"),
        }
        out = evaluate(x)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["score_trace_substitution_missing"],
            ["scorer_implementation_equivariance_or_unique_fit"],
        )

    def test_top_support_route_passes_when_complete(self):
        x = base()
        x["top_support_route"] = {
            "complete_outcome_superdomain": proof("domain"),
            "sound_material_order": proof("order"),
            "brain_support_confined_to_global_top": proof("support"),
            "hidden_evaluator_monotonicity": proof("judge"),
            "frozen_1822_score_monotonicity": proof("score"),
        }
        out = evaluate(x)
        self.assertTrue(out["pass"])
        self.assertEqual(out["accepted_route"], "UNIVERSAL_TOP_SUPPORT")

    def test_top_support_reports_only_missing_slots(self):
        x = base()
        x["top_support_route"] = {
            "complete_outcome_superdomain": proof("domain"),
            "sound_material_order": proof("order"),
        }
        out = evaluate(x)
        self.assertEqual(
            out["top_support_missing"],
            [
                "brain_support_confined_to_global_top",
                "hidden_evaluator_monotonicity",
                "frozen_1822_score_monotonicity",
            ],
        )

    def test_target_identity_is_separate(self):
        x = base()
        x["exact_target_identity"] = {}
        out = evaluate(x)
        self.assertTrue(out["target_identity_missing"])
        self.assertFalse(out["pass"])

    def test_external_help_is_rejected(self):
        x = base()
        x["external_help_allowed"] = True
        with self.assertRaisesRegex(GateError, "INTERNAL_ONLY"):
            evaluate(x)


if __name__ == "__main__":
    unittest.main(verbosity=2)
