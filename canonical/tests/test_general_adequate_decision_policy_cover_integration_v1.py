from unittest import TestCase
from unittest.mock import Mock, patch

from canonical.runtime import general_adequate_decision_controller_v1 as controller


class GeneralAdequateDecisionPolicyCoverIntegrationV1Tests(TestCase):
    def _request(self):
        return {
            "task_id": "R2_POLICY_COVER_INTEGRATION",
            "goal": "Choose and execute an adequate action.",
            "decision_payload": {
                "context_id": "ctx",
                "v3_input": {"task": {}},
                "observable_policy_cover": {
                    "problem": {"state_id": "state-1"},
                    "cover_binding": {"receipt": {}, "verification": {}},
                },
            },
            "goal_to_decision_binding": {"receipt": {}, "verification": {}},
            "execution_problem": {"task_id": "exec", "target_effects": ["DONE"]},
            "policy_execution_binding": {"receipt": {}, "verification": {}},
            "goal_satisfaction_binding": {"receipt": {}, "verification": {}},
        }

    def _raw_contract(self):
        return {
            "pass": True,
            "task_contract_sha256": "raw-contract",
            "nonwhitespace_source_coverage_complete": True,
        }

    def _p3_open_without_information_gap(self):
        return {
            "pass": False,
            "status": "OPEN",
            "detail": {
                "loop_result": {
                    "status": "OPEN__POLICY_ADEQUACY_UNRESOLVED",
                    "reason": "no single policy certified",
                }
            },
        }

    def _cover_pass(self):
        return {
            "pass": True,
            "status": "PASS__AUTHENTICATED_OBSERVABLE_POLICY_SELECTED",
            "selected_policy_id": "policy.covered",
            "policy_selection_authorized": True,
            "selected_policy_adequacy_verified": True,
            "bound_state_totality_proved": True,
        }

    def test_authenticated_cover_fallback_reaches_existing_execution_and_acceptance_path(self):
        request = self._request()
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value={"pass": True}), \
             patch.object(controller, "evaluate_p3", return_value=self._p3_open_without_information_gap()), \
             patch.object(controller, "evaluate_policy_cover", return_value=self._cover_pass()) as cover, \
             patch.object(controller, "_authenticate_policy_execution_binding", return_value={"pass": True}), \
             patch.object(controller, "run_universal", return_value={"pass": True, "verified_target_effects": True}) as execute, \
             patch.object(controller, "_authenticate_goal_satisfaction_binding", return_value={"pass": True, "independent_verifier_id": "test"}):
            out = controller.run(request)

        self.assertTrue(out["pass"], out)
        self.assertEqual(out["selected_policy_id"], "policy.covered")
        self.assertEqual(out["decision_result"]["route"], "OBSERVABLE_POLICY_COVER_EXECUTOR_V1")
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertFalse(out["terminal_authority"])
        cover.assert_called_once()
        execute.assert_called_once()

    def test_cover_open_surfaces_exact_next_policy_changing_observation(self):
        request = self._request()
        next_request = {
            "schema": "PROJECT_BRAIN_POLICY_COVER_OBSERVATION_REQUEST_V1",
            "state_id": "state-1",
            "discriminator_id": "disc-1",
            "surviving_world_ids": ["w1", "w2"],
            "observation_authority": False,
        }
        cover_open = {
            "pass": False,
            "status": "OPEN__POLICY_COVER_OBSERVATION_BINDING_REQUIRED",
            "reason": "SELECTED_POLICY_CHANGING_OBSERVATION_NOT_AUTHENTICATED",
            "next_observation_request": next_request,
        }
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value={"pass": True}), \
             patch.object(controller, "evaluate_p3", return_value=self._p3_open_without_information_gap()), \
             patch.object(controller, "evaluate_policy_cover", return_value=cover_open), \
             patch.object(controller, "run_universal") as execute:
            out = controller.run(request)

        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__POLICY_COVER_OBSERVATION_BINDING_REQUIRED")
        self.assertEqual(
            out["next_required_edge"],
            "AUTHENTICATED_SELECTED_POLICY_CHANGING_OBSERVATION",
        )
        self.assertEqual(out["next_observation_request"], next_request)
        execute.assert_not_called()

    def test_cover_pass_without_adequacy_authority_fails_closed(self):
        request = self._request()
        bad_cover = dict(self._cover_pass())
        bad_cover["selected_policy_adequacy_verified"] = False
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value={"pass": True}), \
             patch.object(controller, "evaluate_p3", return_value=self._p3_open_without_information_gap()), \
             patch.object(controller, "evaluate_policy_cover", return_value=bad_cover):
            out = controller.run(request)

        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("POLICY_COVER_PASS_WITHOUT_AUTHORIZED_ADEQUATE_SELECTION", out["reason"])
