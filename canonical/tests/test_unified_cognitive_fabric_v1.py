from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import autonomous_verified_self_improvement_v1 as r3
from canonical.runtime import universal_verified_adaptive_solver_v12 as solver_v12
from canonical.runtime.unified_cognitive_fabric_v1 import catalog, run


class UnifiedCognitiveFabricV1Tests(unittest.TestCase):
    def test_catalog_exposes_single_front_door(self):
        c = catalog()
        self.assertEqual(c["status"], "LIVE_FEDERATED_COGNITIVE_FABRIC")
        self.assertTrue(c["single_front_door"])
        self.assertGreaterEqual(c["verified_bound_capability_count"], 43)
        self.assertIn("RAW_GOAL", c["engines"])
        self.assertIn("ADEQUATE_DECISION", c["engines"])
        self.assertIn("ADAPTIVE_SOLVER", c["engines"])
        self.assertIn("LEARNING_EPISODE", c["engines"])
        self.assertFalse(c["all_historical_brain_capabilities_unified"])

    def test_raw_goal_dispatches(self):
        out = run({
            "mode": "RAW_GOAL",
            "payload": {
                "task_id": "FABRIC-RAW-UNKNOWN-001",
                "goal": "Calibrate the neutrino interferometer phase drift.",
            },
        })
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertFalse(out["inner_pass"])
        self.assertEqual(out["result"]["failure_class"], "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP")

    def test_decision_dispatches(self):
        out = run({
            "mode": "ADEQUATE_DECISION",
            "payload": {
                "task_id": "FABRIC-DECISION-OPEN-001",
                "goal": "Choose the adequate action.",
            },
        })
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertFalse(out["inner_pass"])
        self.assertEqual(out["result"]["status"], "OPEN__DECISION_CONTEXT_REQUIRED")

    def test_r3_uses_current_solver_v12(self):
        self.assertIs(r3.solver_v12, solver_v12)

    def test_learning_episode_persists_failure_diagnosis(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state.json"
            out = run({
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
            self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
            self.assertFalse(out["inner_pass"])
            self.assertTrue(state.is_file())
            doc = json.loads(state.read_text(encoding="utf-8"))
            self.assertGreaterEqual(doc["stats"]["failure_class_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
