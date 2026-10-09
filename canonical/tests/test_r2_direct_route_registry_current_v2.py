from __future__ import annotations

import json
from pathlib import Path
import unittest
from unittest import mock

from canonical.runtime import r2_direct_route_registry_v1 as registry_router

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "canonical/governance/CURRENT_R2_DIRECT_ROUTE_REGISTRY.json"
FIXED_POINT = ROOT / "canonical/runtime/general_adequate_decision_fixed_point_v2.py"

EDGE = "DIRECT_ADEQUACY::CROSS_DOCUMENT_SEMANTIC_EDGE_LATTICE_V4"
NATURAL = "DIRECT_ADEQUACY::CROSS_DOCUMENT_NATURAL_EFFECT_LATTICE_V3"
COREF = "DIRECT_ADEQUACY::FINANCE_BOUNDED_COREFERENCE_AMBIGUITY_CONTROL_V1"
FIELD = "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_FIELD_LATTICE_V2"
SEMANTIC = "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V1"
SOURCE_RESIDUAL = "DIRECT_ADEQUACY::CROSS_DOCUMENT_SOURCE_RESIDUAL_FRONTIER_V1"
RESIDUAL = "DIRECT_ADEQUACY::CROSS_DOCUMENT_RESIDUAL_EFFECT_FRONTIER_V1"
WORLDSET = "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_WORLDSET_V1"


class R2DirectRouteRegistryCurrentV2Tests(unittest.TestCase):
    def test_current_registry_preserves_exact_v17_precedence_for_all_37_routes(self):
        registry = registry_router.load_registry()
        self.assertEqual(registry["route_count"], 37)
        self.assertEqual(len(registry["routes"]), 37)
        ordered = sorted(registry["routes"], key=lambda row: row["priority"])
        self.assertEqual(
            [row["route_id"] for row in ordered[:8]],
            [EDGE, NATURAL, COREF, FIELD, SEMANTIC, SOURCE_RESIDUAL, RESIDUAL, WORLDSET],
        )
        barriers = {row["route_id"]: row["semantic_open_stops_fallback"] for row in ordered[:8]}
        self.assertTrue(barriers[EDGE])
        self.assertTrue(barriers[NATURAL])
        self.assertFalse(barriers[COREF])
        self.assertTrue(barriers[FIELD])
        self.assertTrue(barriers[SEMANTIC])
        self.assertTrue(barriers[SOURCE_RESIDUAL])
        self.assertTrue(barriers[RESIDUAL])
        self.assertTrue(barriers[WORLDSET])

    def test_pointer_binds_current_immutable_registry(self):
        pointer = json.loads(POINTER.read_text(encoding="utf-8"))
        registry = registry_router.load_registry()
        self.assertEqual(
            pointer["target"]["path"],
            "canonical/governance/R2_DIRECT_ROUTE_REGISTRY_20261009_V3.json",
        )
        self.assertEqual(registry["route_count"], 37)

    def test_current_effective_universe_is_37_before_future_promotions(self):
        state = registry_router.effective_state()
        self.assertEqual(state["baseline_activation_route_count"], 37)
        self.assertEqual(state["legacy_selection_metadata_count"], 37)
        self.assertEqual(state["activation_auto_admitted_route_count"], 0)
        self.assertEqual(state["dynamic_admission_route_count"], 0)
        self.assertEqual(state["deployable_route_count"], 37)
        self.assertEqual(state["stale_selection_metadata_route_ids"], [])

    def test_top_semantic_open_barrier_stops_all_later_routes(self):
        edge = {
            "route_id": EDGE,
            "selection_class": registry_router.LEGACY_SELECTION_CLASS,
            "priority": 0,
            "semantic_open_stops_fallback": True,
        }
        natural = {
            "route_id": NATURAL,
            "selection_class": registry_router.LEGACY_SELECTION_CLASS,
            "priority": 1,
            "semantic_open_stops_fallback": True,
        }
        state = {
            "rows": [edge, natural],
            "deployable_route_ids": [EDGE, NATURAL],
            "baseline_activation_route_ids": [EDGE, NATURAL],
            "legacy_selection_metadata_route_ids": [EDGE, NATURAL],
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
            if row["route_id"] == EDGE:
                return {
                    "matched": False,
                    "direct_route_semantic_open": True,
                    "status": "OPEN__SEMANTIC_EDGE_LATTICE",
                    "route_id": EDGE,
                }
            return {"matched": True, "route_id": NATURAL}
        with mock.patch.object(registry_router, "effective_state", return_value=state):
            with mock.patch.object(registry_router, "_preflight_row", side_effect=fake_pf):
                out = registry_router.preflight({"task_id": "t", "goal": "g"})
        self.assertTrue(out["direct_route_semantic_open"])
        self.assertEqual(out["route_id"], EDGE)
        self.assertEqual(calls, [EDGE])

    def test_fixed_point_uses_stable_dispatcher_not_v17_chain(self):
        source = FIXED_POINT.read_text(encoding="utf-8")
        self.assertIn(
            "from canonical.runtime import r2_direct_route_registry_v1 as direct_adequacy",
            source,
        )
        self.assertNotIn(
            "r2_direct_end_to_end_adequacy_v17 as direct_adequacy",
            source,
        )

    def test_future_route_growth_requires_no_fixed_source_or_registry_edit(self):
        catalog = registry_router.catalog()
        self.assertTrue(catalog["pass"])
        self.assertEqual(catalog["route_count"], 37)
        self.assertFalse(catalog["future_route_source_edit_required"])
        self.assertFalse(catalog["future_route_registry_edit_required"])
        self.assertFalse(catalog["future_route_current_r2_edit_required"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
