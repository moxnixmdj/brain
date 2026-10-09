from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from canonical.runtime import r2_direct_live_dispatcher_v1 as live


ROOT = Path(__file__).resolve().parents[2]
CURRENT_R2 = ROOT / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
CURRENT_LIVE = ROOT / "canonical/governance/CURRENT_R2_DIRECT_LIVE_STATE.json"
FIXED_POINT = ROOT / "canonical/runtime/general_adequate_decision_fixed_point_v2.py"
DISPATCHER = ROOT / "canonical/runtime/r2_direct_live_dispatcher_v1.py"
FIELD_ROUTE_ID = "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_FIELD_LATTICE_V2"


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


class R2DirectDefaultLiveIntegrationV1Tests(unittest.TestCase):
    def load(self, path: Path):
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertIsInstance(value, dict)
        return value

    def test_current_r2_binds_stable_dispatcher_and_fixed_point_bytes(self):
        current = self.load(CURRENT_R2)
        direct = current["direct_adequacy"]
        self.assertEqual(
            direct["direct_runtime_path"],
            "canonical/runtime/r2_direct_live_dispatcher_v1.py",
        )
        self.assertEqual(direct["direct_runtime_git_blob_sha"], blob_sha(DISPATCHER))
        self.assertEqual(
            direct["fixed_point_controller_git_blob_sha"],
            blob_sha(FIXED_POINT),
        )
        self.assertFalse(direct["future_route_source_edit_required"])
        self.assertFalse(direct["future_fixed_point_edit_required"])
        self.assertFalse(direct["legacy_version_chain_load_bearing"])

    def test_fixed_point_uses_stable_dispatcher_not_versioned_router(self):
        source = FIXED_POINT.read_text(encoding="utf-8")
        self.assertIn(
            "from canonical.runtime import r2_direct_live_dispatcher_v1 as direct_adequacy",
            source,
        )
        self.assertNotIn("r2_direct_end_to_end_adequacy_v14 as direct_adequacy", source)

    def test_activation_route_set_equals_live_baseline_route_set(self):
        current = self.load(CURRENT_R2)
        direct = current["direct_adequacy"]
        activation = self.load(ROOT / direct["activation_path"])
        self.assertEqual(blob_sha(ROOT / direct["activation_path"]), direct["activation_git_blob_sha"])

        state = live.load_state()
        baseline_ids = set(state["baseline"]["declared_route_ids"])
        activation_ids = {row["route_id"] for row in activation["current_routes"]}
        self.assertEqual(len(activation_ids), 34)
        self.assertEqual(baseline_ids, activation_ids)
        self.assertEqual(state["baseline"]["declared_route_count"], 34)
        self.assertIn(FIELD_ROUTE_ID, activation_ids)
        self.assertEqual(state["dynamic_routes"], [])

    def test_v14_field_route_has_exact_independent_verification_binding(self):
        current = self.load(CURRENT_R2)
        activation = self.load(ROOT / current["direct_adequacy"]["activation_path"])
        rows = [row for row in activation["current_routes"] if row["route_id"] == FIELD_ROUTE_ID]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(
            row["runtime"],
            "canonical/runtime/r2_cross_document_effect_field_lattice_direct_adequacy_v1.py",
        )
        self.assertEqual(
            blob_sha(ROOT / row["runtime"]),
            row["runtime_git_blob_sha"],
        )
        verification = row["verification"]
        self.assertEqual(
            verification["path"],
            "canonical/verification/R2_CROSS_DOCUMENT_EFFECT_FIELDS_V14_VERIFY_20261009_V1.json",
        )
        self.assertEqual(
            blob_sha(ROOT / verification["path"]),
            verification["git_blob_sha"],
        )
        receipt = self.load(ROOT / verification["path"])
        self.assertEqual(
            receipt["status"],
            "VERIFIED_ISOLATED_FULL_STACK__199_OF_199_PASS",
        )
        self.assertEqual(receipt["isolated_verification"]["total_passed"], 199)
        self.assertEqual(receipt["isolated_verification"]["total_failed"], 0)

    def test_live_catalog_is_source_edit_free(self):
        catalog = live.catalog()
        self.assertTrue(catalog["pass"])
        self.assertEqual(catalog["baseline_route_count"], 34)
        self.assertEqual(catalog["dynamic_route_count"], 0)
        self.assertFalse(catalog["future_route_source_edit_required"])
        self.assertFalse(catalog["future_fixed_point_edit_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
