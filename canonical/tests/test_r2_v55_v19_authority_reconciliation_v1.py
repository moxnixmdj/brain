from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERMINAL = ROOT / "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
FIXED = ROOT / "canonical/runtime/general_adequate_decision_fixed_point_v2.py"
V19 = ROOT / "canonical/runtime/r2_direct_end_to_end_adequacy_v19.py"

SUCCESSOR_IDS = {
    "DIRECT_ADEQUACY::CROSS_DOCUMENT_NATURAL_EFFECT_LATTICE_V3",
    "DIRECT_ADEQUACY::CROSS_DOCUMENT_SEMANTIC_EDGE_LATTICE_V4",
    "DIRECT_ADEQUACY::CROSS_DOCUMENT_SEMANTIC_REGISTRY_LATTICE_V5",
    "DIRECT_ADEQUACY::SOURCE_BOUND_REGCAP_IDENTITY_NYFED_CCOB_V1",
}

def blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

class R2V55V19AuthorityReconciliationTests(unittest.TestCase):
    def test_live_controller_and_current_authority_are_identical(self):
        r2 = load(R2)
        direct = r2["direct_adequacy"]
        source = FIXED.read_text(encoding="utf-8")
        self.assertIn(
            "from canonical.runtime import r2_direct_end_to_end_adequacy_v19 as direct_adequacy",
            source,
        )
        self.assertEqual(direct["direct_runtime_path"], "canonical/runtime/r2_direct_end_to_end_adequacy_v19.py")
        self.assertEqual(direct["direct_runtime_git_blob_sha"], blob(V19))
        self.assertEqual(direct["fixed_point_controller_git_blob_sha"], blob(FIXED))
        self.assertEqual(r2["controller"]["fixed_point_git_blob_sha"], blob(FIXED))

    def test_activation_enumerates_every_v16_to_v19_successor(self):
        r2 = load(R2)
        direct = r2["direct_adequacy"]
        activation_path = ROOT / direct["activation_path"]
        self.assertEqual(direct["activation_git_blob_sha"], blob(activation_path))
        activation = load(activation_path)
        ids = {row["route_id"] for row in activation["current_routes"]}
        self.assertEqual(len(ids), 39)
        self.assertTrue(SUCCESSOR_IDS.issubset(ids), sorted(SUCCESSOR_IDS - ids))
        self.assertEqual(activation["runtime"], "canonical/runtime/r2_direct_end_to_end_adequacy_v19.py")
        self.assertEqual(direct["current_route_count"], 39)
        self.assertEqual(direct["bounded_family_count"], 36)

    def test_scheduler_and_terminal_projection_match_current_r2(self):
        r2 = load(R2)
        terminal = load(TERMINAL)
        cut_path = ROOT / r2["scheduler_cut"]["path"]
        self.assertEqual(r2["scheduler_cut"]["git_blob_sha"], blob(cut_path))
        cut = load(cut_path)
        for obj in (r2["scheduler_result"], cut["scheduler_result"]):
            self.assertEqual(obj["direct_route_count"], 39)
            self.assertEqual(obj["bounded_family_count"], 36)
        self.assertEqual(terminal["live_truth"]["r2_direct_adequacy_route_count"], 39)
        self.assertEqual(terminal["live_truth"]["r2_direct_adequacy_bounded_family_count"], 36)
        self.assertEqual(
            terminal["r2_scheduler_precedence"]["current_scheduler_git_blob_sha"],
            blob(cut_path),
        )
        self.assertIn("CURRENT_R2_V55", terminal["status"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
