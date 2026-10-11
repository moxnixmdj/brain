from __future__ import annotations

import unittest

from canonical.runtime.aa_briefcase_internal_only_certification_gate_v3 import (
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


def floor_proof(value: float):
    return {
        **proof("candidate-floor"),
        "candidate_unrounded_elo_lower_bound": value,
    }


def base():
    return {
        "target": "AA-Briefcase v1.1 >= 1822 Elo",
        "external_help_allowed": False,
        "exact_target_identity": proof("target"),
        "frozen_reference_precision": {
            "owner_measured_unrounded_elo": 1821.85,
            "literal_threshold_elo": 1822.0,
            "threshold_changed": False,
            "proof": proof("precision"),
        },
        "score_trace_substitution_route": {
            "score_bearing_sufficient_statistic": proof("stat"),
            "complete_reference_candidate_trace_equivalence": proof("trace"),
            "scorer_implementation_equivariance_or_unique_fit": proof("scorer"),
        },
        "top_support_route": {},
    }


class Tests(unittest.TestCase):
    def test_exact_trace_equality_is_reference_parity_only(self):
        out = evaluate(base())
        self.assertFalse(out["pass"])
        self.assertTrue(out["trace_equivalence_bound"])
        self.assertTrue(out["trace_equivalence_is_reference_parity_only"])
        self.assertTrue(out["candidate_literal_floor_ge_1822_missing"])
        self.assertEqual(out["frozen_owner_measured_reference_elo"], 1821.85)

    def test_literal_floor_1822_closes_quantitative_trace_route(self):
        x = base()
        x["score_trace_substitution_route"]["candidate_literal_floor_ge_1822"] = floor_proof(1822.0)
        out = evaluate(x)
        self.assertTrue(out["pass"])
        self.assertEqual(out["accepted_route"], "QUANTITATIVE_SCORE_TRACE")

    def test_floor_below_1822_does_not_close(self):
        x = base()
        x["score_trace_substitution_route"]["candidate_literal_floor_ge_1822"] = floor_proof(1821.999)
        out = evaluate(x)
        self.assertFalse(out["pass"])
        self.assertTrue(out["candidate_literal_floor_ge_1822_missing"])

    def test_exact_reference_floor_1821_85_does_not_close(self):
        x = base()
        x["score_trace_substitution_route"]["candidate_literal_floor_ge_1822"] = floor_proof(1821.85)
        out = evaluate(x)
        self.assertFalse(out["pass"])

    def test_wrong_reference_precision_fails_closed(self):
        x = base()
        x["frozen_reference_precision"]["owner_measured_unrounded_elo"] = 1822.0
        out = evaluate(x)
        self.assertFalse(out["pass"])
        self.assertTrue(out["frozen_reference_precision_missing"])

    def test_threshold_change_not_allowed(self):
        x = base()
        x["frozen_reference_precision"]["threshold_changed"] = True
        out = evaluate(x)
        self.assertFalse(out["pass"])
        self.assertTrue(out["frozen_reference_precision_missing"])

    def test_complete_top_support_route_still_can_close(self):
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

    def test_external_help_mode_rejected(self):
        x = base()
        x["external_help_allowed"] = True
        with self.assertRaisesRegex(GateError, "INTERNAL_ONLY"):
            evaluate(x)

    def test_missing_target_identity_blocks(self):
        x = base()
        x["exact_target_identity"] = {}
        out = evaluate(x)
        self.assertFalse(out["pass"])
        self.assertTrue(out["target_identity_missing"])

    def test_required_margin_is_point_15_elo(self):
        out = evaluate(base())
        self.assertAlmostEqual(out["minimum_required_improvement_over_exact_reference"], 0.15, places=9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
