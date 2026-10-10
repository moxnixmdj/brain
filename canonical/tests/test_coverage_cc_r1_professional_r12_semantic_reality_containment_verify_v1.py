from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import coverage_cc_r1_professional_r12_semantic_reality_containment_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]
def load(path):return json.loads((ROOT/path).read_text())
def docs():
 return {
  "frozen":load(v.CLAIM_PATH),"certificate":load(v.CERT_PATH),
  "domain":load(v.DOMAIN_PATH),"scope":load(v.SCOPE_PATH),
  "identity":load(v.IDENTITY_PATH),"identity_activation":load(v.IDENTITY_ACTIVATION_PATH),
  "mission":load(v.MISSION_PATH),
 }

class Tests(unittest.TestCase):
 def ev(self,d,active=None):
  return v.evaluate_documents(
   frozen=d["frozen"],certificate=d["certificate"],domain=d["domain"],scope=d["scope"],
   identity=d["identity"],identity_activation=d["identity_activation"],mission=d["mission"],
   active_claim=active or d["frozen"],root_id=v.ROOT_ID,
  )
 def test_exact_current_claim_passes_cc_r1_only(self):
  o=v.verify_certificate(root=ROOT,certificate_path=ROOT/v.CERT_PATH,active_claim=load(v.CLAIM_PATH),root_id=v.ROOT_ID)
  self.assertTrue(o["pass"],o);self.assertTrue(o["b_real_subseteq_b_plus"])
  self.assertTrue(o["cc_r1_reality_containment_authority"])
  self.assertFalse(o["r12_semantic_property_truth_authority"]);self.assertFalse(o["terminal_authority"])
 def test_claim_id_drift_fails_closed(self):
  d=docs();a=deepcopy(d["frozen"]);a["claim_id"]="0"*64
  self.assertIn("ACTIVE_CLAIM_CORE_DRIFT:claim_id",self.ev(d,a)["errors"])
 def test_domain_filter_narrowing_fails_closed(self):
  d=docs();d["frozen"]["claim_scope"]["scope_definition"]["domain_definition"]["filters"]=["EASY_ONLY"]
  self.assertIn("WHOLE_DOMAIN_FILTER_NARROWING",self.ev(d)["errors"])
 def test_domain_exclusion_narrowing_fails_closed(self):
  d=docs();d["certificate"]["b_plus_model"]["exclusions"]=["UNKNOWN_CASES"]
  self.assertIn("BPLUS_EXCLUSION_NARROWING",self.ev(d)["errors"])
 def test_finite_sample_substitution_fails_closed(self):
  d=docs();d["identity"]["theorem"]["finite_witness_set_used"]=True
  self.assertIn("FINITE_WITNESS_REALITY_NARROWING",self.ev(d)["errors"])
 def test_information_loss_fails_closed(self):
  d=docs();d["identity"]["theorem"]["semantic_information_loss"]=True
  self.assertIn("IDENTITY_CARRIER_INFORMATION_LOSS",self.ev(d)["errors"])
 def test_unknown_top_semantics_cannot_be_removed(self):
  d=docs();d["certificate"]["b_plus_model"]["semantics"]=[
   x for x in d["certificate"]["b_plus_model"]["semantics"] if not x.startswith("UNRESOLVED_OR_UNKNOWN_VALUES")
  ]
  self.assertIn("BPLUS_TOP_SEMANTICS_INCOMPLETE",self.ev(d)["errors"])
 def test_certificate_cannot_self_grant_property_truth(self):
  d=docs();d["certificate"]["r12_semantic_property_truth_authority"]=True
  self.assertIn("CERTIFICATE_SELF_AUTHORITY_FORBIDDEN:r12_semantic_property_truth_authority",self.ev(d)["errors"])
 def test_scope_batch_property_self_promotion_fails_closed(self):
  d=docs();d["scope"]["independent_replay"]["property_truth_count"]=1
  self.assertIn("SCOPE_BATCH_SELF_PROMOTION",self.ev(d)["errors"])

if __name__=="__main__":unittest.main(verbosity=2)
