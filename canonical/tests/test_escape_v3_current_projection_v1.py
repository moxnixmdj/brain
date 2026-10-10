from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
CLASSIFIER=ROOT/"canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json"
BINDING=ROOT/"canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V5.json"

class EscapeV3CurrentProjectionTests(unittest.TestCase):
    def test_v5_binding_projects_verified_v3_audit(self):
        self.assertTrue(BINDING.is_file())
        b=json.loads(BINDING.read_text())
        a=b["successor_executable_audit"]
        self.assertEqual(a["status"],"INDEPENDENTLY_VERIFIED_V3__18_OF_18__PYCOMPILE_PASS")
        self.assertEqual(a["path"],"canonical/runtime/escape_progress_shared_gap_audit_v3.py")
        self.assertEqual(a["git_blob_sha"],"14adf2c1a431285a542340a740e27e764edb1ce5")
        self.assertEqual(
            a["verification"]["path"],
            "canonical/verification/ESCAPE_PROGRESS_SHARED_GAP_EXECUTABLE_AUDIT_V3_VERIFY_20261010_V1.json",
        )
        self.assertEqual(a["verification"]["git_blob_sha"],"4156e6c9a1c27913120568d8e505f0f154907015")

    def test_current_classifier_projects_v3_not_v2(self):
        d=json.loads(CLASSIFIER.read_text())
        by_id={x["residual_id"]:x for x in d["classifications"]}
        for rid in ("ESCAPE_GAP_A_ACQUISITION_TOTALITY","ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"):
            row=by_id[rid]
            self.assertEqual(row["existing_binding"],"canonical/governance/ESCAPE_PROGRESS_SHARED_GAP_REUSE_BINDING_20261010_V5.json")
            self.assertEqual(row["executable_audit"],"canonical/runtime/escape_progress_shared_gap_audit_v3.py")
            self.assertEqual(row["executable_audit_git_blob_sha"],"14adf2c1a431285a542340a740e27e764edb1ce5")
            self.assertEqual(row["audit_verification"],"canonical/verification/ESCAPE_PROGRESS_SHARED_GAP_EXECUTABLE_AUDIT_V3_VERIFY_20261010_V1.json")
            self.assertIn("V3_VERIFIED_18_OF_18",row["current_gate_status"])

if __name__=="__main__":
    unittest.main(verbosity=2)
