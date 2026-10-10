from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
FILES = {
    "assurance": ROOT / "canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json",
    "scheduler": ROOT / "canonical/governance/CURRENT_DEVELOPMENT_SCHEDULER.json",
    "mission": ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json",
    "professional": ROOT / "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json",
    "scope": ROOT / "canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json",
    "r10": ROOT / "canonical/verification/PROFESSIONAL_QUALITY_R10_EXECUTION_PROPERTY_TRUTH_INDEPENDENT_VERIFY_20261010_V1.json",
}

def load(name):
    return json.loads(FILES[name].read_text(encoding="utf-8"))

def blob(path):
    raw=path.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

class ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=load("assurance"); cls.s=load("scheduler"); cls.m=load("mission")
        cls.p=load("professional"); cls.scope=load("scope"); cls.r10=load("r10")

    def test_receipts_exact(self):
        self.assertEqual(blob(FILES["scope"]),"4c2d40a262f18f34bb35f94b59660d60972d45ef")
        self.assertEqual(blob(FILES["r10"]),"cfa1f178e149dbd987a52e9825dc67960dbade4c")
        self.assertEqual(self.scope["independent_replay"]["scope_complete_count"],24)
        self.assertTrue(self.r10["leaf_property_truth_authority"])
        self.assertFalse(self.r10["r10_root_closed"])
        self.assertFalse(self.r10["quality_authority"])
        self.assertFalse(self.r10["terminal_authority"])

    def test_authoritative_professional_state(self):
        self.assertIn("PROPERTY_TRUTH_1_OF_24",self.p["status"])
        f=self.p["property_truth_frontier"]
        self.assertEqual(f["verified_leaf_count"],1)
        self.assertEqual(f["open_leaf_count"],23)
        self.assertEqual(f["verified_leaf_ids"],["PQ::R10_ANALYSIS_DECISION::EXECUTION"])

    def test_assurance_projection(self):
        x=self.a["professional_whole_leaf_progress"]
        self.assertEqual((x["admitted_whole_leaf_scope_count"],x["property_truth_ready_count"],x["remaining_scope_construction_count"]),(24,24,0))
        self.assertEqual((x["property_truth_closed_count"],x["global_leaf_closed_count"],x["open_property_truth_leaf_count"]),(1,1,23))
        self.assertEqual(x["verified_property_truth_leaf_ids"],["PQ::R10_ANALYSIS_DECISION::EXECUTION"])
        self.assertFalse(x["domain_semantic_closure"]); self.assertFalse(x["domain_execution_closure"])

    def test_scheduler_projection(self):
        x=self.s["whole_leaf_residual_control"]
        self.assertEqual((x["admitted_v2_chain_count"],x["claim_scope_construction_required_count"],x["property_truth_ready_count"]),(24,0,24))
        self.assertEqual((x["property_truth_closed_count"],x["property_truth_open_count"]),(1,23))
        self.assertEqual(x["verified_property_truth_leaf_ids"],["PQ::R10_ANALYSIS_DECISION::EXECUTION"])
        self.assertIn("PROPERTY_TRUTH_1_OF_24",x["status"])

    def test_mission_projection(self):
        x=self.m["professional_whole_leaf_control"]
        self.assertEqual((x["leaf_count"],x["admitted_v2_chain_count"],x["claim_scope_construction_required_count"]),(24,24,0))
        self.assertEqual((x["property_truth_ready_count"],x["property_truth_closed_count"],x["property_truth_open_count"]),(24,1,23))
        self.assertEqual(x["verified_property_truth_leaf_ids"],["PQ::R10_ANALYSIS_DECISION::EXECUTION"])

    def test_no_laundering(self):
        self.assertFalse(self.r10["r10_root_closed"]); self.assertFalse(self.r10["quality_authority"]); self.assertFalse(self.r10["terminal_authority"])
        text="\n".join(json.dumps(x,sort_keys=True) for x in (self.a,self.s,self.m))
        self.assertNotIn('"property_truth_closed_count": 24',text)
        self.assertNotIn('"domain_semantic_closure": true',text)
        self.assertNotIn('"domain_execution_closure": true',text)

if __name__=="__main__":
    unittest.main(verbosity=2)
