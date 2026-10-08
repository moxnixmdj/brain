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

        self.assertTrue(out["pass"], out)
        self.assertTrue(out["progress"], out)
        provider = verify_work.call_args.kwargs["episode_verification_provider"]
        self.assertEqual(provider({"kind": "EPISODE_VERIFICATION"}), binding)
        owned_verifier.assert_called_once()

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
            "REPAIR_ALREADY_ATTEMPTED_FOR_CURRENT_EVIDENCE",
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
            verification_effect_root="/private/effects",
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
        self.assertEqual(work["payload"]["effect_root"], "/private/effects")

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
