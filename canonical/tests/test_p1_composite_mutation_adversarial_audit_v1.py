import unittest

from canonical.runtime.p1_composite_mutation_adversarial_audit_v1 import audit


EXPECTED_GAPS = {
    "CHECK:FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS:EMPTY_SUPPORT_NOT_REJECTED",
    "MUTATION:DROP_PROVENANCE_OR_DEPENDENCY_EDGE:PROVENANCE_SUPPORT_DROP_NOT_REJECTED",
}


class P1CompositeMutationAdversarialAuditTests(unittest.TestCase):
    def test_p1_composite_role_audit_finds_exact_receipt_support_gap(self):
        out = audit()
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "FAIL_CLOSED__P1_COMPOSITE_ROLE_GAPS_FOUND")
        self.assertEqual(set(out["gaps"]), EXPECTED_GAPS, out)

    def test_other_assigned_v4_obligations_are_load_bearing(self):
        out = audit()
        checks = out["checks"]
        self.assertTrue(checks["DROPPED_DEPENDENCY_EDGE_IS_REJECTED"])
        self.assertTrue(checks["MULTISTEP_CAUSAL_PREDECESSOR_IS_PRESERVED"])
        self.assertTrue(checks["IGNORED_AUTHORITY_VIOLATION_IS_REJECTED"])
        self.assertTrue(checks["NONIDENTIFIABILITY_IS_PRESERVED"])
        self.assertTrue(checks["MECHANISM_CLASS_TRACKS_VISIBLE_FAILED_CONTRACT"])

    def test_audit_never_claims_credit_or_authority(self):
        out = audit()
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["terminal_results_replayed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
