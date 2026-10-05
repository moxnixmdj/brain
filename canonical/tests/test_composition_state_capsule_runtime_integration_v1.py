from __future__ import annotations

import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from canonical.runtime import astra_runtime as runtime


class CompositionStateCapsuleRuntimeIntegrationTests(unittest.TestCase):
    def _step(self, *, bad_ref=False, wrong_cycle=False):
        ref = {
            "$result": {
                "cycle": 7 if wrong_cycle else 0,
                "field": "items",
                **({} if bad_ref else {"effect": "tree.available"}),
            }
        }
        return {
            "_composition_state_capsule_v1": {
                "initial_facts": [],
                "enforcement": "REQUIRED_FOR_ALL_NON_FINISH_CAPABILITY_ACTIONS",
            },
            "controller_actions": [
                {
                    "type": "list_tree",
                    "args": {"prefix": "canonical"},
                    "capability_id": "producer",
                    "_capability_contract": {
                        "requires": [],
                        "provides": ["tree.available"],
                        "result_fields": ["items"],
                    },
                },
                {
                    "type": "write_json_records",
                    "args": {
                        "output_path": "canonical/astra_runtime/tmp/capsule-test.json",
                        "fields": ["items"],
                        "records": [{"items": ref}],
                    },
                    "capability_id": "consumer",
                    "_capability_contract": {
                        "requires": ["tree.available"],
                        "provides": ["record.written"],
                        "result_fields": ["output_path"],
                    },
                },
                {
                    "type": "finish",
                    "args": {"summary": "CAPSULE_PLAN_COMPLETE"},
                },
            ],
        }

    def _run(self, step):
        observed = []

        def fake_goal_action(action):
            observed.append(action)
            if action["type"] == "list_tree":
                return {"type": "list_tree", "items": ["canonical/a"], "truncated": False}
            if action["type"] == "write_json_records":
                return {
                    "type": "write_json_records",
                    "verified": True,
                    "output_path": "canonical/astra_runtime/tmp/capsule-test.json",
                }
            if action["type"] == "finish":
                return {"type": "finish", "summary": "CAPSULE_PLAN_COMPLETE"}
            raise AssertionError(action)

        checkpoint = {"completed_actions": []}
        with (
            mock.patch.object(
                runtime,
                "_load_controller_checkpoint",
                return_value=(pathlib.Path("checkpoint.json"), checkpoint, False),
            ),
            mock.patch.object(
                runtime,
                "_write_controller_checkpoint",
                side_effect=lambda path, data, trace, status="IN_PROGRESS": {
                    **data,
                    "completed_actions": list(trace),
                    "status": status,
                },
            ),
            mock.patch.object(runtime, "_goal_action", side_effect=fake_goal_action),
        ):
            result = runtime._run_model_independent_goal(step, {"mission_id": "capsule-test"}, "goal")
        return result, observed

    def test_capability_plan_resolves_cross_role_value_only_through_capsule(self):
        result, observed = self._run(self._step())
        self.assertEqual(observed[1]["args"]["records"], [{"items": ["canonical/a"]}])
        capsule = result["composition_state_capsule"]
        self.assertEqual(capsule["status"], "PASS")
        self.assertEqual(capsule["record_count"], 2)
        self.assertTrue(capsule["head_hash"])
        self.assertEqual(
            result["trace"][0]["composition_capsule_head_hash"],
            result["trace"][0]["composition_capsule_head_hash"],
        )

    def test_unbound_raw_result_reference_fails_closed(self):
        with self.assertRaisesRegex(
            runtime.Blocker,
            "COMPOSITION_RESULT_REFERENCE_NOT_EFFECT_BOUND",
        ):
            self._run(self._step(bad_ref=True))

    def test_provider_cycle_mismatch_fails_closed(self):
        with self.assertRaisesRegex(
            runtime.Blocker,
            "COMPOSITION_RESULT_REFERENCE_BINDING_MISMATCH",
        ):
            self._run(self._step(wrong_cycle=True))

    def test_checkpoint_replay_reconstructs_and_checks_capsule_head(self):
        result, _ = self._run(self._step())
        trace = result["trace"][:2]
        module = runtime._load_composition_state_capsule()
        rebuilt = runtime._composition_capsule_from_trace(module, [], trace)
        self.assertEqual(
            rebuilt["head_hash"],
            trace[-1]["composition_capsule_head_hash"],
        )
        tampered = [dict(x) for x in trace]
        tampered[-1] = dict(tampered[-1])
        tampered[-1]["composition_capsule_head_hash"] = "0" * 64
        with self.assertRaisesRegex(
            runtime.Blocker,
            "COMPOSITION_CHECKPOINT_CAPSULE_HEAD_MISMATCH",
        ):
            runtime._composition_capsule_from_trace(module, [], tampered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
