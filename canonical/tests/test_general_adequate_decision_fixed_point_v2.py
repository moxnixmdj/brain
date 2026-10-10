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

    @patch.object(fixed, "run_controller")
    def test_bound_truth_origin_can_be_added_and_reverified(self, controller):
        predicate_id = "source-condition-sha256:critical"
        opened = {
            **self._open("OPEN__USER_MINIMUM_CLARIFICATION_REQUIRED"),
            "next_required_edge": "REGCAP_LOSS_CUSHION_MINIMUM_POLICY_CHANGING_INFORMATION",
            "next_information_request": {
                "schema": "PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_REQUEST_V1",
                "predicate_id": predicate_id,
                "truth_next_information_request": {
                    "request_kind": "ACQUIRE_ONE_AUTHENTICATED_GOVERNING_REQUIREMENT_OBSERVATION",
                    "minimum_observation_count": 1,
                },
                "information_authority": False,
                "semantic_truth_authority": False,
            },
        }
        controller.side_effect = [opened, self._pass()]
        truth_payload = {
            "truth_kind": "TEST_TRUTH_KIND",
            "predicate_id": predicate_id,
            "source_text": "bound evidence",
        }
        provider = Mock(return_value={
            "request_patch": {
                "information_origin_by_predicate_id": {
                    predicate_id: {
                        "context_value_bound": True,
                        "context_binding_id": "binding:critical",
                        "bound_truth_payload": truth_payload,
                    }
                }
            }
        })

        out = fixed.run(self._request(), proposal_provider=provider)

        self.assertTrue(out["pass"], out)
        self.assertEqual(controller.call_count, 2)
        packet = provider.call_args.args[0]
        self.assertIn(
            "information_origin_by_predicate_id",
            packet["allowed_request_patch_fields"],
        )
        second = controller.call_args_list[1].args[0]
        bound = second["information_origin_by_predicate_id"][predicate_id]
        self.assertEqual(bound["context_binding_id"], "binding:critical")
        self.assertEqual(bound["bound_truth_payload"], truth_payload)

    def test_existing_information_origin_binding_cannot_be_rewritten(self):
        predicate_id = "source-condition-sha256:critical"
        current = {
            **self._request(),
            "information_origin_by_predicate_id": {
                predicate_id: {
                    "context_value_bound": True,
                    "context_binding_id": "binding:old",
                    "bound_truth_payload": {"truth_kind": "OLD"},
                }
            },
        }
        candidate = {
            "request_patch": {
                "information_origin_by_predicate_id": {
                    predicate_id: {
                        "context_value_bound": True,
                        "context_binding_id": "binding:new",
                        "bound_truth_payload": {"truth_kind": "NEW"},
                    }
                }
            }
        }
        merged, error = fixed._merge_candidate(current, candidate)
        self.assertIsNone(merged)
        self.assertEqual(
            error,
            "INFORMATION_ORIGIN_BINDING_MUTATION_FORBIDDEN:" + predicate_id,
        )

    def test_information_origin_bindings_accumulate_monotonically(self):
        p1 = "source-condition-sha256:p1"
        p2 = "source-condition-sha256:p2"
        current = {
            **self._request(),
            "information_origin_by_predicate_id": {
                p1: {
                    "context_value_bound": True,
                    "context_binding_id": "binding:p1",
                    "bound_truth_payload": {"truth_kind": "T1"},
                }
            },
        }
        candidate = {
            "request_patch": {
                "information_origin_by_predicate_id": {
                    p2: {
                        "context_value_bound": True,
                        "context_binding_id": "binding:p2",
                        "bound_truth_payload": {"truth_kind": "T2"},
                    }
                }
            }
        }
        merged, error = fixed._merge_candidate(current, candidate)
        self.assertIsNone(error)
        self.assertIsNotNone(merged)
        self.assertEqual(
            set(merged["information_origin_by_predicate_id"]),
            {p1, p2},
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

    @patch.object(fixed, "repair_basis_discriminator")
    @patch.object(fixed, "repair_existing_adequacy")
    @patch.object(fixed, "run_controller")
    def test_policy_adequacy_gap_uses_capability_expander_before_generic_provider(
        self, controller, existing_repair, basis_repair
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
        existing_repair.return_value = {
            "pass": False,
            "status": "UNRESOLVED__NO_NEW_EXISTING_POLICY_ADEQUACY_BINDING_DISCOVERED",
        }
        basis_repair.return_value = {
            "pass": False,
            "status": "NOT_APPLICABLE__NO_CONFLICT_WITNESS_BASIS_REPAIR",
        }
        expander = Mock(
            return_value={
                "source_id": "owned-capability-expander",
                "proposal": {
                    "request_patch": {
                        "decision_payload": {"context_id": "capability-expanded"}
                    }
                },
            }
        )
        provider = Mock()

        out = fixed.run(
            self._request(),
            capability_expander=expander,
            proposal_provider=provider,
        )

        self.assertTrue(out["pass"], out)
        provider.assert_not_called()
        expander.assert_called_once()
        packet = expander.call_args.args[0]
        self.assertEqual(
            packet["schema"],
            "PROJECT_BRAIN_R2_POLICY_ADEQUACY_CAPABILITY_EXPANSION_REQUEST_V1",
        )
        self.assertEqual(
            packet["next_policy_request"]["required_artifact"],
            "POSITIVE_POLICY_ADEQUACY_CERTIFICATE",
        )
        self.assertFalse(packet["expansion_authority"])
        self.assertFalse(packet["policy_adequacy_authority"])
        second = controller.call_args_list[1].args[0]
        self.assertEqual(
            second["decision_payload"]["context_id"],
            "capability-expanded",
        )
        record = out["r2_fixed_point_trace"][0][
            "policy_adequacy_capability_expansion"
        ]
        self.assertEqual(
            record["status"],
            "PROGRESSIVE_POLICY_ADEQUACY_EXPANSION_ACCEPTED_FOR_REVERIFICATION",
        )
        self.assertTrue(record["downstream_reverification_required"])
        self.assertFalse(record["policy_adequacy_authority"])

    @patch.object(fixed, "repair_basis_discriminator")
    @patch.object(fixed, "repair_existing_adequacy")
    @patch.object(fixed, "run_controller")
    def test_capability_expander_cannot_self_certify_policy_adequacy(
        self, controller, existing_repair, basis_repair
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
        controller.return_value = opened
        existing_repair.return_value = {
            "pass": False,
            "status": "UNRESOLVED__NO_NEW_EXISTING_POLICY_ADEQUACY_BINDING_DISCOVERED",
        }
        basis_repair.return_value = {
            "pass": False,
            "status": "NOT_APPLICABLE__NO_CONFLICT_WITNESS_BASIS_REPAIR",
        }
        expander = Mock(return_value={"pass": True, "status": "I_SAY_ADEQUATE"})

        out = fixed.run(self._request(), capability_expander=expander)

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["r2_fixed_point_status"],
            "OPEN__R2_EDGE_RESOLVER_UNAVAILABLE",
        )
        record = out["r2_fixed_point_trace"][0][
            "policy_adequacy_capability_expansion"
        ]
        self.assertEqual(record["status"], "CANDIDATE_REJECTED")
        self.assertEqual(record["reason"], "REQUEST_PATCH_REQUIRED")
        self.assertFalse(record["policy_adequacy_authority"])

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
            ({"pass": True, "status": "PASS__DONE"}, "RETURN_VERIFIED_GOAL_SATISFACTION"),
            ({"pass": False, "status": "OPEN__INFO", "next_information_request": {"predicate_id": "p"}}, "ACQUIRE_MINIMUM_DECISION_INFORMATION"),
            ({"pass": False, "status": "OPEN__OBS", "next_observation_request": {"discriminator_id": "d"}}, "ACQUIRE_MINIMUM_DECISION_INFORMATION"),
            ({"pass": False, "status": "OPEN__POLICY", "next_policy_request": {"required_artifact": "A"}}, "REPAIR_OR_PROVE_POLICY_ADEQUACY"),
            ({"pass": False, "status": "OPEN__EXEC", "next_required_edge": "AUTHENTICATED_SELECTED_POLICY_TO_EXECUTION_BINDING"}, "BIND_OR_EXECUTE_SELECTED_POLICY"),
            ({"pass": False, "status": "OPEN__ACCEPT", "next_required_edge": "INDEPENDENT_ACTUAL_GOAL_SATISFACTION_VERIFICATION"}, "VERIFY_ACTUAL_GOAL_SATISFACTION"),
            ({"pass": False, "status": "FAIL_CLOSED"}, "ABSTAIN_FAIL_CLOSED"),
            ({"pass": False, "status": "OPEN__UNKNOWN", "next_required_edge": "EXACT_UNKNOWN_EDGE"}, "RESOLVE_EXACT_OPEN_EDGE"),
        ]
        for payload, expected in cases:
            with self.subTest(expected=expected):
                action = fixed._next_meta_action(payload)
                self.assertEqual(action["kind"], expected)
                self.assertTrue(action["routing_total"])
                for field in ("semantic_truth_authority", "policy_adequacy_authority", "execution_authority", "acceptance_authority", "terminal_authority"):
                    self.assertFalse(action[field])

    @patch.object(fixed, "run_controller")
    def test_every_decorated_open_result_exposes_one_typed_next_move(self, controller):
        controller.return_value = {
            **self._open("OPEN__GOAL_SATISFACTION_BINDING_REQUIRED"),
            "next_required_edge": "INDEPENDENT_ACTUAL_GOAL_SATISFACTION_VERIFICATION",
        }
        out = fixed.run(self._request())
        self.assertFalse(out["pass"])
        self.assertTrue(out["r2_control_policy_total"])
        self.assertEqual(out["r2_next_meta_action"]["kind"], "VERIFY_ACTUAL_GOAL_SATISFACTION")


    @patch.object(fixed.direct_adequacy, "preflight")
    @patch.object(fixed, "run_controller")
    def test_direct_semantic_open_hint_reaches_resolver_without_authority(
        self, controller, preflight
    ):
        preflight.return_value = {
            "matched": False,
            "pass": False,
            "status": "NOT_APPLICABLE__TERMINALLY_RELEVANT_EFFECT_AMBIGUITY",
            "direct_route_semantic_open": True,
            "route_id": "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_WORLDSET_V1",
            "effect_status": "OPEN__TERMINALLY_RELEVANT_EFFECT_AMBIGUITY",
            "minimum_discriminator_slots": ["B.effect"],
            "possible_outcomes": ["12", "13"],
            "world_count": 2,
        }
        controller.side_effect = [self._open(), self._pass()]
        provider = Mock(
            return_value={
                "request_patch": {
                    "decision_payload": {"context_id": "effect-world-resolved"}
                }
            }
        )

        out = fixed.run(self._request(), proposal_provider=provider)

        self.assertTrue(out["pass"], out)
        packet = provider.call_args.args[0]
        hint = packet["direct_preflight_hint"]
        self.assertEqual(hint["minimum_discriminator_slots"], ["B.effect"])
        self.assertEqual(hint["possible_outcomes"], ["12", "13"])
        self.assertEqual(hint["world_count"], 2)
        self.assertFalse(hint["semantic_truth_authority"])
        self.assertFalse(hint["execution_authority"])
        self.assertFalse(hint["acceptance_authority"])
        self.assertFalse(hint["terminal_authority"])
        self.assertEqual(
            out["r2_fixed_point_trace"][0]["direct_preflight_hint"],
            hint,
        )

    @patch.object(fixed.direct_adequacy, "preflight")
    @patch.object(fixed, "run_controller")
    def test_direct_semantic_open_hint_survives_without_resolver(
        self, controller, preflight
    ):
        preflight.return_value = {
            "matched": False,
            "pass": False,
            "status": "NOT_APPLICABLE__TERMINALLY_RELEVANT_EFFECT_AMBIGUITY",
            "direct_route_semantic_open": True,
            "route_id": "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_WORLDSET_V1",
            "effect_status": "OPEN__TERMINALLY_RELEVANT_EFFECT_AMBIGUITY",
            "minimum_discriminator_slots": ["B.effect"],
            "possible_outcomes": ["12", "13"],
            "world_count": 2,
        }
        controller.return_value = self._open()

        out = fixed.run(self._request())

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["r2_fixed_point_status"],
            "OPEN__R2_EDGE_RESOLVER_UNAVAILABLE",
        )
        hint = out["r2_fixed_point_trace"][0]["direct_preflight_hint"]
        self.assertEqual(hint["minimum_discriminator_slots"], ["B.effect"])
        self.assertFalse(hint["semantic_truth_authority"])


    @patch.object(fixed.direct_adequacy, "preflight")
    @patch.object(fixed, "run_controller")
    def test_residual_top_proof_obligations_reach_resolver_without_authority(
        self, controller, preflight
    ):
        obligation = {
            "kind": "PROVE_EFFECT_TARGET_SCOPE_OR_QUERY_EFFECT_ID_INVENTORY",
            "document_id": "A",
            "query_target_id": "reporting.threshold",
        }
        preflight.return_value = {
            "matched": False,
            "pass": False,
            "status": "NOT_APPLICABLE__SOURCE_BACKED_CROSS_DOCUMENT_SEMANTICS_OPEN",
            "direct_route_semantic_open": True,
            "route_id": "DIRECT_ADEQUACY::CROSS_DOCUMENT_RESIDUAL_EFFECT_FRONTIER_V1",
            "effect_status": "OPEN__RESIDUAL_TOP_EFFECT_MAY_CHANGE_QUERY",
            "blocking_residual_document_ids": ["A"],
            "next_proof_obligations": [obligation],
            "minimum_discriminator_slots": [],
            "possible_outcomes": [],
            "world_count": 1,
        }
        controller.side_effect = [self._open(), self._pass()]
        provider = Mock(
            return_value={
                "request_patch": {
                    "decision_payload": {"context_id": "residual-proof-resolved"}
                }
            }
        )

        out = fixed.run(self._request(), proposal_provider=provider)

        self.assertTrue(out["pass"], out)
        packet = provider.call_args.args[0]
        hint = packet["direct_preflight_hint"]
        self.assertEqual(hint["blocking_residual_document_ids"], ["A"])
        self.assertEqual(hint["next_proof_obligations"], [obligation])
        self.assertFalse(hint["semantic_truth_authority"])
        self.assertFalse(hint["execution_authority"])
        self.assertFalse(hint["acceptance_authority"])
        self.assertFalse(hint["terminal_authority"])


    @patch.object(fixed.direct_adequacy, "preflight")
    @patch.object(fixed, "run_controller")
    def test_combined_source_top_hint_reaches_resolver_without_authority(
        self, controller, preflight
    ):
        region = {
            "document_id": "A",
            "region_id": "A.unknown",
            "start": 290,
            "end": 305,
            "text_sha256": "b" * 64,
        }
        obligation = {
            "kind": "CLOSE_QUERY_RELEVANT_UNKNOWN_SOURCE_REGIONS_OR_PROVE_QUERY_TARGET_EXCLUDED",
            "document_id": "A",
            "open_unknown_region_ids": ["A.unknown"],
            "residual_state": "TOP_EFFECT_MAY_AFFECT_QUERY",
        }
        preflight.return_value = {
            "matched": False,
            "pass": False,
            "status": "NOT_APPLICABLE__COMBINED_SOURCE_SEMANTICS_OPEN",
            "direct_route_semantic_open": True,
            "route_id": "DIRECT_ADEQUACY::CROSS_DOCUMENT_SOURCE_RESIDUAL_FRONTIER_V1",
            "effect_status": "OPEN__QUERY_RELEVANT_SOURCE_TOP_REMAINS",
            "blocking_document_ids": ["A"],
            "blocking_unknown_regions": [region],
            "next_proof_obligations": [obligation],
            "minimum_discriminator_slots": [],
            "possible_outcomes": [],
            "world_count": 1,
            "query_relative_source_completeness_proved": False,
        }
        controller.side_effect = [self._open(), self._pass()]
        provider = Mock(
            return_value={
                "request_patch": {
                    "decision_payload": {"context_id": "combined-source-resolved"}
                }
            }
        )

        out = fixed.run(self._request(), proposal_provider=provider)

        self.assertTrue(out["pass"], out)
        hint = provider.call_args.args[0]["direct_preflight_hint"]
        self.assertEqual(hint["blocking_document_ids"], ["A"])
        self.assertEqual(hint["blocking_unknown_regions"], [region])
        self.assertEqual(hint["next_proof_obligations"], [obligation])
        self.assertFalse(hint["query_relative_source_completeness_proved"])
        self.assertFalse(hint["semantic_truth_authority"])
        self.assertFalse(hint["execution_authority"])
        self.assertFalse(hint["acceptance_authority"])
        self.assertFalse(hint["terminal_authority"])


    @patch.object(fixed.direct_adequacy, "preflight")
    @patch.object(fixed, "run_controller")
    def test_semantic_lattice_top_reaches_resolver_without_authority(
        self, controller, preflight
    ):
        atom = {
            "document_id": "B",
            "dimension": "DOCUMENT_EFFECT_RELATION",
            "effect_id": "B.t",
            "target_id": "threshold",
            "state": "TOP",
            "proof_obligation": {
                "kind": "PROVE_COMPLETE_DOCUMENT_EFFECT_RELATION",
                "document_id": "B",
                "source_id": "B",
                "effect_id": "B.t",
                "target_id": "threshold",
            },
        }
        preflight.return_value = {
            "matched": False,
            "pass": False,
            "status": "NOT_APPLICABLE__SEMANTIC_LATTICE_OPEN",
            "direct_route_semantic_open": True,
            "route_id": "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V1",
            "effect_status": "OPEN__QUERY_RELEVANT_EFFECT_SEMANTIC_TOP_REMAINS",
            "open_lattice_atoms": [atom],
            "next_proof_obligations": [atom["proof_obligation"]],
            "minimum_discriminator_slots": [],
            "possible_outcomes": [],
            "world_count": None,
            "query_relative_effect_semantics_finite": False,
        }
        controller.side_effect = [self._open(), self._pass()]
        provider = Mock(return_value={
            "request_patch": {"decision_payload": {"context_id": "relation-proved"}}
        })

        out = fixed.run(self._request(), proposal_provider=provider)

        self.assertTrue(out["pass"], out)
        hint = provider.call_args.args[0]["direct_preflight_hint"]
        self.assertEqual(hint["open_lattice_atoms"], [atom])
        self.assertFalse(hint["query_relative_effect_semantics_finite"])
        self.assertEqual(
            hint["next_proof_obligations"], [atom["proof_obligation"]]
        )
        self.assertFalse(hint["semantic_truth_authority"])
        self.assertFalse(hint["execution_authority"])
        self.assertFalse(hint["acceptance_authority"])
        self.assertFalse(hint["terminal_authority"])


    @patch.object(fixed.direct_adequacy, "preflight")
    @patch.object(fixed.direct_adequacy, "run")
    @patch.object(fixed, "run_controller")
    def test_progressive_repair_reenters_direct_adequacy_before_second_controller(
        self, controller, direct_run, preflight
    ):
        preflight.side_effect = [
            {
                "matched": False,
                "pass": False,
                "status": "NOT_APPLICABLE__SEMANTIC_LATTICE_OPEN",
                "direct_route_semantic_open": True,
                "route_id": "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V1",
                "effect_status": "OPEN__QUERY_RELEVANT_EFFECT_SEMANTIC_TOP_REMAINS",
                "open_lattice_atoms": [{"dimension": "DOCUMENT_EFFECT_RELATION"}],
                "next_proof_obligations": [{"kind": "PROVE_COMPLETE_DOCUMENT_EFFECT_RELATION"}],
            },
            {
                "matched": True,
                "pass": False,
                "status": "DIRECT_ADEQUACY_ROUTE_MATCHED",
                "route_id": "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V1",
            },
        ]
        controller.return_value = self._open()
        direct_run.return_value = {
            "pass": True,
            "status": "PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "execution_attempted": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
        provider = Mock(
            return_value={
                "request_patch": {
                    "decision_payload": {"context_id": "semantic-repair"}
                }
            }
        )

        out = fixed.run(self._request(), proposal_provider=provider)

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["r2_fixed_point_status"],
            "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED_AFTER_REPAIR",
        )
        self.assertEqual(controller.call_count, 1)
        self.assertEqual(preflight.call_count, 2)
        direct_run.assert_called_once()
        self.assertEqual(
            out["r2_fixed_point_trace"][-1]["kind"],
            "DIRECT_END_TO_END_ADEQUACY_REENTRY",
        )

    @patch.object(fixed.direct_adequacy, "preflight")
    @patch.object(fixed, "run_controller")
    def test_progressive_repair_refreshes_direct_semantic_hint(
        self, controller, preflight
    ):
        first_atom = {"dimension": "DOCUMENT_EFFECT_RELATION", "effect_id": "A"}
        second_atom = {"dimension": "DOCUMENT_EFFECT_RELATION", "effect_id": "B"}
        preflight.side_effect = [
            {
                "matched": False,
                "pass": False,
                "status": "OPEN_A",
                "direct_route_semantic_open": True,
                "route_id": "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V1",
                "open_lattice_atoms": [first_atom],
                "next_proof_obligations": [{"kind": "PROVE_A"}],
            },
            {
                "matched": False,
                "pass": False,
                "status": "OPEN_B",
                "direct_route_semantic_open": True,
                "route_id": "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_SEMANTIC_LATTICE_V1",
                "open_lattice_atoms": [second_atom],
                "next_proof_obligations": [{"kind": "PROVE_B"}],
            },
        ]
        controller.side_effect = [self._open(), self._open()]
        packets = []

        def provider(packet, index, prior):
            packets.append(packet)
            if len(packets) == 1:
                return {
                    "request_patch": {
                        "decision_payload": {"context_id": "first-repair"}
                    }
                }
            return None

        out = fixed.run(
            self._request(),
            proposal_provider=provider,
            provider_max_candidates=1,
        )

        self.assertFalse(out["pass"])
        self.assertEqual(controller.call_count, 2)
        self.assertEqual(preflight.call_count, 2)
        self.assertGreaterEqual(len(packets), 2)
        self.assertEqual(
            packets[0]["direct_preflight_hint"]["open_lattice_atoms"],
            [first_atom],
        )
        self.assertEqual(
            packets[1]["direct_preflight_hint"]["open_lattice_atoms"],
            [second_atom],
        )
        self.assertEqual(
            packets[1]["direct_preflight_hint"]["next_proof_obligations"],
            [{"kind": "PROVE_B"}],
        )

    @patch.object(fixed.direct_adequacy, "preflight")
    @patch.object(fixed.direct_adequacy, "run")
    @patch.object(fixed, "run_controller")
    def test_repaired_matched_direct_failure_remains_fail_closed(
        self, controller, direct_run, preflight
    ):
        preflight.side_effect = [
            {
                "matched": False,
                "pass": False,
                "status": "OPEN",
                "direct_route_semantic_open": True,
                "route_id": "DIRECT_ADEQUACY::TEST",
            },
            {
                "matched": True,
                "pass": False,
                "status": "DIRECT_ADEQUACY_ROUTE_MATCHED",
                "route_id": "DIRECT_ADEQUACY::TEST",
            },
        ]
        controller.return_value = self._open()
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
        provider = Mock(
            return_value={
                "request_patch": {
                    "decision_payload": {"context_id": "repaired-but-invalid"}
                }
            }
        )

        out = fixed.run(self._request(), proposal_provider=provider)

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["r2_fixed_point_status"],
            "OPEN__R2_REPAIRED_MATCHED_DIRECT_ROUTE_DID_NOT_VERIFY",
        )
        self.assertEqual(controller.call_count, 1)
        self.assertEqual(preflight.call_count, 2)
        direct_run.assert_called_once()
        self.assertFalse(
            out["r2_fixed_point_trace"][-1]["pass"]
        )


    @patch.object(fixed.direct_adequacy, "preflight")
    @patch.object(fixed, "run_controller")
    def test_effect_field_top_reaches_resolver_without_authority(
        self, controller, preflight
    ):
        atom = {
            "document_id": "B",
            "dimension": "DOCUMENT_EFFECT_FIELD",
            "effect_id": "B.t",
            "field": "supersedes",
            "target_id": "threshold",
            "state": "TOP",
            "proof_obligation": {
                "kind": "PROVE_DOCUMENT_EFFECT_FIELD",
                "document_id": "B",
                "source_id": "B",
                "effect_id": "B.t",
                "field": "supersedes",
                "target_id": "threshold",
            },
        }
        preflight.return_value = {
            "matched": False,
            "pass": False,
            "status": "NOT_APPLICABLE__SEMANTIC_LATTICE_OPEN",
            "direct_route_semantic_open": True,
            "route_id": "DIRECT_ADEQUACY::CROSS_DOCUMENT_EFFECT_FIELD_LATTICE_V2",
            "effect_status": "OPEN__QUERY_RELEVANT_EFFECT_FIELD_TOP_REMAINS",
            "open_lattice_atoms": [atom],
            "next_proof_obligations": [atom["proof_obligation"]],
            "minimum_discriminator_slots": [],
            "possible_outcomes": [],
            "world_count": None,
            "query_relative_effect_semantics_finite": False,
        }
        controller.side_effect = [self._open(), self._pass()]
        provider = Mock(return_value={
            "request_patch": {"decision_payload": {"context_id": "field-proved"}}
        })

        out = fixed.run(self._request(), proposal_provider=provider)

        self.assertTrue(out["pass"], out)
        hint = provider.call_args.args[0]["direct_preflight_hint"]
        self.assertEqual(hint["open_lattice_atoms"], [atom])
        self.assertEqual(
            hint["next_proof_obligations"], [atom["proof_obligation"]]
        )
        self.assertFalse(hint["query_relative_effect_semantics_finite"])
        self.assertFalse(hint["semantic_truth_authority"])
        self.assertFalse(hint["execution_authority"])
        self.assertFalse(hint["acceptance_authority"])
        self.assertFalse(hint["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
