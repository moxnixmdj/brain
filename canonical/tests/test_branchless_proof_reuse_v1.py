from __future__ import annotations
import unittest
from canonical.runtime.branchless_proof_promotion_gate_v1 import SCHEMA, evaluate

A="a"*40; B="b"*40; C="c"*40; D="d"*40

def base():
    return {
      "schema":SCHEMA,
      "verified_capsule":{
        "scope_id":"P1_SHARED_BATCH_CORE","base_commit":"1"*40,
        "payload_blobs":[{"path":"runtime.py","git_blob_sha":A},{"path":"tests.py","git_blob_sha":B}],
        "dependency_cone_blobs":[{"path":"schema.json","git_blob_sha":C}],
        "verification_receipt":{"path":"canonical/verification/receipt.json","git_blob_sha":D,"status":"INDEPENDENT_PUBLIC_RUNNER_PASS","independent":True},
        "dependency_cone_receipt":{"path":"canonical/verification/cone.json","git_blob_sha":C,"status":"INDEPENDENT_PUBLIC_RUNNER_PASS","independent":True},
        "verification_complete":True,"counterexample_suite_pass":True,
        "execution_authority":False,"promotion_authority":False
      },
      "current_snapshot":{
        "scope_id":"P1_SHARED_BATCH_CORE","base_commit":"2"*40,
        "payload_blobs":[{"path":"runtime.py","git_blob_sha":A},{"path":"tests.py","git_blob_sha":B}],
        "dependency_cone_blobs":[{"path":"schema.json","git_blob_sha":C}]
      }
    }

class Tests(unittest.TestCase):
    def test_base_drift_reuses_exact_verified_bytes(self):
        out=evaluate(base()); self.assertTrue(out["reuse_verified_proof"],out)
        self.assertTrue(out["integration_projection_reverification_required"])
    def test_payload_change_requires_reverification(self):
        d=base(); d["current_snapshot"]["payload_blobs"][0]["git_blob_sha"]=D
        out=evaluate(d); self.assertFalse(out["reuse_verified_proof"]); self.assertEqual(out["payload_changes"],["runtime.py"])
    def test_dependency_change_requires_reverification(self):
        d=base(); d["current_snapshot"]["dependency_cone_blobs"][0]["git_blob_sha"]=D
        out=evaluate(d); self.assertFalse(out["reuse_verified_proof"]); self.assertEqual(out["dependency_cone_changes"],["schema.json"])
    def test_added_dependency_requires_reverification(self):
        d=base(); d["current_snapshot"]["dependency_cone_blobs"].append({"path":"new.json","git_blob_sha":D})
        out=evaluate(d); self.assertFalse(out["reuse_verified_proof"]); self.assertEqual(out["dependency_cone_changes"],["new.json"])
    def test_unverified_receipt_fails_closed(self):
        d=base(); d["verified_capsule"]["verification_receipt"]["independent"]=False
        out=evaluate(d); self.assertEqual(out["status"],"FAIL_CLOSED")
    def test_scope_change_fails_closed(self):
        d=base(); d["current_snapshot"]["scope_id"]="OTHER"
        out=evaluate(d); self.assertEqual(out["status"],"FAIL_CLOSED")
    def test_self_asserted_authority_fails_closed(self):
        d=base(); d["verified_capsule"]["promotion_authority"]=True
        out=evaluate(d); self.assertEqual(out["status"],"FAIL_CLOSED"); self.assertFalse(out["promotion_authority"])

if __name__=="__main__": unittest.main(verbosity=2)
