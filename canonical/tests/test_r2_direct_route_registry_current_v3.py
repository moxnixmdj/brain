from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest import mock

from canonical.runtime import r2_direct_route_registry_v1 as router

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_REGISTRY.json"
FIXED_POINT = ROOT / "canonical/runtime/general_adequate_decision_fixed_point_v2.py"

LATTICE = "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V1"
SOURCE = "DIRECT_ADEQUACY::CROSS_DOCUMENT_SOURCE_RESIDUAL_FRONTIER_V1"
RESIDUAL = "DIRECT_ADEQUACY::CROSS_DOCUMENT_RESIDUAL_EFFECT_FRONTIER_V1"
WORLDSET = "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_WORLDSET_V1"
EFFECT = "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_COMPOSITION_V1"


class R2DirectRouteRegistryCurrentV3Tests(unittest.TestCase):
    def test_metadata_preserves_v13_precedence_for_all_current_routes(self):
        registry = router.load_registry()
        self.assertEqual(registry["route_count"], 33)
        ordered = sorted(registry["routes"], key=lambda row: row["priority"])
        self.assertEqual(
            [x["route_id"] for x in ordered[:5]],
            [LATTICE, SOURCE, RESIDUAL, WORLDSET, EFFECT],
        )
        self.assertEqual(
            [x["semantic_open_stops_fallback"] for x in ordered[:5]],
            [True, True, True, True, False],
        )
        self.assertEqual([x["priority"] for x in ordered], list(range(33)))

    def test_pointer_binds_v4_registry(self):
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        self.assertEqual(
            pointer["target"]["path"],
            "canonical/governance/R2_DIRECT_ROUTE_REGISTRY_20261009_V4.json",
        )
        self.assertEqual(router.load_registry()["route_count"], 33)

    def test_effective_universe_is_current_thirty_three_without_auto_admission(self):
        state = router.effective_state()
        self.assertEqual(state["baseline_activation_route_count"], 33)
        self.assertEqual(state["legacy_selection_metadata_count"], 33)
        self.assertEqual(state["activation_auto_admitted_route_count"], 0)
        self.assertEqual(state["dynamic_admission_route_count"], 0)
        self.assertEqual(state["deployable_route_count"], 33)
        self.assertEqual(state["auto_admitted_route_ids"], [])
        self.assertEqual(state["stale_selection_metadata_route_ids"], [])

    def test_lattice_semantic_open_barrier_stops_all_later_fallback(self):
        lattice = {
            "route_id": LATTICE,
            "selection_class": router.LEGACY_SELECTION_CLASS,
            "priority": 0,
            "semantic_open_stops_fallback": True,
        }
        source = {
            "route_id": SOURCE,
            "selection_class": router.LEGACY_SELECTION_CLASS,
            "priority": 1,
            "semantic_open_stops_fallback": True,
        }
        state = {
            "rows": [lattice, source],
            "deployable_route_ids": [LATTICE, SOURCE],
            "baseline_activation_route_ids": [LATTICE, SOURCE],
            "legacy_selection_metadata_route_ids": [LATTICE, SOURCE],
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
        calls: list[str] = []

        def fake_pf(row, request, repo_root):
            calls.append(row["route_id"])
            if row["route_id"] == LATTICE:
                return {
                    "matched": False,
                    "direct_route_semantic_open": True,
                    "route_id": LATTICE,
                    "status": "OPEN__EFFECT_SEMANTIC_LATTICE_REFINEMENT_REQUIRED",
                }
            return {"matched": True, "route_id": SOURCE}

        with mock.patch.object(router, "effective_state", return_value=state):
            with mock.patch.object(router, "_preflight_row", side_effect=fake_pf):
                out = router.preflight({"task_id": "t", "goal": "g"})
        self.assertTrue(out["direct_route_semantic_open"])
        self.assertEqual(out["route_id"], LATTICE)
        self.assertEqual(calls, [LATTICE])

    def test_fixed_point_uses_stable_dispatcher_not_v13_chain(self):
        source = FIXED_POINT.read_text(encoding="utf-8")
        self.assertIn(
            "from canonical.runtime import r2_direct_route_registry_v1 as direct_adequacy",
            source,
        )
        self.assertNotIn(
            "r2_direct_end_to_end_adequacy_v13 as direct_adequacy",
            source,
        )

    def test_catalog_reports_thirty_three_default_live_routes(self):
        out = router.catalog()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["route_count"], 33)
        self.assertFalse(out["future_route_source_edit_required"])
        self.assertFalse(out["future_route_registry_edit_required"])
        self.assertFalse(out["future_route_current_r2_edit_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
