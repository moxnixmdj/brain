"""Brain-owned symbolic visual rule induction V1.

This module learns exact per-cell decision rules from raw input/output grids.
It is intentionally generic: no ARC task IDs, benchmark-specific templates, or
external learned models are used.

Scope V1
--------
* same-shape grid transformations only;
* categorical relational features derived from cells, connected components,
  local neighborhoods, grid boundaries, and symmetric correspondences;
* symbolic output actions such as KEEP, ZERO, SET_COLOR, copy-neighbor, and
  copy-symmetry;
* bounded exact decision-tree search over a declared feature set;
* fail closed when no exact rule is representable.

A learned rule is a candidate only. Promotion/generalization remain separate.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_VISUAL_SYMBOLIC_RULE_INDUCER_V1"
Grid = tuple[tuple[int, ...], ...]


class VisualRuleInductionError(ValueError):
    pass


@dataclass(frozen=True)
class CellRecord:
    record_id: int
    features: tuple[tuple[str, str], ...]
    admissible_actions: frozenset[str]


_FEATURE_COSTS = {
    "IS_ZERO": 0.5,
    "ON_GRID_EDGE": 0.6,
    "ON_GRID_CORNER": 0.7,
    "N4_NONZERO": 0.7,
    "N4_COLOR_COUNT": 0.75,
    "N8_NONZERO": 0.8,
    "N8_COLOR_COUNT": 0.85,
    "ROW_NONZERO": 0.9,
    "COL_NONZERO": 0.9,
    "COMPONENT_AREA": 0.9,
    "COMPONENT_BBOX_H": 1.0,
    "COMPONENT_BBOX_W": 1.0,
    "COMPONENT_REL_ROW": 1.0,
    "COMPONENT_REL_COL": 1.0,
    "COMPONENT_ON_BBOX_BORDER": 0.9,
    "COMPONENT_TOUCHES_GRID_EDGE": 0.9,
    "VISIBLE_LEFT_COLOR": 1.2,
    "VISIBLE_RIGHT_COLOR": 1.2,
    "VISIBLE_UP_COLOR": 1.2,
    "VISIBLE_DOWN_COLOR": 1.2,
    "VISIBLE_LEFT_DISTANCE": 1.2,
    "VISIBLE_RIGHT_DISTANCE": 1.2,
    "VISIBLE_UP_DISTANCE": 1.2,
    "VISIBLE_DOWN_DISTANCE": 1.2,
    "INPUT_COLOR": 1.5,
}

_ACTION_BASE_COST = {
    "KEEP": 0.1,
    "ZERO": 0.5,
    "COPY_LEFT": 0.7,
    "COPY_RIGHT": 0.7,
    "COPY_UP": 0.7,
    "COPY_DOWN": 0.7,
    "COPY_UP_LEFT": 0.8,
    "COPY_UP_RIGHT": 0.8,
    "COPY_DOWN_LEFT": 0.8,
    "COPY_DOWN_RIGHT": 0.8,
    "COPY_MIRROR_H": 0.6,
    "COPY_MIRROR_V": 0.6,
    "COPY_ROT180": 0.6,
}


def _grid(value: Sequence[Sequence[int]], field: str) -> Grid:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise VisualRuleInductionError(field.upper() + "_INVALID")
    rows: list[tuple[int, ...]] = []
    width: int | None = None
    for raw in value:
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
            raise VisualRuleInductionError(field.upper() + "_ROW_INVALID")
        row: list[int] = []
        for cell in raw:
            if not isinstance(cell, int) or isinstance(cell, bool) or not 0 <= cell <= 9:
                raise VisualRuleInductionError(field.upper() + "_CELL_INVALID")
            row.append(cell)
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise VisualRuleInductionError(field.upper() + "_NON_RECTANGULAR")
        rows.append(tuple(row))
    return tuple(rows)


def _shape(grid: Grid) -> tuple[int, int]:
    return len(grid), len(grid[0])


def _tolist(grid: Grid) -> list[list[int]]:
    return [list(row) for row in grid]


def _component_features(grid: Grid) -> dict[tuple[int, int], dict[str, str]]:
    h, w = _shape(grid)
    seen: set[tuple[int, int]] = set()
    out: dict[tuple[int, int], dict[str, str]] = {}
    for r in range(h):
        for c in range(w):
            color = grid[r][c]
            if color == 0 or (r, c) in seen:
                continue
            q = [(r, c)]
            seen.add((r, c))
            cells: list[tuple[int, int]] = []
            for rr, cc in q:
                cells.append((rr, cc))
                for nr, nc in ((rr - 1, cc), (rr + 1, cc), (rr, cc - 1), (rr, cc + 1)):
                    if (
                        0 <= nr < h
                        and 0 <= nc < w
                        and (nr, nc) not in seen
                        and grid[nr][nc] == color
                    ):
                        seen.add((nr, nc))
                        q.append((nr, nc))
            rs = [x[0] for x in cells]
            cs = [x[1] for x in cells]
            r0, r1 = min(rs), max(rs)
            c0, c1 = min(cs), max(cs)
            bh, bw = r1 - r0 + 1, c1 - c0 + 1
            touches = r0 == 0 or c0 == 0 or r1 == h - 1 or c1 == w - 1
            for rr, cc in cells:
                out[(rr, cc)] = {
                    "COMPONENT_AREA": str(len(cells)),
                    "COMPONENT_BBOX_H": str(bh),
                    "COMPONENT_BBOX_W": str(bw),
                    "COMPONENT_REL_ROW": str(rr - r0),
                    "COMPONENT_REL_COL": str(cc - c0),
                    "COMPONENT_ON_BBOX_BORDER": str(
                        rr in (r0, r1) or cc in (c0, c1)
                    ),
                    "COMPONENT_TOUCHES_GRID_EDGE": str(touches),
                }
    return out


def _visible(grid: Grid, r: int, c: int, dr: int, dc: int) -> tuple[int, int]:
    h, w = _shape(grid)
    d = 1
    rr, cc = r + dr, c + dc
    while 0 <= rr < h and 0 <= cc < w:
        if grid[rr][cc] != 0:
            return grid[rr][cc], d
        rr += dr
        cc += dc
        d += 1
    return -1, -1


def _features(grid: Grid, r: int, c: int, components: Mapping[tuple[int, int], Mapping[str, str]]) -> dict[str, str]:
    h, w = _shape(grid)
    n4 = 0
    n8 = 0
    n4_colors: set[int] = set()
    n8_colors: set[int] = set()
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        rr, cc = r + dr, c + dc
        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] != 0:
            n4 += 1
            n4_colors.add(grid[rr][cc])
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] != 0:
                n8 += 1
                n8_colors.add(grid[rr][cc])

    left = _visible(grid, r, c, 0, -1)
    right = _visible(grid, r, c, 0, 1)
    up = _visible(grid, r, c, -1, 0)
    down = _visible(grid, r, c, 1, 0)

    result = {
        "INPUT_COLOR": str(grid[r][c]),
        "IS_ZERO": str(grid[r][c] == 0),
        "ON_GRID_EDGE": str(r in (0, h - 1) or c in (0, w - 1)),
        "ON_GRID_CORNER": str(r in (0, h - 1) and c in (0, w - 1)),
        "N4_NONZERO": str(n4),
        "N4_COLOR_COUNT": str(len(n4_colors)),
        "N8_NONZERO": str(n8),
        "N8_COLOR_COUNT": str(len(n8_colors)),
        "ROW_NONZERO": str(sum(v != 0 for v in grid[r])),
        "COL_NONZERO": str(sum(grid[rr][c] != 0 for rr in range(h))),
        "VISIBLE_LEFT_COLOR": str(left[0]),
        "VISIBLE_RIGHT_COLOR": str(right[0]),
        "VISIBLE_UP_COLOR": str(up[0]),
        "VISIBLE_DOWN_COLOR": str(down[0]),
        "VISIBLE_LEFT_DISTANCE": str(left[1]),
        "VISIBLE_RIGHT_DISTANCE": str(right[1]),
        "VISIBLE_UP_DISTANCE": str(up[1]),
        "VISIBLE_DOWN_DISTANCE": str(down[1]),
    }
    result.update(
        components.get(
            (r, c),
            {
                "COMPONENT_AREA": "BG",
                "COMPONENT_BBOX_H": "BG",
                "COMPONENT_BBOX_W": "BG",
                "COMPONENT_REL_ROW": "BG",
                "COMPONENT_REL_COL": "BG",
                "COMPONENT_ON_BBOX_BORDER": "BG",
                "COMPONENT_TOUCHES_GRID_EDGE": "BG",
            },
        )
    )
    return result


def _cell(grid: Grid, r: int, c: int) -> int | None:
    h, w = _shape(grid)
    if 0 <= r < h and 0 <= c < w:
        return grid[r][c]
    return None


def _admissible_actions(grid: Grid, target: int, r: int, c: int) -> frozenset[str]:
    h, w = _shape(grid)
    actions: set[str] = set()
    if target == grid[r][c]:
        actions.add("KEEP")
    if target == 0:
        actions.add("ZERO")

    offsets = {
        "COPY_LEFT": (0, -1),
        "COPY_RIGHT": (0, 1),
        "COPY_UP": (-1, 0),
        "COPY_DOWN": (1, 0),
        "COPY_UP_LEFT": (-1, -1),
        "COPY_UP_RIGHT": (-1, 1),
        "COPY_DOWN_LEFT": (1, -1),
        "COPY_DOWN_RIGHT": (1, 1),
    }
    for name, (dr, dc) in offsets.items():
        value = _cell(grid, r + dr, c + dc)
        if value is not None and value == target:
            actions.add(name)

    if grid[r][w - 1 - c] == target:
        actions.add("COPY_MIRROR_H")
    if grid[h - 1 - r][c] == target:
        actions.add("COPY_MIRROR_V")
    if grid[h - 1 - r][w - 1 - c] == target:
        actions.add("COPY_ROT180")

    actions.add(f"SET_COLOR:{target}")
    return frozenset(actions)


def _action_cost(action: str) -> float:
    if action.startswith("SET_COLOR:"):
        return 2.5
    return _ACTION_BASE_COST.get(action, 3.0)


def _feature_cost(feature: str) -> float:
    return _FEATURE_COSTS.get(feature, 2.0)


def _leaf_action(records: Sequence[CellRecord]) -> str | None:
    if not records:
        return None
    common = set(records[0].admissible_actions)
    for row in records[1:]:
        common.intersection_update(row.admissible_actions)
        if not common:
            return None
    return min(common, key=lambda a: (_action_cost(a), a))


def _tree_key(tree: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        float(tree["cost"]),
        int(tree["node_count"]),
        int(tree["depth"]),
        str(tree["signature"]),
    )


def _tree_signature(tree: Mapping[str, Any]) -> str:
    if tree["kind"] == "LEAF":
        return "A(" + tree["action"] + ")"
    return (
        "F(" + tree["feature"] + ":"
        + "|".join(
            value + "=" + _tree_signature(child)
            for value, child in sorted(tree["branches"].items())
        )
        + ")"
    )


def _tree_stats(tree: Mapping[str, Any]) -> tuple[int, int]:
    if tree["kind"] == "LEAF":
        return 1, 0
    child_stats = [_tree_stats(child) for child in tree["branches"].values()]
    return 1 + sum(n for n, _ in child_stats), 1 + max(d for _, d in child_stats)


def _attach_stats(tree: dict[str, Any]) -> dict[str, Any]:
    nodes, depth = _tree_stats(tree)
    tree["node_count"] = nodes
    tree["depth"] = depth
    tree["signature"] = _tree_signature(tree)
    return tree


def _records_from_examples(examples: Sequence[Mapping[str, Any]]) -> tuple[list[CellRecord], list[Grid], list[Grid]]:
    records: list[CellRecord] = []
    inputs: list[Grid] = []
    outputs: list[Grid] = []
    rid = 0
    for i, raw in enumerate(examples):
        if not isinstance(raw, Mapping) or "input" not in raw or "output" not in raw:
            raise VisualRuleInductionError(f"EXAMPLE_{i}_INVALID")
        inp = _grid(raw["input"], f"example_{i}_input")
        out = _grid(raw["output"], f"example_{i}_output")
        if _shape(inp) != _shape(out):
            raise VisualRuleInductionError("SHAPE_CHANGE_OUT_OF_SCOPE")
        inputs.append(inp)
        outputs.append(out)
        components = _component_features(inp)
        h, w = _shape(inp)
        for r in range(h):
            for c in range(w):
                fs = _features(inp, r, c, components)
                records.append(
                    CellRecord(
                        record_id=rid,
                        features=tuple(sorted(fs.items())),
                        admissible_actions=_admissible_actions(inp, out[r][c], r, c),
                    )
                )
                rid += 1
    return records, inputs, outputs


def _feature_value(record: CellRecord, feature: str) -> str:
    return dict(record.features)[feature]


def induce(
    examples: Sequence[Mapping[str, Any]],
    *,
    max_depth: int = 4,
    max_features_per_node: int = 12,
    max_search_subproblems: int = 5000,
    max_generated_split_nodes: int = 20000,
    top_k: int = 8,
) -> dict[str, Any]:
    try:
        if not isinstance(examples, Sequence) or isinstance(examples, (str, bytes)) or not examples:
            raise VisualRuleInductionError("EXAMPLES_INVALID")
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or not 0 <= max_depth <= 8:
            raise VisualRuleInductionError("MAX_DEPTH_INVALID")
        if (
            isinstance(max_features_per_node, bool)
            or not isinstance(max_features_per_node, int)
            or max_features_per_node < 1
        ):
            raise VisualRuleInductionError("MAX_FEATURES_PER_NODE_INVALID")
        if (
            isinstance(max_search_subproblems, bool)
            or not isinstance(max_search_subproblems, int)
            or max_search_subproblems < 1
        ):
            raise VisualRuleInductionError("MAX_SEARCH_SUBPROBLEMS_INVALID")
        if (
            isinstance(max_generated_split_nodes, bool)
            or not isinstance(max_generated_split_nodes, int)
            or max_generated_split_nodes < 1
        ):
            raise VisualRuleInductionError("MAX_GENERATED_SPLIT_NODES_INVALID")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 64:
            raise VisualRuleInductionError("TOP_K_INVALID")
        records, inputs, outputs = _records_from_examples(examples)
    except VisualRuleInductionError as exc:
        return {
            "schema": SCHEMA,
            "status": "OUT_OF_SCOPE" if str(exc) == "SHAPE_CHANGE_OUT_OF_SCOPE" else "FAIL_CLOSED",
            "reason": str(exc),
            "terminal_authority": False,
        }

    record_map = {r.record_id: r for r in records}
    feature_maps = {r.record_id: dict(r.features) for r in records}
    feature_names = sorted(name for name, _ in records[0].features)
    generated_nodes = 0
    search_subproblems = 0
    search_bound_hit = False

    @lru_cache(maxsize=None)
    def search(ids: tuple[int, ...], depth_left: int) -> tuple[dict[str, Any], ...]:
        nonlocal generated_nodes, search_subproblems, search_bound_hit
        search_subproblems += 1
        if search_subproblems > max_search_subproblems:
            search_bound_hit = True
            return tuple()
        subset = [record_map[i] for i in ids]
        leaf = _leaf_action(subset)
        candidates: list[dict[str, Any]] = []
        if leaf is not None:
            candidates.append(
                _attach_stats(
                    {
                        "kind": "LEAF",
                        "action": leaf,
                        "cost": _action_cost(leaf),
                    }
                )
            )
            return tuple(candidates)

        if depth_left == 0:
            return tuple()

        scored_features: list[tuple[tuple[int, int, float, str], str, dict[str, tuple[int, ...]]]] = []
        for feature in feature_names:
            groups: dict[str, list[int]] = {}
            for row in subset:
                groups.setdefault(feature_maps[row.record_id][feature], []).append(row.record_id)
            if len(groups) <= 1:
                continue
            frozen_groups = {k: tuple(sorted(v)) for k, v in groups.items()}
            immediately_solved = sum(
                1 for group_ids in frozen_groups.values()
                if _leaf_action([record_map[i] for i in group_ids]) is not None
            )
            score = (
                -immediately_solved,
                max(len(v) for v in frozen_groups.values()),
                _feature_cost(feature),
                feature,
            )
            scored_features.append((score, feature, frozen_groups))

        scored_features.sort(key=lambda x: x[0])
        for _, feature, groups in scored_features[:max_features_per_node]:
            branch_options: list[tuple[str, tuple[dict[str, Any], ...]]] = []
            failed = False
            for value, group_ids in sorted(groups.items()):
                options = search(group_ids, depth_left - 1)
                if not options:
                    failed = True
                    break
                branch_options.append((value, options[:top_k]))
            if failed:
                continue

            combinations: list[dict[str, dict[str, Any]]] = [{}]
            for value, options in branch_options:
                nxt: list[dict[str, dict[str, Any]]] = []
                for partial in combinations:
                    for child in options:
                        row = dict(partial)
                        row[value] = child
                        nxt.append(row)
                nxt.sort(
                    key=lambda branches: (
                        sum(float(x["cost"]) for x in branches.values()),
                        sum(int(x["node_count"]) for x in branches.values()),
                        tuple(sorted((k, str(v["signature"])) for k, v in branches.items())),
                    )
                )
                combinations = nxt[:top_k]

            for branches in combinations:
                if generated_nodes >= max_generated_split_nodes:
                    search_bound_hit = True
                    break
                generated_nodes += 1
                tree = _attach_stats(
                    {
                        "kind": "SPLIT",
                        "feature": feature,
                        "branches": branches,
                        "cost": _feature_cost(feature) + sum(float(x["cost"]) for x in branches.values()),
                    }
                )
                candidates.append(tree)

        candidates.sort(key=_tree_key)
        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for tree in candidates:
            sig = str(tree["signature"])
            if sig in seen:
                continue
            seen.add(sig)
            unique.append(tree)
            if len(unique) >= top_k:
                break
        return tuple(unique)

    trees = list(search(tuple(range(len(records))), max_depth))
    trees.sort(key=_tree_key)

    if trees:
        status = "EXACT_RULES_FOUND"
    elif search_bound_hit:
        status = "SEARCH_BOUND_REACHED__NO_EXACT_RULE"
    else:
        status = "REPRESENTATION_INSUFFICIENT"

    return {
        "schema": SCHEMA,
        "status": status,
        "example_count": len(inputs),
        "cell_record_count": len(records),
        "feature_count": len(feature_names),
        "feature_names": feature_names,
        "generated_split_nodes": generated_nodes,
        "search_subproblems": search_subproblems,
        "search_bound_hit": search_bound_hit,
        "max_search_subproblems": max_search_subproblems,
        "max_generated_split_nodes": max_generated_split_nodes,
        "rules": trees[:top_k],
        "best_rule": trees[0] if trees else None,
        "next_action": (
            "VERIFY_ON_UNTOUCHED_CASES"
            if trees
            else (
                "INCREASE_SEARCH_BOUND_OR_COMPRESS_SEARCH"
                if search_bound_hit
                else "EXPAND_REPRESENTATION_OR_ACTION_LANGUAGE"
            )
        ),
        "scope": "SAME_SHAPE_PER_CELL_SYMBOLIC_DECISION_RULES",
        "external_learned_capability_calls": 0,
        "donor_runtime_required": False,
        "semantic_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }


def _apply_action(action: str, grid: Grid, r: int, c: int) -> int | None:
    h, w = _shape(grid)
    if action == "KEEP":
        return grid[r][c]
    if action == "ZERO":
        return 0
    if action.startswith("SET_COLOR:"):
        try:
            value = int(action.split(":", 1)[1])
        except ValueError:
            return None
        return value if 0 <= value <= 9 else None

    offsets = {
        "COPY_LEFT": (0, -1),
        "COPY_RIGHT": (0, 1),
        "COPY_UP": (-1, 0),
        "COPY_DOWN": (1, 0),
        "COPY_UP_LEFT": (-1, -1),
        "COPY_UP_RIGHT": (-1, 1),
        "COPY_DOWN_LEFT": (1, -1),
        "COPY_DOWN_RIGHT": (1, 1),
    }
    if action in offsets:
        dr, dc = offsets[action]
        return _cell(grid, r + dr, c + dc)
    if action == "COPY_MIRROR_H":
        return grid[r][w - 1 - c]
    if action == "COPY_MIRROR_V":
        return grid[h - 1 - r][c]
    if action == "COPY_ROT180":
        return grid[h - 1 - r][w - 1 - c]
    return None


def _tree_action(tree: Mapping[str, Any], features: Mapping[str, str]) -> str | None:
    node: Mapping[str, Any] = tree
    while node.get("kind") == "SPLIT":
        feature = node.get("feature")
        if feature not in features:
            return None
        branches = node.get("branches")
        if not isinstance(branches, Mapping):
            return None
        value = features[str(feature)]
        child = branches.get(value)
        if not isinstance(child, Mapping):
            return None
        node = child
    if node.get("kind") != "LEAF" or not isinstance(node.get("action"), str):
        return None
    return str(node["action"])


def predict(rule: Mapping[str, Any], grid: Sequence[Sequence[int]]) -> dict[str, Any]:
    try:
        g = _grid(grid, "prediction_grid")
    except VisualRuleInductionError as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": str(exc)}
    components = _component_features(g)
    h, w = _shape(g)
    out: list[list[int]] = []
    for r in range(h):
        row: list[int] = []
        for c in range(w):
            fs = _features(g, r, c, components)
            action = _tree_action(rule, fs)
            if action is None:
                return {"schema": SCHEMA, "status": "UNSEEN_FEATURE_BRANCH", "prediction": None}
            value = _apply_action(action, g, r, c)
            if value is None:
                return {"schema": SCHEMA, "status": "ACTION_UNDEFINED", "prediction": None}
            row.append(value)
        out.append(row)
    return {
        "schema": SCHEMA,
        "status": "PREDICTED",
        "prediction": out,
        "terminal_authority": False,
    }


def solve(
    task: Mapping[str, Any],
    *,
    attempts: int = 2,
    max_depth: int = 4,
    max_features_per_node: int = 12,
    max_search_subproblems: int = 5000,
    max_generated_split_nodes: int = 20000,
) -> dict[str, Any]:
    train = task.get("train")
    test = task.get("test")
    if not isinstance(train, list) or not train or not isinstance(test, list) or not test:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "TASK_INVALID"}
    result = induce(
        train,
        max_depth=max_depth,
        max_features_per_node=max_features_per_node,
        max_search_subproblems=max_search_subproblems,
        max_generated_split_nodes=max_generated_split_nodes,
        top_k=max(8, attempts * 4),
    )
    if result.get("status") != "EXACT_RULES_FOUND":
        return {
            "schema": SCHEMA,
            "status": result.get("status"),
            "induction": result,
            "attempts": [],
            "terminal_authority": False,
        }

    import json
    bundles: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rule in result["rules"]:
        predictions: list[list[list[int]]] = []
        valid = True
        for row in test:
            out = predict(rule, row["input"])
            if out.get("status") != "PREDICTED":
                valid = False
                break
            predictions.append(out["prediction"])
        if not valid:
            continue
        key = json.dumps(predictions, separators=(",", ":"))
        if key in seen:
            continue
        seen.add(key)
        bundles.append({"rule": rule, "predictions": predictions})
        if len(bundles) >= attempts:
            break

    return {
        "schema": SCHEMA,
        "status": "SOLVED_CANDIDATES" if bundles else "NO_TEST_PREDICTION",
        "induction": result,
        "attempts": bundles,
        "ambiguity_preserved": len(bundles) > 1,
        "terminal_authority": False,
    }


def score_public_task(task: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    result = solve(task, **kwargs)
    test = task.get("test", [])
    expected = [row.get("output") for row in test]
    attempts = result.get("attempts", [])
    exact = bool(expected) and all(
        any(
            len(candidate.get("predictions", [])) > i
            and candidate["predictions"][i] == expected[i]
            for candidate in attempts
        )
        for i in range(len(expected))
    )
    return {**result, "exact_task_solved": bool(exact)}
