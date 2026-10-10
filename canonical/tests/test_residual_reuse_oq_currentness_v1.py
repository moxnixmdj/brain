from __future__ import annotations
import hashlib
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def blob(path:Path)->str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

class ResidualReuseOQCurrentnessTests(unittest.TestCase):
    def test_reuse_classification_tracks_mutable_current_oq_by_path(self):
        reuse=json.loads((ROOT/"canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json").read_text())
        oq=json.loads((ROOT/"canonical/governance/CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1.json").read_text())
        source=next(x for x in reuse["sources"] if x["path"]=="canonical/governance/CURRENT_ESCAPE_OQ_FRONTIER_REDUCTION_20261010_V1.json")
        self.assertEqual(source["binding"],"MUTABLE_CURRENT_POINTER_PATH_IDENTITY__LIVE_INVARIANTS_RECHECKED")
        self.assertFalse(source["observed_blob_is_load_bearing"])
        self.assertEqual(source["observed_git_blob_sha"],blob(ROOT/source["path"]))
        self.assertNotIn("git_blob_sha",source)
        row=next(x for x in reuse["classifications"] if x["residual_id"]=="ESCAPE_OQ_SHARED_ACCEPTANCE_LAWS")
        self.assertEqual(row["current_truth"],oq["status"])
        self.assertIn("SHARED_O_AND_Q_LAWS_BOUND",row["exact_remaining_class"])
        cut="\n".join(reuse["next_shared_execution_cut"])
        self.assertNotIn("ATTACK_O11_OBJECTIVE_ACCEPTANCE_WITH_ONE_REUSABLE",cut)
        self.assertNotIn("ATTACK_Q2_GDPVAL_AND_AA_BRIEFCASE_WITH_ONE_SHARED",cut)
        self.assertIn("INSTANTIATE_O11",cut)
        self.assertIn("INSTANTIATE_Q2",cut)

    def test_development_authority_observes_exact_current_reuse_bytes(self):
        dev=json.loads((ROOT/"canonical/governance/CURRENT_DEVELOPMENT_AUTHORITY.json").read_text())
        ref=dev["authority"]["residual_reuse_source"]
        self.assertEqual(ref["path"],"canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json")
        self.assertEqual(ref["observed_git_blob_sha"],blob(ROOT/ref["path"]))

if __name__=="__main__":
    unittest.main(verbosity=2)
