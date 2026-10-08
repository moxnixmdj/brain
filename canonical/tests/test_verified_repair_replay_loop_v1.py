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
