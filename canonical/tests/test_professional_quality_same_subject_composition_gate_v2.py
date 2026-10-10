from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_same_subject_composition_gate_v2 as v2

ROOT=Path(__file__).resolve().parents[2]
WORKLIST="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_SAME_SUBJECT_ROOT_BINDING_WORKLIST_20261010_V18.json"

def load(path):
    return json.loads((ROOT/path).read_text())

def payload():
    wl=load(WORKLIST)
    return {"root_subject_bindings":[
        {"root_id":row["root_id"],"binding":row["binding"],"verification":row["verification"]}
        for row in wl["roots"]
    ]}

class Tests(unittest.TestCase):
    def test_real_v18_worklist_is_composition_admissible_only(self):
        out=v2.evaluate(payload())
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["composition_admissible"])
        self.assertEqual(out["verified_root_subject_binding_count"],12)
        self.assertEqual(out["composed_subject"]["subject_id"],"PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6")
        self.assertFalse(out["professional_quality_closed"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_all_twelve_real_receipt_formats_are_explicitly_admitted(self):
        p=payload()
        for row in p["root_subject_bindings"]:
            rid=row["root_id"]
            b=load(row["binding"]["path"])
            d=load(row["verification"]["path"])
            ok,reason=v2._verification_evidence_ok(
                rid,d,
                verification_path=row["verification"]["path"],
                binding_path=row["binding"]["path"],
                binding_blob=row["binding"]["git_blob_sha"],
                binding=b,
            )
            self.assertTrue(ok,(rid,reason))
            self.assertIsNone(reason)

    def test_unknown_schema_fails_closed(self):
        row=payload()["root_subject_bindings"][5]
        b=load(row["binding"]["path"]);d=load(row["verification"]["path"])
        d["schema"]="UNKNOWN"
        ok,reason=v2._verification_evidence_ok(row["root_id"],d,verification_path=row["verification"]["path"],binding_path=row["binding"]["path"],binding_blob=row["binding"]["git_blob_sha"],binding=b)
        self.assertFalse(ok);self.assertEqual(reason,"VERIFY_SCHEMA_NOT_EXPLICITLY_ADMITTED")

    def test_public_runner_failure_fails_closed(self):
        row=next(x for x in payload()["root_subject_bindings"] if x["root_id"]=="R12_META_COMPOSITION_CLOSURE")
        b=load(row["binding"]["path"]);d=load(row["verification"]["path"])
        d=deepcopy(d);d["public_runner"]["conclusion"]="failure"
        ok,reason=v2._verification_evidence_ok(row["root_id"],d,verification_path=row["verification"]["path"],binding_path=row["binding"]["path"],binding_blob=row["binding"]["git_blob_sha"],binding=b)
        self.assertFalse(ok);self.assertEqual(reason,"PUBLIC_RUNNER_EVIDENCE_INCOMPLETE")

    def test_binding_blob_mismatch_fails_closed(self):
        row=next(x for x in payload()["root_subject_bindings"] if x["root_id"]=="R4_MEASUREMENT_CONSTRUCT")
        b=load(row["binding"]["path"]);d=load(row["verification"]["path"])
        d=deepcopy(d);d["exact_blobs"]["binding"]="0"*40
        ok,reason=v2._verification_evidence_ok(row["root_id"],d,verification_path=row["verification"]["path"],binding_path=row["binding"]["path"],binding_blob=row["binding"]["git_blob_sha"],binding=b)
        self.assertFalse(ok);self.assertEqual(reason,"VERIFY_BINDING_BLOB_MISMATCH")

    def test_nested_authority_revocation_fails_closed(self):
        row=next(x for x in payload()["root_subject_bindings"] if x["root_id"]=="R1_TARGET_SPECIFICATION")
        b=load(row["binding"]["path"]);d=load(row["verification"]["path"])
        d=deepcopy(d);d["authority"]["root_subject_binding_authority"]=False
        ok,reason=v2._verification_evidence_ok(row["root_id"],d,verification_path=row["verification"]["path"],binding_path=row["binding"]["path"],binding_blob=row["binding"]["git_blob_sha"],binding=b)
        self.assertFalse(ok);self.assertEqual(reason,"ROOT_SUBJECT_BINDING_AUTHORITY_REQUIRED")

if __name__=="__main__":
    unittest.main(verbosity=2)
