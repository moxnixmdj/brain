from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_v7_12_of_12_composition_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def load():
    return json.loads((ROOT/v.WORKLIST).read_text(encoding="utf-8"))

class Tests(unittest.TestCase):
    def test_positive_real_repository_bytes(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["composition_admissible"])
        self.assertEqual(out["verified_root_subject_binding_count"],12)
        self.assertFalse(out["professional_quality_closed"])
        self.assertFalse(out["terminal_authority"])

    def test_missing_root_fails_closed(self):
        w=load();w["roots"]=w["roots"][:-1];w["verified_root_subject_binding_count"]=11
        self.assertEqual(v.evaluate_worklist(w,repo_root=ROOT)["reason"],"VERIFIED_BINDING_COUNT_NOT_12")

    def test_duplicate_root_fails_closed(self):
        w=load();w["roots"][-1]["root_id"]=w["roots"][0]["root_id"]
        self.assertEqual(v.evaluate_worklist(w,repo_root=ROOT)["reason"],"WORKLIST_ROOT_ID_INVALID_OR_DUPLICATE")

    def test_open_root_fails_closed(self):
        w=load();w["roots"][0]["same_subject_binding_status"]="OPEN"
        o=v.evaluate_worklist(w,repo_root=ROOT)
        self.assertEqual(o["reason"],"WORKLIST_ROOT_NOT_VERIFIED")

    def test_missing_receipt_fails_closed(self):
        w=load();w["roots"][0].pop("verification")
        o=v.evaluate_worklist(w,repo_root=ROOT)
        self.assertEqual(o["reason"],"WORKLIST_BINDING_REFERENCE_MISSING")

    def test_gate_failure_is_not_promoted(self):
        w=load();old=v.gate.evaluate
        try:
            v.gate.evaluate=lambda *a,**k:{"pass":False,"status":"FAIL_CLOSED"}
            self.assertEqual(v.evaluate_worklist(w,repo_root=ROOT)["reason"],"COMPOSITION_GATE_NOT_PASS")
        finally:v.gate.evaluate=old

    def test_gate_overclaim_is_rejected(self):
        w=load();old=v.gate.evaluate
        try:
            v.gate.evaluate=lambda *a,**k:{
                "pass":True,
                "status":"PASS__SAME_SUBJECT_ROOT_COMPOSITION_ADMISSIBLE",
                "composition_admissible":True,
                "verified_root_subject_binding_count":12,
                "composed_subject":{"subject_kind":v.SUBJECT_KIND,"subject_id":v.SUBJECT_ID,"subject_sha256":v.SUBJECT_SHA},
                "professional_quality_closed":True,
                "semantic_truth_authority":False,
                "execution_authority":False,
                "quality_authority":False,
                "acceptance_authority":False,
                "promotion_authority":False,
                "terminal_authority":False,
            }
            self.assertEqual(v.evaluate_worklist(w,repo_root=ROOT)["reason"],"GATE_OVERCLAIM:professional_quality_closed")
        finally:v.gate.evaluate=old

if __name__=="__main__":
    unittest.main(verbosity=2)
