from __future__ import annotations

from collections import deque
from fractions import Fraction
from hashlib import sha256
import json
import re
from typing import Any, Mapping


class CouplingError(ValueError):
    pass


_CERT_SCHEMA = "PROJECT_BRAIN_MATERIAL_ORDER_CERTIFICATE_BINDING_V1"
_RESULT_SCHEMA = "PROJECT_BRAIN_HIDDEN_EVALUATOR_MONOTONE_COUPLING_RESULT_V1"


def _f(x: Any) -> Fraction:
    try:
        return Fraction(str(x))
    except Exception as exc:
        raise CouplingError(f"INVALID_PROBABILITY:{x}") from exc


def _distribution(rows: Any, label: str) -> dict[str, Fraction]:
    if not isinstance(rows, list) or not rows:
        raise CouplingError(f"{label}_DISTRIBUTION_MISSING")
    out: dict[str, Fraction] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not row.get("id"):
            raise CouplingError(f"{label}_ROW_INVALID")
        oid = str(row["id"])
        if oid in out:
            raise CouplingError(f"{label}_DUPLICATE_OUTCOME:{oid}")
        p = _f(row.get("probability"))
        if p < 0:
            raise CouplingError(f"{label}_NEGATIVE_PROBABILITY:{oid}")
        out[oid] = p
    if sum(out.values(), Fraction(0)) != Fraction(1):
        raise CouplingError(f"{label}_PROBABILITIES_MUST_SUM_TO_1")
    return out


def _edges(raw_edges: Any) -> set[tuple[str, str]]:
    if not isinstance(raw_edges, list) or not raw_edges:
        raise CouplingError("DOMINANCE_EDGES_MISSING")
    out: set[tuple[str, str]] = set()
    for row in raw_edges:
        if not isinstance(row, Mapping) or not row.get("target") or not row.get("brain"):
            raise CouplingError("DOMINANCE_EDGE_INVALID")
        out.add((str(row["target"]), str(row["brain"])))
    return out


def _edge_digest(edges: set[tuple[str, str]]) -> str:
    payload = [{"brain": b, "target": t} for t, b in sorted(edges)]
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def dominance_relation_sha256(raw_edges: Any) -> str:
    """Return the canonical content digest that a material-order receipt must bind."""
    return _edge_digest(_edges(raw_edges))


def _material_order_certificate(
    value: Any,
    expected_edge_digest: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CouplingError("MATERIAL_ORDER_CERTIFICATE_BOUND_OBJECT_REQUIRED")
    if value.get("schema") != _CERT_SCHEMA:
        raise CouplingError("MATERIAL_ORDER_CERTIFICATE_SCHEMA_MISMATCH")

    certificate_id = value.get("certificate_id")
    if not isinstance(certificate_id, str) or not certificate_id.strip():
        raise CouplingError("MATERIAL_ORDER_CERTIFICATE_ID_REQUIRED")

    relation_digest = value.get("dominance_relation_sha256")
    if relation_digest != expected_edge_digest:
        raise CouplingError("MATERIAL_ORDER_CERTIFICATE_EDGE_BINDING_MISMATCH")

    receipt_digest = value.get("verification_receipt_sha256")
    if (
        not isinstance(receipt_digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", receipt_digest) is None
    ):
        raise CouplingError("MATERIAL_ORDER_VERIFICATION_RECEIPT_SHA256_REQUIRED")

    if value.get("scope_complete") is not True:
        raise CouplingError("MATERIAL_ORDER_SCOPE_COMPLETENESS_REQUIRED")
    if value.get("monotone_evaluator_class_bound") is not True:
        raise CouplingError("MONOTONE_EVALUATOR_CLASS_BINDING_REQUIRED")

    return {
        "schema": _CERT_SCHEMA,
        "certificate_id": certificate_id.strip(),
        "dominance_relation_sha256": relation_digest,
        "verification_receipt_sha256": receipt_digest,
        "scope_complete": True,
        "monotone_evaluator_class_bound": True,
    }


def _max_flow(
    target: Mapping[str, Fraction],
    brain: Mapping[str, Fraction],
    edges: set[tuple[str, str]],
) -> tuple[
    Fraction,
    dict[tuple[str, str], Fraction],
    dict[str, Any] | None,
]:
    source = "__S__"
    sink = "__K__"
    nodes = {source, sink}
    nodes |= {f"T:{x}" for x in target}
    nodes |= {f"B:{x}" for x in brain}

    cap: dict[tuple[str, str], Fraction] = {}
    for t, p in target.items():
        cap[(source, f"T:{t}")] = p
    for b, q in brain.items():
        cap[(f"B:{b}", sink)] = q
    for t, b in edges:
        if t not in target:
            raise CouplingError(f"UNKNOWN_TARGET_OUTCOME_IN_EDGE:{t}")
        if b not in brain:
            raise CouplingError(f"UNKNOWN_BRAIN_OUTCOME_IN_EDGE:{b}")
        # Total probability mass is one, so unit capacity is effectively infinite.
        cap[(f"T:{t}", f"B:{b}")] = Fraction(1)

    residual: dict[tuple[str, str], Fraction] = {}
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    for (u, v), c in cap.items():
        residual[(u, v)] = c
        residual.setdefault((v, u), Fraction(0))
        adj[u].add(v)
        adj[v].add(u)

    total = Fraction(0)
    while True:
        prev: dict[str, str | None] = {source: None}
        q = deque([source])
        while q and sink not in prev:
            u = q.popleft()
            for v in sorted(adj[u]):
                if v not in prev and residual.get((u, v), Fraction(0)) > 0:
                    prev[v] = u
                    q.append(v)
                    if v == sink:
                        break
        if sink not in prev:
            break

        aug: Fraction | None = None
        v = sink
        while v != source:
            u = prev[v]
            assert u is not None
            r = residual[(u, v)]
            aug = r if aug is None else min(aug, r)
            v = u
        assert aug is not None

        v = sink
        while v != source:
            u = prev[v]
            assert u is not None
            residual[(u, v)] -= aug
            residual[(v, u)] += aug
            v = u
        total += aug

    coupling: dict[tuple[str, str], Fraction] = {}
    for t, b in edges:
        u, v = f"T:{t}", f"B:{b}"
        used = cap[(u, v)] - residual[(u, v)]
        if used > 0:
            coupling[(t, b)] = used

    reachable = {source}
    q = deque([source])
    while q:
        u = q.popleft()
        for v in sorted(adj[u]):
            if v not in reachable and residual.get((u, v), Fraction(0)) > 0:
                reachable.add(v)
                q.append(v)

    obstruction: dict[str, Any] | None = None
    if total < Fraction(1):
        target_set = sorted(t for t in target if f"T:{t}" in reachable)
        neighborhood = sorted({b for t, b in edges if t in target_set})
        target_mass = sum((target[t] for t in target_set), Fraction(0))
        brain_capacity = sum((brain[b] for b in neighborhood), Fraction(0))
        deficit = target_mass - brain_capacity

        # With unit middle-edge capacities and total mass one, this is the exact
        # finite Hall/Strassen obstruction dual to the maximum-flow deficit.
        if deficit != Fraction(1) - total or deficit <= 0:
            raise CouplingError("INTERNAL_MIN_CUT_CERTIFICATE_MISMATCH")

        obstruction = {
            "target_set": target_set,
            "dominating_brain_neighborhood": neighborhood,
            "target_mass": str(target_mass),
            "brain_capacity": str(brain_capacity),
            "deficit": str(deficit),
        }

    return total, coupling, obstruction


def solve(task: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(task, Mapping):
        raise CouplingError("TASK_INVALID")

    target = _distribution(task.get("target_distribution"), "TARGET")
    brain = _distribution(task.get("brain_distribution"), "BRAIN")
    edges = _edges(task.get("dominance_edges"))

    relation_digest = _edge_digest(edges)
    cert = _material_order_certificate(
        task.get("material_order_certificate"),
        relation_digest,
    )

    flow, coupling, obstruction = _max_flow(target, brain, edges)
    passed = flow == Fraction(1)

    return {
        "schema": _RESULT_SCHEMA,
        "status": "PASS" if passed else "FAIL_CLOSED",
        "theorem": (
            "DOMINANCE_PRESERVING_COUPLING_IMPLIES_NONINFERIORITY_"
            "FOR_ALL_BOUNDED_ORDER_MONOTONE_UTILITIES"
        ),
        "max_coupled_mass": str(flow),
        "coupling": [
            {"target": t, "brain": b, "mass": str(m)}
            for (t, b), m in sorted(coupling.items())
        ],
        "dominance_relation_sha256": relation_digest,
        "certificate_relation_binding_verified": True,
        "material_order_certificate": cert,
        "material_order_semantics_verified_by_kernel": False,
        "claim_is_conditional_on_external_material_order_semantics": True,
        "min_cut_obstruction": obstruction,
        "universal_monotone_utility_noninferiority": passed,
        "observational_equivalence_required": False if passed else None,
        "terminal_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
