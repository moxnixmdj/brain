from __future__ import annotations
import json, shutil
from pathlib import Path
import tempfile, unittest
from canonical.runtime import coverage_cc_r1_professional_r12_semantic_reality_containment_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]
FILES=[v.CERT]+[x[0] for x in v.PINS.values()]
class Tests(unittest.TestCase):
 def temp(self):
  td=Path(tempfile.mkdtemp())
  for rel in FILES:
   p=td/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
  return td
 def test_current_passes(self):
  o=v.verify();self.assertTrue(o["pass"],o);self.assertTrue(o["b_real_subseteq_b_plus"]);self.assertFalse(o["property_truth_implied"])
 def test_domain_narrowing_fails(self):
  td=self.temp();p=td/v.PINS["claim"][0];j=json.loads(p.read_text());j["claim_scope"]["scope_definition"]["domain_definition"]["filters"]=["EASY_ONLY"];p.write_text(json.dumps(j));o=v.verify(repo_root=td);self.assertFalse(o["pass"]);self.assertIn("CLAIM_BLOB_MISMATCH",o["errors"])
 def test_identity_claim_substitution_fails(self):
  td=self.temp();p=td/v.PINS["identity"][0];j=json.loads(p.read_text());j["independent_replay"]["r12_claim_id"]="0"*64;p.write_text(json.dumps(j));o=v.verify(repo_root=td);self.assertFalse(o["pass"]);self.assertIn("IDENTITY_BLOB_MISMATCH",o["errors"])
 def test_certificate_property_overclaim_fails(self):
  td=self.temp();p=td/v.CERT;j=json.loads(p.read_text());j["theorem"]["property_truth_implied"]=True;p.write_text(json.dumps(j));o=v.verify(repo_root=td);self.assertFalse(o["pass"]);self.assertIn("PROPERTY_TRUTH_OVERCLAIM",o["errors"])
 def test_compressed_bplus_fails(self):
  td=self.temp();p=td/v.CERT;j=json.loads(p.read_text());j["b_plus_model"]["compression_applied"]=True;p.write_text(json.dumps(j));o=v.verify(repo_root=td);self.assertFalse(o["pass"]);self.assertIn("B_PLUS_COMPRESSION_FORBIDDEN",o["errors"])
if __name__=="__main__":unittest.main(verbosity=2)
