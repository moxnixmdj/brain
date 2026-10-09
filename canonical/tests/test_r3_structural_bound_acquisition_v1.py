from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import astra_runtime
from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_improvement_queue_driver_v1 as driver
from canonical.runtime import r3_structural_bound_success_adapter_v1 as structural

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / structural.RULES_PATH
TMP = ROOT / "canonical" / "astra_runtime" / "tmp"


class R3StructuralBoundAcquisitionV1Tests(unittest.TestCase):
    def setUp(self):
        self._rules = RULES.read_bytes()
        RULES.write_text(json.dumps({
            "schema": "PROJECT_BRAIN_R3_STRUCTURAL_BOUND_ADAPTER_RULES_V1",
            "version": 1,
            "rules": [],
        }, indent=2) + "\n", encoding="utf-8")

    def tearDown(self):
        RULES.write_bytes(self._rules)

    def _observation(self, state_path: Path, work_dir: Path, *, replay_targets: bool = True, replay_initials: bool = True):
        cid = "cap.synthetic.structural"
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
            "mission_id": "structural-acquisition",
            "step_id": "controller",
            "plan_sha256": plan_sha,
            "status": "COMPLETE",
            "completed_actions": [
                {
                    "cycle": 0,
                    "plan": action,
                    "result": {
                        "pass": True,
                        "result_sha256": "1" * 64,
                        "composition_capsule_head_hash": "2" * 64,
                    },
                },
                {
                    "cycle": 1,
                    "plan": finish,
                    "result": {"summary": "COMPILED_TASK_COMPLETE"},
                },
            ],
        }
        cp = work_dir / "checkpoint.json"
        cp.write_text(json.dumps(checkpoint), encoding="utf-8")
        rel = cp.relative_to(ROOT).as_posix()
        out = {
            "schema": "TEST_STRUCTURAL_PROOF_BEARING_SUCCESS_V1",
            "status": "PASS__PROOF_BEARING_WRAPPER_MISMATCH",
            "pass": True,
            "task_id": "structural-acquisition",
            "selected_plan": [cid],
            "verified_initial_facts": ["seed"],
            "verified_target_effects": ["done"],
            "controller_checkpoint": {"path": rel, "plan_sha256": plan_sha},
            "execution": [{
                "capability_id": cid,
                "pass": True,
                "status": "PASS",
                "composition_capsule_head_hash": "2" * 64,
            }],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
            "semantic_acceptance_complete": False,
        }
        replay_problem = {
            "task_id": "structural-acquisition",
        }
        if replay_initials:
            replay_problem["initial_facts"] = ["seed"]
        if replay_targets:
            replay_problem["target_effects"] = ["done"]
        observed = learning.record_success_observation(
            out,
            surface="PROOF_BEARING_WRAPPER_MISMATCH",
            state_path=state_path,
            replay_context={
                "mode": "generic",
                "problem": replay_problem,
            },
        )
        self.assertTrue(observed["proof_available"], observed)
        self.assertTrue(observed["replayable"], observed)
        return observed

    def test_native_rule_acquisition_changes_adapter_only_and_reopens(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=TMP) as td:
            work_dir = Path(td)
            state_path = work_dir / "state.json"
            observed = self._observation(state_path, work_dir)
            oid = observed["observation_id"]

            parked = driver.advance_once(
                state_path=state_path,
                repo_root=ROOT,
            )
            self.assertEqual(
                parked["status"],
                "IMPROVEMENT_PARKED__CURRENT_OWNED_VERIFICATION_FRONTIER_INCOMPLETE",
                parked,
            )
            authority_before = driver._owned_success_verification_authority_sha256(
                repo_root=ROOT
            )

            acquired = driver.advance_once(
                state_path=state_path,
                repo_root=ROOT,
            )
            self.assertTrue(acquired["pass"], acquired)
            self.assertEqual(
                acquired["status"],
                "IMPROVEMENT_ADVANCED__SUCCESS_ADAPTER_FRONTIER_EXPANDED_AND_SUCCESS_REOPENED",
                acquired,
            )
            self.assertTrue(acquired["verification_authority_unchanged"], acquired)
            self.assertEqual(
                authority_before,
                driver._owned_success_verification_authority_sha256(repo_root=ROOT),
            )

            replay = learning.get_success_replay_context(
                oid, state_path=state_path
            )["context"]
            state = learning.load_state(state_path)
            observation = state["observations"][oid]
            candidate = structural.adapt(
                {
                    "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
                    "observation": observation,
                    "replay_context": replay,
                    "authority_requested": "CANDIDATE_ONLY",
                },
                repo_root=ROOT,
            )
            self.assertIsInstance(candidate, dict)
            self.assertTrue(candidate["candidate_only"])
            self.assertFalse(candidate["verification_authority"])
            self.assertFalse(candidate["promotion_authority"])
            self.assertEqual(
                candidate["problem"]["verification_kind"],
                "BOUND_CONTROLLER_CHECKPOINT_V1",
            )

    def test_native_rule_acquisition_recovers_exact_proved_target_effects(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=TMP) as td:
            work_dir = Path(td)
            state_path = work_dir / "state.json"
            observed = self._observation(
                state_path,
                work_dir,
                replay_targets=False,
            )
            oid = observed["observation_id"]

            parked = driver.advance_once(
                state_path=state_path,
                repo_root=ROOT,
            )
            self.assertEqual(
                parked["status"],
                "IMPROVEMENT_PARKED__CURRENT_OWNED_VERIFICATION_FRONTIER_INCOMPLETE",
                parked,
            )
            authority_before = driver._owned_success_verification_authority_sha256(
                repo_root=ROOT
            )

            acquired = driver.advance_once(
                state_path=state_path,
                repo_root=ROOT,
            )
            self.assertTrue(acquired["pass"], acquired)
            self.assertEqual(
                acquired["status"],
                "IMPROVEMENT_ADVANCED__SUCCESS_ADAPTER_FRONTIER_EXPANDED_AND_SUCCESS_REOPENED",
                acquired,
            )
            self.assertTrue(acquired["verification_authority_unchanged"], acquired)
            self.assertEqual(
                authority_before,
                driver._owned_success_verification_authority_sha256(repo_root=ROOT),
            )

            rules = json.loads(RULES.read_text(encoding="utf-8"))
            active = [row for row in rules["rules"] if row.get("status") == "ACTIVE"]
            self.assertEqual(len(active), 1, active)
            self.assertEqual(
                active[0]["normalization_profile"],
                structural.PROFILE_PROOF_TARGETS,
            )

            replay = learning.get_success_replay_context(
                oid, state_path=state_path
            )["context"]
            state = learning.load_state(state_path)
            observation = state["observations"][oid]
            candidate = structural.adapt(
                {
                    "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
                    "observation": observation,
                    "replay_context": replay,
                    "authority_requested": "CANDIDATE_ONLY",
                },
                repo_root=ROOT,
            )
            self.assertIsInstance(candidate, dict)
            self.assertEqual(
                candidate["structural_normalization_profile"],
                structural.PROFILE_PROOF_TARGETS,
            )
            self.assertEqual(
                candidate["problem"]["target_effects"],
                ["done"],
            )
            self.assertFalse(candidate["verification_authority"])
            self.assertFalse(candidate["promotion_authority"])


    def test_native_rule_acquisition_recovers_proved_initial_and_target_effects(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=TMP) as td:
            work_dir = Path(td)
            state_path = work_dir / "state.json"
            observed = self._observation(
                state_path,
                work_dir,
                replay_targets=False,
                replay_initials=False,
            )
            oid = observed["observation_id"]

            parked = driver.advance_once(
                state_path=state_path,
                repo_root=ROOT,
            )
            self.assertEqual(
                parked["status"],
                "IMPROVEMENT_PARKED__CURRENT_OWNED_VERIFICATION_FRONTIER_INCOMPLETE",
                parked,
            )
            authority_before = driver._owned_success_verification_authority_sha256(
                repo_root=ROOT
            )

            acquired = driver.advance_once(
                state_path=state_path,
                repo_root=ROOT,
            )
            self.assertTrue(acquired["pass"], acquired)
            self.assertEqual(
                acquired["status"],
                "IMPROVEMENT_ADVANCED__SUCCESS_ADAPTER_FRONTIER_EXPANDED_AND_SUCCESS_REOPENED",
                acquired,
            )
            self.assertTrue(acquired["verification_authority_unchanged"], acquired)
            self.assertEqual(
                authority_before,
                driver._owned_success_verification_authority_sha256(repo_root=ROOT),
            )

            rules = json.loads(RULES.read_text(encoding="utf-8"))
            active = [row for row in rules["rules"] if row.get("status") == "ACTIVE"]
            self.assertEqual(len(active), 1, active)
            self.assertEqual(
                active[0]["normalization_profile"],
                structural.PROFILE_PROOF_IO,
            )

            replay = learning.get_success_replay_context(
                oid, state_path=state_path
            )["context"]
            state = learning.load_state(state_path)
            observation = state["observations"][oid]
            request = {
                "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
                "observation": observation,
                "replay_context": replay,
                "authority_requested": "CANDIDATE_ONLY",
            }
            candidate = structural.adapt(request, repo_root=ROOT)
            self.assertIsInstance(candidate, dict)
            self.assertEqual(
                candidate["structural_normalization_profile"],
                structural.PROFILE_PROOF_IO,
            )
            self.assertEqual(candidate["problem"]["initial_facts"], ["seed"])
            self.assertEqual(candidate["problem"]["target_effects"], ["done"])
            self.assertFalse(candidate["verification_authority"])
            self.assertFalse(candidate["promotion_authority"])

            conflicted = deepcopy(replay)
            conflicted["problem"] = dict(conflicted["problem"])
            conflicted["problem"]["initial_facts"] = ["other-seed"]
            rejected = structural.adapt(
                {**request, "replay_context": conflicted},
                repo_root=ROOT,
            )
            self.assertIsNone(rejected)



if __name__ == "__main__":
    unittest.main(verbosity=2)
