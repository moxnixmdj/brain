from __future__ import annotations

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
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["new_reality_units_consumed"], 0)

    def test_adding_scope_kind_alone_leaves_only_intervention_rescue(self):
        kinds = set(compiler.candidate_v4.ALLOWED_KINDS) | {"SCOPE"}
        out = compiler.evaluate(v4_kinds=kinds)
        self.assertTrue(out["pass"], out)
        ids = {row["id"] for row in out["residual_obligations"]}
        self.assertEqual(ids, {"P1_HETEROGENEOUS_INTERVENTION_RESCUE"})
        self.assertEqual(out["unresolved_terminal_missing_semantics"], [])
        self.assertFalse(out["can_clear_p1_scope_quarantine"])

    def test_rescue_proof_alone_leaves_explicit_scope_class(self):
        out = compiler.evaluate(rescue_intervention_verified=True)
        self.assertTrue(out["pass"], out)
        ids = {row["id"] for row in out["residual_obligations"]}
        self.assertEqual(ids, {"P1_EXPLICIT_SCOPE_FAILURE_CLASS"})
        self.assertFalse(out["can_clear_p1_scope_quarantine"])

    def test_both_residuals_discharged_make_quarantine_clearable_candidate_only(self):
        kinds = set(compiler.candidate_v4.ALLOWED_KINDS) | {"SCOPE"}
        out = compiler.evaluate(
            v4_kinds=kinds,
            rescue_intervention_verified=True,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["residual_obligations"], [])
        self.assertEqual(out["unresolved_terminal_missing_semantics"], [])
        self.assertTrue(out["can_clear_p1_scope_quarantine"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["family_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
