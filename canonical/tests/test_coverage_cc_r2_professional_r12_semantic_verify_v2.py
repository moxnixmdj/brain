from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime import coverage_cc_r2_professional_r12_semantic_verify_v2 as v

ROOT=Path(__file__).resolve().parents[2]
CERT=ROOT/"canonical/governance/COVERAGE_CC_R2_PROFESSIONAL_R12_SEMANTIC_CERTIFICATE_20261010_V2.json"
CLAIM=ROOT/"canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V2.json"

def claim():return json.loads(CLAIM.read_text(encoding="utf-8"))
def run(doc):
 with tempfile.NamedTemporaryFile("w",suffix=".json",encoding="utf-8",delete=False) as f:
  json.dump(doc,f);p=Path(f.name)
 try:return v.verify_certificate(root=ROOT,certificate_path=p,active_claim=claim(),root_id=v.ROOT_ID)
 finally:p.unlink(missing_ok=True)

class Tests(unittest.TestCase):
 def test_current_exact_certificate_passes(self):
  o=v.verify_certificate(root=ROOT,certificate_path=CERT,active_claim=claim(),root_id=v.ROOT_ID)
  self.assertTrue(o["pass"],o);self.assertTrue(o["g_minus_subseteq_g_real"])
  self.assertFalse(o["global_mission_completion_derivable"]);self.assertEqual(o["terminal_credit_delta"],0)
 def test_wrong_claim_fails(self):
  c=claim();c["claim_id"]="0"*64
  o=v.verify_certificate(root=ROOT,certificate_path=CERT,active_claim=c,root_id=v.ROOT_ID)
  self.assertFalse(o["pass"]);self.assertIn("ACTIVE_CLAIM_ID_MISMATCH",o["errors"])
 def test_unauthorized_axiom_drift_fails(self):
  d=json.loads(CERT.read_text());d["authorized_mission_axioms"]["M_VERIFY"]["exact_value"]="WEAKER"
  o=run(d);self.assertFalse(o["pass"]);self.assertIn("CERTIFICATE_M_VERIFY_BINDING_DRIFT",o["errors"])
 def test_reduction_coverage_drop_fails(self):
  d=json.loads(CERT.read_text());d["reduction"]=d["reduction"][:-1]
  o=run(d);self.assertFalse(o["pass"]);self.assertIn("REDUCTION_SHAPE_INVALID",o["errors"])
 def test_property_truth_overclaim_fails(self):
  d=json.loads(CERT.read_text());d["theorem"]["r12_semantic_property_truth_implied"]=True
  o=run(d);self.assertFalse(o["pass"]);self.assertIn("THEOREM_OVERCLAIM:r12_semantic_property_truth_implied",o["errors"])

if __name__=="__main__":unittest.main(verbosity=2)
