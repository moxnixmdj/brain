from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from canonical.runtime import general_adequate_decision_controller_v1 as controller


class GeneralAdequateDecisionControllerV1Tests(unittest.TestCase):
    def _base_request(self):
        return {
            "task_id": "R2_TEST_001",
            "goal": "Choose and realize the adequate action for this bounded decision.",
            "decision_payload": {
                "context_id": "ctx",
                "v3_input": {"task": {}},
                "bound_relevance_cegar_loop": {
                    "cegar_problem": {},
                    "truth_payloads_by_discriminator_id": {},
                    "truth_payloads_by_predicate_id": {},
                    "source_positive_selection_contracts": {},
                },
            },
            "goal_to_decision_binding": {"receipt": {}, "verification": {}},
        }

    @staticmethod
    def _raw_contract():
        return {
            "pass": True,
            "task_contract_sha256": "contract-sha",
            "task_sha256": "goal-sha",
            "nonwhitespace_source_coverage_complete": True,
            "acceptance_contract": {"obligations": [{"id": "o1"}]},
        }

    @staticmethod
    def _goal_binding_pass():
        return {
            "pass": True,
            "status": "PASS__GOAL_TO_DECISION_CONTEXT_AUTHENTICATED",
            "goal_sha256": "g",
            "decision_payload_sha256": "d",
        }

    @staticmethod
    def _goal_satisfaction_pass():
        return {
            "pass": True,
            "status": "PASS__ACTUAL_GOAL_SATISFACTION_AUTHENTICATED",
            "policy_id": "policy.p",
            "realization_sha256": "r",
        }

    @staticmethod
    def _decision_pass():
        return {
            "pass": True,
            "status": "PASS__P3_REAL_CONTEXT_BOUND_RELEVANCE_CEGAR_LOOP",
            "selected_policy_id": "policy.p",
            "selected_claim_ids": ["A"],
            "rendered_text": "Do the certified action.",
            "p3_contract_cell_authorized": True,
        }

    @staticmethod
    def _information_open(predicate_id="source-condition-sha256:a"):
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "BOUND_RELEVANCE_CEGAR_LOOP_UNSATISFIED",
            "detail": {
                "loop_result": {
                    "pass": False,
                    "status": "OPEN__SELECTED_PREDICATE_PROOF_PAYLOAD_REQUIRED",
                    "reason": "SELECTED_FORMULA_ATOM_HAS_NO_TRUTH_CERTIFICATE_PAYLOAD",
                    "detail": {"predicate_id": predicate_id},
                }
            },
        }

    def test_missing_decision_context_stays_open(self):
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()):
            out = controller.run(
                {"task_id": "R2_TEST_MISSING_CONTEXT", "goal": "Choose the adequate action."}
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__DECISION_CONTEXT_REQUIRED")
        self.assertFalse(out["semantic_acceptance_complete"])
        self.assertFalse(out["actual_goal_satisfaction_verified"])

    def test_goal_binding_is_required_before_policy_reasoning(self):
        request = self._base_request()
        request.pop("goal_to_decision_binding")
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "evaluate_p3") as p3:
            out = controller.run(request)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__GOAL_TO_DECISION_BINDING_REQUIRED")
        p3.assert_not_called()

    def test_adequate_grounded_expression_is_not_goal_success_without_acceptance(self):
        request = self._base_request()
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=self._decision_pass()):
            out = controller.run(request)
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "OPEN__GOAL_SATISFACTION_BINDING_REQUIRED")
        self.assertEqual(
            out["next_required_edge"],
            "INDEPENDENT_ACTUAL_GOAL_SATISFACTION_VERIFICATION",
        )
        self.assertFalse(out["actual_goal_satisfaction_verified"])

    def test_grounded_expression_closes_only_with_independent_goal_acceptance(self):
        request = self._base_request()
        request["goal_satisfaction_binding"] = {"receipt": {}, "verification": {}}
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=self._decision_pass()), \
             patch.object(
                 controller,
                 "_authenticate_goal_satisfaction_binding",
                 return_value=self._goal_satisfaction_pass(),
             ):
            out = controller.run(request)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__GOAL_BOUND_ADEQUATE_DECISION_REALIZED_AND_ACCEPTANCE_VERIFIED",
        )
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertFalse(out["terminal_authority"])

    def test_only_selected_policy_changing_predicate_is_requested(self):
        request = self._base_request()
        predicate_id = "source-condition-sha256:critical"
        provider = Mock(return_value={"source_text": "truth payload"})
        observed_payloads = []

        def p3_side_effect(payload, *, repo_root=None):
            observed_payloads.append(payload)
            if len(observed_payloads) == 1:
                return self._information_open(predicate_id)
            return self._decision_pass()

        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", side_effect=p3_side_effect), \
             patch.object(
                 controller,
                 "_authenticate_goal_satisfaction_binding",
                 return_value=self._goal_satisfaction_pass(),
             ):
            out = controller.run(request, information_provider=provider)

        self.assertTrue(out["pass"], out)
        provider.assert_called_once()
        info_request = provider.call_args.args[0]
        self.assertEqual(info_request["predicate_id"], predicate_id)
        self.assertFalse(info_request["information_authority"])
        self.assertFalse(info_request["semantic_truth_authority"])
        inserted = observed_payloads[1]["bound_relevance_cegar_loop"][
            "truth_payloads_by_predicate_id"
        ]
        self.assertEqual(inserted[predicate_id], {"source_text": "truth payload"})
        self.assertEqual(out["minimum_information_rounds_used"], 1)

    def test_without_provider_returns_exact_minimum_information_request(self):
        request = self._base_request()
        predicate_id = "source-condition-sha256:critical"
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=self._information_open(predicate_id)):
            out = controller.run(request)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__MINIMUM_POLICY_CHANGING_INFORMATION_REQUIRED")
        self.assertEqual(out["next_information_request"]["predicate_id"], predicate_id)
        self.assertFalse(out["actual_goal_satisfaction_verified"])

    def test_provider_cannot_self_authorize_semantic_truth(self):
        request = self._base_request()
        request["max_information_rounds"] = 1
        provider = Mock(
            return_value={
                "pass": True,
                "predicate_truth": "TRUE",
                "semantic_truth_authority": True,
            }
        )
        still_open = self._information_open("source-condition-sha256:a")
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", side_effect=[still_open, still_open]):
            out = controller.run(request, information_provider=provider)
        self.assertFalse(out["pass"])
        self.assertIn(
            out["status"],
            {
                "OPEN__MINIMUM_INFORMATION_ROUND_BOUND_EXHAUSTED",
                "OPEN__ADEQUATE_DECISION_NOT_CERTIFIED",
            },
        )
        self.assertFalse(out["actual_goal_satisfaction_verified"])

    def test_selected_policy_execution_requires_independent_binding(self):
        request = self._base_request()
        request["execution_problem"] = {
            "task_id": "exec",
            "initial_facts": [],
            "target_effects": ["DONE"],
            "capabilities": [],
        }
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=self._decision_pass()), \
             patch.object(controller, "run_universal") as solver:
            out = controller.run(request)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__POLICY_EXECUTION_BINDING_REQUIRED")
        solver.assert_not_called()

    def test_execution_success_is_not_goal_success_without_acceptance(self):
        request = self._base_request()
        request["execution_problem"] = {"task_id": "exec", "target_effects": ["DONE"]}
        request["policy_execution_binding"] = {"receipt": {}, "verification": {}}
        execution_pass = {"pass": True, "status": "SOLVED__VERIFIED_EPISODE"}
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=self._decision_pass()), \
             patch.object(controller, "_authenticate_policy_execution_binding", return_value={"pass": True}), \
             patch.object(controller, "run_universal", return_value=execution_pass):
            out = controller.run(request)
        self.assertFalse(out["pass"], out)
        self.assertEqual(out["status"], "OPEN__GOAL_SATISFACTION_BINDING_REQUIRED")
        self.assertFalse(out["actual_goal_satisfaction_verified"])

    def test_bound_execution_closes_only_with_independent_goal_acceptance(self):
        request = self._base_request()
        request["execution_problem"] = {"task_id": "exec", "target_effects": ["DONE"]}
        request["policy_execution_binding"] = {"receipt": {}, "verification": {}}
        request["goal_satisfaction_binding"] = {"receipt": {}, "verification": {}}
        execution_pass = {"pass": True, "status": "SOLVED__VERIFIED_EPISODE"}
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=self._decision_pass()), \
             patch.object(controller, "_authenticate_policy_execution_binding", return_value={"pass": True}), \
             patch.object(controller, "run_universal", return_value=execution_pass), \
             patch.object(
                 controller,
                 "_authenticate_goal_satisfaction_binding",
                 return_value=self._goal_satisfaction_pass(),
             ):
            out = controller.run(request)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__GOAL_BOUND_ADEQUATE_POLICY_EXECUTED_AND_ACCEPTANCE_VERIFIED",
        )
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertFalse(out["terminal_authority"])

    def test_goal_satisfaction_receipt_is_exact_content_bound_and_tamper_evident(self):
        goal = "do the exact task"
        policy = "policy.p"
        realization = {"kind": "TEST", "value": 7}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / "canonical/governance"
            ver = root / "canonical/verification"
            gov.mkdir(parents=True)
            ver.mkdir(parents=True)
            receipt_path = gov / "goal.json"
            verify_path = ver / "goal_verify.json"
            goal_sha = controller.sha256(goal.encode("utf-8")).hexdigest()
            realization_sha = controller._digest(realization)
            receipt = {
                "schema": controller.GOAL_SATISFACTION_SCHEMA,
                "goal_sha256": goal_sha,
                "policy_id": policy,
                "realization_sha256": realization_sha,
                "goal_satisfaction_proved": True,
                "all_load_bearing_constraints_satisfied": True,
                "acceptance_relation_bound": True,
            }
            receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
            receipt_blob = controller._git_blob_sha(receipt_path)
            verification = {
                "schema": controller.GOAL_SATISFACTION_VERIFY_SCHEMA,
                "subject_git_blob_sha": receipt_blob,
                "goal_sha256": goal_sha,
                "policy_id": policy,
                "realization_sha256": realization_sha,
                "pass": True,
                "independent_verified": True,
                "goal_satisfaction_verified": True,
                "acceptance_relation_verified": True,
                "load_bearing_constraints_verified": True,
                "independent_verifier_id": "independent-test-verifier",
            }
            verify_path.write_text(json.dumps(verification, sort_keys=True), encoding="utf-8")
            binding = {
                "receipt": {
                    "path": "canonical/governance/goal.json",
                    "git_blob_sha": receipt_blob,
                },
                "verification": {
                    "path": "canonical/verification/goal_verify.json",
                    "git_blob_sha": controller._git_blob_sha(verify_path),
                },
            }
            passed = controller._authenticate_goal_satisfaction_binding(
                binding,
                goal=goal,
                selected_policy_id=policy,
                realization=realization,
                repo_root=root,
            )
            self.assertTrue(passed["pass"], passed)

            receipt["goal_satisfaction_proved"] = False
            receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
            tampered = controller._authenticate_goal_satisfaction_binding(
                binding,
                goal=goal,
                selected_policy_id=policy,
                realization=realization,
                repo_root=root,
            )
            self.assertFalse(tampered["pass"])
            self.assertEqual(
                tampered["status"],
                "FAIL_CLOSED__GOAL_SATISFACTION_BINDING_INVALID",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
