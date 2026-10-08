from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import autonomous_verified_self_improvement_v1 as r3
from canonical.runtime import universal_verified_adaptive_solver_v12 as solver_v12
from canonical.runtime.unified_cognitive_fabric_v1 import catalog, run, ROOT


class UnifiedCognitiveFabricV1Tests(unittest.TestCase):
    def test_catalog_exposes_one_front_door_and_real_bound_registry(self):
        c = catalog()
        self.assertEqual(c["status"], "LIVE_FEDERATED_COGNITIVE_FABRIC")
        self.assertTrue(c["single_front_door"])
        self.assertGreaterEqual(c["verified_bound_capability_count"], 43)
        self.assertIn("RAW_GOAL", c["engines"])
        self.assertIn("ADEQUATE_DECISION", c["engines"])
        self.assertIn("ADAPTIVE_SOLVER", c["engines"])
        self.assertIn("LEARNING_EPISODE", c["engines"])
        self.assertFalse(c["all_historical_brain_capabilities_unified"])

    def test_raw_goal_routes_through_same_fabric(self):
        result = run({
            "mode": "RAW_GOAL",
            "payload": {
                "task_id": "FABRIC-UNKNOWN-RAW-001",
                "goal": "Calibrate the neutrino interferometer phase drift.",
            },
        })
        self.assertEqual(result["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertEqual(result["mode"], "RAW_GOAL")
        self.assertFalse(result["inner_pass"])
        self.assertEqual(
            result["result"]["failure_class"],
            "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP",
        )

    def test_decision_controller_is_live_through_same_front_door(self):
        result = run({
            "mode": "ADEQUATE_DECISION",
            "payload": {
                "task_id": "FABRIC-DECISION-OPEN-001",
                "goal": "Choose the adequate action.",
            },
        })
        self.assertEqual(result["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertFalse(result["inner_pass"])
        self.assertEqual(
            result["result"]["status"],
            "OPEN__DECISION_CONTEXT_REQUIRED",
        )

    def test_p3_is_live_through_same_front_door(self):
        result = run({
            "mode": "P3",
            "payload": {"context_id": "fabric-p3-invalid"},
        })
        self.assertEqual(result["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertEqual(result["mode"], "P3")
        self.assertFalse(result["inner_pass"])

    def test_r3_uses_current_solver_v12(self):
        self.assertIs(r3.solver_v12, solver_v12)

    def test_learning_episode_dispatches_and_persists_failure_diagnosis(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state.json"
            result = run({
                "mode": "LEARNING_EPISODE",
                "payload": {
                    "task_id": "FABRIC-LEARN-FAIL-001",
                    "initial_facts": [],
                    "target_effects": ["unreachable.effect"],
                    "capabilities": [],
                },
                "options": {
                    "state_path": str(state),
                    "episode_id": "fabric-episode-1",
                    "scope_id": "fabric-scope",
                    "max_capability_expansions": 0,
                },
            })
            self.assertEqual(result["status"], "FABRIC_DISPATCH_COMPLETE")
            self.assertFalse(result["inner_pass"])
            self.assertTrue(state.is_file())
            doc = json.loads(state.read_text(encoding="utf-8"))
            self.assertEqual(doc["schema"], "PROJECT_BRAIN_SELF_IMPROVEMENT_STATE_V1")
            self.assertGreaterEqual(doc["stats"]["failure_class_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
