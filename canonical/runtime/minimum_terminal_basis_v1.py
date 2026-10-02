"""Fail-closed minimum terminal generating-basis and false-world hitting-set compiler.

This compiler never invents implications. It accepts only explicitly verified implication
edges and searches exact finite candidate sets. It grants zero acceptance/capability/family
credit. Its purpose is to detect redundant proof obligations before reality is consumed.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_MINIMUM_TERMINAL_BASIS_V1"
MAX_CANDIDATES = 24
MAX_MINIMA = 128


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "minimum_generating_bases": [],
        "minimum_false_world_hitting_sets": [],
        "minimum_joint_terminal_cuts": [],
        "all_targets_derivable": False,
        "all_false_worlds_hittable": False,
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


def _closure(seed: set[str], implications: list[tuple[frozenset[str], frozenset[str]]]) -> set[str]:
    out = set(seed)
    changed = True
    while changed:
        changed = False
        for antecedent, consequent in implications:
            if antecedent <= out and not consequent <= out:
                out.update(consequent)
                changed = True
    return out


def _minimum_subsets(candidates: list[str], predicate) -> list[list[str]]:
    for size in range(len(candidates) + 1):
        found: list[list[str]] = []
        for combo in combinations(candidates, size):
            if predicate(set(combo)):
                found.append(list(combo))
                if len(found) >= MAX_MINIMA:
                    break
        if found:
            return found
    return []


def _intersection_of_sets(rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    common = set(rows[0])
    for row in rows[1:]:
        common.intersection_update(row)
    return sorted(common)


def evaluate(doc: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, Mapping):
        return _fail("INPUT_NOT_OBJECT")

    targets = doc.get("targets")
    baseline = doc.get("baseline_facts", [])
    candidates = doc.get("candidate_facts")
    implications_raw = doc.get("implications", [])
    worlds = doc.get("terminal_false_worlds", [])

    if not _valid_atoms(targets, nonempty=True):
        return _fail("TARGETS_INVALID")
    if not _valid_atoms(baseline):
        return _fail("BASELINE_FACTS_INVALID")
    if not _valid_atoms(candidates):
        return _fail("CANDIDATE_FACTS_INVALID")
    if len(candidates) > MAX_CANDIDATES:
        return _fail(f"CANDIDATE_LIMIT_EXCEEDED:{len(candidates)}>{MAX_CANDIDATES}")
    if set(baseline) & set(candidates):
        return _fail("BASELINE_AND_CANDIDATE_FACTS_OVERLAP")
    if not isinstance(implications_raw, list):
        return _fail("IMPLICATIONS_INVALID")
    if not isinstance(worlds, list):
        return _fail("TERMINAL_FALSE_WORLDS_INVALID")

    implications: list[tuple[frozenset[str], frozenset[str]]] = []
    edge_ids: set[str] = set()
    for i, row in enumerate(implications_raw):
        if not isinstance(row, Mapping):
            return _fail(f"IMPLICATION_{i}_INVALID")
        edge_id = row.get("edge_id")
        lhs, rhs = row.get("if_all"), row.get("then")
        if not isinstance(edge_id, str) or not edge_id or edge_id in edge_ids:
            return _fail("IMPLICATION_EDGE_ID_INVALID_OR_DUPLICATE")
        edge_ids.add(edge_id)
        if not _valid_atoms(lhs, nonempty=True) or not _valid_atoms(rhs, nonempty=True):
            return _fail(f"IMPLICATION_ATOMS_INVALID:{edge_id}")
        if row.get("verified") is not True or row.get("independent") is not True:
            return _fail(f"IMPLICATION_NOT_INDEPENDENTLY_VERIFIED:{edge_id}")
        if not isinstance(row.get("receipt"), str) or not row.get("receipt"):
            return _fail(f"IMPLICATION_RECEIPT_REQUIRED:{edge_id}")
        implications.append((frozenset(lhs), frozenset(rhs)))

    candidate_set = set(candidates)
    parsed_worlds: list[tuple[str, set[str]]] = []
    world_ids: set[str] = set()
    for i, row in enumerate(worlds):
        if not isinstance(row, Mapping):
            return _fail(f"WORLD_{i}_INVALID")
        wid = row.get("world_id")
        eliminators = row.get("eliminated_by")
        if not isinstance(wid, str) or not wid or wid in world_ids:
            return _fail("WORLD_ID_INVALID_OR_DUPLICATE")
        world_ids.add(wid)
        if not _valid_atoms(eliminators, nonempty=True):
            return _fail(f"WORLD_ELIMINATORS_INVALID:{wid}")
        unknown = set(eliminators) - candidate_set
        if unknown:
            return _fail(f"WORLD_REFERENCES_UNKNOWN_CANDIDATE:{wid}:{','.join(sorted(unknown))}")
        parsed_worlds.append((wid, set(eliminators)))

    target_set = set(targets)
    baseline_closure = _closure(set(baseline), implications)

    bases = _minimum_subsets(
        candidates,
        lambda chosen: target_set <= _closure(set(baseline) | chosen, implications),
    )
    hitting_sets = (
        _minimum_subsets(
            candidates,
            lambda chosen: all(bool(chosen & eliminators) for _, eliminators in parsed_worlds),
        )
        if parsed_worlds
        else [[]]
    )
    joint = (
        _minimum_subsets(
            candidates,
            lambda chosen: (
                target_set <= _closure(set(baseline) | chosen, implications)
                and all(bool(chosen & eliminators) for _, eliminators in parsed_worlds)
            ),
        )
        if parsed_worlds
        else bases
    )

    all_targets = bool(bases)
    all_worlds = bool(hitting_sets)

    return {
        "schema": SCHEMA,
        "status": (
            "EXACT_MINIMUM_TERMINAL_BASIS_AND_HITTING_SET_COMPUTED"
            if all_targets and all_worlds
            else "TERMINAL_BASIS_RESIDUAL_UNSATISFIABLE_WITH_DECLARED_CANDIDATES"
        ),
        "errors": [],
        "target_count": len(targets),
        "candidate_count": len(candidates),
        "baseline_closure": sorted(baseline_closure),
        "minimum_generating_basis_size": len(bases[0]) if bases else None,
        "minimum_generating_bases": bases,
        "facts_in_every_minimum_generating_basis": _intersection_of_sets(bases),
        "terminal_false_world_count": len(parsed_worlds),
        "minimum_false_world_hitting_set_size": len(hitting_sets[0]) if hitting_sets else None,
        "minimum_false_world_hitting_sets": hitting_sets,
        "facts_in_every_minimum_hitting_set": _intersection_of_sets(hitting_sets),
        "minimum_joint_terminal_cut_size": len(joint[0]) if joint else None,
        "minimum_joint_terminal_cuts": joint,
        "all_targets_derivable": all_targets,
        "all_false_worlds_hittable": all_worlds,
        "rule": (
            "ONLY_EXPLICIT_INDEPENDENTLY_VERIFIED_IMPLICATIONS_COUNT__"
            "EXACT_FINITE_SEARCH_ONLY__NO_SEMANTIC_EDGE_INVENTION__ZERO_CREDIT"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
