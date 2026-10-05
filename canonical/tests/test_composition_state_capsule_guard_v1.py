from __future__ import annotations

import copy
import importlib.util
import pathlib
import sys
import unittest

CANONICAL = pathlib.Path(__file__).resolve().parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

planner = load("planner_guard_test", CANONICAL/"runtime"/"capability_planner.py")
guard = load("capsule_guard_test", CANONICAL/"runtime"/"composition_state_capsule_guard_v1.py")

def fixture():
    return {
        "initial_facts": ["repo.available"],
        "target_effects": ["record.verified"],
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
    }

class Tests(unittest.TestCase):
    def test_valid_contract_and_state_chain(self):
        p = planner.plan_actions(fixture())
        v = guard.validate_plan(p["actions"], p["composition_contract"], p["planning"]["initial_facts"])
        self.assertEqual(v["status"], "PASS")
        cap = guard.seed_capsule(p["planning"]["initial_facts"])
        cap = guard.append_action_result(
            cap,
            p["composition_contract"][0],
            p["actions"][0],
            {"path": "canonical/runtime/EXECUTOR_POLICY_V1.json"},
        )
        guard.assert_action_ready(cap, p["composition_contract"][1])
        cap = guard.append_action_result(
            cap,
            p["composition_contract"][1],
            p["actions"][1],
            {"verified": True},
        )
        verdict = guard.verify_capsule(cap)
        self.assertEqual(verdict["status"], "PASS")
        self.assertTrue(verdict["action_is_content_bound"])
        self.assertTrue(verdict["producer_is_content_bound"])
        self.assertTrue(verdict["output_lineage_binds_action_and_producer"])

    def test_executed_action_descriptor_is_load_bearing(self):
        p = planner.plan_actions(fixture())
        cap = guard.seed_capsule(p["planning"]["initial_facts"])
        bad_action = copy.deepcopy(p["actions"][0])
        bad_action["capability_id"] = "different"
        with self.assertRaisesRegex(
            guard.CompositionGuardError, "ACTION_CAPABILITY_ID_MISMATCH"
        ):
            guard.append_action_result(
                cap,
                p["composition_contract"][0],
                bad_action,
                {"path": "canonical/runtime/EXECUTOR_POLICY_V1.json"},
            )

    def test_provider_binding_drift_fails_closed(self):
        p = planner.plan_actions(fixture())
        bad = copy.deepcopy(p["composition_contract"])
        bad[1]["provider_bindings"]["record.path"]["cycle"] = 99
        with self.assertRaisesRegex(guard.CompositionGuardError, "PROVIDER_BINDING_MISMATCH"):
            guard.validate_plan(p["actions"], bad, p["planning"]["initial_facts"])

    def test_undeclared_extra_action_fails_closed(self):
        p = planner.plan_actions(fixture())
        actions = copy.deepcopy(p["actions"])
        actions.insert(-1, {"type": "read_file", "args": {"path": "canonical/runtime/EXECUTOR_POLICY_V1.json"}, "capability_id": "extra"})
        with self.assertRaisesRegex(guard.CompositionGuardError, "CONTRACT_ACTION_COUNT_MISMATCH"):
            guard.validate_plan(actions, p["composition_contract"], p["planning"]["initial_facts"])

    def test_resume_rebuild(self):
        p = planner.plan_actions(fixture())
        trace = [{"cycle": 0, "plan": p["actions"][0], "result": {"path": "canonical/runtime/EXECUTOR_POLICY_V1.json"}}]
        cap = guard.rebuild_from_trace(p["actions"], p["composition_contract"], p["planning"]["initial_facts"], trace)
        latest = guard.verify_capsule(cap)["latest"]
        self.assertIn("repo.available", latest)
        self.assertIn("record.path", latest)
        self.assertNotIn("record.verified", latest)

if __name__ == "__main__":
    unittest.main(verbosity=2)
