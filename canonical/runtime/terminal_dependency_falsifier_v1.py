"""Systematic falsifier for the terminal dependency graph V1.

The falsifier never proves open-world completeness. It turns declared attack
families into explicit counterexample obligations and reports which current
nodes appear to discharge them. Applicability must be declared; omission is
not treated as a pass.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.terminal_dependency_graph_guard_v1 import validate_graph

SCHEMA = "PROJECT_BRAIN_TERMINAL_DEPENDENCY_FALSIFIER_V1"
FAMILIES = frozenset(
    {
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
    }
)


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "pass": False,
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "obligations": [],
        "covered_attacks": [],
        "highest_dominance_unresolved_leaf": None,
        "generator_coverage_proved": False,
        "terminal_closure_proved": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _declared_families(node: Mapping[str, Any]) -> tuple[list[str] | None, str | None]:
    value = node.get("attack_families")
    if value is None:
        return None, None
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None, "ATTACK_FAMILIES_INVALID"
    rows = [str(x).strip() for x in value]
    # Empty is an explicit "applicability unknown" state. It is projected as
    # an unresolved obligation below, never as a pass.
    if any(not x for x in rows) or len(rows) != len(set(rows)):
        return None, "ATTACK_FAMILIES_INVALID"
    unsupported = [x for x in rows if x not in FAMILIES]
    if unsupported:
        return None, "ATTACK_FAMILY_UNSUPPORTED"
    return rows, None


def _is_open(node: Mapping[str, Any], family: str) -> bool:
    kind = node.get("kind")
    if kind == "LEAF":
        return node.get("status") == "UNRESOLVED"

    if kind != "ROUTE":
        return True

    lifecycle = node.get("lifecycle")
    refinement = node.get("refinement")
    refinement_status = (
        refinement.get("status") if isinstance(refinement, Mapping) else None
    )
    live_status = node.get("live_authority_status")

    if family == "IMPLEMENTATION_REFINEMENT_MISMATCH":
        return (
            lifecycle not in {"REFINEMENT_VERIFIED", "VERIFIED_LIVE"}
            or refinement_status != "PROVED"
        )

    if family == "VERSION_DRIFT":
        # The graph guard verifies the current exact blob identity. Drift is
        # currently covered only while that validation remains current.
        return lifecycle == "SPECIFIED"

    if family in {"COMPOSITION_MISMATCH", "HIDDEN_STATE", "TIMING", "CONCURRENCY",
                  "CRASH_RESTART", "ROLLBACK_FORK", "BYZANTINE_INPUT",
                  "RESOURCE_EXHAUSTION", "REVOCATION", "NOVEL_DIMENSION"}:
        return (
            refinement_status == "UNRESOLVED"
            or live_status == "UNRESOLVED"
        )

    # Statistical/measurement/causal families are only meaningful when
    # explicitly declared. For a route that declares them, unresolved
    # refinement/live authority conservatively leaves them open.
    return (
        refinement_status == "UNRESOLVED"
        or live_status == "UNRESOLVED"
    )


def falsify_graph(
    raw: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    validate_structure: bool = True,
) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return _fail("GRAPH_NOT_OBJECT")

    if validate_structure:
        structural = validate_graph(raw, repo_root=repo_root)
        if structural.get("pass") is not True:
            return _fail(
                "GRAPH_STRUCTURAL_VALIDATION_FAILED",
                structural_reason=structural.get("reason"),
            )

    nodes = raw.get("nodes")
    if not isinstance(nodes, Sequence) or isinstance(nodes, (str, bytes)):
        return _fail("GRAPH_NODES_REQUIRED")

    obligations: list[dict[str, str]] = []
    covered: list[dict[str, str]] = []

    for index, node in enumerate(nodes):
        if not isinstance(node, Mapping):
            return _fail("NODE_NOT_OBJECT", index=index)
        node_id = str(node.get("id") or "").strip()
        if not node_id:
            return _fail("NODE_ID_REQUIRED", index=index)

        families, reason = _declared_families(node)
        if reason:
            return _fail(reason, node_id=node_id)

        if families is None or not families:
            obligations.append(
                {
                    "node_id": node_id,
                    "family": "UNDECLARED_APPLICABILITY",
                    "status": "APPLICABILITY_UNRESOLVED",
                }
            )
            continue

        for family in families:
            row = {"node_id": node_id, "family": family}
            if _is_open(node, family):
                obligations.append(
                    {
                        **row,
                        "status": "OPEN_COUNTEREXAMPLE_OBLIGATION",
                    }
                )
            else:
                covered.append(
                    {
                        **row,
                        "status": "CURRENTLY_DISCHARGED__NOT_CLOSURE_PROOF",
                    }
                )

    counts = Counter(row["node_id"] for row in obligations)
    highest = None
    if counts:
        highest = sorted(counts, key=lambda k: (-counts[k], k))[0]

    return {
        "pass": True,
        "schema": SCHEMA,
        "status": "PASS__FALSIFICATION_OBLIGATIONS_PROJECTED",
        "obligations": obligations,
        "covered_attacks": covered,
        "highest_dominance_unresolved_leaf": highest,
        "generator_coverage_proved": False,
        "terminal_closure_proved": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
