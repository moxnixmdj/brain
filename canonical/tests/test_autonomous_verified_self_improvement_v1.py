from __future__ import annotations

from copy import deepcopy
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


def candidate_from(skill: dict) -> dict:
    out = deepcopy(skill)
    out["status"] = "EXECUTABLE_SKILL_CANDIDATE_ONLY"
    out["verified_skill"] = False
    out["reuse_authorized"] = False
    out["candidate_only"] = True
    out["verification_receipt"] = None
    return out


def skill_auth_record() -> dict:
    return {
        "pass": True,
        "receipt": {"path": "skill-r.json", "git_blob_sha": "3" * 40},
        "verification": {"path": "skill-v.json", "git_blob_sha": "4" * 40},
    }


def solved_with_skill(skill: dict) -> dict:
    return {
        "schema": loop.solver_v10.SCHEMA,
        "pass": True,
        "status": "SOLVED__VERIFIED_EXECUTABLE_SKILL_READY",
        "current_episode_verified": False,
        "current_episode": None,
        "skill_candidate": candidate_from(skill),
        "skill_verification_authentication": skill_auth_record(),
        "verified_skill_reuse_authorized": True,
        "verified_executable_skill": skill,
    }


class AutonomousVerifiedSelfImprovementV1Tests(unittest.TestCase):
    def temp_state(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        return Path(td.name) / "state.json"

    def test_failure_is_causally_classified_and_deduplicated(self):
        path = self.temp_state()
        failure = {
            "schema": loop.solver_v10.SCHEMA,
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

    def test_forged_verified_episode_cannot_enter_durable_state(self):
        path = self.temp_state()
        ep = verified_episode("ep1")
        out = {
            "schema": loop.solver_v10.SCHEMA,
            "pass": True,
            "status": "SOLVED__VERIFIED_EPISODE",
            "current_episode_verified": True,
            "current_episode": ep,
            "skill_candidate": None,
            "verified_skill_reuse_authorized": False,
            "verified_executable_skill": None,
        }
        integrated = loop.integrate_solver_output(
            out,
            state_path=path,
            repo_root=path.parent,
        )
        state = loop.load_state(path)
        self.assertFalse(integrated["pass"])
        self.assertIn("EPISODE_REAUTHENTICATION_FAILED", integrated["reason"])
        self.assertEqual(state["stats"]["verified_episode_count"], 0)

    def test_only_reauthenticated_verified_episode_is_persisted(self):
        path = self.temp_state()
        ep = verified_episode("ep1")
        out = {
            "schema": loop.solver_v10.SCHEMA,
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

    def test_unverified_candidate_never_gets_durable_reuse(self):
        path = self.temp_state()
        out = {
            "schema": loop.solver_v10.SCHEMA,
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

    def test_forged_verified_skill_cannot_enter_durable_state(self):
        path = self.temp_state()
        skill = verified_skill("2")
        out = solved_with_skill(skill)
        integrated = loop.integrate_solver_output(
            out,
            state_path=path,
            repo_root=path.parent,
        )
        self.assertFalse(integrated["pass"])
        self.assertIn("SKILL_REAUTHENTICATION_FAILED", integrated["reason"])
        self.assertEqual(loop.load_state(path)["stats"]["verified_skill_count"], 0)

    def test_verified_stronger_same_program_pareto_replaces_weaker_evidence(self):
        path = self.temp_state()
        first_skill = verified_skill("3", relation="EXACT", source_ids=("ep1", "ep2"))
        stronger = verified_skill(
            "4",
            relation="PROVEN_SUPERSET",
            source_ids=("ep1", "ep2", "ep3"),
        )
        by_digest = {
            first_skill["candidate_sha256"]: first_skill,
            stronger["candidate_sha256"]: stronger,
        }

        def auth(candidate, binding, *, repo_root):
            return {
                "pass": True,
                "verified_skill": by_digest[candidate["candidate_sha256"]],
            }

        with mock.patch.object(loop, "authenticate_skill_verification", side_effect=auth):
            first = loop.integrate_solver_output(
                solved_with_skill(first_skill),
                state_path=path,
            )
            second = loop.integrate_solver_output(
                solved_with_skill(stronger),
                state_path=path,
            )

        state = loop.load_state(path)
        first_id = first["active_skill_id"]
        second_id = second["active_skill_id"]
        self.assertIsNotNone(second_id)
        self.assertNotEqual(first_id, second_id)
        self.assertFalse(state["skills"][first_id]["active"])
        self.assertEqual(state["skills"][first_id]["dominated_by"], second_id)
        self.assertTrue(state["skills"][second_id]["active"])
        family = state["skills"][second_id]["family_id"]
        self.assertEqual(state["pareto_frontiers"][family], [second_id])

    def test_weaker_same_program_is_retained_as_evidence_but_not_activated(self):
        path = self.temp_state()
        strong = verified_skill(
            "5",
            relation="PROVEN_SUPERSET",
            source_ids=("ep1", "ep2", "ep3"),
        )
        weak = verified_skill("6", relation="EXACT", source_ids=("ep1", "ep2"))
        by_digest = {
            strong["candidate_sha256"]: strong,
            weak["candidate_sha256"]: weak,
        }

        def auth(candidate, binding, *, repo_root):
            return {
                "pass": True,
                "verified_skill": by_digest[candidate["candidate_sha256"]],
            }

        with mock.patch.object(loop, "authenticate_skill_verification", side_effect=auth):
            active = loop.integrate_solver_output(solved_with_skill(strong), state_path=path)
            rejected = loop.integrate_solver_output(solved_with_skill(weak), state_path=path)

        state = loop.load_state(path)
        weak_id = "skill:" + "6" * 64
        self.assertIsNone(rejected["active_skill_id"])
        self.assertFalse(rejected["permanent_reuse_authorized"])
        self.assertIn(weak_id, state["skills"])
        self.assertFalse(state["skills"][weak_id]["active"])
        self.assertEqual(state["skills"][weak_id]["dominated_by"], active["active_skill_id"])

    def test_different_programs_with_same_postcondition_do_not_delete_each_other(self):
        path = self.temp_state()
        a = verified_skill("7", relation="PROVEN_SUPERSET", source_ids=("ep1", "ep2", "ep3"), step_count=1)
        b = verified_skill("8", relation="EXACT", source_ids=("ep1", "ep2"), step_count=2)
        by_digest = {a["candidate_sha256"]: a, b["candidate_sha256"]: b}

        def auth(candidate, binding, *, repo_root):
            return {"pass": True, "verified_skill": by_digest[candidate["candidate_sha256"]]}

        with mock.patch.object(loop, "authenticate_skill_verification", side_effect=auth):
            one = loop.integrate_solver_output(solved_with_skill(a), state_path=path)
            two = loop.integrate_solver_output(solved_with_skill(b), state_path=path)

        state = loop.load_state(path)
        self.assertTrue(state["skills"][one["active_skill_id"]]["active"])
        self.assertTrue(state["skills"][two["active_skill_id"]]["active"])
        self.assertNotEqual(
            state["skills"][one["active_skill_id"]]["family_id"],
            state["skills"][two["active_skill_id"]]["family_id"],
        )

    def test_learning_run_automatically_reuses_prior_verified_episodes(self):
        path = self.temp_state()
        state = loop.load_state(path)
        ep = verified_episode("ep1")
        state["episodes"][loop._episode_key(ep)] = ep
        loop._refresh_stats(state)
        loop._write_state(state, path)

        solver_out = {
            "schema": loop.solver_v10.SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "TEST_STOP",
            "falsified_capability_ids": [],
            "deferred_capability_ids": [],
            "counterexamples": [],
            "attempts": [],
        }
        with mock.patch.object(loop.solver_v10, "run", return_value=solver_out) as run_mock:
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

    def test_active_verified_skill_is_reauthenticated_and_fed_back_as_preferred_route(self):
        path = self.temp_state()
        skill = verified_skill("9")
        candidate = candidate_from(skill)
        sid = loop._skill_id(skill)
        family = loop._family_id(skill)
        state = loop.load_state(path)
        state["skills"][sid] = {
            "candidate": candidate,
            "skill": skill,
            "verification_binding": {
                "receipt": {"path": "skill-r.json", "git_blob_sha": "3" * 40},
                "verification": {"path": "skill-v.json", "git_blob_sha": "4" * 40},
            },
            "family_id": family,
            "pareto_metrics": loop._skill_pareto_row(sid, skill),
            "active": True,
            "dominated_by": None,
            "compression": {},
        }
        state["pareto_frontiers"][family] = [sid]
        loop._refresh_stats(state)
        loop._write_state(state, path)

        problem = {
            "task_id": "t",
            "initial_facts": [],
            "target_effects": ["goal"],
            "capabilities": [
                {"id": "op0", "requires": [], "provides": ["x"], "cost": 1, "action": {}},
                {"id": "op1", "requires": ["x"], "provides": ["goal"], "cost": 1, "action": {}},
            ],
        }
        solver_out = {
            "schema": loop.solver_v10.SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "TEST_STOP",
            "falsified_capability_ids": [],
            "deferred_capability_ids": [],
            "counterexamples": [],
            "attempts": [],
        }
        with mock.patch.object(
            loop,
            "authenticate_skill_verification",
            return_value={"pass": True, "verified_skill": skill},
        ), mock.patch.object(
            loop,
            "plan_with_skills",
            return_value={
                "pass": True,
                "status": "PASS__SKILL_AWARE_PLAN_COMPILED",
                "used_verified_skill_macros": ["SKILL_MACRO::x"],
                "expanded_execution_plan": ["op0", "op1"],
            },
        ), mock.patch.object(
            loop.solver_v10,
            "run",
            return_value=solver_out,
        ) as run_mock:
            result = loop.run_learning_episode(
                problem,
                state_path=path,
                repo_root=Path("."),
                episode_id="ep3",
                scope_id="scope",
            )

        self.assertEqual(result["active_verified_skill_count_reauthenticated"], 1)
        self.assertTrue(result["verified_skill_reuse_attempted"])
        self.assertEqual(result["preferred_capability_order"], ["op0", "op1"])
        records = run_mock.call_args.kwargs["verified_skill_records"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["skill"]["candidate_sha256"], skill["candidate_sha256"])
        self.assertEqual(run_mock.call_args.kwargs["active_skill_invalidators"], [])

    def test_tampered_active_skill_fails_closed_before_solver_execution(self):
        path = self.temp_state()
        skill = verified_skill("a")
        sid = loop._skill_id(skill)
        family = loop._family_id(skill)
        state = loop.load_state(path)
        state["skills"][sid] = {
            "candidate": candidate_from(skill),
            "skill": skill,
            "verification_binding": {
                "receipt": {"path": "missing.json", "git_blob_sha": "3" * 40},
                "verification": {"path": "missing-v.json", "git_blob_sha": "4" * 40},
            },
            "family_id": family,
            "pareto_metrics": loop._skill_pareto_row(sid, skill),
            "active": True,
            "dominated_by": None,
            "compression": {},
        }
        state["pareto_frontiers"][family] = [sid]
        loop._refresh_stats(state)
        loop._write_state(state, path)

        with mock.patch.object(loop.solver_v10, "run") as run_mock:
            result = loop.run_learning_episode(
                {"task_id": "t", "initial_facts": [], "target_effects": ["goal"], "capabilities": []},
                state_path=path,
                repo_root=path.parent,
                episode_id="ep4",
                scope_id="scope",
            )
        self.assertFalse(result["pass"])
        self.assertEqual(
            result["status"],
            "FAIL_CLOSED__DURABLE_SKILL_REAUTHENTICATION_FAILED",
        )
        run_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
