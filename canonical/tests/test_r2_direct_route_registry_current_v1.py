from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest import mock

from canonical.runtime import r2_direct_route_registry_v1 as registry_router


ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_REGISTRY.json"
FIXED_POINT = ROOT / "canonical/runtime/general_adequate_decision_fixed_point_v2.py"

WORLDSET = "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_WORLDSET_V1"
EFFECT = "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_COMPOSITION_V1"


class R2DirectRouteRegistryCurrentTests(unittest.TestCase):
    def test_current_registry_migrates_all_thirty_routes(self):
        registry = registry_router.load_registry()
        self.assertEqual(registry["route_count"], 30)
        self.assertEqual(len(registry["routes"]), 30)
        ordered = sorted(registry["routes"], key=lambda row: row["priority"])
        self.assertEqual(ordered[0]["route_id"], WORLDSET)
        self.assertEqual(ordered[1]["route_id"], EFFECT)
        self.assertTrue(ordered[0]["semantic_open_stops_fallback"])
        self.assertFalse(ordered[1]["semantic_open_stops_fallback"])

    def test_pointer_binds_current_immutable_registry(self):
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        registry = registry_router.load_registry()
        self.assertEqual(pointer["target"]["path"], "canonical/governance/R2_DIRECT_ROUTE_REGISTRY_20261009_V2.json")
        self.assertEqual(registry["route_count"], 30)

    def test_current_effective_universe_is_thirty_before_future_promotions(self):
        state = registry_router.effective_state()
        self.assertEqual(state["baseline_activation_route_count"], 30)
        self.assertEqual(state["legacy_selection_metadata_count"], 30)
        self.assertEqual(state["activation_auto_admitted_route_count"], 0)
        self.assertEqual(state["dynamic_admission_route_count"], 0)
        self.assertEqual(state["deployable_route_count"], 30)
        self.assertEqual(state["stale_selection_metadata_route_ids"], [])

    def test_semantic_open_barrier_stops_later_route_fallback(self):
        world = {
            "route_id": WORLDSET,
            "selection_class": registry_router.LEGACY_SELECTION_CLASS,
            "priority": 0,
            "semantic_open_stops_fallback": True,
        }
        effect = {
            "route_id": EFFECT,
            "selection_class": registry_router.LEGACY_SELECTION_CLASS,
            "priority": 1,
            "semantic_open_stops_fallback": False,
        }
        state = {
            "rows": [world, effect],
            "deployable_route_ids": [WORLDSET, EFFECT],
            "baseline_activation_route_ids": [WORLDSET, EFFECT],
            "legacy_selection_metadata_route_ids": [WORLDSET, EFFECT],
            "activation_auto_admitted_route_ids": [],
            "dynamic_admission_route_ids": [],
            "dynamic_shadowed_by_baseline_route_ids": [],
            "auto_admitted_route_ids": [],
            "stale_selection_metadata_route_ids": [],
            "deployable_route_count": 2,
            "baseline_activation_route_count": 2,
            "legacy_selection_metadata_count": 2,
            "activation_auto_admitted_route_count": 0,
            "dynamic_admission_route_count": 0,
            "auto_admitted_route_count": 0,
            "current_activation_path": "x",
            "current_activation_git_blob_sha": "y",
            "dynamic_admission_target_path": "z",
            "dynamic_admission_target_git_blob_sha": "w",
        }
        calls = []
        def fake_pf(row, request, repo_root):
            calls.append(row["route_id"])
            if row["route_id"] == WORLDSET:
                return {
                    "matched": False,
                    "direct_route_semantic_open": True,
                    "status": "OPEN__DECISION_CHANGING_WORLDSET",
                    "route_id": WORLDSET,
                }
            return {"matched": True, "route_id": EFFECT}
        with mock.patch.object(registry_router, "effective_state", return_value=state):
            with mock.patch.object(registry_router, "_preflight_row", side_effect=fake_pf):
                out = registry_router.preflight({"task_id": "t", "goal": "g"})
        self.assertTrue(out["direct_route_semantic_open"])
        self.assertEqual(out["route_id"], WORLDSET)
        self.assertEqual(calls, [WORLDSET])

    def test_fixed_point_uses_stable_dispatcher_not_v10_chain(self):
        source = FIXED_POINT.read_text(encoding="utf-8")
        self.assertIn(
            "from canonical.runtime import r2_direct_route_registry_v1 as direct_adequacy",
            source,
        )
        self.assertNotIn(
            "r2_direct_end_to_end_adequacy_v10 as direct_adequacy",
            source,
        )

    def test_future_route_growth_requires_no_fixed_source_or_registry_edit(self):
        catalog = registry_router.catalog()
        self.assertTrue(catalog["pass"])
        self.assertEqual(catalog["route_count"], 30)
        self.assertFalse(catalog["future_route_source_edit_required"])
        self.assertFalse(catalog["future_route_registry_edit_required"])
        self.assertFalse(catalog["future_route_current_r2_edit_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
