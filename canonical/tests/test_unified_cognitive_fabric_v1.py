from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import Mock, patch
from pathlib import Path

from canonical.runtime import autonomous_verified_self_improvement_v1 as r3
from canonical.runtime import universal_verified_adaptive_solver_v12 as solver_v12
from canonical.runtime.unified_cognitive_fabric_v1 import catalog, run


class UnifiedCognitiveFabricV1Tests(unittest.TestCase):
    def setUp(self):
        self._state_tmp = tempfile.TemporaryDirectory()
        self._state_patch = patch.object(
            r3,
            "DEFAULT_STATE_PATH",
            Path(self._state_tmp.name) / "SELF_IMPROVEMENT_STATE_V1.json",
        )
        self._state_patch.start()

    def tearDown(self):
        self._state_patch.stop()
        self._state_tmp.cleanup()

    def test_catalog_exposes_single_front_door(self):
        c = catalog()
        self.assertEqual(c["status"], "LIVE_FEDERATED_COGNITIVE_FABRIC")
        self.assertTrue(c["single_front_door"])
        self.assertEqual(c["canonical_public_entrypoint"], "canonical.runtime.unified_cognitive_fabric_v1.run")
        self.assertEqual(c["subordinate_runtime_entrypoint"], "canonical.runtime.live_brain_runtime_v1.run")
        self.assertFalse(c["subordinate_runtime_public_authority"])
        self.assertGreaterEqual(c["verified_bound_capability_count"], 43)
        self.assertIn("RAW_GOAL", c["engines"])
        self.assertIn("ADEQUATE_DECISION", c["engines"])
        self.assertIn("ADAPTIVE_SOLVER", c["engines"])
        self.assertIn("LEARNING_EPISODE", c["engines"])
        self.assertIn("H100_INFERENCE", c["engines"])
        self.assertIn("MYSTERY_INFERENCE", c["engines"])
        self.assertIn("CAPABILITY_SCHEDULER", c["engines"])
        self.assertIn("UNIVERSAL_ESCAPE", c["engines"])
        self.assertIn("CERTIFIED_ROUTE", c["engines"])
        self.assertIn("TERMINAL_AUTOPILOT", c["engines"])
        self.assertIn("TERMINAL_ROOT", c["engines"])
        self.assertIn("TERMINAL_CLOSURE", c["engines"])
        self.assertIn("OWNERSHIP_CATALOG", c["engines"])
        self.assertIn("SEMANTIC_AMBIGUITY", c["engines"])
        self.assertIn("SEMANTIC_RELATION", c["engines"])
        self.assertIn("SEMANTIC_RELATION", c["engines"])
        self.assertIn("SEMANTIC_RELATION", c["engines"])
        self.assertIn("SEMANTIC_RELATION", c["engines"])
        self.assertIn("SEMANTIC_RELATION", c["engines"])
        self.assertIn("SEMANTIC_RELATION", c["engines"])
        self.assertIn("SEMANTIC_RELATION", c["engines"])
        self.assertGreater(c["brain_owned_transitive_file_count"], 1)
        self.assertGreater(c["brain_owned_transitive_source_bytes"], 0)
        self.assertIn(
            "canonical/runtime/unified_cognitive_fabric_v1.py",
            c["brain_owned_transitive_files"],
        )
        self.assertGreaterEqual(
            c["authority_pointer_runtime_reachability_census"][
                "authority_pointer_runtime_reference_count"
            ],
            1,
        )
        self.assertEqual(
            c["authority_pointer_runtime_reference_reachability_complete"],
            c["authority_pointer_runtime_reference_missing_count"] == 0,
        )
        self.assertTrue(c["current_live_ownership_ontology_complete"], c)
        self.assertTrue(c["live_owned_equals_fabric_reachable"], c)
        self.assertTrue(c["r1_structural_closure"], c)
        self.assertEqual(c["known_r1_residuals"], [])
        self.assertFalse(c["all_historical_brain_capabilities_unified"])
        self.assertNotIn(
            "H100_SPECIALIZED_INFERENCE_REGISTRIES_NOT_YET_EXPOSED_AS_FABRIC_CAPABILITIES",
            c["known_unified_fabric_residuals"],
        )
        self.assertNotIn(
            "MYSTERYMECHANISM_SPECIALIZED_INFERENCE_KERNELS_NOT_YET_EXPOSED_AS_FABRIC_CAPABILITIES",
            c["known_unified_fabric_residuals"],
        )
        self.assertFalse(c["all_historical_brain_capabilities_unified"])

    def test_raw_goal_dispatches(self):
        out = run({
            "mode": "RAW_GOAL",
            "payload": {
                "task_id": "FABRIC-RAW-UNKNOWN-001",
                "goal": "Calibrate the neutrino interferometer phase drift.",
            },
            "options": {"learn": False, "auto_repair": False},
        })
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertFalse(out["inner_pass"])
        self.assertEqual(out["result"]["failure_class"], "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP")
        self.assertEqual(out["result"]["_live_runtime"]["subruntime_entrypoint"], "canonical.runtime.live_brain_runtime_v1.run")

    def test_auto_raw_goal_enters_r2_decision_fixed_point(self):
        out = run({
            "payload": {
                "task_id": "FABRIC-AUTO-RAW-001",
                "goal": "Calibrate the neutrino interferometer phase drift.",
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "ADEQUATE_DECISION")
        self.assertEqual(out["requested_mode"], "AUTO")
        self.assertEqual(out["result"].get("r2_fixed_point_status"), "OPEN__R2_EDGE_RESOLVER_UNAVAILABLE")

    def test_auto_compiled_task_route_is_structurally_selected(self):
        out = run({
            "payload": {
                "task_id": "FABRIC-AUTO-COMPILED-001",
                "initial_facts": [],
                "target_effects": ["effect.that.does.not.exist"],
                "capability_inputs": {},
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "COMPILED_TASK")

    def test_auto_ambiguous_payload_fails_closed(self):
        out = run({"payload": {"mystery": "unmodeled"}})
        self.assertFalse(out["pass"])
        self.assertIn("AUTO_ROUTE_AMBIGUOUS_OR_UNMODELED", out["reason"])



    def test_auto_semantic_relation_proves_scoped_exact_equivalence(self):
        scope = "1" * 64
        out = run({
            "payload": {
                "expression_a": "reserve buffer",
                "expression_b": "liquidity cushion",
                "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
                "scope_sha256": scope,
                "evidence": {
                    "explicit_source_equivalence": {
                        "verified": True,
                        "relation": "EXACT_EQUIVALENT",
                        "source_kind": "EXPLICIT_SOURCE_DEFINITION",
                        "verifier_id": "verifier:source-definition",
                        "evidence_sha256": "e" * 64,
                        "scope_sha256": scope,
                    }
                },
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["strongest_proved_relation"],
            "EXACT_EQUIVALENT",
        )

    def test_auto_semantic_relation_can_stop_at_task_equivalence(self):
        scope = "2" * 64
        out = run({
            "payload": {
                "expression_a": "reserve buffer",
                "expression_b": "liquidity cushion",
                "required_relation": "TASK_EQUIVALENCE",
                "scope_sha256": scope,
                "evidence": {},
                "task_terminal_rows": [
                    {
                        "raw_id": "A",
                        "signature_complete": True,
                        "terminal_signature": {
                            "threshold": 10,
                            "action": "REDUCE",
                        },
                    },
                    {
                        "raw_id": "B",
                        "signature_complete": True,
                        "terminal_signature": {
                            "threshold": 10,
                            "action": "REDUCE",
                        },
                    },
                ],
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["strongest_proved_relation"],
            "TASK_EQUIVALENT",
        )
        self.assertTrue(out["result"]["task_equivalent"])

    def test_auto_semantic_ambiguity_skips_irrelevant_identity_question(self):
        out = run({
            "payload": {
                "ambiguity_owner": "USER_INTENT",
                "hypothesis_set_complete": True,
                "worlds": [
                    {
                        "world_id": "alice",
                        "terminal_signature_complete": True,
                        "terminal_signature": {"action": "SAME"},
                    },
                    {
                        "world_id": "sarah",
                        "terminal_signature_complete": True,
                        "terminal_signature": {"action": "SAME"},
                    },
                ],
                "observations": [],
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_AMBIGUITY")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["action"],
            "CONTINUE_WITHOUT_DISAMBIGUATION",
        )
        self.assertFalse(out["result"]["ask_user_required"])

    def test_auto_semantic_underdetermination_asks_only_when_action_differs(self):
        out = run({
            "payload": {
                "ambiguity_owner": "USER_INTENT",
                "hypothesis_set_complete": True,
                "worlds": [
                    {
                        "world_id": "alice",
                        "terminal_signature_complete": True,
                        "terminal_signature": {"recipient": "ALICE"},
                    },
                    {
                        "world_id": "sarah",
                        "terminal_signature_complete": True,
                        "terminal_signature": {"recipient": "SARAH"},
                    },
                ],
                "observations": [],
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_AMBIGUITY")
        self.assertFalse(out["inner_pass"])
        self.assertTrue(out["result"]["ask_user_required"])
        self.assertEqual(
            out["result"]["action"],
            "ASK_USER_MINIMUM_CLARIFICATION",
        )


    def test_auto_semantic_relation_uses_task_equivalence_without_claiming_identity(self):
        out = run({
            "payload": {
                "left_id": "reserve-buffer",
                "right_id": "liquidity-cushion",
                "scope_id": "finance:policy:2026",
                "required_relation": "CURRENT_DECISION_SUBSTITUTION",
                "terminal_signature_rows": [
                    {
                        "raw_id": "reserve-buffer",
                        "signature_complete": True,
                        "terminal_signature": {"action": "REDUCE"},
                    },
                    {
                        "raw_id": "liquidity-cushion",
                        "signature_complete": True,
                        "terminal_signature": {"action": "REDUCE"},
                    },
                ],
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["strongest_proved_relation"],
            "CURRENT_DECISION_SUBSTITUTION",
        )
        self.assertFalse(out["result"]["proved_facts"]["semantic_identity"])


    def test_auto_semantic_relation_task_equivalence_without_global_synonymy(self):
        out = run({
            "payload": {
                "expression_a": "reserve buffer",
                "expression_b": "liquidity cushion",
                "required_relation": "TASK_EQUIVALENCE",
                "evidence": {},
                "task_terminal_rows": [
                    {
                        "raw_id": "A",
                        "signature_complete": True,
                        "terminal_signature": {"action": "REDUCE", "threshold": 10},
                    },
                    {
                        "raw_id": "B",
                        "signature_complete": True,
                        "terminal_signature": {"action": "REDUCE", "threshold": 10},
                    },
                ],
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["strongest_proved_relation"],
            "TASK_EQUIVALENT",
        )

    def test_auto_semantic_relation_similarity_never_becomes_equivalence(self):
        out = run({
            "payload": {
                "expression_a": "reserve buffer",
                "expression_b": "liquidity cushion",
                "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
                "evidence": {"embedding_similarity": 0.999},
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertFalse(out["inner_pass"])
        self.assertEqual(
            out["result"]["reason"],
            "UNSAFE_SIMILARITY_EVIDENCE_CANNOT_GRANT_SEMANTIC_RELATION",
        )


    def test_auto_semantic_relation_uses_task_equivalence_without_global_synonymy(self):
        out = run({
            "payload": {
                "expression_a": "reserve buffer",
                "expression_b": "liquidity cushion",
                "required_relation": "TASK_EQUIVALENCE",
                "scope_sha256": "1" * 64,
                "evidence": {},
                "task_terminal_rows": [
                    {
                        "raw_id": "A",
                        "signature_complete": True,
                        "terminal_signature": {"action": "REDUCE"},
                    },
                    {
                        "raw_id": "B",
                        "signature_complete": True,
                        "terminal_signature": {"action": "REDUCE"},
                    },
                ],
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["strongest_proved_relation"],
            "TASK_EQUIVALENT",
        )

    def test_auto_semantic_relation_similarity_never_becomes_authority(self):
        out = run({
            "payload": {
                "expression_a": "reserve buffer",
                "expression_b": "liquidity cushion",
                "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
                "scope_sha256": "1" * 64,
                "evidence": {"embedding_similarity": 0.999},
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertFalse(out["inner_pass"])
        self.assertEqual(
            out["result"]["reason"],
            "UNSAFE_SIMILARITY_EVIDENCE_CANNOT_GRANT_SEMANTIC_RELATION",
        )


    def test_auto_semantic_relation_routes_and_preserves_direction(self):
        scope = "1" * 64
        out = run({
            "payload": {
                "expression_a": "CET1 capital",
                "expression_b": "regulatory capital",
                "required_relation": "A_ENTAILS_B_REQUIRED",
                "scope_sha256": scope,
                "evidence": {
                    "entailment_a_to_b": {
                        "verified": True,
                        "relation": "A_ENTAILS_B",
                        "source_kind": "CHECKED_PROOF_DAG",
                        "verifier_id": "verifier:test",
                        "evidence_sha256": "e" * 64,
                        "scope_sha256": scope,
                    }
                },
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["strongest_proved_relation"],
            "A_ENTAILS_B",
        )

    def test_auto_semantic_relation_rejects_similarity_as_authority(self):
        scope = "1" * 64
        out = run({
            "payload": {
                "expression_a": "reserve buffer",
                "expression_b": "liquidity cushion",
                "required_relation": "ANY_SOUND_RELATION",
                "scope_sha256": scope,
                "evidence": {"embedding_similarity": 0.99},
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertFalse(out["inner_pass"])
        self.assertEqual(
            out["result"]["reason"],
            "UNSAFE_SIMILARITY_EVIDENCE_CANNOT_GRANT_SEMANTIC_RELATION",
        )


    def test_auto_semantic_relation_exact_equivalence(self):
        scope = "1" * 64
        receipt = {
            "verified": True,
            "relation": "EXACT_EQUIVALENT",
            "source_kind": "EXPLICIT_SOURCE_DEFINITION",
            "verifier_id": "verifier:test",
            "evidence_sha256": "e" * 64,
            "scope_sha256": scope,
        }
        out = run({
            "payload": {
                "expression_a": "reserve buffer",
                "expression_b": "liquidity cushion",
                "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
                "scope_sha256": scope,
                "evidence": {"explicit_source_equivalence": receipt},
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["strongest_proved_relation"],
            "EXACT_EQUIVALENT",
        )

    def test_auto_semantic_relation_preserves_one_way_entailment(self):
        scope = "2" * 64
        receipt = {
            "verified": True,
            "relation": "A_ENTAILS_B",
            "source_kind": "CHECKED_PROOF_DAG",
            "verifier_id": "verifier:test",
            "evidence_sha256": "f" * 64,
            "scope_sha256": scope,
        }
        out = run({
            "payload": {
                "expression_a": "CET1 capital",
                "expression_b": "regulatory capital",
                "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
                "scope_sha256": scope,
                "evidence": {"entailment_a_to_b": receipt},
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertFalse(out["inner_pass"])
        self.assertEqual(
            out["result"]["strongest_proved_relation"],
            "A_ENTAILS_B",
        )

    def test_auto_semantic_relation_allows_task_equivalence_without_global_synonymy(self):
        scope = "3" * 64
        completeness = {
            "verified": True,
            "relation": "TASK_TERMINAL_SIGNATURES_COMPLETE",
            "source_kind": "CHECKED_PROOF_DAG",
            "verifier_id": "verifier:test",
            "evidence_sha256": "a" * 64,
            "scope_sha256": scope,
        }
        out = run({
            "payload": {
                "expression_a": "reserve buffer",
                "expression_b": "liquidity cushion",
                "required_relation": "TASK_EQUIVALENCE",
                "scope_sha256": scope,
                "evidence": {},
                "task_terminal_signature_completeness_receipt": completeness,
                "task_terminal_rows": [
                    {
                        "raw_id": "A",
                        "signature_complete": True,
                        "terminal_signature": {"action": "REDUCE"},
                    },
                    {
                        "raw_id": "B",
                        "signature_complete": True,
                        "terminal_signature": {"action": "REDUCE"},
                    },
                ],
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["strongest_proved_relation"],
            "TASK_EQUIVALENT",
        )
        self.assertTrue(out["result"]["task_equivalent"])


    def test_auto_semantic_relation_accepts_scoped_exact_equivalence_receipt(self):
        scope = "1" * 64
        out = run({
            "payload": {
                "expression_a": "reserve buffer",
                "expression_b": "liquidity cushion",
                "required_relation": "BIDIRECTIONAL_EQUIVALENCE",
                "scope_sha256": scope,
                "evidence": {
                    "explicit_source_equivalence": {
                        "verified": True,
                        "relation": "EXACT_EQUIVALENT",
                        "source_kind": "EXPLICIT_SOURCE_DEFINITION",
                        "verifier_id": "verifier:test",
                        "evidence_sha256": "e" * 64,
                        "scope_sha256": scope,
                    }
                },
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["strongest_proved_relation"],
            "EXACT_EQUIVALENT",
        )

    def test_auto_semantic_relation_rejects_similarity_as_authority(self):
        scope = "1" * 64
        out = run({
            "payload": {
                "expression_a": "reserve buffer",
                "expression_b": "liquidity cushion",
                "required_relation": "ANY_SOUND_RELATION",
                "scope_sha256": scope,
                "evidence": {"embedding_similarity": 0.99},
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertFalse(out["inner_pass"])
        self.assertEqual(
            out["result"]["reason"],
            "UNSAFE_SIMILARITY_EVIDENCE_CANNOT_GRANT_SEMANTIC_RELATION",
        )

    def test_capability_scheduler_is_inside_fabric(self):
        out = run({
            "payload": {
                "work": [{
                    "work_id": "BUILD",
                    "work_type": "CAPABILITY_BUILD",
                    "expected_capability_gain_lcb": 1,
                    "expected_efficiency_gain_lcb": 0,
                    "expected_reliability_gain_lcb": 1,
                    "reuse_breadth_lcb": 1,
                    "generalization_lcb": 1,
                    "success_probability_lcb": "1",
                    "wall_clock_cost_ub": 1,
                    "compute_cost_ub": 1,
                    "memory_cost_ub": 1,
                    "complexity_cost_ub": 1,
                }],
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "CAPABILITY_SCHEDULER")
        self.assertTrue(out["inner_pass"])
        self.assertEqual(out["result"]["ranked"][0]["work_id"], "BUILD")

    def test_canonical_front_door_opportunistically_advances_verifier_backed_learning(self):
        verifier = Mock()
        tick = {
            "schema": r3.SCHEMA,
            "status": "VERIFICATION_QUEUE_ADVANCED",
            "pass": True,
            "attempted": 1,
            "completed": 1,
        }
        request = {
            "mode": "CAPABILITY_SCHEDULER",
            "payload": {
                "work": [{
                    "work_id": "R3-TICK",
                    "work_type": "CAPABILITY_BUILD",
                    "expected_capability_gain_lcb": 1,
                    "expected_efficiency_gain_lcb": 0,
                    "expected_reliability_gain_lcb": 1,
                    "reuse_breadth_lcb": 1,
                    "generalization_lcb": 1,
                    "success_probability_lcb": 1,
                    "wall_clock_cost_ub": 1,
                    "compute_cost_ub": 1,
                    "memory_cost_ub": 1,
                    "complexity_cost_ub": 1,
                }],
            },
            "options": {"self_improvement_max_actions": 2},
        }
        with patch(
            "canonical.runtime.unified_cognitive_fabric_v1.improvement_driver.drain",
            return_value=tick,
        ) as advance:
            out = run(
                request,
                skill_verification_provider=verifier,
            )

        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertEqual(out["compounding_tick"], tick)
        self.assertEqual(
            out["episode_compounding_tick"]["status"],
            "MERGED_INTO_UNIFIED_COMPOUNDING_TICK",
        )
        advance.assert_called_once()
        kwargs = advance.call_args.kwargs
        self.assertIs(kwargs["skill_verification_provider"], verifier)
        self.assertIsNone(kwargs["failure_repair_provider"])
        self.assertEqual(kwargs["max_actions"], 2)


    def test_canonical_front_door_advances_queue_even_without_attached_verifiers(self):
        tick = {
            "schema": "PROJECT_BRAIN_R3_IMPROVEMENT_QUEUE_DRIVER_V1",
            "status": "IMPROVEMENT_QUEUE_STABLE",
            "pass": True,
            "progress_count": 0,
            "actions": [],
            "terminal_authority": False,
        }
        request = {
            "mode": "CAPABILITY_SCHEDULER",
            "payload": {
                "work": [{
                    "work_id": "R3-ALWAYS-TICK",
                    "work_type": "CAPABILITY_BUILD",
                    "expected_capability_gain_lcb": 1,
                    "expected_efficiency_gain_lcb": 0,
                    "expected_reliability_gain_lcb": 1,
                    "reuse_breadth_lcb": 1,
                    "generalization_lcb": 1,
                    "success_probability_lcb": 1,
                    "wall_clock_cost_ub": 1,
                    "compute_cost_ub": 1,
                    "memory_cost_ub": 1,
                    "complexity_cost_ub": 1,
                }],
            },
            "options": {"self_improvement_max_actions": 2},
        }
        with patch(
            "canonical.runtime.unified_cognitive_fabric_v1.improvement_driver.drain",
            return_value=tick,
        ) as drain:
            out = run(request)

        self.assertEqual(out["compounding_tick"], tick)
        drain.assert_called_once()
        kwargs = drain.call_args.kwargs
        self.assertIsNone(kwargs["episode_verification_provider"])
        self.assertIsNone(kwargs["skill_verification_provider"])
        self.assertIsNone(kwargs["success_episode_adapter_provider"])
        self.assertIsNone(kwargs["failure_repair_provider"])
        self.assertEqual(kwargs["max_actions"], 2)

    def test_background_compounding_forwards_available_repair_authority(self):
        tick = {
            "schema": "PROJECT_BRAIN_R3_IMPROVEMENT_QUEUE_DRIVER_V1",
            "status": "IMPROVEMENT_QUEUE_STABLE",
            "pass": True,
            "progress_count": 0,
            "actions": [],
            "terminal_authority": False,
        }
        component = {"id": "repairer"}
        expander = Mock()
        with (
            patch(
                "canonical.runtime.unified_cognitive_fabric_v1.improvement_driver.drain",
                return_value=tick,
            ) as drain,
            patch(
                "canonical.runtime.unified_cognitive_fabric_v1.live_runtime.execute_failure_repair_cycle",
                return_value={"pass": False, "status": "BLOCKED"},
            ) as repair_cycle,
        ):
            out = run(
                {
                    "mode": "CAPABILITY_SCHEDULER",
                    "payload": {
                        "work": [{
                            "work_id": "R3-REPAIR-AUTHORITY",
                            "work_type": "CAPABILITY_BUILD",
                            "expected_capability_gain_lcb": 1,
                            "expected_efficiency_gain_lcb": 0,
                            "expected_reliability_gain_lcb": 1,
                            "reuse_breadth_lcb": 1,
                            "generalization_lcb": 1,
                            "success_probability_lcb": 1,
                            "wall_clock_cost_ub": 1,
                            "compute_cost_ub": 1,
                            "memory_cost_ub": 1,
                            "complexity_cost_ub": 1,
                        }],
                    },
                    "options": {
                        "repair_components": [component],
                        "self_improvement_max_actions": 2,
                    },
                },
                capability_expander=expander,
            )

            provider = drain.call_args.kwargs["failure_repair_provider"]
            self.assertIsNotNone(provider)
            provider({
                "payload": {
                    "failure_fingerprint": "fp:pending",
                    "retry_capsule_sha256": "retry:pending",
                }
            })

        self.assertEqual(out["compounding_tick"], tick)
        request = repair_cycle.call_args.args[0]
        self.assertEqual(request["failure_fingerprint"], "fp:pending")
        self.assertEqual(request["retry_capsule_sha256"], "retry:pending")
        self.assertEqual(request["components"], [component])
        self.assertTrue(request["autonomous"])
        self.assertIs(
            repair_cycle.call_args.kwargs["capability_expander"],
            expander,
        )

    def test_auto_universal_escape_route_is_structurally_selected(self):
        out = run({
            "payload": {
                "escape_cell_id": "cell-x",
                "escape_membership_bound": False,
                "admission_candidates": {},
                "v9_args": {},
            },
        })
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "UNIVERSAL_ESCAPE")
        self.assertFalse(out["inner_pass"])

    def test_terminal_root_dispatches_fail_closed_without_receipt(self):
        out = run({
            "mode": "TERMINAL_ROOT",
            "payload": {},
        })
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertFalse(out["inner_pass"])
        self.assertEqual(out["result"]["status"], "FAIL_CLOSED")

    def test_certified_route_preflight_is_available_through_fabric(self):
        out = run({
            "mode": "CERTIFIED_ROUTE",
            "payload": {"operation": "PREFLIGHT"},
        })
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertIn("result", out)

    def test_ownership_catalog_dispatches_and_structurally_closes_r1(self):
        out = run({
            "mode": "OWNERSHIP_CATALOG",
            "payload": {},
        })
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertTrue(out["inner_pass"], out)
        self.assertTrue(out["result"]["live_owned_equals_fabric_reachable"])
        self.assertTrue(out["result"]["r1_structural_closure"])

    def test_decision_dispatches(self):
        out = run({
            "mode": "ADEQUATE_DECISION",
            "payload": {
                "task_id": "FABRIC-DECISION-OPEN-001",
                "goal": "Choose the adequate action.",
            },
        })
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertFalse(out["inner_pass"])
        self.assertEqual(out["result"]["status"], "OPEN__DECISION_CONTEXT_REQUIRED")

    @patch("canonical.runtime.unified_cognitive_fabric_v1.live_runtime.run")
    def test_adaptive_solver_delegates_through_r3_reuse_repair_runtime(self, runtime_run):
        runtime_run.return_value = {
            "pass": True,
            "status": "UNIFIED_GENERIC_EXECUTION_COMPLETE",
            "solver_output": {"pass": True, "status": "SOLVED__VERIFIED_EPISODE"},
            "learning": {"status": "VERIFIED_EPISODE_PERSISTED"},
            "reuse_first": True,
            "reused_skill_id": "skill:test",
        }
        out = run({
            "mode": "ADAPTIVE_SOLVER",
            "payload": {"task_id":"FABRIC-R1-DELEGATE","initial_facts":[],"target_effects":["DONE"],"capabilities":[]},
        })
        self.assertTrue(out["inner_pass"], out)
        self.assertTrue(out["result"]["_live_runtime"]["reuse_first"])
        self.assertEqual(runtime_run.call_args.args[0]["mode"], "generic")

    def test_r3_uses_current_solver_v12(self):
        self.assertIs(r3.solver_v12, solver_v12)

    @patch("canonical.runtime.unified_cognitive_fabric_v1.self_improvement.run_learning_episode")
    def test_auto_solver_with_independent_verifier_provider_routes_through_r3(
        self, learning_run
    ):
        learning_run.return_value = {
            "pass": True,
            "status": "VERIFIED_SKILL_PERMANENTLY_ADMITTED_FOR_REUSE",
        }
        episode_verifier = Mock()
        skill_verifier = Mock()
        out = run(
            {
                "mode": "AUTO",
                "payload": {
                    "task_id": "FABRIC-R3-AUTO-001",
                    "initial_facts": [],
                    "target_effects": ["DONE"],
                    "capabilities": [],
                },
                "options": {
                    "episode_id": "ep",
                    "scope_id": "scope",
                },
            },
            episode_verification_provider=episode_verifier,
            skill_verification_provider=skill_verifier,
        )
        self.assertEqual(out["mode"], "LEARNING_EPISODE")
        self.assertTrue(out["auto_routed"])
        kwargs = learning_run.call_args.kwargs
        self.assertIs(kwargs["episode_verification_provider"], episode_verifier)
        self.assertIs(kwargs["skill_verification_provider"], skill_verifier)

    def test_learning_episode_persists_failure_diagnosis(self):
        with tempfile.TemporaryDirectory() as td:
            state = Path(td) / "state.json"
            out = run({
                "mode": "LEARNING_EPISODE",
                "payload": {
                    "task_id": "FABRIC-LEARN-FAIL-001",
                    "initial_facts": [],
                    "target_effects": ["unreachable.effect"],
                    "capabilities": [],
                },
                "options": {
                    "state_path": str(state),
                    "episode_id": "fabric-episode-1",
                    "scope_id": "fabric-scope",
                    "max_capability_expansions": 0,
                },
            })
            self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
            self.assertFalse(out["inner_pass"])
            self.assertTrue(state.is_file())
            doc = json.loads(state.read_text(encoding="utf-8"))
            self.assertGreaterEqual(doc["stats"]["failure_class_count"], 1)

    def test_h100_snapshot_dispatches_through_fabric(self):
        out = run({
            "mode": "H100_INFERENCE",
            "payload": {"operation": "SNAPSHOT"},
        })
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertTrue(out["inner_pass"], out)
        self.assertGreaterEqual(out["result"]["entry_count"], 21)

    def test_mystery_exact_polytope_dispatches_through_fabric(self):
        out = run({
            "mode": "MYSTERY_INFERENCE",
            "payload": {
                "operation": "EXACT_LINEAR_POLYTOPE",
                "problem": {
                    "feature_semantics_bound": True,
                    "observation_intervals_sound": True,
                    "observations": [
                        {"features": ["1"], "output_interval": ["1", "1"]},
                    ],
                    "queries": [
                        {"query_id": "q", "features": ["2"]},
                    ],
                },
            },
        })
        self.assertEqual(out["status"], "FABRIC_DISPATCH_COMPLETE")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(out["result"]["query_predictions"][0]["prediction_interval"], ["2", "2"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
