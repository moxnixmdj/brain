"""Exact fail-closed leaf cut for monotone terminal proof/obligation graphs.

The solver expands AND/OR proof structure to nondominated leaf sets, deduplicates
shared leaves, deletes impossible branches, and separates known nonnegative
reality cost from unresolved cost. It grants no acceptance or ownership credit.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_PROOF_LEAF_CUT_V1"
ALLOWED_KINDS = {"AND", "OR", "LEAF", "PROVED", "IMPOSSIBLE"}
ALLOWED_COST_STATES = {"KNOWN", "UNKNOWN"}
MAX_NONDOMINATED_ALTERNATIVES = 4096


class GraphError(Exception):
    pass


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "selected_leaf_ids": [],
        "lower_bound_reality_units": None,
        "upper_bound_reality_units": None,
        "optimality_certificate": {"optimality_proved": False},
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _prune(sets: list[frozenset[str]]) -> list[frozenset[str]]:
    unique = sorted(set(sets), key=lambda s: (len(s), tuple(sorted(s))))
    kept: list[frozenset[str]] = []
    for candidate in unique:
        if any(prev <= candidate for prev in kept):
            continue
        kept.append(candidate)
        if len(kept) > MAX_NONDOMINATED_ALTERNATIVES:
            raise GraphError("ALTERNATIVE_LIMIT_EXCEEDED")
    return kept


def _combine_and(left: list[frozenset[str]], right: list[frozenset[str]]) -> list[frozenset[str]]:
    if not left or not right:
        return []
    product = [a | b for a in left for b in right]
    if len(product) > MAX_NONDOMINATED_ALTERNATIVES * MAX_NONDOMINATED_ALTERNATIVES:
        raise GraphError("ALTERNATIVE_PRODUCT_LIMIT_EXCEEDED")
    return _prune(product)


def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping):
        return _fail("INPUT_NOT_OBJECT")

    roots = doc.get("roots")
    rows = doc.get("nodes")
    errors: list[str] = []
    if (
        not isinstance(roots, list)
        or not roots
        or any(not isinstance(x, str) or not x for x in roots)
        or len(set(roots)) != len(roots)
    ):
        errors.append("ROOTS_INVALID")
    if not isinstance(rows, list) or not rows:
        errors.append("NODES_INVALID")
    if errors:
        return _fail(*errors)

    nodes: dict[str, dict[str, Any]] = {}
    for i, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            errors.append(f"NODE_{i}_INVALID")
            continue
        node = dict(raw)
        nid = node.get("id")
        kind = node.get("kind")
        if not isinstance(nid, str) or not nid:
            errors.append(f"NODE_{i}_ID_INVALID")
            continue
        if nid in nodes:
            errors.append("DUPLICATE_NODE_ID:" + nid)
            continue
        if kind not in ALLOWED_KINDS:
            errors.append("NODE_KIND_INVALID:" + nid)
            continue

        children = node.get("children")
        if kind in {"AND", "OR"}:
            if (
                not isinstance(children, list)
                or not children
                or any(not isinstance(x, str) or not x for x in children)
                or len(set(children)) != len(children)
            ):
                errors.append("NODE_CHILDREN_INVALID:" + nid)
        elif children not in (None, []):
            errors.append("TERMINAL_NODE_HAS_CHILDREN:" + nid)

        if kind == "LEAF":
            state = node.get("cost_state")
            if state not in ALLOWED_COST_STATES:
                errors.append("LEAF_COST_STATE_INVALID:" + nid)
            elif state == "KNOWN":
                units = node.get("reality_units")
                if isinstance(units, bool) or not isinstance(units, (int, float)) or not isfinite(float(units)) or units < 0:
                    errors.append("LEAF_REALITY_UNITS_INVALID:" + nid)
            elif "reality_units" in node:
                errors.append("UNKNOWN_LEAF_MUST_NOT_ASSERT_REALITY_UNITS:" + nid)
        elif "cost_state" in node or "reality_units" in node:
            errors.append("NONLEAF_HAS_REALITY_COST:" + nid)

        nodes[nid] = node

    for root in roots if isinstance(roots, list) else []:
        if root not in nodes:
            errors.append("ROOT_NODE_MISSING:" + root)
    for nid, node in nodes.items():
        for child in node.get("children") or []:
            if child not in nodes:
                errors.append("CHILD_NODE_MISSING:" + nid + "->" + child)
    if errors:
        return _fail(*errors)

    memo: dict[str, list[frozenset[str]]] = {}
    visiting: list[str] = []

    def solve(nid: str) -> list[frozenset[str]]:
        if nid in memo:
            return memo[nid]
        if nid in visiting:
            cycle = visiting[visiting.index(nid):] + [nid]
            raise GraphError("CYCLE_DETECTED:" + "->".join(cycle))
        visiting.append(nid)
        node = nodes[nid]
        kind = node["kind"]
        if kind == "PROVED":
            out = [frozenset()]
        elif kind == "IMPOSSIBLE":
            out = []
        elif kind == "LEAF":
            out = [frozenset({nid})]
        elif kind == "OR":
            out = _prune([proof for child in node["children"] for proof in solve(child)])
        else:
            out = [frozenset()]
            for child in node["children"]:
                out = _combine_and(out, solve(child))
                if not out:
                    break
        visiting.pop()
        memo[nid] = out
        return out

    try:
        alternatives = [frozenset()]
        for root in roots:
            alternatives = _combine_and(alternatives, solve(root))
            if not alternatives:
                break
    except GraphError as exc:
        return _fail(str(exc))

    if not alternatives:
        return _fail("ROOTS_UNSATISFIABLE")

    leaf_nodes = {nid: n for nid, n in nodes.items() if n["kind"] == "LEAF"}
    profiles: list[dict[str, Any]] = []
    for proof in alternatives:
        known_units = 0.0
        unknown: list[str] = []
        for lid in proof:
            leaf = leaf_nodes[lid]
            if leaf["cost_state"] == "KNOWN":
                known_units += float(leaf["reality_units"])
            else:
                unknown.append(lid)
        profiles.append({
            "leaf_ids": sorted(proof),
            "known_reality_units": known_units,
            "unknown_cost_leaf_ids": sorted(unknown),
        })

    lower = min(p["known_reality_units"] for p in profiles)
    fully_known = [p for p in profiles if not p["unknown_cost_leaf_ids"]]
    upper = min((p["known_reality_units"] for p in fully_known), default=None)
    optimality_proved = upper is not None and upper == lower

    if optimality_proved:
        eligible = [p for p in fully_known if p["known_reality_units"] == lower]
        selected = min(eligible, key=lambda p: (len(p["leaf_ids"]), tuple(p["leaf_ids"])))
        status = "EXACT_OPTIMUM_PROVED"
    else:
        eligible = [p for p in profiles if p["known_reality_units"] == lower]
        selected = min(
            eligible,
            key=lambda p: (
                len(p["unknown_cost_leaf_ids"]),
                len(p["leaf_ids"]),
                tuple(p["leaf_ids"]),
            ),
        )
        status = "LOWER_BOUND_ONLY_UNKNOWN_COSTS_REMAIN"

    lower_frontier_unknowns = sorted({
        lid
        for p in profiles
        if p["known_reality_units"] == lower
        for lid in p["unknown_cost_leaf_ids"]
    })
    gap = None if upper is None else upper - lower

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": [],
        "root_count": len(roots),
        "node_count": len(nodes),
        "nondominated_proof_set_count": len(profiles),
        "selected_leaf_ids": selected["leaf_ids"],
        "selected_known_reality_units": selected["known_reality_units"],
        "selected_unknown_cost_leaf_ids": selected["unknown_cost_leaf_ids"],
        "lower_bound_reality_units": lower,
        "upper_bound_reality_units": upper,
        "unknown_cost_leaf_ids_on_lower_bound_frontier": lower_frontier_unknowns,
        "optimality_certificate": {
            "basis": "EXHAUSTIVE_MONOTONE_AND_OR_ENUMERATION_AFTER_SAFE_SUBSET_DOMINANCE_PRUNING",
            "nonnegative_leaf_cost_assumption_enforced": True,
            "lower_bound_reality_units": lower,
            "upper_bound_reality_units": upper,
            "gap_reality_units": gap,
            "optimality_proved": optimality_proved,
            "unknown_costs_blocking_exact_optimality": [] if optimality_proved else lower_frontier_unknowns,
        },
        "rule": (
            "EXPAND_TO_LEAVES__DEDUPLICATE_SHARED_LEAVES__DELETE_IMPOSSIBLE_BRANCHES__"
            "NEVER_PRICE_UNKNOWN_REALITY_AS_ZERO__PROVE_OPTIMALITY_ONLY_WHEN_LOWER_EQUALS_KNOWN_UPPER"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
