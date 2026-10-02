"""Compile a proof-first terminal action frontier.

This layer does not perform semantic theorem proving. It enforces ordering:
bounded zero-reality proof compilation/search actions that can affect unresolved
predicates outrank fresh acceptance-case execution. Reality is queried only
after the declared proof-first actions have either closed their target or are
explicitly saturated/exhausted.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROOF_FIRST_FRONTIER_V1"
PROOF_CLASSES = {"PROOF_COMPILE", "PROOF_SEARCH", "DEPENDENCY_REDUCE", "ROUTE_BIND"}
REALITY_CLASSES = {"REALITY_QUERY"}


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "selected_action": None,
        "actions": [],
        "execution_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def evaluate(gap_verdict: Mapping[str, Any]) -> dict[str, Any]:
    actions = gap_verdict.get("actions")
    if not isinstance(actions, list):
        return _fail("ACTIONS_NOT_LIST")

    compiled: list[dict[str, Any]] = []
    errors: list[str] = []
    for i, raw in enumerate(actions):
        if not isinstance(raw, Mapping):
            errors.append(f"ACTION_NOT_OBJECT:{i}")
            continue
        aid = raw.get("id")
        cls = raw.get("action_class")
        executable = raw.get("executable")
        useful = raw.get("useful")
        unresolved = raw.get("unresolved_target_predicates", [])
        saturated = raw.get("proof_saturated") is True
        bounded_proof = raw.get("bounded_proof_action") is True
        if not isinstance(aid, str) or not aid:
            errors.append(f"ACTION_ID_INVALID:{i}")
            continue
        if not isinstance(cls, str):
            errors.append(f"ACTION_CLASS_INVALID:{aid}")
            continue
        if not isinstance(executable, bool) or not isinstance(useful, bool):
            errors.append(f"ACTION_FLAGS_INVALID:{aid}")
            continue
        if not isinstance(unresolved, list):
            errors.append(f"ACTION_TARGETS_INVALID:{aid}")
            continue
        is_proof = cls in PROOF_CLASSES
        is_reality = cls in REALITY_CLASSES
        eligible = executable and useful and (not is_proof or (bounded_proof and not saturated))
        row = dict(raw)
        row["proof_first_class"] = is_proof
        row["reality_class"] = is_reality
        row["bounded_proof_action"] = bounded_proof
        row["frontier_eligible"] = eligible
        compiled.append(row)
    if errors:
        return _fail(*errors)

    proof_actions = [a for a in compiled if a["frontier_eligible"] and a["proof_first_class"]]
    reality_actions = [a for a in compiled if a["frontier_eligible"] and a["reality_class"]]
    other_actions = [a for a in compiled if a["frontier_eligible"] and not a["proof_first_class"] and not a["reality_class"]]

    def pkey(a: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            -int(a.get("affected_unresolved_count", 0)),
            -int(a.get("affected_family_count", 0)),
            0 if a.get("critical_path") is True else 1,
            str(a.get("id")),
        )

    def rkey(a: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            int(a.get("new_reality_units", 0)),
            -int(a.get("affected_unresolved_count", 0)),
            0 if a.get("critical_path") is True else 1,
            str(a.get("id")),
        )

    proof_actions.sort(key=pkey)
    reality_actions.sort(key=rkey)
    other_actions.sort(key=pkey)

    selected = proof_actions[0] if proof_actions else (other_actions[0] if other_actions else (reality_actions[0] if reality_actions else None))
    reason = (
        "PROOF_FIRST_ZERO_REALITY_ACTION"
        if selected in proof_actions
        else "NON_REALITY_SUPPORT_ACTION"
        if selected in other_actions
        else "REALITY_QUERY_ONLY_AFTER_PROOF_FRONTIER_EMPTY_OR_SATURATED"
        if selected in reality_actions
        else "NO_EXECUTABLE_ACTION"
    )
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "pass": True,
        "errors": [],
        "selected_action": selected,
        "selection_reason": reason,
        "proof_frontier_count": len(proof_actions),
        "reality_frontier_count": len(reality_actions),
        "actions": compiled,
        "execution_authority": False,
        "rule": "ZERO_REALITY_PROOF_CLOSURE_DOMINATES_FRESH_CASE_SPEND_UNTIL_DECLARED_PROOF_ACTIONS_ARE_CLOSED_OR_EXPLICITLY_SATURATED",
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
