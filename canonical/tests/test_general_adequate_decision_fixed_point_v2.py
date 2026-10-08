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
        preflight.return_value = {"matched": True, "route_id": "DIRECT_ADEQUACY::TEST"}
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
        self.assertEqual(out["r2_fixed_point_status"], "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED")
        self.assertEqual(out["r2_fixed_point_steps"], 0)
        controller.assert_not_called()
        direct_run.assert_called_once()

    @patch.object(fixed.direct_adequacy, "preflight")
    @patch.object(fixed.direct_adequacy, "run")
    @patch.object(fixed, "run_controller")
    def test_matched_direct_route_failure_never_retries_semantic_path(
        self, controller, direct_run, preflight
    ):
        preflight.return_value = {"matched": True, "route_id": "DIRECT_ADEQUACY::TEST"}
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
        self.assertEqual(out["r2_fixed_point_status"], "OPEN__R2_MATCHED_DIRECT_ROUTE_DID_NOT_VERIFY")
        controller.assert_not_called()
        direct_run.assert_called_once()

    @patch.object(fixed.direct_adequacy, "preflight")
    @patch.object(fixed, "run_controller")
    def test_unmatched_direct_route_preserves_v1_fixed_point_path(
        self, controller, preflight
    ):
        preflight.return_value = {"pass": False, "status": "NO_DIRECT_ADEQUACY_ROUTE", "matched": False}
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
    def test_policy_cover_observation_request_can_be_repaired_and_reverified(self, controller):
        open_cover = {
            **self._open("OPEN__POLICY_COVER_OBSERVATION_BINDING_REQUIRED"),
            "next_required_edge": "AUTHENTICATED_SELECTED_POLICY_CHANGING_OBSERVATION",
            "next_observation_request": {
                "schema": "PROJECT_BRAIN_POLICY_COVER_OBSERVATION_REQUEST_V1",
                "state_id": "state-1",
                "discriminator_id": "disc-1",
                "surviving_world_ids": ["w1", "w2"],
                "observation_authority": False,
            },
        }
        controller.side_effect = [open_cover, self._pass()]

        provider = Mock(
            return_value={
                "request_patch": {
                    "policy_cover_observation_bindings": {
                        "disc-1": {
                            "receipt": {
                                "path": "canonical/governance/obs.json",
                                "git_blob_sha": "abc",
                            },
                            "verification": {
                                "path": "canonical/verification/obs.json",
                                "git_blob_sha": "def",
                            },
                        }
                    },
                    "max_policy_cover_observations": 8,
                }
            }
        )

        out = fixed.run(self._request(), proposal_provider=provider)

        self.assertTrue(out["pass"], out)
        self.assertEqual(controller.call_count, 2)
        packet = provider.call_args.args[0]
        self.assertEqual(
            packet["next_observation_request"]["discriminator_id"],
            "disc-1",
        )
        self.assertIn(
            "policy_cover_observation_bindings",
            packet["allowed_request_patch_fields"],
        )
        second = controller.call_args_list[1].args[0]
        self.assertIn("disc-1", second["policy_cover_observation_bindings"])
        self.assertEqual(second["max_policy_cover_observations"], 8)

    @patch.object(fixed, "run_controller")
    def test_multi_observation_cover_accumulates_without_erasing_prior_evidence(self, controller):
        def open_for(discriminator):
            return {
                **self._open("OPEN__POLICY_COVER_OBSERVATION_BINDING_REQUIRED"),
                "next_required_edge": "AUTHENTICATED_SELECTED_POLICY_CHANGING_OBSERVATION",
                "next_observation_request": {
                    "schema": "PROJECT_BRAIN_POLICY_COVER_OBSERVATION_REQUEST_V1",
                    "state_id": "state-1",
                    "discriminator_id": discriminator,
                    "surviving_world_ids": ["w1", "w2"],
                    "observation_authority": False,
                },
            }

        controller.side_effect = [open_for("d1"), open_for("d2"), self._pass()]

        def provider(packet, index, prior):
            discriminator = packet["next_observation_request"]["discriminator_id"]
            return {
                "request_patch": {
                    "policy_cover_observation_bindings": {
                        discriminator: {
                            "receipt": {"path": discriminator + "-r", "git_blob_sha": "a"},
                            "verification": {"path": discriminator + "-v", "git_blob_sha": "b"},
                        }
                    }
                }
            }

        out = fixed.run(
            self._request(),
            proposal_provider=provider,
            provider_max_candidates=1,
        )

        self.assertTrue(out["pass"], out)
        self.assertEqual(controller.call_count, 3)
        final_request = controller.call_args_list[2].args[0]
        self.assertEqual(
            set(final_request["policy_cover_observation_bindings"]),
            {"d1", "d2"},
        )

    def test_existing_policy_cover_observation_binding_cannot_be_rewritten(self):
        current = {
            **self._request(),
            "policy_cover_observation_bindings": {
                "d1": {"receipt": {"path": "old"}}
            },
        }
        candidate = {
            "request_patch": {
                "policy_cover_observation_bindings": {
                    "d1": {"receipt": {"path": "new"}}
                }
            }
        }
        merged, error = fixed._merge_candidate(current, candidate)
        self.assertIsNone(merged)
        self.assertEqual(
            error,
            "POLICY_COVER_OBSERVATION_BINDING_MUTATION_FORBIDDEN:d1",
        )

    @patch.object(fixed, "repair_existing_adequacy")
    @patch.object(fixed, "run_controller")
    def test_existing_adequacy_evidence_is_reused_without_external_provider(
        self, controller, automatic
    ):
        opened = {
            **self._open("OPEN__POSITIVE_POLICY_ADEQUACY_CERTIFICATE_REQUIRED"),
            "next_required_edge": "AUTHENTICATED_POSITIVE_POLICY_ADEQUACY_CERTIFICATE",
            "next_policy_request": {
                "schema": "PROJECT_BRAIN_MINIMUM_POLICY_REPAIR_REQUEST_V1",
                "required_artifact": "POSITIVE_POLICY_ADEQUACY_CERTIFICATE",
                "selected_policy_id": "policy.p",
                "policy_adequacy_authority": False,
            },
        }
        controller.side_effect = [opened, self._pass()]
        automatic.return_value = {
            "pass": True,
            "status": "PASS__EXISTING_POLICY_ADEQUACY_BINDINGS_DISCOVERED_FOR_REVERIFICATION",
            "request_patch": {
                "decision_payload": {
                    "context_id": "auto-reused",
                    "bound_relevance_cegar_loop": {
                        "cegar_problem": {
                            "policy_adequacy_bindings": {
                                "policy.p": {"adequacy_certificate_path": "canonical/governance/p.json"}
                            }
                        }
                    },
                }
            },
            "added_policy_ids": ["policy.p"],
            "repair_authority": False,
        }

        out = fixed.run(self._request())

        self.assertTrue(out["pass"], out)
        self.assertEqual(controller.call_count, 2)
        automatic.assert_called_once()
        second = controller.call_args_list[1].args[0]
        self.assertEqual(second["decision_payload"]["context_id"], "auto-reused")
        auto_trace = out["r2_fixed_point_trace"][0][
            "automatic_existing_adequacy_repair"
        ]
        self.assertTrue(auto_trace["pass"])
        self.assertEqual(auto_trace["added_policy_ids"], ["policy.p"])
        self.assertFalse(auto_trace["repair_authority"])
        self.assertTrue(auto_trace["downstream_reverification_required"])

    @patch.object(fixed, "repair_basis_discriminator")
    @patch.object(fixed, "repair_existing_adequacy")
    @patch.object(fixed, "run_controller")
    def test_conflict_witness_basis_question_is_generated_without_external_provider(
        self, controller, existing_repair, basis_repair
    ):
        opened = {
            **self._open(
                "OPEN__POLICY_CHANGING_DISCRIMINATOR_OR_STRONGER_ADEQUACY_REQUIRED"
            ),
            "next_required_edge": (
                "ONE_POLICY_CHANGING_DISCRIMINATOR_OR_STRONGER_POSITIVE_ADEQUACY"
            ),
            "next_policy_request": {
                "schema": "PROJECT_BRAIN_MINIMUM_POLICY_REPAIR_REQUEST_V1",
                "required_artifact": (
                    "POLICY_CHANGING_DISCRIMINATOR_OR_STRONGER_ADEQUACY"
                ),
                "search_context": {
                    "decision_basis": ["x"],
                    "conflicting_policy_region_witness": [
                        {
                            "model_id": "m0",
                            "valuation": {"x": False},
                            "adequate_policy_ids": ["p0"],
                        },
                        {
                            "model_id": "m1",
                            "valuation": {"x": True},
                            "adequate_policy_ids": ["p1"],
                        },
                    ],
                },
            },
        }
        controller.side_effect = [opened, self._pass()]
        existing_repair.return_value = {
            "pass": False,
            "status": "NOT_APPLICABLE__POLICY_ARTIFACT_NOT_REUSE_DISCOVERABLE",
        }
        basis_repair.return_value = {
            "pass": True,
            "status": "PASS__DECISION_BASIS_DISCRIMINATORS_PROPOSED_FOR_REVERIFICATION",
            "request_patch": {
                "decision_payload": {
                    "context_id": "basis-repaired",
                    "bound_relevance_cegar_loop": {
                        "cegar_problem": {
                            "discriminators": [
                                {
                                    "discriminator_id": "auto-x",
                                    "formula": {"op": "ATOM", "id": "x"},
                                }
                            ]
                        }
                    },
                }
            },
            "added_discriminator_ids": ["auto-x"],
            "added_basis_atoms": ["x"],
        }

        out = fixed.run(self._request())

        self.assertTrue(out["pass"], out)
        self.assertEqual(controller.call_count, 2)
        existing_repair.assert_called_once()
        basis_repair.assert_called_once()
        second = controller.call_args_list[1].args[0]
        self.assertEqual(second["decision_payload"]["context_id"], "basis-repaired")
        trace = out["r2_fixed_point_trace"][0][
            "automatic_basis_discriminator_repair"
        ]
        self.assertTrue(trace["pass"])
        self.assertEqual(trace["added_basis_atoms"], ["x"])
        self.assertFalse(trace["semantic_truth_authority"])
        self.assertTrue(trace["downstream_cegar_reverification_required"])

    @patch.object(fixed, "run_controller")
    def test_exact_policy_repair_request_reaches_resolver(self, controller):
        opened = {
            **self._open("OPEN__POSITIVE_POLICY_ADEQUACY_CERTIFICATE_REQUIRED"),
            "next_required_edge": "AUTHENTICATED_POSITIVE_POLICY_ADEQUACY_CERTIFICATE",
            "next_policy_request": {
                "schema": "PROJECT_BRAIN_MINIMUM_POLICY_REPAIR_REQUEST_V1",
                "required_artifact": "POSITIVE_POLICY_ADEQUACY_CERTIFICATE",
                "selected_policy_id": "policy.p",
                "policy_adequacy_authority": False,
            },
        }
        controller.side_effect = [opened, self._pass()]
        provider = Mock(
            return_value={
                "request_patch": {
                    "decision_payload": {"context_id": "refined-context"}
                }
            }
        )

        out = fixed.run(self._request(), proposal_provider=provider)

        self.assertTrue(out["pass"], out)
        packet = provider.call_args.args[0]
        self.assertEqual(
            packet["next_policy_request"]["required_artifact"],
            "POSITIVE_POLICY_ADEQUACY_CERTIFICATE",
        )
        self.assertEqual(
            packet["next_required_edge"],
            "AUTHENTICATED_POSITIVE_POLICY_ADEQUACY_CERTIFICATE",
        )

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


    def test_next_meta_action_is_total_and_non_authoritative(self):
        cases = [
            (
                {"pass": True, "status": "PASS__DONE"},
                "RETURN_VERIFIED_GOAL_SATISFACTION",
            ),
            (
                {
                    "pass": False,
                    "status": "OPEN__INFO",
                    "next_information_request": {"predicate_id": "p"},
                },
                "ACQUIRE_MINIMUM_DECISION_INFORMATION",
            ),
            (
                {
                    "pass": False,
                    "status": "OPEN__OBS",
                    "next_observation_request": {"discriminator_id": "d"},
                },
                "ACQUIRE_MINIMUM_DECISION_INFORMATION",
            ),
            (
                {
                    "pass": False,
                    "status": "OPEN__POLICY",
                    "next_policy_request": {"required_artifact": "A"},
                },
                "REPAIR_OR_PROVE_POLICY_ADEQUACY",
            ),
            (
                {
                    "pass": False,
                    "status": "OPEN__EXEC",
                    "next_required_edge": "AUTHENTICATED_SELECTED_POLICY_TO_EXECUTION_BINDING",
                },
                "BIND_OR_EXECUTE_SELECTED_POLICY",
            ),
            (
                {
                    "pass": False,
                    "status": "OPEN__ACCEPT",
                    "next_required_edge": "INDEPENDENT_ACTUAL_GOAL_SATISFACTION_VERIFICATION",
                },
                "VERIFY_ACTUAL_GOAL_SATISFACTION",
            ),
            (
                {"pass": False, "status": "FAIL_CLOSED"},
                "ABSTAIN_FAIL_CLOSED",
            ),
            (
                {
                    "pass": False,
                    "status": "OPEN__UNKNOWN",
                    "next_required_edge": "EXACT_UNKNOWN_EDGE",
                },
                "RESOLVE_EXACT_OPEN_EDGE",
            ),
        ]
        for payload, expected in cases:
            with self.subTest(expected=expected):
                action = fixed._next_meta_action(payload)
                self.assertEqual(action["kind"], expected)
                self.assertTrue(action["routing_total"])
                self.assertFalse(action["semantic_truth_authority"])
                self.assertFalse(action["policy_adequacy_authority"])
                self.assertFalse(action["execution_authority"])
                self.assertFalse(action["acceptance_authority"])
                self.assertFalse(action["terminal_authority"])

    @patch.object(fixed, "run_controller")
    def test_every_decorated_open_result_exposes_one_typed_next_move(self, controller):
        controller.return_value = {
            **self._open("OPEN__GOAL_SATISFACTION_BINDING_REQUIRED"),
            "next_required_edge": "INDEPENDENT_ACTUAL_GOAL_SATISFACTION_VERIFICATION",
        }
        out = fixed.run(self._request())
        self.assertFalse(out["pass"])
        self.assertTrue(out["r2_control_policy_total"])
        self.assertEqual(
            out["r2_next_meta_action"]["kind"],
            "VERIFY_ACTUAL_GOAL_SATISFACTION",
        )
        self.assertEqual(
            out["r2_next_meta_action"]["required_edge"],
            "INDEPENDENT_ACTUAL_GOAL_SATISFACTION_VERIFICATION",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
