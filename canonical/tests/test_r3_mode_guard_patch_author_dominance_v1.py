from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_bound_success_adapter_v1 as bound
from canonical.runtime import r3_checkpoint_reconstruction_success_adapter_v1 as checkpoint
from canonical.runtime import r3_deterministic_mode_guard_patch_author_v1 as author
from canonical.runtime import r3_structural_bound_success_adapter_v1 as structural

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
    plan_sha = "a" * 64
    doc = {
        "schema": "PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1",
        "mission_id": "mode-guard-dominance",
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


def _request(work: Path, *, mode: str, include_targets: bool = True):
    checkpoint_path, plan_sha = _checkpoint(work)
    material = {
        "source_schema": "TEST_MODE_GUARD_DOMINANCE_V1",
        "source_status": "PASS",
        "task_id": "mode-guard-dominance",
        "selected_plan": ["cap.a", "cap.b"],
        "verified_target_effects": ["done"],
        "controller_checkpoint": {
            "path": checkpoint_path.relative_to(ROOT).as_posix(),
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
        "cognition_dependency_class": "DETERMINISTIC_ONLY",
        "model_dependency_count": 0,
        "semantic_acceptance_complete": False,
    }
    observation = {
        "observation_id": "observation:mode-guard-dominance",
        "proof_capsule": {
            "schema": "PROJECT_BRAIN_SUCCESS_PROOF_CAPSULE_V1",
            "sha256": learning._sha(material),
            "material": material,
            "secret_scan": "PASS",
        },
    }
    raw = {
        "task_id": "mode-guard-dominance",
        "initial_facts": ["seed", "external"],
    }
    if include_targets:
        raw["target_effects"] = ["done"]
    return {
        "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
        "observation": observation,
        "replay_context": {
            "mode": mode,
            "request": raw,
        },
        "authority_requested": "CANDIDATE_ONLY",
    }


def _patched_bound_equivalent(request):
    """Simulate the mode-guard-only patch without mutating source bytes."""
    normalized = deepcopy(request)
    normalized["replay_context"]["mode"] = "compiled_bound"
    return bound.adapt(normalized, repo_root=ROOT)


def _strip_structural_marker(candidate):
    out = deepcopy(dict(candidate))
    out.pop("structural_normalization_profile", None)
    return out


class R3ModeGuardPatchAuthorDominanceV1Tests(unittest.TestCase):
    def test_source_shape_proves_mode_normalization_is_exact_patch_semantics(self):
        source = (
            ROOT / "canonical/runtime/r3_bound_success_adapter_v1.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(source.count('replay.get("mode")'), 1)
        self.assertEqual(source.count(author.OLD_GUARD), 1)

    def test_replay_target_structural_preflight_equals_mode_guard_patch_candidate(self):
        TMP.mkdir(parents=True, exist_ok=True)
        self.assertEqual(
            set(author.SUPPORTED_NEW_MODES),
            {"generic", "specialized", "decision"},
        )
        for mode in sorted(author.SUPPORTED_NEW_MODES):
            with self.subTest(mode=mode), TemporaryDirectory(dir=TMP) as td:
                request = _request(Path(td), mode=mode, include_targets=True)
                patched = _patched_bound_equivalent(request)
                structural_candidate = structural.preflight(
                    request,
                    repo_root=ROOT,
                    normalization_profile=structural.PROFILE_REPLAY_TARGETS,
                )
                self.assertIsInstance(patched, dict)
                self.assertIsInstance(structural_candidate, dict)
                self.assertEqual(
                    structural_candidate["structural_normalization_profile"],
                    structural.PROFILE_REPLAY_TARGETS,
                )
                self.assertEqual(
                    _strip_structural_marker(structural_candidate),
                    patched,
                )

    def test_structural_proof_targets_is_strictly_stronger_when_replay_targets_missing(self):
        TMP.mkdir(parents=True, exist_ok=True)
        for mode in sorted(author.SUPPORTED_NEW_MODES):
            with self.subTest(mode=mode), TemporaryDirectory(dir=TMP) as td:
                request = _request(Path(td), mode=mode, include_targets=False)
                patched = _patched_bound_equivalent(request)
                replay_profile = structural.preflight(
                    request,
                    repo_root=ROOT,
                    normalization_profile=structural.PROFILE_REPLAY_TARGETS,
                )
                proof_profile = structural.preflight(
                    request,
                    repo_root=ROOT,
                    normalization_profile=structural.PROFILE_PROOF_TARGETS,
                )
                self.assertIsNone(patched)
                self.assertIsNone(replay_profile)
                self.assertIsInstance(proof_profile, dict)
                self.assertEqual(
                    proof_profile["problem"]["target_effects"],
                    ["done"],
                )
                self.assertEqual(
                    proof_profile["structural_normalization_profile"],
                    structural.PROFILE_PROOF_TARGETS,
                )

    def test_checkpoint_reconstruction_yields_to_structural_owner_for_this_class(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=TMP) as td:
            request = _request(
                Path(td),
                mode="specialized",
                include_targets=False,
            )
            structural_candidate = structural.preflight(
                request,
                repo_root=ROOT,
                normalization_profile=structural.PROFILE_PROOF_TARGETS,
            )
            checkpoint_candidate = checkpoint.adapt(request, repo_root=ROOT)
        self.assertIsInstance(structural_candidate, dict)
        self.assertEqual(
            structural_candidate["structural_normalization_profile"],
            structural.PROFILE_PROOF_TARGETS,
        )
        self.assertIsNone(checkpoint_candidate)

    def test_corrupt_checkpoint_is_not_fixed_by_mode_guard_patch(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=TMP) as td:
            request = _request(
                Path(td),
                mode="specialized",
                include_targets=True,
            )
            checkpoint_path = (
                ROOT
                / request["observation"]["proof_capsule"]["material"][
                    "controller_checkpoint"
                ]["path"]
            )
            doc = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            doc["status"] = "INCOMPLETE"
            checkpoint_path.write_text(json.dumps(doc), encoding="utf-8")
            patched = _patched_bound_equivalent(request)
            structural_candidate = structural.preflight(
                request,
                repo_root=ROOT,
            )
            checkpoint_candidate = checkpoint.adapt(request, repo_root=ROOT)
        self.assertIsNone(patched)
        self.assertIsNone(structural_candidate)
        self.assertIsNone(checkpoint_candidate)


if __name__ == "__main__":
    unittest.main(verbosity=2)
