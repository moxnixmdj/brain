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

    def test_missing_decision_context_bootstraps_lossless_opaque_overapproximation(self):
        raw = {
            "pass": True,
            "task_contract_sha256": "contract-sha",
            "task_sha256": "goal-sha",
            "nonwhitespace_source_coverage_complete": True,
            "acceptance_contract": {
                "obligations": [
                    {"obligation_id": "RAWREQ:o1"},
                    {"obligation_id": "RAWREQ:o2"},
                ]
            },
        }
        observed = {}

        def p3(payload, *, repo_root=None):
            observed.update(payload)
            return {
                "pass": False,
                "status": "FAIL_CLOSED",
                "reason": "AUTHENTICATED_POLICY_COVER_INCOMPLETE",
            }

        with patch.object(controller, "compile_contract", return_value=raw), \
             patch.object(controller, "evaluate_p3", side_effect=p3):
            out = controller.run(
                {"task_id": "R2_TEST_MISSING_CONTEXT", "goal": "Choose the adequate action."}
            )

        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__ADEQUATE_POLICY_OR_SEMANTIC_COVERAGE_REQUIRED")
        binding = out["goal_to_decision_binding"]
        self.assertEqual(binding["status"], "PASS__OPAQUE_GOAL_CONTEXT_BOOTSTRAPPED_BY_CONSTRUCTION")
        self.assertEqual(binding["opaque_remainder_obligation_count"], 2)
        self.assertTrue(binding["sound_overapproximation_only"])
        self.assertFalse(binding["semantic_completeness_claimed"])
        basis = observed["bound_relevance_cegar_loop"]["cegar_problem"]["decision_basis"]
        self.assertEqual(
            set(basis),
            {
                controller._opaque_goal_atom_id("RAWREQ:o1"),
                controller._opaque_goal_atom_id("RAWREQ:o2"),
            },
        )
        self.assertFalse(out["semantic_acceptance_complete"])
        self.assertFalse(out["actual_goal_satisfaction_verified"])


    def test_opaque_bootstrap_helper_preserves_every_raw_obligation_without_semantic_claim(self):
        raw = {
            "pass": True,
            "task_contract_sha256": "raw-contract-bootstrap",
            "nonwhitespace_source_coverage_complete": True,
            "acceptance_contract": {
                "obligations": [
                    {"obligation_id": "RAWREQ:a"},
                    {"obligation_id": "RAWREQ:b"},
                    {"obligation_id": "RAWREQ:c"},
                ]
            },
        }
        payload, binding = controller._bootstrap_opaque_decision_context(
            task_id="opaque-bootstrap-test",
            goal="Do something with three unknown requirements.",
            raw_contract=raw,
        )
        basis = payload["bound_relevance_cegar_loop"]["cegar_problem"]["decision_basis"]
        expected = [
            controller._opaque_goal_atom_id("RAWREQ:a"),
            controller._opaque_goal_atom_id("RAWREQ:b"),
            controller._opaque_goal_atom_id("RAWREQ:c"),
        ]
        self.assertEqual(basis, expected)
        self.assertEqual(binding["raw_obligation_count"], 3)
        self.assertEqual(binding["opaque_remainder_obligation_count"], 3)
        self.assertTrue(binding["all_raw_obligations_represented"])
        self.assertFalse(binding["semantic_authority"])
        self.assertFalse(binding["semantic_completeness_claimed"])

    def test_opaque_bootstrap_injects_verified_grounded_candidates_without_adequacy(self):
        raw = {
            "pass": True,
            "task_contract_sha256": "contract-grounded",
            "task_sha256": "goal-sha",
            "nonwhitespace_source_coverage_complete": True,
            "acceptance_contract": {
                "obligations": [{"obligation_id": "RAWREQ:o1"}]
            },
        }
        observed = {}
        frontier = {
            "pass": True,
            "status": "PASS__VERIFIED_GROUNDING_EXPOSED_AS_UNTRUSTED_POLICY_FRONTIER",
            "policy_conditions": {
                controller.grounded_policy_frontier.goal_scoped_policy_id("python.tests.audit.unittest", "Audit the Python tests with unittest."): {"op": "TRUE"}
            },
            "policy_adequacy_authority": False,
            "semantic_truth_authority": False,
        }

        def p3(payload, *, repo_root=None):
            observed.update(payload)
            return {
                "pass": False,
                "status": "FAIL_CLOSED",
                "reason": "BOUND_RELEVANCE_CEGAR_LOOP_UNSATISFIED",
                "detail": {
                    "loop_result": {
                        "pass": False,
                        "status": "OPEN__POSITIVE_POLICY_ADEQUACY_CERTIFICATE_REQUIRED",
                        "reason": "NO_AUTHENTICATED_POLICY_ADEQUACY",
                        "detail": {
                            "cegar": {
                                "decision_basis": list(
                                    payload["bound_relevance_cegar_loop"][
                                        "cegar_problem"
                                    ]["decision_basis"]
                                ),
                                "rejected_policy_adequacy_bindings": [{
                                    "policy_id": controller.grounded_policy_frontier.goal_scoped_policy_id("python.tests.audit.unittest", "Audit the Python tests with unittest."),
                                    "reason": "ADEQUACY_BINDING_MISSING",
                                }],
                            }
                        },
                    }
                },
            }

        with patch.object(controller, "compile_contract", return_value=raw), \
             patch.object(
                 controller.grounded_policy_frontier,
                 "propose",
                 return_value=frontier,
             ), \
             patch.object(controller, "evaluate_p3", side_effect=p3):
            out = controller.run({
                "task_id": "R2-GROUNDED-FRONTIER",
                "goal": "Audit the Python tests with unittest.",
            })

        problem = observed["bound_relevance_cegar_loop"]["cegar_problem"]
        self.assertEqual(
            problem["policy_conditions"],
            frontier["policy_conditions"],
        )
        self.assertEqual(problem["policy_adequacy_bindings"], {})
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["next_required_edge"],
            "AUTHENTICATED_POSITIVE_POLICY_ADEQUACY_CERTIFICATE",
        )
        self.assertEqual(
            out["next_policy_request"]["search_context"][
                "rejected_policy_candidates"
            ][0]["policy_id"],
            controller.grounded_policy_frontier.goal_scoped_policy_id("python.tests.audit.unittest", "Audit the Python tests with unittest."),
        )
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
        self.assertEqual(out["status"], "OPEN__USER_MINIMUM_CLARIFICATION_REQUIRED")
        self.assertEqual(out["next_information_request"]["predicate_id"], predicate_id)
        self.assertEqual(
            out["next_information_request"]["acquisition_plan"]["action"],
            "ASK_USER_MINIMUM_CLARIFICATION",
        )
        self.assertFalse(out["next_information_request"]["external_research_authorized"])
        self.assertFalse(out["actual_goal_satisfaction_verified"])

    def test_concrete_truth_request_survives_into_controller_acquisition_packet(self):
        request = self._base_request()
        predicate_id = "source-condition-sha256:critical"
        concrete = {
            "request_kind": "ACQUIRE_ONE_AUTHENTICATED_GOVERNING_REQUIREMENT_OBSERVATION",
            "minimum_observation_count": 1,
            "independent_verification_required": True,
        }
        opened = self._information_open(predicate_id)
        loop = opened["detail"]["loop_result"]
        loop["status"] = "OPEN__SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED"
        loop["reason"] = "SELECTED_SEMANTIC_TRUTH_CERTIFICATE_RETURNED_UNKNOWN_OR_FAILED"
        loop["next_information_request"] = concrete
        loop["next_required_edge"] = (
            "REGCAP_LOSS_CUSHION_MINIMUM_POLICY_CHANGING_INFORMATION"
        )
        template = {
            "schema": "PROJECT_BRAIN_SEMANTIC_TRUTH_MATERIALIZATION_TEMPLATE_V1",
            "truth_kind": "REGCAP_LOSS_CUSHION_GROUNDING",
            "claim_kind": "RELATIVE_RIVAL_SELECTION",
            "target_concept_id": "REGCAP::CCOB",
            "provider_semantic_truth_authority": False,
        }
        loop["checker_materialization_template"] = template
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=opened):
            out = controller.run(request)

        self.assertFalse(out["pass"])
        packet = out["next_information_request"]
        self.assertEqual(packet["predicate_id"], predicate_id)
        self.assertEqual(packet["truth_next_information_request"], concrete)
        self.assertEqual(
            packet["truth_next_required_edge"],
            "REGCAP_LOSS_CUSHION_MINIMUM_POLICY_CHANGING_INFORMATION",
        )
        self.assertEqual(packet["checker_materialization_template"], template)
        self.assertFalse(packet["information_authority"])
        self.assertFalse(packet["semantic_truth_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_concrete_truth_request_is_preserved_for_information_provider(self):
        request = self._base_request()
        predicate_id = "source-condition-sha256:critical"
        concrete = {
            "request_kind": "ACQUIRE_ONE_AUTHENTICATED_GOVERNING_REQUIREMENT_OBSERVATION",
            "minimum_observation_count": 1,
            "independent_verification_required": True,
        }
        opened = self._information_open(predicate_id)
        loop = opened["detail"]["loop_result"]
        loop["status"] = "OPEN__SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED"
        loop["next_information_request"] = concrete
        loop["next_required_edge"] = (
            "REGCAP_LOSS_CUSHION_MINIMUM_POLICY_CHANGING_INFORMATION"
        )
        provider = Mock(return_value=None)
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=opened):
            out = controller.run(request, information_provider=provider)

        self.assertFalse(out["pass"])
        provider.assert_called_once()
        packet = provider.call_args.args[0]
        self.assertEqual(packet["truth_next_information_request"], concrete)
        self.assertEqual(
            packet["truth_next_required_edge"],
            "REGCAP_LOSS_CUSHION_MINIMUM_POLICY_CHANGING_INFORMATION",
        )


    def test_positive_adequacy_gap_is_preserved_as_exact_policy_repair(self):
        request = self._base_request()
        opened = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "BOUND_RELEVANCE_CEGAR_LOOP_UNSATISFIED",
            "detail": {
                "loop_result": {
                    "pass": False,
                    "status": "OPEN__POSITIVE_POLICY_ADEQUACY_CERTIFICATE_REQUIRED",
                    "reason": "NO_AUTHENTICATED_POLICY_ADEQUACY",
                    "detail": {
                        "selected_policy_id": "policy.p",
                        "cegar": {"reason": "NO_AUTHENTICATED_POLICY_ADEQUACY"},
                    },
                }
            },
        }
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=opened):
            out = controller.run(request)

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__POSITIVE_POLICY_ADEQUACY_CERTIFICATE_REQUIRED",
        )
        self.assertEqual(
            out["next_required_edge"],
            "AUTHENTICATED_POSITIVE_POLICY_ADEQUACY_CERTIFICATE",
        )
        policy_request = out["next_policy_request"]
        self.assertEqual(
            policy_request["required_artifact"],
            "POSITIVE_POLICY_ADEQUACY_CERTIFICATE",
        )
        self.assertEqual(policy_request["selected_policy_id"], "policy.p")
        self.assertFalse(policy_request["policy_adequacy_authority"])
        self.assertFalse(policy_request["semantic_truth_authority"])
        self.assertEqual(
            policy_request["preferred_resolution_order"][0],
            "REPAIR_OR_REUSE_EXISTING_DECLARED_POLICY_BEFORE_INVENTION",
        )
        self.assertIn(
            "CERTIFY_ONE_COMMON_BRAIN_OWNED_POLICY_IF_POSSIBLE",
            policy_request["preferred_resolution_order"],
        )

    def test_common_policy_selection_binding_gap_is_not_collapsed_to_generic_semantics(self):
        request = self._base_request()
        opened = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "BOUND_RELEVANCE_CEGAR_LOOP_UNSATISFIED",
            "detail": {
                "loop_result": {
                    "pass": False,
                    "status": "OPEN__COMMON_POLICY_SELECTION_BINDING_REQUIRED",
                    "reason": "COMMON_POLICY_HAS_NO_EXACT_SOURCE_POSITIVE_SELECTION_CONTRACT",
                    "detail": {"selected_policy_id": "policy.certified"},
                }
            },
        }
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=opened):
            out = controller.run(request)

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["next_required_edge"],
            "EXACT_SOURCE_POSITIVE_SELECTION_CONTRACT_FOR_CERTIFIED_COMMON_POLICY",
        )
        self.assertEqual(
            out["next_policy_request"]["selected_policy_id"],
            "policy.certified",
        )
        self.assertEqual(
            out["next_policy_request"]["required_artifact"],
            "SOURCE_POSITIVE_SELECTION_CONTRACT",
        )

    def test_policy_repair_request_exposes_only_verified_cegar_search_frontier(self):
        request = self._base_request()
        opened = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "BOUND_RELEVANCE_CEGAR_LOOP_UNSATISFIED",
            "detail": {
                "loop_result": {
                    "pass": False,
                    "status": "OPEN__POLICY_CHANGING_DISCRIMINATOR_OR_STRONGER_ADEQUACY_REQUIRED",
                    "reason": "NO_DECLARED_ONE_STEP_DISCRIMINATOR_CLOSES_POLICY_REGIONS",
                    "detail": {
                        "cegar": {
                            "decision_basis": ["x", "y"],
                            "surviving_model_count": 2,
                            "authenticated_policy_adequacy": [
                                {"policy_id": "policy.a", "receipt": "opaque"},
                                {"policy_id": "policy.b", "receipt": "opaque"},
                            ],
                            "rejected_policy_adequacy_bindings": [
                                {"policy_id": "policy.c", "reason": "ADEQUACY_BINDING_MISSING"},
                            ],
                            "conflicting_policy_region_witness": [
                                {
                                    "model_id": "m0",
                                    "valuation": {"x": False, "y": False},
                                    "adequate_policy_ids": ["policy.a"],
                                },
                                {
                                    "model_id": "m1",
                                    "valuation": {"x": True, "y": False},
                                    "adequate_policy_ids": ["policy.b"],
                                },
                            ],
                            "certified_common_policies": [],
                        }
                    },
                }
            },
        }
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=opened):
            out = controller.run(request)

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["next_required_edge"],
            "ONE_POLICY_CHANGING_DISCRIMINATOR_OR_STRONGER_POSITIVE_ADEQUACY",
        )
        search = out["next_policy_request"]["search_context"]
        self.assertEqual(
            search["authenticated_policy_ids"],
            ["policy.a", "policy.b"],
        )
        self.assertEqual(
            search["rejected_policy_candidates"],
            [{"policy_id": "policy.c", "reason": "ADEQUACY_BINDING_MISSING"}],
        )
        self.assertEqual(search["decision_basis"], ["x", "y"])
        self.assertEqual(search["surviving_model_count"], 2)
        self.assertEqual(
            search["conflicting_policy_region_witness"][0]["adequate_policy_ids"],
            ["policy.a"],
        )
        order = out["next_policy_request"]["preferred_resolution_order"]
        self.assertEqual(
            order[0],
            "REPAIR_OR_REUSE_EXISTING_DECLARED_POLICY_BEFORE_INVENTION",
        )
        self.assertIn(
            "INVENT_A_NEW_POLICY_ONLY_IF_THE_CURRENT_AUTHENTICATED_SET_CANNOT_COVER_THE_CONFLICT_WITNESS",
            order,
        )
        self.assertFalse(out["next_policy_request"]["policy_adequacy_authority"])
        self.assertFalse(out["next_policy_request"]["semantic_truth_authority"])

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

    def test_raw_source_provider_material_cannot_bypass_checker_ingestion(self):
        request = self._base_request()
        request["max_information_rounds"] = 1
        predicate_id = "source-condition-sha256:a"
        provider = Mock(return_value={
            "kind": controller.source_proof_material.KIND,
            "source_text": "Total exposure means exposure_amount.",
            "source_id": "policy",
            "fact_source": '{"schema_id":"FINANCE_TYPED_CONTEXT_V1","fields":{}}',
            "fact_source_id": "facts",
            "condition_holds": True,
        })
        still_open = self._information_open(predicate_id)
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=still_open):
            out = controller.run(request, information_provider=provider)

        self.assertFalse(out["pass"])
        provider.assert_called_once()
        self.assertEqual(
            out["information_material_rejection"]["status"],
            "SOURCE_PROOF_MATERIAL_REJECTED",
        )
        self.assertIn(
            "UNMODELED_SOURCE_PROOF_MATERIAL_FIELDS",
            out["information_material_rejection"]["reason"],
        )
        self.assertEqual(
            out["information_trace"][-1]["ingestion_status"],
            "SOURCE_PROOF_MATERIAL_REJECTED",
        )
        self.assertFalse(out["actual_goal_satisfaction_verified"])
        self.assertFalse(out["terminal_authority"])

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

    def test_execution_provider_replaces_only_execution_carrier(self):
        request = self._base_request()
        request["execution_problem"] = {"task_id": "exec", "target_effects": ["DONE"]}
        request["policy_execution_binding"] = {"receipt": {}, "verification": {}}
        request["goal_satisfaction_binding"] = {"receipt": {}, "verification": {}}
        execution_pass = {"pass": True, "status": "SOLVED__VERIFIED_EPISODE"}
        provider = Mock(return_value=execution_pass)

        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=self._decision_pass()), \
             patch.object(controller, "_authenticate_policy_execution_binding", return_value={"pass": True}), \
             patch.object(controller, "run_universal") as default_solver, \
             patch.object(
                 controller,
                 "_authenticate_goal_satisfaction_binding",
                 return_value=self._goal_satisfaction_pass(),
             ):
            out = controller.run(request, execution_provider=provider)

        self.assertTrue(out["pass"], out)
        provider.assert_called_once()
        default_solver.assert_not_called()
        kwargs = provider.call_args.kwargs
        self.assertEqual(kwargs["episode_id"], "R2_TEST_001")
        self.assertEqual(kwargs["scope_id"], "general-adequate-decision")
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertFalse(out["terminal_authority"])

    def test_execution_provider_cannot_bypass_policy_execution_binding(self):
        request = self._base_request()
        request["execution_problem"] = {"task_id": "exec", "target_effects": ["DONE"]}
        provider = Mock(return_value={"pass": True})
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=self._decision_pass()):
            out = controller.run(request, execution_provider=provider)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__POLICY_EXECUTION_BINDING_REQUIRED")
        provider.assert_not_called()

    def test_non_mapping_execution_provider_result_fails_closed(self):
        request = self._base_request()
        request["execution_problem"] = {"task_id": "exec", "target_effects": ["DONE"]}
        request["policy_execution_binding"] = {"receipt": {}, "verification": {}}
        provider = Mock(return_value="not-an-execution-result")
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(controller, "_authenticate_goal_binding", return_value=self._goal_binding_pass()), \
             patch.object(controller, "evaluate_p3", return_value=self._decision_pass()), \
             patch.object(controller, "_authenticate_policy_execution_binding", return_value={"pass": True}):
            out = controller.run(request, execution_provider=provider)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("EXECUTION_PROVIDER_RESULT_NOT_OBJECT", out["reason"])

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


    def test_partial_goal_binding_can_preserve_unknown_goal_remainder_opaquely(self):
        goal = "Do the useful thing while preserving every unknown requirement."
        raw_contract = {
            "pass": True,
            "task_contract_sha256": "raw-contract-1",
            "nonwhitespace_source_coverage_complete": True,
            "acceptance_contract": {
                "obligations": [
                    {"obligation_id": "RAWREQ:o1"},
                    {"obligation_id": "RAWREQ:o2"},
                ]
            },
        }
        opaque = controller._opaque_goal_atom_id("RAWREQ:o2")
        decision_payload = {
            "context_id": "ctx",
            "v3_input": {"task": {}},
            "bound_relevance_cegar_loop": {
                "cegar_problem": {
                    "decision_basis": ["SEM:o1", opaque],
                },
                "truth_payloads_by_discriminator_id": {},
                "truth_payloads_by_predicate_id": {},
                "source_positive_selection_contracts": {},
            },
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / "canonical/governance"
            ver = root / "canonical/verification"
            gov.mkdir(parents=True)
            ver.mkdir(parents=True)

            receipt_path = gov / "partial_goal.json"
            verify_path = ver / "partial_goal_verify.json"
            goal_sha = controller.sha256(goal.encode("utf-8")).hexdigest()
            decision_sha = controller._digest(decision_payload)
            receipt = {
                "schema": controller.PARTIAL_GOAL_BINDING_SCHEMA,
                "goal_sha256": goal_sha,
                "decision_payload_sha256": decision_sha,
                "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
                "binding_proved": True,
                "all_raw_obligations_represented": True,
                "sound_overapproximation_proved": True,
                "load_bearing_constraints_preserved": True,
                "fully_semantically_bound_obligation_ids": ["RAWREQ:o1"],
                "semantic_atom_ids_by_obligation": {
                    "RAWREQ:o1": ["SEM:o1"],
                },
                "opaque_remainder_atom_ids": {
                    "RAWREQ:o2": opaque,
                },
            }
            receipt_path.write_text(
                json.dumps(receipt, sort_keys=True), encoding="utf-8"
            )
            receipt_blob = controller._git_blob_sha(receipt_path)
            verification = {
                "schema": controller.PARTIAL_GOAL_BINDING_VERIFY_SCHEMA,
                "subject_git_blob_sha": receipt_blob,
                "goal_sha256": goal_sha,
                "decision_payload_sha256": decision_sha,
                "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
                "pass": True,
                "independent_verified": True,
                "representation_completeness_verified": True,
                "semantic_atom_mapping_verified": True,
                "opaque_remainder_completeness_verified": True,
                "sound_overapproximation_verified": True,
                "load_bearing_constraints_verified": True,
            }
            verify_path.write_text(
                json.dumps(verification, sort_keys=True), encoding="utf-8"
            )
            binding = {
                "receipt": {
                    "path": "canonical/governance/partial_goal.json",
                    "git_blob_sha": receipt_blob,
                },
                "verification": {
                    "path": "canonical/verification/partial_goal_verify.json",
                    "git_blob_sha": controller._git_blob_sha(verify_path),
                },
            }
            out = controller._authenticate_partial_goal_binding(
                binding,
                goal=goal,
                decision_payload=decision_payload,
                raw_contract=raw_contract,
                repo_root=root,
            )

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__PARTIAL_GOAL_CONTEXT_SOUND_OVERAPPROXIMATION_AUTHENTICATED",
        )
        self.assertEqual(out["fully_semantically_bound_obligation_count"], 1)
        self.assertEqual(out["opaque_remainder_obligation_count"], 1)
        self.assertTrue(out["sound_overapproximation_only"])
        self.assertFalse(out["semantic_completeness_claimed"])

    def test_partial_goal_binding_fails_if_opaque_remainder_is_not_in_decision_basis(self):
        goal = "Keep the unparsed requirement alive."
        raw_contract = {
            "pass": True,
            "task_contract_sha256": "raw-contract-2",
            "nonwhitespace_source_coverage_complete": True,
            "acceptance_contract": {
                "obligations": [{"obligation_id": "RAWREQ:o1"}]
            },
        }
        opaque = controller._opaque_goal_atom_id("RAWREQ:o1")
        decision_payload = {
            "context_id": "ctx",
            "v3_input": {"task": {}},
            "bound_relevance_cegar_loop": {
                "cegar_problem": {"decision_basis": ["OTHER"]},
                "truth_payloads_by_discriminator_id": {},
                "truth_payloads_by_predicate_id": {},
                "source_positive_selection_contracts": {},
            },
        }
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gov = root / "canonical/governance"
            ver = root / "canonical/verification"
            gov.mkdir(parents=True)
            ver.mkdir(parents=True)
            receipt_path = gov / "partial_goal.json"
            verify_path = ver / "partial_goal_verify.json"
            goal_sha = controller.sha256(goal.encode("utf-8")).hexdigest()
            decision_sha = controller._digest(decision_payload)
            receipt = {
                "schema": controller.PARTIAL_GOAL_BINDING_SCHEMA,
                "goal_sha256": goal_sha,
                "decision_payload_sha256": decision_sha,
                "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
                "binding_proved": True,
                "all_raw_obligations_represented": True,
                "sound_overapproximation_proved": True,
                "load_bearing_constraints_preserved": True,
                "fully_semantically_bound_obligation_ids": [],
                "semantic_atom_ids_by_obligation": {},
                "opaque_remainder_atom_ids": {"RAWREQ:o1": opaque},
            }
            receipt_path.write_text(
                json.dumps(receipt, sort_keys=True), encoding="utf-8"
            )
            receipt_blob = controller._git_blob_sha(receipt_path)
            verification = {
                "schema": controller.PARTIAL_GOAL_BINDING_VERIFY_SCHEMA,
                "subject_git_blob_sha": receipt_blob,
                "goal_sha256": goal_sha,
                "decision_payload_sha256": decision_sha,
                "raw_task_contract_sha256": raw_contract["task_contract_sha256"],
                "pass": True,
                "independent_verified": True,
                "representation_completeness_verified": True,
                "semantic_atom_mapping_verified": True,
                "opaque_remainder_completeness_verified": True,
                "sound_overapproximation_verified": True,
                "load_bearing_constraints_verified": True,
            }
            verify_path.write_text(
                json.dumps(verification, sort_keys=True), encoding="utf-8"
            )
            binding = {
                "receipt": {
                    "path": "canonical/governance/partial_goal.json",
                    "git_blob_sha": receipt_blob,
                },
                "verification": {
                    "path": "canonical/verification/partial_goal_verify.json",
                    "git_blob_sha": controller._git_blob_sha(verify_path),
                },
            }
            out = controller._authenticate_partial_goal_binding(
                binding,
                goal=goal,
                decision_payload=decision_payload,
                raw_contract=raw_contract,
                repo_root=root,
            )

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__PARTIAL_GOAL_TO_DECISION_BINDING_INVALID",
        )
        self.assertIn(
            "PARTIAL_GOAL_REPRESENTATION_OUTSIDE_DECISION_BASIS",
            out["reason"],
        )

    def test_controller_can_enter_policy_reasoning_with_sound_partial_goal_binding(self):
        request = self._base_request()
        request.pop("goal_to_decision_binding")
        request["partial_goal_to_decision_binding"] = {
            "receipt": {},
            "verification": {},
        }
        request["goal_satisfaction_binding"] = {"receipt": {}, "verification": {}}
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()), \
             patch.object(
                 controller,
                 "_authenticate_partial_goal_binding",
                 return_value={
                     "pass": True,
                     "status": "PASS__PARTIAL_GOAL_CONTEXT_SOUND_OVERAPPROXIMATION_AUTHENTICATED",
                 },
             ), \
             patch.object(controller, "evaluate_p3", return_value=self._decision_pass()) as p3, \
             patch.object(
                 controller,
                 "_authenticate_goal_satisfaction_binding",
                 return_value=self._goal_satisfaction_pass(),
             ):
            out = controller.run(request)
        self.assertTrue(out["pass"], out)
        p3.assert_called_once()
        self.assertTrue(out["actual_goal_satisfaction_verified"])

    def test_controller_rejects_ambiguous_full_and_partial_goal_binding_modes(self):
        request = self._base_request()
        request["partial_goal_to_decision_binding"] = {
            "receipt": {},
            "verification": {},
        }
        with patch.object(controller, "compile_contract", return_value=self._raw_contract()):
            out = controller.run(request)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("GOAL_BINDING_MODE_AMBIGUOUS", out["reason"])


    def test_bound_evidence_rejects_symlink_outside_allowed_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            allowed = root / "canonical/governance"
            allowed.mkdir(parents=True)
            outside = root / "outside.json"
            outside.write_text('{"valid": true}', encoding="utf-8")
            link = allowed / "redirect.json"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation not supported on this runner")
            with self.assertRaisesRegex(
                controller.DecisionControllerError, "BOUND_SYMLINK_FORBIDDEN"
            ):
                controller._bound_json(
                    {
                        "path": "canonical/governance/redirect.json",
                        "git_blob_sha": controller._git_blob_sha(outside),
                    },
                    repo_root=root,
                    prefixes=("canonical/governance/",),
                )

    def test_bound_evidence_accepts_regular_in_scope_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            allowed = root / "canonical/governance"
            allowed.mkdir(parents=True)
            receipt = allowed / "receipt.json"
            receipt.write_text('{"valid": true}', encoding="utf-8")
            obj, rel, blob = controller._bound_json(
                {
                    "path": "canonical/governance/receipt.json",
                    "git_blob_sha": controller._git_blob_sha(receipt),
                },
                repo_root=root,
                prefixes=("canonical/governance/",),
            )
            self.assertTrue(obj["valid"])
            self.assertEqual(rel, "canonical/governance/receipt.json")
            self.assertEqual(blob, controller._git_blob_sha(receipt))


if __name__ == "__main__":
    unittest.main(verbosity=2)
