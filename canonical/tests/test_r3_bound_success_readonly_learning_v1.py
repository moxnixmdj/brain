from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

from canonical.runtime import astra_runtime
from canonical.runtime import r3_bound_success_adapter_v1 as adapter
from canonical.runtime import r3_bound_success_checkpoint_verifier_v1 as verifier
from canonical.runtime import r3_independent_learning_verifier_v1 as independent
from canonical.runtime import r3_improvement_queue_driver_v1 as driver
from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime.universal_solver_episode_verification_authenticator_v1 import (
    authenticate as authenticate_episode,
)


class R3BoundSuccessReadonlyLearningV1Tests(unittest.TestCase):
    def material(self, root: Path):
        artifact = root / "artifact.bin"
        artifact.write_bytes(b"verified-bound-success")
        artifact_sha = sha256(artifact.read_bytes()).hexdigest()
        cid = "cap.test"
        inner = {
            "output_path": "artifact.bin",
            "output_sha256": artifact_sha,
        }
        prepared = {
            "capability_id": cid,
            "instance_id": cid,
            "requires": ["seed"],
            "provides": ["done"],
            "result_fields": [],
            "inputs": {"value": 7},
            "inputs_sha256": "1" * 64,
            "registry_file_sha256": "2" * 64,
            "registry_entry_sha256": "3" * 64,
            "rendered_action_sha256": "4" * 64,
            "rendered_action": {
                "type": "invoke_capability",
                "args": {"capability_id": cid},
            },
        }
        result = {
            "pass": True,
            "inputs_sha256": prepared["inputs_sha256"],
            "registry_file_sha256": prepared["registry_file_sha256"],
            "registry_entry_sha256": prepared["registry_entry_sha256"],
            "rendered_action_sha256": prepared["rendered_action_sha256"],
            "rendered_action": deepcopy(prepared["rendered_action"]),
            "result_sha256": verifier._sha(inner),
            "result": inner,
            "execution_trace": {"trace": [{"proof": "already-verified"}]},
            "composition_capsule_head_hash": "5" * 64,
        }
        action = {
            "type": "invoke_verified_bound_capability_adapter",
            "args": {
                "capability_id": cid,
                "inputs": {"value": 7},
                "instance_id": cid,
                "requires": ["seed"],
                "provides": ["done"],
                "result_fields": [],
            },
            "expect": {"type": "field_equals", "field": "pass", "value": True},
        }
        finish = {"type": "finish", "args": {"summary": "COMPILED_TASK_COMPLETE"}}
        plan_sha = astra_runtime._controller_plan_sha256([action, finish])
        checkpoint = {
            "schema": "PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1",
            "mission_id": "task-1",
            "step_id": "live-compiled-task-controller",
            "plan_sha256": plan_sha,
            "status": "COMPLETE",
            "completed_actions": [
                {"cycle": 0, "plan": action, "result": result},
                {"cycle": 1, "plan": finish, "result": {"summary": "COMPILED_TASK_COMPLETE"}},
            ],
        }
        checkpoint_path = root / "checkpoint.json"
        checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
        proof = {
            "schema": "PROJECT_BRAIN_SUCCESS_PROOF_CAPSULE_V1",
            "material": {
                "source_schema": "PROJECT_BRAIN_LIVE_INTEGRATED_BRAIN_V1",
                "source_status": "PASS__REAL_TASK_PLANNED_EXECUTED_AND_REVERIFIED",
                "task_id": "task-1",
                "selected_plan": [cid],
                "verified_target_effects": ["done"],
                "controller_checkpoint": {
                    "path": "checkpoint.json",
                    "plan_sha256": plan_sha,
                },
                "execution": [{
                    "capability_id": cid,
                    "pass": True,
                    "status": "PASS",
                    "composition_capsule_head_hash": "5" * 64,
                }],
                "cognition_dependency_class": "MODEL_INDEPENDENT",
                "model_dependency_count": 0,
                "semantic_acceptance_complete": True,
            },
        }
        observation = {
            "observation_id": "observation:test",
            "proof_capsule": proof,
        }
        replay = {
            "mode": "compiled_bound",
            "request": {
                "task_id": "task-1",
                "initial_facts": ["seed"],
                "target_effects": ["done"],
                "capability_inputs": {cid: {"value": 7}},
            },
        }
        return observation, replay, prepared

    def test_adapter_and_readonly_verifier_accept_unchanged_bound_success(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            observation, replay, prepared = self.material(root)
            adapted = adapter.adapt(
                {"observation": observation, "replay_context": replay},
                repo_root=root,
            )
            self.assertIsInstance(adapted, dict)
            solver = adapted["solver_output"]
            with (
                mock.patch.object(
                    verifier.astra_runtime,
                    "_controller_checkpoint_record_valid",
                    return_value=True,
                ),
                mock.patch.object(
                    verifier.bound_adapter,
                    "prepare",
                    return_value=prepared,
                ),
                mock.patch.object(
                    verifier.bound_adapter,
                    "inspect",
                    return_value={"entry": {"cost": 1}},
                ),
                mock.patch.object(
                    verifier,
                    "verify_bound_execution",
                    return_value={
                        "pass": True,
                        "verified_output": {"capsule_head_hash": "5" * 64},
                    },
                ),
            ):
                out = verifier.verify_material(
                    problem=adapted["problem"],
                    episode=solver["current_episode"],
                    trace=solver["trace"],
                    fact_capsule_head_hash=solver["state_capsule_head_hash"],
                    value_capsule_head_hash=solver["value_capsule_head_hash"],
                    repo_root=root,
                )
            self.assertTrue(out["pass"], out)
            self.assertFalse(out["execution_replayed"])
            self.assertTrue(out["effect_outcomes_reverified"])

    def test_artifact_tampering_blocks_success_learning(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            observation, replay, prepared = self.material(root)
            adapted = adapter.adapt(
                {"observation": observation, "replay_context": replay},
                repo_root=root,
            )
            (root / "artifact.bin").write_bytes(b"tampered")
            solver = adapted["solver_output"]
            with (
                mock.patch.object(
                    verifier.astra_runtime,
                    "_controller_checkpoint_record_valid",
                    return_value=True,
                ),
                mock.patch.object(verifier.bound_adapter, "prepare", return_value=prepared),
                mock.patch.object(
                    verifier.bound_adapter,
                    "inspect",
                    return_value={"entry": {"cost": 1}},
                ),
                mock.patch.object(
                    verifier,
                    "verify_bound_execution",
                    return_value={
                        "pass": True,
                        "verified_output": {"capsule_head_hash": "5" * 64},
                    },
                ),
            ):
                out = verifier.verify_material(
                    problem=adapted["problem"],
                    episode=solver["current_episode"],
                    trace=solver["trace"],
                    fact_capsule_head_hash=solver["state_capsule_head_hash"],
                    value_capsule_head_hash=solver["value_capsule_head_hash"],
                    repo_root=root,
                )
            self.assertFalse(out["pass"])
            self.assertIn("DURABLE_ARTIFACT_HASH_MISMATCH", out["reason"])

    def test_adapter_rejects_raw_bound_without_complete_semantic_acceptance(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            observation, replay, _ = self.material(root)
            replay["mode"] = "raw_bound"
            observation["proof_capsule"]["material"]["semantic_acceptance_complete"] = False
            self.assertIsNone(
                adapter.adapt(
                    {"observation": observation, "replay_context": replay},
                    repo_root=root,
                )
            )

    def test_semantically_accepted_raw_bound_success_adapts_and_reverifies(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            cid = "archive.tar_gz.create_from_manifest"
            action = {
                "type": "invoke_capability",
                "args": {
                    "capability_id": cid,
                    "manifest_path": "manifest.json",
                    "output_path": "bundle.tar.gz",
                },
            }
            finish = {"type": "finish", "args": {"summary": "RAW_GOAL_COMPLETE"}}
            plan_sha = astra_runtime._controller_plan_sha256([action, finish])
            raw_result = {
                "output_verified": True,
                "output_path": "bundle.tar.gz",
                "output_sha256": "a" * 64,
            }
            checkpoint = {
                "schema": "PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1",
                "mission_id": "raw-task",
                "step_id": "live-raw-goal-controller",
                "plan_sha256": plan_sha,
                "status": "COMPLETE",
                "completed_actions": [
                    {"cycle": 0, "plan": action, "result": raw_result},
                    {"cycle": 1, "plan": finish, "result": {"summary": "RAW_GOAL_COMPLETE"}},
                ],
            }
            checkpoint_path = root / "checkpoint.json"
            checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")
            acceptance = {
                "schema": "PROJECT_BRAIN_RAW_GOAL_ARCHIVE_ACCEPTANCE_V1",
                "pass": True,
                "status": "PASS__EXACT_RAW_GOAL_ARCHIVE_ACCEPTED",
                "goal_sha256": "b" * 64,
                "task_contract_sha256": "c" * 64,
                "accepted_obligation_ids": ["o1"],
                "verified_output_path": "bundle.tar.gz",
                "verified_output_sha256": "a" * 64,
                "verified_archive_members": ["manifest.json"],
                "semantic_acceptance_complete": True,
                "acceptance_scope": "EXACT_ARCHIVE_MANIFEST_VERIFICATION_PATHS_GOAL_ONLY",
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }
            observation = {
                "observation_id": "observation:raw",
                "proof_capsule": {
                    "schema": "PROJECT_BRAIN_SUCCESS_PROOF_CAPSULE_V1",
                    "material": {
                        "source_schema": "PROJECT_BRAIN_LIVE_INTEGRATED_BRAIN_V1",
                        "source_status": "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED",
                        "task_id": "raw-task",
                        "selected_plan": [cid],
                        "controller_checkpoint": {
                            "path": "checkpoint.json",
                            "plan_sha256": plan_sha,
                        },
                        "semantic_acceptance_complete": True,
                        "raw_goal_sha256": "b" * 64,
                        "raw_task_contract_sha256": "c" * 64,
                        "raw_acceptance_obligation_count": 1,
                        "accepted_raw_obligation_ids": ["o1"],
                        "compiled_capability_id": cid,
                        "raw_goal_acceptance": acceptance,
                    },
                },
            }
            replay = {
                "mode": "raw_bound",
                "request": {
                    "task_id": "raw-task",
                    "goal": (
                        "Create a tar.gz archive from the manifest manifest.json, "
                        "including all its verification_paths files, and save it to bundle.tar.gz."
                    ),
                },
            }
            registry = {
                cid: {
                    "status": "VERIFIED_BOUND_CAPABILITY",
                    "requires": ["manifest.json.available"],
                    "provides": ["archive.tar_gz.create_from_manifest"],
                    "incremental_spend_usd": 0,
                }
            }
            with mock.patch.object(adapter, "load_verified_registry", return_value=registry):
                adapted = adapter.adapt(
                    {"observation": observation, "replay_context": replay},
                    repo_root=root,
                )
            self.assertIsInstance(adapted, dict)
            self.assertEqual(
                adapted["problem"]["verification_kind"],
                adapter.RAW_BOUND_VERIFICATION_KIND,
            )
            solver = adapted["solver_output"]
            recomputed_contract = {
                "pass": True,
                "task_sha256": "b" * 64,
                "task_contract_sha256": "c" * 64,
            }
            with (
                mock.patch.object(verifier, "load_verified_registry", return_value=registry),
                mock.patch.object(verifier, "compile_contract", return_value=recomputed_contract),
                mock.patch.object(verifier, "verify_raw_acceptance", return_value=acceptance),
            ):
                out = verifier.verify_material(
                    problem=adapted["problem"],
                    episode=solver["current_episode"],
                    trace=solver["trace"],
                    fact_capsule_head_hash=solver["state_capsule_head_hash"],
                    value_capsule_head_hash=solver["value_capsule_head_hash"],
                    repo_root=root,
                )
            self.assertTrue(out["pass"], out)
            self.assertFalse(out["execution_replayed"])
            self.assertTrue(out["effect_outcomes_reverified"])

    def test_standard_episode_authenticator_accepts_bound_readback_receipt(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            observation, replay, _ = self.material(root)
            adapted = adapter.adapt(
                {"observation": observation, "replay_context": replay},
                repo_root=root,
            )
            solver = adapted["solver_output"]
            with mock.patch.object(
                independent.bound_success_verifier,
                "verify_material",
                return_value={
                    "pass": True,
                    "status": "PASS",
                    "verification_basis": "BOUND_CONTROLLER_CHECKPOINT_AND_DURABLE_ARTIFACT_READBACK_V1",
                },
            ):
                binding = independent.verify_episode_request(
                    {
                        "kind": "EPISODE_VERIFICATION",
                        "problem": adapted["problem"],
                        "episode": solver["current_episode"],
                        "trace": solver["trace"],
                        "fact_capsule_head_hash": solver["state_capsule_head_hash"],
                        "value_capsule_head_hash": solver["value_capsule_head_hash"],
                    },
                    repo_root=root,
                )
            self.assertIsInstance(binding, dict)
            auth = authenticate_episode(
                binding,
                problem=adapted["problem"],
                episode=solver["current_episode"],
                trace=solver["trace"],
                fact_capsule_head_hash=solver["state_capsule_head_hash"],
                value_capsule_head_hash=solver["value_capsule_head_hash"],
                repo_root=root,
            )
            self.assertTrue(auth["pass"], auth)
            self.assertTrue(auth["effect_outcomes_reverified"])

    def test_queue_uses_internal_success_adapter_by_default(self):
        with TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            state = learning._empty_state()
            learning._enqueue_improvement(
                state,
                kind="ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE",
                priority=50,
                identity={"surface": "COMPILED_BOUND"},
                payload={
                    "observation_id": "observation:test",
                    "required_result": "VERIFIED_EPISODE_OR_PROVED_NONLEARNABLE_SUCCESS",
                },
            )
            learning._refresh_stats(state)
            learning._write_state(state, state_path)

            with (
                mock.patch.object(
                    driver,
                    "_adapt_success_work",
                    return_value={
                        "schema": driver.SCHEMA,
                        "status": "IMPROVEMENT_ADVANCED__SUCCESS_BECAME_VERIFIED_EPISODE",
                        "pass": True,
                        "work_id": "x",
                        "terminal_authority": False,
                    },
                ) as adapt_work,
                mock.patch(
                    "canonical.runtime.r3_bound_success_adapter_v1.adapt",
                    return_value={"candidate": True},
                ),
            ):
                out = driver.advance_once(state_path=state_path, repo_root=Path(td))
            self.assertTrue(out["pass"], out)
            self.assertTrue(out["progress"], out)
            provider = adapt_work.call_args.kwargs["success_episode_adapter_provider"]
            self.assertTrue(callable(provider))


if __name__ == "__main__":
    unittest.main(verbosity=2)
