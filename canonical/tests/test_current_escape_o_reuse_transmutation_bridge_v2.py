from __future__ import annotations
import unittest
from canonical.runtime.current_escape_o_reuse_transmutation_bridge_v2 import analyze_documents, CUT_SCHEMA

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

def alias_cut():
    ids=[O1,O2,"HLE_TOOLS_GE_67_7","PROWORK_GDPVAL_GE_1846","MYSTERYMECHANISM_INTRINSIC_OPUS55_NONINFERIORITY_OR_STRONGER"]
    return {"schema":CUT_SCHEMA,"current_partition":{
        "active_o_obligation_ids":ids,
        "active_q_obligation_ids":[Q1],
        "parked_obligation_ids":[P1],
        "active_o_rows":len(ids),"active_q_rows":1,"parked_rows":1,"active_rows":len(ids)+1,"total_escape_rows":len(ids)+2}}

def strict():
    return {"mode":"UNIVERSAL","verified":True,"independent":True,
      "contamination_clean":True,"binds_frozen_protocol":True,"scope_relation":"PROVEN_STRONGER",
      "closes_entire_protocol":True,
      "result":{"all_admissible_inputs_proved":True,"formal_completeness":True}}

class Tests(unittest.TestCase):
    def test_legacy_row_target_is_surfaced_for_adaptation_not_acceptance(self):
        doc={"target_predicate":O1,"status":"PROVED_SCOPED_NONNECESSITY__ZERO_CREDIT",
             "new_primitive_required":False,
             "frontier_effect":{"new_single_primary_burden":"PROVE_THRESHOLD_OR_STRONGER_CERTIFICATE"},
             "hard_nonclaims":["NO_ACCEPTANCE_CREDIT"]}
        out=analyze_documents(cut(),[("canonical/governance/tb4.json","a"*40,doc)])
        self.assertEqual(out["adaptation_candidate_obligation_ids"],[O1])
        self.assertEqual(out["strict_candidate_obligation_ids"],[])
        self.assertEqual(out["reuse_uncovered_obligation_ids"],[O2])
        row=out["legacy_adaptation_inputs"][0]
        self.assertEqual(row["remaining_delta"],["PROVE_THRESHOLD_OR_STRONGER_CERTIFICATE"])
        self.assertFalse(row["acceptance_authority"])
        self.assertFalse(out["acceptance_authority"])

    def test_frozen_predicate_id_is_visible_to_legacy_lane(self):
        out=analyze_documents(cut(),[("canonical/governance/fc.json","b"*40,
            {"frozen_predicate_id":O2,"status":"CANDIDATE__ZERO_CREDIT","next":"SEARCH_EXISTING_WHOLE_CELL_CERTIFICATES"})])
        self.assertEqual(out["adaptation_candidate_obligation_ids"],[O2])

    def test_q_and_parked_legacy_artifacts_never_enter_active_o_reuse(self):
        out=analyze_documents(cut(),[
          ("canonical/governance/q.json","c"*40,{"target_predicate":Q1,"next":"X"}),
          ("canonical/governance/p.json","d"*40,{"target_predicate":P1,"next":"Y"})])
        self.assertEqual(out["adaptation_candidate_obligation_ids"],[])
        self.assertEqual(out["reuse_uncovered_obligation_ids"],sorted([O1,O2]))

    def test_strict_transmutation_candidate_retains_separate_strict_lane(self):
        out=analyze_documents(cut(),[("canonical/governance/x.json","e"*40,
             {"target_predicate":O1,"certificate":strict()})])
        self.assertEqual(out["strict_candidate_obligation_ids"],[O1])
        self.assertEqual(out["adaptation_candidate_obligation_ids"],[])
        self.assertEqual(out["reuse_uncovered_obligation_ids"],[O2])

    def test_text_mentions_do_not_create_legacy_adaptation_context(self):
        out=analyze_documents(cut(),[("canonical/governance/n.json","f"*40,
             {"notes":[O1],"next":"SHOULD_NOT_BIND"})])
        self.assertEqual(out["adaptation_candidate_obligation_ids"],[])


    def test_hle_structured_target_surface_alias_is_adaptation_input(self):
        out=analyze_documents(alias_cut(),[("canonical/governance/hle.json","1"*40,
            {"target_surface":"HUMANITYS_LAST_EXAM","status":"ZERO_CREDIT","theorem":{"x":"y"}})])
        self.assertIn("HLE_TOOLS_GE_67_7",out["adaptation_candidate_obligation_ids"])

    def test_gdpval_structured_scope_alias_is_adaptation_input(self):
        out=analyze_documents(alias_cut(),[("canonical/governance/gdp.json","2"*40,
            {"scope":"CURRENT_GDPVAL_AA_V2_1_PUBLIC_FIXED_BAR_ACCEPTANCE_ROUTE_ONLY","status":"ZERO_CREDIT"})])
        self.assertIn("PROWORK_GDPVAL_GE_1846",out["adaptation_candidate_obligation_ids"])

    def test_mystery_structured_problem_alias_is_adaptation_input(self):
        out=analyze_documents(alias_cut(),[("canonical/governance/mm.json","3"*40,
            {"problem":"MYSTERYMECHANISM_V2_FITS_SPARSE_LINEAR_IN_COEFFICIENT_MODELS","status":"ZERO_CREDIT"})])
        self.assertIn("MYSTERYMECHANISM_INTRINSIC_OPUS55_NONINFERIORITY_OR_STRONGER",out["adaptation_candidate_obligation_ids"])

if __name__=="__main__": unittest.main(verbosity=2)
