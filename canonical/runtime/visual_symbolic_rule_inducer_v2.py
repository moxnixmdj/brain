"""Brain-owned symbolic visual predicate-rule induction V2.

V2 replaces V1's observed-value multiway branches with binary predicates and an
explicit else path. This preserves exact finite induction while allowing unseen
feature values to route through a learned rule rather than fail as an unseen
categorical branch.

It reuses V1's raw feature and symbolic-action extraction.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping, Sequence

from canonical.runtime import visual_symbolic_rule_inducer_v1 as v1

SCHEMA = "PROJECT_BRAIN_VISUAL_SYMBOLIC_RULE_INDUCER_V2"
Grid = v1.Grid
CellRecord = v1.CellRecord


@dataclass(frozen=True)
class Predicate:
    feature: str
    op: str
    value: str
    cost: float

    @property
    def signature(self) -> str:
        return f"{self.feature}{self.op}{self.value}"


_NUMERIC_FEATURES = {
    "N4_NONZERO",
    "N4_COLOR_COUNT",
    "N8_NONZERO",
    "N8_COLOR_COUNT",
    "ROW_NONZERO",
    "COL_NONZERO",
    "COMPONENT_AREA",
    "COMPONENT_BBOX_H",
    "COMPONENT_BBOX_W",
    "COMPONENT_REL_ROW",
    "COMPONENT_REL_COL",
    "VISIBLE_LEFT_DISTANCE",
    "VISIBLE_RIGHT_DISTANCE",
    "VISIBLE_UP_DISTANCE",
    "VISIBLE_DOWN_DISTANCE",
}


def _predicate_cost(feature: str, op: str) -> float:
    base = v1._feature_cost(feature)
    return base + (0.15 if op == "==" else 0.25)


def _eval_predicate(predicate: Predicate, feature_map: Mapping[str, str]) -> bool:
    raw = feature_map[predicate.feature]
    if predicate.op == "==":
        return raw == predicate.value
    if predicate.op == "<=":
        try:
            return int(raw) <= int(predicate.value)
        except ValueError:
            return False
    raise ValueError("PREDICATE_OP_UNSUPPORTED")


def _candidate_predicates(
    feature_names: Sequence[str],
    feature_maps: Mapping[int, Mapping[str, str]],
    ids: Sequence[int],
) -> list[Predicate]:
    out: list[Predicate] = []
    for feature in feature_names:
        values = sorted({feature_maps[i][feature] for i in ids})
        if len(values) <= 1:
            continue
        for value in values:
            out.append(Predicate(feature, "==", value, _predicate_cost(feature, "==")))
        if feature in _NUMERIC_FEATURES:
            ints = sorted({int(x) for x in values if x not in {"BG", "True", "False"}})
            for threshold in ints[:-1]:
                out.append(
                    Predicate(
                        feature,
                        "<=",
                        str(threshold),
                        _predicate_cost(feature, "<="),
                    )
                )
    unique = {p.signature: p for p in out}
    return sorted(unique.values(), key=lambda p: (p.cost, p.signature))


def _tree_signature(tree: Mapping[str, Any]) -> str:
    if tree["kind"] == "LEAF":
        return "A(" + tree["action"] + ")"
    p = tree["predicate"]
    return (
        "P(" + p["feature"] + p["op"] + p["value"]
        + "?Y=" + _tree_signature(tree["yes"])
        + ":N=" + _tree_signature(tree["no"])
        + ")"
    )


def _tree_stats(tree: Mapping[str, Any]) -> tuple[int, int]:
    if tree["kind"] == "LEAF":
        return 1, 0
    yn, yd = _tree_stats(tree["yes"])
    nn, nd = _tree_stats(tree["no"])
    return 1 + yn + nn, 1 + max(yd, nd)


def _attach_stats(tree: dict[str, Any]) -> dict[str, Any]:
    nodes, depth = _tree_stats(tree)
    tree["node_count"] = nodes
    tree["depth"] = depth
    tree["signature"] = _tree_signature(tree)
    return tree


def _tree_key(tree: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        float(tree["cost"]),
        int(tree["node_count"]),
        int(tree["depth"]),
        str(tree["signature"]),
    )


def induce(
    examples: Sequence[Mapping[str, Any]],
    *,
    max_depth: int = 5,
    max_predicates_per_node: int = 16,
    max_search_subproblems: int = 6000,
    max_generated_split_nodes: int = 24000,
    top_k: int = 8,
) -> dict[str, Any]:
    try:
        if not isinstance(examples, Sequence) or isinstance(examples, (str, bytes)) or not examples:
            raise v1.VisualRuleInductionError("EXAMPLES_INVALID")
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or not 0 <= max_depth <= 10:
            raise v1.VisualRuleInductionError("MAX_DEPTH_INVALID")
        if (
            isinstance(max_predicates_per_node, bool)
            or not isinstance(max_predicates_per_node, int)
            or max_predicates_per_node < 1
        ):
            raise v1.VisualRuleInductionError("MAX_PREDICATES_PER_NODE_INVALID")
        if (
            isinstance(max_search_subproblems, bool)
            or not isinstance(max_search_subproblems, int)
            or max_search_subproblems < 1
        ):
            raise v1.VisualRuleInductionError("MAX_SEARCH_SUBPROBLEMS_INVALID")
        if (
            isinstance(max_generated_split_nodes, bool)
            or not isinstance(max_generated_split_nodes, int)
            or max_generated_split_nodes < 1
        ):
            raise v1.VisualRuleInductionError("MAX_GENERATED_SPLIT_NODES_INVALID")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 64:
            raise v1.VisualRuleInductionError("TOP_K_INVALID")
        records, inputs, outputs = v1._records_from_examples(examples)
    except v1.VisualRuleInductionError as exc:
        return {
            "schema": SCHEMA,
            "status": "OUT_OF_SCOPE" if str(exc) == "SHAPE_CHANGE_OUT_OF_SCOPE" else "FAIL_CLOSED",
            "reason": str(exc),
            "terminal_authority": False,
        }

    record_map = {r.record_id: r for r in records}
    feature_maps = {r.record_id: dict(r.features) for r in records}
    feature_names = sorted(feature_maps[records[0].record_id])
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
        action = v1._leaf_action(subset)
        if action is not None:
            return (
                _attach_stats(
                    {
                        "kind": "LEAF",
                        "action": action,
                        "cost": v1._action_cost(action),
                    }
                ),
            )
        if depth_left == 0:
            return tuple()

        ranked: list[
            tuple[
                tuple[int, int, float, str],
                Predicate,
                tuple[int, ...],
                tuple[int, ...],
            ]
        ] = []
        for predicate in _candidate_predicates(feature_names, feature_maps, ids):
            yes = tuple(
                i for i in ids if _eval_predicate(predicate, feature_maps[i])
            )
            yes_set = set(yes)
            no = tuple(i for i in ids if i not in yes_set)
            if not yes or not no:
                continue
            yes_leaf = v1._leaf_action([record_map[i] for i in yes]) is not None
            no_leaf = v1._leaf_action([record_map[i] for i in no]) is not None
            immediate = int(yes_leaf) + int(no_leaf)
            score = (
                -immediate,
                max(len(yes), len(no)),
                predicate.cost,
                predicate.signature,
            )
            ranked.append((score, predicate, yes, no))

        ranked.sort(key=lambda x: x[0])
        candidates: list[dict[str, Any]] = []
        for _, predicate, yes_ids, no_ids in ranked[:max_predicates_per_node]:
            yes_options = search(yes_ids, depth_left - 1)
            if not yes_options:
                continue
            no_options = search(no_ids, depth_left - 1)
            if not no_options:
                continue

            pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
            for yes_tree in yes_options[:top_k]:
                for no_tree in no_options[:top_k]:
                    pairs.append((yes_tree, no_tree))
            pairs.sort(
                key=lambda pair: (
                    float(pair[0]["cost"]) + float(pair[1]["cost"]),
                    int(pair[0]["node_count"]) + int(pair[1]["node_count"]),
                    str(pair[0]["signature"]),
                    str(pair[1]["signature"]),
                )
            )

            for yes_tree, no_tree in pairs[:top_k]:
                if generated_nodes >= max_generated_split_nodes:
                    search_bound_hit = True
                    break
                generated_nodes += 1
                tree = _attach_stats(
                    {
                        "kind": "PREDICATE",
                        "predicate": {
                            "feature": predicate.feature,
                            "op": predicate.op,
                            "value": predicate.value,
                        },
                        "yes": yes_tree,
                        "no": no_tree,
                        "cost": (
                            predicate.cost
                            + float(yes_tree["cost"])
                            + float(no_tree["cost"])
                        ),
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
        "scope": "SAME_SHAPE_PER_CELL_BINARY_PREDICATE_SYMBOLIC_RULES",
        "external_learned_capability_calls": 0,
        "donor_runtime_required": False,
        "semantic_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }


def _tree_action(tree: Mapping[str, Any], features: Mapping[str, str]) -> str | None:
    node: Mapping[str, Any] = tree
    while node.get("kind") == "PREDICATE":
        raw = node.get("predicate")
        if not isinstance(raw, Mapping):
            return None
        try:
            predicate = Predicate(
                feature=str(raw["feature"]),
                op=str(raw["op"]),
                value=str(raw["value"]),
                cost=0.0,
            )
        except KeyError:
            return None
        branch = "yes" if _eval_predicate(predicate, features) else "no"
        child = node.get(branch)
        if not isinstance(child, Mapping):
            return None
        node = child
    if node.get("kind") != "LEAF" or not isinstance(node.get("action"), str):
        return None
    return str(node["action"])


def predict(rule: Mapping[str, Any], grid: Sequence[Sequence[int]]) -> dict[str, Any]:
    try:
        g = v1._grid(grid, "prediction_grid")
    except v1.VisualRuleInductionError as exc:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": str(exc)}
    components = v1._component_features(g)
    h, w = v1._shape(g)
    out: list[list[int]] = []
    for r in range(h):
        row: list[int] = []
        for c in range(w):
            fs = v1._features(g, r, c, components)
            action = _tree_action(rule, fs)
            if action is None:
                return {"schema": SCHEMA, "status": "RULE_INVALID", "prediction": None}
            value = v1._apply_action(action, g, r, c)
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
    max_depth: int = 5,
    max_predicates_per_node: int = 16,
    max_search_subproblems: int = 6000,
    max_generated_split_nodes: int = 24000,
) -> dict[str, Any]:
    train = task.get("train")
    test = task.get("test")
    if not isinstance(train, list) or not train or not isinstance(test, list) or not test:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "reason": "TASK_INVALID"}
    result = induce(
        train,
        max_depth=max_depth,
        max_predicates_per_node=max_predicates_per_node,
        max_search_subproblems=max_search_subproblems,
        max_generated_split_nodes=max_generated_split_nodes,
        top_k=max(2, attempts),
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
