from __future__ import annotations
from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
import unittest
from canonical.runtime import professional_quality_same_subject_composition_gate_v4 as v

ROOT=Path(__file__).resolve().parents[2]
R3_BINDING="canonical/governance/PROFESSIONAL_QUALITY_R3_ROOT_SUBJECT_BINDING_20261010_V2.json"
R3_VERIFY="canonical/verification/PROFESSIONAL_QUALITY_R3_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V2.json"

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))
def blob(path):
    data=(ROOT/path).read_bytes()
    return sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

class V4SchemaAdapterTests(unittest.TestCase):
    def test_schema_map_is_exactly_one_r3_v2_exception(self):
        self.assertEqual(set(v.ALLOWED_BINDING_SCHEMA),set(v.EXPECTED_ROOTS))
        self.assertEqual(v.ALLOWED_BINDING_SCHEMA["R3_REALIZATION_OBSERVATION"],"PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V2")
        for rid,schema in v.ALLOWED_BINDING_SCHEMA.items():
            if rid!="R3_REALIZATION_OBSERVATION":
                self.assertEqual(schema,"PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1")

    def test_real_r3_v2_chains_to_verified_v1_nonauthority(self):
        b=load(R3_BINDING)
        self.assertIsNone(v._r3_v2_binding_boundary(ROOT,b))

    def test_r3_v2_global_root_overclaim_fails_closed(self):
        b=load(R3_BINDING);b["global_r3_root_closed"]=True
        self.assertEqual(v._r3_v2_binding_boundary(ROOT,b),"R3_V2_GLOBAL_ROOT_CLOSURE_FORBIDDEN")

    def test_r3_v2_receipt_binds_exact_v2_blob(self):
        b=load(R3_BINDING);receipt=load(R3_VERIFY)
        err=v._verification_receipt_error(
            root_id="R3_REALIZATION_OBSERVATION",verification=receipt,binding_blob=blob(R3_BINDING),
            subject_kind=b["subject_kind"],subject_id=b["subject_id"],subject_sha=b["subject_sha256"])
        self.assertIsNone(err)

    def test_r3_v2_receipt_hash_mismatch_fails_closed(self):
        b=load(R3_BINDING);receipt=deepcopy(load(R3_VERIFY))
        receipt["exact_blobs"]["v2_binding"]="0"*40
        err=v._verification_receipt_error(
            root_id="R3_REALIZATION_OBSERVATION",verification=receipt,binding_blob=blob(R3_BINDING),
            subject_kind=b["subject_kind"],subject_id=b["subject_id"],subject_sha=b["subject_sha256"])
        self.assertEqual(err,"SUBJECT_BINDING_VERIFY_BLOB_MISMATCH")

if __name__=="__main__":unittest.main(verbosity=2)
