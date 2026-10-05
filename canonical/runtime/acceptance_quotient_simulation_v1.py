"""Fail-closed verifier for acceptance-complete quotient simulation.

This verifies only a finite abstract certificate. It does not prove that the
abstraction is sound or that abstract Brain macrosteps are universally
realizable; those facts must be supplied by independent, scope-complete
receipts and are treated as load-bearing premises.
"""
from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_QUOTIENT_SIMULATION_V1"


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


def _receipt(value: Any, label: str, required_true: Sequence[str]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CertificateError(label + "_INVALID")
    path = _token(value.get("path"), label + "_PATH")
    sha = _token(value.get("git_blob_sha"), label + "_SHA")
    for field in required_true:
        if value.get(field) is not True:
            raise CertificateError(label + "_" + field.upper() + "_NOT_TRUE")
    return {"path": path, "git_blob_sha": sha, **{f: True for f in required_true}}


def verify_acceptance_quotient_certificate(cert: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(cert, Mapping):
            raise CertificateError("CERT_NOT_OBJECT")

        target_states = _unique_tokens(cert.get("target_states"), "TARGET_STATES")
        brain_states = _unique_tokens(cert.get("brain_states"), "BRAIN_STATES")
        if not target_states:
            raise CertificateError("TARGET_STATES_EMPTY")
        if not brain_states:
            raise CertificateError("BRAIN_STATES_EMPTY")
        target_set, brain_set = set(target_states), set(brain_states)

        initial_target = _unique_tokens(cert.get("initial_target_states"), "INITIAL_TARGET_STATES")
        initial_brain = _unique_tokens(cert.get("initial_brain_states"), "INITIAL_BRAIN_STATES")
        terminal_target = set(_unique_tokens(cert.get("terminal_target_states"), "TERMINAL_TARGET_STATES"))
        terminal_brain = set(_unique_tokens(cert.get("terminal_brain_states"), "TERMINAL_BRAIN_STATES"))
        if not initial_target:
            raise CertificateError("INITIAL_TARGET_STATES_EMPTY")
        if not initial_brain:
            raise CertificateError("INITIAL_BRAIN_STATES_EMPTY")
        if any(x not in target_set for x in initial_target + list(terminal_target)):
            raise CertificateError("TARGET_BOUNDARY_STATE_UNKNOWN")
        if any(x not in brain_set for x in initial_brain + list(terminal_brain)):
            raise CertificateError("BRAIN_BOUNDARY_STATE_UNKNOWN")

        relation_pairs: set[tuple[str, str]] = set()
        for i, raw in enumerate(_seq(cert.get("relation"), "RELATION")):
            pair = _seq(raw, f"RELATION_{i}")
            if len(pair) != 2:
                raise CertificateError(f"RELATION_{i}_ARITY")
            t = _token(pair[0], f"RELATION_{i}_TARGET")
            b = _token(pair[1], f"RELATION_{i}_BRAIN")
            if t not in target_set or b not in brain_set:
                raise CertificateError(f"RELATION_{i}_UNKNOWN_STATE")
            if (t, b) in relation_pairs:
                raise CertificateError("RELATION_DUPLICATE")
            relation_pairs.add((t, b))
        if not relation_pairs:
            raise CertificateError("RELATION_EMPTY")

        abstraction_receipt = _receipt(
            cert.get("abstraction_receipt"),
            "ABSTRACTION_RECEIPT",
            (
                "acceptance_complete",
                "load_bearing_observations_complete",
                "target_conservative_coverage",
                "independent_or_objective",
            ),
        )

        target_edges_by_from: dict[str, list[dict[str, str]]] = defaultdict(list)
        edge_ids: set[str] = set()
        for i, raw in enumerate(_seq(cert.get("target_cut_edges"), "TARGET_CUT_EDGES")):
            if not isinstance(raw, Mapping):
                raise CertificateError(f"TARGET_EDGE_{i}_INVALID")
            edge_id = _token(raw.get("id"), f"TARGET_EDGE_{i}_ID")
            if edge_id in edge_ids:
                raise CertificateError("TARGET_EDGE_ID_DUPLICATE")
            edge_ids.add(edge_id)
            src = _token(raw.get("from"), f"TARGET_EDGE_{i}_FROM")
            dst = _token(raw.get("to"), f"TARGET_EDGE_{i}_TO")
            if src not in target_set or dst not in target_set:
                raise CertificateError(f"TARGET_EDGE_{i}_UNKNOWN_STATE")
            target_edges_by_from[src].append({"id": edge_id, "from": src, "to": dst})

        brain_edges_by_from: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for i, raw in enumerate(_seq(cert.get("brain_macro_edges"), "BRAIN_MACRO_EDGES")):
            if not isinstance(raw, Mapping):
                raise CertificateError(f"BRAIN_EDGE_{i}_INVALID")
            src = _token(raw.get("from"), f"BRAIN_EDGE_{i}_FROM")
            dst = _token(raw.get("to"), f"BRAIN_EDGE_{i}_TO")
            if src not in brain_set or dst not in brain_set:
                raise CertificateError(f"BRAIN_EDGE_{i}_UNKNOWN_STATE")
            covers = _unique_tokens(raw.get("covers_target_edge_ids"), f"BRAIN_EDGE_{i}_COVERS")
            if not covers:
                raise CertificateError(f"BRAIN_EDGE_{i}_COVERS_EMPTY")
            unknown = [x for x in covers if x not in edge_ids]
            if unknown:
                raise CertificateError(f"BRAIN_EDGE_{i}_UNKNOWN_TARGET_EDGE:" + unknown[0])
            if raw.get("scope_authority_invariant") is not True:
                raise CertificateError(f"BRAIN_EDGE_{i}_SCOPE_AUTHORITY_INVARIANT_NOT_TRUE")
            receipt = _receipt(
                raw.get("realizability_receipt"),
                f"BRAIN_EDGE_{i}_REALIZABILITY_RECEIPT",
                ("scope_complete", "universal_from_abstract_class", "independent_or_objective"),
            )
            brain_edges_by_from[src].append(
                {"from": src, "to": dst, "covers": set(covers), "receipt": receipt}
            )

        initial_pairs = {
            (t, b)
            for t in initial_target
            for b in initial_brain
            if (t, b) in relation_pairs
        }
        missing_initial = [
            t for t in initial_target if not any((t, b) in initial_pairs for b in initial_brain)
        ]
        if missing_initial:
            raise CertificateError("INITIALIZATION_UNSATISFIED:" + missing_initial[0])

        reached_pairs = set(initial_pairs)
        q: deque[tuple[str, str]] = deque(initial_pairs)
        witnessed_edges: set[str] = set()

        while q:
            t, b = q.popleft()
            for target_edge in target_edges_by_from.get(t, []):
                matches = []
                for brain_edge in brain_edges_by_from.get(b, []):
                    if target_edge["id"] not in brain_edge["covers"]:
                        continue
                    next_pair = (target_edge["to"], brain_edge["to"])
                    if next_pair not in relation_pairs:
                        continue
                    matches.append((brain_edge, next_pair))
                if not matches:
                    raise CertificateError(
                        "LOCAL_QUOTIENT_SIMULATION_MISSING:"
                        + target_edge["id"] + ":" + t + ":" + b
                    )
                witnessed_edges.add(target_edge["id"])
                for _, next_pair in matches:
                    if next_pair not in reached_pairs:
                        reached_pairs.add(next_pair)
                        q.append(next_pair)

        reachable_target = set(initial_target)
        tq = deque(initial_target)
        while tq:
            t = tq.popleft()
            for edge in target_edges_by_from.get(t, []):
                if edge["to"] not in reachable_target:
                    reachable_target.add(edge["to"])
                    tq.append(edge["to"])
        for t in reachable_target:
            if not any(rt == t for rt, _ in reached_pairs):
                raise CertificateError("REACHABLE_TARGET_STATE_UNRELATED:" + t)

        for t, b in reached_pairs:
            if t in terminal_target and b not in terminal_brain:
                raise CertificateError("TERMINAL_PRESERVATION_MISSING:" + t + ":" + b)

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "theorem": "ACCEPTANCE_COMPLETE_QUOTIENT_SIMULATION_LIFTS_TO_CONCRETE_TERMINAL_NONINFERIORITY",
            "target_state_count": len(target_states),
            "brain_state_count": len(brain_states),
            "target_cut_edge_count": len(edge_ids),
            "witnessed_target_cut_edge_count": len(witnessed_edges),
            "reachable_pair_count": len(reached_pairs),
            "target_distribution_required": False,
            "concrete_intermediate_stepwise_dominance_required": False,
            "abstraction_receipt": abstraction_receipt,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }
