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

planner = load("planner_guard_v2_test", CANONICAL/"runtime"/"capability_planner.py")
guard = load("capsule_guard_v2_test", CANONICAL/"runtime"/"composition_state_capsule_guard_v2.py")

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
    def _first_step(self):
        p = planner.plan_actions(fixture())
        v = guard.validate_plan(p["actions"], p["composition_contract"], p["planning"]["initial_facts"])
        self.assertEqual(v["status"], "PASS")
        cap = guard.seed_capsule(p["planning"]["initial_facts"])
        row = p["composition_contract"][0]
        action = guard.resolve_action_from_capsule(cap, row, p["actions"][0])
        result = {"path": "canonical/runtime/EXECUTOR_POLICY_V1.json"}
        cap = guard.append_action_result(cap, row, action, result)
        return p, cap, action, result

    def test_reads_prior_state_from_capsule(self):
        p, cap, _, _ = self._first_step()
        row = p["composition_contract"][1]
        resolved = guard.resolve_action_from_capsule(cap, row, p["actions"][1])
        self.assertEqual(resolved["args"]["path"], "canonical/runtime/EXECUTOR_POLICY_V1.json")
        self.assertEqual(guard.verify_capsule(cap)["status"], "PASS")

    def test_trace_result_tamper_cannot_rebind_on_resume(self):
        p, cap, action, result = self._first_step()
        trace = [{"cycle": 0, "plan": action, "result": result, "composition_capsule_head_hash": cap["head_hash"]}]
        valid = guard.rebuild_valid_prefix(p["actions"], p["composition_contract"], p["planning"]["initial_facts"], trace)
        self.assertEqual(valid["valid_count"], 1)
        bad = copy.deepcopy(trace)
        bad[0]["result"]["path"] = "tampered/path"
        rebuilt = guard.rebuild_valid_prefix(p["actions"], p["composition_contract"], p["planning"]["initial_facts"], bad)
        self.assertEqual(rebuilt["valid_count"], 0)
        self.assertIn("CAPSULE_HEAD_MISMATCH", rebuilt["reason"])

    def test_recorded_plan_drift_fails_prefix(self):
        p, cap, action, result = self._first_step()
        trace = [{"cycle": 0, "plan": action, "result": result, "composition_capsule_head_hash": cap["head_hash"]}]
        bad = copy.deepcopy(trace)
        bad[0]["plan"]["args"]["path"] = "other"
        rebuilt = guard.rebuild_valid_prefix(p["actions"], p["composition_contract"], p["planning"]["initial_facts"], bad)
        self.assertEqual(rebuilt["valid_count"], 0)
        self.assertIn("RESOLVED_ACTION_DRIFT", rebuilt["reason"])

    def test_provider_binding_drift_fails_closed(self):
        p = planner.plan_actions(fixture())
        bad = copy.deepcopy(p["composition_contract"])
        bad[1]["provider_bindings"]["record.path"]["cycle"] = 99
        with self.assertRaisesRegex(guard.CompositionGuardError, "PROVIDER_BINDING_MISMATCH"):
            guard.validate_plan(p["actions"], bad, p["planning"]["initial_facts"])

    def test_undeclared_result_field_fails_closed(self):
        p = planner.plan_actions(fixture())
        bad_actions = copy.deepcopy(p["actions"])
        bad_actions[1]["args"]["path"]["$result"]["field"] = "undeclared"
        with self.assertRaisesRegex(guard.CompositionGuardError, "RESULT_REFERENCE_FIELD_UNDECLARED"):
            guard.validate_plan(bad_actions, p["composition_contract"], p["planning"]["initial_facts"])

    def test_capsule_v2_binds_action_producer_and_evidence(self):
        _, cap, _, _ = self._first_step()
        verdict = guard.verify_capsule(cap)
        self.assertEqual(verdict["status"], "PASS")
        self.assertTrue(verdict["evidence_is_content_bound"])
        self.assertTrue(verdict["action_is_content_bound"])
        self.assertTrue(verdict["producer_is_content_bound"])
        self.assertTrue(verdict["output_lineage_binds_action_and_producer"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
