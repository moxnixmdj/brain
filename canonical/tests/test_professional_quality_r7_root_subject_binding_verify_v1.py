from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r7_root_subject_binding_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class R7V7BindingTests(unittest.TestCase):
    def subjects(self):
        b=load(v.BINDING_PATH)
        s=load(v.SUBJECT_PATH)
        d={k:load(p) for k,(p,_sha) in v.REFS.items()}
        return b,s,d

    def test_positive_exact_current_subject(self):
        b,s,d=self.subjects()
        out=v.evaluate_documents(b,s,d)
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["root_subject_binding_authority"])
        self.assertFalse(out["global_r7_root_closed"])
        self.assertFalse(out["multi_edit_attribution_proved"])

    def test_wrong_subject_tuple_fails_closed(self):
        b,s,d=self.subjects(); b=deepcopy(b); b["subject_sha256"]="bad"
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"SUBJECT_TUPLE_MISMATCH")

    def test_missing_repaired_component_fails_closed(self):
        b,s,d=self.subjects(); s=deepcopy(s)
        s["system_material"]["components"]=[x for x in s["system_material"]["components"] if x.get("path")!=v.REPAIRED_RUNTIME_PATH]
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"REPAIRED_CAUSAL_TARGET_NOT_IN_V7_SUBJECT")

    def test_scope_widening_fails_closed(self):
        b,s,d=self.subjects(); d=deepcopy(d)
        d["causal_scope"]["semantics"]["global_r7_root_closed"]=True
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"CAUSAL_SCOPE_WIDENING_FORBIDDEN")

    def test_fail_to_pass_signature_corruption_fails_closed(self):
        b,s,d=self.subjects(); d=deepcopy(d)
        d["causal_instance"]["real_execution"]["predecessor_result"]["outcome"]="PASS"
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"FAIL_TO_PASS_CAUSAL_SIGNATURE_MISSING")

    def test_binding_self_authority_fails_closed(self):
        b,s,d=self.subjects(); b=deepcopy(b); b["root_subject_binding_authority"]=True
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"BINDING_SELF_AUTHORITY_FORBIDDEN")

if __name__=="__main__":
    unittest.main(verbosity=2)
