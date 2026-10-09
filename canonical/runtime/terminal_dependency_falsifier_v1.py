"""Systematic, non-authoritative falsifier for terminal dependency graphs V1."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_TERMINAL_DEPENDENCY_FALSIFIER_V1"
ALLOWED_FAMILIES = frozenset({
    "NEGATION",
    "QUANTIFIER_SWAP",
    "COMPOSITION_MISMATCH",
    "HIDDEN_STATE",
    "TIMING",
    "CONCURRENCY",
    "CRASH_RESTART",
    "ROLLBACK_FORK",
    "BYZANTINE_INPUT",
    "RESOURCE_EXHAUSTION",
    "VERSION_DRIFT",
    "REVOCATION",
    "ADAPTIVE_SELECTION",
    "PROXY_MEASUREMENT",
    "CAUSAL_CONFOUNDING",
    "NOVEL_DIMENSION",
    "IMPLEMENTATION_REFINEMENT_MISMATCH",
})


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "open_world_closure": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def analyze_graph(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return _fail("GRAPH_NOT_OBJECT")
    leaves = raw.get("leaves")
    routes = raw.get("routes")
    if not isinstance(leaves, Sequence) or isinstance(leaves, (str, bytes)):
        return _fail("GRAPH_LEAVES_INVALID")
    if not isinstance(routes, Sequence) or isinstance(routes, (str, bytes)):
        return _fail("GRAPH_ROUTES_INVALID")

    route_deps: dict[str, list[Mapping[str, Any]]] = {}
    for route in routes:
        if not isinstance(route, Mapping):
            continue
        for dep in route.get("dependency_leaf_ids") or []:
            route_deps.setdefault(str(dep), []).append(route)

    obligations: list[dict[str, Any]] = []
    unknown_applicability: list[dict[str, str]] = []
    scored: list[tuple[int, str]] = []
    for leaf in leaves:
        if not isinstance(leaf, Mapping):
            continue
        leaf_id = str(leaf.get("id") or "")
        if leaf.get("status") != "UNRESOLVED":
            continue
        families = leaf.get("failure_families") or []
        if not isinstance(families, Sequence) or isinstance(families, (str, bytes)):
            unknown_applicability.append({"leaf_id": leaf_id, "family": "UNSPECIFIED"})
            continue
        deps = route_deps.get(leaf_id, [])
        score = 10 if leaf.get("kind") == "EXECUTABLE_REFINEMENT" else 0
        score += 100 * sum(1 for r in deps if r.get("terminal_load_bearing") is True)
        score += 20 * sum(1 for r in deps if r.get("creditable") is True)
        score += len(deps)
        scored.append((score, leaf_id))
        for family in families:
            family = str(family)
            if family not in ALLOWED_FAMILIES:
                unknown_applicability.append({"leaf_id": leaf_id, "family": family})
                continue
            obligations.append({
                "leaf_id": leaf_id,
                "family": family,
                "status": "UNRESOLVED_COUNTEREXAMPLE_OBLIGATION",
                "terminal_load_bearing": any(r.get("terminal_load_bearing") is True for r in deps),
                "creditable_dependency": any(r.get("creditable") is True for r in deps),
            })

    scored.sort(key=lambda x: (-x[0], x[1]))
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__FALSIFICATION_FRONTIER_ENUMERATED",
        "highest_dominance_unresolved_leaf": scored[0][1] if scored else None,
        "unresolved_obligations": obligations,
        "unknown_applicability": unknown_applicability,
        "open_world_closure": False,
        "generator_coverage_proved": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
