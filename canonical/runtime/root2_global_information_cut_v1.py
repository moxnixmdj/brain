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
    if not aid or not closes:
        raise CutError("ACTION_ID_AND_CLOSES_REQUIRED")
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


def _cost(action_ids: frozenset[str], by_id: dict[str, Action]) -> tuple[float, int, int, tuple[str, ...]]:
    # Dependencies are serialized only when explicitly declared. Otherwise actions are assumed
    # parallelizable, so wall-clock is the longest selected action, not the sum.
    closure = _dependency_closure(action_ids, by_id)
    if not closure:
        return (0.0, 0, 0, ())
    wall = max(by_id[x].wall_clock_s for x in closure)
    count = sum(by_id[x].action_count for x in closure)
    reality = sum(by_id[x].reality_units for x in closure)
    return (wall, count, reality, tuple(sorted(closure)))


def solve(predicates: Iterable[str], actions: Iterable[Action]) -> dict:
    preds = tuple(dict.fromkeys(str(x).strip() for x in predicates if str(x).strip()))
    if not preds:
        raise CutError("PREDICATES_REQUIRED")
    index = {p: i for i, p in enumerate(preds)}
    full = (1 << len(preds)) - 1
    by_id = {a.action_id: a for a in actions}
    if len(by_id) == 0:
        raise CutError("ACTIONS_REQUIRED")
    if len(by_id) != len(list(actions)):
        raise CutError("DUPLICATE_ACTION_ID")

    coverage: dict[str, int] = {}
    for aid, a in by_id.items():
        mask = 0
        for p in a.closes:
            if p in index:
                mask |= 1 << index[p]
        coverage[aid] = mask

    # DP state stores the selected root action ids. Cost evaluation expands dependencies.
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
    covered_mask = full if selected is not None else max(best, key=lambda m: (m.bit_count(), -_cost(best[m], by_id)[0]))
    selected = best[covered_mask]
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
            "wall_clock_s_lower_model": wall,
            "action_count": count,
            "reality_units": reality,
            "lexicographic_order": ["wall_clock_s_lower_model", "action_count", "reality_units"],
        },
        "hard_nonclaim": "WALL_CLOCK_IS_A_SCHEDULING_LOWER_MODEL_NOT_A_RUNTIME_GUARANTEE",
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
