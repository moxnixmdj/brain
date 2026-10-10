from __future__ import annotations
import copy,json,shutil,tempfile,unittest
from pathlib import Path
from canonical.runtime import professional_r12_semantic_cc_r3_contract_decomposition_v1 as v
ROOT=Path(__file__).resolve().parents[2]
class T(unittest.TestCase):
 def tmp(self):
  td=Path(tempfile.mkdtemp())
  for rel in [v.CAND,v.CLAIM]:
   p=td/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
  return td
 def test_current_exact_eight_clause_decomposition(self):
  o=v.evaluate();self.assertTrue(o["pass"],o);self.assertEqual(o["clause_count"],8);self.assertFalse(o["cc_r3_terminal_closure"])
 def test_missing_clause_fails(self):
  td=self.tmp();p=td/v.CAND;j=json.loads(p.read_text());j["clauses"]=j["clauses"][:-1];p.write_text(json.dumps(j));self.assertFalse(v.evaluate(root=td)["pass"])
 def test_reordered_clause_fails(self):
  td=self.tmp();p=td/v.CAND;j=json.loads(p.read_text());j["clauses"][0],j["clauses"][1]=j["clauses"][1],j["clauses"][0];p.write_text(json.dumps(j));self.assertFalse(v.evaluate(root=td)["pass"])
 def test_contract_text_drift_fails(self):
  td=self.tmp();p=td/v.CLAIM;j=json.loads(p.read_text());j["claim_scope"]["scope_definition"]["domain_definition"]["root_contract"]+=" Extra.";p.write_text(json.dumps(j));self.assertFalse(v.evaluate(root=td)["pass"])
 def test_decomposition_cannot_self_promote_cc_r3(self):
  td=self.tmp();p=td/v.CAND;j=json.loads(p.read_text());j["semantic_property_truth_authority"]=True;p.write_text(json.dumps(j));self.assertFalse(v.evaluate(root=td)["pass"])
if __name__=="__main__":unittest.main(verbosity=2)
