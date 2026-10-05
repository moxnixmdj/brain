from __future__ import annotations

from collections import deque
from fractions import Fraction
from typing import Any, Mapping


class CouplingError(ValueError):
    pass


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


def _max_flow(
    target: Mapping[str, Fraction],
    brain: Mapping[str, Fraction],
    edges: set[tuple[str, str]],
) -> tuple[Fraction, dict[tuple[str, str], Fraction]]:
    source = "__S__"
    sink = "__K__"
    nodes = {source, sink}
    tnodes = {f"T:{x}" for x in target}
    bnodes = {f"B:{x}" for x in brain}
    nodes |= tnodes | bnodes

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
    return total, coupling


def solve(task: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(task, Mapping):
        raise CouplingError("TASK_INVALID")
    target = _distribution(task.get("target_distribution"), "TARGET")
    brain = _distribution(task.get("brain_distribution"), "BRAIN")

    raw_edges = task.get("dominance_edges")
    if not isinstance(raw_edges, list) or not raw_edges:
        raise CouplingError("DOMINANCE_EDGES_MISSING")
    edges: set[tuple[str, str]] = set()
    for row in raw_edges:
        if not isinstance(row, Mapping) or not row.get("target") or not row.get("brain"):
            raise CouplingError("DOMINANCE_EDGE_INVALID")
        edges.add((str(row["target"]), str(row["brain"])))

    cert = task.get("material_order_certificate")
    if not isinstance(cert, str) or not cert.strip():
        raise CouplingError("MATERIAL_ORDER_CERTIFICATE_REQUIRED")

    flow, coupling = _max_flow(target, brain, edges)
    passed = flow == Fraction(1)
    return {
        "schema": "PROJECT_BRAIN_HIDDEN_EVALUATOR_MONOTONE_COUPLING_RESULT_V1",
        "status": "PASS" if passed else "FAIL_CLOSED",
        "theorem": "DOMINANCE_PRESERVING_COUPLING_IMPLIES_NONINFERIORITY_FOR_ALL_BOUNDED_ORDER_MONOTONE_UTILITIES",
        "max_coupled_mass": str(flow),
        "coupling": [
            {"target": t, "brain": b, "mass": str(m)}
            for (t, b), m in sorted(coupling.items())
        ],
        "material_order_certificate": cert,
        "universal_monotone_utility_noninferiority": passed,
        "observational_equivalence_required": False if passed else None,
        "terminal_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
