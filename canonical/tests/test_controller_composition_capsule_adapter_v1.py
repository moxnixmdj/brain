from __future__ import annotations

import copy
import importlib.util
import pathlib
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
ADAPTER_PATH = ROOT / "canonical" / "runtime" / "controller_composition_capsule_adapter_v1.py"
RUNTIME_PATH = ROOT / "canonical" / "runtime" / "astra_runtime.py"

adapter_spec = importlib.util.spec_from_file_location(
    "controller_composition_capsule_adapter_v1_test", ADAPTER_PATH
)
adapter = importlib.util.module_from_spec(adapter_spec)
adapter_spec.loader.exec_module(adapter)

runtime_spec = importlib.util.spec_from_file_location(
    "astra_runtime_controller_capsule_test", RUNTIME_PATH
)
runtime = importlib.util.module_from_spec(runtime_spec)
runtime_spec.loader.exec_module(runtime)


class ControllerCompositionCapsuleAdapterTests(unittest.TestCase):
    def test_explicit_result_flow_is_capsule_authoritative(self):
        capsule = adapter.empty_capsule(ROOT)
        first_raw = {"type": "synthetic", "args": {"seed": "alpha"}}
        first_result = {"value": 42, "status": "PASS"}
        capsule = adapter.append_cycle(
            capsule,
            cycle=0,
            raw_action=first_raw,
            resolved_action=first_raw,
            result=first_result,
            root=ROOT,
        )

        second_raw = {
            "type": "synthetic",
            "args": {"x": {"$result": {"cycle": 0, "field": "value"}}},
        }
        adapter.assert_no_prior_state_bypass(second_raw, capsule)
        resolved = adapter.resolve_result_refs(second_raw, capsule, ROOT)
        self.assertEqual(resolved["args"]["x"], 42)
        second_result = {"observed": resolved["args"]["x"]}
        capsule = adapter.append_cycle(
            capsule,
            cycle=1,
            raw_action=second_raw,
            resolved_action=resolved,
            result=second_result,
            root=ROOT,
        )
        trace = [
            {"cycle": 0, "plan": first_raw, "result": first_result},
            {"cycle": 1, "plan": resolved, "result": second_result},
        ]
        verdict = adapter.verify_controller_state(capsule, trace, ROOT)
        self.assertEqual(verdict["status"], "PASS")
        self.assertEqual(verdict["record_count"], 2)

    def test_literal_prior_durable_path_bypass_is_rejected(self):
        path = ROOT / "canonical" / "astra_runtime" / "tmp" / "CAPSULE_BYPASS_TEST.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"value":1}', encoding="utf-8")
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        rel = str(path.relative_to(ROOT)).replace("\\", "/")

        capsule = adapter.empty_capsule(ROOT)
        first_raw = {"type": "synthetic", "args": {}}
        first_result = {"result_path": rel}
        capsule = adapter.append_cycle(
            capsule,
            cycle=0,
            raw_action=first_raw,
            resolved_action=first_raw,
            result=first_result,
            root=ROOT,
        )

        bypass = {"type": "synthetic", "args": {"input_path": rel}}
        with self.assertRaisesRegex(
            adapter.ControllerCapsuleError,
            "CONTROLLER_STATE_PROVENANCE_BYPASS",
        ):
            adapter.assert_no_prior_state_bypass(bypass, capsule)

        explicit = {
            "type": "synthetic",
            "args": {
                "input_path": {
                    "$result": {"cycle": 0, "field": "result_path"}
                }
            },
        }
        adapter.assert_no_prior_state_bypass(explicit, capsule)
        resolved = adapter.resolve_result_refs(explicit, capsule, ROOT)
        self.assertEqual(resolved["args"]["input_path"], rel)

    def test_durable_artifact_drift_fails_closed(self):
        path = ROOT / "canonical" / "astra_runtime" / "tmp" / "CAPSULE_DRIFT_TEST.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"value":"alpha"}', encoding="utf-8")
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        rel = str(path.relative_to(ROOT)).replace("\\", "/")

        capsule = adapter.empty_capsule(ROOT)
        raw = {"type": "synthetic", "args": {}}
        result = {"output_path": rel}
        capsule = adapter.append_cycle(
            capsule,
            cycle=0,
            raw_action=raw,
            resolved_action=raw,
            result=result,
            root=ROOT,
        )
        trace = [{"cycle": 0, "plan": raw, "result": result}]
        self.assertEqual(
            adapter.verify_controller_state(capsule, trace, ROOT)["status"],
            "PASS",
        )

        path.write_text('{"value":"mutated"}', encoding="utf-8")
        verdict = adapter.verify_controller_state(capsule, trace, ROOT)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("DURABLE_EVIDENCE_DRIFT", verdict["reason"])

    def test_capsule_payload_tamper_fails_closed(self):
        capsule = adapter.empty_capsule(ROOT)
        raw = {"type": "synthetic", "args": {"seed": "alpha"}}
        result = {"value": "alpha"}
        capsule = adapter.append_cycle(
            capsule,
            cycle=0,
            raw_action=raw,
            resolved_action=raw,
            result=result,
            root=ROOT,
        )
        bad = copy.deepcopy(capsule)
        bad["records"][0]["values"][adapter.result_key(0)]["value"] = "forged"
        trace = [{"cycle": 0, "plan": raw, "result": result}]
        verdict = adapter.verify_controller_state(bad, trace, ROOT)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("CAPSULE_VERIFY", verdict["reason"])

    def test_future_result_reference_is_rejected(self):
        capsule = adapter.empty_capsule(ROOT)
        raw = {
            "type": "synthetic",
            "args": {"x": {"$result": {"cycle": 1, "field": "value"}}},
        }
        with self.assertRaisesRegex(
            adapter.ControllerCapsuleError,
            "RESULT_REFERENCE_NONCAUSAL:1",
        ):
            adapter.append_cycle(
                capsule,
                cycle=0,
                raw_action=raw,
                resolved_action={"type": "synthetic", "args": {"x": 1}},
                result={"value": 1},
                root=ROOT,
            )

    def test_capability_planner_route_mandates_capsule_v2(self):
        class Planner:
            @staticmethod
            def plan_actions(problem):
                return {
                    "actions": [{"type": "finish", "args": {"summary": "DONE"}}],
                    "planning": {"status": "PLANNED"},
                }

        problem = {
            "initial_facts": [],
            "target_effects": [],
            "capabilities": [],
        }
        captured = {}

        def fake_run(step, mission, goal):
            captured.update(step)
            return {
                "adapter": "goal",
                "returncode": 0,
                "stdout": "DONE",
                "controller_mode": "MODEL_INDEPENDENT_ACTION_PLAN",
                "planner_source": None,
                "planner_transport": None,
                "planner_model_last": None,
            }

        with mock.patch.object(runtime, "_capability_problem", return_value=problem), \
             mock.patch.object(runtime, "_inherit_verified_capabilities", side_effect=lambda x: x), \
             mock.patch.object(runtime, "_load_capability_planner", return_value=Planner()), \
             mock.patch.object(runtime, "_run_model_independent_goal", side_effect=fake_run):
            result = runtime._run_capability_planned_goal(
                {"max_controller_actions": 4},
                {"mission_id": "TEST-CAPSULE-PLANNER-ACTIVATION"},
                "test",
            )
        self.assertTrue(captured["_composition_capsule_v2_enforced"])
        self.assertEqual(result["planning_mode"], "DETERMINISTIC_CAPABILITY_GRAPH")


if __name__ == "__main__":
    unittest.main()
