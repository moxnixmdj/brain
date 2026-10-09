from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_checkpoint_reconstruction_success_adapter_v1 as adapter

ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical" / "astra_runtime" / "tmp"


def _checkpoint(work: Path):
    action_a = {
        "type": "invoke_verified_bound_capability_adapter",
        "args": {
            "capability_id": "cap.a",
            "requires": ["seed"],
            "provides": ["mid"],
        },
    }
    action_b = {
        "type": "invoke_verified_bound_capability_adapter",
        "args": {
            "capability_id": "cap.b",
            "requires": ["mid", "external"],
            "provides": ["done"],
        },
    }
    finish = {"type": "finish", "args": {"summary": "DONE"}}
    from canonical.runtime import astra_runtime

    plan_sha = astra_runtime._controller_plan_sha256(
        [action_a, action_b, finish]
    )
    doc = {
        "schema": "PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1",
        "mission_id": "checkpoint-reconstruct",
        "step_id": "controller",
        "plan_sha256": plan_sha,
        "status": "COMPLETE",
        "completed_actions": [
            {
                "cycle": 0,
                "plan": action_a,
                "result": {
                    "pass": True,
                    "result_sha256": "1" * 64,
                    "composition_capsule_head_hash": "2" * 64,
                },
            },
            {
                "cycle": 1,
                "plan": action_b,
                "result": {
                    "pass": True,
                    "result_sha256": "3" * 64,
                    "composition_capsule_head_hash": "4" * 64,
                },
            },
            {
                "cycle": 2,
                "plan": finish,
                "result": {"summary": "DONE"},
            },
        ],
    }
    path = work / "checkpoint.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path, plan_sha


def _request(work: Path, *, targets):
    checkpoint, plan_sha = _checkpoint(work)
    material = {
        "source_schema": "TEST_WRAPPED_BOUND_SUCCESS_V1",
        "source_status": "PASS",
        "task_id": "checkpoint-reconstruct",
        "selected_plan": ["cap.a", "cap.b"],
        "verified_target_effects": list(targets),
        "controller_checkpoint": {
            "path": checkpoint.relative_to(ROOT).as_posix(),
            "plan_sha256": plan_sha,
        },
        "execution": [
            {
                "capability_id": "cap.a",
                "pass": True,
                "status": "PASS",
                "composition_capsule_head_hash": "2" * 64,
            },
            {
                "capability_id": "cap.b",
                "pass": True,
                "status": "PASS",
                "composition_capsule_head_hash": "4" * 64,
            },
        ],
        "semantic_acceptance_complete": False,
    }
    observation = {
        "observation_id": "observation:checkpoint-reconstruct",
        "proof_capsule": {
            "schema": "PROJECT_BRAIN_SUCCESS_PROOF_CAPSULE_V1",
            "sha256": learning._sha(material),
            "material": material,
            "secret_scan": "PASS",
        },
    }
    return {
        "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
        "observation": observation,
        "replay_context": {
            "mode": "specialized",
        },
        "authority_requested": "CANDIDATE_ONLY",
    }


class CheckpointReconstructionAdapterTests(unittest.TestCase):
    def test_reconstructs_minimal_conservative_preconditions(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=TMP) as td:
            out = adapter.adapt(
                _request(Path(td), targets=["done"]),
                repo_root=ROOT,
            )
        self.assertIsInstance(out, dict)
        self.assertEqual(
            out["status"],
            "CHECKPOINT_RECONSTRUCTION_SUCCESS_EPISODE_CANDIDATE_READY",
        )
        self.assertEqual(out["reconstructed_preconditions"], ["seed", "external"])
        self.assertEqual(out["reconstructed_postconditions"], ["done"])
        episode = out["solver_output"]["current_episode"]
        self.assertEqual(episode["preconditions"], ["seed", "external"])
        self.assertEqual(episode["postconditions"], ["done"])
        self.assertTrue(out["candidate_only"])
        self.assertFalse(out["verification_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_rejects_retained_target_not_produced_by_verified_plan(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=TMP) as td:
            out = adapter.adapt(
                _request(Path(td), targets=["ghost"]),
                repo_root=ROOT,
            )
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
