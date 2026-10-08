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

    @patch("canonical.runtime.live_brain_runtime_v1._run_learning_episode")
    def test_generic_path_executes_through_r3_reuse_first(self, learning_run):
        learning_run.return_value = {
            "pass": True,
            "status": "VERIFIED_SKILL_PERMANENTLY_ADMITTED_FOR_REUSE",
            "solver_output": {"pass": True, "status": "SOLVED__VERIFIED_EPISODE"},
            "learning": {"status": "VERIFIED_SKILL_PERMANENTLY_ADMITTED_FOR_REUSE"},
            "prior_verified_episode_count_used": 2,
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
        })

        self.assertTrue(out["pass"], out)
        self.assertEqual(out["verified_prior_episode_count_reused"], 2)
        self.assertTrue(out["reuse_first"])
        self.assertEqual(out["reused_skill_id"], "skill:abc")
        self.assertFalse(out["fallback_used"])
        self.assertEqual(
            out["solver"],
            "R3_REUSE_FIRST_OVER_UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V12",
        )
        learning_run.assert_called_once()

    @patch("canonical.runtime.live_brain_runtime_v1._v12_run")
    def test_generic_can_explicitly_disable_learning_and_use_plain_v12(self, solver):
        solver.return_value = {"pass": True, "status": "SOLVED__VERIFIED_EPISODE"}
        out = brain.run({
            "mode": "generic",
            "problem": self.problem(),
            "learn": False,
            "episode_id": "plain",
            "scope_id": "scope",
        })
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["learning_persistence_enabled"])
        self.assertFalse(out["reuse_first"])
        solver.assert_called_once()

    @patch("canonical.runtime.live_brain_runtime_v1._decision_run")
    @patch("canonical.runtime.live_brain_runtime_v1._run_learning_episode")
    def test_raw_goal_defaults_to_r2_and_uses_r3_as_execution_carrier(self, learning_run, decision):
        execution = {"pass": True, "status": "SOLVED__VERIFIED_EPISODE"}

        def decision_side_effect(request, **kwargs):
            provider = kwargs["execution_provider"]
            self.assertTrue(callable(provider))
            observed = provider(
                self.problem(),
                repo_root=brain.ROOT,
                episode_id="d1",
                scope_id="general-adequate-decision",
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
            "learning": {"status": "VERIFIED_EPISODE_PERSISTED__MORE_EVIDENCE_NEEDED_FOR_SKILL"},
            "reuse_first": True,
            "reused_skill_id": "skill:xyz",
            "reuse_attempt": {"pass": True},
            "fallback_used": False,
        }

        out = brain.run({"task_id": "d1", "goal": "do the exact thing"})
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["semantic_acceptance_complete"])
        self.assertTrue(out["actual_goal_satisfaction_verified"])
        self.assertTrue(out["reuse_first"])
        self.assertEqual(out["reused_skill_id"], "skill:xyz")
        decision.assert_called_once()
        learning_run.assert_called_once()

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

    def test_unknown_mode_fails_closed(self):
        out = brain.run({"mode": "invented"})
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
