from __future__ import annotations
from copy import deepcopy
import json,tempfile,unittest
from pathlib import Path

from canonical.runtime import coverage_cc_r1_professional_r12_semantic_verify_v2 as v

ROOT=Path(__file__).resolve().parents[2]
CERT=ROOT/"canonical/governance/COVERAGE_CC_R1_PROFESSIONAL_R12_SEMANTIC_CERTIFICATE_20261010_V2.json"
CLAIM=ROOT/"canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V2.json"

def claim():
 return json.loads(CLAIM.read_text(encoding="utf-8"))

def run_cert(doc):
 with tempfile.NamedTemporaryFile("w",suffix=".json",encoding="utf-8",delete=False) as f:
  json.dump(doc,f);p=Path(f.name)
 try:return v.verify_certificate(root=ROOT,certificate_path=p,active_claim=claim(),root_id=v.ROOT_ID)
 finally:p.unlink(missing_ok=True)

class Tests(unittest.TestCase):
 def test_current_exact_certificate_passes(self):
  o=v.verify_certificate(root=ROOT,certificate_path=CERT,active_claim=claim(),root_id=v.ROOT_ID)
  self.assertTrue(o["pass"],o)
  self.assertTrue(o["b_real_subseteq_b_plus"])
  self.assertFalse(o["property_truth_implied"])
  self.assertEqual(o["terminal_credit_delta"],0)

 def test_wrong_active_claim_fails(self):
  c=claim();c["claim_id"]="0"*64
  o=v.verify_certificate(root=ROOT,certificate_path=CERT,active_claim=c,root_id=v.ROOT_ID)
  self.assertFalse(o["pass"])
  self.assertIn("ACTIVE_CLAIM_ID_MISMATCH",o["errors"])

 def test_identity_carrier_ref_drift_fails(self):
  d=json.loads(CERT.read_text());d["identity_carrier"]["git_blob_sha"]="0"*40
  o=run_cert(d)
  self.assertFalse(o["pass"])
  self.assertTrue(any("IDENTITY_CARRIER" in x for x in o["errors"]))

 def test_authority_overclaim_fails(self):
  d=json.loads(CERT.read_text());d["semantic_truth_authority"]=True
  o=run_cert(d)
  self.assertFalse(o["pass"])
  self.assertIn("CERTIFICATE_AUTHORITY_OVERCLAIM:semantic_truth_authority",o["errors"])

if __name__=="__main__":unittest.main(verbosity=2)
