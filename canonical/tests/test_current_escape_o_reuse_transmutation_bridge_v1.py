from __future__ import annotations
from copy import deepcopy
import unittest
from canonical.runtime.current_escape_o_reuse_transmutation_bridge_v1 import analyze_documents, CUT_SCHEMA

O1="CODING_TB4_GE_66_4"
O2="AUTOMATIONBENCH_GE_40"
Q1="PROWORK_AA_BRIEFCASE_GE_1822__SHARED_MEASUREMENT_WITH_ARTIFACT"
P1="TB_SCIENCE_GE_58_7"

def cut():
    return {"schema":CUT_SCHEMA,"current_partition":{
        "active_o_obligation_ids":[O1,O2],
        "active_q_obligation_ids":[Q1],
        "parked_obligation_ids":[P1],
        "active_o_rows":2,"active_q_rows":1,"parked_rows":1,"active_rows":3,"total_escape_rows":4}}

def universal():
    return {"id":"E1","mode":"UNIVERSAL","verified":True,"independent":True,
      "contamination_clean":True,"binds_frozen_protocol":True,"scope_relation":"PROVEN_STRONGER",
      "closes_entire_protocol":True,
      "result":{"all_admissible_inputs_proved":True,"formal_completeness":True}}

class Tests(unittest.TestCase):
    def test_nested_current_o_evidence_becomes_candidate(self):
        out=analyze_documents(cut(),[("canonical/governance/a.json","a"*40,{"target_predicate":O1,"certificate":universal()})])
        self.assertTrue(out["pass"],out); self.assertEqual(out["candidate_obligation_ids"],[O1])
        self.assertEqual(out["missing_obligation_ids"],[O2]); self.assertTrue(out["candidates"][0]["v4_packaging_required"])
        self.assertFalse(out["acceptance_authority"])
    def test_partial_or_incomplete_evidence_is_rejected(self):
        e=universal(); e["scope_relation"]="PARTIAL"
        out=analyze_documents(cut(),[("canonical/evidence/b.json","b"*40,{"obligation_id":O1,"evidence":e})])
        self.assertEqual(out["candidate_obligation_count"],0)
        self.assertEqual(out["missing_obligation_ids"],sorted([O1,O2]))
        self.assertTrue(any("SCOPE_NOT_EXACT_OR_PROVEN_STRONGER" in r["reasons"] for r in out["rejections"]))
    def test_q_and_parked_rows_do_not_enter_o_candidates(self):
        out=analyze_documents(cut(),[
          ("canonical/evidence/q.json","c"*40,{"target_predicate":Q1,"e":universal()}),
          ("canonical/evidence/p.json","d"*40,{"target_predicate":P1,"e":universal()})])
        self.assertEqual(out["candidate_obligation_count"],0)
        self.assertEqual(out["missing_obligation_ids"],sorted([O1,O2]))
    def test_explicit_multirow_binding_is_preserved(self):
        out=analyze_documents(cut(),[("canonical/verification/multi.json","e"*40,{"predicate_ids":[O1,O2],"stronger_proof":universal()})])
        self.assertEqual(out["candidate_obligation_ids"],sorted([O1,O2])); self.assertEqual(out["missing_obligation_count"],0)
        self.assertEqual(out["multi_row_sources"][0]["row_count"],2)
    def test_no_cross_row_inference_without_explicit_context(self):
        out=analyze_documents(cut(),[("canonical/governance/no-context.json","f"*40,{"notes":[O1,O2],"certificate":universal()})])
        self.assertEqual(out["candidate_obligation_count"],0)
    def test_mode_failure_is_rejected_not_promoted(self):
        e=universal(); e["mode"]="ABSOLUTE_DOMINANCE"; e["result"]={"direction":"higher","brain_lower_bound":1,"theoretical_upper_bound":1}
        out=analyze_documents(cut(),[("canonical/governance/abs.json","1"*40,{"predicate_id":O1,"e":e})])
        self.assertEqual(out["candidate_obligation_count"],0)
        self.assertTrue(any("ABSOLUTE_SCOPE_COMPLETENESS_MISSING" in r["reasons"] for r in out["rejections"]))
    def test_duplicate_object_is_deduplicated(self):
        e=universal()
        out=analyze_documents(cut(),[("canonical/evidence/dup.json","2"*40,{"target_predicate":O1,"a":e,"b":deepcopy(e)})])
        self.assertEqual(out["transmutation_candidate_count"],1)
    def test_bad_current_cut_fails_closed(self):
        bad=cut(); bad["current_partition"]["active_o_rows"]=99
        with self.assertRaisesRegex(ValueError,"CURRENT_O_COUNT_MISMATCH"): analyze_documents(bad,[])

if __name__=="__main__": unittest.main(verbosity=2)
