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
    @patch("canonical.runtime.live_brain_runtime_v1._run_learning_episode")
    def test_generic_path_executes_through_r3_reuse_first(self, learning_run, context):
        context.return_value = {
            "state_path": "/tmp/state.json",
            "state": {},
            "prior_verified_episodes": [{"episode_id": "old"}],
            "active_verified_skills": [],
        }
        learning_run.return_value = {
            "pass": True,
            "status": "VERIFIED_SKILL_PERMANENTLY_ADMITTED_FOR_REUSE",
            "solver_output": {"pass": True, "status": "SOLVED__VERIFIED_EPISODE"},
            "learning": {
                "status": "VERIFIED_SKILL_PERMANENTLY_ADMITTED_FOR_REUSE"
            },
            "prior_verified_episode_count_used": 1,
            "reuse_first": True,
            "reused_skill_id": "skill:abc",
            "reuse_attempt": {"pass": True},
            "fallback_used": False,
        }

        out = brain.run({
            "mode": "generic",
            "problem": self.problem(),
            "episode_id": "new",
            "scope_id": "scope",
            "known_absent_invalidators": ["inv.old"],
        })

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["solver"],
            "R3_REUSE_FIRST_OVER_UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V12",
        )
        self.assertEqual(out["verified_prior_episode_count_reused"], 1)
        self.assertTrue(out["reuse_first"])
        self.assertEqual(out["reused_skill_id"], "skill:abc")
        self.assertFalse(out["fallback_used"])
        self.assertFalse(out["fallback_blocked_effect_may_have_occurred"])
        kwargs = learning_run.call_args.kwargs
        self.assertEqual(kwargs["episode_id"], "new")
        self.assertEqual(kwargs["scope_id"], "scope")
        self.assertEqual(kwargs["known_absent_invalidators"], ["inv.old"])
        self.assertEqual(kwargs["retry_context"]["mode"], "generic")
        self.assertEqual(kwargs["retry_context"]["problem"]["task_id"], "t1")
        self.assertEqual(
            kwargs["retry_context"]["known_absent_invalidators"],
            ["inv.old"],
        )

    @patch("canonical.runtime.live_brain_runtime_v1._active_learning_context")
    @patch("canonical.runtime.live_brain_runtime_v1._v12_run")
    def test_generic_learn_false_preserves_plain_v12_path(self, solver, context):
        context.return_value = {
            "state_path": "/tmp/state.json",
            "state": {},
            "prior_verified_episodes": [{"episode_id": "old"}],
            "active_verified_skills": [],
        }
        solver.return_value = {"pass": True, "status": "SOLVED__VERIFIED_EPISODE"}
        out = brain.run({
            "mode": "generic",
            "problem": self.problem(),
            "episode_id": "plain",
            "scope_id": "scope",
            "learn": False,
        })
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["solver"], "UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V12")
        self.assertFalse(out["learning_persistence_enabled"])
        self.assertFalse(out["reuse_first"])
        kwargs = solver.call_args.kwargs["kwargs"]
        self.assertEqual(
            kwargs["prior_verified_episode_records"],
            [{"episode_id": "old"}],
        )

    @patch("canonical.runtime.live_brain_runtime_v1._decision_run")
    @patch("canonical.runtime.live_brain_runtime_v1._run_learning_episode")
    def test_raw_goal_r2_delegates_execution_to_r3_reuse_first(
        self, learning_run, decision
    ):
        execution = {"pass": True, "status": "SOLVED__VERIFIED_EPISODE"}

        def decision_side_effect(request, **kwargs):
            self.assertEqual(request["scope_id"], "unified-live-brain")
            provider = kwargs["execution_provider"]
            self.assertTrue(callable(provider))
            observed = provider(
                self.problem(),
                repo_root=brain.ROOT,
                episode_id="d1",
                scope_id=request["scope_id"],
                proposal_provider=None,
                capability_expander=None,
            )
            self.assertEqual(observed, execution)
            return {
                "pass": True,
                "status": "PASS__GOAL_BOUND_ADEQUATE_POLICY_EXECUTED_AND_ACCEPTANCE_VERIFIED",
                "execution_result": execution,
                "semantic_acceptance_complete": True,
                "actual_goal_satisfaction_verified": True,
            }

        decision.side_effect = decision_side_effect
        learning_run.return_value = {
            "pass": True,
            "solver_output": execution,
            "learning": {
                "status": "VERIFIED_EPISODE_PERSISTED__MORE_EVIDENCE_NEEDED_FOR_SKILL"
            },
            "reuse_first": True,
            "reused_skill_id": "skill:xyz",
            "reuse_attempt": {"pass": True},
            "fallback_used": False,
        }

        out = brain.run({
            "task_id": "d1",
            "goal": "do the exact thing",
            "known_absent_invalidators": ["inv.old"],
        })
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["reuse_first"])
        self.assertEqual(out["reused_skill_id"], "skill:xyz")
        kwargs = learning_run.call_args.kwargs
        self.assertEqual(kwargs["scope_id"], "unified-live-brain")
        self.assertEqual(kwargs["known_absent_invalidators"], ["inv.old"])
        self.assertEqual(kwargs["retry_context"]["mode"], "decision")
        self.assertEqual(kwargs["retry_context"]["request"]["task_id"], "d1")
        self.assertEqual(
            kwargs["retry_context"]["request"]["scope_id"],
            "unified-live-brain",
        )

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
        self.assertTrue(out["verified_skill_execution_reuse_first"])
        self.assertEqual(out["default_learning_scope"], "unified-live-brain")


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
        integrate.assert_called_once_with(
            failure,
            state_path=None,
            retry_context={
                "mode": "compiled_bound",
                "request": {
                    "mode": "compiled_bound",
                    "task_id": "b-fail",
                    "initial_facts": [],
                    "target_effects": ["X"],
                },
                "learn": True,
            },
        )

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
        integrate.assert_called_once_with(
            failure,
            state_path=None,
            retry_context={
                "mode": "raw_bound",
                "request": {"task_id": "r-fail", "goal": "unknown"},
                "learn": True,
            },
        )

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

    def test_unknown_mode_fails_closed(self):
        out = brain.run({"mode": "invented"})
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")


    @patch("canonical.runtime.live_brain_runtime_v1._automatic_failure_repair")
    @patch("canonical.runtime.live_brain_runtime_v1._active_learning_context")
    @patch("canonical.runtime.live_brain_runtime_v1._run_learning_episode")
    def test_generic_failure_automatically_repairs_then_replays_original(
        self, learning_run, context, automatic_repair
    ):
        context.return_value = {
            "state_path": "/tmp/state.json",
            "state": {},
            "prior_verified_episodes": [],
            "active_verified_skills": [],
        }
        failed_solver = {
            "pass": False,
            "status": "FAIL__CAPABILITY_OR_TASK_CONTRACT_GAP",
        }
        diagnosis = {
            "pass": False,
            "status": "FAILURE_DIAGNOSED__REPAIR_NOT_SELF_CERTIFIED",
            "diagnosis": {"failure_fingerprint": "fp:auto"},
            "retry_capsule_sha256": "retry:auto",
        }
        learning_run.return_value = {
            "pass": False,
            "solver_output": failed_solver,
            "learning": diagnosis,
            "reuse_first": False,
            "fallback_used": False,
        }
        repaired_solver = {"pass": True, "status": "SOLVED__VERIFIED_EPISODE"}
        automatic_repair.return_value = {
            "pass": True,
            "status": "REPAIR_VERIFIED_BY_ORIGINAL_OBLIGATION_REPLAY",
            "original_replay": {
                "pass": True,
                "solver_output": repaired_solver,
            },
        }
        repair_components = [{"id": "verified-repairer"}]

        out = brain.run({
            "mode": "generic",
            "problem": self.problem(),
            "episode_id": "auto",
            "scope_id": "scope",
            "repair_components": repair_components,
        })

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "UNIFIED_GENERIC_EXECUTION_REPAIRED_AND_REPLAYED",
        )
        self.assertEqual(out["solver_output"], repaired_solver)
        self.assertEqual(out["initial_solver_output"], failed_solver)
        self.assertTrue(out["automatic_repair_attempted"])
        auto_kwargs = automatic_repair.call_args.kwargs
        self.assertEqual(auto_kwargs["repair_components"], repair_components)
        learning_kwargs = learning_run.call_args.kwargs
        self.assertFalse(learning_kwargs["retry_context"]["auto_repair"])

    @patch("canonical.runtime.live_brain_runtime_v1._automatic_failure_repair")
    @patch("canonical.runtime.live_brain_runtime_v1._observe_runtime_outcome")
    @patch("canonical.runtime.live_brain_runtime_v1._decision_run")
    def test_decision_failure_automatically_repairs_then_replays_original(
        self, decision, observe, automatic_repair
    ):
        failed = {
            "pass": False,
            "status": "OPEN__SELECTED_ADEQUATE_POLICY_EXECUTION_UNRESOLVED",
            "semantic_acceptance_complete": False,
            "actual_goal_satisfaction_verified": False,
        }
        diagnosis = {
            "pass": False,
            "diagnosis": {"failure_fingerprint": "fp:decision"},
            "retry_capsule_sha256": "retry:decision",
        }
        decision.return_value = failed
        observe.return_value = diagnosis
        repaired_decision = {
            "pass": True,
            "status": "PASS__GOAL_BOUND_ADEQUATE_POLICY_EXECUTED_AND_ACCEPTANCE_VERIFIED",
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
        }
        automatic_repair.return_value = {
            "pass": True,
            "status": "REPAIR_VERIFIED_BY_ORIGINAL_OBLIGATION_REPLAY",
            "original_replay": {
                "pass": True,
                "decision_output": repaired_decision,
            },
        }

        out = brain.run({
            "mode": "decision",
            "request": {"task_id": "d-auto", "goal": "do exact thing"},
            "repair_components": [{"id": "verified-repairer"}],
        })

        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "UNIFIED_DECISION_EXECUTION_REPAIRED_AND_REPLAYED",
        )
        self.assertEqual(out["decision_output"], repaired_decision)
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        retry_context = observe.call_args.kwargs["retry_context"]
        self.assertFalse(retry_context["auto_repair"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
