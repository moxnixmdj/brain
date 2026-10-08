from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

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

        episode_verifier = Mock()
        skill_verifier = Mock()
        out = brain.run({
            "mode": "generic",
            "problem": self.problem(),
            "episode_id": "new",
            "scope_id": "scope",
            "known_absent_invalidators": ["inv.old"],
        }, episode_verification_provider=episode_verifier, skill_verification_provider=skill_verifier)

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
        self.assertIs(kwargs["episode_verification_provider"], episode_verifier)
        self.assertIs(kwargs["skill_verification_provider"], skill_verifier)

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
            @staticmethod
            def next_improvement_action(*, state_path):
                return None
        learning_module.return_value = L
        out = brain.inventory()
        self.assertEqual(out["status"], "UNIFIED_LIVE_BRAIN_READY")
        self.assertEqual(out["public_entrypoint"], "canonical.runtime.unified_cognitive_fabric_v1.run")
        self.assertEqual(out["subruntime_entrypoint"], "canonical.runtime.live_brain_runtime_v1.run")
        self.assertFalse(out["subruntime_public_authority"])
        self.assertIn("GENERAL_ADEQUATE_DECISION_FIXED_POINT_V2", out["surfaces"])
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
            "status": "FAILURE_DIAGNOSED__REPAIR_QUEUED",
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
            "FAILURE_DIAGNOSED__REPAIR_QUEUED",
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
            "status": "FAILURE_DIAGNOSED__REPAIR_QUEUED",
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
            "status": "FAILURE_DIAGNOSED__REPAIR_QUEUED",
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
            "FAILURE_DIAGNOSED__REPAIR_QUEUED",
        )
        observed = integrate.call_args.args[0]
        self.assertFalse(observed["pass"])
        self.assertEqual(
            observed["reason"],
            "SELECTED_PREDICATE_PROOF_COVERAGE_REQUIRED",
        )

    @patch("canonical.runtime.live_brain_runtime_v1._learning_module")
    @patch("canonical.runtime.live_brain_runtime_v1._bound_run")
    def test_plain_success_queues_verifiable_episode_adapter_without_promotion(
        self, bound, learning_module
    ):
        bound.return_value = {
            "pass": True,
            "status": "PASS__REAL_TASK_PLANNED_EXECUTED_AND_REVERIFIED",
        }
        learning = Mock()
        learning.DEFAULT_STATE_PATH = "/tmp/state.json"
        learning.record_success_observation.return_value = {
            "status": "SUCCESS_OBSERVED__VERIFIABLE_EPISODE_ADAPTER_QUEUED",
            "pass": True,
            "permanent_reuse_authorized": False,
        }
        learning_module.return_value = learning
        out = brain.run({
            "mode": "compiled_bound",
            "task_id": "b-ok",
            "initial_facts": [],
            "target_effects": ["X"],
            "state_path": "/tmp/state.json",
        })
        self.assertTrue(out["pass"])
        self.assertEqual(
            out["learning"]["status"],
            "SUCCESS_OBSERVED__VERIFIABLE_EPISODE_ADAPTER_QUEUED",
        )
        self.assertFalse(out["learning"]["permanent_reuse_authorized"])
        learning.record_success_observation.assert_called_once()


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

    @patch("canonical.runtime.live_brain_runtime_v1.execute_failure_repair_cycle")
    @patch("canonical.runtime.live_brain_runtime_v1.run_generic")
    def test_live_failure_auto_dispatches_verified_repair_when_frontier_is_available(
        self, generic, repair_cycle
    ):
        generic.return_value = {
            "schema": brain.SCHEMA,
            "status": "UNIFIED_GENERIC_EXECUTION_COMPLETE",
            "pass": False,
            "learning": {
                "pass": False,
                "diagnosis": {"failure_fingerprint": "fp:auto"},
                "retry_capsule_sha256": "retry:auto",
            },
        }
        repaired_replay = {"pass": True, "status": "UNIFIED_GENERIC_EXECUTION_COMPLETE"}
        repair_cycle.return_value = {
            "pass": True,
            "status": "REPAIR_VERIFIED_BY_ORIGINAL_OBLIGATION_REPLAY",
            "original_replay": repaired_replay,
        }
        component = {
            "id": "repairer",
            "verified": True,
            "brain_owned": True,
            "donor_independent": True,
        }
        out = brain.run({
            "mode": "generic",
            "problem": self.problem(),
            "repair_components": [component],
        })

        self.assertTrue(out["pass"], out)
        self.assertTrue(out["auto_repair_attempted"])
        self.assertEqual(out["recovered_execution"], repaired_replay)
        request = repair_cycle.call_args.args[0]
        self.assertEqual(request["failure_fingerprint"], "fp:auto")
        self.assertEqual(request["retry_capsule_sha256"], "retry:auto")
        self.assertEqual(request["components"], [component])
        self.assertTrue(request["autonomous"])

    @patch("canonical.runtime.live_brain_runtime_v1.execute_failure_repair_cycle")
    @patch("canonical.runtime.live_brain_runtime_v1.run_generic")
    def test_live_failure_without_injected_repair_authority_uses_internal_cycle(
        self, generic, repair_cycle
    ):
        generic.return_value = {
            "schema": brain.SCHEMA,
            "status": "UNIFIED_GENERIC_EXECUTION_COMPLETE",
            "pass": False,
            "learning": {
                "pass": False,
                "diagnosis": {"failure_fingerprint": "fp:blocked"},
                "retry_capsule_sha256": "retry:blocked",
            },
        }
        repair_cycle.return_value = {
            "pass": False,
            "status": "REPAIR_CYCLE_UNRESOLVED_AT_SYNTHESIS",
        }
        out = brain.run({"mode": "generic", "problem": self.problem()})

        self.assertFalse(out["pass"])
        self.assertTrue(out["auto_repair_attempted"])
        request = repair_cycle.call_args.args[0]
        self.assertEqual(request["failure_fingerprint"], "fp:blocked")
        self.assertEqual(request["retry_capsule_sha256"], "retry:blocked")
        self.assertEqual(request["components"], [])
        self.assertTrue(request["autonomous"])

    @patch("canonical.runtime.live_brain_runtime_v1.synthesize_failure_repair")
    @patch("canonical.runtime.live_brain_runtime_v1._learning_module")
    def test_autonomous_repair_refuses_retry_not_proved_safe(
        self, learning_module, synthesize
    ):
        class L:
            DEFAULT_STATE_PATH = "/tmp/r3-autonomous-repair-safety.json"

            @staticmethod
            def get_failure_retry_context(fid, state_path, retry_capsule_sha256=None):
                return {
                    "failure_fingerprint": fid,
                    "retry_capsule_sha256": "r" * 64,
                    "context": {
                        "mode": "generic",
                        "problem": {"task_id": "effectful"},
                    },
                    "autonomous_replay_authorized": False,
                    "autonomous_replay_reason": (
                        "EFFECT_MAY_HAVE_OCCURRED__RECOVERY_OR_EXPLICIT_REPLAY_REQUIRED"
                    ),
                    "resolved": False,
                }

        learning_module.return_value = L
        out = brain.execute_failure_repair_cycle(
            {
                "failure_fingerprint": "fp:effectful",
                "retry_capsule_sha256": "r" * 64,
                "components": [],
                "autonomous": True,
            }
        )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "AUTONOMOUS_REPAIR_BLOCKED__REPLAY_NOT_PROVED_SAFE",
        )
        self.assertEqual(
            out["autonomous_replay_reason"],
            "EFFECT_MAY_HAVE_OCCURRED__RECOVERY_OR_EXPLICIT_REPLAY_REQUIRED",
        )
        synthesize.assert_not_called()

    def test_replay_payload_strips_auto_repair_control_plane_fields(self):
        cleaned = brain._replay_request_payload({
            "task_id": "t",
            "target_effects": ["x"],
            "repair_components": [{"id": "r"}],
            "repair_solver_kwargs": {"x": 1},
            "auto_repair": True,
            "autonomous": True,
        })
        self.assertEqual(cleaned, {"task_id": "t", "target_effects": ["x"]})


    @patch("canonical.runtime.live_brain_runtime_v1._replay_retry_context")
    @patch("canonical.runtime.live_brain_runtime_v1._owned_raw_capability_acquisition")
    @patch("canonical.runtime.live_brain_runtime_v1.synthesize_failure_repair")
    @patch("canonical.runtime.live_brain_runtime_v1._learning_module")
    def test_raw_new_primitive_uses_owned_acquisition_then_original_replay(
        self, learning_module, synthesize, acquire, replay
    ):
        class L:
            DEFAULT_STATE_PATH = "/tmp/owned-acquisition-state.json"

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
                return {"retry_instance_resolved": kwargs["original_replay_pass"]}

        learning_module.return_value = L
        synthesize.return_value = {
            "pass": False,
            "required_repair_effect": "repair.capability.available",
            "causal_synthesis": {
                "pass": False,
                "classification": "NEW_PRIMITIVE_REQUIRED",
            },
        }
        acquire.return_value = {
            "pass": True,
            "status": "OWNED_RAW_CAPABILITY_ACQUISITION_EXECUTED",
            "mission_id": "LIVE-BRAIN-AUTO-ACQUIRE-ABC",
            "origin_mission_sha256": "a" * 64,
            "auto_acquisition": {"status": "VERIFIED_AND_PROMOTED"},
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
        self.assertEqual(replay.call_args.kwargs["state_path"], L.DEFAULT_STATE_PATH)

    @patch("canonical.runtime.live_brain_runtime_v1._owned_raw_capability_acquisition")
    @patch("canonical.runtime.live_brain_runtime_v1.synthesize_failure_repair")
    @patch("canonical.runtime.live_brain_runtime_v1._learning_module")
    def test_owned_raw_acquisition_failure_stays_unresolved(
        self, learning_module, synthesize, acquire
    ):
        class L:
            DEFAULT_STATE_PATH = "/tmp/owned-acquisition-state.json"

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


    def test_policy_adequacy_repair_class_has_distinct_causal_effect(self):
        self.assertEqual(
            brain._REPAIR_EFFECT_BY_CLASS[
                "SYNTHESIZE_OR_AUTHENTICATE_POLICY_ADEQUACY_COVER"
            ],
            "repair.policy_adequacy_cover.available",
        )


    def test_policy_repair_context_is_compact_and_drops_raw_model_valuations(self):
        out = brain._compact_policy_repair_context({
            "decision_output": {
                "next_policy_request": {
                    "loop_status": "OPEN__POSITIVE_POLICY_ADEQUACY_COVERAGE_REQUIRED",
                    "required_artifact": "POSITIVE_POLICY_ADEQUACY_COVERAGE",
                    "selected_policy_id": "p0",
                    "search_context": {
                        "authenticated_policy_ids": ["p1", "p0"],
                        "rejected_policy_candidates": [
                            {
                                "policy_id": "BOUND_CAPABILITY_POLICY::python.tests.audit.unittest",
                                "reason": "missing authority",
                                "raw_secret": "drop",
                            },
                            {"policy_id": "p2", "reason": "missing authority"},
                        ],
                        "certified_common_policies": [],
                        "uncovered_models": [
                            {"model_id": "m1", "valuation": {"PRIVATE_RAW_FACT": True}},
                        ],
                        "conflicting_policy_region_witness": [
                            {
                                "model_id": "m1",
                                "valuation": {"PRIVATE_RAW_FACT": True},
                                "adequate_policy_ids": ["p0"],
                            },
                            {
                                "model_id": "m2",
                                "valuation": {"OTHER_PRIVATE_FACT": False},
                                "adequate_policy_ids": ["p1"],
                            },
                        ],
                        "selected_discriminator": {
                            "discriminator_id": "d1",
                            "formula": {"atom": "PRIVATE_RAW_FACT"},
                            "cost_units": 1,
                        },
                        "alternative_resolving_discriminators": [
                            {
                                "discriminator_id": "d2",
                                "formula": {"atom": "OTHER_PRIVATE_FACT"},
                                "cost_units": 2,
                            },
                        ],
                        "decision_basis": ["PRIVATE_RAW_FACT", "OTHER_PRIVATE_FACT"],
                        "surviving_model_count": 2,
                    },
                },
            },
        })
        self.assertEqual(out["authenticated_policy_ids"], ["p0", "p1"])
        self.assertEqual(out["uncovered_model_ids"], ["m1"])
        self.assertEqual(
            out["conflicting_policy_region_witness"],
            [
                {"model_id": "m1", "adequate_policy_ids": ["p0"]},
                {"model_id": "m2", "adequate_policy_ids": ["p1"]},
            ],
        )
        self.assertEqual(
            out["selected_discriminator"],
            {"discriminator_id": "d1", "cost_units": 1},
        )
        self.assertEqual(
            out["grounded_bound_policy_candidates"],
            [
                {
                    "policy_id": (
                        "BOUND_CAPABILITY_POLICY::python.tests.audit.unittest"
                    ),
                    "capability_id": "python.tests.audit.unittest",
                }
            ],
        )
        rendered = str(out)
        self.assertNotIn("PRIVATE_RAW_FACT", rendered)
        self.assertNotIn("OTHER_PRIVATE_FACT", rendered)
        self.assertNotIn("raw_secret", rendered)

    def test_exact_grounded_policy_gap_becomes_one_concrete_adequacy_target(self):
        targets, source = brain._concretize_policy_adequacy_repair_target(
            "repair.policy_adequacy_cover.available",
            {
                "selected_policy_id": (
                    "BOUND_CAPABILITY_POLICY::python.tests.audit.unittest"
                ),
                "grounded_bound_policy_candidates": [
                    {
                        "policy_id": (
                            "BOUND_CAPABILITY_POLICY::python.tests.audit.unittest"
                        ),
                        "capability_id": "python.tests.audit.unittest",
                    },
                    {
                        "policy_id": "BOUND_CAPABILITY_POLICY::auto.pypi.msgpack",
                        "capability_id": "auto.pypi.msgpack",
                    },
                ],
            },
        )
        self.assertEqual(len(targets), 1)
        self.assertTrue(targets[0].startswith("repair.policy_adequacy.prove::"))
        self.assertEqual(
            source,
            "R2_EXACT_GROUNDED_BOUND_POLICY_ADEQUACY_GAP",
        )
        again, again_source = brain._concretize_policy_adequacy_repair_target(
            "repair.policy_adequacy_cover.available",
            {
                "selected_policy_id": (
                    "BOUND_CAPABILITY_POLICY::python.tests.audit.unittest"
                ),
                "grounded_bound_policy_candidates": [
                    {
                        "policy_id": (
                            "BOUND_CAPABILITY_POLICY::python.tests.audit.unittest"
                        ),
                        "capability_id": "python.tests.audit.unittest",
                    }
                ],
            },
        )
        self.assertEqual(targets, again)
        self.assertEqual(source, again_source)

    def test_ambiguous_grounded_policy_gap_requests_proof_of_one_not_all(self):
        targets, source = brain._concretize_policy_adequacy_repair_target(
            "repair.policy_adequacy_cover.available",
            {
                "grounded_bound_policy_candidates": [
                    {
                        "policy_id": "BOUND_CAPABILITY_POLICY::auto.pypi.msgpack",
                        "capability_id": "auto.pypi.msgpack",
                    },
                    {
                        "policy_id": "BOUND_CAPABILITY_POLICY::auto.npm.msgpack-msgpack",
                        "capability_id": "auto.npm.msgpack-msgpack",
                    },
                ],
            },
        )
        self.assertEqual(len(targets), 1)
        self.assertTrue(
            targets[0].startswith(
                "repair.policy_adequacy_cover.prove_one_of::"
            )
        )
        self.assertEqual(
            source,
            "R2_GROUNDED_BOUND_POLICY_FRONTIER_ADEQUACY_GAP",
        )

    def test_policy_concretizer_is_not_applied_to_capability_repair_targets(self):
        targets, source = brain._concretize_policy_adequacy_repair_target(
            "effect.originally.required",
            {
                "grounded_bound_policy_candidates": [
                    {
                        "policy_id": "BOUND_CAPABILITY_POLICY::irrelevant",
                        "capability_id": "irrelevant",
                    }
                ]
            },
        )
        self.assertEqual(targets, ["effect.originally.required"])
        self.assertEqual(source, "REPAIR_CLASS_META_EFFECT")

    def test_non_grounded_policy_gap_keeps_generic_meta_effect(self):
        targets, source = brain._concretize_policy_adequacy_repair_target(
            "repair.policy_adequacy_cover.available",
            {
                "rejected_policy_candidates": [
                    {"policy_id": "some.other.policy"}
                ]
            },
        )
        self.assertEqual(targets, ["repair.policy_adequacy_cover.available"])
        self.assertEqual(source, "REPAIR_CLASS_META_EFFECT")

    @patch("canonical.runtime.live_brain_runtime_v1.execute_failure_repair_cycle")
    def test_same_dispatch_auto_repair_receives_compact_policy_frontier(self, repair):
        repair.return_value = {"pass": False, "status": "REPAIR_PENDING"}
        result = {
            "pass": False,
            "status": "UNIFIED_DECISION_EXECUTION_COMPLETE",
            "learning": {
                "pass": False,
                "diagnosis": {"failure_fingerprint": "fp:policy"},
                "retry_capsule_sha256": "r" * 64,
            },
            "decision_output": {
                "next_policy_request": {
                    "loop_status": "OPEN__POSITIVE_POLICY_ADEQUACY_COVERAGE_REQUIRED",
                    "required_artifact": "POSITIVE_POLICY_ADEQUACY_COVERAGE",
                    "search_context": {
                        "authenticated_policy_ids": ["p0"],
                        "uncovered_models": [{"model_id": "m-gap", "valuation": {"x": True}}],
                    },
                },
            },
        }
        out = brain._auto_repair_live_failure(
            result,
            {"mode": "decision", "repair_components": []},
            repo_root=brain.ROOT,
            information_provider=None,
            proposal_provider=None,
            capability_expander=None,
        )
        self.assertTrue(out["auto_repair_attempted"])
        request = repair.call_args.args[0]
        self.assertEqual(
            request["repair_context"]["authenticated_policy_ids"],
            ["p0"],
        )
        self.assertEqual(
            request["repair_context"]["uncovered_model_ids"],
            ["m-gap"],
        )
        self.assertNotIn("valuation", str(request["repair_context"]))

    def test_unknown_mode_fails_closed(self):
        out = brain.run({"mode": "invented"})
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
