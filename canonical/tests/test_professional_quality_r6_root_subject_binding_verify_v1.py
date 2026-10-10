from copy import deepcopy
import unittest
from canonical.runtime import professional_quality_r6_root_subject_binding_verify_v1 as v

class R6V7BindingTests(unittest.TestCase):
 def _docs(self):
  root=v.Path(__file__).resolve().parents[2]
  b,e=v._read(root,v.BINDING_PATH,v.BINDING_BLOB); self.assertIsNone(e)
  s,e=v._read(root,v.SUBJECT_PATH,v.SUBJECT_BLOB); self.assertIsNone(e)
  docs={}
  for k,(p,h) in v.REFS.items():
   d,e=v._read(root,p,h); self.assertIsNone(e); docs[k]=d
  sr=v.scoped.evaluate(registry_path=root/v.REFS["scoped_registry"][0],repo_root=root)
  return b,s,docs,sr
 def test_current_binding_passes(self):
  out=v.verify(); self.assertTrue(out["pass"],out); self.assertEqual(out["admitted_scoped_capability_count"],21); self.assertTrue(out["global_leaf_registry_empty"]); self.assertFalse(out["global_leaf_closure"])
 def test_wrong_subject_fails(self):
  b,s,d,sr=self._docs(); b=deepcopy(b); b["subject_sha256"]="bad"; self.assertEqual(v.evaluate_documents(b,s,d,sr)["reason"],"SUBJECT_TUPLE_MISMATCH")
 def test_rejected_scoped_evidence_fails(self):
  b,s,d,sr=self._docs(); sr=deepcopy(sr); sr["pass"]=False; sr["rejected_scope_count"]=1; self.assertEqual(v.evaluate_documents(b,s,d,sr)["reason"],"SCOPED_EVIDENCE_VALIDATION_NOT_PASS")
 def test_missing_root_fails(self):
  b,s,d,sr=self._docs(); sr=deepcopy(sr); sr["admitted_scopes"]=[x for x in sr["admitted_scopes"] if x["root_id"]!="R12_META_COMPOSITION_CLOSURE"]; sr["admitted_scope_count"]=len(sr["admitted_scopes"]); self.assertEqual(v.evaluate_documents(b,s,d,sr)["reason"],"SCOPED_EVIDENCE_COUNT_MISMATCH")
 def test_global_leaf_promotion_fails(self):
  b,s,d,sr=self._docs(); d=deepcopy(d); d["leaf_registry"]["leaf_receipts"]={"X":[]}; self.assertEqual(v.evaluate_documents(b,s,d,sr)["reason"],"GLOBAL_LEAF_REGISTRY_NOT_EMPTY")
 def test_candidate_cannot_self_authorize(self):
  b,s,d,sr=self._docs(); b=deepcopy(b); b["root_subject_binding_authority"]=True; self.assertEqual(v.evaluate_documents(b,s,d,sr)["reason"],"BINDING_SELF_AUTHORITY_FORBIDDEN")
if __name__=="__main__":unittest.main()
