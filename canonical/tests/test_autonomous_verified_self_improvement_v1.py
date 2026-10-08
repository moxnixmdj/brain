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
        integrated = loop.integrate_solver_output(out, state_path=path)
        state = loop.load_state(path)

        self.assertTrue(integrated["episode_added"])
        self.assertEqual(state["stats"]["verified_episode_count"], 1)
        self.assertEqual(len(state["episodes"]), 1)
        self.assertEqual(
            loop.next_improvement_action(state_path=path)["kind"],
            "COLLECT_MATCHING_VERIFIED_EPISODE",
        )

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

    def test_verified_stronger_skill_pareto_replaces_dominated_variant(self):
        path = self.temp_state()
        first_skill = verified_skill("3", relation="EXACT", source_ids=("ep1", "ep2"))
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
        with mock.patch.object(loop.solver_v12, "run", return_value=solved) as run_mock:
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
        with mock.patch.object(
            loop.solver_v12, "run", side_effect=[failed, solved]
        ) as run_mock:
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
        with mock.patch.object(loop.solver_v12, "run", return_value=failed) as run_mock:
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
        self.assertEqual(
            loop.next_improvement_action(state_path=path)["kind"],
            "REVERIFY_QUARANTINED_SKILL",
        )

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
