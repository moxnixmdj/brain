from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from canonical.runtime.tb4_minimum_carrier_recovery_cut_v1 import evaluate

ROOT=Path(__file__).resolve().parents[2]
SPEC=ROOT/"canonical/governance/TB4_MINIMUM_CARRIER_RECOVERY_CUT_V1.json"

class CutTests(unittest.TestCase):
    def doc(self):
        return json.loads(SPEC.read_text())
    def test_live_candidate_reopens_boundary_only(self):
        out=evaluate(self.doc())
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["minimum_additional_creditable_tasks"],8)
        self.assertEqual(out["selected_task_count"],8)
        self.assertEqual(out["projected_creditable_task_count"],44)
        self.assertEqual(out["projected_upper_bound_successes"],220)
        self.assertEqual(out["required_successes"],220)
        self.assertTrue(out["attainability_would_reopen_at_boundary"])
        self.assertEqual(out["minimum_carrier_envelope"],{
            "cpus_at_least":8,
            "usable_memory_mb_at_least":16384,
            "free_storage_mb_at_least":51200,
            "gpus_required":0,
        })
        self.assertFalse(out["concrete_carrier_bound"])
        self.assertFalse(out["execution_authority"])
    def test_seven_rows_cannot_claim_cut(self):
        d=self.doc()
        d["minimum_recovery_set"]=d["minimum_recovery_set"][:-1]
        out=evaluate(d)
        self.assertFalse(out["pass"])
        self.assertIn("RECOVERY_SET_NOT_MINIMUM_CARDINALITY",out["errors"])
    def test_self_authorization_fails(self):
        d=self.doc()
        d["verification_state"]["concrete_zero_cost_carrier_bound"]=True
        out=evaluate(d)
        self.assertFalse(out["pass"])
        self.assertIn("CANDIDATE_MUST_NOT_SELF_AUTHORIZE",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
