from __future__ import annotations
import unittest
from canonical.runtime import recovery_acceptance_integrator_v1 as r

class RecoveryAcceptanceIntegratorV1Tests(unittest.TestCase):
    def test_exact_recovery_delta_only(self):
        out=r.evaluate(); self.assertTrue(out["pass"],out)
        self.assertEqual(out["before"],{"proved_atomic":8,"unresolved_atomic":30,"accepted_families":3,"open_families":16})
        self.assertEqual(out["after"],{"proved_atomic":11,"unresolved_atomic":27,"accepted_families":4,"open_families":15})
        self.assertEqual(set(out["newly_proved_predicates"]),r.RECOVERY)
        self.assertEqual(out["newly_closed_families"],[r.FAMILY])
    def test_no_other_family_or_predicate_receives_credit(self):
        out=r.evaluate(); self.assertTrue(out["pass"],out)
        self.assertEqual(set(out["preserved_closed_families"]),r.CURRENT_CLOSED)
        self.assertEqual({x["predicate_id"] for x in out["proposed_claims"]},r.RECOVERY)
        self.assertEqual(len(out["proposed_claims"]),3)
    def test_verified_hardened_receipt_is_only_new_basis(self):
        out=r.evaluate(); self.assertTrue(out["pass"],out)
        for claim in out["proposed_claims"]:
            self.assertEqual(claim["source_path"],r.RECEIPT)
            self.assertEqual(claim["source_sha"],r.EXPECTED[r.RECEIPT])
            self.assertTrue(claim["scope_complete"])
            self.assertTrue(claim["independent_or_objective"])
    def test_integrator_cannot_self_promote_or_consume_reality(self):
        out=r.evaluate(); self.assertTrue(out["pass"],out)
        self.assertTrue(out["promotion_eligible"])
        self.assertFalse(out["promotion_authority"]); self.assertFalse(out["execution_authority"])
        self.assertEqual(out["new_reality_units_consumed"],0); self.assertEqual(out["terminal_results_replayed"],0)
if __name__=="__main__": unittest.main(verbosity=2)
