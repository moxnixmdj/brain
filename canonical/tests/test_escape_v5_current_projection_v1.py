import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]

class EscapeV5ProjectionTests(unittest.TestCase):
    def test_current_escape_rows_use_v5(self):
        cur=json.loads((ROOT/"canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json").read_text())
        rows=[x for x in cur["classifications"] if x.get("residual_id") in {"ESCAPE_GAP_A_ACQUISITION_TOTALITY","ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"}]
        self.assertEqual(len(rows),2)
        for row in rows:
            self.assertEqual(row["executable_audit"],"canonical/runtime/escape_progress_shared_gap_audit_v5.py")
            self.assertEqual(row["executable_audit_git_blob_sha"],"1f1dcf4806b3d944721abe86f46f018c5345726d")
            self.assertEqual(row["audit_verification"],"canonical/verification/ESCAPE_PROGRESS_SHARED_GAP_EXECUTABLE_AUDIT_V5_VERIFY_20261010_V1.json")
            self.assertEqual(row["audit_verification_git_blob_sha"],"db0d6ae5c19193f2966c9ec4cb47980652e2405e")
            self.assertEqual(row["currentness_activation"]["git_blob_sha"],"41a50db02a1b60a4ab47a02ddb29d5f9f3338019")
            self.assertIn("CURRENT_ROUTE_SEMANTICS",row["row_proof_authority_rule"])

if __name__=="__main__":
    unittest.main(verbosity=2)
