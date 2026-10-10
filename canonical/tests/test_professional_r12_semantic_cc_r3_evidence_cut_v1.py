from __future__ import annotations
import copy, json
from pathlib import Path
import unittest
from canonical.runtime import professional_r12_semantic_cc_r3_evidence_cut_v1 as c

ROOT=Path(__file__).resolve().parents[2]
PATHS={
 "decomposition":"canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_CONTRACT_DECOMPOSITION_20261010_V1.json",
 "composition_verify":"canonical/verification/PROFESSIONAL_QUALITY_V7_12_OF_12_COMPOSITION_INDEPENDENT_VERIFY_20261010_V1.json",
 "identity_verify":"canonical/verification/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_VERIFY_20261010_V1.json",
 "domain_verify":"canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V1_INDEPENDENT_VERIFY_20261010_V1.json",
 "scope_verify":"canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json",
 "defeater_replay":"canonical/verification/PROFESSIONAL_QUALITY_80_DEFEATER_UVCK_REPLAY_VERIFY_20261009_V1.json",
 "challenge_verify":"canonical/verification/UVCK_V2_DOMAIN_CHALLENGE_VERIFY_20261009_V1.json",
 "root_theorem":"canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json",
 "r12_execution_verify":"canonical/verification/PROFESSIONAL_QUALITY_R12_EXECUTION_PROPERTY_TRUTH_INDEPENDENT_VERIFY_20261010_V1.json",
 "cc_r2_verify":"canonical/verification/COVERAGE_CC_R2_PROFESSIONAL_R12_SEMANTIC_VERIFY_20261010_V1.json",
}
def docs():
 return {k:json.loads((ROOT/p).read_text()) for k,p in PATHS.items()}
def run(d=None):
 return c.analyze(**(d or docs()))

class CutTests(unittest.TestCase):
 def test_current_cut(self):
  out=run();self.assertTrue(out["pass"],out)
  self.assertEqual(out["verified_clause_count"],5)
  self.assertEqual(out["partial_clause_count"],3)
  self.assertEqual(out["open_clause_count"],0)
  self.assertFalse(out["cc_r3_terminal_closure"])
  self.assertFalse(out["semantic_property_truth_authority"])
  self.assertEqual(
   [x["clause_id"] for x in out["clauses"] if x["state"]=="PARTIAL_EXISTING_EVIDENCE"],
   ["R12C1_ASSUMPTION_GUARANTEE_COMPOSITION","R12C3_ABSTRACTION_SOUNDNESS","R12C8_NONVACUITY"],
  )
  self.assertEqual(out["stronger_target_residual"]["state"],"OPEN")
 def test_cc_r2_soundness_rule_does_not_prove_nonvacuity_existence(self):
  out=run();self.assertTrue(out["pass"],out)
  rows={x["clause_id"]:x for x in out["clauses"]}
  self.assertEqual(rows["R12C8_NONVACUITY"]["state"],"PARTIAL_EXISTING_EVIDENCE")
  self.assertIn("REAL_SUPPORTED_POSITIVE_R12_SEMANTIC_CERTIFICATION_ROUTE",rows["R12C8_NONVACUITY"]["remaining"])
  self.assertFalse(out["cc_r3_terminal_closure"])
 def test_known_defeaters_cannot_self_promote_to_completeness(self):
  d=docs();d["defeater_replay"]=copy.deepcopy(d["defeater_replay"])
  d["defeater_replay"]["hard_nonclaims"]=[x for x in d["defeater_replay"]["hard_nonclaims"] if x!="NO_ADVERSARIAL_COMPLETENESS_OF_UNKNOWN_ATTACKS"]
  out=run(d);self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"UNKNOWN_DEFEATER_BOUNDARY_NOT_PRESERVED")
 def test_execution_unknown_completeness_nonclaim_required(self):
  d=docs();d["r12_execution_verify"]=copy.deepcopy(d["r12_execution_verify"])
  d["r12_execution_verify"]["hard_nonclaims"]=[x for x in d["r12_execution_verify"]["hard_nonclaims"] if x!="NO_UNKNOWN_DEFEATER_COMPLETENESS"]
  out=run(d);self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"UNKNOWN_DEFEATER_BOUNDARY_NOT_PRESERVED")
 def test_lossless_decomposition_required(self):
  d=docs();d["decomposition"]=copy.deepcopy(d["decomposition"]);d["decomposition"]["decomposition_claim"]["coverage_complete"]=False
  out=run(d);self.assertFalse(out["pass"]);self.assertEqual(out["reason"],"DECOMPOSITION_NOT_LOSSLESS")
 def test_same_subject_failure_reopens_c2_and_c1(self):
  d=docs();d["composition_verify"]=copy.deepcopy(d["composition_verify"]);d["composition_verify"]["proves"]=[]
  out=run(d);self.assertTrue(out["pass"])
  rows={x["clause_id"]:x for x in out["clauses"]}
  self.assertEqual(rows["R12C1_ASSUMPTION_GUARANTEE_COMPOSITION"]["state"],"OPEN")
  self.assertEqual(rows["R12C2_SAME_SUBJECT_ROOT_CONJUNCTION"]["state"],"OPEN")
if __name__=="__main__":unittest.main(verbosity=2)
