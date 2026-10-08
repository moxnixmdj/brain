from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_improvement_queue_driver_v1 as driver


class R3ImprovementQueueDriverTests(unittest.TestCase):
    def temp_state(self) -> Path:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        return Path(td.name) / "state.json"

    def write_state(self, path: Path, queue: dict) -> None:
        state = learning._empty_state()
        state["improvement_queue"] = queue
        learning._refresh_stats(state)
        learning._write_state(state, path)

    def test_blocked_higher_priority_work_does_not_starve_actionable_repair(self):
        path = self.temp_state()
        self.write_state(
            path,
            {
                "skill": {
                    "work_id": "skill",
                    "kind": "VERIFY_SKILL_CANDIDATE",
                    "priority": 10,
                    "identity": {},
                    "payload": {},
                    "status": "PENDING",
                    "observations": 1,
                    "reopen_count": 0,
                },
                "repair": {
                    "work_id": "repair",
                    "kind": "REPAIR_FAILURE_CLASS",
                    "priority": 30,
                    "identity": {},
                    "payload": {"failure_fingerprint": "f", "retry_capsule_sha256": "r"},
                    "status": "PENDING",
                    "observations": 1,
                    "reopen_count": 0,
                },
            },
        )
        repair = mock.Mock(return_value={"pass": True, "status": "REPAIRED"})
        out = driver.advance_once(state_path=path, failure_repair_provider=repair)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"], out)
        self.assertEqual(out["work_id"], "repair")
        self.assertEqual(
            out["blockers_skipped"][0]["blocker"],
            "LEGACY_SKILL_VERIFICATION_MATERIAL_INCOMPLETE",
        )
        repair.assert_called_once()

    def test_owned_independent_episode_verifier_is_default_when_host_provider_missing(self):
        path = self.temp_state()
        episode = {
            "episode_id": "ep",
            "scope_id": "scope",
            "steps": [{"index": 0, "op": "x", "inputs": [], "outputs": ["goal"]}],
            "preconditions": [],
            "postconditions": ["goal"],
            "invalidators": [],
            "program_sha256": "sha256:" + "a" * 64,
        }
        self.write_state(
            path,
            {
                "episode": {
                    "work_id": "episode",
                    "kind": "VERIFY_EPISODE",
                    "priority": 20,
                    "identity": {},
                    "payload": {
                        "episode": episode,
                        "problem": {
                            "task_id": "t",
                            "initial_facts": [],
                            "target_effects": ["goal"],
                            "capabilities": [],
                        },
                        "trace": [],
                        "fact_capsule_head_hash": "f" * 64,
                        "value_capsule_head_hash": "v" * 64,
                    },
                    "status": "PENDING",
                    "observations": 1,
                    "reopen_count": 0,
                }
            },
        )
        binding = {"receipt": {"path": "x", "git_blob_sha": "x"}}
        with (
            mock.patch(
                "canonical.runtime.r3_independent_learning_verifier_v1.verify_episode_request",
                return_value=binding,
            ) as owned_verifier,
            mock.patch.object(
                driver,
                "_verify_episode_work",
                return_value={
                    "schema": driver.SCHEMA,
                    "status": "IMPROVEMENT_ADVANCED__EPISODE_VERIFIED",
                    "pass": True,
                    "work_id": "episode",
                    "terminal_authority": False,
                },
            ) as verify_work,
        ):
            out = driver.advance_once(state_path=path)
            provider = verify_work.call_args.kwargs["episode_verification_provider"]
            self.assertEqual(provider({"kind": "EPISODE_VERIFICATION"}), binding)
            owned_verifier.assert_called_once()

        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"], out)

    def test_delayed_episode_worker_forwards_retained_effect_root(self):
        path = self.temp_state()
        learning._write_state(learning._empty_state(), path)
        work = {
            "work_id": "episode-effect",
            "kind": "VERIFY_EPISODE",
            "payload": {
                "episode": {
                    "episode_id": "ep",
                    "scope_id": "scope",
                    "steps": [{"op": "x", "inputs": [], "outputs": ["goal"]}],
                    "preconditions": [],
                    "postconditions": ["goal"],
                    "invalidators": [],
                    "program_sha256": "sha256:" + "a" * 64,
                },
                "problem": {
                    "task_id": "t",
                    "initial_facts": [],
                    "target_effects": ["goal"],
                    "capabilities": [],
                },
                "trace": [],
                "fact_capsule_head_hash": "f" * 64,
                "value_capsule_head_hash": "v" * 64,
                "effect_root": "/private/effect-root",
            },
        }
        with mock.patch.object(
            learning,
            "_post_execution_independent_verification",
            return_value={
                "current_episode_verified": False,
                "post_execution_episode_verification_error": "expected-test-stop",
            },
        ) as verify:
            out = driver._verify_episode_work(
                work,
                state_path=path,
                repo_root=driver.ROOT,
                episode_verification_provider=object(),
                skill_verification_provider=None,
            )
        self.assertFalse(out["pass"], out)
        self.assertEqual(
            verify.call_args.kwargs["effect_root"],
            "/private/effect-root",
        )

    def test_repair_queue_uses_internal_verified_repair_cycle_without_injected_provider(self):
        path = self.temp_state()
        self.write_state(
            path,
            {
                "repair": {
                    "work_id": "repair",
                    "kind": "REPAIR_FAILURE_CLASS",
                    "priority": 30,
                    "identity": {},
                    "payload": {
                        "failure_fingerprint": "f",
                        "retry_capsule_sha256": "r",
                    },
                    "status": "PENDING",
                    "observations": 1,
                    "reopen_count": 0,
                }
            },
        )
        with mock.patch.object(
            driver,
            "_internal_failure_repair",
            return_value={"pass": True, "status": "REPAIR_VERIFIED_BY_ORIGINAL_OBLIGATION_REPLAY"},
        ) as repair:
            out = driver.advance_once(state_path=path)

        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"], out)
        self.assertEqual(
            out["status"],
            "IMPROVEMENT_ADVANCED__FAILURE_REPAIR_REPLAY_VERIFIED",
        )
        repair.assert_called_once()
        self.assertEqual(repair.call_args.kwargs["state_path"], path)

    def test_internal_repair_marks_replay_as_autonomous(self):
        path = self.temp_state()
        work = {
            "work_id": "repair",
            "kind": "REPAIR_FAILURE_CLASS",
            "payload": {
                "failure_fingerprint": "f",
                "retry_capsule_sha256": "r",
            },
        }
        with mock.patch(
            "canonical.runtime.live_brain_runtime_v1.execute_failure_repair_cycle",
            return_value={"pass": False, "status": "BLOCKED"},
        ) as repair:
            driver._internal_failure_repair(
                work,
                state_path=path,
                repo_root=driver.ROOT,
            )

        request = repair.call_args.args[0]
        self.assertTrue(request["autonomous"])
        self.assertEqual(request["failure_fingerprint"], "f")
        self.assertEqual(request["retry_capsule_sha256"], "r")

    def test_failed_internal_repair_is_not_retried_until_new_evidence(self):
        path = self.temp_state()
        self.write_state(
            path,
            {
                "repair": {
                    "work_id": "repair",
                    "kind": "REPAIR_FAILURE_CLASS",
                    "priority": 30,
                    "identity": {},
                    "payload": {
                        "failure_fingerprint": "f",
                        "retry_capsule_sha256": "r",
                    },
                    "status": "PENDING",
                    "observations": 1,
                    "reopen_count": 0,
                    "attempt_count": 0,
                    "last_attempt_observations": None,
                    "last_attempt_status": None,
                    "last_attempt_reason": None,
                }
            },
        )
        with mock.patch.object(
            driver,
            "_internal_failure_repair",
            return_value={
                "pass": False,
                "status": "AUTONOMOUS_REPAIR_BLOCKED__REPLAY_NOT_PROVED_SAFE",
                "autonomous_replay_reason": "unsafe",
            },
        ) as repair:
            first = driver.advance_once(state_path=path)
            second = driver.advance_once(state_path=path)

        self.assertFalse(first["pass"], first)
        self.assertFalse(first["progress"], first)
        self.assertTrue(second["pass"], second)
        self.assertFalse(second["progress"], second)
        self.assertEqual(
            second["blockers"][0]["blocker"],
            "WORK_ALREADY_ATTEMPTED_FOR_CURRENT_EVIDENCE",
        )
        repair.assert_called_once()
        state = learning.load_state(path)
        row = state["improvement_queue"]["repair"]
        self.assertEqual(row["attempt_count"], 1)
        self.assertEqual(row["last_attempt_observations"], 1)

        row["observations"] = 2
        learning._write_state(state, path)
        with mock.patch.object(
            driver,
            "_internal_failure_repair",
            return_value={"pass": True, "status": "REPAIRED"},
        ) as repair_after_new_evidence:
            third = driver.advance_once(state_path=path)
        self.assertTrue(third["pass"], third)
        self.assertTrue(third["progress"], third)
        repair_after_new_evidence.assert_called_once()

    def test_failed_skill_verification_retries_only_after_new_evidence(self):
        path = self.temp_state()
        candidate = {
            "candidate_sha256": "sha256:" + "f" * 64,
            "source_episode_ids": ["ep-1", "ep-2"],
            "source_scopes": ["scope-a"],
            "steps": [{"index": 0, "op": "solve", "inputs": [], "outputs": ["goal"]}],
            "preconditions": [],
            "postconditions": ["goal"],
            "invalidators": [],
            "candidate_only": True,
            "verified_skill": False,
            "reuse_authorized": False,
        }
        identity = {"candidate_sha256": candidate["candidate_sha256"]}
        payload = {"candidate": candidate}
        state = learning._empty_state()
        learning._enqueue_improvement(
            state,
            kind="VERIFY_SKILL_CANDIDATE",
            priority=10,
            identity=identity,
            payload=payload,
        )
        learning._refresh_stats(state)
        learning._write_state(state, path)

        provider = mock.Mock(return_value=None)
        first = driver.advance_once(
            state_path=path,
            skill_verification_provider=provider,
        )
        second = driver.advance_once(
            state_path=path,
            skill_verification_provider=provider,
        )

        self.assertFalse(first["pass"], first)
        self.assertTrue(first["attempt_backoff_recorded"], first)
        self.assertEqual(
            first["status"],
            "IMPROVEMENT_PROVIDER_RETURNED_NO_SKILL_BINDING",
        )
        self.assertTrue(second["pass"], second)
        self.assertFalse(second["progress"], second)
        self.assertEqual(
            second["blockers"][0]["blocker"],
            "WORK_ALREADY_ATTEMPTED_FOR_CURRENT_EVIDENCE",
        )
        self.assertEqual(provider.call_count, 1)

        state = learning.load_state(path)
        learning._enqueue_improvement(
            state,
            kind="VERIFY_SKILL_CANDIDATE",
            priority=10,
            identity=identity,
            payload=payload,
        )
        learning._refresh_stats(state)
        learning._write_state(state, path)

        third = driver.advance_once(
            state_path=path,
            skill_verification_provider=provider,
        )
        self.assertFalse(third["pass"], third)
        self.assertTrue(third["attempt_backoff_recorded"], third)
        self.assertEqual(provider.call_count, 2)

    def test_failed_verifier_work_does_not_starve_unrelated_queue_items(self):
        path = self.temp_state()
        candidate = {
            "candidate_sha256": "sha256:" + "e" * 64,
            "source_episode_ids": ["ep-1", "ep-2"],
            "source_scopes": ["scope-a"],
            "steps": [{"index": 0, "op": "solve", "inputs": [], "outputs": ["goal"]}],
            "preconditions": [],
            "postconditions": ["goal"],
            "invalidators": [],
            "candidate_only": True,
            "verified_skill": False,
            "reuse_authorized": False,
        }
        state = learning._empty_state()
        learning._enqueue_improvement(
            state,
            kind="VERIFY_SKILL_CANDIDATE",
            priority=10,
            identity={"candidate_sha256": candidate["candidate_sha256"]},
            payload={"candidate": candidate},
        )
        learning._enqueue_improvement(
            state,
            kind="REPAIR_FAILURE_CLASS",
            priority=30,
            identity={"failure_fingerprint": "failure"},
            payload={
                "failure_fingerprint": "failure",
                "retry_capsule_sha256": "retry",
            },
        )
        learning._refresh_stats(state)
        learning._write_state(state, path)

        verifier = mock.Mock(return_value=None)
        repair = mock.Mock(return_value={"pass": True, "status": "REPAIRED"})
        out = driver.drain(
            state_path=path,
            skill_verification_provider=verifier,
            failure_repair_provider=repair,
            max_actions=2,
        )

        self.assertEqual(verifier.call_count, 1)
        repair.assert_called_once()
        self.assertEqual(out["progress_count"], 1, out)
        self.assertGreaterEqual(len(out["actions"]), 2)
        self.assertTrue(out["actions"][0]["attempt_backoff_recorded"])
        self.assertEqual(out["actions"][1]["work_id"], next(
            row["work_id"]
            for row in learning.load_state(path)["improvement_queue"].values()
            if row.get("kind") == "REPAIR_FAILURE_CLASS"
        ))

    def test_delayed_episode_queue_retains_exact_verification_material(self):
        path = self.temp_state()
        episode = {
            "episode_id": "ep",
            "scope_id": "scope",
            "program_sha256": "sha256:p",
            "trace_sha256": "sha256:t",
        }
        problem = {
            "task_id": "task",
            "initial_facts": [],
            "target_effects": ["goal"],
            "capabilities": [],
        }
        out = {
            "pass": True,
            "current_episode": episode,
            "current_episode_verified": False,
            "trace": [{"capability_id": "c"}],
            "state_capsule_head_hash": "fact",
            "value_capsule_head_hash": "value",
        }
        learning.integrate_solver_output(
            out,
            state_path=path,
            verification_problem=problem,
            verification_effect_root="/secure/effect-root",
        )
        state = learning.load_state(path)
        work = next(
            row
            for row in state["improvement_queue"].values()
            if row["kind"] == "VERIFY_EPISODE"
        )
        self.assertEqual(work["payload"]["episode"], episode)
        self.assertEqual(work["payload"]["problem"], problem)
        self.assertEqual(work["payload"]["trace"], out["trace"])
        self.assertEqual(work["payload"]["fact_capsule_head_hash"], "fact")
        self.assertEqual(work["payload"]["value_capsule_head_hash"], "value")
        self.assertEqual(work["payload"]["effect_root"], "/secure/effect-root")

    def test_scope_generalization_runs_through_canonical_driver(self):
        path = self.temp_state()
        verified_skill = {
            "schema": "PROJECT_BRAIN_EXECUTABLE_SKILL_PROGRAM_V7",
            "status": "VERIFIED_EXECUTABLE_SKILL",
            "source_episode_ids": ["ep-1", "ep-2"],
            "source_scopes": ["scope-a"],
            "steps": [{"index": 0, "op": "solve", "inputs": [], "outputs": ["goal"]}],
            "preconditions": [],
            "postconditions": ["goal"],
            "invalidators": [],
            "candidate_sha256": "sha256:" + "7" * 64,
            "verified_skill": True,
            "reuse_authorized": True,
            "candidate_only": False,
            "scope_relation": "EXACT",
            "verification_receipt": "SKVR:old",
        }
        sid = learning._skill_id(verified_skill)
        family = learning._family_id(verified_skill)
        state = learning._empty_state()
        state["skills"][sid] = {
            "skill": verified_skill,
            "family_id": family,
            "pareto_metrics": learning._skill_pareto_row(sid, verified_skill),
            "active": True,
            "dominated_by": None,
            "compression": {},
        }
        state["pareto_frontiers"][family] = [sid]
        learning._enqueue_improvement(
            state,
            kind="SEEK_VERIFIED_SCOPE_GENERALIZATION",
            priority=60,
            identity={"family_id": family, "skill_id": sid},
            payload={
                "family_id": family,
                "skill_id": sid,
                "source_scopes": ["scope-a"],
                "postconditions": ["goal"],
                "required_result": "INDEPENDENTLY_VERIFIED_PROVEN_SUPERSET_SKILL",
            },
        )
        learning._refresh_stats(state)
        learning._write_state(state, path)

        promoted = {
            **verified_skill,
            "scope_relation": "PROVEN_SUPERSET",
            "scope_predicate": learning.VERIFIED_SUPERSET_SCOPE_PREDICATE,
            "verification_receipt": "SKVR:new",
        }
        provider = mock.Mock(return_value={"binding": "content-addressed"})
        with (
            mock.patch.object(
                driver.learning,
                "reauthenticate_skill_record",
                return_value={"pass": True, "verified_skill": verified_skill},
            ),
            mock.patch.object(
                driver,
                "authenticate_skill_verification",
                return_value={"pass": True, "verified_skill": promoted},
            ),
            mock.patch.object(
                driver.learning,
                "integrate_solver_output",
                return_value={
                    "pass": True,
                    "status": "VERIFIED_SKILL_PERMANENTLY_ADMITTED_FOR_REUSE",
                    "active_skill_id": sid,
                },
            ) as integrate,
        ):
            out = driver.advance_once(
                state_path=path,
                skill_verification_provider=provider,
            )

        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"], out)
        self.assertEqual(
            out["status"],
            "IMPROVEMENT_ADVANCED__SCOPE_GENERALIZATION_VERIFIED_AND_PARETO_ADJUDICATED",
        )
        request = provider.call_args.args[0]
        self.assertEqual(
            request["kind"],
            "SKILL_SCOPE_GENERALIZATION_VERIFICATION",
        )
        self.assertEqual(request["requested_scope_relation"], "PROVEN_SUPERSET")
        self.assertEqual(
            request["requested_scope_predicate"],
            learning.VERIFIED_SUPERSET_SCOPE_PREDICATE,
        )
        self.assertTrue(request["candidate"]["candidate_only"])
        self.assertNotIn("scope_relation", request["candidate"])
        integrate.assert_called_once()

    def test_scope_generalization_rejects_unauthenticated_source_before_provider(self):
        path = self.temp_state()
        skill = {
            "candidate_sha256": "sha256:" + "3" * 64,
            "source_episode_ids": ["ep1", "ep2"],
            "source_scopes": ["scope-a"],
            "steps": [{"index": 0, "op": "solve", "inputs": [], "outputs": ["goal"]}],
            "preconditions": [],
            "postconditions": ["goal"],
            "invalidators": [],
            "verified_skill": True,
            "reuse_authorized": True,
            "candidate_only": False,
            "scope_relation": "EXACT",
        }
        sid = learning._skill_id(skill)
        family = learning._family_id(skill)
        state = learning._empty_state()
        state["skills"][sid] = {
            "skill": skill,
            "family_id": family,
            "pareto_metrics": learning._skill_pareto_row(sid, skill),
            "active": True,
            "dominated_by": None,
            "compression": {},
        }
        learning._enqueue_improvement(
            state,
            kind="SEEK_VERIFIED_SCOPE_GENERALIZATION",
            priority=60,
            identity={"family_id": family, "skill_id": sid},
            payload={"family_id": family, "skill_id": sid},
        )
        learning._refresh_stats(state)
        learning._write_state(state, path)

        provider = mock.Mock()
        with mock.patch.object(
            driver.learning,
            "reauthenticate_skill_record",
            return_value={"pass": False, "reason": "TAMPERED"},
        ):
            out = driver.advance_once(
                state_path=path,
                skill_verification_provider=provider,
            )

        self.assertFalse(out["pass"], out)
        self.assertEqual(
            out["status"],
            "SCOPE_GENERALIZATION_SOURCE_SKILL_AUTHORITY_INVALID",
        )
        provider.assert_not_called()

    def test_default_success_adapter_parks_current_evidence_without_permanent_claim(self):
        path = self.temp_state()
        observed = learning.record_success_observation(
            {
                "schema": "TEST_SUCCESS_V1",
                "status": "PASS__OPAQUE_EXTERNAL_SUCCESS",
                "pass": True,
                "result": {"opaque": True},
            },
            surface="OPAQUE_EXTERNAL_SURFACE",
            state_path=path,
            replay_context={
                "mode": "generic",
                "problem": {"task_id": "opaque-success"},
            },
        )

        out = driver.advance_once(state_path=path)
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["progress"], out)
        self.assertTrue(out["disposition_recorded"], out)
        self.assertEqual(
            out["status"],
            "IMPROVEMENT_PARKED__CURRENT_OWNED_VERIFICATION_FRONTIER_INCOMPLETE",
        )
        self.assertFalse(out["epistemic_nonlearnability_proved"])
        self.assertFalse(out["observational_inseparability_proved"])
        self.assertTrue(out["frontier_expansion_required"])
        self.assertFalse(out["permanent_nonlearnability_claimed"])

        state = learning.load_state(path)
        row = state["improvement_queue"][observed["improvement_work_id"]]
        self.assertEqual(row["status"], "PARKED")
        self.assertEqual(
            row["parked_reason"],
            "NO_CURRENT_OWNED_VERIFICATION_PATH",
        )
        self.assertFalse(row["epistemic_nonlearnability_proved"])
        self.assertFalse(row["observational_inseparability_proved"])
        self.assertTrue(row["frontier_expansion_required"])
        self.assertEqual(len(row["adapter_frontier_sha256"]), 64)
        self.assertEqual(len(row["verification_authority_sha256"]), 64)
        observation = state["observations"][observed["observation_id"]]
        self.assertEqual(
            observation["learning_disposition"],
            "UNRESOLVED_WITH_CURRENT_OWNED_VERIFICATION_FRONTIER",
        )
        self.assertFalse(observation["epistemic_nonlearnability_proved"])
        self.assertFalse(observation["observational_inseparability_proved"])
        self.assertTrue(observation["frontier_expansion_required"])
        self.assertFalse(observation["permanent_nonlearnability_claimed"])
        self.assertEqual(state["stats"]["pending_improvement_count"], 1)
        self.assertEqual(state["stats"]["parked_success_learning_count"], 1)
        expansion_id = row["frontier_expansion_work_id"]
        expansion = state["improvement_queue"][expansion_id]
        self.assertEqual(expansion["kind"], driver.FRONTIER_EXPANSION_KIND)
        self.assertEqual(expansion["status"], "PENDING")
        self.assertEqual(
            expansion["payload"]["boundary_root"],
            "R1_CAPABILITY_ACQUISITION",
        )
        self.assertEqual(
            expansion["payload"]["required_capability_class"],
            "INDEPENDENT_READONLY_SUCCESS_VERIFIER_OR_ADAPTER",
        )
        self.assertFalse(expansion["payload"]["replay_original_success"])
        self.assertFalse(expansion["payload"]["promotion_authority"])
        self.assertEqual(
            expansion["payload"]["adapter_frontier_sha256"],
            row["adapter_frontier_sha256"],
        )
        self.assertEqual(
            expansion["payload"]["verification_authority_sha256"],
            row["verification_authority_sha256"],
        )

    def test_missing_owned_adapter_is_not_labeled_information_theoretic_impossibility(self):
        path = self.temp_state()
        observed = learning.record_success_observation(
            {
                "schema": "TEST_SUCCESS_V1",
                "status": "PASS__EVIDENCE_EXISTS_BUT_NO_OWNED_ADAPTER",
                "pass": True,
                "result": {"receipt_like_evidence": "present"},
            },
            surface="UNSUPPORTED_BUT_OBSERVABLE_SURFACE",
            state_path=path,
            replay_context={
                "mode": "generic",
                "problem": {"task_id": "frontier-gap-not-theorem"},
            },
        )

        out = driver.advance_once(state_path=path)
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["progress"], out)
        self.assertTrue(out["frontier_expansion_required"], out)
        self.assertFalse(out["epistemic_nonlearnability_proved"], out)
        self.assertFalse(out["observational_inseparability_proved"], out)

        state = learning.load_state(path)
        observation = state["observations"][observed["observation_id"]]
        self.assertNotEqual(
            observation["learning_disposition"],
            "PROVED_NONLEARNABLE_FROM_CURRENT_RETAINED_EVIDENCE",
        )
        self.assertEqual(
            observation["learning_disposition"],
            "UNRESOLVED_WITH_CURRENT_OWNED_VERIFICATION_FRONTIER",
        )

    def test_frontier_expansion_handoff_waits_without_replaying_success(self):
        path = self.temp_state()
        observed = learning.record_success_observation(
            {
                "schema": "TEST_SUCCESS_V1",
                "status": "PASS__OPAQUE_EXTERNAL_SUCCESS",
                "pass": True,
                "result": {"opaque": True},
            },
            surface="OPAQUE_EXTERNAL_SURFACE",
            state_path=path,
            replay_context={
                "mode": "generic",
                "problem": {"task_id": "frontier-handoff"},
            },
        )
        first = driver.advance_once(state_path=path)
        self.assertTrue(first["disposition_recorded"], first)

        second = driver.advance_once(state_path=path)
        self.assertTrue(second["pass"], second)
        self.assertFalse(second["progress"], second)
        blocker = next(
            row
            for row in second["blockers"]
            if row["kind"] == driver.FRONTIER_EXPANSION_KIND
        )
        self.assertEqual(
            blocker["blocker"],
            "ROOT1_VERIFICATION_CAPABILITY_ACQUISITION_REQUIRED",
        )
        self.assertEqual(blocker["boundary_root"], "R1_CAPABILITY_ACQUISITION")
        self.assertFalse(blocker["replay_original_success"])

        state = learning.load_state(path)
        parked = state["improvement_queue"][observed["improvement_work_id"]]
        expansion = state["improvement_queue"][parked["frontier_expansion_work_id"]]
        self.assertEqual(expansion["status"], "PENDING")
        self.assertFalse(expansion["payload"]["candidate_generation_authority"])
        self.assertFalse(expansion["payload"]["promotion_authority"])

    def test_frontier_acquisition_provider_may_expand_adapter_only_when_authority_unchanged(self):
        path = self.temp_state()
        observed = learning.record_success_observation(
            {
                "schema": "TEST_SUCCESS_V1",
                "status": "PASS__OPAQUE_EXTERNAL_SUCCESS",
                "pass": True,
                "result": {"opaque": True},
            },
            surface="OPAQUE_EXTERNAL_SURFACE",
            state_path=path,
            replay_context={
                "mode": "generic",
                "problem": {"task_id": "frontier-executable-handoff"},
            },
        )
        parked = driver.advance_once(state_path=path)
        self.assertTrue(parked["disposition_recorded"], parked)
        state = learning.load_state(path)
        parked_row = state["improvement_queue"][observed["improvement_work_id"]]
        old_frontier = parked_row["verification_frontier_sha256"]
        old_adapter = parked_row["adapter_frontier_sha256"]
        old_authority = parked_row["verification_authority_sha256"]
        new_frontier = "f" * 64
        new_adapter = "a" * 64
        phase = {"after": False}

        def acquire(_request):
            phase["after"] = True
            return {"pass": True, "status": "ROOT1_SUCCESS_ADAPTER_INSTALLED"}

        provider = mock.Mock(side_effect=acquire)
        activation = {
            "schema": driver.SCHEMA,
            "status": "SUCCESS_ADAPTER_FRONTIER_ACTIVATED__VERIFICATION_AUTHORITY_UNCHANGED",
            "pass": True,
            "adapter_frontier_sha256": new_adapter,
            "verification_authority_sha256": old_authority,
            "activated_module_bindings": [],
            "terminal_authority": False,
        }
        with (
            mock.patch.object(
                driver,
                "_owned_success_learning_frontier_sha256",
                side_effect=lambda **_: (
                    new_frontier if phase["after"] else old_frontier
                ),
            ),
            mock.patch.object(
                driver,
                "_owned_success_adapter_frontier_sha256",
                side_effect=lambda **_: (
                    new_adapter if phase["after"] else old_adapter
                ),
            ),
            mock.patch.object(
                driver,
                "_owned_success_verification_authority_sha256",
                return_value=old_authority,
            ),
            mock.patch.object(
                driver,
                "_activate_owned_success_adapter_frontier",
                return_value=activation,
            ) as activate,
        ):
            out = driver.advance_once(
                state_path=path,
                verification_frontier_acquisition_provider=provider,
                verification_frontier_acquisition_provider_id="root1-worker-v1",
            )

        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"], out)
        self.assertEqual(
            out["status"],
            "IMPROVEMENT_ADVANCED__SUCCESS_ADAPTER_FRONTIER_EXPANDED_AND_SUCCESS_REOPENED",
        )
        self.assertTrue(out["verification_authority_unchanged"])
        provider.assert_called_once()
        request = provider.call_args.args[0]
        self.assertEqual(
            request["allowed_frontier_change_class"],
            "SUCCESS_ADAPTER_ONLY__VERIFICATION_AUTHORITY_IMMUTABLE",
        )
        self.assertFalse(request["verification_authority_change_allowed"])
        self.assertEqual(request["verification_authority_sha256"], old_authority)
        activate.assert_called_once_with(
            expected_adapter_frontier_sha256=new_adapter,
            expected_verification_authority_sha256=old_authority,
            repo_root=driver.ROOT,
        )
        self.assertEqual(
            out["frontier_activation"]["status"],
            "SUCCESS_ADAPTER_FRONTIER_ACTIVATED__VERIFICATION_AUTHORITY_UNCHANGED",
        )

        state = learning.load_state(path)
        reopened = state["improvement_queue"][observed["improvement_work_id"]]
        self.assertEqual(reopened["status"], "PENDING")
        self.assertEqual(
            reopened["reactivated_by"],
            "OWNED_SUCCESS_ADAPTER_FRONTIER_CHANGED__AUTHORITY_UNCHANGED",
        )
        expansion = state["improvement_queue"][
            parked_row["frontier_expansion_work_id"]
        ]
        self.assertEqual(expansion["status"], "RESOLVED")

    def test_frontier_acquisition_provider_cannot_self_certify_without_byte_change(self):
        path = self.temp_state()
        observed = learning.record_success_observation(
            {
                "schema": "TEST_SUCCESS_V1",
                "status": "PASS__OPAQUE_EXTERNAL_SUCCESS",
                "pass": True,
                "result": {"opaque": True},
            },
            surface="OPAQUE_EXTERNAL_SURFACE",
            state_path=path,
            replay_context={
                "mode": "generic",
                "problem": {"task_id": "frontier-no-self-cert"},
            },
        )
        driver.advance_once(state_path=path)
        state = learning.load_state(path)
        parked_row = state["improvement_queue"][observed["improvement_work_id"]]
        frontier = parked_row["verification_frontier_sha256"]
        provider = mock.Mock(return_value={"pass": True, "status": "CLAIMS_DONE"})

        adapter = parked_row["adapter_frontier_sha256"]
        authority = parked_row["verification_authority_sha256"]
        with (
            mock.patch.object(
                driver,
                "_owned_success_learning_frontier_sha256",
                return_value=frontier,
            ),
            mock.patch.object(
                driver,
                "_owned_success_adapter_frontier_sha256",
                return_value=adapter,
            ),
            mock.patch.object(
                driver,
                "_owned_success_verification_authority_sha256",
                return_value=authority,
            ),
        ):
            first = driver.advance_once(
                state_path=path,
                verification_frontier_acquisition_provider=provider,
                verification_frontier_acquisition_provider_id="root1-worker-v1",
            )
            second = driver.advance_once(
                state_path=path,
                verification_frontier_acquisition_provider=provider,
                verification_frontier_acquisition_provider_id="root1-worker-v1",
            )

        self.assertFalse(first["pass"], first)
        self.assertFalse(first["progress"], first)
        self.assertTrue(first["attempt_backoff_recorded"], first)
        self.assertEqual(
            first["status"],
            "FRONTIER_ACQUISITION_DID_NOT_CHANGE_OWNED_SUCCESS_ADAPTER_FRONTIER",
        )
        self.assertTrue(second["pass"], second)
        self.assertFalse(second["progress"], second)
        self.assertEqual(provider.call_count, 1)
        blocker = next(
            row for row in second["blockers"]
            if row["kind"] == driver.FRONTIER_EXPANSION_KIND
        )
        self.assertEqual(
            blocker["blocker"],
            "FRONTIER_ACQUISITION_ALREADY_ATTEMPTED_FOR_CURRENT_PROVIDER_AND_FRONTIER",
        )

    def test_owned_frontier_module_origin_accepts_exact_repo_file(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        relative = "canonical/runtime/r3_bound_success_adapter_v1.py"
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# exact frontier module\n", encoding="utf-8")
        module = mock.Mock()
        module.__file__ = str(target)
        module.__name__ = "canonical.runtime.r3_bound_success_adapter_v1"

        out = driver._assert_owned_success_module_origin(
            module,
            relative_path=relative,
            repo_root=root,
        )

        self.assertEqual(out["relative_path"], relative)
        self.assertEqual(out["origin"], str(target.resolve()))

    def test_owned_frontier_module_origin_rejects_different_checkout(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name) / "expected"
        other = Path(td.name) / "other"
        relative = "canonical/runtime/r3_bound_success_adapter_v1.py"
        expected = root / relative
        actual = other / relative
        expected.parent.mkdir(parents=True, exist_ok=True)
        actual.parent.mkdir(parents=True, exist_ok=True)
        expected.write_text("# expected\n", encoding="utf-8")
        actual.write_text("# wrong checkout\n", encoding="utf-8")
        module = mock.Mock()
        module.__file__ = str(actual)
        module.__name__ = "canonical.runtime.r3_bound_success_adapter_v1"

        with self.assertRaisesRegex(
            driver.ImprovementDriverError,
            "SUCCESS_FRONTIER_MODULE_ORIGIN_MISMATCH",
        ):
            driver._assert_owned_success_module_origin(
                module,
                relative_path=relative,
                repo_root=root,
            )

    def test_owned_adapter_frontier_change_must_activate_before_reopen(self):
        path = self.temp_state()
        observed = learning.record_success_observation(
            {
                "schema": "TEST_SUCCESS_V1",
                "status": "PASS__OPAQUE_EXTERNAL_SUCCESS",
                "pass": True,
                "result": {"opaque": True},
            },
            surface="OPAQUE_EXTERNAL_SURFACE",
            state_path=path,
            replay_context={
                "mode": "generic",
                "problem": {"task_id": "frontier-activation-required"},
            },
        )
        driver.advance_once(state_path=path)
        state = learning.load_state(path)
        parked = state["improvement_queue"][observed["improvement_work_id"]]
        old_frontier = parked["verification_frontier_sha256"]
        old_adapter = parked["adapter_frontier_sha256"]
        authority = parked["verification_authority_sha256"]
        new_frontier = "e" * 64
        new_adapter = "c" * 64

        with (
            mock.patch.object(
                driver,
                "_owned_success_learning_frontier_sha256",
                return_value=new_frontier,
            ),
            mock.patch.object(
                driver,
                "_owned_success_adapter_frontier_sha256",
                return_value=new_adapter,
            ),
            mock.patch.object(
                driver,
                "_owned_success_verification_authority_sha256",
                return_value=authority,
            ),
            mock.patch.object(
                driver,
                "_activate_owned_success_adapter_frontier",
                side_effect=RuntimeError("activation failed"),
            ) as activate,
        ):
            out = driver._reactivate_parked_successes(
                state_path=path,
                repo_root=driver.ROOT,
                external_authority_available=False,
            )

        activate.assert_called_once_with(
            expected_adapter_frontier_sha256=new_adapter,
            expected_verification_authority_sha256=authority,
            repo_root=driver.ROOT,
        )
        self.assertEqual(out["reopened_work_ids"], [])
        self.assertFalse(out["frontier_activation"]["pass"])
        state = learning.load_state(path)
        row = state["improvement_queue"][observed["improvement_work_id"]]
        self.assertEqual(row["status"], "PARKED")
        self.assertEqual(row["verification_frontier_sha256"], old_frontier)
        self.assertEqual(row["adapter_frontier_sha256"], old_adapter)

    def test_owned_adapter_frontier_change_reloads_then_reopens(self):
        path = self.temp_state()
        observed = learning.record_success_observation(
            {
                "schema": "TEST_SUCCESS_V1",
                "status": "PASS__OPAQUE_EXTERNAL_SUCCESS",
                "pass": True,
                "result": {"opaque": True},
            },
            surface="OPAQUE_EXTERNAL_SURFACE",
            state_path=path,
            replay_context={
                "mode": "generic",
                "problem": {"task_id": "frontier-activation-pass"},
            },
        )
        driver.advance_once(state_path=path)
        state = learning.load_state(path)
        parked = state["improvement_queue"][observed["improvement_work_id"]]
        old_authority = parked["verification_authority_sha256"]
        new_frontier = "d" * 64
        new_adapter = "b" * 64
        activation = {
            "schema": driver.SCHEMA,
            "status": "SUCCESS_ADAPTER_FRONTIER_ACTIVATED__VERIFICATION_AUTHORITY_UNCHANGED",
            "pass": True,
            "adapter_frontier_sha256": new_adapter,
            "verification_authority_sha256": old_authority,
            "activated_module_bindings": [],
            "terminal_authority": False,
        }

        with (
            mock.patch.object(
                driver,
                "_owned_success_learning_frontier_sha256",
                return_value=new_frontier,
            ),
            mock.patch.object(
                driver,
                "_owned_success_adapter_frontier_sha256",
                return_value=new_adapter,
            ),
            mock.patch.object(
                driver,
                "_owned_success_verification_authority_sha256",
                return_value=old_authority,
            ),
            mock.patch.object(
                driver,
                "_activate_owned_success_adapter_frontier",
                return_value=activation,
            ) as activate,
        ):
            out = driver._reactivate_parked_successes(
                state_path=path,
                repo_root=driver.ROOT,
                external_authority_available=False,
            )

        activate.assert_called_once()
        self.assertIn(observed["improvement_work_id"], out["reopened_work_ids"])
        self.assertTrue(out["frontier_activation"]["pass"])
        state = learning.load_state(path)
        row = state["improvement_queue"][observed["improvement_work_id"]]
        self.assertEqual(row["status"], "PENDING")
        self.assertEqual(
            row["reactivated_by"],
            "OWNED_SUCCESS_ADAPTER_FRONTIER_CHANGED__AUTHORITY_UNCHANGED",
        )
        self.assertEqual(row["verification_frontier_sha256"], new_frontier)
        self.assertEqual(row["adapter_frontier_sha256"], new_adapter)
        self.assertEqual(row["verification_authority_sha256"], old_authority)
        expansion = state["improvement_queue"][parked["frontier_expansion_work_id"]]
        self.assertEqual(expansion["status"], "RESOLVED")

    def test_frontier_acquisition_cannot_rewrite_verification_authority(self):
        path = self.temp_state()
        observed = learning.record_success_observation(
            {
                "schema": "TEST_SUCCESS_V1",
                "status": "PASS__OPAQUE_EXTERNAL_SUCCESS",
                "pass": True,
                "result": {"opaque": True},
            },
            surface="OPAQUE_EXTERNAL_SURFACE",
            state_path=path,
            replay_context={
                "mode": "generic",
                "problem": {"task_id": "frontier-authority-rewrite"},
            },
        )
        driver.advance_once(state_path=path)
        state = learning.load_state(path)
        parked = state["improvement_queue"][observed["improvement_work_id"]]
        old_frontier = parked["verification_frontier_sha256"]
        old_adapter = parked["adapter_frontier_sha256"]
        old_authority = parked["verification_authority_sha256"]
        new_frontier = "9" * 64
        new_authority = "8" * 64
        phase = {"after": False}

        def acquire(_request):
            phase["after"] = True
            return {"pass": True, "status": "CLAIMS_VERIFIER_INSTALLED"}

        provider = mock.Mock(side_effect=acquire)
        with (
            mock.patch.object(
                driver,
                "_owned_success_learning_frontier_sha256",
                side_effect=lambda **_: (
                    new_frontier if phase["after"] else old_frontier
                ),
            ),
            mock.patch.object(
                driver,
                "_owned_success_adapter_frontier_sha256",
                return_value=old_adapter,
            ),
            mock.patch.object(
                driver,
                "_owned_success_verification_authority_sha256",
                side_effect=lambda **_: (
                    new_authority if phase["after"] else old_authority
                ),
            ),
            mock.patch.object(
                driver,
                "_activate_owned_success_adapter_frontier",
            ) as activate,
        ):
            first = driver.advance_once(
                state_path=path,
                verification_frontier_acquisition_provider=provider,
                verification_frontier_acquisition_provider_id="root1-worker-v1",
            )
            second = driver.advance_once(state_path=path)

        self.assertFalse(first["pass"], first)
        self.assertFalse(first["progress"], first)
        self.assertEqual(
            first["status"],
            "FRONTIER_ACQUISITION_REJECTED__VERIFICATION_AUTHORITY_REWRITTEN",
        )
        self.assertFalse(first["verification_authority_change_accepted"])
        activate.assert_not_called()
        self.assertTrue(second["pass"], second)
        self.assertFalse(second["progress"], second)

        state = learning.load_state(path)
        blocked = state["improvement_queue"][observed["improvement_work_id"]]
        self.assertEqual(blocked["status"], "PARKED")
        self.assertTrue(blocked["verification_authority_change_blocked"])
        self.assertEqual(
            blocked["blocked_verification_authority_sha256"],
            new_authority,
        )

    def test_external_adapter_cannot_override_changed_verification_authority(self):
        path = self.temp_state()
        observed = learning.record_success_observation(
            {
                "schema": "TEST_SUCCESS_V1",
                "status": "PASS__OPAQUE_EXTERNAL_SUCCESS",
                "pass": True,
                "result": {"opaque": True},
            },
            surface="OPAQUE_EXTERNAL_SURFACE",
            state_path=path,
            replay_context={"mode": "generic", "problem": {"task_id": "external-adapter"}},
        )
        driver.advance_once(state_path=path)
        state = learning.load_state(path)
        parked = state["improvement_queue"][observed["improvement_work_id"]]
        old_adapter = parked["adapter_frontier_sha256"]
        new_authority = "7" * 64

        with (
            mock.patch.object(
                driver,
                "_owned_success_learning_frontier_sha256",
                return_value="6" * 64,
            ),
            mock.patch.object(
                driver,
                "_owned_success_adapter_frontier_sha256",
                return_value=old_adapter,
            ),
            mock.patch.object(
                driver,
                "_owned_success_verification_authority_sha256",
                return_value=new_authority,
            ),
        ):
            out = driver._reactivate_parked_successes(
                state_path=path,
                repo_root=driver.ROOT,
                external_authority_available=False,
                external_adapter_available=True,
            )

        self.assertEqual(out["reopened_work_ids"], [])
        state = learning.load_state(path)
        row = state["improvement_queue"][observed["improvement_work_id"]]
        self.assertEqual(row["status"], "PARKED")
        self.assertTrue(row["verification_authority_change_blocked"])

    def test_parked_success_reopens_on_new_evidence_or_external_authority(self):
        path = self.temp_state()
        first = learning.record_success_observation(
            {
                "schema": "TEST_SUCCESS_V1",
                "status": "PASS__OPAQUE_EXTERNAL_SUCCESS",
                "pass": True,
                "result": {"generation": 1},
            },
            surface="OPAQUE_EXTERNAL_SURFACE",
            state_path=path,
            replay_context={"mode": "generic", "problem": {"task_id": "opaque-1"}},
        )
        parked = driver.advance_once(state_path=path)
        self.assertTrue(parked["disposition_recorded"], parked)

        second = learning.record_success_observation(
            {
                "schema": "TEST_SUCCESS_V1",
                "status": "PASS__OPAQUE_EXTERNAL_SUCCESS",
                "pass": True,
                "result": {"generation": 2},
            },
            surface="OPAQUE_EXTERNAL_SURFACE",
            state_path=path,
            replay_context={"mode": "generic", "problem": {"task_id": "opaque-2"}},
        )
        self.assertEqual(first["improvement_work_id"], second["improvement_work_id"])
        state = learning.load_state(path)
        row = state["improvement_queue"][second["improvement_work_id"]]
        self.assertEqual(row["status"], "PENDING")
        self.assertEqual(row["observations"], 2)

        driver.advance_once(state_path=path)
        state = learning.load_state(path)
        self.assertEqual(
            state["improvement_queue"][second["improvement_work_id"]]["status"],
            "PARKED",
        )

        with mock.patch.object(
            driver,
            "_adapt_success_work",
            return_value={
                "schema": driver.SCHEMA,
                "status": "IMPROVEMENT_ADVANCED__SUCCESS_BECAME_VERIFIED_EPISODE",
                "pass": True,
                "work_id": second["improvement_work_id"],
                "terminal_authority": False,
            },
        ) as adapt:
            out = driver.advance_once(
                state_path=path,
                episode_verification_provider=object(),
                success_episode_adapter_provider=object(),
            )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"], out)
        adapt.assert_called_once()
        state = learning.load_state(path)
        self.assertEqual(
            state["improvement_queue"][second["improvement_work_id"]]["status"],
            "PENDING",
        )
        self.assertEqual(
            state["improvement_queue"][second["improvement_work_id"]]["reactivated_by"],
            "EXTERNAL_VERIFICATION_AUTHORITY_AVAILABLE",
        )
        expansion_rows = [
            row
            for row in state["improvement_queue"].values()
            if row.get("kind") == driver.FRONTIER_EXPANSION_KIND
        ]
        self.assertTrue(expansion_rows)
        self.assertTrue(all(row["status"] == "RESOLVED" for row in expansion_rows))
        self.assertTrue(all(
            row["resolved_by"] == "EXTERNAL_VERIFICATION_AUTHORITY_AVAILABLE"
            for row in expansion_rows
        ))

    def test_event_waiting_work_does_not_claim_progress(self):
        path = self.temp_state()
        self.write_state(
            path,
            {
                "collect": {
                    "work_id": "collect",
                    "kind": "COLLECT_MATCHING_VERIFIED_EPISODE",
                    "priority": 40,
                    "identity": {},
                    "payload": {},
                    "status": "PENDING",
                    "observations": 1,
                    "reopen_count": 0,
                }
            },
        )
        out = driver.advance_once(state_path=path)
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["progress"], out)
        self.assertEqual(
            out["blockers"][0]["blocker"],
            "WAITING_FOR_NEW_INDEPENDENTLY_VERIFIED_EXPERIENCE",
        )

    def test_drain_failed_repair_does_not_stall_unrelated_actionable_work(self):
        path = self.temp_state()
        stable_state = learning._empty_state()
        learning._write_state(stable_state, path)
        failed_repair = {
            "schema": driver.SCHEMA,
            "status": "IMPROVEMENT_REPAIR_ATTEMPT_DID_NOT_CLOSE_ORIGINAL_OBLIGATION",
            "pass": False,
            "progress": False,
            "work_id": "repair",
            "attempt_backoff_recorded": True,
            "terminal_authority": False,
        }
        advanced_other = {
            "schema": driver.SCHEMA,
            "status": "IMPROVEMENT_ADVANCED__SUCCESS_BECAME_VERIFIED_EPISODE",
            "pass": True,
            "progress": True,
            "work_id": "other",
            "terminal_authority": False,
        }
        stable = {
            "schema": driver.SCHEMA,
            "status": "IMPROVEMENT_QUEUE_HAS_NO_CURRENTLY_ACTIONABLE_WORK",
            "pass": True,
            "progress": False,
            "pending_count": 1,
            "blockers": [],
            "terminal_authority": False,
        }
        with mock.patch.object(
            driver,
            "advance_once",
            side_effect=[failed_repair, advanced_other, stable],
        ) as advance:
            out = driver.drain(state_path=path, max_actions=3)

        self.assertEqual(advance.call_count, 3)
        self.assertEqual(out["progress_count"], 1)
        self.assertEqual(out["status"], "IMPROVEMENT_QUEUE_ADVANCED")
        self.assertFalse(out["pass"])

    def test_drain_stops_when_no_more_actionable_work_exists(self):
        path = self.temp_state()
        self.write_state(
            path,
            {
                "collect": {
                    "work_id": "collect",
                    "kind": "COLLECT_MATCHING_VERIFIED_EPISODE",
                    "priority": 40,
                    "identity": {},
                    "payload": {},
                    "status": "PENDING",
                    "observations": 1,
                    "reopen_count": 0,
                }
            },
        )
        out = driver.drain(state_path=path, max_actions=4)
        self.assertEqual(out["progress_count"], 0)
        self.assertEqual(len(out["actions"]), 1)
        self.assertEqual(out["status"], "IMPROVEMENT_QUEUE_STABLE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
