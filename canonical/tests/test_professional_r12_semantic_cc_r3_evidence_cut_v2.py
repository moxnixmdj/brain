from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_r12_semantic_cc_r3_evidence_cut_v2 as c

ROOT=Path(__file__).resolve().parents[2]
PATHS={
 "decomposition":"canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_CONTRACT_DECOMPOSITION_20261010_V1.json",
 "composition_verify":"canonical/verification/PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_INDEPENDENT_VERIFY_20261010_V1.json",
 "v3_current_verify":"canonical/verification/PROFESSIONAL_SEMANTIC_V3_CURRENT_BYTES_INDEPENDENT_VERIFY_20261010_V1.json",
 "c1_verify":"canonical/verification/PROFESSIONAL_R12_STABLE_C1_INDEPENDENT_VERIFY_20261010_V1.json",
 "c3_verify":"canonical/verification/PROFESSIONAL_R12_C3_LOSSLESS_COMPOSITION_PROJECTION_VERIFY_20261010_V1.json",
 "defeater_replay":"canonical/verification/PROFESSIONAL_QUALITY_80_DEFEATER_UVCK_REPLAY_VERIFY_20261009_V1.json",
 "challenge_verify":"canonical/verification/UVCK_V2_DOMAIN_CHALLENGE_VERIFY_20261009_V1.json",
 "root_theorem":"canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json",
 "r12_execution_verify":"canonical/verification/PROFESSIONAL_QUALITY_R12_EXECUTION_PROPERTY_TRUTH_INDEPENDENT_VERIFY_20261010_V1.json",
 "c8_verify":"canonical/verification/PROFESSIONAL_R12_C8_NONVACUITY_INDEPENDENT_VERIFY_20261010_V1.json",
}
def docs():
 d={k:json.loads((ROOT/p).read_text()) for k,p in PATHS.items()}
 from canonical.runtime import professional_r12_semantic_v3_c5_bridge_v1 as b
 d["c5_bridge"]=b.verify(repo_root=ROOT)
 return d
def run(d=None): return c.analyze(**(d or docs()))

class Tests(unittest.TestCase):
 def test_current_v3_cut_has_all_eight_contract_clauses_verified(self):
  o=run();self.assertTrue(o["pass"],o)
  self.assertEqual((o["verified_clause_count"],o["partial_clause_count"],o["open_clause_count"]),(8,0,0))
  self.assertFalse(o["cc_r3_terminal_closure_proved"])
  self.assertFalse(o["claim_scoped_totality_proved"])
  self.assertFalse(o["semantic_property_truth_authority"])
  self.assertEqual([x["clause_id"] for x in o["clauses"] if x["state"]=="PARTIAL_EXISTING_EVIDENCE"],[])
 def test_c1_current_proof_failure_reopens_c1(self):
  d=docs();d["c1_verify"]=deepcopy(d["c1_verify"]);d["c1_verify"]["c1_assumption_guarantee_composition_proved"]=False
  o=run(d);self.assertTrue(o["pass"]);row=next(x for x in o["clauses"] if x["clause_id"]=="R12C1_ASSUMPTION_GUARANTEE_COMPOSITION")
  self.assertEqual(row["state"],"OPEN");self.assertEqual(o["verified_clause_count"],7)
 def test_c3_current_proof_failure_reopens_c3(self):
  d=docs();d["c3_verify"]=deepcopy(d["c3_verify"]);d["c3_verify"]["proves"]=[]
  o=run(d);self.assertTrue(o["pass"]);row=next(x for x in o["clauses"] if x["clause_id"]=="R12C3_ABSTRACTION_SOUNDNESS")
  self.assertEqual(row["state"],"OPEN");self.assertEqual(o["verified_clause_count"],7)
 def test_current_v3_property_claim_is_required(self):
  d=docs();d["v3_current_verify"]=deepcopy(d["v3_current_verify"]);d["v3_current_verify"]["observed"]["r12_stable_claim_id"]="0"*64
  o=run(d);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"CURRENT_V3_PROPERTY_CLAIM_OR_CARRIER_NOT_VERIFIED")
 def test_c5_bridge_failure_reopens_c5_without_crashing_cut(self):
  d=docs();d["c5_bridge"]=deepcopy(d["c5_bridge"]);d["c5_bridge"]["pass"]=False
  o=run(d);self.assertTrue(o["pass"]);row=next(x for x in o["clauses"] if x["clause_id"]=="R12C5_COVERAGE_ACCOUNTING")
  self.assertEqual(row["state"],"OPEN");self.assertEqual(o["verified_clause_count"],7)
 def test_c8_current_receipt_failure_reopens_c8(self):
  d=docs();d["c8_verify"]=deepcopy(d["c8_verify"]);d["c8_verify"]["truth"]["c8_nonvacuity_proved"]=False
  o=run(d);self.assertTrue(o["pass"]);row=next(x for x in o["clauses"] if x["clause_id"]=="R12C8_NONVACUITY")
  self.assertEqual(row["state"],"OPEN");self.assertEqual(o["verified_clause_count"],7)
 def test_unknown_defeater_completeness_boundary_is_mandatory(self):
  d=docs();d["defeater_replay"]=deepcopy(d["defeater_replay"]);d["defeater_replay"]["hard_nonclaims"]=[]
  o=run(d);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"UNKNOWN_DEFEATER_BOUNDARY_NOT_PRESERVED")
 def test_scope_claim_identity_drift_fails_closed(self):
  d=docs();d["decomposition"]=deepcopy(d["decomposition"]);d["decomposition"]["claim_id"]="0"*64
  o=run(d);self.assertFalse(o["pass"]);self.assertEqual(o["reason"],"DECOMPOSITION_SCOPE_CLAIM_DRIFT")
 def test_v2_property_authority_transport_cannot_enter_through_c5(self):
  d=docs();d["c5_bridge"]=deepcopy(d["c5_bridge"]);d["c5_bridge"]["source_v2_property_authority_transported"]=True
  o=run(d);self.assertTrue(o["pass"]);row=next(x for x in o["clauses"] if x["clause_id"]=="R12C5_COVERAGE_ACCOUNTING")
  self.assertEqual(row["state"],"OPEN")
if __name__=="__main__": unittest.main(verbosity=2)
