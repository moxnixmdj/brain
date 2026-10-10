from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_quality_v7_12_of_12_composition_verify_v1 as v

ROOT=Path(__file__).resolve().parents[2]

def rows():
    d=json.loads((ROOT/v.MANIFEST).read_text(encoding="utf-8"))
    return deepcopy(d["root_subject_bindings"])

class V7CompositionTests(unittest.TestCase):
    def test_real_twelve_of_twelve_composition_passes_without_quality_authority(self):
        out=v.verify()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["composition_admissible"])
        self.assertEqual(out["verified_root_subject_binding_count"],12)
        self.assertFalse(out["professional_quality_closed"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_missing_root_remains_open(self):
        r=rows()[:-1]
        out=v.evaluate_rows(r)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["status"],"OPEN__SAME_SUBJECT_BINDINGS_INCOMPLETE")

    def test_stale_binding_reference_fails_closed(self):
        r=rows();r[0]["binding"]["git_blob_sha"]="0"*40
        out=v.evaluate_rows(r)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["reason"],"SUBJECT_BINDING_BLOB_STALE")

    def test_duplicate_root_fails_closed(self):
        r=rows();r.append(deepcopy(r[0]))
        out=v.evaluate_rows(r)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["reason"],"ROOT_SUBJECT_BINDING_ROOT_DUPLICATE")

    def test_r12_verification_blob_must_match(self):
        r=rows();row=next(x for x in r if x["root_id"]=="R12_META_COMPOSITION_CLOSURE")
        row["verification"]["git_blob_sha"]="0"*40
        out=v.evaluate_rows(r)
        self.assertFalse(out["pass"],out)
        self.assertEqual(out["reason"],"SUBJECT_BINDING_VERIFICATION_BLOB_STALE")

if __name__=="__main__":unittest.main(verbosity=2)
