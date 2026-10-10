from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
from canonical.runtime import systemic_bank_hla_necessary_property_authority_v1 as hla

ROOT=Path(__file__).resolve().parents[2]

def req(c,p):
 return {"schema":hla.REQUEST_SCHEMA,"scope_id":hla.SCOPE_ID,"concept_id":c,"property_id":p}

def fake(pack):
 return {"pass":True,"receipt":{"fragment_ids":sorted(str(x["fragment_id"]) for x in pack.get("fragments",[])),"receipt_sha256":"a"*64}}

class Tests(unittest.TestCase):
 def test_gsib_loss_absorption_going_concern_cet1(self):
  for p in ("FUNCTION::LOSS_ABSORPTION","DISPOSITION::LOSS_ABSORPTION","REGIME::GOING_CONCERN","COMPOSITION::CET1","SCOPE::G_SIB"):
   out=hla.verify_property_request(req(hla.GSIB_HLA,p),repo_root=ROOT,projection_verifier=fake)
   self.assertTrue(out["pass"],(p,out))
   self.assertFalse(out["reverse_inference_authorized"])
 def test_gsib_extends_ccob(self):
  out=hla.verify_property_request(req(hla.GSIB_HLA,"RELATION::EXTENDS_CCOB"),repo_root=ROOT,projection_verifier=fake)
  self.assertTrue(out["pass"],out)
 def test_dsib_loss_absorption_cet1_scope(self):
  for p in ("FUNCTION::LOSS_ABSORPTION","DISPOSITION::LOSS_ABSORPTION","COMPOSITION::CET1","SCOPE::D_SIB"):
   out=hla.verify_property_request(req(hla.DSIB_HLA,p),repo_root=ROOT,projection_verifier=fake)
   self.assertTrue(out["pass"],(p,out))
 def test_dsib_extends_ccob_and_systemic_calibration(self):
  for p in ("RELATION::EXTENDS_CCOB","CALIBRATION::COMMENSURATE_SYSTEMIC_IMPORTANCE"):
   out=hla.verify_property_request(req(hla.DSIB_HLA,p),repo_root=ROOT,projection_verifier=fake)
   self.assertTrue(out["pass"],(p,out))
 def test_dsib_going_concern_is_unknown_not_inferred(self):
  out=hla.verify_property_request(req(hla.DSIB_HLA,"REGIME::GOING_CONCERN"),repo_root=ROOT,projection_verifier=fake)
  self.assertFalse(out["pass"]);self.assertEqual(out["status"],"UNKNOWN__PROPERTY_NOT_PROVED_IN_BOUND_SCOPE")
  self.assertFalse(out["absence_means_false"])
 def test_reverse_request_does_not_classify(self):
  out=hla.verify_property_request(req("DISPOSITION::LOSS_ABSORPTION",hla.GSIB_HLA),repo_root=ROOT,projection_verifier=fake)
  self.assertFalse(out["pass"]);self.assertFalse(out["reverse_inference_authorized"])
 def test_source_failure_fails_closed(self):
  out=hla.verify_property_request(req(hla.GSIB_HLA,"COMPOSITION::CET1"),repo_root=ROOT,projection_verifier=lambda _:{"pass":False})
  self.assertFalse(out["pass"]);self.assertEqual(out["status"],"FAIL_CLOSED")
 def test_pack_drift_fails_closed(self):
  doc=json.loads((ROOT/hla.PACK_PATH).read_text())
  doc["scope_id"]+="-tampered"
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);target=root/hla.PACK_PATH;target.parent.mkdir(parents=True);target.write_text(json.dumps(doc))
   out=hla.verify_property_request(req(hla.GSIB_HLA,"COMPOSITION::CET1"),repo_root=root,projection_verifier=fake)
  self.assertFalse(out["pass"]);self.assertIn("PACK_GIT_BLOB_DRIFT",out["reason"])
 def test_no_terminal_or_identity_authority(self):
  out=hla.verify_property_request(req(hla.GSIB_HLA,"REGIME::GOING_CONCERN"),repo_root=ROOT,projection_verifier=fake)
  self.assertTrue(out["pass"]);self.assertFalse(out["exact_concept_identity_authority"]);self.assertFalse(out["terminal_authority"])
if __name__=="__main__":unittest.main(verbosity=2)
