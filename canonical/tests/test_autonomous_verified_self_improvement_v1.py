from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as loop


def verified_episode(eid: str, scope: str = "scope") -> dict:
    return {
        "episode_id": eid,
        "scope_id": scope,
        "steps": [{"index": 0, "op": "solve", "inputs": [], "outputs": ["goal"]}],
        "preconditions": [],
        "postconditions": ["goal"],
        "invalidators": [],
        "program_sha256": "sha256:" + ("a" * 64),
        "problem_sha256": "b" * 64,
        "trace_sha256": ("c" if eid == "ep1" else "d") * 64,
        "fact_capsule_head_hash": "e" * 64,
        "value_capsule_head_hash": "f" * 64,
        "verification_receipt": {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "behavior_verified": True,
            "episode_id": eid,
            "scope_id": scope,
            "program_sha256": "sha256:" + ("a" * 64),
            "receipt_id": "EPVR:test-" + eid,
        },
        "verification_binding": {
            "receipt": {"path": "r-" + eid, "git_blob_sha": "1" * 40},
            "verification": {"path": "v-" + eid, "git_blob_sha": "2" * 40},
        },
    }


def valid_transfer_record(candidate_sha256: str) -> dict:
    return {
        "brain_candidate_sha256": candidate_sha256,
        "transfer_method": "DISTILLATION",
        "acquisition_and_deployment_phases_separated": True,
        "donor_use_confined_to_acquisition": True,
        "brain_owned_operative_artifact": True,
        "operative_artifact_content_addressed": True,
        "applicable_rights_and_provenance_closed": True,
        "donor_access_disabled_during_qualification": True,
        "donor_deletion_behavior_preserved": True,
        "independent_heldout_qualification_pass": True,
        "heldout_not_used_for_training_selection_or_tuning": True,
        "causal_ablation_pass": True,
        "causal_rescue_pass": True,
        "full_runtime_dependency_inventory_complete": True,
        "no_answer_leakage": True,
        "future_use_requires_no_donor_rediscovery": True,
        "donor_runtime_dependency_count": 0,
        "external_model_runtime_dependency_count": 0,
        "online_teacher_call_count": 0,
        "teacher_fallback_path_count": 0,
        "undeclared_runtime_dependency_count": 0,
        "qualification_performed_after_donor_removal": True,
        "donor_role": "ACQUISITION_SOURCE_ONLY",
        "operative_solver_role": "BRAIN_OWNED_DERIVED_MECHANISM",
        "student_or_derived_artifact_distinct_from_donor": True,
    }


def verified_skill(
    digest_char: str,
    *,
    relation: str = "EXACT",
    source_ids=("ep1", "ep2"),
    step_count: int = 2,
) -> dict:
    return {
        "schema": "PROJECT_BRAIN_EXECUTABLE_SKILL_PROGRAM_V7",
        "status": "VERIFIED_EXECUTABLE_SKILL",
        "source_episode_ids": list(source_ids),
        "source_episode_receipts": ["EPVR:" + x for x in source_ids],
        "source_scopes": ["scope"],
        "steps": [
            {
                "index": i,
                "op": "op" + str(i),
                "inputs": ["x"] if i else [],
                "outputs": ["goal"] if i == step_count - 1 else ["x"],
            }
            for i in range(step_count)
        ],
        "preconditions": [],
        "postconditions": ["goal"],
        "invalidators": [],
        "candidate_sha256": "sha256:" + (digest_char * 64),
        "verified_skill": True,
        "reuse_authorized": True,
        "candidate_only": False,
        "scope_relation": relation,
        "scope_predicate": (
            loop.VERIFIED_SUPERSET_SCOPE_PREDICATE
            if relation == "PROVEN_SUPERSET"
            else None
        ),
        "verification_receipt": "SKVR:" + digest_char * 40,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "promotion_authority": False,
        "execution_authority": False,
    }


class AutonomousVerifiedSelfImprovementV1Tests(unittest.TestCase):
    def temp_state(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        return Path(td.name) / "state.json"

    def test_failure_is_causally_classified_and_deduplicated(self):
        path = self.temp_state()
        failure = {
            "pass": False,
            "status": "FAIL__CAPABILITY_OR_TASK_CONTRACT_GAP",
            "failure_class": "MISSING_CAPABILITY_OR_COMPILED_TASK_CONTRACT",
            "attempts": [{"capability_id": "x", "status": "failed"}],
        }
        first = loop.integrate_solver_output(failure, state_path=path)
        second = loop.integrate_solver_output(failure, state_path=path)

        self.assertFalse(first["pass"])
        self.assertEqual(
            first["diagnosis"]["repair_class"],
            "ACQUIRE_COMPOSE_OR_INVENT_VERIFIABLE_CAPABILITY",
        )
        self.assertEqual(
            first["diagnosis"]["failure_fingerprint"],
            second["diagnosis"]["failure_fingerprint"],
        )
        state = loop.load_state(path)
        self.assertEqual(len(state["failures"]), 1)
        self.assertEqual(next(iter(state["failures"].values()))["count"], 2)
        self.assertEqual(state["stats"]["pending_improvement_count"], 1)
        next_work = loop.next_improvement_action(state_path=path)
        self.assertEqual(next_work["kind"], "REPAIR_FAILURE_CLASS")
        self.assertEqual(next_work["observations"], 2)

    def test_retry_capsule_autonomous_replay_is_effect_safety_bound(self):
        path = self.temp_state()
        safe_failure = {
            "pass": False,
            "status": "FAIL__CAPABILITY_OR_TASK_CONTRACT_GAP",
            "failure_class": "MISSING_CAPABILITY_OR_COMPILED_TASK_CONTRACT",
            "trace": [{"capability_id": "x"}],
        }
        safe = loop.integrate_solver_output(
            safe_failure,
            state_path=path,
            retry_context={"mode": "generic", "problem": {"task_id": "safe"}},
        )
        safe_retry = loop.get_failure_retry_context(
            safe["diagnosis"]["failure_fingerprint"],
            state_path=path,
            retry_capsule_sha256=safe["retry_capsule_sha256"],
        )
        self.assertTrue(safe_retry["autonomous_replay_authorized"])
        self.assertEqual(
            safe_retry["autonomous_replay_reason"],
            "NO_EFFECT_OUTCOME_RECORDED",
        )

        effectful_failure = {
            "pass": False,
            "status": "FAIL__CAPABILITY_OR_TASK_CONTRACT_GAP",
            "failure_class": "MISSING_CAPABILITY_OR_COMPILED_TASK_CONTRACT",
            "trace": [{
                "capability_id": "x",
                "effect_outcome_sha256": "sha256:" + "e" * 64,
            }],
        }
        effectful = loop.integrate_solver_output(
            effectful_failure,
            state_path=path,
            retry_context={"mode": "generic", "problem": {"task_id": "effectful"}},
        )
        effectful_retry = loop.get_failure_retry_context(
            effectful["diagnosis"]["failure_fingerprint"],
            state_path=path,
            retry_capsule_sha256=effectful["retry_capsule_sha256"],
        )
        self.assertFalse(effectful_retry["autonomous_replay_authorized"])
        self.assertEqual(
            effectful_retry["autonomous_replay_reason"],
            "EFFECT_MAY_HAVE_OCCURRED__RECOVERY_OR_EXPLICIT_REPLAY_REQUIRED",
        )

        later_safe_same_context = loop.integrate_solver_output(
            safe_failure,
            state_path=path,
            retry_context={"mode": "generic", "problem": {"task_id": "effectful"}},
        )
        later_retry = loop.get_failure_retry_context(
            later_safe_same_context["diagnosis"]["failure_fingerprint"],
            state_path=path,
            retry_capsule_sha256=effectful["retry_capsule_sha256"],
        )
        self.assertFalse(later_retry["autonomous_replay_authorized"])
        self.assertEqual(
            later_retry["autonomous_replay_reason"],
            "EFFECT_MAY_HAVE_OCCURRED__RECOVERY_OR_EXPLICIT_REPLAY_REQUIRED",
        )

    def test_repair_resolution_is_bound_to_exact_retry_capsule(self):
        path = self.temp_state()
        failure = {
            "pass": False,
            "status": "FAIL__CAPABILITY_OR_TASK_CONTRACT_GAP",
            "failure_class": "MISSING_CAPABILITY_OR_COMPILED_TASK_CONTRACT",
            "attempts": [],
        }
        first = loop.integrate_solver_output(
            failure,
            state_path=path,
            retry_context={"mode": "generic", "problem": {"task_id": "a"}},
        )
        second = loop.integrate_solver_output(
            failure,
            state_path=path,
            retry_context={"mode": "generic", "problem": {"task_id": "b"}},
        )
        self.assertNotEqual(first["retry_capsule_sha256"], second["retry_capsule_sha256"])

        loop.record_repair_outcome(
            first["diagnosis"]["failure_fingerprint"],
            retry_capsule_sha256=first["retry_capsule_sha256"],
            repair_record={"repair": "verified-a"},
            original_replay_pass=True,
            state_path=path,
        )
        state = loop.load_state(path)
        repair_rows = [
            row for row in state["improvement_queue"].values()
            if row.get("kind") == "REPAIR_FAILURE_CLASS"
        ]
        self.assertEqual(len(repair_rows), 2)
        by_retry = {
            row["identity"]["retry_capsule_sha256"]: row["status"]
            for row in repair_rows
        }
        self.assertEqual(by_retry[first["retry_capsule_sha256"]], "RESOLVED")
        self.assertEqual(by_retry[second["retry_capsule_sha256"]], "PENDING")

    def test_only_authenticated_verified_episode_is_persisted(self):
        path = self.temp_state()
        ep = verified_episode("ep1")
        out = {
            "pass": True,
            "status": "SOLVED__VERIFIED_EPISODE",
            "current_episode_verified": True,
            "current_episode": ep,
            "skill_candidate": None,
            "verified_skill_reuse_authorized": False,
            "verified_executable_skill": None,
        }
        with mock.patch.object(
            loop,
            "reauthenticate_episode_record",
            return_value={"pass": True, "authenticated_episode": ep},
        ):
            integrated = loop.integrate_solver_output(out, state_path=path)
        state = loop.load_state(path)

        self.assertTrue(integrated["episode_added"])
        self.assertEqual(state["stats"]["verified_episode_count"], 1)
        self.assertEqual(len(state["episodes"]), 1)
        self.assertEqual(
            loop.next_improvement_action(state_path=path)["kind"],
            "COLLECT_MATCHING_VERIFIED_EPISODE",
        )

    def test_forged_verified_episode_flag_cannot_persist_without_reauthentication(self):
        path = self.temp_state()
        ep = verified_episode("forged-episode")
        out = {
            "pass": True,
            "status": "SOLVED__VERIFIED_EPISODE",
            "current_episode_verified": True,
            "current_episode": ep,
            "skill_candidate": None,
            "verified_skill_reuse_authorized": False,
            "verified_executable_skill": None,
        }
        with mock.patch.object(
            loop,
            "reauthenticate_episode_record",
            return_value={"pass": False, "reason": "FORGED_BINDING"},
        ):
            with self.assertRaisesRegex(
                loop.SelfImprovementError,
                "VERIFIED_EPISODE_REAUTHENTICATION_FAILED",
            ):
                loop.integrate_solver_output(out, state_path=path)

        state = loop.load_state(path)
        self.assertEqual(state["stats"]["verified_episode_count"], 0)
        self.assertEqual(state["episodes"], {})

    def test_forged_verified_skill_flag_cannot_enter_pareto_state(self):
        path = self.temp_state()
        skill = verified_skill("f", relation="EXACT")
        out = {
            "pass": True,
            "status": "SOLVED__VERIFIED_EXECUTABLE_SKILL_READY",
            "current_episode_verified": False,
            "skill_candidate": skill,
            "verified_skill_reuse_authorized": True,
            "verified_executable_skill": skill,
        }
        with mock.patch.object(
            loop,
            "reauthenticate_skill_record",
            return_value={"pass": False, "reason": "FORGED_BINDING"},
        ):
            with self.assertRaisesRegex(
                loop.SelfImprovementError,
                "VERIFIED_SKILL_REAUTHENTICATION_FAILED",
            ):
                loop.integrate_solver_output(out, state_path=path)

        state = loop.load_state(path)
        self.assertEqual(state["stats"]["verified_skill_count"], 0)
        self.assertEqual(state["stats"]["active_skill_count"], 0)
        self.assertEqual(state["skills"], {})

    def test_unverified_candidate_never_gets_permanent_reuse(self):
        path = self.temp_state()
        out = {
            "pass": True,
            "status": "SOLVED__SKILL_CANDIDATE_READY",
            "current_episode_verified": False,
            "skill_candidate": {"candidate_sha256": "sha256:" + "9" * 64},
            "verified_skill_reuse_authorized": False,
            "verified_executable_skill": None,
        }
        integrated = loop.integrate_solver_output(out, state_path=path)
        state = loop.load_state(path)

        self.assertEqual(
            integrated["status"],
            "SKILL_CANDIDATE_AWAITS_INDEPENDENT_VERIFICATION",
        )
        self.assertFalse(integrated["permanent_reuse_authorized"])
        self.assertEqual(state["stats"]["verified_skill_count"], 0)
        self.assertEqual(
            loop.next_improvement_action(state_path=path)["kind"],
            "VERIFY_SKILL_CANDIDATE",
        )
        work = loop.next_improvement_action(state_path=path)
        self.assertEqual(work["payload"]["candidate"], out["skill_candidate"])

    def test_verified_stronger_skill_pareto_replaces_dominated_variant(self):
        path = self.temp_state()
        first_skill = verified_skill("3", relation="EXACT", source_ids=("ep1", "ep2"))
        with mock.patch.object(
            loop,
            "reauthenticate_skill_record",
            return_value={"pass": True, "verified_skill": first_skill},
        ):
            first = loop.integrate_solver_output(
                {
                    "pass": True,
                    "status": "SOLVED__VERIFIED_EXECUTABLE_SKILL_READY",
                    "current_episode_verified": False,
                    "skill_candidate": first_skill,
                    "verified_skill_reuse_authorized": True,
                    "verified_executable_skill": first_skill,
                },
                state_path=path,
            )
        self.assertTrue(first["permanent_reuse_authorized"])
        first_id = first["active_skill_id"]
        self.assertEqual(
            loop.next_improvement_action(state_path=path)["kind"],
            "SEEK_VERIFIED_SCOPE_GENERALIZATION",
        )

        stronger = verified_skill(
            "4",
            relation="PROVEN_SUPERSET",
            source_ids=("ep1", "ep2", "ep3"),
        )
        with mock.patch.object(
            loop,
            "reauthenticate_skill_record",
            side_effect=lambda skill, **_: {"pass": True, "verified_skill": skill},
        ):
            second = loop.integrate_solver_output(
                {
                    "pass": True,
                    "status": "SOLVED__VERIFIED_EXECUTABLE_SKILL_READY",
                    "current_episode_verified": False,
                    "skill_candidate": stronger,
                    "verified_skill_reuse_authorized": True,
                    "verified_executable_skill": stronger,
                },
                state_path=path,
            )
        state = loop.load_state(path)
        second_id = second["active_skill_id"]

        self.assertIsNotNone(second_id)
        self.assertNotEqual(first_id, second_id)
        self.assertFalse(state["skills"][first_id]["active"])
        self.assertEqual(state["skills"][first_id]["dominated_by"], second_id)
        self.assertTrue(state["skills"][second_id]["active"])
        family = state["skills"][second_id]["family_id"]
        self.assertEqual(state["pareto_frontiers"][family], [second_id])
        self.assertFalse(any(
            row.get("kind") == "SEEK_VERIFIED_SCOPE_GENERALIZATION"
            and row.get("status") == "PENDING"
            for row in state["improvement_queue"].values()
        ))

    def test_dominated_verified_skill_is_kept_as_evidence_but_not_activated(self):
        path = self.temp_state()
        strong = verified_skill(
            "5",
            relation="PROVEN_SUPERSET",
            source_ids=("ep1", "ep2", "ep3"),
            step_count=1,
        )
        with mock.patch.object(
            loop,
            "reauthenticate_skill_record",
            return_value={"pass": True, "verified_skill": strong},
        ):
            active = loop.integrate_solver_output(
                {
                    "pass": True,
                    "current_episode_verified": False,
                    "skill_candidate": strong,
                    "verified_skill_reuse_authorized": True,
                    "verified_executable_skill": strong,
                },
                state_path=path,
            )
        weak = verified_skill("6", relation="EXACT", source_ids=("ep1", "ep2"), step_count=2)
        with mock.patch.object(
            loop,
            "reauthenticate_skill_record",
            side_effect=lambda skill, **_: {"pass": True, "verified_skill": skill},
        ):
            rejected = loop.integrate_solver_output(
                {
                    "pass": True,
                    "current_episode_verified": False,
                    "skill_candidate": weak,
                    "verified_skill_reuse_authorized": True,
                    "verified_executable_skill": weak,
                },
                state_path=path,
            )
        state = loop.load_state(path)
        weak_id = "skill:" + "6" * 64

        self.assertIsNone(rejected["active_skill_id"])
        self.assertFalse(rejected["permanent_reuse_authorized"])
        self.assertIn(weak_id, state["skills"])
        self.assertFalse(state["skills"][weak_id]["active"])
        self.assertEqual(state["skills"][weak_id]["dominated_by"], active["active_skill_id"])

    def test_unauthenticated_frontier_entry_cannot_dominate_new_verified_skill(self):
        path = self.temp_state()
        stale = verified_skill(
            "5",
            relation="PROVEN_SUPERSET",
            source_ids=("ep1", "ep2", "ep3"),
            step_count=1,
        )
        stale_sid = self._seed_active_skill(path, stale)
        fresh = verified_skill(
            "6",
            relation="EXACT",
            source_ids=("ep4", "ep5"),
            step_count=2,
        )

        def reauth(skill, **_):
            if skill.get("candidate_sha256") == stale.get("candidate_sha256"):
                return {"pass": False, "reason": "STALE_AUTHORITY"}
            return {"pass": True, "verified_skill": skill}

        with mock.patch.object(
            loop,
            "reauthenticate_skill_record",
            side_effect=reauth,
        ):
            admitted = loop.integrate_solver_output(
                {
                    "pass": True,
                    "current_episode_verified": False,
                    "skill_candidate": fresh,
                    "verified_skill_reuse_authorized": True,
                    "verified_executable_skill": fresh,
                },
                state_path=path,
            )

        state = loop.load_state(path)
        fresh_sid = loop._skill_id(fresh)
        self.assertEqual(admitted["active_skill_id"], fresh_sid)
        self.assertTrue(state["skills"][fresh_sid]["active"])
        self.assertFalse(state["skills"][stale_sid]["active"])
        self.assertEqual(
            state["skills"][stale_sid]["authority_invalidated"],
            "STALE_AUTHORITY",
        )
        family = loop._family_id(fresh)
        self.assertEqual(state["pareto_frontiers"][family], [fresh_sid])

    def test_verification_queue_autonomously_promotes_pending_candidate(self):
        path = self.temp_state()
        skill = verified_skill("a", relation="EXACT")
        candidate = loop._candidate_from_verified_skill(skill)
        loop.integrate_solver_output(
            {
                "pass": True,
                "status": "SOLVED__SKILL_CANDIDATE_READY",
                "current_episode_verified": False,
                "skill_candidate": candidate,
                "verified_skill_reuse_authorized": False,
                "verified_executable_skill": None,
            },
            state_path=path,
        )
        provider = mock.Mock(
            return_value={"receipt": {"path": "r"}, "verification": {"path": "v"}}
        )
        with (
            mock.patch.object(
                loop,
                "authenticate_skill_verification",
                return_value={
                    "pass": True,
                    "verified_skill": skill,
                    "status": "PASS__AUTHENTICATED_VERIFIED_EXECUTABLE_SKILL",
                },
            ),
            mock.patch.object(
                loop,
                "reauthenticate_skill_record",
                return_value={"pass": True, "verified_skill": skill},
            ),
        ):
            tick = loop.advance_verification_queue(
                state_path=path,
                repo_root=Path("."),
                skill_verification_provider=provider,
                max_actions=1,
            )

        self.assertEqual(tick["attempted"], 1, tick)
        self.assertEqual(tick["completed"], 1, tick)
        sid = loop._skill_id(skill)
        state = loop.load_state(path)
        self.assertTrue(state["skills"][sid]["active"])
        self.assertFalse(any(
            row.get("kind") == "VERIFY_SKILL_CANDIDATE"
            and row.get("status") == "PENDING"
            for row in state["improvement_queue"].values()
        ))
        provider.assert_called_once()
        self.assertEqual(provider.call_args.args[0]["kind"], "SKILL_VERIFICATION")

    def test_verification_queue_upgrades_same_skill_to_bound_superset_without_self_deactivation(self):
        path = self.temp_state()
        exact = verified_skill("b", relation="EXACT")
        with mock.patch.object(
            loop,
            "reauthenticate_skill_record",
            return_value={"pass": True, "verified_skill": exact},
        ):
            first = loop.integrate_solver_output(
                {
                    "pass": True,
                    "status": "SOLVED__VERIFIED_EXECUTABLE_SKILL_READY",
                    "current_episode_verified": False,
                    "skill_candidate": exact,
                    "verified_skill_reuse_authorized": True,
                    "verified_executable_skill": exact,
                },
                state_path=path,
            )
        sid = first["active_skill_id"]
        self.assertIsNotNone(sid)
        generalized = {
            **exact,
            "scope_relation": "PROVEN_SUPERSET",
            "scope_predicate": loop.VERIFIED_SUPERSET_SCOPE_PREDICATE,
        }
        provider = mock.Mock(
            return_value={"receipt": {"path": "r"}, "verification": {"path": "v"}}
        )
        with (
            mock.patch.object(
                loop,
                "authenticate_skill_verification",
                return_value={
                    "pass": True,
                    "verified_skill": generalized,
                    "status": "PASS__AUTHENTICATED_VERIFIED_EXECUTABLE_SKILL",
                },
            ),
            mock.patch.object(
                loop,
                "reauthenticate_skill_record",
                return_value={"pass": True, "verified_skill": generalized},
            ),
        ):
            tick = loop.advance_verification_queue(
                state_path=path,
                repo_root=Path("."),
                skill_verification_provider=provider,
                max_actions=1,
            )

        self.assertEqual(tick["completed"], 1, tick)
        state = loop.load_state(path)
        self.assertTrue(state["skills"][sid]["active"], state["skills"][sid])
        self.assertEqual(
            state["skills"][sid]["skill"]["scope_predicate"],
            loop.VERIFIED_SUPERSET_SCOPE_PREDICATE,
        )
        self.assertEqual(state["skills"][sid]["pareto_metrics"]["generalization"], 2)
        self.assertFalse(any(
            row.get("kind") == "SEEK_VERIFIED_SCOPE_GENERALIZATION"
            and row.get("status") == "PENDING"
            for row in state["improvement_queue"].values()
        ))
        request = provider.call_args.args[0]
        self.assertEqual(request["kind"], "SKILL_SCOPE_GENERALIZATION_VERIFICATION")
        self.assertEqual(request["requested_scope_relation"], "PROVEN_SUPERSET")
        self.assertEqual(
            request["requested_scope_predicate"],
            loop.VERIFIED_SUPERSET_SCOPE_PREDICATE,
        )

    def test_failed_queue_verification_is_not_hammered_without_new_evidence(self):
        path = self.temp_state()
        skill = verified_skill("c", relation="EXACT")
        candidate = loop._candidate_from_verified_skill(skill)
        episode = {
            "pass": True,
            "status": "SOLVED__SKILL_CANDIDATE_READY",
            "current_episode_verified": False,
            "skill_candidate": candidate,
            "verified_skill_reuse_authorized": False,
            "verified_executable_skill": None,
        }
        loop.integrate_solver_output(episode, state_path=path)
        provider = mock.Mock(
            return_value={"receipt": {"path": "r"}, "verification": {"path": "v"}}
        )
        rejected = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "independent proof absent",
        }
        with mock.patch.object(
            loop,
            "authenticate_skill_verification",
            return_value=rejected,
        ):
            first = loop.advance_verification_queue(
                state_path=path,
                repo_root=Path("."),
                skill_verification_provider=provider,
            )
            second = loop.advance_verification_queue(
                state_path=path,
                repo_root=Path("."),
                skill_verification_provider=provider,
            )
            loop.integrate_solver_output(episode, state_path=path)
            third = loop.advance_verification_queue(
                state_path=path,
                repo_root=Path("."),
                skill_verification_provider=provider,
            )

        self.assertEqual(first["attempted"], 1)
        self.assertEqual(second["attempted"], 0)
        self.assertEqual(third["attempted"], 1)
        self.assertEqual(provider.call_count, 2)


    def test_learning_run_automatically_reuses_prior_verified_episodes(self):
        path = self.temp_state()
        state = loop.load_state(path)
        ep = verified_episode("ep1")
        state["episodes"][loop._episode_key(ep)] = ep
        loop._refresh_stats(state)
        loop._write_state(state, path)

        solver_out = {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "TEST_STOP",
            "falsified_capability_ids": [],
            "deferred_capability_ids": [],
            "counterexamples": [],
            "attempts": [],
        }
        with mock.patch.object(loop.solver_v12, "run", return_value=solver_out) as run_mock:
            result = loop.run_learning_episode(
                {"task_id": "t", "initial_facts": [], "target_effects": ["goal"], "capabilities": []},
                state_path=path,
                repo_root=Path("."),
                episode_id="ep2",
                scope_id="scope",
            )

        self.assertEqual(result["prior_verified_episode_count_used"], 1)
        kwargs = run_mock.call_args.kwargs
        self.assertEqual(len(kwargs["prior_verified_episode_records"]), 1)
        self.assertEqual(kwargs["prior_verified_episode_records"][0]["episode_id"], "ep1")


    def _seed_active_skill(self, path, skill):
        state = loop.load_state(path)
        sid = loop._skill_id(skill)
        row = loop._skill_pareto_row(sid, skill)
        state["skills"][sid] = {
            "skill": skill,
            "family_id": loop._family_id(skill),
            "pareto_metrics": row,
            "active": True,
            "dominated_by": None,
            "compression": {},
        }
        state["pareto_frontiers"][loop._family_id(skill)] = [sid]
        loop._refresh_stats(state)
        loop._write_state(state, path)
        return sid

    def _reuse_problem(self):
        return {
            "task_id": "reuse-task",
            "initial_facts": [],
            "target_effects": ["goal"],
            "capabilities": [
                {
                    "id": "op0",
                    "requires": [],
                    "provides": ["x"],
                    "cost": 1,
                    "action": {"type": "verified_policy"},
                },
                {
                    "id": "op1",
                    "requires": ["x"],
                    "provides": ["goal"],
                    "cost": 1,
                    "action": {"type": "verified_policy"},
                },
                {
                    "id": "distractor",
                    "requires": [],
                    "provides": ["other"],
                    "cost": 1,
                    "action": {"type": "verified_policy"},
                },
            ],
        }

    def test_unreauthenticated_active_skill_is_invisible_to_reuse_planner(self):
        path = self.temp_state()
        skill = verified_skill("1", relation="EXACT", source_ids=("ep1", "ep2"))
        self._seed_active_skill(path, skill)
        solved = {
            "pass": True,
            "status": "SOLVED__EPISODE_VERIFICATION_REQUIRED",
            "current_episode_verified": False,
            "skill_candidate": None,
            "verified_skill_reuse_authorized": False,
            "verified_executable_skill": None,
        }
        with (
            mock.patch.object(
                loop,
                "reauthenticate_skill_record",
                return_value={"pass": False, "reason": "LEGACY_OR_TAMPERED"},
            ) as reauth,
            mock.patch.object(loop.solver_v12, "run", return_value=solved) as run_mock,
        ):
            out = loop.run_learning_episode(
                self._reuse_problem(),
                state_path=path,
                repo_root=Path("."),
                episode_id="ep3",
                scope_id="scope",
            )

        self.assertTrue(out["pass"], out)
        self.assertFalse(out["reuse_first"], out)
        self.assertIsNone(out["reused_skill_id"])
        self.assertEqual(run_mock.call_count, 1)
        full_problem = run_mock.call_args.args[0]
        self.assertEqual(
            [x["id"] for x in full_problem["capabilities"]],
            ["op0", "op1", "distractor"],
        )
        reauth.assert_called_once()

    def test_reauthenticated_skill_with_registry_identity_mismatch_is_not_reused(self):
        path = self.temp_state()
        skill = verified_skill("2", relation="EXACT", source_ids=("ep1", "ep2"))
        state = loop._empty_state()
        real_sid = loop._skill_id(skill)
        family = loop._family_id(skill)
        wrong_sid = "skill:" + "0" * 64
        state["skills"][wrong_sid] = {
            "skill": skill,
            "family_id": family,
            "pareto_metrics": loop._skill_pareto_row(real_sid, skill),
            "active": True,
            "dominated_by": None,
            "compression": {},
        }
        state["pareto_frontiers"][family] = [wrong_sid]
        loop._refresh_stats(state)
        loop._write_state(state, path)

        solved = {
            "pass": True,
            "status": "SOLVED__EPISODE_VERIFICATION_REQUIRED",
            "current_episode_verified": False,
            "skill_candidate": None,
            "verified_skill_reuse_authorized": False,
            "verified_executable_skill": None,
        }
        with (
            mock.patch.object(
                loop,
                "reauthenticate_skill_record",
                return_value={"pass": True, "verified_skill": skill},
            ),
            mock.patch.object(loop.solver_v12, "run", return_value=solved) as run_mock,
        ):
            out = loop.run_learning_episode(
                self._reuse_problem(),
                state_path=path,
                repo_root=Path("."),
                episode_id="ep3",
                scope_id="scope",
            )

        self.assertFalse(out["reuse_first"], out)
        self.assertIsNone(out["reused_skill_id"])
        self.assertEqual(run_mock.call_count, 1)
        self.assertNotEqual(wrong_sid, real_sid)

    def test_active_verified_skill_is_automatically_used_as_planning_compression(self):
        path = self.temp_state()
        skill = verified_skill("7", relation="EXACT", source_ids=("ep1", "ep2"))
        sid = self._seed_active_skill(path, skill)
        solved = {
            "pass": True,
            "status": "SOLVED__EPISODE_VERIFICATION_REQUIRED",
            "current_episode_verified": False,
            "skill_candidate": None,
            "verified_skill_reuse_authorized": False,
            "verified_executable_skill": None,
        }
        with (
            mock.patch.object(
                loop,
                "reauthenticate_skill_record",
                side_effect=lambda skill, **_: {"pass": True, "verified_skill": skill},
            ),
            mock.patch.object(loop.solver_v12, "run", return_value=solved) as run_mock,
        ):
            out = loop.run_learning_episode(
                self._reuse_problem(),
                state_path=path,
                repo_root=Path("."),
                episode_id="ep3",
                scope_id="scope",
            )

        self.assertTrue(out["pass"])
        self.assertTrue(out["reuse_first"])
        self.assertEqual(out["reused_skill_id"], sid)
        self.assertFalse(out["fallback_used"])
        self.assertEqual(run_mock.call_count, 1)
        learned_problem = run_mock.call_args.args[0]
        self.assertEqual(
            [cap["id"] for cap in learned_problem["capabilities"]],
            ["op0", "op1"],
        )
        state = loop.load_state(path)
        self.assertEqual(state["reuse"][sid]["attempts"], 1)
        self.assertEqual(state["reuse"][sid]["successes"], 1)

    def test_pre_effect_learned_route_failure_falls_back_to_full_solver(self):
        path = self.temp_state()
        skill = verified_skill("8", relation="EXACT", source_ids=("ep1", "ep2"))
        sid = self._seed_active_skill(path, skill)
        failed = {
            "pass": False,
            "status": "FAIL_CLOSED__PROPOSAL_SEARCH_FAILED",
            "reason": "no proposal",
            "trace": [],
            "falsified_capability_ids": [],
            "deferred_capability_ids": [],
            "counterexamples": [],
            "attempts": [],
        }
        solved = {
            "pass": True,
            "status": "SOLVED__EPISODE_VERIFICATION_REQUIRED",
            "current_episode_verified": False,
            "skill_candidate": None,
            "verified_skill_reuse_authorized": False,
            "verified_executable_skill": None,
        }
        with (
            mock.patch.object(
                loop,
                "reauthenticate_skill_record",
                side_effect=lambda skill, **_: {"pass": True, "verified_skill": skill},
            ),
            mock.patch.object(
                loop.solver_v12, "run", side_effect=[failed, solved]
            ) as run_mock,
        ):
            out = loop.run_learning_episode(
                self._reuse_problem(),
                state_path=path,
                repo_root=Path("."),
                episode_id="ep3",
                scope_id="scope",
            )

        self.assertTrue(out["pass"])
        self.assertTrue(out["reuse_first"])
        self.assertTrue(out["fallback_used"])
        self.assertEqual(out["reused_skill_id"], sid)
        self.assertEqual(run_mock.call_count, 2)
        first_problem = run_mock.call_args_list[0].args[0]
        second_problem = run_mock.call_args_list[1].args[0]
        self.assertEqual([x["id"] for x in first_problem["capabilities"]], ["op0", "op1"])
        self.assertEqual(
            [x["id"] for x in second_problem["capabilities"]],
            ["op0", "op1", "distractor"],
        )
        state = loop.load_state(path)
        self.assertEqual(state["reuse"][sid]["pre_effect_failures"], 1)

    def test_effectful_learned_route_failure_blocks_blind_fallback(self):
        path = self.temp_state()
        skill = verified_skill("9", relation="EXACT", source_ids=("ep1", "ep2"))
        sid = self._seed_active_skill(path, skill)
        failed = {
            "pass": False,
            "status": "BOUND_SUBPLAN_EFFECT_OUTCOME_UNRESOLVED__RECOVERY_REQUIRED",
            "reason": "effect may have occurred",
            "trace": [{"capability_id": "op0", "effect_outcome_sha256": "a" * 64}],
            "falsified_capability_ids": [],
            "deferred_capability_ids": [],
            "counterexamples": [],
            "attempts": [],
        }
        with (
            mock.patch.object(
                loop,
                "reauthenticate_skill_record",
                side_effect=lambda skill, **_: {"pass": True, "verified_skill": skill},
            ),
            mock.patch.object(loop.solver_v12, "run", return_value=failed) as run_mock,
        ):
            out = loop.run_learning_episode(
                self._reuse_problem(),
                state_path=path,
                repo_root=Path("."),
                episode_id="ep3",
                scope_id="scope",
            )

        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "FAIL_CLOSED__LEARNED_ROUTE_EFFECT_OCCURRED__NO_BLIND_REPLAY",
        )
        self.assertTrue(out["fallback_blocked_effect_may_have_occurred"])
        self.assertEqual(run_mock.call_count, 1)
        state = loop.load_state(path)
        self.assertEqual(state["reuse"][sid]["effectful_failures"], 1)
        self.assertFalse(state["skills"][sid]["active"])
        self.assertTrue(state["skills"][sid]["quarantined"])
        self.assertNotIn(sid, state["pareto_frontiers"][state["skills"][sid]["family_id"]])
        next_work = loop.next_improvement_action(state_path=path)
        self.assertEqual(next_work["kind"], "REVERIFY_QUARANTINED_SKILL")
        self.assertFalse(next_work["payload"]["scope_contraction_safe"])

    def test_effectful_superset_failure_outside_source_scope_queues_safe_contraction(self):
        path = self.temp_state()
        skill = verified_skill("8", relation="PROVEN_SUPERSET", source_ids=("ep1", "ep2"))
        sid = self._seed_active_skill(path, skill)
        failed = {
            "pass": False,
            "status": "BOUND_SUBPLAN_EFFECT_OUTCOME_UNRESOLVED__RECOVERY_REQUIRED",
            "reason": "effect may have occurred",
            "trace": [{"capability_id": "op0", "effect_outcome_sha256": "b" * 64}],
            "falsified_capability_ids": [],
            "deferred_capability_ids": [],
            "counterexamples": [],
            "attempts": [],
        }
        with (
            mock.patch.object(
                loop,
                "reauthenticate_skill_record",
                side_effect=lambda skill, **_: {"pass": True, "verified_skill": skill},
            ),
            mock.patch.object(loop.solver_v12, "run", return_value=failed),
        ):
            out = loop.run_learning_episode(
                self._reuse_problem(),
                state_path=path,
                repo_root=Path("."),
                episode_id="ep-outside",
                scope_id="outside-scope",
            )

        self.assertFalse(out["pass"])
        state = loop.load_state(path)
        rec = state["skills"][sid]
        self.assertTrue(rec["quarantined"])
        self.assertEqual(rec["generalization_counterexample_scopes"], ["outside-scope"])
        self.assertTrue(rec["generalization_repromotion_blocked"])
        work = loop.next_improvement_action(state_path=path)
        self.assertTrue(work["payload"]["scope_contraction_safe"])
        self.assertEqual(work["payload"]["counterexample_scope_id"], "outside-scope")
        self.assertEqual(work["payload"]["source_scopes"], ["scope"])
        self.assertEqual(work["payload"]["previous_scope_relation"], "PROVEN_SUPERSET")

    def test_post_execution_episode_verifier_promotes_without_rerunning_task(self):
        path = self.temp_state()
        raw_episode = {
            "episode_id": "ep-post",
            "scope_id": "scope",
            "program_sha256": "sha256:program",
            "trace_sha256": "sha256:trace",
        }
        solved = {
            "pass": True,
            "status": "SOLVED__EPISODE_VERIFICATION_REQUIRED",
            "current_episode": raw_episode,
            "current_episode_verified": False,
            "trace": [{"capability_id": "c1"}],
            "state_capsule_head_hash": "fact-head",
            "value_capsule_head_hash": "value-head",
            "skill_candidate": None,
        }
        authenticated = {
            **raw_episode,
            "verification_binding": {"receipt": {}, "verification": {}},
            "verification_receipt": {
                "independent_verified": True,
                "exact_byte_bound": True,
                "conclusion": "success",
                "behavior_verified": True,
                "episode_id": "ep-post",
                "scope_id": "scope",
                "program_sha256": "sha256:program",
                "receipt_id": "EPVR:test",
            },
        }
        provider = mock.Mock(return_value={"receipt": {"path": "r"}, "verification": {"path": "v"}})
        auth = {
            "pass": True,
            "authenticated_episode": authenticated,
            "status": "PASS__AUTHENTICATED_INDEPENDENT_EPISODE_VERIFICATION",
        }
        integrated = {
            "status": "VERIFIED_EPISODE_PERSISTED__MORE_EVIDENCE_NEEDED_FOR_SKILL",
            "pass": True,
        }
        with mock.patch.object(loop, "load_state", return_value=loop._empty_state()), \
             mock.patch.object(loop, "_select_active_skill", return_value=None), \
             mock.patch.object(loop.solver_v12, "run", return_value=solved) as run_mock, \
             mock.patch.object(loop, "authenticate_episode_verification", return_value=auth) as authenticate, \
             mock.patch.object(loop, "integrate_solver_output", return_value=integrated) as integrate:
            out = loop.run_learning_episode(
                self._reuse_problem(),
                state_path=path,
                repo_root=Path("."),
                episode_id="ep-post",
                scope_id="scope",
                episode_verification_provider=provider,
            )

        self.assertTrue(out["pass"], out)
        self.assertEqual(run_mock.call_count, 1)
        provider.assert_called_once()
        authenticate.assert_called_once()
        integrated_out = integrate.call_args.args[0]
        self.assertTrue(integrated_out["current_episode_verified"])
        self.assertEqual(integrated_out["current_episode"], authenticated)

    def test_post_execution_skill_verifier_promotes_candidate_without_rerunning_task(self):
        path = self.temp_state()
        candidate = {
            "candidate_only": True,
            "candidate_sha256": "sha256:candidate",
            "source_episode_ids": ["e1", "e2"],
            "source_scopes": ["scope"],
            "postconditions": ["DONE"],
        }
        episode = {
            "episode_id": "ep-skill",
            "scope_id": "scope",
            "program_sha256": "sha256:program",
            "trace_sha256": "sha256:trace",
            "verification_binding": {"receipt": {}, "verification": {}},
            "verification_receipt": {"receipt_id": "EPVR:test"},
        }
        solved = {
            "pass": True,
            "status": "SOLVED__SKILL_CANDIDATE_READY",
            "current_episode": episode,
            "current_episode_verified": True,
            "trace": [],
            "skill_candidate": candidate,
            "verified_executable_skill": None,
            "verified_skill_reuse_authorized": False,
        }
        verified_skill = {
            **candidate,
            "candidate_only": False,
            "verified_skill": True,
            "reuse_authorized": True,
            "scope_relation": "EXACT",
        }
        provider = mock.Mock(return_value={"receipt": {"path": "r"}, "verification": {"path": "v"}})
        auth = {
            "pass": True,
            "verified_skill": verified_skill,
            "status": "PASS__AUTHENTICATED_VERIFIED_EXECUTABLE_SKILL",
        }
        with mock.patch.object(loop, "load_state", return_value=loop._empty_state()), \
             mock.patch.object(loop, "_select_active_skill", return_value=None), \
             mock.patch.object(loop.solver_v12, "run", return_value=solved) as run_mock, \
             mock.patch.object(loop, "authenticate_skill_verification", return_value=auth) as authenticate, \
             mock.patch.object(
                 loop,
                 "integrate_solver_output",
                 return_value={
                     "status": "VERIFIED_SKILL_PERMANENTLY_ADMITTED_FOR_REUSE",
                     "pass": True,
                 },
             ) as integrate:
            out = loop.run_learning_episode(
                self._reuse_problem(),
                state_path=path,
                repo_root=Path("."),
                episode_id="ep-skill",
                scope_id="scope",
                skill_verification_provider=provider,
            )

        self.assertTrue(out["pass"], out)
        self.assertEqual(run_mock.call_count, 1)
        provider.assert_called_once()
        authenticate.assert_called_once()
        integrated_out = integrate.call_args.args[0]
        self.assertEqual(integrated_out["verified_executable_skill"], verified_skill)
        self.assertTrue(integrated_out["verified_skill_reuse_authorized"])

    def test_plain_success_is_retained_as_adapter_work_without_promotion(self):
        path = self.temp_state()
        result = loop.record_success_observation(
            {"pass": True, "schema": "X", "status": "PASS", "value": 7},
            surface="TEST_SURFACE",
            state_path=path,
        )
        self.assertEqual(
            result["status"],
            "SUCCESS_OBSERVED__VERIFIABLE_EPISODE_ADAPTER_QUEUED",
        )
        self.assertFalse(result["permanent_reuse_authorized"])
        state = loop.load_state(path)
        self.assertEqual(state["stats"]["success_observation_count"], 1)
        self.assertEqual(state["stats"]["pending_improvement_count"], 1)
        self.assertEqual(
            loop.next_improvement_action(state_path=path)["kind"],
            "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE",
        )


    def test_success_observation_retains_digest_checked_replay_capsule(self):
        path = self.temp_state()
        replay_context = {
            "mode": "compiled_bound",
            "request": {
                "task_id": "success-replay",
                "initial_facts": ["seed"],
                "target_effects": ["goal"],
            },
            "learn": True,
        }
        result = loop.record_success_observation(
            {"pass": True, "schema": "X", "status": "PASS", "value": 9},
            surface="TEST_SURFACE",
            state_path=path,
            replay_context=replay_context,
        )
        self.assertTrue(result["replayable"])
        recovered = loop.get_success_replay_context(
            result["observation_id"],
            state_path=path,
        )
        self.assertEqual(recovered["context"], replay_context)
        self.assertTrue(recovered["replay_authorized"])
        self.assertEqual(
            recovered["replay_capsule_sha256"],
            result["replay_capsule_sha256"],
        )
        state = loop.load_state(path)
        work = loop.next_improvement_action(state_path=path)
        self.assertTrue(work["payload"]["replayable"])
        self.assertEqual(
            work["payload"]["replay_capsule_sha256"],
            result["replay_capsule_sha256"],
        )

    def test_success_observation_retains_bounded_digest_checked_proof_capsule(self):
        path = self.temp_state()
        out = {
            "pass": True,
            "schema": "PROJECT_BRAIN_LIVE_INTEGRATED_BRAIN_V1",
            "status": "PASS__REAL_TASK_PLANNED_EXECUTED_AND_REVERIFIED",
            "task_id": "proof-task",
            "selected_plan": ["cap.a"],
            "verified_target_effects": ["goal"],
            "execution": [{
                "capability_id": "cap.a",
                "pass": True,
                "status": "PASS",
                "composition_capsule_head_hash": "c" * 64,
                "result": {"private_payload": "must-not-be-copied"},
            }],
            "controller_checkpoint": {
                "path": "canonical/astra_runtime/state/proof.json",
                "plan_sha256": "a" * 64,
            },
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
        }
        result = loop.record_success_observation(
            out,
            surface="COMPILED_BOUND",
            state_path=path,
            replay_context={
                "mode": "compiled_bound",
                "request": {
                    "task_id": "proof-task",
                    "initial_facts": [],
                    "target_effects": ["goal"],
                },
                "learn": True,
            },
        )
        self.assertTrue(result["proof_available"])
        recovered = loop.get_success_proof_context(
            result["observation_id"],
            state_path=path,
        )
        self.assertEqual(
            recovered["proof_capsule_sha256"],
            result["proof_capsule_sha256"],
        )
        material = recovered["material"]
        self.assertEqual(material["selected_plan"], ["cap.a"])
        self.assertEqual(material["verified_target_effects"], ["goal"])
        self.assertNotIn("result", material["execution"][0])
        self.assertNotIn("private_payload", repr(material))

    def test_success_replay_capsule_rejects_sensitive_context(self):
        path = self.temp_state()
        with self.assertRaisesRegex(
            loop.SelfImprovementError,
            "RETRY_CONTEXT_SENSITIVE_KEY_REJECTED",
        ):
            loop.record_success_observation(
                {"pass": True, "schema": "X", "status": "PASS"},
                surface="TEST_SURFACE",
                state_path=path,
                replay_context={
                    "mode": "compiled_bound",
                    "request": {"task_id": "x", "api_key": "do-not-persist"},
                },
            )

    def test_post_execution_induces_cross_scope_candidate_from_exact_same_program(self):
        steps = [{"index": 0, "op": "solve", "inputs": [], "outputs": ["goal"]}]
        from canonical.runtime.executable_skill_program_v7 import program_digest
        digest = program_digest(
            steps=steps,
            preconditions=[],
            postconditions=["goal"],
            invalidators=[],
        )

        def episode(eid, scope):
            return {
                "episode_id": eid,
                "scope_id": scope,
                "steps": steps,
                "preconditions": [],
                "postconditions": ["goal"],
                "invalidators": [],
                "program_sha256": digest,
                "verification_receipt": {
                    "independent_verified": True,
                    "exact_byte_bound": True,
                    "conclusion": "success",
                    "behavior_verified": True,
                    "episode_id": eid,
                    "scope_id": scope,
                    "program_sha256": digest,
                    "receipt_id": "EPVR:" + eid,
                },
                "verification_binding": {
                    "receipt": {"path": "r-" + eid, "git_blob_sha": "1" * 40},
                    "verification": {"path": "v-" + eid, "git_blob_sha": "2" * 40},
                },
                "problem_sha256": "b" * 64,
                "trace_sha256": ("c" if eid == "prior" else "d") * 64,
                "fact_capsule_head_hash": "e" * 64,
                "value_capsule_head_hash": "f" * 64,
            }

        prior = episode("prior", "scope-a")
        current = episode("current", "scope-b")
        solved = {
            "pass": True,
            "status": "SOLVED__VERIFIED_EPISODE",
            "current_episode": current,
            "current_episode_verified": True,
            "trace": [],
            "skill_candidate": None,
            "verified_executable_skill": None,
        }

        provider = mock.Mock(return_value=None)
        with mock.patch.object(
            loop,
            "reauthenticate_episode_record",
            side_effect=lambda record, repo_root: {
                "pass": True,
                "authenticated_episode": record,
            },
        ):
            out = loop._post_execution_independent_verification(
                solved,
                problem={"task_id": "x"},
                prior_verified_episode_records=[],
                generalization_episode_records=[prior],
                repo_root=Path("."),
                skill_verification_provider=provider,
            )

        self.assertTrue(out["cross_scope_candidate_induced"], out)
        self.assertEqual(out["candidate_source_scopes"], ["scope-a", "scope-b"])
        candidate = out["skill_candidate"]
        self.assertEqual(candidate["source_scopes"], ["scope-a", "scope-b"])
        self.assertFalse(candidate["reuse_authorized"])
        provider.assert_called_once()
        self.assertEqual(
            provider.call_args.args[0]["candidate"]["source_scopes"],
            ["scope-a", "scope-b"],
        )

    def test_reuse_first_runner_forwards_retry_context_to_failure_integration(self):
        path = self.temp_state()
        failed = {
            "pass": False,
            "status": "FAIL_CLOSED__PROPOSAL_SEARCH_FAILED",
            "reason": "no proposal",
            "trace": [],
            "falsified_capability_ids": [],
            "deferred_capability_ids": [],
            "counterexamples": [],
            "attempts": [],
        }
        retry_context = {
            "mode": "generic",
            "problem": self._reuse_problem(),
            "scope_id": "scope",
            "episode_id": "ep3",
            "learn": True,
        }
        empty = loop._empty_state()
        with mock.patch.object(loop, "load_state", return_value=empty), \
             mock.patch.object(loop, "_select_active_skill", return_value=None), \
             mock.patch.object(loop.solver_v12, "run", return_value=failed), \
             mock.patch.object(
                 loop,
                 "integrate_solver_output",
                 return_value={
                     "status": "FAILURE_DIAGNOSED__REPAIR_QUEUED",
                     "pass": False,
                 },
             ) as integrate:
            out = loop.run_learning_episode(
                self._reuse_problem(),
                state_path=path,
                repo_root=Path("."),
                episode_id="ep3",
                scope_id="scope",
                retry_context=retry_context,
            )

        self.assertFalse(out["pass"])
        integrate.assert_called_once_with(
            failed,
            state_path=path,
            repo_root=Path("."),
            retry_context=retry_context,
            verification_problem=self._reuse_problem(),
            verification_effect_root=None,
        )


    def test_donor_provenance_survives_episode_to_later_candidate(self):
        state = loop._empty_state()
        ep = verified_episode("teacher-episode")
        key = loop._episode_key(ep)
        state["episodes"][key] = ep
        state["episode_provenance"][key] = {
            "used": True,
            "proposal_source_ids": ["teacher-model"],
            "capability_expansion_source_ids": [],
            "donor_role": "ACQUISITION_SOURCE_ONLY",
            "runtime_credit_authority": False,
            "transfer_gate_required_before_reuse": True,
        }
        candidate = {
            "candidate_sha256": "sha256:" + ("9" * 64),
            "source_episode_ids": ["teacher-episode"],
            "source_scopes": ["scope"],
            "postconditions": ["goal"],
        }
        provenance = loop._candidate_acquisition_donor_provenance(
            state, candidate, None
        )
        self.assertTrue(provenance["used"])
        self.assertEqual(provenance["proposal_source_ids"], ["teacher-model"])
        self.assertTrue(provenance["transfer_gate_required_before_reuse"])

    def test_donor_derived_candidate_blocks_verifier_until_transfer_gate_bound(self):
        path = self.temp_state()
        candidate_sha = "sha256:" + ("8" * 64)
        candidate = {
            "candidate_sha256": candidate_sha,
            "source_episode_ids": ["teacher-episode"],
            "source_scopes": ["scope"],
            "postconditions": ["goal"],
        }
        out = loop.integrate_solver_output(
            {
                "pass": True,
                "status": "SOLVED__SKILL_CANDIDATE_READY",
                "skill_candidate": candidate,
                "verified_executable_skill": None,
                "verified_skill_reuse_authorized": False,
                "acquisition_donor_provenance": {
                    "used": True,
                    "proposal_source_ids": ["teacher-model"],
                    "capability_expansion_source_ids": [],
                    "donor_role": "ACQUISITION_SOURCE_ONLY",
                    "runtime_credit_authority": False,
                    "transfer_gate_required_before_reuse": True,
                },
            },
            state_path=path,
        )
        self.assertEqual(
            out["status"],
            "SKILL_CANDIDATE_AWAITS_INDEPENDENT_VERIFICATION",
        )

        verifier = mock.Mock(side_effect=AssertionError("must not be called"))
        blocked = loop.advance_verification_queue(
            state_path=path,
            skill_verification_provider=verifier,
        )
        self.assertEqual(blocked["completed"], 0)
        self.assertEqual(
            blocked["results"][0]["status"],
            "BLOCKED__CAPABILITY_TRANSFER_GATE_REQUIRED",
        )
        verifier.assert_not_called()

        bound = loop.bind_capability_transfer_record(
            candidate_sha,
            valid_transfer_record(candidate_sha),
            state_path=path,
        )
        self.assertTrue(bound["pass"])
        self.assertFalse(bound["reuse_authority"])

        verifier = mock.Mock(return_value=None)
        after = loop.advance_verification_queue(
            state_path=path,
            skill_verification_provider=verifier,
        )
        self.assertEqual(
            after["results"][0]["status"],
            "BLOCKED__VERIFIER_RETURNED_NO_BINDING",
        )
        verifier.assert_called_once()

    def test_transfer_record_must_bind_exact_candidate_hash(self):
        path = self.temp_state()
        candidate_sha = "sha256:" + ("7" * 64)
        state = loop._empty_state()
        wid = "work:test-transfer"
        state["improvement_queue"][wid] = {
            "work_id": wid,
            "kind": "VERIFY_SKILL_CANDIDATE",
            "priority": 10,
            "identity": {"candidate_sha256": candidate_sha},
            "payload": {
                "candidate_sha256": candidate_sha,
                "candidate": {
                    "candidate_sha256": candidate_sha,
                    "source_episode_ids": [],
                    "source_scopes": ["scope"],
                    "postconditions": ["goal"],
                },
                "acquisition_donor_provenance": {
                    "used": True,
                    "proposal_source_ids": ["teacher-model"],
                    "capability_expansion_source_ids": [],
                },
            },
            "status": "PENDING",
            "observations": 1,
            "reopen_count": 0,
            "attempt_count": 0,
            "last_attempt_observations": None,
            "last_attempt_status": None,
            "last_attempt_reason": None,
        }
        path.write_text(json.dumps(state), encoding="utf-8")
        wrong = valid_transfer_record("sha256:" + ("6" * 64))
        with self.assertRaisesRegex(
            loop.SelfImprovementError,
            "CAPABILITY_TRANSFER_RECORD_CANDIDATE_MISMATCH",
        ):
            loop.bind_capability_transfer_record(
                candidate_sha,
                wrong,
                state_path=path,
            )

    def test_policy_adequacy_gap_is_not_collapsed_into_generic_semantics(self):
        out = loop._diagnose_failure({
            "pass": False,
            "status": "OPEN__POSITIVE_POLICY_ADEQUACY_COVERAGE_REQUIRED",
            "next_required_edge": "AUTHENTICATED_POSITIVE_POLICY_ADEQUACY_COVERAGE",
        })
        self.assertEqual(
            out["repair_class"],
            "SYNTHESIZE_OR_AUTHENTICATE_POLICY_ADEQUACY_COVER",
        )
        self.assertEqual(
            out["next_required_edge"],
            "AUTHENTICATED_POSITIVE_POLICY_ADEQUACY_COVERAGE",
        )

    def test_policy_changing_observation_gap_remains_information_acquisition(self):
        out = loop._diagnose_failure({
            "pass": False,
            "status": "OPEN__POLICY_COVER_OBSERVATION_BINDING_REQUIRED",
            "next_required_edge": "AUTHENTICATED_SELECTED_POLICY_CHANGING_OBSERVATION",
        })
        self.assertEqual(
            out["repair_class"],
            "RESOLVE_MINIMUM_BLOCKING_INFORMATION_AND_RETRY",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
