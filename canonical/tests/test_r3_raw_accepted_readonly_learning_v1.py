from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tarfile
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import astra_runtime, goal_compiler
from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_independent_learning_verifier_v1 as independent
from canonical.runtime import r3_raw_success_adapter_v1 as adapter
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.raw_goal_archive_acceptance_v1 import (
    CAPABILITY,
    verify as verify_raw_acceptance,
)
from canonical.runtime.universal_solver_episode_verification_authenticator_v1 import (
    authenticate as authenticate_episode,
)


class R3RawAcceptedReadonlyLearningV1Tests(unittest.TestCase):
    def material(self, root: Path):
        (root / "canonical").mkdir(parents=True, exist_ok=True)
        source = root / "canonical/source.txt"
        manifest = root / "manifest.json"
        output = root / "bundle.tar.gz"
        source.write_text("raw accepted learning", encoding="utf-8")
        manifest.write_text(
            json.dumps({"records": [{"verification_paths": ["canonical/source.txt"]}]}),
            encoding="utf-8",
        )
        goal = (
            "Create a tar.gz archive from the manifest manifest.json, including all its "
            "verification_paths files, and save it to bundle.tar.gz."
        )
        registry = load_verified_registry()
        admissible = goal_compiler._platform_admissible_registry(dict(registry))
        compiled = goal_compiler.compile_goal(goal, admissible, root)
        self.assertEqual(compiled["selected_capability"], CAPABILITY)
        inputs = dict(compiled["inputs"])
        action = goal_compiler._render_template(
            admissible[CAPABILITY]["action_template"],
            inputs,
        )
        finish = {"type": "finish", "args": {"summary": "RAW_GOAL_COMPLETE"}}
        plans = [action, finish]
        plan_sha = astra_runtime._controller_plan_sha256(plans)

        with tarfile.open(output, "w:gz") as archive:
            archive.add(manifest, arcname="manifest.json")
            archive.add(source, arcname="canonical/source.txt")
        source_hashes = {
            "canonical/source.txt": sha256(source.read_bytes()).hexdigest(),
            "manifest.json": sha256(manifest.read_bytes()).hexdigest(),
        }
        inner = {
            "output_verified": True,
            "output_path": "bundle.tar.gz",
            "output_sha256": sha256(output.read_bytes()).hexdigest(),
            "members": ["canonical/source.txt", "manifest.json"],
            "member_count": 2,
            "source_sha256": source_hashes,
        }
        completed = [
            {"cycle": 0, "plan": action, "result": inner},
            {"cycle": 1, "plan": finish, "result": {"summary": "RAW_GOAL_COMPLETE"}},
        ]
        checkpoint = {
            "schema": "PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1",
            "mission_id": "raw-task",
            "step_id": "live-raw-goal-controller",
            "plan_sha256": plan_sha,
            "status": "COMPLETE",
            "completed_actions": completed,
        }
        checkpoint_path = root / "checkpoint.json"
        checkpoint_path.write_text(json.dumps(checkpoint), encoding="utf-8")

        raw_contract = compile_contract(
            goal,
            source_id="user",
            routing_target_effects=list(compiled["target_effects"]),
        )
        execution = {
            "capability_id": CAPABILITY,
            "pass": True,
            "status": "PASS__MODEL_INDEPENDENT_CONTROLLER_ACTION",
            "result": inner,
            "execution_proof_type": "MODEL_INDEPENDENT_CONTROLLER_TRACE_V1",
            "controller_plan_sha256": plan_sha,
            "controller_trace": completed,
        }
        acceptance = verify_raw_acceptance(
            goal=goal,
            capability_id=CAPABILITY,
            inputs=inputs,
            execution=execution,
            raw_contract=raw_contract,
            root=root,
        )
        self.assertTrue(acceptance["pass"], acceptance)
        output_record = {
            "schema": "PROJECT_BRAIN_LIVE_INTEGRATED_BRAIN_V1",
            "status": "PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED",
            "pass": True,
            "task_id": "raw-task",
            "selected_plan": [CAPABILITY],
            "execution": [{
                "capability_id": CAPABILITY,
                "pass": True,
                "status": "PASS__MODEL_INDEPENDENT_CONTROLLER_ACTION",
                "composition_capsule_head_hash": None,
            }],
            "controller_checkpoint": {
                "path": "checkpoint.json",
                "plan_sha256": plan_sha,
            },
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
            "raw_goal_sha256": raw_contract["task_sha256"],
            "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
            "raw_acceptance_obligation_count": len(
                raw_contract["acceptance_contract"]["required_obligation_ids"]
            ),
            "accepted_raw_obligation_ids": list(acceptance["accepted_obligation_ids"]),
            "raw_goal_acceptance": acceptance,
            "semantic_acceptance_complete": True,
        }
        proof = learning._make_success_proof_capsule(output_record)
        self.assertIsInstance(proof, dict)
        observation = {
            "observation_id": "observation:raw-accepted",
            "proof_capsule": proof,
        }
        replay = {
            "mode": "raw_bound",
            "request": {"task_id": "raw-task", "goal": goal},
        }
        return output_record, observation, replay, output

    def test_success_capsule_retains_exact_raw_acceptance_receipt(self):
        with TemporaryDirectory() as td:
            out, _, _, _ = self.material(Path(td))
            proof = learning._make_success_proof_capsule(out)
            self.assertTrue(proof["material"]["semantic_acceptance_complete"])
            self.assertEqual(
                proof["material"]["raw_goal_acceptance"],
                out["raw_goal_acceptance"],
            )

    def test_semantically_complete_raw_success_authenticates_readonly(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _, observation, replay, _ = self.material(root)
            adapted = adapter.adapt(
                {"observation": observation, "replay_context": replay},
                repo_root=root,
            )
            self.assertIsInstance(adapted, dict)
            solver = adapted["solver_output"]
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
            self.assertEqual(
                auth["authenticated_episode"]["scope_id"],
                "raw-goal-sha256:" + adapted["problem"]["goal_sha256"],
            )

    def test_post_success_archive_tampering_blocks_learning(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _, observation, replay, output = self.material(root)
            adapted = adapter.adapt(
                {"observation": observation, "replay_context": replay},
                repo_root=root,
            )
            output.write_bytes(b"tampered")
            solver = adapted["solver_output"]
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
            self.assertIsNone(binding)

    def test_execution_success_without_semantic_acceptance_remains_nonlearnable(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            _, observation, replay, _ = self.material(root)
            observation["proof_capsule"]["material"]["semantic_acceptance_complete"] = False
            observation["proof_capsule"]["material"]["raw_goal_acceptance"] = None
            self.assertIsNone(
                adapter.adapt(
                    {"observation": observation, "replay_context": replay},
                    repo_root=root,
                )
            )

    def test_semantically_complete_success_without_receipt_fails_proof_capture(self):
        with self.assertRaises(learning.SelfImprovementError):
            learning._make_success_proof_capsule({
                "pass": True,
                "selected_plan": ["x"],
                "controller_checkpoint": {"path": "x", "plan_sha256": "0" * 64},
                "semantic_acceptance_complete": True,
            })


if __name__ == "__main__":
    unittest.main(verbosity=2)
