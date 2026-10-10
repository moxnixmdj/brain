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
    "scope_verify": ROOT / "canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json",
    "r10_verify": ROOT / "canonical/verification/PROFESSIONAL_QUALITY_R10_EXECUTION_PROPERTY_TRUTH_INDEPENDENT_VERIFY_20261010_V1.json",
}

def load(name: str) -> dict:
    return json.loads(FILES[name].read_text(encoding="utf-8"))

def blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

class ProfessionalScopePropertyProjectionConsistencyV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assurance=load("assurance")
        cls.scheduler=load("scheduler")
        cls.mission=load("mission")
        cls.professional=load("professional")
        cls.scope=load("scope_verify")
        cls.r10=load("r10_verify")

    def test_source_receipts_are_exact(self):
        self.assertEqual(blob(FILES["scope_verify"]), "4c2d40a262f18f34bb35f94b59660d60972d45ef")
        self.assertEqual(blob(FILES["r10_verify"]), "cfa1f178e149dbd987a52e9825dc67960dbade4c")
        self.assertEqual(self.scope["independent_replay"]["scope_complete_count"], 24)
        self.assertEqual(self.scope["independent_replay"]["property_truth_count"], 0)
        self.assertTrue(self.r10["status"].startswith("PASS__"))
        self.assertTrue(self.r10["leaf_property_truth_authority"])
        self.assertFalse(self.r10["r10_root_closed"])
        self.assertFalse(self.r10["quality_authority"])
        self.assertFalse(self.r10["terminal_authority"])

    def test_authoritative_professional_pointer_is_24_scope_1_property(self):
        self.assertIn("24_OF_24_WHOLE_LEAF_DOMAIN_AND_SCOPE_VERIFIED", self.professional["status"])
        self.assertIn("PROPERTY_TRUTH_1_OF_24", self.professional["status"])
        p=self.professional["property_truth_frontier"]
        self.assertEqual(p["verified_leaf_count"],1)
        self.assertEqual(p["open_leaf_count"],23)
        self.assertEqual(p["verified_leaf_ids"],["PQ::R10_ANALYSIS_DECISION::EXECUTION"])

    def test_assurance_projection_matches_authoritative_state(self):
        p=self.assurance["professional_whole_leaf_progress"]
        self.assertEqual(p["admitted_whole_leaf_scope_count"],24)
        self.assertEqual(p["property_truth_ready_count"],24)
        self.assertEqual(p["remaining_scope_construction_count"],0)
        self.assertEqual(p["property_truth_closed_count"],1)
        self.assertEqual(p["global_leaf_closed_count"],1)
        self.assertEqual(p["open_property_truth_leaf_count"],23)
        self.assertEqual(p["verified_property_truth_leaf_ids"],["PQ::R10_ANALYSIS_DECISION::EXECUTION"])
        self.assertFalse(p["domain_semantic_closure"])
        self.assertFalse(p["domain_execution_closure"])

    def test_scheduler_projection_matches_authoritative_state(self):
        p=self.scheduler["whole_leaf_residual_control"]
        self.assertEqual(p["admitted_v2_chain_count"],24)
        self.assertEqual(p["claim_scope_construction_required_count"],0)
        self.assertEqual(p["property_truth_ready_count"],24)
        self.assertEqual(p["property_truth_closed_count"],1)
        self.assertEqual(p["property_truth_open_count"],23)
        self.assertEqual(p["verified_property_truth_leaf_ids"],["PQ::R10_ANALYSIS_DECISION::EXECUTION"])
        self.assertIn("1_PROPERTY_TRUTH_CLOSED",p["status"])

    def test_mission_projection_matches_authoritative_state(self):
        p=self.mission["professional_whole_leaf_control"]
        self.assertEqual(p["leaf_count"],24)
        self.assertEqual(p["admitted_v2_chain_count"],24)
        self.assertEqual(p["claim_scope_construction_required_count"],0)
        self.assertEqual(p["property_truth_ready_count"],24)
        self.assertEqual(p["property_truth_closed_count"],1)
        self.assertEqual(p["property_truth_open_count"],23)
        self.assertEqual(p["verified_property_truth_leaf_ids"],["PQ::R10_ANALYSIS_DECISION::EXECUTION"])

    def test_no_property_to_root_quality_or_terminal_laundering(self):
        self.assertFalse(self.r10["r10_root_closed"])
        self.assertFalse(self.r10["quality_authority"])
        self.assertFalse(self.r10["terminal_authority"])
        text="\n".join(json.dumps(x,sort_keys=True) for x in (self.assurance,self.scheduler,self.mission))
        self.assertNotIn('"property_truth_closed_count": 24',text)
        self.assertNotIn('"domain_semantic_closure": true',text)
        self.assertNotIn('"domain_execution_closure": true',text)

if __name__=="__main__":
    unittest.main(verbosity=2)
