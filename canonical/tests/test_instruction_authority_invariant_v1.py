from itertools import chain, combinations

from canonical.runtime.instruction_authority_invariant_v1 import (
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
    assert out["execution_authority"] is True
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
                        if out["execution_authority"]:
                            assert proposal_epoch == state["current_epoch"]
                            assert not unresolved
                            assert set(required) <= set(authorized)
                            assert not (set(required) & set(forbidden))
                            assert not (set(authorized) & set(forbidden))
