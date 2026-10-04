#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_ROOT2_GLOBAL_INFORMATION_CUT_RESULT_V1"


class CutError(RuntimeError):
    pass


@dataclass(frozen=True)
class Action:
    action_id: str
    closes: frozenset[str]
    wall_clock_s: float
    reality_units: int
    action_count: int
    dependencies: tuple[str, ...]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_action(raw: dict) -> Action:
    aid = str(raw.get("id") or "").strip()
    closes = frozenset(str(x).strip() for x in raw.get("closes") or [] if str(x).strip())
    deps = tuple(str(x).strip() for x in raw.get("dependencies") or [] if str(x).strip())
    if not aid:
        raise CutError("ACTION_ID_REQUIRED")
    wall = float(raw.get("wall_clock_s", 0))
    reality = int(raw.get("reality_units", 0))
    count = int(raw.get("action_count", 1))
    if wall < 0 or reality < 0 or count < 1:
        raise CutError("ACTION_COST_INVALID:" + aid)
    return Action(aid, closes, wall, reality, count, deps)


def _dependency_closure(selected: frozenset[str], by_id: dict[str, Action]) -> frozenset[str]:
    out = set(selected)
    stack = list(selected)
    while stack:
        aid = stack.pop()
        action = by_id.get(aid)
        if action is None:
            raise CutError("UNKNOWN_ACTION:" + aid)
        for dep in action.dependencies:
            if dep not in by_id:
                raise CutError("UNKNOWN_DEPENDENCY:" + aid + ":" + dep)
            if dep not in out:
                out.add(dep)
                stack.append(dep)
    return frozenset(out)


def _critical_path_s(aid: str, by_id: dict[str, Action], memo: dict[str, float], visiting: set[str]) -> float:
    if aid in memo:
        return memo[aid]
    if aid in visiting:
        raise CutError("DEPENDENCY_CYCLE:" + aid)
    visiting.add(aid)
    action = by_id[aid]
    dep_path = max((_critical_path_s(dep, by_id, memo, visiting) for dep in action.dependencies), default=0.0)
    visiting.remove(aid)
    memo[aid] = dep_path + action.wall_clock_s
    return memo[aid]


def _cost(action_ids: frozenset[str], by_id: dict[str, Action]) -> tuple[float, int, int, tuple[str, ...]]:
    closure = _dependency_closure(action_ids, by_id)
    if not closure:
        return (0.0, 0, 0, ())
    memo: dict[str, float] = {}
    wall = max(_critical_path_s(aid, by_id, memo, set()) for aid in action_ids)
    count = sum(by_id[x].action_count for x in closure)
    reality = sum(by_id[x].reality_units for x in closure)
    return (wall, count, reality, tuple(sorted(closure)))


def solve(predicates: Iterable[str], actions: Iterable[Action]) -> dict:
    preds = tuple(dict.fromkeys(str(x).strip() for x in predicates if str(x).strip()))
    action_list = list(actions)
    if not preds:
        raise CutError("PREDICATES_REQUIRED")
    if not action_list:
        raise CutError("ACTIONS_REQUIRED")
    index = {p: i for i, p in enumerate(preds)}
    full = (1 << len(preds)) - 1
    by_id = {a.action_id: a for a in action_list}
    if len(by_id) != len(action_list):
        raise CutError("DUPLICATE_ACTION_ID")

    # Validate the full dependency graph before optimizing any subset.
    for action in action_list:
        _dependency_closure(frozenset({action.action_id}), by_id)
        _critical_path_s(action.action_id, by_id, {}, set())

    coverage: dict[str, int] = {}
    for aid, a in by_id.items():
        mask = 0
        for p in a.closes:
            if p in index:
                mask |= 1 << index[p]
        coverage[aid] = mask

    # Exact set-cover DP over the current <=19 predicate Root2 surface.
    # State stores selected root actions; dependency expansion happens in _cost.
    best: dict[int, frozenset[str]] = {0: frozenset()}
    for aid in sorted(by_id):
        bit = coverage[aid]
        if bit == 0:
            continue
        snapshot = list(best.items())
        for mask, selected in snapshot:
            new_mask = mask | bit
            candidate = frozenset(set(selected) | {aid})
            incumbent = best.get(new_mask)
            if incumbent is None or _cost(candidate, by_id) < _cost(incumbent, by_id):
                best[new_mask] = candidate

    selected = best.get(full)
    if selected is None:
        covered_mask = max(
            best,
            key=lambda m: (
                m.bit_count(),
                -_cost(best[m], by_id)[0],
                -_cost(best[m], by_id)[1],
                -_cost(best[m], by_id)[2],
            ),
        )
        selected = best[covered_mask]
    else:
        covered_mask = full

    closure = _dependency_closure(selected, by_id)
    covered = [p for p, i in index.items() if covered_mask & (1 << i)]
    unresolved = [p for p, i in index.items() if not covered_mask & (1 << i)]
    wall, count, reality, _ = _cost(selected, by_id)

    return {
        "schema": SCHEMA,
        "predicate_count": len(preds),
        "covered_predicate_count": len(covered),
        "unresolved_predicate_count": len(unresolved),
        "covered_predicates": covered,
        "unresolved_predicates": unresolved,
        "selected_root_actions": sorted(selected),
        "selected_with_dependencies": sorted(closure),
        "objective": {
            "critical_path_wall_clock_s": wall,
            "action_count": count,
            "reality_units": reality,
            "lexicographic_order": ["critical_path_wall_clock_s", "action_count", "reality_units"],
        },
        "hard_nonclaim": "DECLARED_ACTION_DURATIONS_ARE_INPUTS_NOT_EMPIRICALLY_GUARANTEED_RUNTIME",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ns = ap.parse_args()
    raw = _load(Path(ns.manifest))
    preds = raw.get("predicates") or []
    actions_raw = raw.get("actions") or []
    actions = [_parse_action(x) for x in actions_raw]
    result = solve(preds, actions)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
