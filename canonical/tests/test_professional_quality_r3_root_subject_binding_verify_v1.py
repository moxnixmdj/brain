from copy import deepcopy
import unittest
from canonical.runtime import professional_quality_r3_root_subject_binding_verify_v1 as v

class R3V7BindingTests(unittest.TestCase):
    def _docs(self):
        root=v.Path(__file__).resolve().parents[2]
        b,e=v._read(root,v.BINDING_PATH,v.BINDING_BLOB); self.assertIsNone(e)
        s,e=v._read(root,v.SUBJECT_PATH,v.SUBJECT_BLOB); self.assertIsNone(e)
        docs={}
        for k,(p,h) in v.REFS.items():
            d,e=v._read(root,p,h); self.assertIsNone(e); docs[k]=d
        return b,s,docs

    def test_current_binding_passes(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["root_subject_binding_authority"])
        self.assertFalse(out["real_task_step_receipt_proved"])
        self.assertFalse(out["global_r3_root_closed"])

    def test_wrong_subject_fails(self):
        b,s,d=self._docs(); b=deepcopy(b); b["subject_sha256"]="bad"
        self.assertEqual(v.evaluate_documents(b,s,d)["reason"],"SUBJECT_TUPLE_MISMATCH")

    def test_render_step_must_be_proof_bound(self):
        b,s,d=self._docs(); d=deepcopy(d)
        d["proof_bound_step_verification"]["formerly_self_attested_steps"]=[]
        self.assertEqual(v.evaluate_documents(b,s,d)["reason"],"RENDER_STEP_NOT_PROOF_BOUND")

    def test_scope_widening_fails(self):
        b,s,d=self._docs(); d=deepcopy(d)
        d["r3_semantic_scope"]["limitations"]=[x for x in d["r3_semantic_scope"]["limitations"] if x!="NO_ARBITRARY_SEMANTIC_TARGET_SELECTION"]
        self.assertEqual(v.evaluate_documents(b,s,d)["reason"],"R3_SCOPE_LIMITATION_MISSING")

    def test_public_render_verification_must_succeed(self):
        b,s,d=self._docs(); d=deepcopy(d)
        d["native_render_public_verification"]["independent_public_runner"]["conclusion"]="failure"
        self.assertEqual(v.evaluate_documents(b,s,d)["reason"],"NATIVE_PUBLIC_VERIFY_NOT_SUCCESS")

    def test_candidate_cannot_self_authorize(self):
        b,s,d=self._docs(); b=deepcopy(b); b["root_subject_binding_authority"]=True
        self.assertEqual(v.evaluate_documents(b,s,d)["reason"],"BINDING_SELF_AUTHORITY_FORBIDDEN")

if __name__=="__main__": unittest.main()
