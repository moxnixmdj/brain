from copy import deepcopy
from pathlib import Path
import json
import unittest
from canonical.runtime import professional_semantic_totality_claim_pack_v3 as v3

ROOT=Path(__file__).resolve().parents[2]

class V3Tests(unittest.TestCase):
    def test_current(self):
        out=v3.verify(repo_root=ROOT)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["semantic_claim_count"],12)
        self.assertEqual(out["unique_claim_id_count"],12)
        self.assertEqual(out["mission_blob_sha"],v3.EXPECTED_MISSION_AUTHORITY_BLOB)
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_pointer_drift(self):
        p=json.loads((ROOT/v3.MISSION_POINTER_PATH).read_text())
        a=json.loads((ROOT/v3.MISSION_AUTHORITY_PATH).read_text())
        p=deepcopy(p);p["real_objective"]+="x"
        out=v3.resolve_mission_authority(
            p,a,authority_blob_sha=v3.EXPECTED_MISSION_AUTHORITY_BLOB
        )
        self.assertFalse(out["pass"])

    def test_pointer_bookkeeping_drift_preserves_resolution(self):
        p=json.loads((ROOT/v3.MISSION_POINTER_PATH).read_text())
        a=json.loads((ROOT/v3.MISSION_AUTHORITY_PATH).read_text())
        p=deepcopy(p);p["synthetic_currentness_only"]={"n":1}
        out=v3.resolve_mission_authority(
            p,a,authority_blob_sha=v3.EXPECTED_MISSION_AUTHORITY_BLOB
        )
        self.assertTrue(out["pass"],out)

    def test_authority_drift(self):
        p=json.loads((ROOT/v3.MISSION_POINTER_PATH).read_text())
        a=json.loads((ROOT/v3.MISSION_AUTHORITY_PATH).read_text())
        out=v3.resolve_mission_authority(p,a,authority_blob_sha="0"*40)
        self.assertFalse(out["pass"])

if __name__=="__main__":
    unittest.main(verbosity=2)
