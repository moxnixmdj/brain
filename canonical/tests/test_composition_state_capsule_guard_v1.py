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
        cap = guard.append_action_result(cap, p["composition_contract"][0], {"path": "canonical/runtime/EXECUTOR_POLICY_V1.json"})
        guard.assert_action_ready(cap, p["composition_contract"][1])
        cap = guard.append_action_result(cap, p["composition_contract"][1], {"verified": True})
        self.assertEqual(guard.verify_capsule(cap)["status"], "PASS")

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

    def test_requirement_binding_drift_fails_closed(self):
        p = planner.plan_actions(fixture())
        bad = copy.deepcopy(p["composition_contract"])
        bad[0]["requirement_bindings"]["repo.available"] = {
            "source": "capability",
            "cycle": 99,
            "capability_id": "ghost",
        }
        with self.assertRaisesRegex(
            guard.CompositionGuardError,
            "REQUIREMENT_BINDING_MISMATCH",
        ):
            guard.validate_plan(
                p["actions"], bad, p["planning"]["initial_facts"]
            )

    def test_capsule_is_authority_for_result_reference_resolution(self):
        p = planner.plan_actions(fixture())
        cap = guard.seed_capsule(p["planning"]["initial_facts"])
        provider_result = {
            "path": "canonical/runtime/EXECUTOR_POLICY_V1.json"
        }
        cap = guard.append_action_result(
            cap, p["composition_contract"][0], provider_result
        )
        action = guard.resolve_action_from_capsule(
            cap, p["composition_contract"][1], p["actions"][1]
        )
        self.assertEqual(
            action["args"]["path"],
            "canonical/runtime/EXECUTOR_POLICY_V1.json",
        )

    def test_existing_trace_without_checkpoint_capsule_fails_closed(self):
        p = planner.plan_actions(fixture())
        trace = [{
            "cycle": 0,
            "plan": p["actions"][0],
            "result": {"path": "tampered.json"},
        }]
        with self.assertRaisesRegex(
            guard.CompositionGuardError,
            "CHECKPOINT_CAPSULE_MISSING_FOR_EXISTING_TRACE",
        ):
            guard.bind_checkpoint(
                p["actions"],
                p["composition_contract"],
                p["planning"]["initial_facts"],
                {},
                trace,
            )

    def test_tampered_trace_cannot_redefine_checkpoint_capsule(self):
        p = planner.plan_actions(fixture())
        cap = guard.seed_capsule(p["planning"]["initial_facts"])
        provider_result = {
            "path": "canonical/runtime/EXECUTOR_POLICY_V1.json"
        }
        cap = guard.append_action_result(
            cap, p["composition_contract"][0], provider_result
        )
        trace = [{
            "cycle": 0,
            "plan": p["actions"][0],
            "result": {"path": "evil.json"},
            "composition_capsule_head_hash": cap["head_hash"],
        }]
        with self.assertRaisesRegex(
            guard.CompositionGuardError,
            "TRACE_CAPSULE_RESULT_MISMATCH",
        ):
            guard.bind_checkpoint(
                p["actions"],
                p["composition_contract"],
                p["planning"]["initial_facts"],
                {"composition_state_capsule": cap},
                trace,
            )

    def test_checkpoint_rewind_rolls_capsule_to_authenticated_prefix(self):
        p = planner.plan_actions(fixture())
        cap = guard.seed_capsule(p["planning"]["initial_facts"])
        provider_result = {
            "path": "canonical/runtime/EXECUTOR_POLICY_V1.json"
        }
        cap = guard.append_action_result(
            cap, p["composition_contract"][0], provider_result
        )
        first_head = cap["head_hash"]
        trace = [{
            "cycle": 0,
            "plan": p["actions"][0],
            "result": provider_result,
            "composition_capsule_head_hash": first_head,
        }]
        cap = guard.append_action_result(
            cap, p["composition_contract"][1], {"verified": True}
        )
        rebound = guard.bind_checkpoint(
            p["actions"],
            p["composition_contract"],
            p["planning"]["initial_facts"],
            {"composition_state_capsule": cap},
            trace,
        )
        verdict = guard.verify_capsule(rebound)
        self.assertEqual(rebound["head_hash"], first_head)
        self.assertIn("record.path", verdict["latest"])
        self.assertNotIn("record.verified", verdict["latest"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
