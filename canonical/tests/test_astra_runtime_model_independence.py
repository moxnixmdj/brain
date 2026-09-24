#!/usr/bin/env python3
import importlib.util
import pathlib
import unittest
from unittest import mock

CANONICAL_ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH = CANONICAL_ROOT / "runtime" / "astra_runtime.py"
spec = importlib.util.spec_from_file_location("astra_runtime", RUNTIME_PATH)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

class ModelIndependenceTests(unittest.TestCase):
    def test_goal_completes_with_model_planner_forbidden(self):
        mission = {"goal": "Verify model-independent bounded goal execution."}
        step = {
            "goal_ref": "goal",
            "controller_actions": [
                {"type": "search_text", "args": {"query": "MODEL_NON_DEPENDENCE_LAW_V1"}},
                {"type": "read_file", "args": {"path": "canonical/laws/MODEL_NON_DEPENDENCE_LAW_V1.md"}},
                {"type": "finish", "args": {"summary": "MODEL_INDEPENDENT_GOAL_COMPLETE"}}
            ]
        }
        with mock.patch.object(runtime, "_planner_post", side_effect=AssertionError("model planner must not be called")):
            result = runtime.run_goal(step, mission)
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["controller_mode"], "MODEL_INDEPENDENT_ACTION_PLAN")
        self.assertIsNone(result["planner_model_last"])
        self.assertIn("MODEL_INDEPENDENT_GOAL_COMPLETE", result["stdout"])

    def test_goal_without_controller_plan_fails_closed(self):
        with self.assertRaisesRegex(runtime.Blocker, "MODEL_INDEPENDENT_CONTROLLER_PLAN_REQUIRED"):
            runtime.run_goal({}, {"goal": "No implicit model fallback is allowed."})

    def test_model_planner_is_explicit_opt_in_only(self):
        planned = '{"actions":[{"type":"finish","args":{"summary":"OPTIONAL_MODEL_ROUTE_USED"},"why":"explicit opt-in"}]}'
        with mock.patch.object(runtime, "_planner_post", return_value={"text": planned, "model": "stub", "duration_s": 0, "errors": []}):
            result = runtime.run_goal(
                {"allow_optional_model_planner": True, "max_cycles": 1},
                {"goal": "Use optional model route only because this step explicitly opts in."}
            )
        self.assertEqual(result["controller_mode"], "OPTIONAL_MODEL_ADVISORY")
        self.assertEqual(result["planner_model_last"], "stub")
        self.assertIn("OPTIONAL_MODEL_ROUTE_USED", result["stdout"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
