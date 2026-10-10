from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_leaf_binder_v2 as binder

ROOT=Path(__file__).resolve().parents[2]
ASSURANCE=ROOT/"canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
REGISTRY=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_LEAF_EVIDENCE_REGISTRY_20261010_V1.json"
VERIFY=ROOT/"canonical/verification/PROFESSIONAL_QUALITY_LEAF_REGISTRY_PROPERTY_TRUTH_VERIFY_20261010_V1.json"


def blob(path:Path)->str:
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


class LeafRegistryAssuranceCurrentnessV1Tests(unittest.TestCase):
    def test_assurance_matches_current_registry_projection(self):
        assurance=json.loads(ASSURANCE.read_text())
        admission=assurance["professional_quality_leaf_admission_v2"]
        out=binder.evaluate()
        self.assertEqual(admission["registry_git_blob_sha"],blob(REGISTRY))
        self.assertEqual(admission["current_projection_verification_git_blob_sha"],blob(VERIFY))
        self.assertEqual(admission["verified_leaf_count"],out["verified_leaf_count"])
        self.assertEqual(admission["open_leaf_count"],out["open_leaf_count"])
        self.assertEqual(set(admission["verified_execution_leaf_ids"]),set(out["verified_execution_leaf_ids"]))
        self.assertEqual(admission["verified_semantic_leaf_ids"],out["verified_semantic_leaf_ids"])
        self.assertTrue(admission["existing_evidence_current"])
        self.assertEqual(admission["rejected_receipt_count"],0)
        self.assertFalse(out["promotion_ready"])


if __name__=="__main__":
    unittest.main(verbosity=2)
