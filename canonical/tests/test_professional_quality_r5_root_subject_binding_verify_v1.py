from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r5_root_subject_binding_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class R5V7BindingTests(unittest.TestCase):
    def subjects(self):
        b=load(v.BINDING_PATH)
        s=load(v.SUBJECT_PATH)
        docs={k:load(p) for k,(p,_sha) in v.REFS.items()}
        return b,s,docs

    def test_positive_exact_current_subject(self):
        b,s,d=self.subjects()
        out=v.evaluate_documents(b,s,d)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["root_subject_binding_authority"])
        self.assertFalse(out["true_owner_evaluator_containment_proved"])
        self.assertFalse(out["public_rubric_owner_semantic_authority"])
        self.assertFalse(out["quality_authority"])

    def test_wrong_subject_tuple_fails_closed(self):
        b,s,d=self.subjects(); b=deepcopy(b); b["subject_sha256"]="bad"
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"SUBJECT_TUPLE_MISMATCH")

    def test_comparative_step_not_proof_bound_fails_closed(self):
        b,s,d=self.subjects(); d=deepcopy(d)
        d["proof_bound_step_verification"]["formerly_self_attested_steps"]=[
            x for x in d["proof_bound_step_verification"]["formerly_self_attested_steps"] if x!=v.STEP_ID
        ]
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"COMPARATIVE_EVALUATION_STEP_NOT_PROOF_BOUND")

    def test_owner_containment_self_claim_fails_closed(self):
        b,s,d=self.subjects(); b=deepcopy(b); b["true_owner_evaluator_containment_proved"]=True
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"OWNER_CONTAINMENT_SELF_CLAIM_FORBIDDEN")

    def test_public_rubric_owner_authority_fails_closed(self):
        b,s,d=self.subjects(); b=deepcopy(b); b["public_rubric_owner_semantic_authority"]=True
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"PUBLIC_RUBRIC_AUTHORITY_FORBIDDEN")

    def test_scope_widening_fails_closed(self):
        b,s,d=self.subjects(); b=deepcopy(b)
        b["binding_scope"]["limitations"]=[
            x for x in b["binding_scope"]["limitations"]
            if x!="NO_PROOF_THE_TRUE_CURRENT_OWNER_EVALUATOR_IS_IN_ANY_PROPOSED_DECOMPOSITION"
        ]
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"BINDING_LIMITATIONS_INSUFFICIENT")

if __name__=="__main__":
    unittest.main(verbosity=2)
