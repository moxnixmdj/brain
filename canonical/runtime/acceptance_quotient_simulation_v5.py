"""Mechanical uniform-policy hardening for acceptance-quotient simulation V4.

V3/V4 require receipts asserting that pointwise graph witnesses are induced by
one owned causal policy, but they do not mechanically bind one policy identity
or one action choice across all target edges at a Brain quotient state.

V5 closes that finite-certificate quantifier gap:
  * one top-level policy_id must bind the strategy receipt and every edge receipt;
  * policy_table selects exactly one policy_action_id per bound Brain state;
  * every reachable target edge must be simulated using an edge carrying that
    same selected action for the current Brain state.

Thus target-edge-conditioned action switching is rejected mechanically. This is
still only a finite abstract verifier. Receipt bytes, quotient-state causal
sufficiency, concrete policy ownership, outcome completeness, and scope
completeness remain independent load-bearing obligations.
"""
from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from typing import Any

from canonical.runtime.acceptance_quotient_simulation_v4 import (
    verify_acceptance_quotient_certificate_v4 as verify_v4,
)

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_QUOTIENT_SIMULATION_V5"


class CertificateError(ValueError):
    pass


def _seq(value: Any, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CertificateError(label + "_INVALID")
    return list(value)


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CertificateError(label + "_INVALID")
    return value.strip()


def _unique_tokens(value: Any, label: str) -> list[str]:
    items = [_token(x, label + "_ITEM") for x in _seq(value, label)]
    if len(items) != len(set(items)):
        raise CertificateError(label + "_DUPLICATE")
    return items


def _bind_policy_identity(cert: Mapping[str, Any]) -> str:
    policy_id = _token(cert.get("policy_id"), "POLICY_ID")

    strategy = cert.get("causal_strategy_receipt")
    if not isinstance(strategy, Mapping):
        raise CertificateError("CAUSAL_STRATEGY_RECEIPT_INVALID")
    if _token(strategy.get("policy_id"), "CAUSAL_STRATEGY_POLICY_ID") != policy_id:
        raise CertificateError("CAUSAL_STRATEGY_POLICY_ID_MISMATCH")

    raw_edges = cert.get("brain_macro_edges")
    if not isinstance(raw_edges, list):
        raise CertificateError("BRAIN_MACRO_EDGES_INVALID")
    for index, raw in enumerate(raw_edges):
        if not isinstance(raw, Mapping):
            raise CertificateError(f"BRAIN_EDGE_{index}_INVALID")
        receipt = raw.get("causal_policy_binding_receipt")
        if not isinstance(receipt, Mapping):
            raise CertificateError(
                f"BRAIN_EDGE_{index}_CAUSAL_POLICY_BINDING_RECEIPT_INVALID"
            )
        edge_policy_id = _token(
            receipt.get("policy_id"),
            f"BRAIN_EDGE_{index}_CAUSAL_POLICY_BINDING_POLICY_ID",
        )
        if edge_policy_id != policy_id:
            raise CertificateError(f"BRAIN_EDGE_{index}_POLICY_ID_MISMATCH")
    return policy_id


def _verify_uniform_policy(cert: Mapping[str, Any]) -> dict[str, Any]:
    target_states = _unique_tokens(cert.get("target_states"), "TARGET_STATES")
    brain_states = _unique_tokens(cert.get("brain_states"), "BRAIN_STATES")
    target_set, brain_set = set(target_states), set(brain_states)
    if not target_set or not brain_set:
        raise CertificateError("STATE_DOMAIN_EMPTY")

    relation: set[tuple[str, str]] = set()
    for index, raw in enumerate(_seq(cert.get("relation"), "RELATION")):
        pair = _seq(raw, f"RELATION_{index}")
        if len(pair) != 2:
            raise CertificateError(f"RELATION_{index}_ARITY")
        t = _token(pair[0], f"RELATION_{index}_TARGET")
        b = _token(pair[1], f"RELATION_{index}_BRAIN")
        if t not in target_set or b not in brain_set:
            raise CertificateError(f"RELATION_{index}_UNKNOWN_STATE")
        relation.add((t, b))

    target_edges_by_from: dict[str, list[dict[str, str]]] = defaultdict(list)
    edge_ids: set[str] = set()
    for index, raw in enumerate(_seq(cert.get("target_cut_edges"), "TARGET_CUT_EDGES")):
        if not isinstance(raw, Mapping):
            raise CertificateError(f"TARGET_EDGE_{index}_INVALID")
        edge_id = _token(raw.get("id"), f"TARGET_EDGE_{index}_ID")
        src = _token(raw.get("from"), f"TARGET_EDGE_{index}_FROM")
        dst = _token(raw.get("to"), f"TARGET_EDGE_{index}_TO")
        if edge_id in edge_ids:
            raise CertificateError("TARGET_EDGE_ID_DUPLICATE")
        if src not in target_set or dst not in target_set:
            raise CertificateError(f"TARGET_EDGE_{index}_UNKNOWN_STATE")
        edge_ids.add(edge_id)
        target_edges_by_from[src].append({"id": edge_id, "from": src, "to": dst})

    brain_edges_by_from: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, raw in enumerate(_seq(cert.get("brain_macro_edges"), "BRAIN_MACRO_EDGES")):
        if not isinstance(raw, Mapping):
            raise CertificateError(f"BRAIN_EDGE_{index}_INVALID")
        src = _token(raw.get("from"), f"BRAIN_EDGE_{index}_FROM")
        dst = _token(raw.get("to"), f"BRAIN_EDGE_{index}_TO")
        action = _token(raw.get("policy_action_id"), f"BRAIN_EDGE_{index}_POLICY_ACTION_ID")
        covers = set(
            _unique_tokens(raw.get("covers_target_edge_ids"), f"BRAIN_EDGE_{index}_COVERS")
        )
        if src not in brain_set or dst not in brain_set:
            raise CertificateError(f"BRAIN_EDGE_{index}_UNKNOWN_STATE")
        if not covers:
            raise CertificateError(f"BRAIN_EDGE_{index}_COVERS_EMPTY")
        unknown = covers - edge_ids
        if unknown:
            raise CertificateError(
                f"BRAIN_EDGE_{index}_UNKNOWN_TARGET_EDGE:" + sorted(unknown)[0]
            )
        brain_edges_by_from[src].append(
            {"from": src, "to": dst, "action": action, "covers": covers}
        )

    policy: dict[str, str] = {}
    for index, raw in enumerate(_seq(cert.get("policy_table"), "POLICY_TABLE")):
        if not isinstance(raw, Mapping):
            raise CertificateError(f"POLICY_TABLE_{index}_INVALID")
        state = _token(raw.get("brain_state"), f"POLICY_TABLE_{index}_BRAIN_STATE")
        action = _token(raw.get("policy_action_id"), f"POLICY_TABLE_{index}_ACTION")
        if state not in brain_set:
            raise CertificateError(f"POLICY_TABLE_{index}_UNKNOWN_BRAIN_STATE")
        if state in policy:
            raise CertificateError("POLICY_TABLE_DUPLICATE_BRAIN_STATE:" + state)
        if not any(edge["action"] == action for edge in brain_edges_by_from.get(state, [])):
            raise CertificateError("POLICY_ACTION_HAS_NO_DECLARED_MACROEDGE:" + state + ":" + action)
        policy[state] = action
    if not policy:
        raise CertificateError("POLICY_TABLE_EMPTY")

    initial_target = _unique_tokens(cert.get("initial_target_states"), "INITIAL_TARGET_STATES")
    initial_brain = _unique_tokens(cert.get("initial_brain_states"), "INITIAL_BRAIN_STATES")
    initial_pairs = {
        (t, b)
        for t in initial_target
        for b in initial_brain
        if (t, b) in relation
    }
    missing_initial = [
        t for t in initial_target if not any((t, b) in initial_pairs for b in initial_brain)
    ]
    if missing_initial:
        raise CertificateError("INITIALIZATION_UNSATISFIED:" + missing_initial[0])

    reached_pairs = set(initial_pairs)
    queue: deque[tuple[str, str]] = deque(initial_pairs)
    witnessed_target_edges: set[str] = set()
    used_policy_states: set[str] = set()

    while queue:
        target_state, brain_state = queue.popleft()
        outgoing_target = target_edges_by_from.get(target_state, [])
        if not outgoing_target:
            continue
        if brain_state not in policy:
            raise CertificateError("REACHABLE_POLICY_STATE_UNBOUND:" + brain_state)
        selected_action = policy[brain_state]
        used_policy_states.add(brain_state)

        for target_edge in outgoing_target:
            matches = []
            for brain_edge in brain_edges_by_from.get(brain_state, []):
                if brain_edge["action"] != selected_action:
                    continue
                if target_edge["id"] not in brain_edge["covers"]:
                    continue
                next_pair = (target_edge["to"], brain_edge["to"])
                if next_pair not in relation:
                    continue
                matches.append(next_pair)

            if not matches:
                raise CertificateError(
                    "UNIFORM_POLICY_SIMULATION_MISSING:"
                    + target_edge["id"]
                    + ":"
                    + target_state
                    + ":"
                    + brain_state
                    + ":"
                    + selected_action
                )

            witnessed_target_edges.add(target_edge["id"])
            for next_pair in matches:
                if next_pair not in reached_pairs:
                    reached_pairs.add(next_pair)
                    queue.append(next_pair)

    reachable_target = set(initial_target)
    target_queue = deque(initial_target)
    while target_queue:
        target_state = target_queue.popleft()
        for edge in target_edges_by_from.get(target_state, []):
            if edge["to"] not in reachable_target:
                reachable_target.add(edge["to"])
                target_queue.append(edge["to"])

    for target_state in reachable_target:
        if not any(t == target_state for t, _ in reached_pairs):
            raise CertificateError("REACHABLE_TARGET_STATE_UNRELATED:" + target_state)

    return {
        "status": "PASS",
        "policy_table": [
            {"brain_state": state, "policy_action_id": policy[state]}
            for state in sorted(policy)
        ],
        "used_policy_states": sorted(used_policy_states),
        "reachable_pair_count": len(reached_pairs),
        "witnessed_target_cut_edge_count": len(witnessed_target_edges),
        "uniform_action_choice_mechanically_checked": True,
        "target_edge_conditioned_action_choice_forbidden": True,
    }


def verify_acceptance_quotient_certificate_v5(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")

        policy_id = _bind_policy_identity(cert)
        uniform = _verify_uniform_policy(cert)

        v4 = verify_v4(cert)
        if v4.get("status") != "PASS":
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED",
                "reason": "V4_ACCEPTANCE_CAUSAL_GRAPH_CHECK_FAILED:"
                + str(v4.get("reason") or "UNKNOWN"),
                "acceptance_credit_delta": 0,
            }

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "theorem": "POLICY_IDENTITY_BOUND_UNIFORM_ACTION_ACCEPTANCE_QUOTIENT_SIMULATION_V5",
            "policy_id": policy_id,
            "uniform_policy": uniform,
            "v4": v4,
            "pointwise_existential_action_switching_load_bearing": False,
            "policy_identity_bound_across_strategy_and_edge_receipts": True,
            "finite_quotient_uniform_action_quantifier_mechanically_proved": True,
            "receipt_byte_verification_still_required": True,
            "quotient_state_causal_sufficiency_still_required": True,
            "concrete_policy_ownership_still_required": True,
            "outcome_completeness_still_required": True,
            "scope_completeness_still_required": True,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }
