#!/usr/bin/env python3
"""Exact minimum-byte cover over a finite verified mechanism library.

This does not claim a universal minimum. It returns the exact minimum over the
explicit, eligible mechanism library supplied to it, counting shared dependency
artifacts once.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, List, Mapping, Set, Tuple


class SpecError(ValueError):
    pass


@dataclass(frozen=True)
class Mechanism:
    id: str
    bytes: int
    covers: FrozenSet[str]
    dependencies: Tuple[str, ...]
    conflicts: FrozenSet[str]
    eligible: bool


def _load_mechanisms(spec: Mapping) -> Tuple[FrozenSet[str], Dict[str, Mechanism]]:
    required = spec.get("required_behaviors")
    raw_mechanisms = spec.get("mechanisms")
    if not isinstance(required, list) or not required or not all(isinstance(x, str) and x for x in required):
        raise SpecError("required_behaviors must be a non-empty list of non-empty strings")
    if len(set(required)) != len(required):
        raise SpecError("required_behaviors contains duplicates")
    if not isinstance(raw_mechanisms, list):
        raise SpecError("mechanisms must be a list")

    out: Dict[str, Mechanism] = {}
    for raw in raw_mechanisms:
        if not isinstance(raw, dict):
            raise SpecError("each mechanism must be an object")
        mid = raw.get("id")
        if not isinstance(mid, str) or not mid:
            raise SpecError("mechanism id must be a non-empty string")
        if mid in out:
            raise SpecError(f"duplicate mechanism id: {mid}")
        b = raw.get("bytes")
        if not isinstance(b, int) or isinstance(b, bool) or b < 0:
            raise SpecError(f"mechanism {mid}: bytes must be a non-negative integer")
        covers = raw.get("covers", [])
        deps = raw.get("dependencies", [])
        conflicts = raw.get("conflicts", [])
        eligible = raw.get("eligible", True)
        if not isinstance(covers, list) or not all(isinstance(x, str) and x for x in covers):
            raise SpecError(f"mechanism {mid}: covers must be a list of strings")
        if not isinstance(deps, list) or not all(isinstance(x, str) and x for x in deps):
            raise SpecError(f"mechanism {mid}: dependencies must be a list of strings")
        if not isinstance(conflicts, list) or not all(isinstance(x, str) and x for x in conflicts):
            raise SpecError(f"mechanism {mid}: conflicts must be a list of strings")
        if not isinstance(eligible, bool):
            raise SpecError(f"mechanism {mid}: eligible must be boolean")
        out[mid] = Mechanism(mid, b, frozenset(covers), tuple(deps), frozenset(conflicts), eligible)

    ids = set(out)
    for m in out.values():
        missing = (set(m.dependencies) | set(m.conflicts)) - ids
        if missing:
            raise SpecError(f"mechanism {m.id}: unknown referenced ids: {sorted(missing)}")
    return frozenset(required), out


def _dependency_closures(mechanisms: Mapping[str, Mechanism]) -> Dict[str, FrozenSet[str]]:
    cache: Dict[str, FrozenSet[str]] = {}
    visiting: Set[str] = set()

    def visit(mid: str) -> FrozenSet[str]:
        if mid in cache:
            return cache[mid]
        if mid in visiting:
            raise SpecError(f"dependency cycle detected at {mid}")
        visiting.add(mid)
        closure: Set[str] = {mid}
        for dep in mechanisms[mid].dependencies:
            closure.update(visit(dep))
        visiting.remove(mid)
        frozen = frozenset(closure)
        cache[mid] = frozen
        return frozen

    for mid in mechanisms:
        visit(mid)
    return cache


def solve(spec: Mapping) -> Mapping:
    required, mechanisms = _load_mechanisms(spec)
    closures = _dependency_closures(mechanisms)

    choice_closure: Dict[str, FrozenSet[str]] = {}
    for mid, closure in closures.items():
        if mechanisms[mid].eligible and all(mechanisms[x].eligible for x in closure):
            choice_closure[mid] = closure

    coverers: Dict[str, List[str]] = {b: [] for b in required}
    for mid in choice_closure:
        for behavior in mechanisms[mid].covers & required:
            coverers[behavior].append(mid)

    missing = sorted(b for b, ids in coverers.items() if not ids)
    if missing:
        return {
            "status": "UNSATISFIABLE",
            "reason": "REQUIRED_BEHAVIOR_HAS_NO_ELIGIBLE_COVERER",
            "missing_behaviors": missing,
            "claim_scope": "EXACT_ONLY_OVER_ENUMERATED_ELIGIBLE_MECHANISM_LIBRARY",
        }

    for ids in coverers.values():
        ids.sort(key=lambda x: (mechanisms[x].bytes, x))

    best: Tuple[int, int, Tuple[str, ...]] | None = None
    best_selected: FrozenSet[str] | None = None
    nodes = 0

    def selection_cost(selected: FrozenSet[str]) -> int:
        return sum(mechanisms[x].bytes for x in selected)

    def covered_by(selected: FrozenSet[str]) -> FrozenSet[str]:
        covered: Set[str] = set()
        for x in selected:
            covered.update(mechanisms[x].covers)
        return frozenset(covered & required)

    def conflicts_ok(selected: FrozenSet[str]) -> bool:
        return all(not (mechanisms[x].conflicts & selected) for x in selected)

    def search(selected: FrozenSet[str]) -> None:
        nonlocal best, best_selected, nodes
        nodes += 1
        cost = selection_cost(selected)
        if best is not None and cost > best[0]:
            return

        covered = covered_by(selected)
        if required <= covered:
            key = (cost, len(selected), tuple(sorted(selected)))
            if best is None or key < best:
                best = key
                best_selected = selected
            return

        ranked = []
        for behavior in required - covered:
            feasible = []
            for mid in coverers[behavior]:
                candidate = frozenset(set(selected) | set(choice_closure[mid]))
                if conflicts_ok(candidate):
                    feasible.append((selection_cost(candidate) - cost, mid, candidate))
            if not feasible:
                return
            feasible.sort(key=lambda t: (t[0], t[1]))
            ranked.append((len(feasible), behavior, feasible))

        _, _, branches = min(ranked, key=lambda t: (t[0], t[1]))
        seen: Set[FrozenSet[str]] = set()
        for _, _, candidate in branches:
            if candidate in seen:
                continue
            seen.add(candidate)
            if best is not None and selection_cost(candidate) > best[0]:
                continue
            search(candidate)

    search(frozenset())

    if best_selected is None:
        return {
            "status": "UNSATISFIABLE",
            "reason": "CONFLICTS_OR_DEPENDENCIES_PREVENT_COMPLETE_COVER",
            "claim_scope": "EXACT_ONLY_OVER_ENUMERATED_ELIGIBLE_MECHANISM_LIBRARY",
            "search_nodes": nodes,
        }

    return {
        "status": "OPTIMAL_OVER_ENUMERATED_LIBRARY",
        "selected_mechanisms": sorted(best_selected),
        "total_unique_bytes": best[0],
        "selected_mechanism_count": best[1],
        "covered_behaviors": sorted(required),
        "search_nodes": nodes,
        "claim_scope": "EXACT_ONLY_OVER_ENUMERATED_ELIGIBLE_MECHANISM_LIBRARY",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out")
    ns = ap.parse_args()
    spec = json.loads(Path(ns.spec).read_text(encoding="utf-8"))
    result = solve(spec)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if ns.out:
        Path(ns.out).write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    if result["status"] != "OPTIMAL_OVER_ENUMERATED_LIBRARY":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
