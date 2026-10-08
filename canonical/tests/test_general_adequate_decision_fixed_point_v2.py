from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from canonical.runtime import general_adequate_decision_fixed_point_v2 as fixed


class GeneralAdequateDecisionFixedPointV2Tests(unittest.TestCase):
    @staticmethod
    def _request():
        return {"task_id": "R2-FP-1", "goal": "Do the right action."}

    @staticmethod
    def _open(status="OPEN__DECISION_CONTEXT_REQUIRED"):
        return {
            "schema": "PROJECT_BRAIN_GENERAL_ADEQUATE_DECISION_CONTROLLER_V1",
            "status": status,
            "pass": False,
            "goal_sha256": "g",
            "next_required_edge": "AUTHENTICATED_GOAL_TO_DECISION_CONTEXT",
            "semantic_acceptance_complete": False,
            "actual_goal_satisfaction_verified": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "incremental_spend_usd": 0,
        }

    @staticmethod
    def _pass():
        return {
            "schema": "PROJECT_BRAIN_GENERAL_ADEQUATE_DECISION_CONTROLLER_V1",
            "status": "PASS__GOAL_BOUND_ADEQUATE_DECISION_REALIZED_AND_ACCEPTANCE_VERIFIED",
            "pass": True,
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
            "incremental_spend_usd": 0,
        }


    @patch.object(fixed.direct_adequacy, "preflight")
    @patch.object(fixed.direct_adequacy, "run")
    @patch.object(fixed, "run_controller")
    def test_exact_direct_adequacy_closes_before_semantic_loop(
        self, controller, direct_run, preflight
    ):
        preflight.return_value = {
            "matched": True,
            "route_id": "DIRECT_ADEQUACY::TEST",
        }
        direct_run.return_value = {
            "pass": True,
            "status": "PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "execution_attempted": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
        out = fixed.run(self._request())
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["r2_fixed_point_status"],
            "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED",
        )
        self.assertEqual(out["r2_fixed_point_steps"], 0)
        controller.assert_not_called()
        direct_run.assert_called_once()

    @patch.object(fixed.direct_adequacy, "preflight")
    @patch.object(fixed.direct_adequacy, "run")
    @patch.object(fixed, "run_controller")
    def test_matched_direct_route_failure_never_retries_semantic_path(
        self, controller, direct_run, preflight
    ):
        preflight.return_value = {
            "matched": True,
            "route_id": "DIRECT_ADEQUACY::TEST",
        }
        direct_run.return_value = {
            "pass": False,
            "status": "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY",
            "semantic_acceptance_complete": False,
            "actual_goal_satisfaction_verified": False,
            "execution_attempted": True,
            "retry_by_other_route_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
        out = fixed.run(self._request())
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["r2_fixed_point_status"],
            "OPEN__R2_MATCHED_DIRECT_ROUTE_DID_NOT_VERIFY",
        )
        controller.assert_not_called()
        direct_run.assert_called_once()

    @patch.object(fixed.direct_adequacy, "preflight")
    @patch.object(fixed, "run_controller")
    def test_unmatched_direct_route_preserves_v1_fixed_point_path(
        self, controller, preflight
    ):
        preflight.return_value = {
            "pass": False,
            "status": "NO_DIRECT_ADEQUACY_ROUTE",
            "matched": False,
        }
        controller.return_value = self._open()
        out = fixed.run(self._request())
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__DECISION_CONTEXT_REQUIRED")
        controller.assert_called_once()

    @patch.object(fixed, "run_controller")
    def test_without_resolver_preserves_exact_v1_open_state(self, controller):
        controller.return_value = self._open()
        out = fixed.run(self._request())
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__DECISION_CONTEXT_REQUIRED")
        self.assertEqual(
            out["r2_fixed_point_status"], "OPEN__R2_EDGE_RESOLVER_UNAVAILABLE"
        )
        self.assertEqual(out["r2_fixed_point_steps"], 0)
        self.assertFalse(out["r2_edge_resolver_authority"])

    @patch.object(fixed, "run_controller")
    def test_progressive_candidate_is_reverified_before_success(self, controller):
        controller.side_effect = [self._open(), self._pass()]
        provider = Mock(
            return_value={
                "proposal": {
                    "request_patch": {
                        "decision_payload": {"context_id": "ctx"},
                        "partial_goal_to_decision_binding": {
                            "receipt": {"path": "r"},
                            "verification": {"path": "v"},
                        },
                    }
                },
                "source_id": "host-general-cognition",
            }
        )
        out = fixed.run(self._request(), proposal_provider=provider)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["r2_fixed_point_status"], "PASS__R2_ADAPTIVE_FIXED_POINT_CLOSED"
        )
        self.assertEqual(out["r2_fixed_point_steps"], 1)
        self.assertEqual(controller.call_count, 2)
        second_request = controller.call_args_list[1].args[0]
        self.assertEqual(second_request["task_id"], "R2-FP-1")
        self.assertEqual(second_request["goal"], "Do the right action.")
        self.assertEqual(second_request["decision_payload"]["context_id"], "ctx")
        packet = provider.call_args.args[0]
        self.assertFalse(packet["provider_is_semantic_truth_authority"])
        self.assertFalse(packet["provider_is_terminal_authority"])

    @patch.object(fixed, "run_controller")
    def test_provider_pass_claim_cannot_bypass_controller(self, controller):
        controller.return_value = self._open()
        provider = Mock(return_value={"pass": True, "status": "I_SAY_DONE"})
        out = fixed.run(self._request(), proposal_provider=provider)
        self.assertFalse(out["pass"])
        self.assertEqual(controller.call_count, 1)
        self.assertEqual(
            out["r2_fixed_point_status"],
            "OPEN__R2_EDGE_RESOLVER_NO_PROGRESSIVE_CANDIDATE",
        )

    @patch.object(fixed, "run_controller")
    def test_goal_mutation_candidate_is_rejected(self, controller):
        controller.return_value = self._open()
        provider = Mock(
            return_value={"request_patch": {"goal": "silently changed goal"}}
        )
        out = fixed.run(self._request(), proposal_provider=provider)
        self.assertFalse(out["pass"])
        self.assertEqual(controller.call_count, 1)
        attempts = out["r2_fixed_point_trace"][0]["resolver_attempts"]
        self.assertTrue(
            any(
                "UNMODELED_REQUEST_PATCH_FIELDS:goal" == row.get("reason")
                for row in attempts
            )
        )

    @patch.object(fixed, "run_controller")
    def test_later_candidate_can_supply_progress_when_first_is_invalid(self, controller):
        controller.side_effect = [self._open(), self._pass()]

        def provider(packet, index, prior):
            if index == 0:
                return {"request_patch": {"goal": "forbidden"}}
            return {"request_patch": {"decision_payload": {"context_id": "ctx"}}}

        out = fixed.run(
            self._request(),
            proposal_provider=provider,
            provider_max_candidates=2,
        )
        self.assertTrue(out["pass"], out)
        attempts = out["r2_fixed_point_trace"][0]["resolver_attempts"]
        self.assertEqual(attempts[0]["status"], "CANDIDATE_REJECTED")
        self.assertEqual(
            attempts[1]["status"],
            "PROGRESSIVE_REQUEST_PATCH_ACCEPTED_FOR_REVERIFICATION",
        )

    @patch.object(fixed, "run_controller")
    def test_repeated_candidate_cannot_spin(self, controller):
        controller.return_value = self._open()
        provider = Mock(
            return_value={"request_patch": {"decision_payload": {"context_id": "ctx"}}}
        )
        out = fixed.run(
            self._request(),
            proposal_provider=provider,
            provider_max_candidates=1,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(controller.call_count, 2)
        self.assertEqual(
            out["r2_fixed_point_status"],
            "OPEN__R2_EDGE_RESOLVER_NO_PROGRESSIVE_CANDIDATE",
        )
        attempts = out["r2_fixed_point_trace"][-1]["resolver_attempts"]
        self.assertEqual(attempts[0]["reason"], "NO_PROGRESS")

    @patch.object(fixed, "run_controller")
    def test_step_bound_is_fail_closed_without_false_success(self, controller):
        controller.return_value = self._open()

        def provider(packet, index, prior):
            return {
                "request_patch": {
                    "decision_payload": {"context_id": "ctx-" + str(packet["step"])}
                }
            }

        out = fixed.run(
            self._request(),
            proposal_provider=provider,
            max_fixed_point_steps=1,
            provider_max_candidates=1,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(controller.call_count, 2)
        self.assertEqual(
            out["r2_fixed_point_status"],
            "OPEN__R2_FIXED_POINT_STEP_BOUND_EXHAUSTED",
        )
        self.assertFalse(out["actual_goal_satisfaction_verified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
