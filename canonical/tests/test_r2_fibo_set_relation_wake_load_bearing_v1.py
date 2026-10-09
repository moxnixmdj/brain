import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
CUR=ROOT/"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
SCHED=ROOT/"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V52.json"
REC=ROOT/"canonical/governance/R2_FINANCE_FIBO_FULL_RELEASE_SET_RELATION_WAKE_RECONCILIATION_20261009_V1.json"
VER=ROOT/"canonical/verification/R2_FINANCE_FIBO_FULL_RELEASE_SET_RELATION_WAKE_RECONCILIATION_VERIFY_20261009_V1.json"

class TestR2FiboSetRelationWakeLoadBearing(unittest.TestCase):
    def test_v54_pointer_and_v52_scheduler_are_coherent(self):
        cur=json.loads(CUR.read_text())
        sched=json.loads(SCHED.read_text())
        rec=json.loads(REC.read_text())
        ver=json.loads(VER.read_text())
        old="NEW_AUTHENTICATED_COMPLETE_BOUNDED_DENOTATION_EXTENSION_OR_SET_RELATION_EVIDENCE"
        new="NEW_AUTHENTICATED_COMPLETE_BOUNDED_DENOTATION_EXTENSION_OR_SET_RELATION_EVIDENCE_OUTSIDE_VERIFIED_FIBO_Q2_2026_FULL_RELEASE_295_FILE_SCOPE"

        self.assertIn("V54",cur["status"])
        self.assertEqual(cur["scheduler_cut"]["path"],"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V52.json")
        self.assertEqual(sched["schema"],"PROJECT_BRAIN_ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V52")
        self.assertEqual(sched["supersedes"]["path"],"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V51.json")

        for doc in (cur,sched):
            finance=doc["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
            self.assertNotIn(old,finance["wake_on"])
            self.assertIn(new,finance["wake_on"])
            self.assertTrue(any(
                row.get("condition")==old and
                "FULL_RELEASE_295_FILE" in str(row.get("scope") or "") and
                row.get("global_finance_semantic_tail_closed") is False
                for row in finance["satisfied_wake_conditions"]
            ))

        self.assertEqual(rec["scheduler_effect"]["finance_primary_unsolved_count_delta"],0)
        self.assertFalse(rec["scheduler_effect"]["remove_global_wake_condition"])
        self.assertEqual(ver["result"]["finance_primary_unsolved_count_delta"],0)
        self.assertEqual(ver["accounting"]["terminal_credit_delta"],0)
        self.assertEqual(cur["full_fibo_set_relation_wake_reconciliation"]["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main()
