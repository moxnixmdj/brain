from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest import mock

from canonical.runtime import r2_direct_route_registry_v1 as router

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_REGISTRY.json"
FIXED_POINT = ROOT / "canonical/runtime/general_adequate_decision_fixed_point_v2.py"

RESIDUAL = "DIRECT_ADEQUACY::CROSS_DOCUMENT_RESIDUAL_EFFECT_FRONTIER_V1"
WORLDSET = "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_WORLDSET_V1"
EFFECT = "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_COMPOSITION_V1"
V12 = "DIRECT_ADEQUACY::CROSS_DOCUMENT_SOURCE_RESIDUAL_FRONTIER_V1"


class R2DirectRouteRegistryCurrentV2Tests(unittest.TestCase):
    def test_metadata_preserves_v11_precedence(self):
        registry = router.load_registry()
        self.assertEqual(registry["route_count"], 31)
        ordered = sorted(registry["routes"], key=lambda row: row["priority"])
        self.assertEqual([x["route_id"] for x in ordered[:3]], [RESIDUAL, WORLDSET, EFFECT])
        self.assertTrue(ordered[0]["semantic_open_stops_fallback"])
        self.assertTrue(ordered[1]["semantic_open_stops_fallback"])

    def test_pointer_binds_v3_registry(self):
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        self.assertEqual(
            pointer["target"]["path"],
            "canonical/governance/R2_DIRECT_ROUTE_REGISTRY_20261009_V3.json",
        )
        self.assertEqual(router.load_registry()["route_count"], 31)

    def test_effective_universe_adds_verified_v12_without_source_edit(self):
        state = router.effective_state()
        self.assertEqual(state["baseline_activation_route_count"], 31)
        self.assertEqual(state["dynamic_admission_route_count"], 1)
        self.assertEqual(state["deployable_route_count"], 32)
        self.assertEqual(state["dynamic_admission_route_ids"], [V12])
        row = next(x for x in state["rows"] if x["route_id"] == V12)
        self.assertTrue(row["semantic_open_stops_fallback"])
        self.assertTrue(row["automatic_live_admission"])

    def test_authorized_dynamic_semantic_open_stops_legacy_fallback(self):
        dynamic = {
            "route_id": V12,
            "selection_class": router.DYNAMIC_SELECTION_CLASS,
            "activation_index": 31,
            "semantic_open_stops_fallback": True,
        }
        legacy = {
            "route_id": RESIDUAL,
            "selection_class": router.LEGACY_SELECTION_CLASS,
            "priority": 0,
        }
        state = {
            "rows": [dynamic, legacy],
            "deployable_route_ids": [V12, RESIDUAL],
            "baseline_activation_route_ids": [RESIDUAL],
            "legacy_selection_metadata_route_ids": [RESIDUAL],
            "activation_auto_admitted_route_ids": [],
            "dynamic_admission_route_ids": [V12],
            "dynamic_shadowed_by_baseline_route_ids": [],
            "auto_admitted_route_ids": [V12],
            "stale_selection_metadata_route_ids": [],
            "deployable_route_count": 2,
            "baseline_activation_route_count": 1,
            "legacy_selection_metadata_count": 1,
            "activation_auto_admitted_route_count": 0,
            "dynamic_admission_route_count": 1,
            "auto_admitted_route_count": 1,
            "current_activation_path": "x",
            "current_activation_git_blob_sha": "y",
            "dynamic_admission_target_path": "z",
            "dynamic_admission_target_git_blob_sha": "w",
        }
        calls = []
        def fake_pf(row, request, repo_root):
            calls.append(row["route_id"])
            if row["route_id"] == V12:
                return {
                    "matched": False,
                    "direct_route_semantic_open": True,
                    "route_id": V12,
                    "status": "NOT_APPLICABLE__COMBINED_SOURCE_SEMANTICS_OPEN",
                }
            return {"matched": True, "route_id": RESIDUAL}
        with mock.patch.object(router, "effective_state", return_value=state):
            with mock.patch.object(router, "_preflight_row", side_effect=fake_pf):
                out = router.preflight({"task_id": "t", "goal": "g"})
        self.assertTrue(out["direct_route_semantic_open"])
        self.assertEqual(out["route_id"], V12)
        self.assertEqual(calls, [V12])

    def test_fixed_point_uses_stable_dispatcher(self):
        source = FIXED_POINT.read_text(encoding="utf-8")
        self.assertIn(
            "from canonical.runtime import r2_direct_route_registry_v1 as direct_adequacy",
            source,
        )
        self.assertNotIn(
            "r2_direct_end_to_end_adequacy_v12 as direct_adequacy",
            source,
        )

    def test_catalog_reports_32_default_live_routes(self):
        out = router.catalog()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["route_count"], 32)
        self.assertFalse(out["future_route_source_edit_required"])
        self.assertFalse(out["future_route_registry_edit_required"])
        self.assertFalse(out["future_route_current_r2_edit_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
