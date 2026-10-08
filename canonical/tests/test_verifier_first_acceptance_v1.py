from __future__ import annotations

from copy import deepcopy
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.verifier_compiler_v1 import (
    compile_verifier_plan,
    validate_structural_candidate,
)
from canonical.runtime.proof_carrying_outcome_v1 import (
    build_proof_carrying_outcome,
    verify_proof_carrying_outcome_integrity,
)
from canonical.runtime import autonomous_verified_self_improvement_v1 as r3


class VerifierFirstAcceptanceV1Tests(unittest.TestCase):
    def _contract(self, goal: str):
        out = compile_contract(
            goal,
            source_id="user",
            routing_target_effects=["decision.adequate_action"],
        )
        self.assertTrue(out["pass"], out)
        return out

    @staticmethod
    def _goal_binding(policy_id: str = "policy.test"):
        return {
            "pass": True,
            "status": "PASS__ACTUAL_GOAL_SATISFACTION_AUTHENTICATED",
            "goal_sha256": "goal-sha",
            "policy_id": policy_id,
            "realization_sha256": "sha256:realization",
            "receipt_path": "canonical/verification/acceptance.json",
            "receipt_git_blob_sha": "a" * 40,
            "verification_path": "canonical/verification/acceptance.verify.json",
            "verification_git_blob_sha": "b" * 40,
            "independent_verifier_id": "independent-test-verifier",
        }

    def _pco(self, goal: str = "Create a report."):
        raw = self._contract(goal)
        plan = compile_verifier_plan(raw)
        pco = build_proof_carrying_outcome(
            raw_contract=raw,
            verifier_plan=plan,
            selected_policy_id="policy.test",
            realization={"kind": "test"},
            goal_satisfaction_binding=self._goal_binding(),
        )
        self.assertTrue(pco["pass"], pco)
        return raw, plan, pco

    def test_verifier_plan_preserves_every_raw_obligation(self):
        raw = self._contract(
            "Create a report. It must include revenue. Keep it under 500 words."
        )
        plan = compile_verifier_plan(raw)
        expected = raw["acceptance_contract"]["required_obligation_ids"]
        actual = [row["obligation_id"] for row in plan["obligation_verifiers"]]
        self.assertEqual(actual, expected)
        self.assertEqual(plan["raw_obligation_count"], len(expected))
        self.assertTrue(plan["all_raw_obligations_have_explicit_verifier_route"])
        self.assertFalse(plan["automatic_success_authority"])
        self.assertEqual(
            {row["primary_verifier"]["class"] for row in plan["obligation_verifiers"]},
            {"INDEPENDENT_GOAL_SATISFACTION_BINDING"},
        )

    def test_structural_checker_is_supplemental_not_semantic_authority(self):
        raw = self._contract('Respond exactly "amber".')
        plan = compile_verifier_plan(raw)
        good = validate_structural_candidate(plan, "amber")
        bad = validate_structural_candidate(plan, "wrong")
        self.assertTrue(good["pass"])
        self.assertFalse(good["semantic_success_authority"])
        self.assertFalse(bad["pass"])
        self.assertIn("EXACT_RESPONSE", bad["validation_errors"])

    def test_proof_carrying_outcome_is_r3_compatible_raw_goal_acceptance(self):
        raw, plan, pco = self._pco("Create a report. Include revenue.")
        expected = raw["acceptance_contract"]["required_obligation_ids"]
        self.assertEqual(pco["accepted_raw_obligation_ids"], expected)
        self.assertEqual(pco["raw_acceptance_obligation_count"], len(expected))
        self.assertEqual(pco["raw_goal_sha256"], raw["task_sha256"])
        self.assertEqual(pco["raw_task_contract_sha256"], raw["task_contract_sha256"])
        self.assertTrue(pco["all_raw_obligations_bound_to_authenticated_acceptance"])
        self.assertTrue(pco["semantic_acceptance_complete"])
        self.assertFalse(pco["acceptance_authority"])
        self.assertFalse(pco["self_certifying"])
        self.assertEqual(
            pco["proof_authority_derived_from"],
            "AUTHENTICATED_R2_GOAL_SATISFACTION_BINDING",
        )
        self.assertTrue(verify_proof_carrying_outcome_integrity(pco)["pass"])

    def test_proof_carrying_outcome_integrity_rejects_tampering(self):
        _, _, pco = self._pco("Create a report. Include revenue.")
        tampered = deepcopy(pco)
        tampered["obligation_evidence"][0]["accepted"] = False
        checked = verify_proof_carrying_outcome_integrity(tampered)
        self.assertFalse(checked["pass"])
        self.assertIn("OBLIGATION_EVIDENCE_NOT_ACCEPTED", checked["reason"])

    def test_proof_carrying_outcome_fails_without_independent_verifier(self):
        raw = self._contract("Create a report.")
        plan = compile_verifier_plan(raw)
        binding = self._goal_binding()
        binding["independent_verifier_id"] = ""
        out = build_proof_carrying_outcome(
            raw_contract=raw,
            verifier_plan=plan,
            selected_policy_id="policy.test",
            realization={"kind": "test"},
            goal_satisfaction_binding=binding,
        )
        self.assertFalse(out["pass"])
        self.assertIn("INDEPENDENT_VERIFIER_ID_REQUIRED", out["reason"])

    def test_r3_retains_integrity_checked_r2_acceptance_proof(self):
        _, _, pco = self._pco()
        observed = {
            "schema": "TEST_R2_SUCCESS",
            "status": "PASS",
            "pass": True,
            "task_id": "task-1",
            "semantic_acceptance_complete": True,
            "raw_goal_sha256": pco["raw_goal_sha256"],
            "raw_task_contract_sha256": pco["raw_task_contract_sha256"],
            "raw_acceptance_obligation_count": pco[
                "raw_acceptance_obligation_count"
            ],
            "accepted_raw_obligation_ids": pco["accepted_raw_obligation_ids"],
            "raw_goal_acceptance": pco,
        }
        capsule = r3._make_success_proof_capsule(observed)
        self.assertIsInstance(capsule, dict)
        self.assertEqual(
            capsule["material"]["proof_kind"],
            "R2_PROOF_CARRYING_RAW_GOAL_ACCEPTANCE_V1",
        )
        self.assertTrue(capsule["material"]["semantic_acceptance_complete"])

        tampered = deepcopy(observed)
        tampered["raw_goal_acceptance"]["obligation_evidence"][0]["accepted"] = False
        self.assertIsNone(r3._make_success_proof_capsule(tampered))

    def test_r3_success_observation_queues_verified_episode_adapter_with_proof(self):
        _, _, pco = self._pco()
        observed = {
            "schema": "TEST_R2_SUCCESS",
            "status": "PASS",
            "pass": True,
            "task_id": "task-1",
            "semantic_acceptance_complete": True,
            "raw_goal_sha256": pco["raw_goal_sha256"],
            "raw_task_contract_sha256": pco["raw_task_contract_sha256"],
            "raw_acceptance_obligation_count": pco[
                "raw_acceptance_obligation_count"
            ],
            "accepted_raw_obligation_ids": pco["accepted_raw_obligation_ids"],
            "raw_goal_acceptance": pco,
        }
        with tempfile.TemporaryDirectory() as td:
            state_path = Path(td) / "state.json"
            out = r3.record_success_observation(
                observed,
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
