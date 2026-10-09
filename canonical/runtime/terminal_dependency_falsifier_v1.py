"""Systematic, non-authoritative falsifier for terminal dependency graph V1.

This tool enumerates reusable attack families and surfaces open/unknown
obligations. It is deliberately incapable of proving open-world closure.
Applicability must be explicit or remain UNKNOWN_APPLICABILITY, except for a
small set of structural attacks implied by the node kind itself.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_DEPENDENCY_FALSIFIER_V1"

ATTACK_FAMILIES = (
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
)

_PROFILE_VALUES = frozenset({"APPLICABLE", "NOT_APPLICABLE"})

_PRIORITY = {
    "ALL_CREDITABLE_LIVE_ROUTES_EXECUTABLE_REFINEMENT": 0,
    "EXECUTABLE_REFINEMENT_FRAMEWORK": 1,
    "TERMINAL_DEPENDENCY_GRAPH_GENERATOR_COVERAGE": 2,
}


def _applicability(
    node: Mapping[str, Any],
    family: str,
    profiles: Mapping[str, Mapping[str, str]],
) -> str:
    node_id = str(node.get("id") or "")
    explicit = profiles.get(node_id, {}).get(family)
    if explicit in _PROFILE_VALUES:
        return explicit

    kind = node.get("kind")
    if family == "NEGATION":
        return "APPLICABLE"
    if kind == "ROUTE" and family in {
        "IMPLEMENTATION_REFINEMENT_MISMATCH",
        "VERSION_DRIFT",
    }:
        return "APPLICABLE"
    return "UNKNOWN"


def _disposition(
    node: Mapping[str, Any],
    family: str,
    applicability: str,
) -> tuple[str, str]:
    if applicability == "NOT_APPLICABLE":
        return "NOT_APPLICABLE", "EXPLICIT_PROFILE"
    if applicability == "UNKNOWN":
        return (
            "UNKNOWN_APPLICABILITY",
            "NO_SOUND_APPLICABILITY_RULE_OR_EXPLICIT_PROFILE",
        )

    kind = node.get("kind")
    if family == "IMPLEMENTATION_REFINEMENT_MISMATCH" and kind == "ROUTE":
        refinement = node.get("refinement")
        if not isinstance(refinement, Mapping):
            return "OPEN", "ROUTE_REFINEMENT_STATE_MISSING"
        if (
            refinement.get("status") == "PROVED"
            and node.get("lifecycle")
            in {"REFINEMENT_VERIFIED", "VERIFIED_LIVE"}
            and refinement.get("verification_receipt") is not None
        ):
            return (
                "COVERED_BY_BOUND_GUARD",
                "ROUTE_DECLARED_REFINEMENT_VERIFIED_WITH_BOUND_RECEIPT",
            )
        return (
            "OPEN",
            "NO_VERIFIED_EXECUTABLE_REFINEMENT_RECEIPT_FOR_ROUTE",
        )

    if family == "VERSION_DRIFT" and kind == "ROUTE":
        implementation = node.get("implementation")
        if (
            isinstance(implementation, Mapping)
            and implementation.get("path")
            and implementation.get("git_blob_sha")
        ):
            return (
                "COVERED_BY_BOUND_GUARD",
                "EXACT_IMPLEMENTATION_BLOB_BOUND_IN_DEPENDENCY_GRAPH",
            )
        return "OPEN", "IMPLEMENTATION_IDENTITY_NOT_CONTENT_ADDRESSED"

    if family == "NEGATION":
        if node.get("kind") == "LEAF" and node.get("status") == "UNRESOLVED":
            return "OPEN", "LEAF_ALREADY_DECLARED_UNRESOLVED"
        if node.get("kind") == "ROUTE":
            if node.get("live_authority_status") == "UNRESOLVED":
                return "OPEN", "ROUTE_LIVE_AUTHORITY_ALREADY_UNRESOLVED"
            refinement = node.get("refinement")
            if (
                isinstance(refinement, Mapping)
                and refinement.get("status") == "UNRESOLVED"
            ):
                return "OPEN", "ROUTE_REFINEMENT_ALREADY_UNRESOLVED"
        return (
            "UNKNOWN",
            "NO_COUNTEREXAMPLE_COMPLETENESS_THEOREM_BOUND_FOR_NEGATION_FAMILY",
        )

    return (
        "OPEN",
        "ATTACK_FAMILY_DECLARED_APPLICABLE_WITHOUT_BOUND_CLOSURE_ARGUMENT",
    )


def falsify(
    graph: Mapping[str, Any],
    *,
    attack_profiles: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    if not isinstance(graph, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "GRAPH_NOT_OBJECT",
            "closure_proved": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "GRAPH_NODES_NOT_LIST",
            "closure_proved": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    profiles = attack_profiles or {}
    invalid_profiles = []
    for node_id, per_family in profiles.items():
        if not isinstance(per_family, Mapping):
            invalid_profiles.append(str(node_id))
            continue
        for family, value in per_family.items():
            if family not in ATTACK_FAMILIES or value not in _PROFILE_VALUES:
                invalid_profiles.append(f"{node_id}:{family}:{value}")
    if invalid_profiles:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "ATTACK_PROFILE_INVALID",
            "invalid_profiles": sorted(invalid_profiles),
            "closure_proved": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    rows = []
    open_obligations = []
    unknown_applicability = []
    for node in nodes:
        if not isinstance(node, Mapping):
            continue
        node_id = str(node.get("id") or "")
        for family in ATTACK_FAMILIES:
            applicability = _applicability(node, family, profiles)
            disposition, reason = _disposition(node, family, applicability)
            row = {
                "node_id": node_id,
                "family": family,
                "applicability": applicability,
                "disposition": disposition,
                "reason": reason,
            }
            rows.append(row)
            if disposition == "OPEN":
                open_obligations.append(
                    {"node_id": node_id, "family": family, "reason": reason}
                )
            elif disposition == "UNKNOWN_APPLICABILITY":
                unknown_applicability.append(
                    {"node_id": node_id, "family": family}
                )

    def priority(item: Mapping[str, Any]) -> tuple[int, str, str]:
        node_id = str(item.get("node_id") or "")
        base = _PRIORITY.get(node_id, 10)
        if item.get("family") == "IMPLEMENTATION_REFINEMENT_MISMATCH":
            base -= 1
        return base, node_id, str(item.get("family") or "")

    ranked = sorted(open_obligations, key=priority)
    highest = ranked[0] if ranked else None

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__FALSIFICATION_FRONTIER_ENUMERATED",
        "attack_family_count": len(ATTACK_FAMILIES),
        "node_count": len([n for n in nodes if isinstance(n, Mapping)]),
        "rows": rows,
        "open_obligations": ranked,
        "unknown_applicability": unknown_applicability,
        "highest_priority_open_candidate": highest,
        "priority_is_heuristic_not_proof": True,
        "generator_coverage_proved": False,
        "closure_proved": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
