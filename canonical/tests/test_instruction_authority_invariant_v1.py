from itertools import chain, combinations
import copy
import threading

import pytest

from canonical.runtime.instruction_authority_invariant_v1 import (
    AuthorityCommitError,
    InstructionAuthorityCommitGate,
    evaluate_instruction_action,
    next_requirement_epoch,
)


def req(rid: str):
    return {
        "id": rid,
        "critical": True,
        "dependencies": [],
        "children": [],
        "open_questions": [],
        "clauses": [
            {
                "id": rid + ":must",
                "keyword": "MUST",
                "covered_by_scenarios": [rid + ":scenario"],
            }
        ],
        "scenarios": [
            {
                "id": rid + ":scenario",
                "given": ["normalized requirement"],
                "when": ["action proposed"],
                "then": ["authority invariant checked"],
            }
        ],
    }


def base_state():
    return {
        "current_epoch": 3,
        "active_requirement_ids": ["R1", "R2"],
        "superseded_requirement_ids": [],
        "authorized_scopes": ["read", "write"],
        "forbidden_scopes": ["delete"],
        "unresolved_authority_questions": [],
    }


def base_proposal():
    return {
        "action_id": "A1",
        "epoch": 3,
        "requirement_ids": ["R1", "R2"],
        "required_scopes": ["read"],
    }


def test_valid_normalized_action_passes():
    out = evaluate_instruction_action([req("R1"), req("R2")], base_state(), base_proposal())
    assert out["pass"] is True
    assert out["execution_authority"] is False
    assert out["point_in_time_authority"] is True
    assert out["commit_gate_required"] is True
    assert out["semantic_extraction_proved"] is False
    assert out["bypass_coverage_proved"] is False


def test_missing_authority_abstains():
    p = base_proposal()
    p["required_scopes"] = ["read", "network"]
    out = evaluate_instruction_action([req("R1"), req("R2")], base_state(), p)
    assert out["execution_authority"] is False
    assert any(x.startswith("REQUIRED_SCOPE_NOT_AUTHORIZED:") for x in out["errors"])


def test_forbidden_scope_abstains():
    s = base_state()
    s["authorized_scopes"] = ["read", "delete"]
    p = base_proposal()
    p["required_scopes"] = ["delete"]
    out = evaluate_instruction_action([req("R1"), req("R2")], s, p)
    assert out["execution_authority"] is False
    assert any(x.startswith("FORBIDDEN_SCOPE_REQUESTED:") for x in out["errors"])


def test_requirement_change_invalidates_stale_proposal():
    old = base_state()
    new = next_requirement_epoch(
        old,
        active_requirement_ids=["R2", "R3"],
        authorized_scopes=["read"],
        forbidden_scopes=["write", "delete"],
    )
    stale = base_proposal()
    out = evaluate_instruction_action([req("R2"), req("R3")], new, stale)
    assert out["execution_authority"] is False
    assert "STALE_OR_FUTURE_PROPOSAL_EPOCH" in out["errors"]


def test_superseded_requirement_reference_abstains():
    old = base_state()
    new = next_requirement_epoch(
        old,
        active_requirement_ids=["R2"],
        authorized_scopes=["read"],
    )
    p = {
        "action_id": "A2",
        "epoch": new["current_epoch"],
        "requirement_ids": ["R1"],
        "required_scopes": ["read"],
    }
    out = evaluate_instruction_action([req("R2")], new, p)
    assert out["execution_authority"] is False
    assert any(x.startswith("PROPOSAL_REFERENCES_SUPERSEDED_REQUIREMENTS:") for x in out["errors"])


def test_unresolved_authority_question_abstains():
    s = base_state()
    s["unresolved_authority_questions"] = ["is external publish authorized?"]
    out = evaluate_instruction_action([req("R1"), req("R2")], s, base_proposal())
    assert out["execution_authority"] is False
    assert "UNRESOLVED_AUTHORITY_AMBIGUITY" in out["errors"]


def test_requirement_graph_ambiguity_abstains():
    requirements = [req("R1"), req("R2")]
    requirements[0]["open_questions"] = ["which account is authorized?"]
    out = evaluate_instruction_action(requirements, base_state(), base_proposal())
    assert out["execution_authority"] is False
    assert "REQUIREMENT_GRAPH_FAIL_CLOSED" in out["errors"]


def _powerset(items):
    items = list(items)
    return chain.from_iterable(combinations(items, r) for r in range(len(items) + 1))


def test_exhaustive_two_scope_normalized_soundness():
    # Exhaustively check the finite normalized authority universe.  If the gate
    # authorizes execution, the exercised scopes are authorized, non-forbidden,
    # ambiguity-free, and current-epoch.  This is the deterministic theorem,
    # not a semantic extraction theorem.
    universe = ["read", "write"]
    requirements = [req("R1")]
    for authorized in _powerset(universe):
        for forbidden in _powerset(universe):
            for required in _powerset(universe):
                for proposal_epoch in (0, 1):
                    for unresolved in ([], ["ambiguous"]):
                        state = {
                            "current_epoch": 1,
                            "active_requirement_ids": ["R1"],
                            "superseded_requirement_ids": [],
                            "authorized_scopes": list(authorized),
                            "forbidden_scopes": list(forbidden),
                            "unresolved_authority_questions": unresolved,
                        }
                        proposal = {
                            "action_id": "A",
                            "epoch": proposal_epoch,
                            "requirement_ids": ["R1"],
                            "required_scopes": list(required),
                        }
                        out = evaluate_instruction_action(requirements, state, proposal)
                        if out["point_in_time_authority"]:
                            assert proposal_epoch == state["current_epoch"]
                            assert not unresolved
                            assert set(required) <= set(authorized)
                            assert not (set(required) & set(forbidden))
                            assert not (set(authorized) & set(forbidden))



def _gate():
    return InstructionAuthorityCommitGate(
        [req("R1"), req("R2")],
        base_state(),
    )


def test_point_in_time_decision_cannot_be_used_as_durable_execution_authority():
    out = evaluate_instruction_action(
        [req("R1"), req("R2")],
        base_state(),
        base_proposal(),
    )
    assert out["pass"] is True
    assert out["point_in_time_authority"] is True
    assert out["execution_authority"] is False
    assert out["commit_gate_required"] is True


def test_one_use_commit_executes_effect_exactly_once():
    gate = _gate()
    issued = gate.issue_grant(base_proposal(), grant_id="grant-once")
    assert issued["pass"] is True
    assert issued["execution_authority"] is False

    calls = []
    committed = gate.commit(
        issued["grant"],
        base_proposal(),
        lambda: calls.append("effect") or {"ok": True},
    )
    assert committed["pass"] is True
    assert committed["execution_authority"] is True
    assert committed["effect_committed"] is True
    assert calls == ["effect"]

    with pytest.raises(AuthorityCommitError, match="GRANT_REPLAY_FORBIDDEN"):
        gate.commit(
            issued["grant"],
            base_proposal(),
            lambda: calls.append("replay"),
        )
    assert calls == ["effect"]


def test_requirement_change_between_issue_and_commit_invalidates_grant():
    gate = _gate()
    issued = gate.issue_grant(base_proposal(), grant_id="grant-stale")
    gate.advance_requirements(
        [req("R2"), req("R3")],
        active_requirement_ids=["R2", "R3"],
        authorized_scopes=["read"],
        forbidden_scopes=["write", "delete"],
    )

    with pytest.raises(
        AuthorityCommitError,
        match="CURRENT_AUTHORITY_REVALIDATION_FAILED|GRANT_EPOCH_MISMATCH",
    ):
        gate.commit(
            issued["grant"],
            base_proposal(),
            lambda: "must-not-run",
        )


def test_action_digest_mismatch_fails_closed():
    gate = _gate()
    issued = gate.issue_grant(base_proposal(), grant_id="grant-action")
    changed = base_proposal()
    changed["action_id"] = "A2"

    with pytest.raises(
        AuthorityCommitError,
        match="GRANT_ACTION_DIGEST_MISMATCH",
    ):
        gate.commit(issued["grant"], changed, lambda: "must-not-run")


def test_state_digest_mismatch_fails_closed():
    gate = _gate()
    issued = gate.issue_grant(base_proposal(), grant_id="grant-state")
    forged = copy.deepcopy(issued["grant"])
    forged["normalized_authority_state_digest"] = "0" * 64

    with pytest.raises(
        AuthorityCommitError,
        match="GRANT_STATE_DIGEST_MISMATCH",
    ):
        gate.commit(forged, base_proposal(), lambda: "must-not-run")


def test_effect_failure_consumes_grant_and_prevents_replay():
    gate = _gate()
    issued = gate.issue_grant(base_proposal(), grant_id="grant-fail")

    def fail_effect():
        raise RuntimeError("partial-effect-failure")

    with pytest.raises(RuntimeError, match="partial-effect-failure"):
        gate.commit(issued["grant"], base_proposal(), fail_effect)

    with pytest.raises(AuthorityCommitError, match="GRANT_REPLAY_FORBIDDEN"):
        gate.commit(issued["grant"], base_proposal(), lambda: "retry")


def test_requirement_epoch_change_cannot_interleave_with_effect_commit():
    gate = _gate()
    issued = gate.issue_grant(base_proposal(), grant_id="grant-linear")
    effect_entered = threading.Event()
    allow_effect_exit = threading.Event()
    update_started = threading.Event()
    update_finished = threading.Event()
    errors = []

    def effect():
        effect_entered.set()
        if not allow_effect_exit.wait(2):
            raise RuntimeError("effect-release-timeout")
        return "committed"

    def do_commit():
        try:
            gate.commit(issued["grant"], base_proposal(), effect)
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(exc)

    def do_update():
        update_started.set()
        try:
            gate.advance_requirements(
                [req("R2"), req("R3")],
                active_requirement_ids=["R2", "R3"],
                authorized_scopes=["read"],
                forbidden_scopes=["write", "delete"],
            )
            update_finished.set()
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(exc)

    commit_thread = threading.Thread(target=do_commit)
    update_thread = threading.Thread(target=do_update)
    commit_thread.start()
    assert effect_entered.wait(2)

    update_thread.start()
    assert update_started.wait(2)
    assert not update_finished.wait(0.05)

    allow_effect_exit.set()
    commit_thread.join(2)
    update_thread.join(2)

    assert not commit_thread.is_alive()
    assert not update_thread.is_alive()
    assert update_finished.is_set()
    assert errors == []
    assert gate.snapshot()["current_epoch"] == 4
