from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

CANONICAL = pathlib.Path(__file__).resolve().parents[1]
RUNTIME_PATH = CANONICAL / "runtime" / "astra_runtime.py"
spec = importlib.util.spec_from_file_location(
    "astra_runtime_capsule_authority_test", RUNTIME_PATH
)
runtime = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runtime
spec.loader.exec_module(runtime)


class Tests(unittest.TestCase):
    mission_id = "TEST-CAPSULE-AUTHORITY-RUNTIME-V1"

    def tearDown(self):
        for root in (runtime.STATE_DIR, runtime.EVID_DIR):
            for path in root.glob(self.mission_id + "*"):
                path.unlink(missing_ok=True)

    def problem(self):
        return {
            "initial_facts": ["repo.available"],
            "target_effects": ["record.verified"],
            "restrict_inherited_bound_capabilities": True,
            "capabilities": [
                {
                    "id": "read",
                    "requires": ["repo.available"],
                    "provides": ["record.path"],
                    "cost": 1,
                    "action": {
                        "type": "read_file",
                        "args": {"path": "seed.json"},
                    },
                    "result_fields": ["path"],
                },
                {
                    "id": "verify",
                    "requires": ["record.path"],
                    "provides": ["record.verified"],
                    "cost": 1,
                    "action": {
                        "type": "assert_file_exists",
                        "args": {
                            "path": {
                                "$effect_result": {
                                    "effect": "record.path",
                                    "field": "path",
                                }
                            }
                        },
                    },
                    "result_fields": ["verified"],
                },
            ],
        }

    def test_capability_execution_never_uses_raw_trace_result_resolver(self):
        mission = {"mission_id": self.mission_id}
        step = {
            "id": "goal",
            "capability_problem": self.problem(),
        }
        observed = []

        def fake_goal_action(action):
            observed.append(action)
            if action.get("type") == "finish":
                return {
                    "type": "finish",
                    "summary": action["args"]["summary"],
                }
            if action.get("capability_id") == "read":
                return {"path": "trusted.json"}
            if action.get("capability_id") == "verify":
                self.assertEqual(action["args"]["path"], "trusted.json")
                return {"verified": True}
            raise AssertionError("unexpected action")

        with mock.patch.object(
            runtime,
            "_resolve_result_refs",
            side_effect=AssertionError("raw trace resolver is a forbidden bypass"),
        ), mock.patch.object(
            runtime,
            "_goal_action",
            side_effect=fake_goal_action,
        ):
            result = runtime._run_capability_planned_goal(
                step, mission, "execute capsule-authoritative capability graph"
            )

        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["planning_mode"], "DETERMINISTIC_CAPABILITY_GRAPH")
        self.assertEqual(result["composition_state_capsule"]["status"], "PASS")
        self.assertTrue(
            result["composition_state_capsule"][
                "declared_cross_capability_state_no_bypass"
            ]
        )
        self.assertEqual(observed[1]["args"]["path"], "trusted.json")

    def test_resume_rejects_trace_tamper_instead_of_rebuilding_trust(self):
        mission = {"mission_id": self.mission_id}
        problem = self.problem()
        planner = runtime._load_capability_planner()
        planned = planner.plan_actions(problem)
        actions = planned["actions"]
        step = {
            "id": "goal",
            "controller_actions": actions,
            "_composition_capsule_enforced": True,
            "_composition_contract": planned["composition_contract"],
            "_composition_initial_facts": planned["planning"]["initial_facts"],
            "interrupt_after_controller_actions_once": 1,
        }

        def fake_goal_action(action):
            if action.get("capability_id") == "read":
                return {"path": "trusted.json"}
            if action.get("capability_id") == "verify":
                return {"verified": True}
            return {"type": "finish", "summary": "DONE"}

        with mock.patch.object(runtime, "_goal_action", side_effect=fake_goal_action):
            with self.assertRaisesRegex(
                runtime.Blocker, "CONTROLLER_CHECKPOINT_TEST_INTERRUPTION"
            ):
                runtime._run_model_independent_goal(step, mission, "x")

        plan_sha = runtime._controller_plan_sha256(actions)
        checkpoint_path = runtime._controller_checkpoint_path(
            step, mission, plan_sha=plan_sha
        )
        checkpoint = runtime.readj(checkpoint_path)
        checkpoint["completed_actions"][0]["result"]["path"] = "evil.json"
        runtime.writej(checkpoint_path, checkpoint)

        step.pop("interrupt_after_controller_actions_once")
        with mock.patch.object(runtime, "_goal_action", side_effect=fake_goal_action):
            with self.assertRaisesRegex(
                runtime.Blocker,
                "COMPOSITION_STATE_CHECKPOINT_BINDING_FAILED:.*TRACE_CAPSULE_RESULT_MISMATCH",
            ):
                runtime._run_model_independent_goal(step, mission, "x")


if __name__ == "__main__":
    unittest.main(verbosity=2)
