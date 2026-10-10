from copy import deepcopy
import unittest
from canonical.runtime import professional_quality_r5_root_subject_binding_verify_v1 as v
class R5V7BindingTests(unittest.TestCase):
 def _docs(self):
  root=v.Path(__file__).resolve().parents[2]
  b,e=v._read(root,v.BINDING_PATH,v.BINDING_BLOB); self.assertIsNone(e)
  s,e=v._read(root,v.SUBJECT_PATH,v.SUBJECT_BLOB); self.assertIsNone(e)
  docs={}
  for k,(p,h) in v.REFS.items():
   d,e=v._read(root,p,h); self.assertIsNone(e); docs[k]=d
  return b,s,docs
 def test_current_binding_passes(self):
  out=v.verify(); self.assertTrue(out["pass"],out); self.assertTrue(out["root_subject_binding_authority"]); self.assertFalse(out["true_current_owner_evaluator_containment_proved"]); self.assertFalse(out["quality_authority"])
 def test_wrong_subject_fails(self):
  b,s,d=self._docs(); b=deepcopy(b); b["subject_sha256"]="bad"; self.assertEqual(v.evaluate_documents(b,s,d)["reason"],"SUBJECT_TUPLE_MISMATCH")
 def test_evaluation_step_must_be_proof_bound(self):
  b,s,d=self._docs(); d=deepcopy(d); d["proof_bound_step_verification"]["formerly_self_attested_steps"]=[]; self.assertEqual(v.evaluate_documents(b,s,d)["reason"],"EVALUATION_STEP_NOT_PROOF_BOUND")
 def test_public_rubric_laundering_fails(self):
  b,s,d=self._docs(); d=deepcopy(d); d["evaluator_uncertainty_governance"]["soundness_firewall"]["forbidden_as_semantic_containment_proof"]=[]; self.assertEqual(v.evaluate_documents(b,s,d)["reason"],"EVALUATOR_FIREWALL_INSUFFICIENT")
 def test_owner_containment_overclaim_fails(self):
  b,s,d=self._docs(); b=deepcopy(b); b["true_current_owner_evaluator_containment_proved"]=True; self.assertEqual(v.evaluate_documents(b,s,d)["reason"],"OWNER_EVALUATOR_CONTAINMENT_OVERCLAIM")
 def test_candidate_cannot_self_authorize(self):
  b,s,d=self._docs(); b=deepcopy(b); b["root_subject_binding_authority"]=True; self.assertEqual(v.evaluate_documents(b,s,d)["reason"],"BINDING_SELF_AUTHORITY_FORBIDDEN")
if __name__=="__main__":unittest.main()
