"""R3 regression tests: no result or receipt may self-promote capability."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from canonical.runtime import autonomous_verified_compounding_v1 as r3
from canonical.runtime import executable_skill_program_v7 as programs
from canonical.runtime.universal_verified_adaptive_solver_v12 import run as v12_run

# In unit tests only, a mock external attestor isolates coordinator behavior.
# This is NOT evidence that a real independent runner has been authenticated.
TRUSTED_FOR_UNIT_TESTS = lambda kind, record: True


def episode(eid, scope="s", op="safe-capability"):
    steps = [{"op": op, "inputs": [], "outputs": ["RESULT"]}]
    return {
        "episode_id": eid, "scope_id": scope, "steps": steps,
        "preconditions": [], "postconditions": ["RESULT"], "invalidators": [],
        "program_sha256": programs.program_digest(
            steps=steps, preconditions=[], postconditions=["RESULT"], invalidators=[]
        ),
        "verification_binding": {"receipt": {"path": "r", "git_blob_sha": "a" * 40}},
    }


def test_no_independent_proof_no_learning(tmp_path):
    with patch.object(r3.solver, "run", return_value={
        "pass": True, "status": "SOLVED__EPISODE_VERIFICATION_REQUIRED",
        "current_episode_verified": False, "current_episode": episode("e1"),
    }):
        out = r3.run(independent_authority=TRUSTED_FOR_UNIT_TESTS, 
            {"task_id": "t"}, repo_root=tmp_path, episode_id="e1", scope_id="s",
        )
    assert out["r3_learning"]["episodes_retained"] == 0
    assert out["r3_learning"]["new_verified_skills"] == 0
    assert not (tmp_path / "canonical/learning/R3_VERIFIED_COMPOUNDING_STATE.json").exists()


def test_forged_unbound_episode_rejected(tmp_path):
    with pytest.raises(r3.CompoundingError, match="NEW_EPISODE_REAUTH_FAILED"):
        r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, 
            repo_root=tmp_path, state_path="canonical/learning/state.json",
            new_episode=episode("faked"),
        )


def test_retains_two_authenticated_episodes_then_induces_candidate_only(tmp_path):
    path = "canonical/learning/state.json"
    with patch.object(r3, "reauthenticate_record", side_effect=lambda e, repo_root: {
        "pass": True, "authenticated_episode": e,
    }):
        first = r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path, new_episode=episode("a"))
        second = r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path, new_episode=episode("b"))
        state, data = r3.load_state(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path)
        assert first["episodes_retained"] == 1
        assert second["episodes_retained"] == 2
        assert second["new_candidates"] == 1
        assert second["verified_skills_retained"] == 0
        assert state["candidates"][0]["reuse_authorized"] is False
        assert data is not None


def test_unauthenticated_skill_receipt_fails_closed(tmp_path):
    path = "canonical/learning/state.json"
    with patch.object(r3, "reauthenticate_record", return_value={"pass": True}):
        r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path, new_episode=episode("a"))
        r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path, new_episode=episode("b"))
        state, _ = r3.load_state(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path)
        candidate_id = state["candidates"][0]["candidate_sha256"]
        with pytest.raises(r3.CompoundingError, match="CANDIDATE_VERIFICATION_FAILED"):
            r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, 
                repo_root=tmp_path, state_path=path,
                candidate_verification_bindings={candidate_id: {
                    "receipt": {"path": "missing.json"}, "verification": {"path": "no.json"}
                }},
            )


def test_skill_promotion_can_only_follow_external_authenticator(tmp_path):
    path = "canonical/learning/state.json"
    with patch.object(r3, "reauthenticate_record", return_value={"pass": True}):
        r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path, new_episode=episode("a"))
        r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path, new_episode=episode("b"))
        state, _ = r3.load_state(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path)
        candidate_id = state["candidates"][0]["candidate_sha256"]
        # Explicitly mock the trusted verifier to isolate orchestration behavior;
        # this does not test real receipt independence.
        with patch.object(r3, "authenticate_and_verify",
                          return_value={"pass": True, "verified_skill": {}}):
            out = r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, 
                repo_root=tmp_path, state_path=path,
                candidate_verification_bindings={candidate_id: {"external": "binding"}},
            )
            assert out["new_verified_skills"] == 1
            reload, _ = r3.load_state(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path)
            assert len(reload["skills"]) == 1
        with pytest.raises(r3.CompoundingError, match="STORED_SKILL_REAUTH_FAILED"):
            r3.load_state(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path)


def test_stored_episode_reauthenticated_before_solver_execution(tmp_path):
    path = "canonical/learning/state.json"
    with patch.object(r3, "reauthenticate_record", return_value={"pass": True}):
        r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path, new_episode=episode("e1"))
    with patch.object(r3.solver, "run") as execute:
        with pytest.raises(r3.CompoundingError, match="STORED_EPISODE_REAUTH_FAILED"):
            r3.run(independent_authority=TRUSTED_FOR_UNIT_TESTS, {"task_id": "next"}, repo_root=tmp_path,
                   state_path=path, episode_id="e2", scope_id="s")
        execute.assert_not_called()


def test_failures_are_recorded_only_as_observations(tmp_path):
    path = "canonical/learning/state.json"
    result = r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, 
        repo_root=tmp_path, state_path=path,
        failure={"status": "UNRESOLVED", "trace": [], "attempts": []},
    )
    state, _ = r3.load_state(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path)
    assert result["failure_observations_retained"] == 1
    assert state["failures"][0]["interpretation"] == "UNDIAGNOSED_OBSERVATION_ONLY"
    assert result["ownership_credit_delta"] == 0


def test_path_escape_and_concurrent_writer_fail_closed(tmp_path):
    with pytest.raises(r3.CompoundingError, match="STATE_PATH_OUTSIDE_REPOSITORY"):
        r3.load_state(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path="../external.json")
    lock = tmp_path / "canonical/learning/stored.json.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("busy")
    with pytest.raises(r3.CompoundingError, match="CONCURRENT_LEARNING_WRITER"):
        r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path="canonical/learning/stored.json",
                     failure={"status": "error"})


def test_v12_rejects_unverified_macro_injection_before_execution(tmp_path):
    result = v12_run(
        {"task_id": "t", "initial_facts": [], "target_effects": ["x"],
         "capabilities": []},
        repo_root=tmp_path,
        verified_skill_records=[{"candidate": {"candidate_sha256": "bogus"},
                                 "binding": {"fake": True}}],
    )
    assert result["pass"] is False
    assert "VERIFIED_SKILL_REAUTH_FAILED" in result.get("reason", "")


def test_solver_receives_only_authenticated_prior_episodes(tmp_path):
    path = "canonical/learning/state.json"
    with patch.object(r3, "reauthenticate_record", return_value={"pass": True}):
        r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path, new_episode=episode("old", scope="scopeA"))
        r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path, new_episode=episode("other", scope="scopeB"))
        with patch.object(r3.solver, "run", return_value={
            "pass": False, "status": "NEED_MORE_EVIDENCE", "attempts": [],
        }) as spy:
            result = r3.run(independent_authority=TRUSTED_FOR_UNIT_TESTS, {"task_id": "current"}, repo_root=tmp_path,
                            state_path=path, episode_id="new", scope_id="scopeA")
        assert result["pass"] is False
        ids = [e["episode_id"] for e in spy.call_args.kwargs["prior_verified_episode_records"]]
        assert ids == ["old"]


def test_configured_episode_verifier_can_admit_only_authenticated_pair(tmp_path):
    offered = {"receipt": {"path": "external-r.json"},
               "verification": {"path": "external-v.json"}}
    outcome = {
        "pass": True, "status": "SOLVED__EPISODE_VERIFICATION_REQUIRED",
        "current_episode_verified": False, "current_episode": episode("new"),
        "trace": [], "state_capsule_head_hash": "a" * 64,
        "value_capsule_head_hash": "b" * 64,
        "expanded_problem": {"task_id": "t", "capabilities": []},
    }
    with patch.object(r3.solver, "run", return_value=outcome):
        with patch.object(r3, "authenticate_episode_verification",
                          return_value={"pass": True, "authenticated_episode": episode("new")}) as authenticator:
            with patch.object(r3, "reauthenticate_record", return_value={"pass": True}):
                result = r3.run(independent_authority=TRUSTED_FOR_UNIT_TESTS, 
                    {"task_id": "t"}, repo_root=tmp_path,
                    episode_id="new", scope_id="s",
                    episode_verifier=lambda solved: offered,
                )
    authenticator.assert_called_once()
    assert result["r3_episode_admitted"] is True
    assert result["r3_learning"]["episodes_retained"] == 1


def test_configured_verifier_rejection_does_not_promote(tmp_path):
    outcome = {
        "pass": True, "status": "SOLVED__EPISODE_VERIFICATION_REQUIRED",
        "current_episode_verified": False, "current_episode": episode("new"),
        "trace": [], "state_capsule_head_hash": "a" * 64,
        "value_capsule_head_hash": "b" * 64,
    }
    with patch.object(r3.solver, "run", return_value=outcome):
        with patch.object(r3, "authenticate_episode_verification",
                          return_value={"pass": False, "reason": "NO_PROOF"}):
            result = r3.run(independent_authority=TRUSTED_FOR_UNIT_TESTS, 
                {"task_id": "t"}, repo_root=tmp_path,
                episode_id="new", scope_id="s",
                episode_verifier=lambda solved: {"receipt": {}, "verification": {}},
            )
    assert result["r3_episode_admitted"] is False
    assert result["r3_learning"]["episodes_retained"] == 0


def test_configured_candidate_verifier_is_automatically_consulted(tmp_path):
    path = "canonical/learning/state.json"
    with patch.object(r3, "reauthenticate_record", return_value={"pass": True}):
        r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, repo_root=tmp_path, state_path=path, new_episode=episode("a"))
        with patch.object(r3, "authenticate_and_verify", return_value={
            "pass": True, "verified_skill": {}
        }):
            result = r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS, 
                repo_root=tmp_path, state_path=path, new_episode=episode("b"),
                candidate_verifier=lambda candidate: {
                    "receipt": {"path": "external-1"},
                    "verification": {"path": "external-2"},
                },
            )
            assert result["new_candidates"] == 1
            assert result["new_verified_skills"] == 1


def test_raw_receipt_declarations_never_establish_independence(tmp_path):
    with patch.object(r3, "reauthenticate_record", return_value={"pass": True}):
        with pytest.raises(r3.CompoundingError, match="INDEPENDENT_EXECUTION_NOT_AUTHENTICATED"):
            r3.reconcile(
                repo_root=tmp_path, state_path="canonical/learning/state.json",
                new_episode=episode("cannot-self-certify"),
            )


def test_stored_claims_cannot_bypass_missing_external_trust_on_reload(tmp_path):
    path = "canonical/learning/state.json"
    with patch.object(r3, "reauthenticate_record", return_value={"pass": True}):
        r3.reconcile(independent_authority=TRUSTED_FOR_UNIT_TESTS,
                     repo_root=tmp_path, state_path=path, new_episode=episode("e1"))
        with pytest.raises(r3.CompoundingError, match="INDEPENDENT_EXECUTION_NOT_AUTHENTICATED"):
            r3.load_state(repo_root=tmp_path, state_path=path)
