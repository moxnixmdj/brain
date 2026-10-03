from __future__ import annotations
import unittest
from canonical.runtime import recovery_opus55_zero_reality_acceptance_reduction_v1 as r

class RecoveryOpus55ZeroRealityAcceptanceReductionV1Tests(unittest.TestCase):
    def test_three_recovery_predicates_are_eligible(self):
        out=r.evaluate()
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["proposed_atomic_acceptance_delta"],3)
        self.assertEqual(out["proposed_family_acceptance_delta"],1)
        self.assertTrue(out["promotion_eligible"])
        self.assertEqual(set(out["predicate_verdicts"]),{
            "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
            "RECOVERY_TERMINAL_NONINFERIOR",
            "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
        })

    def test_only_zero_reality_scope_complete_stronger_proof_is_load_bearing(self):
        out=r.evaluate()
        self.assertTrue(out["pass"],out)
        b=out["stronger_proof_basis"]
        self.assertTrue(b["scope_complete"])
        self.assertTrue(b["objective_ceiling_or_floor"])
        self.assertFalse(b["exact_opus_case_level_access_required"])
        self.assertFalse(b["historical_narrow_terminal_run_used_as_proof"])
        self.assertFalse(b["quarantined_public_recovery_run_used_as_proof"])
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["terminal_results_replayed"],0)

    def test_candidate_cannot_self_promote(self):
        out=r.evaluate()
        self.assertTrue(out["pass"],out)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertEqual(out["family_credit_delta"],0)
        self.assertEqual(out["capability_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
