import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
CUR=ROOT/"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
SCHED=ROOT/"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V54.json"
REC=ROOT/"canonical/governance/R2_SEC_INLINE_XBRL_FIELD_SEMANTICS_WAKE_RECONCILIATION_20261009_V1.json"

class TestR2SecInlineXbrlFieldSemanticsWake(unittest.TestCase):
    def test_bounded_refinement_preserves_global_residual(self):
        cur=json.loads(CUR.read_text())
        sched=json.loads(SCHED.read_text())
        rec=json.loads(REC.read_text())
        old="NEW_AUTHENTICATED_CONTEXT_SOURCE_AND_FIELD_SEMANTICS_BINDING_OUTSIDE_VERIFIED_SEC_STANDARD_XBRL_COMPANYCONCEPT_SCOPE"
        new="NEW_AUTHENTICATED_CONTEXT_SOURCE_AND_FIELD_SEMANTICS_BINDING_OUTSIDE_VERIFIED_SEC_COMPANYCONCEPT_AND_SEC_INLINE_XBRL_STANDARD_FASB_SCOPES"
        self.assertIn("V56",cur["status"])
        self.assertEqual(cur["scheduler_cut"]["path"],"canonical/governance/ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V54.json")
        self.assertEqual(sched["schema"],"PROJECT_BRAIN_ROOT2_SINGLE_PRIMITIVE_WAKE_CUT_20261009_V54")
        for doc in (cur,sched):
            finance=doc["current_cell_classifications"]["FINANCE_SEMANTIC_ADEQUACY_TAIL"]
            self.assertNotIn(old,finance["wake_on"])
            self.assertIn(new,finance["wake_on"])
            self.assertTrue(any(
                row.get("condition")==old and
                "INLINE_XBRL" in str(row.get("scope") or "") and
                row.get("global_finance_semantic_tail_closed") is False
                for row in finance["satisfied_wake_conditions"]
            ))
        self.assertTrue(rec["proved"]["occurrence_local_inline_xbrl_qname_identity"])
        self.assertTrue(rec["proved"]["exact_standard_us_gaap_release_metadata_rederived_from_fasb_taxonomy_bytes"])
        self.assertTrue(rec["proved"]["producer_independent_raw_byte_rederivation"])
        self.assertFalse(rec["proved"]["nearby_visible_prose_semantics_claimed"])
        self.assertFalse(rec["proved"]["custom_extension_semantics_claimed"])
        self.assertFalse(rec["proved"]["free_text_policy_semantics_claimed"])
        self.assertFalse(rec["proved"]["policy_adequacy_authority"])
        self.assertFalse(rec["proved"]["semantic_truth_authority"])
        self.assertFalse(rec["scheduler_effect"]["remove_global_wake_condition"])
        self.assertEqual(rec["scheduler_effect"]["finance_primary_unsolved_count_delta"],0)
        self.assertEqual(rec["accounting"]["terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main()
