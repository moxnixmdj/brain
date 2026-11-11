"""Fail-closed abductive residual compiler with global-joint exactness guards.

V2 preserves inclusion-minimal alternatives for joint optimization, reports shortest
alternatives only as a view, and never claims global exactness if any antichain cap
binds. It remains zero-credit scheduling/proof-compression machinery.
"""
from __future__ import annotations

from itertools import product
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ABDUCTIVE_RESIDUAL_THEOREM_V2"
MAX_ATOMS = 128
MAX_RULES = 256
MAX_MINIMA_PER_ATOM = 128
MAX_JOINT_MINIMA = 128


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "exact": False,
        "bounded_incomplete": False,
        "bounded_events": [],
        "errors": sorted(set(errors)),
        "target_residuals": {},
        "shared_residual_groups": [],
        "minimum_joint_residual_sets": [],
        "all_targets_reachable": False,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _valid_atoms(xs: Any, *, nonempty: bool = False) -> bool:
    return (
        isinstance(xs, list)
        and (bool(xs) or not nonempty)
        and all(isinstance(x, str) and bool(x.strip()) for x in xs)
        and len(xs) == len(set(xs))
    )


def _minimize(
    sets: set[frozenset[str]],
    limit: int,
) -> tuple[list[frozenset[str]], bool]:
    """Return inclusion-minimal sets and whether the output cap discarded a minimum."""
    ordered = sorted(sets, key=lambda s: (len(s), tuple(sorted(s))))
    out: list[frozenset[str]] = []
    for candidate in ordered:
        if any(existing <= candidate for existing in out):
            continue
        out.append(candidate)
        if len(out) > limit:
            return out[:limit], True
    return out, False


def _combine(
    parts: list[list[frozenset[str]]],
    limit: int,
) -> tuple[list[frozenset[str]], bool]:
    if not parts:
        return [frozenset()], False
    combos: set[frozenset[str]] = set()
    bounded = False
    for choice in product(*parts):
        merged: set[str] = set()
        for item in choice:
            merged.update(item)
        combos.add(frozenset(merged))
        if len(combos) > limit * 32:
            reduced, truncated = _minimize(combos, limit * 4)
            combos = set(reduced)
            if truncated:
                bounded = True
                break
    reduced, truncated = _minimize(combos, limit)
    return reduced, bounded or truncated


def _closure(seed: set[str], rules: list[tuple[frozenset[str], frozenset[str]]]) -> set[str]:
    out = set(seed)
    changed = True
    while changed:
        changed = False
        for lhs, rhs in rules:
            if lhs <= out and not rhs <= out:
                out.update(rhs)
                changed = True
    return out


def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping):
        return _fail("INPUT_NOT_OBJECT")

    targets = doc.get("targets")
    baseline = doc.get("baseline_facts", [])
    raw_rules = doc.get("implications", [])

    if not _valid_atoms(targets, nonempty=True):
        return _fail("TARGETS_INVALID")
    if not _valid_atoms(baseline):
        return _fail("BASELINE_FACTS_INVALID")
    if not isinstance(raw_rules, list):
        return _fail("IMPLICATIONS_INVALID")
    if len(raw_rules) > MAX_RULES:
        return _fail(f"RULE_LIMIT_EXCEEDED:{len(raw_rules)}>{MAX_RULES}")

    rules: list[tuple[frozenset[str], frozenset[str]]] = []
    rule_ids: set[str] = set()
    universe: set[str] = set(targets) | set(baseline)
    producers: dict[str, list[frozenset[str]]] = {}

    for i, row in enumerate(raw_rules):
        if not isinstance(row, Mapping):
            return _fail(f"IMPLICATION_{i}_INVALID")
        edge_id = row.get("edge_id")
        lhs, rhs = row.get("if_all"), row.get("then")
        if not isinstance(edge_id, str) or not edge_id or edge_id in rule_ids:
            return _fail("IMPLICATION_EDGE_ID_INVALID_OR_DUPLICATE")
        rule_ids.add(edge_id)
        if not _valid_atoms(lhs, nonempty=True) or not _valid_atoms(rhs, nonempty=True):
            return _fail(f"IMPLICATION_ATOMS_INVALID:{edge_id}")
        if row.get("verified") is not True or row.get("independent") is not True:
            return _fail(f"IMPLICATION_NOT_INDEPENDENTLY_VERIFIED:{edge_id}")
        receipt = row.get("receipt")
        if not isinstance(receipt, str) or not receipt:
            return _fail(f"IMPLICATION_RECEIPT_REQUIRED:{edge_id}")
        left, right = frozenset(lhs), frozenset(rhs)
        rules.append((left, right))
        universe.update(left)
        universe.update(right)
        for atom in right:
            producers.setdefault(atom, []).append(left)

    if len(universe) > MAX_ATOMS:
        return _fail(f"ATOM_LIMIT_EXCEEDED:{len(universe)}>{MAX_ATOMS}")

    known = _closure(set(baseline), rules)
    primitives = sorted(atom for atom in universe if atom not in known and atom not in producers)

    minima: dict[str, list[frozenset[str]]] = {}
    for atom in sorted(universe):
        if atom in known:
            minima[atom] = [frozenset()]
        elif atom in primitives:
            minima[atom] = [frozenset([atom])]
        else:
            minima[atom] = []

    bounded_events: set[str] = set()
    changed = True
    rounds = 0
    while changed and rounds <= len(universe) + len(rules):
        changed = False
        rounds += 1
        for lhs, rhs in rules:
            parts = [minima[a] for a in sorted(lhs)]
            if any(not x for x in parts):
                continue
            antecedent_minima, combine_bounded = _combine(parts, MAX_MINIMA_PER_ATOM)
            if combine_bounded:
                bounded_events.add("ANTECEDENT_COMBINATION_LIMIT")
            for atom in rhs:
                merged = set(minima[atom]) | set(antecedent_minima)
                reduced, atom_bounded = _minimize(merged, MAX_MINIMA_PER_ATOM)
                if atom_bounded:
                    bounded_events.add(f"ATOM_MINIMA_LIMIT:{atom}")
                if reduced != minima[atom]:
                    minima[atom] = reduced
                    changed = True

    target_residuals: dict[str, Any] = {}
    all_reachable = True
    for target in targets:
        rows = minima.get(target, [])
        if not rows:
            all_reachable = False
            target_residuals[target] = {
                "reachable": False,
                "minimum_residual_size": None,
                "minimum_residual_sets": [],
                "all_inclusion_minimal_residual_sets": [],
                "facts_in_every_minimum_residual": [],
                "facts_in_every_inclusion_minimal_residual": [],
            }
            continue

        min_size = min(len(r) for r in rows)
        shortest = [r for r in rows if len(r) == min_size]
        common_shortest = set(shortest[0]) if shortest else set()
        for row in shortest[1:]:
            common_shortest.intersection_update(row)
        common_all = set(rows[0]) if rows else set()
        for row in rows[1:]:
            common_all.intersection_update(row)

        target_residuals[target] = {
            "reachable": True,
            "minimum_residual_size": min_size,
            "minimum_residual_sets": [sorted(r) for r in shortest],
            "all_inclusion_minimal_residual_sets": [sorted(r) for r in rows],
            "facts_in_every_minimum_residual": sorted(common_shortest),
            "facts_in_every_inclusion_minimal_residual": sorted(common_all),
        }

    groups: dict[tuple[tuple[str, ...], ...], list[str]] = {}
    for target in targets:
        row = target_residuals[target]
        if not row["reachable"]:
            continue
        key = tuple(tuple(x) for x in row["all_inclusion_minimal_residual_sets"])
        groups.setdefault(key, []).append(target)
    shared = [
        {
            "targets": sorted(ts),
            "inclusion_minimal_residual_sets": [list(x) for x in key],
        }
        for key, ts in groups.items()
        if len(ts) > 1
    ]
    shared.sort(key=lambda x: (-len(x["targets"]), x["targets"]))

    joint: list[frozenset[str]] = []
    if all_reachable:
        parts: list[list[frozenset[str]]] = []
        for target in targets:
            rows = target_residuals[target]["all_inclusion_minimal_residual_sets"]
            parts.append([frozenset(x) for x in rows])
        joint, joint_bounded = _combine(parts, MAX_JOINT_MINIMA)
        if joint_bounded:
            bounded_events.add("JOINT_MINIMA_LIMIT")
        if joint:
            smallest = min(len(x) for x in joint)
            joint = [x for x in joint if len(x) == smallest]

    bounded_incomplete = bool(bounded_events)
    exact = all_reachable and not bounded_incomplete
    if bounded_incomplete:
        status = "BOUNDED_INCOMPLETE__NO_GLOBAL_EXACTNESS_CLAIM"
    elif all_reachable:
        status = "EXACT_WEAKEST_SUFFICIENT_RESIDUALS_COMPUTED"
    else:
        status = "RESIDUAL_GRAPH_CONTAINS_UNREACHABLE_TARGETS"

    return {
        "schema": SCHEMA,
        "status": status,
        "exact": exact,
        "bounded_incomplete": bounded_incomplete,
        "bounded_events": sorted(bounded_events),
        "errors": [],
        "target_count": len(targets),
        "verified_rule_count": len(rules),
        "atom_count": len(universe),
        "baseline_closure": sorted(known),
        "primitive_residual_facts": primitives,
        "target_residuals": target_residuals,
        "shared_residual_groups": shared,
        "minimum_joint_residual_size": len(joint[0]) if joint else None,
        "minimum_joint_residual_sets": [sorted(x) for x in joint],
        "all_targets_reachable": all_reachable,
        "rule": (
            "ONLY_INDEPENDENTLY_VERIFIED_IMPLICATIONS_COUNT__"
            "JOINT_OPTIMIZATION_USES_ALL_RETAINED_INCLUSION_MINIMAL_TARGET_ALTERNATIVES__"
            "ANY_CAP_TRUNCATION_FORBIDS_GLOBAL_EXACTNESS__"
            "CYCLES_DO_NOT_SELF_PROVE__NO_SEMANTIC_SCOPE_METRIC_OR_CREDIT_INVENTION"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
