from __future__ import annotations

import tempfile
from pathlib import Path
import unittest
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import live_brain_runtime_v1 as brain


FAILURE = {
    "pass": False,
    "status": "FAIL__CAPABILITY_OR_TASK_CONTRACT_GAP",
    "failure_class": "MISSING_CAPABILITY_OR_COMPILED_TASK_CONTRACT",
    "attempts": [],
    "counterexamples": [],
    "falsified_capability_ids": [],
    "deferred_capability_ids": [],
}


class VerifiedRepairReplayLoopV1Tests(unittest.TestCase):
    def temp_state(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        return Path(td.name) / "state.json"

    def seed_failure(self, path, *, task_id="t1"):
        retry = {
            "mode": "raw_bound",
            "request": {"task_id": task_id, "goal": "do the original obligation"},
            "learn": True,
        }
        out = learning.integrate_solver_output(
            FAILURE,
            state_path=path,
            retry_context=retry,
        )
        return out["diagnosis"]["failure_fingerprint"], out["retry_capsule_sha256"], retry

    def component(self):
        effect = "repair.capability.available"
        return {
            "id": "repairer",
            "kind": "MECHANISM",
            "requires": [],
            "provides": [effect],
            "verified": True,
            "brain_owned": True,
            "donor_independent": True,
            "cost": {
                "wall_clock": 1,
                "incremental_spend_usd": 0,
                "persistent_bits": 1,
                "risk": 0,
            },
            "executable_capability": {
                "id": "repairer",
                "requires": [],
                "provides": [effect],
                "cost": 1,
                "action": {"type": "verified_policy"},
                "effect_semantics_binding": {},
            },
        }

    def architecture(self):
        effect = "repair.capability.available"
        return {
            "pass": True,
            "classification": "ARCHITECTURE_FOUND",
            "winner": {
                "components": ["repairer"],
                "provided_target_effects": [effect],
            },
            "alternatives": [],
        }

    def test_failure_persists_content_addressed_retry_capsule(self):
        path = self.temp_state()
        fid, retry_sha, retry = self.seed_failure(path)
        recovered = learning.get_failure_retry_context(
            fid, state_path=path, retry_capsule_sha256=retry_sha
        )
        self.assertEqual(recovered["context"], retry)
        self.assertFalse(recovered["resolved"])

        second = learning.integrate_solver_output(
            FAILURE,
            state_path=path,
            retry_context=retry,
        )
        self.assertEqual(second["retry_capsule_sha256"], retry_sha)
        state = learning.load_state(path)
        self.assertEqual(len(state["failures"][fid]["retry_capsules"]), 1)
        self.assertEqual(state["failures"][fid]["count"], 2)

    def test_retry_capsule_rejects_obvious_secret_keys(self):
        path = self.temp_state()
        with self.assertRaisesRegex(
            learning.SelfImprovementError,
            "RETRY_CONTEXT_SENSITIVE_KEY_REJECTED",
        ):
            learning.integrate_solver_output(
                FAILURE,
                state_path=path,
                retry_context={
                    "mode": "raw_bound",
                    "request": {"task_id": "t", "api_key": "must-not-persist"},
                },
            )

    def test_repair_receipt_resolves_only_target_retry_instance(self):
        path = self.temp_state()
        fid, sha1, _ = self.seed_failure(path, task_id="t1")
        _, sha2, _ = self.seed_failure(path, task_id="t2")
        self.assertNotEqual(sha1, sha2)
        receipt = learning.record_repair_outcome(
            fid,
            retry_capsule_sha256=sha1,
            repair_record={"repair": "x"},
            original_replay_pass=True,
            state_path=path,
        )
        self.assertTrue(receipt["retry_instance_resolved"])
        self.assertEqual(receipt["unresolved_retry_instance_count"], 1)
        state = learning.load_state(path)
        caps = state["failures"][fid]["retry_capsules"]
        self.assertTrue(caps[sha1]["resolved"])
        self.assertFalse(caps[sha2]["resolved"])

    def test_verified_repair_counts_only_after_original_obligation_replay_passes(self):
        path = self.temp_state()
        fid, retry_sha, _ = self.seed_failure(path)
        with (
            mock.patch.object(brain, "_causal_synthesize", return_value=self.architecture()),
            mock.patch.object(
                brain,
                "_v12_run",
                return_value={
                    "pass": True,
                    "status": "SOLVED__EPISODE_VERIFICATION_REQUIRED",
                },
            ),
            mock.patch.object(
                brain,
                "_raw_bound_run",
                return_value={"pass": True, "status": "PASS__ORIGINAL_OBLIGATION"},
            ) as replay,
        ):
            out = brain.execute_failure_repair_cycle(
                {
                    "failure_fingerprint": fid,
                    "retry_capsule_sha256": retry_sha,
                    "components": [self.component()],
                    "initial_facts": [],
                },
                state_path=path,
            )

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "REPAIR_VERIFIED_BY_ORIGINAL_OBLIGATION_REPLAY",
        )
        self.assertTrue(out["repair_execution"]["pass"])
        self.assertTrue(out["original_replay"]["pass"])
        replay.assert_called_once()
        state = learning.load_state(path)
        self.assertTrue(
            state["failures"][fid]["retry_capsules"][retry_sha]["resolved"]
        )

    def test_repair_effect_without_original_replay_success_stays_unresolved(self):
        path = self.temp_state()
        fid, retry_sha, _ = self.seed_failure(path)
        with (
            mock.patch.object(brain, "_causal_synthesize", return_value=self.architecture()),
            mock.patch.object(
                brain,
                "_v12_run",
                return_value={
                    "pass": True,
                    "status": "SOLVED__EPISODE_VERIFICATION_REQUIRED",
                },
            ),
            mock.patch.object(
                brain,
                "_raw_bound_run",
                return_value={
                    "pass": False,
                    "status": "FAIL__CAPABILITY_OR_TASK_CONTRACT_GAP",
                    "failure_class": "MISSING_CAPABILITY_OR_COMPILED_TASK_CONTRACT",
                },
            ),
        ):
            out = brain.execute_failure_repair_cycle(
                {
                    "failure_fingerprint": fid,
                    "retry_capsule_sha256": retry_sha,
                    "components": [self.component()],
                    "initial_facts": [],
                },
                state_path=path,
            )

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "REPAIR_EFFECT_VERIFIED__ORIGINAL_FAILURE_PERSISTS",
        )
        state = learning.load_state(path)
        self.assertFalse(
            state["failures"][fid]["retry_capsules"][retry_sha]["resolved"]
        )


    def test_new_primitive_required_without_expander_remains_unresolved_for_generic_gap(self):
        path = self.temp_state()
        retry = {
            "mode": "generic",
            "problem": {
                "task_id": "generic-gap",
                "initial_facts": [],
                "target_effects": ["GENERIC_TARGET"],
                "capabilities": [],
            },
            "episode_id": "generic-gap",
            "scope_id": "scope",
            "learn": True,
        }
        seeded = learning.integrate_solver_output(
            FAILURE,
            state_path=path,
            retry_context=retry,
        )
        fid = seeded["diagnosis"]["failure_fingerprint"]
        retry_sha = seeded["retry_capsule_sha256"]
        missing = {
            "pass": False,
            "classification": "NEW_PRIMITIVE_REQUIRED",
            "missing_required_effects": ["repair.capability.available"],
            "next_action": "SYNTHESIZE_OR_ACQUIRE_ONLY_THE_LISTED_MISSING_CAUSAL_EFFECTS_THEN_RERUN",
        }
        with mock.patch.object(brain, "_causal_synthesize", return_value=missing):
            out = brain.execute_failure_repair_cycle(
                {
                    "failure_fingerprint": fid,
                    "retry_capsule_sha256": retry_sha,
                    "components": [],
                    "initial_facts": [],
                },
                state_path=path,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "REPAIR_CYCLE_UNRESOLVED_AT_SYNTHESIS")
        self.assertFalse(out["capability_expander_available"])
        self.assertFalse(out["owned_raw_acquisition_available"])


    def test_raw_gap_without_host_expander_uses_owned_acquisition_then_replays(self):
        path = self.temp_state()
        fid, retry_sha, _ = self.seed_failure(path)
        missing = {
            "pass": False,
            "classification": "NEW_PRIMITIVE_REQUIRED",
            "missing_required_effects": ["repair.capability.available"],
        }
        acquisition = {
            "pass": True,
            "status": "OWNED_RAW_CAPABILITY_ACQUISITION_EXECUTED",
            "mission_id": "LIVE-BRAIN-AUTO-ACQUIRE-ABC",
            "origin_mission_sha256": "a" * 64,
            "auto_acquisition": {
                "status": "VERIFIED_AND_PROMOTED",
                "capability_id": "auto.new",
            },
        }
        with (
            mock.patch.object(brain, "_causal_synthesize", return_value=missing),
            mock.patch.object(
                brain,
                "_owned_raw_capability_acquisition",
                return_value=acquisition,
            ) as acquire,
            mock.patch.object(
                brain,
                "_raw_bound_run",
                return_value={"pass": True, "status": "PASS__ORIGINAL_OBLIGATION"},
            ) as replay,
        ):
            out = brain.execute_failure_repair_cycle(
                {
                    "failure_fingerprint": fid,
                    "retry_capsule_sha256": retry_sha,
                    "components": [],
                    "initial_facts": [],
                },
                state_path=path,
            )

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "REPAIR_VERIFIED_BY_OWNED_ACQUISITION_AND_ORIGINAL_REPLAY",
        )
        self.assertEqual(out["repair_mode"], "OWNED_RAW_CAPABILITY_ACQUISITION")
        acquire.assert_called_once()
        replay.assert_called_once()
        state = learning.load_state(path)
        self.assertTrue(
            state["failures"][fid]["retry_capsules"][retry_sha]["resolved"]
        )

    def test_owned_acquisition_without_original_replay_success_stays_unresolved(self):
        path = self.temp_state()
        fid, retry_sha, _ = self.seed_failure(path)
        missing = {
            "pass": False,
            "classification": "NEW_PRIMITIVE_REQUIRED",
            "missing_required_effects": ["repair.capability.available"],
        }
        acquisition = {
            "pass": True,
            "status": "OWNED_RAW_CAPABILITY_ACQUISITION_EXECUTED",
            "mission_id": "LIVE-BRAIN-AUTO-ACQUIRE-ABC",
            "origin_mission_sha256": "a" * 64,
            "auto_acquisition": {"status": "VERIFIED_AND_PROMOTED"},
        }
        with (
            mock.patch.object(brain, "_causal_synthesize", return_value=missing),
            mock.patch.object(
                brain,
                "_owned_raw_capability_acquisition",
                return_value=acquisition,
            ),
            mock.patch.object(
                brain,
                "_raw_bound_run",
                return_value={
                    "pass": False,
                    "status": "FAIL__RAW_GOAL_COMPILATION_GAP",
                    "failure_class": "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP",
                },
            ),
        ):
            out = brain.execute_failure_repair_cycle(
                {
                    "failure_fingerprint": fid,
                    "retry_capsule_sha256": retry_sha,
                    "components": [],
                    "initial_facts": [],
                },
                state_path=path,
            )

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OWNED_ACQUISITION_COMPLETED__ORIGINAL_FAILURE_PERSISTS",
        )
        state = learning.load_state(path)
        self.assertFalse(
            state["failures"][fid]["retry_capsules"][retry_sha]["resolved"]
        )

    def test_new_primitive_required_uses_authenticated_v12_expansion_then_replays(self):
        path = self.temp_state()
        fid, retry_sha, _ = self.seed_failure(path)
        missing = {
            "pass": False,
            "classification": "NEW_PRIMITIVE_REQUIRED",
            "missing_required_effects": ["repair.capability.available"],
            "next_action": "SYNTHESIZE_OR_ACQUIRE_ONLY_THE_LISTED_MISSING_CAUSAL_EFFECTS_THEN_RERUN",
        }
        invented_expander = mock.Mock(name="brain_owned_expander")
        solver_out = {
            "pass": True,
            "status": "SOLVED__EPISODE_VERIFICATION_REQUIRED",
            "expanded_capability_ids": ["invented-repair-capability"],
            "capability_expansion_attempts": [{
                "status": "EXPANSION_ADMITTED",
                "admitted": [{"capability_id": "invented-repair-capability"}],
                "rejected": [],
            }],
        }
        with (
            mock.patch.object(brain, "_causal_synthesize", return_value=missing),
            mock.patch.object(brain, "_v12_run", return_value=solver_out) as execute,
            mock.patch.object(
                brain,
                "_raw_bound_run",
                return_value={"pass": True, "status": "PASS__ORIGINAL_OBLIGATION"},
            ),
        ):
            out = brain.execute_failure_repair_cycle(
                {
                    "failure_fingerprint": fid,
                    "retry_capsule_sha256": retry_sha,
                    "components": [],
                    "initial_facts": [],
                },
                state_path=path,
                capability_expander=invented_expander,
            )

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["repair_mode"],
            "V12_AUTHENTICATED_CAPABILITY_EXPANSION",
        )
        call = execute.call_args
        problem = call.args[0]
        kwargs = call.kwargs["kwargs"]
        self.assertEqual(problem["capabilities"], [])
        self.assertEqual(
            problem["target_effects"],
            ["repair.capability.available"],
        )
        self.assertIs(kwargs["capability_expander"], invented_expander)
        self.assertEqual(
            out["repair_receipt"]["original_replay_pass"],
            True,
        )
        state = learning.load_state(path)
        self.assertTrue(
            state["failures"][fid]["retry_capsules"][retry_sha]["resolved"]
        )


    def test_new_primitive_targets_original_generic_obligation_effects(self):
        path = self.temp_state()
        retry = {
            "mode": "generic",
            "problem": {
                "task_id": "generic-missing",
                "initial_facts": ["A"],
                "target_effects": ["REAL_TARGET_X", "REAL_TARGET_Y"],
                "capabilities": [],
            },
            "episode_id": "generic-missing",
            "scope_id": "scope",
            "learn": True,
        }
        seeded = learning.integrate_solver_output(
            FAILURE,
            state_path=path,
            retry_context=retry,
        )
        fid = seeded["diagnosis"]["failure_fingerprint"]
        retry_sha = seeded["retry_capsule_sha256"]
        missing = {
            "pass": False,
            "classification": "NEW_PRIMITIVE_REQUIRED",
            "missing_required_effects": ["repair.capability.available"],
        }
        invented_expander = mock.Mock(name="brain_owned_expander")
        solver_out = {
            "pass": True,
            "status": "SOLVED__EPISODE_VERIFICATION_REQUIRED",
            "expanded_capability_ids": ["invented-real-targets"],
            "capability_expansion_attempts": [{
                "status": "EXPANSION_ADMITTED",
                "admitted": [{"capability_id": "invented-real-targets"}],
                "rejected": [],
            }],
        }
        with (
            mock.patch.object(brain, "_causal_synthesize", return_value=missing),
            mock.patch.object(brain, "_v12_run", return_value=solver_out) as execute,
        ):
            out = brain.execute_failure_repair_cycle(
                {
                    "failure_fingerprint": fid,
                    "retry_capsule_sha256": retry_sha,
                    "components": [],
                    "initial_facts": ["A"],
                },
                state_path=path,
                capability_expander=invented_expander,
            )

        self.assertTrue(out["pass"], out)
        first_problem = execute.call_args_list[0].args[0]
        self.assertEqual(
            first_problem["target_effects"],
            ["REAL_TARGET_X", "REAL_TARGET_Y"],
        )
        self.assertEqual(
            out["invention_target_source"],
            "STORED_ORIGINAL_OBLIGATION_TARGET_EFFECTS",
        )
        self.assertEqual(
            out["invention_target_effects"],
            ["REAL_TARGET_X", "REAL_TARGET_Y"],
        )

    def test_missing_executable_binding_never_reaches_v12(self):
        path = self.temp_state()
        fid, retry_sha, _ = self.seed_failure(path)
        component = self.component()
        del component["executable_capability"]
        with (
            mock.patch.object(brain, "_causal_synthesize", return_value=self.architecture()),
            mock.patch.object(brain, "_v12_run") as execute,
        ):
            out = brain.execute_failure_repair_cycle(
                {
                    "failure_fingerprint": fid,
                    "retry_capsule_sha256": retry_sha,
                    "components": [component],
                    "initial_facts": [],
                },
                state_path=path,
            )
        self.assertFalse(out["pass"])
        self.assertIn("REPAIR_COMPONENT_EXECUTABLE_BINDING_REQUIRED", out["reason"])
        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
