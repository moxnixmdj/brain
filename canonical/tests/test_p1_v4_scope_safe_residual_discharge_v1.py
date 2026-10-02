from __future__ import annotations

import copy
import unittest

from canonical.runtime import p1_v4_scope_safe_residual_discharge_v1 as compiler


class P1V4ScopeSafeResidualDischargeTests(unittest.TestCase):
    def test_live_v4_compresses_quarantine_but_does_not_clear_it(self):
        out = compiler.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["can_clear_p1_scope_quarantine"])
        self.assertEqual(out["v4_recomputed_case_count"], 168)
        self.assertEqual(out["v4_case_failures"], [])
        self.assertIn(
            "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS",
            out["semantics_discharged_by_existing_v4"],
        )
        self.assertIn(
            "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
            out["semantics_discharged_by_existing_v4"],
        )
        self.assertIn(
            "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
            out["semantics_discharged_by_existing_v4"],
        )
        ids = {row["id"] for row in out["residual_obligations"]}
        self.assertEqual(
            ids,
            {"P1_EXPLICIT_SCOPE_FAILURE_CLASS", "P1_HETEROGENEOUS_INTERVENTION_RESCUE"},
        )
        self.assertEqual(out["class_coverage"]["missing_from_v4"], ["SCOPE"])
        self.assertFalse(out["heterogeneous_post_intervention_terminal_rescue_verified"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["new_reality_units_consumed"], 0)

    def test_even_complete_prewave_v4_cannot_clear_terminal_quarantine(self):
        v = copy.deepcopy(compiler._load(compiler.V4_VERIFICATION))
        future_kinds = set(compiler.candidate_v4.ALLOWED_KINDS) | {"SCOPE"}
        v["verified"]["mechanism_classes"] = sorted(future_kinds)
        v["verified"]["heterogeneous_post_intervention_terminal_rescue_verified"] = True

        original = compiler.candidate_v4.ALLOWED_KINDS
        compiler.candidate_v4.ALLOWED_KINDS = future_kinds
        try:
            out = compiler.evaluate(v4_verification=v)
        finally:
            compiler.candidate_v4.ALLOWED_KINDS = original

        self.assertTrue(out["pass"], out)
        self.assertFalse(
            out["can_clear_p1_scope_quarantine"],
            "prewave V4 evidence must never substitute for frozen T0/T2 terminal rescue evidence",
        )

    def test_spoofed_scope_claim_without_live_candidate_support_fails_closed(self):
        v = copy.deepcopy(compiler._load(compiler.V4_VERIFICATION))
        v["verified"]["mechanism_classes"] = list(v["verified"]["mechanism_classes"]) + ["SCOPE"]
        out = compiler.evaluate(v4_verification=v)
        self.assertFalse(out["pass"], out)
        self.assertIn("V4_VERIFIED_KIND_SET_DOES_NOT_MATCH_LIVE_CANDIDATE", out["errors"])
        self.assertFalse(out["can_clear_p1_scope_quarantine"])

    def test_missing_ambiguity_pattern_fails_closed(self):
        v = copy.deepcopy(compiler._load(compiler.V4_VERIFICATION))
        v["verified"]["causal_patterns"] = ["SINGLE", "DELAYED", "INTERACTION"]
        out = compiler.evaluate(v4_verification=v)
        self.assertFalse(out["pass"], out)
        self.assertIn("V4_CAUSAL_PATTERN_COVERAGE_DRIFT", out["errors"])

    def test_unverified_rescue_claim_is_ignored(self):
        v = copy.deepcopy(compiler._load(compiler.V4_VERIFICATION))
        v["unverified_note"] = {"heterogeneous_post_intervention_terminal_rescue_verified": True}
        out = compiler.evaluate(v4_verification=v)
        self.assertTrue(out["pass"], out)
        ids = {row["id"] for row in out["residual_obligations"]}
        self.assertIn("P1_HETEROGENEOUS_INTERVENTION_RESCUE", ids)
        self.assertFalse(out["heterogeneous_post_intervention_terminal_rescue_verified"])
        self.assertFalse(out["can_clear_p1_scope_quarantine"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
