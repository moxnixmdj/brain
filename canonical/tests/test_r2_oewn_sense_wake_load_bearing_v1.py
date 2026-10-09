import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
CUR=ROOT/"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
SCHED=ROOT/"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V53.json"
REC=ROOT/"canonical/governance/R2_OEWN_SENSE_UNIVERSE_WAKE_RECONCILIATION_20261009_V1.json"
ACT=ROOT/"canonical/governance/OEWN_2025_RELEASE_SENSE_UNIVERSE_ACTIVATION_20261009_V1.json"
VER=ROOT/"canonical/verification/OEWN_2025_RELEASE_SENSE_UNIVERSE_REMOTE_VERIFY_20261009_V1.json"

class TestR2OEWNSenseWakeLoadBearing(unittest.TestCase):
    def test_v55_v53_refinement_is_sound(self):
        cur=json.loads(CUR.read_text())
        sched=json.loads(SCHED.read_text())
        rec=json.loads(REC.read_text())
        act=json.loads(ACT.read_text())
        ver=json.loads(VER.read_text())
        old="NEW_EXACT_OEWN_RELEASE_RELATIVE_SENSE_UNIVERSE_FOR_A_POLICY_CHANGING_LEMMA"
        new="NEW_TASK_SPECIFIC_OEWN_TERMINAL_SIGNATURE_OR_DISCRIMINATOR_BINDING_FOR_SURVIVING_RELEASE_RELATIVE_SENSES"

        self.assertIn("V55",cur["status"])
        self.assertEqual(cur["scheduler_cut"]["path"],"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V53.json")
        self.assertEqual(sched["schema"],"PROJECT_BRAIN_ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V53")

        for doc in (cur,sched):
            finance=doc["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
            self.assertNotIn(old,finance["wake_on"])
            self.assertIn(new,finance["wake_on"])
            self.assertTrue(any(
                row.get("condition")==old and
                "OEWN_2025" in str(row.get("scope") or "") and
                row.get("intended_sense_globally_closed") is False
                for row in finance["satisfied_wake_conditions"]
            ))

        self.assertTrue(rec["proved"]["candidate_set_complete_relative_to_release"])
        self.assertFalse(rec["proved"]["intended_sense_identified_by_enumeration"])
        self.assertFalse(rec["scheduler_effect"]["remove_global_word_sense_residual"])
        self.assertEqual(rec["scheduler_effect"]["finance_primary_unsolved_count_delta"],0)

        self.assertEqual(act["authority"]["semantic_truth_authority"],False)
        self.assertEqual(ver["verification"]["candidate_set_complete_relative_to_release"],True)
        self.assertEqual(ver["verification"]["intended_sense_identified"],False)
        self.assertEqual(rec["accounting"]["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main()
