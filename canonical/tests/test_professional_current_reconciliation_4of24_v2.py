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
    def test_embedded_property_truth_matches_independent_registry(self):
        v=load("canonical/verification/PROFESSIONAL_QUALITY_LEAF_REGISTRY_PROPERTY_TRUTH_VERIFY_20261010_V2.json")
        p=load("canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json")
        expected=v["independent_replay"]["verified_execution_leaf_ids"]
        pf=p["property_truth_frontier"]
        self.assertEqual(v["independent_replay"]["verified_leaf_count"],4)
        self.assertEqual(v["independent_replay"]["open_leaf_count"],20)
        self.assertEqual(pf["verified_leaf_count"],4)
        self.assertEqual(pf["open_leaf_count"],20)
        self.assertEqual(pf["verified_execution_leaf_count"],4)
        self.assertEqual(pf["open_execution_leaf_count"],8)
        self.assertEqual(pf["verified_semantic_leaf_count"],0)
        self.assertEqual(pf["open_semantic_leaf_count"],12)
        self.assertEqual(pf["verified_leaf_ids"],expected)

    def test_semantic_totality_reduction_is_bound_without_credit(self):
        s=load("canonical/verification/PROFESSIONAL_SEMANTIC_TOTALITY_REDUCTION_VERIFY_20261010_V1.json")
        p=load("canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json")
        a=load("canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json")
        m=load("canonical/governance/CURRENT_MISSION_OBJECTIVE.json")
        self.assertIn("TWELVE_SEMANTIC_LEAVES_REDUCED_TO_CLAIM_SCOPED_TOTALITY",s["status"])
        self.assertIn("ZERO_PROPERTY_TRUTH_CREDIT",s["status"])
        self.assertEqual(p["semantic_totality_reduction"]["git_blob_sha"],blob("canonical/verification/PROFESSIONAL_SEMANTIC_TOTALITY_REDUCTION_VERIFY_20261010_V1.json"))
        self.assertEqual(a["semantic_totality_reduction"]["git_blob_sha"],blob("canonical/verification/PROFESSIONAL_SEMANTIC_TOTALITY_REDUCTION_VERIFY_20261010_V1.json"))
        self.assertEqual(m["semantic_totality_reduction_reconciliation"]["observed_git_blob_sha"],blob("canonical/verification/PROFESSIONAL_SEMANTIC_TOTALITY_REDUCTION_VERIFY_20261010_V1.json"))
        self.assertFalse(a["semantic_totality_reduction"]["semantic_leaf_totality_proved"])
        self.assertEqual(a["semantic_totality_reduction"]["property_truth_credit_delta"],0)

    def test_mission_binds_exact_current_pointer_bytes(self):
        m=load("canonical/governance/CURRENT_MISSION_OBJECTIVE.json")
        prof="canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
        ass="canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
        self.assertEqual(m["current_professional_quality_execution"]["observed_git_blob_sha"],blob(prof))
        self.assertEqual(m["current_assurance_closure_compiler"]["observed_git_blob_sha"],blob(ass))
        self.assertEqual(m["property_truth_reconciliation"]["verified_leaf_count"],4)
        self.assertEqual(m["professional_whole_leaf_control"]["property_truth_closed_count"],4)

    def test_live_frontier_binds_exact_current_pointer_bytes(self):
        f=load("canonical/governance/CURRENT_LIVE_WORK_FRONTIER.json")
        prof="canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
        ass="canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"
        p=next(x for x in f["candidates"] if x["work_id"]=="PROFESSIONAL_QUALITY_V7_PROPERTY_TRUTH_DEPLETION")
        a=next(x for x in f["candidates"] if x["work_id"]=="ASSURANCE_UVCK_V2_PROMOTION_GATES")
        self.assertEqual(p["read_only_evidence"]["source_git_blob_sha"],blob(prof))
        self.assertEqual(a["read_only_evidence"]["source_git_blob_sha"],blob(ass))
        self.assertEqual(a["read_only_evidence"]["professional_current_git_blob_sha"],blob(prof))
        self.assertEqual(p["read_only_evidence"]["property_truth_closed_count"],4)
        self.assertEqual(p["read_only_evidence"]["open_execution_leaf_count"],8)
        self.assertEqual(p["read_only_evidence"]["open_semantic_leaf_count"],12)
        self.assertNotIn("PROPERTY_TRUTH_2_OF_24",f["live_selection"]["reason"])
        self.assertNotIn("TEN_EXECUTION",f["live_selection"]["reason"])

    def test_assurance_has_no_precomposition_or_pre_r12_nonclaims(self):
        a=load("canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json")
        t="\n".join(a.get("hard_nonclaims") or [])
        self.assertNotIn("NO_PROFESSIONAL_SAME_SUBJECT_COMPOSITION_PASS",t)
        self.assertNotIn("NO_R12_CURRENT_ROOT_SUBJECT_BINDING_YET",t)
        self.assertIn("NO_24_OF_24_PROPERTY_TRUTH",t)
        self.assertEqual(a["professional_whole_leaf_progress"]["property_truth_closed_count"],4)
        self.assertEqual(a["professional_whole_leaf_progress"]["remaining_scope_construction_count"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
