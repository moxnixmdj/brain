from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import live_brain_runtime_v1 as brain


class UnifiedLiveBrainV1Tests(unittest.TestCase):
    def problem(self):
        return {
            "task_id": "t1",
            "initial_facts": [],
            "target_effects": ["DONE"],
            "capabilities": [],
        }

    @patch("canonical.runtime.live_brain_runtime_v1._active_learning_context")
    @patch("canonical.runtime.live_brain_runtime_v1._integrate_learning")
    @patch("canonical.runtime.live_brain_runtime_v1._v12_run")
    def test_generic_path_reuses_verified_experience_and_integrates_new_experience(
        self, solver, integrate, context
    ):
        context.return_value = {
            "state_path": "/tmp/state.json",
            "state": {},
            "prior_verified_episodes": [{"episode_id": "old"}],
            "active_verified_skills": [],
        }
        solver.return_value = {"pass": True, "status": "SOLVED__VERIFIED_EPISODE"}
        integrate.return_value = {"status": "VERIFIED_EPISODE_PERSISTED__MORE_EVIDENCE_NEEDED_FOR_SKILL"}

        out = brain.run({
            "mode": "generic",
            "problem": self.problem(),
            "episode_id": "new",
            "scope_id": "scope",
        })

        self.assertTrue(out["pass"], out)
        self.assertEqual(out["verified_prior_episode_count_reused"], 1)
        kwargs = solver.call_args.kwargs["kwargs"]
        self.assertEqual(kwargs["prior_verified_episode_records"], [{"episode_id": "old"}])
        self.assertEqual(kwargs["episode_id"], "new")
        integrate.assert_called_once_with(solver.return_value, state_path="/tmp/state.json")

    @patch("canonical.runtime.live_brain_runtime_v1._decision_run")
    @patch("canonical.runtime.live_brain_runtime_v1._integrate_learning")
    def test_raw_goal_defaults_to_r2_and_feeds_verified_execution_to_r3(self, integrate, decision):
        execution = {"pass": True, "status": "SOLVED__VERIFIED_EPISODE"}
        decision.return_value = {
            "pass": True,
            "status": "PASS__GOAL_BOUND_ADEQUATE_POLICY_EXECUTED_AND_ACCEPTANCE_VERIFIED",
            "execution_result": execution,
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
        }
        integrate.return_value = {"status": "VERIFIED_EPISODE_PERSISTED__MORE_EVIDENCE_NEEDED_FOR_SKILL"}

        out = brain.run({"task_id": "d1", "goal": "do the exact thing"})
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        decision.assert_called_once()
        integrate.assert_called_once_with(execution, state_path=None)

    @patch("canonical.runtime.live_brain_runtime_v1._bound_run")
    def test_compiled_bound_route_is_behind_same_front_door(self, bound):
        bound.return_value = {"pass": True, "status": "PASS__REAL_TASK_PLANNED_EXECUTED_AND_REVERIFIED"}
        out = brain.run({
            "mode": "compiled_bound",
            "task_id": "b1",
            "initial_facts": [],
            "target_effects": ["X"],
        })
        self.assertTrue(out["pass"], out)
        bound.assert_called_once()

    @patch("canonical.runtime.live_brain_runtime_v1._p3")
    def test_p3_is_reachable_through_same_front_door(self, p3):
        p3.return_value = {"pass": True, "status": "PASS"}
        out = brain.run({
            "mode": "specialized",
            "surface": "P3_REAL_CONTEXT_V12",
            "payload": {"x": 1},
        })
        self.assertTrue(out["pass"], out)
        p3.assert_called_once()

    @patch("canonical.runtime.live_brain_runtime_v1._rank_work")
    def test_capability_first_scheduler_is_integrated_without_fake_execution_authority(self, rank):
        rank.return_value = {"status": "CAPABILITY_FIRST_RANKING", "planning_only": True}
        out = brain.run({"mode": "development_schedule", "work": [{"work_id": "w"}]})
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["scheduler_role"], "DEVELOPMENT_PRIORITY_NOT_TASK_SUCCESS_AUTHORITY")
        self.assertFalse(out["execution_authority"])

    @patch("canonical.runtime.live_brain_runtime_v1._active_learning_context")
    @patch("canonical.runtime.live_brain_runtime_v1._skill_plan")
    def test_verified_skills_are_loaded_for_reuse_planning(self, plan, context):
        context.return_value = {
            "state_path": "/tmp/state.json",
            "state": {},
            "prior_verified_episodes": [],
            "active_verified_skills": [{"candidate_sha256": "sha256:x"}],
        }
        plan.return_value = {"pass": True, "status": "PASS__SKILL_AWARE_PLAN_COMPILED"}
        out = brain.run({"mode": "skill_plan", "problem": self.problem()})
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["active_verified_skill_count"], 1)
        plan.assert_called_once()

    @patch("canonical.runtime.live_brain_runtime_v1._learning_module")
    def test_inventory_names_single_entrypoint_and_major_surfaces(self, learning_module):
        class L:
            DEFAULT_STATE_PATH = "/tmp/brain-state-does-not-exist.json"
            @staticmethod
            def load_state(path):
                return {"stats": {}}
        learning_module.return_value = L
        out = brain.inventory()
        self.assertEqual(out["status"], "UNIFIED_LIVE_BRAIN_READY")
        self.assertEqual(out["public_entrypoint"], "canonical.runtime.live_brain_runtime_v1.run")
        self.assertIn("GENERAL_ADEQUATE_DECISION_CONTROLLER_V1", out["surfaces"])
        self.assertIn("UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V12", out["surfaces"])
        self.assertIn("AUTONOMOUS_VERIFIED_SELF_IMPROVEMENT_V1", out["surfaces"])


    @patch("canonical.runtime.live_brain_runtime_v1._integrate_learning")
    @patch("canonical.runtime.live_brain_runtime_v1._bound_run")
    def test_compiled_bound_failure_is_durably_diagnosed(self, bound, integrate):
        failure = {
            "pass": False,
            "status": "FAIL__CAPABILITY_OR_TASK_CONTRACT_GAP",
            "failure_class": "MISSING_CAPABILITY_OR_COMPILED_TASK_CONTRACT",
        }
        bound.return_value = failure
        integrate.return_value = {
            "status": "FAILURE_DIAGNOSED__REPAIR_NOT_SELF_CERTIFIED",
            "pass": False,
        }
        out = brain.run({
            "mode": "compiled_bound",
            "task_id": "b-fail",
            "initial_facts": [],
            "target_effects": ["X"],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["learning"]["status"],
            "FAILURE_DIAGNOSED__REPAIR_NOT_SELF_CERTIFIED",
        )
        integrate.assert_called_once_with(failure, state_path=None)

    @patch("canonical.runtime.live_brain_runtime_v1._integrate_learning")
    @patch("canonical.runtime.live_brain_runtime_v1._raw_bound_run")
    def test_raw_bound_failure_is_durably_diagnosed(self, raw_bound, integrate):
        failure = {
            "pass": False,
            "status": "FAIL__RAW_GOAL_COMPILATION_GAP",
            "failure_class": "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP",
        }
        raw_bound.return_value = failure
        integrate.return_value = {
            "status": "FAILURE_DIAGNOSED__REPAIR_NOT_SELF_CERTIFIED",
            "pass": False,
        }
        out = brain.run({
            "mode": "raw_bound",
            "request": {"task_id": "r-fail", "goal": "unknown"},
        })
        self.assertFalse(out["pass"])
        integrate.assert_called_once_with(failure, state_path=None)

    @patch("canonical.runtime.live_brain_runtime_v1._integrate_learning")
    @patch("canonical.runtime.live_brain_runtime_v1._p3")
    def test_specialized_failure_is_durably_diagnosed(self, p3, integrate):
        p3.return_value = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED",
        }
        integrate.return_value = {
            "status": "FAILURE_DIAGNOSED__REPAIR_NOT_SELF_CERTIFIED",
            "pass": False,
        }
        out = brain.run({
            "mode": "specialized",
            "surface": "P3_REAL_CONTEXT_V12",
            "payload": {"x": 1},
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["learning"]["status"],
            "FAILURE_DIAGNOSED__REPAIR_NOT_SELF_CERTIFIED",
        )
        observed = integrate.call_args.args[0]
        self.assertFalse(observed["pass"])
        self.assertEqual(
            observed["reason"],
            "SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED",
        )

    @patch("canonical.runtime.live_brain_runtime_v1._integrate_learning")
    @patch("canonical.runtime.live_brain_runtime_v1._bound_run")
    def test_plain_success_without_verified_episode_is_not_promoted(self, bound, integrate):
        bound.return_value = {
            "pass": True,
            "status": "PASS__REAL_TASK_PLANNED_EXECUTED_AND_REVERIFIED",
        }
        out = brain.run({
            "mode": "compiled_bound",
            "task_id": "b-ok",
            "initial_facts": [],
            "target_effects": ["X"],
        })
        self.assertTrue(out["pass"])
        self.assertEqual(
            out["learning"]["status"],
            "SUCCESS_OBSERVED__NO_VERIFIED_LEARNING_ARTIFACT",
        )
        self.assertFalse(out["learning"]["permanent_reuse_authorized"])
        integrate.assert_not_called()


    @patch("canonical.runtime.live_brain_runtime_v1._causal_synthesize")
    @patch("canonical.runtime.live_brain_runtime_v1._learning_module")
    def test_failure_fingerprint_compiles_to_minimum_causal_repair_search(self, learning_module, synthesize):
        class L:
            DEFAULT_STATE_PATH = "/tmp/repair-state.json"
            @staticmethod
            def load_state(path):
                return {
                    "failures": {
                        "fp:verify": {
                            "repair_class": "OBTAIN_OR_REPAIR_INDEPENDENT_VERIFICATION",
                            "count": 3,
                        }
                    }
                }
        learning_module.return_value = L
        synthesize.return_value = {
            "pass": True,
            "classification": "ARCHITECTURE_FOUND",
            "winner": {"components": ["independent-verifier"]},
        }
        components = [{
            "id": "independent-verifier",
            "kind": "VERIFIER",
            "requires": [],
            "provides": ["repair.independent_verification.available"],
            "verified": True,
            "brain_owned": True,
            "donor_independent": True,
            "cost": {"wall_clock": 1, "incremental_spend_usd": 0},
        }]
        out = brain.run({
            "mode": "repair_synthesis",
            "failure_fingerprint": "fp:verify",
            "components": components,
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["required_repair_effect"],
            "repair.independent_verification.available",
        )
        self.assertTrue(out["candidate_only"])
        manifest = synthesize.call_args.args[0]
        self.assertEqual(
            manifest["target"]["required_effects"],
            ["repair.independent_verification.available"],
        )
        self.assertEqual(manifest["components"], components)

    @patch("canonical.runtime.live_brain_runtime_v1._causal_synthesize")
    @patch("canonical.runtime.live_brain_runtime_v1._learning_module")
    def test_missing_repair_provider_emits_new_primitive_required(self, learning_module, synthesize):
        class L:
            DEFAULT_STATE_PATH = "/tmp/repair-state.json"
            @staticmethod
            def load_state(path):
                return {
                    "failures": {
                        "fp:cap": {
                            "repair_class": "ACQUIRE_COMPOSE_OR_INVENT_VERIFIABLE_CAPABILITY",
                            "count": 1,
                        }
                    }
                }
        learning_module.return_value = L
        synthesize.return_value = {
            "pass": False,
            "classification": "NEW_PRIMITIVE_REQUIRED",
            "missing_required_effects": ["repair.capability.available"],
        }
        out = brain.run({
            "mode": "repair_synthesis",
            "failure_fingerprint": "fp:cap",
            "components": [],
        })
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["causal_synthesis"]["classification"],
            "NEW_PRIMITIVE_REQUIRED",
        )
        self.assertEqual(out["required_repair_effect"], "repair.capability.available")
        self.assertFalse(out["execution_authority"])

    @patch("canonical.runtime.live_brain_runtime_v1._learning_module")
    def test_unknown_failure_fingerprint_fails_closed(self, learning_module):
        class L:
            DEFAULT_STATE_PATH = "/tmp/repair-state.json"
            @staticmethod
            def load_state(path):
                return {"failures": {}}
        learning_module.return_value = L
        out = brain.run({
            "mode": "repair_synthesis",
            "failure_fingerprint": "missing",
            "components": [],
        })
        self.assertFalse(out["pass"])
        self.assertIn("FAILURE_FINGERPRINT_UNKNOWN", out["reason"])


    @patch("canonical.runtime.live_brain_runtime_v1._replay_retry_context")
    @patch("canonical.runtime.live_brain_runtime_v1._owned_raw_capability_acquisition")
    @patch("canonical.runtime.live_brain_runtime_v1.synthesize_failure_repair")
    @patch("canonical.runtime.live_brain_runtime_v1._learning_module")
    def test_raw_repair_gap_uses_owned_acquisition_without_host_expander(
        self, learning_module, synthesize, acquire, replay
    ):
        class L:
            DEFAULT_STATE_PATH = "/tmp/owned-acquisition-test-state.json"
            @staticmethod
            def get_failure_retry_context(fid, state_path, retry_capsule_sha256=None):
                return {
                    "failure_fingerprint": fid,
                    "retry_capsule_sha256": "r" * 64,
                    "context": {
                        "mode": "raw_bound",
                        "request": {"task_id": "raw-gap", "goal": "encode this as cbor"},
                        "learn": True,
                    },
                    "resolved": False,
                }
            @staticmethod
            def record_repair_outcome(*args, **kwargs):
                return {
                    "retry_instance_resolved": kwargs.get("original_replay_pass") is True
                }
        learning_module.return_value = L
        synthesize.return_value = {
            "pass": False,
            "status": "REPAIR_ARCHITECTURE_UNRESOLVED",
            "required_repair_effect": "repair.capability.available",
            "causal_synthesis": {
                "pass": False,
                "classification": "NEW_PRIMITIVE_REQUIRED",
                "missing_required_effects": ["repair.capability.available"],
            },
        }
        acquire.return_value = {
            "pass": True,
            "status": "OWNED_RAW_CAPABILITY_ACQUISITION_EXECUTED",
            "mission_id": "LIVE-BRAIN-AUTO-ACQUIRE-ABC",
            "origin_mission_sha256": "a" * 64,
            "auto_acquisition": {
                "status": "VERIFIED_AND_PROMOTED",
                "capability_id": "auto.new",
            },
        }
        replay.return_value = {"pass": True, "status": "PASS__ORIGINAL_OBLIGATION"}

        out = brain.execute_failure_repair_cycle(
            {
                "failure_fingerprint": "fp:raw",
                "retry_capsule_sha256": "r" * 64,
                "components": [],
            },
            capability_expander=None,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "REPAIR_VERIFIED_BY_OWNED_ACQUISITION_AND_ORIGINAL_REPLAY",
        )
        self.assertEqual(out["repair_mode"], "OWNED_RAW_CAPABILITY_ACQUISITION")
        acquire.assert_called_once()
        replay.assert_called_once()

    @patch("canonical.runtime.live_brain_runtime_v1._owned_raw_capability_acquisition")
    @patch("canonical.runtime.live_brain_runtime_v1.synthesize_failure_repair")
    @patch("canonical.runtime.live_brain_runtime_v1._learning_module")
    def test_owned_acquisition_failure_remains_fail_closed(
        self, learning_module, synthesize, acquire
    ):
        class L:
            DEFAULT_STATE_PATH = "/tmp/owned-acquisition-test-state.json"
            @staticmethod
            def get_failure_retry_context(fid, state_path, retry_capsule_sha256=None):
                return {
                    "failure_fingerprint": fid,
                    "retry_capsule_sha256": "r" * 64,
                    "context": {
                        "mode": "raw_bound",
                        "request": {"task_id": "raw-gap", "goal": "unknown capability"},
                        "learn": True,
                    },
                    "resolved": False,
                }
        learning_module.return_value = L
        synthesize.return_value = {
            "pass": False,
            "status": "REPAIR_ARCHITECTURE_UNRESOLVED",
            "required_repair_effect": "repair.capability.available",
            "causal_synthesis": {
                "pass": False,
                "classification": "NEW_PRIMITIVE_REQUIRED",
            },
        }
        acquire.return_value = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "NO_COMPATIBLE_SUPPLIER_CONTRACT",
        }
        out = brain.execute_failure_repair_cycle(
            {
                "failure_fingerprint": "fp:raw",
                "retry_capsule_sha256": "r" * 64,
                "components": [],
            },
            capability_expander=None,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "REPAIR_CYCLE_UNRESOLVED_AT_OWNED_ACQUISITION",
        )
        self.assertTrue(out["owned_raw_acquisition_available"])

    def test_unknown_mode_fails_closed(self):
        out = brain.run({"mode": "invented"})
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
