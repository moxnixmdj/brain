from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]

def load(path:str):
    return json.loads((ROOT/path).read_text())

def blob(path:str)->str:
    data=(ROOT/path).read_bytes()
    return sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

class Tests(unittest.TestCase):
    def test_current_professional_truth_matches_verified_registry(self):
        v=load("canonical/verification/PROFESSIONAL_QUALITY_LEAF_REGISTRY_PROPERTY_TRUTH_VERIFY_20261010_V2.json")
        p=load("canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json")
        self.assertEqual(v["independent_replay"]["verified_leaf_count"],4)
        self.assertEqual(v["independent_replay"]["open_leaf_count"],20)
        self.assertEqual(p["property_truth_frontier"]["verified_leaf_count"],4)
        self.assertEqual(p["property_truth_frontier"]["open_leaf_count"],20)
        self.assertEqual(p["property_truth_frontier"]["verified_execution_leaf_count"],4)
        self.assertEqual(p["property_truth_frontier"]["open_execution_leaf_count"],8)
        self.assertEqual(p["property_truth_frontier"]["verified_semantic_leaf_count"],0)
        self.assertEqual(p["property_truth_frontier"]["open_semantic_leaf_count"],12)
        self.assertEqual(
            p["property_truth_frontier"]["verified_leaf_ids"],
            v["independent_replay"]["verified_execution_leaf_ids"],
        )

    def test_mission_and_assurance_bind_current_pointer_bytes(self):
        mission=load("canonical/governance/CURRENT_MISSION_OBJECTIVE.json")
        prof="canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
        assurance="canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
        self.assertEqual(mission["current_professional_quality_execution"]["observed_git_blob_sha"],blob(prof))
        self.assertEqual(mission["current_assurance_closure_compiler"]["observed_git_blob_sha"],blob(assurance))
        self.assertEqual(mission["property_truth_reconciliation"]["verified_leaf_count"],4)
        self.assertEqual(mission["professional_whole_leaf_control"]["property_truth_closed_count"],4)

    def test_frontier_reads_exact_current_professional_and_assurance_bytes(self):
        f=load("canonical/governance/CURRENT_LIVE_WORK_FRONTIER.json")
        prof="canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
        assurance="canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
        p=next(x for x in f["candidates"] if x["work_id"]=="PROFESSIONAL_QUALITY_V7_PROPERTY_TRUTH_DEPLETION")
        a=next(x for x in f["candidates"] if x["work_id"]=="ASSURANCE_UVCK_V2_PROMOTION_GATES")
        self.assertEqual(p["read_only_evidence"]["source_git_blob_sha"],blob(prof))
        self.assertEqual(a["read_only_evidence"]["source_git_blob_sha"],blob(assurance))
        self.assertEqual(a["read_only_evidence"]["professional_current_git_blob_sha"],blob(prof))
        self.assertEqual(p["read_only_evidence"]["property_truth_closed_count"],4)
        self.assertEqual(p["read_only_evidence"]["open_execution_leaf_count"],8)
        self.assertEqual(p["read_only_evidence"]["open_semantic_leaf_count"],12)

    def test_stale_professional_nonclaims_are_removed(self):
        a=load("canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json")
        text="\n".join(a.get("hard_nonclaims") or [])
        self.assertNotIn("NO_PROFESSIONAL_SAME_SUBJECT_COMPOSITION_PASS",text)
        self.assertNotIn("NO_R12_CURRENT_ROOT_SUBJECT_BINDING_YET",text)
        self.assertIn("NO_24_OF_24_PROPERTY_TRUTH",text)

if __name__=="__main__":
    unittest.main(verbosity=2)
