from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest

CANONICAL = pathlib.Path(__file__).resolve().parents[1]
ROOT = CANONICAL.parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

runtime = load("astra_runtime_capsule_integration_test", CANONICAL/"runtime"/"astra_runtime.py")
guard = load("capsule_guard_integration_test", CANONICAL/"runtime"/"composition_state_capsule_guard_v2.py")

class Tests(unittest.TestCase):
    def test_capability_graph_execution_is_capsule_bound(self):
        mission = {"mission_id": "TEST-COMPOSITION-CAPSULE-RUNTIME"}
        step = {
            "id": "capsule-runtime",
            "capability_problem": {
                "initial_facts": ["repo.available"],
                "target_effects": ["record.verified"],
                "finish_summary": "CAPSULE_RUNTIME_COMPLETE",
                "capabilities": [
                    {
                        "id": "read",
                        "requires": ["repo.available"],
                        "provides": ["record.path"],
                        "cost": 1,
                        "action": {"type": "read_file", "args": {"path": "canonical/runtime/EXECUTOR_POLICY_V1.json"}},
                        "result_fields": ["path"],
                    },
                    {
                        "id": "verify",
                        "requires": ["record.path"],
                        "provides": ["record.verified"],
                        "cost": 1,
                        "action": {"type": "assert_file_exists", "args": {"path": {"$effect_result": {"effect": "record.path", "field": "path"}}}},
                        "result_fields": ["verified"],
                    },
                ],
            },
        }
        checkpoint = runtime._controller_checkpoint_path(step, mission)
        evidence = runtime.EVID_DIR/(checkpoint.stem+"__COMPOSITION_STATE_CAPSULE.json")
        checkpoint.unlink(missing_ok=True)
        evidence.unlink(missing_ok=True)
        try:
            out = runtime._run_capability_planned_goal(step, mission, "verify capsule runtime")
            self.assertEqual(out["final_summary"], "CAPSULE_RUNTIME_COMPLETE")
            bound = out["composition_state_capsule"]
            self.assertEqual(bound["status"], "PASS", bound)
            self.assertTrue(bound["declared_cross_capability_state_no_bypass"])
            self.assertEqual(out["planning_mode"], "DETERMINISTIC_CAPABILITY_GRAPH")
            self.assertTrue(evidence.is_file())
            cap = json.loads(evidence.read_text(encoding="utf-8"))
            verdict = guard.verify_capsule(cap)
            self.assertEqual(verdict["status"], "PASS", verdict)
            self.assertIn("record.path", verdict["latest"])
            self.assertIn("record.verified", verdict["latest"])
            self.assertIn("composition_capsule_head_hash", out["trace"][0])
            self.assertIn("composition_capsule_head_hash", out["trace"][1])
            self.assertNotIn("composition_capsule_head_hash", out["trace"][2])
        finally:
            checkpoint.unlink(missing_ok=True)
            evidence.unlink(missing_ok=True)

if __name__ == "__main__":
    unittest.main(verbosity=2)
