from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.verifier_compiler_v1 import compile_verifier_plan
from canonical.runtime.proof_carrying_outcome_v1 import build_proof_carrying_outcome
from canonical.runtime import autonomous_verified_self_improvement_v1 as r3


class R3ProofCarryingOutcomeBridgeV1Tests(unittest.TestCase):
    def _proof_outcome(self):
        raw = compile_contract(
            "Create a report.",
            source_id="user",
            routing_target_effects=["decision.adequate_action"],
        )
        self.assertTrue(raw["pass"], raw)
        plan = compile_verifier_plan(raw)
        binding = {
            "pass": True,
            "status": "PASS__ACTUAL_GOAL_SATISFACTION_AUTHENTICATED",
            "goal_sha256": "goal-sha",
            "policy_id": "policy.test",
            "realization_sha256": "sha256:realization",
            "receipt_path": "canonical/verification/acceptance.json",
            "receipt_git_blob_sha": "a" * 40,
            "verification_path": "canonical/verification/acceptance.verify.json",
            "verification_git_blob_sha": "b" * 40,
            "independent_verifier_id": "independent-test-verifier",
        }
        pco = build_proof_carrying_outcome(
            raw_contract=raw,
            verifier_plan=plan,
            selected_policy_id="policy.test",
            realization={"kind": "test"},
            goal_satisfaction_binding=binding,
        )
        self.assertTrue(pco["pass"], pco)
        return raw, pco

    def test_r3_retains_proof_carrying_success_as_bounded_proof_capsule(self):
        raw, pco = self._proof_outcome()
        observed = {
            "schema": "TEST_R2_SUCCESS",
            "status": "PASS",
            "pass": True,
            "task_id": "task-1",
            "proof_carrying_outcome": pco,
        }
        capsule = r3._make_success_proof_capsule(observed)
        self.assertIsInstance(capsule, dict)
        self.assertEqual(
            capsule["material"]["proof_kind"],
            "PROOF_CARRYING_OUTCOME_V1",
        )
        self.assertTrue(capsule["material"]["semantic_acceptance_complete"])
        self.assertEqual(
            len(capsule["material"]["obligation_evidence"]),
            len(raw["acceptance_contract"]["obligations"]),
        )

    def test_success_observation_queues_verified_episode_adaptation_with_proof(self):
        _, pco = self._proof_outcome()
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            out = r3.record_success_observation(
                {
                    "schema": "TEST_R2_SUCCESS",
                    "status": "PASS",
                    "pass": True,
                    "task_id": "task-1",
                    "proof_carrying_outcome": pco,
                },
                surface="DECISION:R2_GENERAL_ADEQUATE_DECISION",
                state_path=state_path,
                replay_context={"mode": "decision", "request": {"task_id": "task-1"}},
            )
            self.assertTrue(out["pass"])
            self.assertTrue(out["proof_available"])
            state = r3.load_state(state_path)
            self.assertEqual(state["stats"]["success_observation_count"], 1)
            self.assertEqual(state["stats"]["pending_improvement_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
