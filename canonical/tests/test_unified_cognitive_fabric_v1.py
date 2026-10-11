from __future__ import annotations

import hashlib
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
        self.assertIn("OEWN_DECISION_SENSE", c["engines"])
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
        signature = {"action": "REDUCE"}
        signature_sha = hashlib.sha256(
            json.dumps(
                signature,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        receipt = {
            "pass": True,
            "schema": "PROJECT_BRAIN_TERMINAL_SIGNATURE_COMPLETENESS_AUTHORITY_RECEIPT_V1",
            "scope_id": "finance:policy:2026",
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "left_terminal_signature_complete": True,
            "right_terminal_signature_complete": True,
            "left_terminal_signature_sha256": signature_sha,
            "right_terminal_signature_sha256": signature_sha,
            "verification_authority_mutated": False,
            "receipt_sha256": "f" * 64,
        }
        verifier = Mock(side_effect=lambda value: value)
        out = run(
            {
                "payload": {
                    "left_id": "reserve-buffer",
                    "right_id": "liquidity-cushion",
                    "scope_id": "finance:policy:2026",
                    "required_relation": "CURRENT_DECISION_SUBSTITUTION",
                    "terminal_signature_rows": [
                        {
                            "raw_id": "reserve-buffer",
                            "signature_complete": True,
                            "terminal_signature": signature,
                        },
                        {
                            "raw_id": "liquidity-cushion",
                            "signature_complete": True,
                            "terminal_signature": signature,
                        },
                    ],
                    "terminal_signature_authority_receipt": receipt,
                },
            },
            semantic_authority_verifier=verifier,
        )
        self.assertTrue(out["auto_routed"])
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["strongest_proved_relation"],
            "CURRENT_DECISION_SUBSTITUTION",
        )
        self.assertFalse(out["result"]["proved_facts"]["semantic_identity"])
        verifier.assert_called_once()

    def test_auto_semantic_relation_forwards_semantic_authority_verifier(self):
        receipt = {
            "pass": True,
            "schema": "PROJECT_BRAIN_SHARED_CONCEPT_IDENTITY_AUTHORITY_RECEIPT_V1",
            "scope_id": "finance:policy:2026",
            "left_id": "reserve-buffer",
            "right_id": "liquidity-cushion",
            "shared_concept_id": "REGCAP:42",
            "left_binding_authenticated": True,
            "right_binding_authenticated": True,
            "concept_semantics_authenticated": True,
            "left_binding_sha256": "a" * 64,
            "right_binding_sha256": "b" * 64,
            "registry_sha256": "c" * 64,
            "verification_authority_mutated": False,
            "receipt_sha256": "d" * 64,
        }
        verifier = Mock(side_effect=lambda value: value)
        out = run(
            {
                "payload": {
                    "left_id": "reserve-buffer",
                    "right_id": "liquidity-cushion",
                    "scope_id": "finance:policy:2026",
                    "required_relation": "SEMANTIC_IDENTITY",
                    "shared_concept_identity_receipt": receipt,
                },
            },
            semantic_authority_verifier=verifier,
        )
        self.assertTrue(out["auto_routed"], out)
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["strongest_proved_relation"],
            "SEMANTIC_IDENTITY",
        )
        verifier.assert_called_once()

    @patch("canonical.runtime.unified_cognitive_fabric_v1.oewn_decision_sense.resolve")
    def test_auto_oewn_decision_sense_routes_through_authenticated_control(self, resolver):
        resolver.return_value = {
            "schema": "PROJECT_BRAIN_OEWN_DECISION_SENSE_CONTROL_V1",
            "status": "PASS__OEWN_SENSE_AMBIGUITY_DECISION_SUFFICIENT",
            "pass": True,
        }
        authority_verifier = Mock()
        evidence_verifier = Mock()
        out = run(
            {
                "payload": {
                    "sense_universe": {"schema": "synthetic"},
                    "decision_manifest": {"schema": "synthetic"},
                    "authority_receipt": {"receipt": "authority"},
                    "evidence_receipts": [{"receipt": "evidence"}],
                    "ambiguity_owner": "SYSTEM_MODEL",
                }
            },
            semantic_authority_verifier=authority_verifier,
            semantic_evidence_verifier=evidence_verifier,
        )
        self.assertTrue(out["auto_routed"], out)
        self.assertEqual(out["mode"], "OEWN_DECISION_SENSE")
        self.assertTrue(out["inner_pass"], out)
        kwargs = resolver.call_args.kwargs
        self.assertIs(kwargs["authority_verifier"], authority_verifier)
        self.assertIs(kwargs["evidence_verifier"], evidence_verifier)
        self.assertEqual(kwargs["ambiguity_owner"], "SYSTEM_MODEL")
        self.assertEqual(kwargs["authority_receipt"], {"receipt": "authority"})
        self.assertEqual(kwargs["evidence_receipts"], [{"receipt": "evidence"}])

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

    def test_opaque_cognition_providers_are_forbidden_in_live_fabric(self):
        request = {
            "mode": "CAPABILITY_SCHEDULER",
            "payload": {
                "work": [{
                    "work_id": "NO-OPAQUE-COGNITION",
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
        }
        cases = {
            "proposal_provider": {"proposal_provider": Mock()},
            "capability_expander": {"capability_expander": Mock()},
            "success_episode_adapter_provider": {"success_episode_adapter_provider": Mock()},
            "one_shot_failure_repair_provider": {"one_shot_failure_repair_provider": Mock()},
            "one_shot_capability_synthesis_provider": {"one_shot_capability_synthesis_provider": Mock()},
        }
        for name, kwargs in cases.items():
            with self.subTest(provider=name):
                out = run(request, **kwargs)
                self.assertFalse(out["pass"], out)
                self.assertIn(
                    "OPAQUE_COGNITION_PROVIDER_FORBIDDEN_IN_LIVE_FABRIC:" + name,
                    out["reason"],
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
