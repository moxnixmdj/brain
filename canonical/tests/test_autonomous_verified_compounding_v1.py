"""R3 regression tests: no result or receipt may self-promote capability."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from canonical.runtime import autonomous_verified_compounding_v1 as r3
from canonical.runtime import executable_skill_program_v7 as programs
from canonical.runtime.universal_verified_adaptive_solver_v12 import run as v12_run


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
        out = r3.run(
            {"task_id": "t"}, repo_root=tmp_path, episode_id="e1", scope_id="s",
        )
    assert out["r3_learning"]["episodes_retained"] == 0
    assert out["r3_learning"]["new_verified_skills"] == 0
    assert not (tmp_path / "canonical/learning/R3_VERIFIED_COMPOUNDING_STATE.json").exists()


def test_forged_unbound_episode_rejected(tmp_path):
    with pytest.raises(r3.CompoundingError, match="NEW_EPISODE_REAUTH_FAILED"):
        r3.reconcile(
            repo_root=tmp_path, state_path="canonical/learning/state.json",
            new_episode=episode("faked"),
        )


def test_retains_two_authenticated_episodes_then_induces_candidate_only(tmp_path):
    path = "canonical/learning/state.json"
    with patch.object(r3, "reauthenticate_record", side_effect=lambda e, repo_root: {
        "pass": True, "authenticated_episode": e,
    }):
        first = r3.reconcile(repo_root=tmp_path, state_path=path, new_episode=episode("a"))
        second = r3.reconcile(repo_root=tmp_path, state_path=path, new_episode=episode("b"))
        state, data = r3.load_state(repo_root=tmp_path, state_path=path)
        assert first["episodes_retained"] == 1
        assert second["episodes_retained"] == 2
        assert second["new_candidates"] == 1
        assert second["verified_skills_retained"] == 0
        assert state["candidates"][0]["reuse_authorized"] is False
        assert data is not None


def test_unauthenticated_skill_receipt_fails_closed(tmp_path):
    path = "canonical/learning/state.json"
    with patch.object(r3, "reauthenticate_record", return_value={"pass": True}):
        r3.reconcile(repo_root=tmp_path, state_path=path, new_episode=episode("a"))
        r3.reconcile(repo_root=tmp_path, state_path=path, new_episode=episode("b"))
        state, _ = r3.load_state(repo_root=tmp_path, state_path=path)
        candidate_id = state["candidates"][0]["candidate_sha256"]
        with pytest.raises(r3.CompoundingError, match="CANDIDATE_VERIFICATION_FAILED"):
            r3.reconcile(
                repo_root=tmp_path, state_path=path,
                candidate_verification_bindings={candidate_id: {
                    "receipt": {"path": "missing.json"}, "verification": {"path": "no.json"}
                }},
            )


def test_skill_promotion_can_only_follow_external_authenticator(tmp_path):
    path = "canonical/learning/state.json"
    with patch.object(r3, "reauthenticate_record", return_value={"pass": True}):
        r3.reconcile(repo_root=tmp_path, state_path=path, new_episode=episode("a"))
        r3.reconcile(repo_root=tmp_path, state_path=path, new_episode=episode("b"))
        state, _ = r3.load_state(repo_root=tmp_path, state_path=path)
        candidate_id = state["candidates"][0]["candidate_sha256"]
        # Explicitly mock the trusted verifier to isolate orchestration behavior;
        # this does not test real receipt independence.
        with patch.object(r3, "authenticate_and_verify",
                          return_value={"pass": True, "verified_skill": {}}):
            out = r3.reconcile(
                repo_root=tmp_path, state_path=path,
                candidate_verification_bindings={candidate_id: {"external": "binding"}},
            )
            assert out["new_verified_skills"] == 1
            reload, _ = r3.load_state(repo_root=tmp_path, state_path=path)
            assert len(reload["skills"]) == 1
        with pytest.raises(r3.CompoundingError, match="STORED_SKILL_REAUTH_FAILED"):
            r3.load_state(repo_root=tmp_path, state_path=path)


def test_stored_episode_reauthenticated_before_solver_execution(tmp_path):
    path = "canonical/learning/state.json"
    with patch.object(r3, "reauthenticate_record", return_value={"pass": True}):
        r3.reconcile(repo_root=tmp_path, state_path=path, new_episode=episode("e1"))
    with patch.object(r3.solver, "run") as execute:
        with pytest.raises(r3.CompoundingError, match="STORED_EPISODE_REAUTH_FAILED"):
            r3.run({"task_id": "next"}, repo_root=tmp_path,
                   state_path=path, episode_id="e2", scope_id="s")
        execute.assert_not_called()


def test_failures_are_recorded_only_as_observations(tmp_path):
    path = "canonical/learning/state.json"
    result = r3.reconcile(
        repo_root=tmp_path, state_path=path,
        failure={"status": "UNRESOLVED", "trace": [], "attempts": []},
    )
    state, _ = r3.load_state(repo_root=tmp_path, state_path=path)
    assert result["failure_observations_retained"] == 1
    assert state["failures"][0]["interpretation"] == "UNDIAGNOSED_OBSERVATION_ONLY"
    assert result["ownership_credit_delta"] == 0


def test_path_escape_and_concurrent_writer_fail_closed(tmp_path):
    with pytest.raises(r3.CompoundingError, match="STATE_PATH_OUTSIDE_REPOSITORY"):
        r3.load_state(repo_root=tmp_path, state_path="../external.json")
    lock = tmp_path / "canonical/learning/stored.json.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("busy")
    with pytest.raises(r3.CompoundingError, match="CONCURRENT_LEARNING_WRITER"):
        r3.reconcile(repo_root=tmp_path, state_path="canonical/learning/stored.json",
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
        r3.reconcile(repo_root=tmp_path, state_path=path, new_episode=episode("old", scope="scopeA"))
        r3.reconcile(repo_root=tmp_path, state_path=path, new_episode=episode("other", scope="scopeB"))
        with patch.object(r3.solver, "run", return_value={
            "pass": False, "status": "NEED_MORE_EVIDENCE", "attempts": [],
        }) as spy:
            result = r3.run({"task_id": "current"}, repo_root=tmp_path,
                            state_path=path, episode_id="new", scope_id="scopeA")
        assert result["pass"] is False
        ids = [e["episode_id"] for e in spy.call_args.kwargs["prior_verified_episode_records"]]
        assert ids == ["old"]
