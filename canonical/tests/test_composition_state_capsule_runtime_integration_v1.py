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
                "composition_c1_strict": True,
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
            self.assertEqual(
                bound["capsule_schema"],
                "PROJECT_BRAIN_COMPOSITION_STATE_CAPSULE_V2",
            )
            self.assertTrue(bound["content_bound_action_result_provenance"])
            self.assertTrue(bound["runtime_channel_receipts_complete"])
            self.assertTrue(bound["observed_file_ambient_channel_subset_closed"])
            self.assertEqual(
                bound["semantic_declaration_completeness"],
                "UNVERIFIED__RUNTIME_OBSERVATION_IS_NOT_A_SEMANTIC_SCOPE_PROOF",
            )
            self.assertEqual(
                bound["external_evidence_channel_completeness"],
                "UNVERIFIED__EXTERNAL_RUNTIME_CHANNELS_FORBIDDEN_BUT_REPO_EVIDENCE_PROVENANCE_NOT_SCOPE_COMPLETE",
            )
            self.assertEqual(
                bound["broader_runtime_channel_totality"],
                "CANDIDATE__STRICT_AUDITED_ACTION_SUBSET_ONLY",
            )
            self.assertTrue(bound["strict_runtime_channel_candidate_pass"])
            self.assertTrue(bound["rollback_scope_complete"])
            self.assertEqual(
                bound["rollback_policy"],
                "FAIL_CLOSED_ON_INVALID_PREFIX",
            )
            self.assertEqual(out["planning_mode"], "DETERMINISTIC_CAPABILITY_GRAPH")
            self.assertTrue(evidence.is_file())
            cap = json.loads(evidence.read_text(encoding="utf-8"))
            verdict = guard.verify_capsule(cap)
            self.assertEqual(verdict["status"], "PASS", verdict)
            self.assertIn("record.path", verdict["latest"])
            self.assertIn("record.verified", verdict["latest"])
            self.assertIn("composition_capsule_head_hash", out["trace"][0])
            self.assertIn("composition_capsule_head_hash", out["trace"][1])
            self.assertEqual(
                out["trace"][0]["composition_channel_receipt"]["status"],
                "PASS",
            )
            self.assertEqual(
                out["trace"][1]["composition_channel_receipt"]["status"],
                "PASS",
            )
            self.assertNotIn("composition_capsule_head_hash", out["trace"][2])

            drifted = json.loads(checkpoint.read_text(encoding="utf-8"))
            drifted["completed_actions"][0]["composition_capsule_head_hash"] = "0" * 64
            runtime.writej(checkpoint, drifted)
            with self.assertRaisesRegex(
                runtime.Blocker,
                "COMPOSITION_C1_STRICT_CAPSULE_PREFIX_INVALID",
            ):
                runtime._run_capability_planned_goal(
                    step, mission, "verify strict fail-closed resume"
                )
            preserved = json.loads(checkpoint.read_text(encoding="utf-8"))
            self.assertEqual(
                len(preserved["completed_actions"]),
                len(drifted["completed_actions"]),
            )
        finally:
            checkpoint.unlink(missing_ok=True)
            evidence.unlink(missing_ok=True)

if __name__ == "__main__":
    unittest.main(verbosity=2)
