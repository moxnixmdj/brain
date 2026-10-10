from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r6_root_subject_binding_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

class R6V7BindingTests(unittest.TestCase):
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
        self.assertFalse(out["global_evidence_completeness_proved"])
        self.assertFalse(out["quality_authority"])

    def test_wrong_subject_tuple_fails_closed(self):
        b,s,d=self.subjects(); b=deepcopy(b); b["subject_sha256"]="bad"
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"SUBJECT_TUPLE_MISMATCH")

    def test_missing_subject_evidence_component_fails_closed(self):
        b,s,d=self.subjects(); s=deepcopy(s)
        comps=s["system_material"]["components"]
        s["system_material"]["components"]=[x for x in comps if x.get("path")!="canonical/runtime/professional_quality_leaf_binder_v2.py"]
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"REQUIRED_EVIDENCE_COMPONENTS_NOT_IN_SUBJECT")

    def test_scope_widening_fails_closed(self):
        b,s,d=self.subjects(); d=deepcopy(d)
        row=next(x for x in d["scoped_evidence_registry"]["entries"] if x.get("root_id")==v.ROOT_ID)
        row["global_root_closure"]=True
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"R6_SCOPE_WIDENING_FORBIDDEN")

    def test_status_string_authority_fails_closed(self):
        b,s,d=self.subjects(); b=deepcopy(b); b["evidence_status_string_authority"]=True
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"STATUS_STRING_AUTHORITY_FORBIDDEN")

    def test_leaf_admission_law_drift_fails_closed(self):
        b,s,d=self.subjects(); d=deepcopy(d)
        d["leaf_evidence_registry"]["admission_law"]="manifest status decides everything"
        out=v.evaluate_documents(b,s,d)
        self.assertFalse(out["pass"]); self.assertEqual(out["reason"],"LEAF_ADMISSION_LAW_MISSING")

if __name__=="__main__":
    unittest.main(verbosity=2)
