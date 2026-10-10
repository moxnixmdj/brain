import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
from canonical.runtime import professional_semantic_contract_truth_repair_verify_v1 as v
ROOT=Path(__file__).resolve().parents[2]
class Tests(unittest.TestCase):
 def test_exact_successor_diff_passes(self):
  o=v.verify(root=ROOT);self.assertTrue(o["pass"],o);self.assertEqual(o["repaired_semantic_leaf_count"],12)
 def test_zero_authority(self):
  o=v.verify(root=ROOT);self.assertFalse(o["leaf_property_truth_authority"]);self.assertEqual(o["terminal_credit_delta"],0)
 def test_root_contract_mutation_fails(self):
  p=ROOT/v.NEW_PATH;doc=json.loads(p.read_text());doc["roots"][0]["contract"]+="X"
  tmp=ROOT/"tmp_manifest_bad.json";tmp.write_text(json.dumps(doc))
  with patch.object(v,"NEW_PATH","tmp_manifest_bad.json"):
   self.assertFalse(v.verify(root=ROOT)["pass"])
  tmp.unlink()
 def test_execution_mutation_fails(self):
  p=ROOT/v.NEW_PATH;doc=json.loads(p.read_text());doc["roots"][0]["execution_leaf"]["acceptance"]="WEAK"
  tmp=ROOT/"tmp_manifest_bad2.json";tmp.write_text(json.dumps(doc))
  with patch.object(v,"NEW_PATH","tmp_manifest_bad2.json"):
   self.assertFalse(v.verify(root=ROOT)["pass"])
  tmp.unlink()
 def test_semantic_obligation_mutation_fails(self):
  p=ROOT/v.NEW_PATH;doc=json.loads(p.read_text());doc["roots"][0]["semantic_leaf"]["obligation"]="WEAK"
  tmp=ROOT/"tmp_manifest_bad3.json";tmp.write_text(json.dumps(doc))
  with patch.object(v,"NEW_PATH","tmp_manifest_bad3.json"):
   self.assertFalse(v.verify(root=ROOT)["pass"])
  tmp.unlink()
if __name__=="__main__":unittest.main(verbosity=2)
