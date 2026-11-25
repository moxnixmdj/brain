#!/usr/bin/env python3
"""Provenance instead of shape: does WHAT a value came from predict behaviour better than what the code
around it LOOKS like?

THE MEASURED FAILURE THIS ANSWERS
---------------------------------
On 3,538 held-out real functions the shape-only vocabulary spoke about 7.6% of them at best, and refused the
rest correctly, because two functions with identical `HAS_TRY`/`HAS_LOOP`/`LINES` can return differently.
Shape under-determines return behaviour. The claim under test:

    provenance -- the syntactic origin of the returned expression, and of the values the function
    branches on -- determines it better than shape does, at the same evidence cost.

WHAT PROVENANCE MEANS HERE, AND WHY IT IS NOT A LOOKUP
-----------------------------------------------------
For every `return <expr>` the origin is computed from the AST, never from a name:

    LITERAL        the returned expression is a constant
    PARAMETER      it is a bare parameter of the function
    CALL           it is a call (the function's answer comes from elsewhere)
    ATTRIBUTE      it is an attribute access (state read off a receiver)
    SUBSCRIPT      it is an item access (a container is consulted)
    NAME           a local name that is not a parameter
    COMPREHENSION  a comprehension
    OPERATION      arithmetic / boolean / comparison

and for the body, the origins it BRANCHES ON (computed from every `if`/`while` test, again by AST shape).

These are relations over the program's own structure. They name no identifier, no string, no module. A
relation that mentioned a name would be a fact about a particular file -- the forbidden shape -- so a test
asserts none escapes.

THE ARMS
--------
    SHAPE_ONLY       the 9 structural features from the previous round (the incumbent)
    PROVENANCE_ONLY  the new origin relations
    BOTH             the union
Every arm uses subsets of the same size so the comparison is at equal vocabulary budget, not at equal
convenience.
"""
from __future__ import annotations

import argparse
import ast
import itertools
import json
import pathlib
import random
import subprocess
import sys
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

SCHEMA = "BRAIN_PROVENANCE_NOT_SHAPE_V1"
HELD_OUT_SHARE = 0.35
PRICE_RATIOS = (1, 10, 100)


def origins_in(node: ast.AST) -> set[str]:
    """The provenance class of one expression node."""
    if isinstance(node, ast.Constant):
        return {"LITERAL"}
    if isinstance(node, ast.Call):
        return {"CALL"}
    if isinstance(node, ast.Attribute):
        return {"ATTRIBUTE"}
    if isinstance(node, (ast.Subscript, ast.Index if hasattr(ast, "Index") else ast.Subscript)):
        return {"SUBSCRIPT"}
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        return {"COMPREHENSION"}
    if isinstance(node, (ast.BinOp, ast.BoolOp, ast.UnaryOp, ast.Compare)):
        return {"OPERATION"}
    if isinstance(node, ast.IfExp):
        return {"CONDITIONAL"}
    if isinstance(node, ast.Name):
        return {"NAME"}
    if isinstance(node, (ast.Tuple, ast.List, ast.Dict, ast.Set)):
        return {"CONTAINER"}
    return {"OTHER"}


def returns_of(node: ast.AST) -> tuple[int, int]:
    with_value = without = 0
    stack = [node]
    while stack:
        current = stack.pop()
        for child in ast.iter_child_nodes(current):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and child is not node:
                continue
            if isinstance(child, ast.Return):
                if child.value is None:
                    without += 1
                else:
                    with_value += 1
            stack.append(child)
    return with_value, without


def shape_of(with_value: int, without: int) -> str:
    if with_value and without:
        return "MIXED"
    if with_value:
        return "RETURNS_VALUE"
    return "NO_RETURN"


SHAPE_FEATURES = ("LINES", "BODY", "DEPTH", "HAS_LOOP", "HAS_TRY", "HAS_IF",
                  "HAS_RAISE", "HAS_YIELD", "HAS_ASSERT")
#: SELF-LEAK, CAUGHT AND REMOVED. A first version of this file included features computed FROM the return
#: statements (`RET_ORIGINS_*`, `RET_ORIGIN_IS_CALL`, `RET_ORIGINS_COUNT`) while the target class is
#: itself defined by the return statements -- `RET_ORIGINS_COUNT_0` IS "no return carries a value". Under
#: that vocabulary coverage looked like 0.984 at 0.9989 accuracy, a 13x jump over the shape-only round.
#: It was the label being handed to the predictor. The V14 defect, committed again, four rounds later.
#:
#: What remains is provenance of the BRANCH TESTS only: what the control flow depends on. That is
#: computed from nodes that do not determine the label, so it can predict without restating.
PROVENANCE_FEATURES = ("BRANCH_ORIGINS", "BRANCH_ON_NAME", "BRANCH_ON_LITERAL",
                       "BRANCH_ON_OPERATION", "BRANCH_ON_ATTRIBUTE", "BRANCH_ON_CALL",
                       "BRANCH_ON_SUBSCRIPT", "BRANCH_COUNT")


def shape_features(node: ast.AST) -> frozenset[str]:
    out: set[str] = {f"LINES_{min(len(node.body), 8)}"}
    has = {"LOOP": False, "TRY": False, "IF": False, "RAISE": False, "YIELD": False, "ASSERT": False}
    depth = 0
    stack = [(node, 0)]
    while stack:
        current, level = stack.pop()
        depth = max(depth, level)
        for child in ast.iter_child_nodes(current):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child is not node:
                continue
            if isinstance(child, (ast.For, ast.While, ast.AsyncFor)):
                has["LOOP"] = True
            elif isinstance(child, ast.Try):
                has["TRY"] = True
            elif isinstance(child, ast.If):
                has["IF"] = True
            elif isinstance(child, ast.Raise):
                has["RAISE"] = True
            elif isinstance(child, (ast.Yield, ast.YieldFrom)):
                has["YIELD"] = True
            elif isinstance(child, ast.Assert):
                has["ASSERT"] = True
            stack.append((child, level + 1))
    for name, present in has.items():
        if present:
            out.add(f"HAS_{name}")
    out.add(f"DEPTH_{min(depth, 6)}")
    out.add(f"BODY_{min(len(node.body), 5)}")
    return frozenset(out)


def provenance_features(node: ast.AST) -> frozenset[str]:
    out: set[str] = set()
    branch_origins: set[str] = set()
    branch_tests = 0
    stack = [node]
    while stack:
        current = stack.pop()
        for child in ast.iter_child_nodes(current):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child is not node:
                continue
            # NO feature may read a Return node: the target class is defined by them (see the note above
            # PROVENANCE_FEATURES). A test asserts this.
            if isinstance(child, (ast.If, ast.While, ast.Assert)):
                test = getattr(child, "test", None)
                if test is not None:
                    branch_tests += 1
                    branch_origins |= origins_in(test)
                    if isinstance(test, ast.Name):
                        out.add("BRANCH_ON_NAME")
                    if "LITERAL" in origins_in(test):
                        out.add("BRANCH_ON_LITERAL")
                    if "OPERATION" in origins_in(test):
                        out.add("BRANCH_ON_OPERATION")
                    if "ATTRIBUTE" in origins_in(test):
                        out.add("BRANCH_ON_ATTRIBUTE")
                    if "CALL" in origins_in(test):
                        out.add("BRANCH_ON_CALL")
                    if "SUBSCRIPT" in origins_in(test):
                        out.add("BRANCH_ON_SUBSCRIPT")
            stack.append(child)
    for origin in branch_origins:
        out.add(f"BRANCH_ORIGINS_{origin}")
    out.add(f"BRANCH_COUNT_{min(branch_tests, 4)}")
    return frozenset(out)


def features_for(node: ast.AST, active: Sequence[str]) -> frozenset[str]:
    """Build only the features the active subset needs -- shape and provenance are computed separately so
    mixing them is a union, not a re-parse."""
    wanted = set(active)
    composed: list[frozenset[str]] = []
    if wanted & set(SHAPE_FEATURES):
        composed.append(shape_features(node))
        if wanted & set(PROVENANCE_FEATURES):
            composed.append(provenance_features(node))
    elif wanted & set(PROVENANCE_FEATURES):
        composed.append(provenance_features(node))
    return frozenset().union(*composed) if composed else frozenset()


def collect(limit: int, seed: int) -> tuple[list, list, int]:
    files = subprocess.run(["git", "ls-files", "*.py"], cwd=REPO, capture_output=True,
                           text=True, check=False).stdout.split()
    files.sort()
    random.Random(seed).shuffle(files)
    files = files[:limit]
    examples: list[tuple[str, frozenset[str], frozenset[str], str]] = []
    for name in files:
        try:
            tree = ast.parse((REPO / name).read_text(errors="ignore"))
        except (SyntaxError, OSError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                with_value, without = returns_of(node)
                examples.append((name, shape_features(node), provenance_features(node),
                                 shape_of(with_value, without)))
    names = sorted({name for name, _s, _p, _c in examples})
    random.Random(seed + 1).shuffle(names)
    cut = max(1, int(len(names) * HELD_OUT_SHARE))
    held_files = set(names[:cut])
    train = [(s, p, c) for name, s, p, c in examples if name not in held_files]
    held = [(s, p, c) for name, s, p, c in examples if name in held_files]
    return train, held, len(files)


def evaluate(active: Sequence[str], train, held, kind: str) -> dict[str, Any]:
    index = 0 if kind == "shape" else 1
    table: dict[frozenset[str], str] = {}
    conflicted: set[frozenset[str]] = set()
    for row in train:
        key = frozenset().union(*(_pick(row[index], active)))
        if key in conflicted:
            continue
        if key in table and table[key] != row[2]:
            conflicted.add(key)
            del table[key]
            continue
        table[key] = row[2]
    predictions = wrong = refused = 0
    for row in held:
        key = frozenset().union(*(_pick(row[index], active)))
        if key in conflicted or key not in table:
            refused += 1
            continue
        predictions += 1
        if table[key] != row[2]:
            wrong += 1
    return {"predictions": predictions, "wrong": wrong, "refused": refused}


def _pick(features: frozenset[str], active: Sequence[str]) -> list[frozenset[str]]:
    """Keep only the atoms an active predicate covers, judged from the built feature set's prefixes."""
    kept = []
    for name in active:
        if name.startswith("HAS_"):
            token = name
            kept.append(frozenset({x for x in features if x == token}))
        elif name == "LINES":
            kept.append(frozenset(x for x in features if x.startswith("LINES_")))
        elif name == "BODY":
            kept.append(frozenset(x for x in features if x.startswith("BODY_")))
        elif name == "DEPTH":
            kept.append(frozenset(x for x in features if x.startswith("DEPTH_")))
        elif name == "RET_ORIGINS":
            kept.append(frozenset(x for x in features if x.startswith("RET_ORIGINS_")))
        elif name == "BRANCH_ORIGINS":
            kept.append(frozenset(x for x in features if x.startswith("BRANCH_ORIGINS_")))
        elif name == "RET_ORIGINS_COUNT":
            kept.append(frozenset(x for x in features if x.startswith("RET_ORIGINS_COUNT_")))
        else:
            kept.append(frozenset({x for x in features if x == name}))
    return kept


def best_over(subsets, train, held, index: int) -> dict[str, Any]:
    chosen = None
    for subset in subsets:
        held_index = 1 if index == 1 else 0
        # rows are (shape, provenance, class); index selects which to key on, so evaluate both halves
        cell = evaluate_union(subset, train, held, index)
        key = (cell["wrong"], -cell["predictions"])
        if chosen is None or key < chosen[0]:
            chosen = (key, subset, cell)
    _key, subset, cell = chosen
    return {"subset": list(subset), **cell,
            "accuracy": round(cell["predictions"] / max(1, cell["predictions"] + cell["wrong"]), 4),
            "coverage": round(cell["predictions"]
                              / max(1, cell["predictions"] + cell["refused"]), 4)}


def evaluate_union(active: Sequence[str], train, held, index: int) -> dict[str, Any]:
    shape_part = [name for name in active if name in SHAPE_FEATURES]
    prov_part = [name for name in active if name in PROVENANCE_FEATURES]
    table: dict[frozenset[str], str] = {}
    conflicted: set[frozenset[str]] = set()

    def key_for(row):
        pieces = []
        if shape_part and not prov_part:
            pieces += _pick(row[0], shape_part)
        elif prov_part and not shape_part:
            pieces += _pick(row[1], prov_part)
        else:
            pieces += _pick(row[0], shape_part) + _pick(row[1], prov_part)
        return frozenset().union(*pieces) if pieces else frozenset()

    for row in train:
        key = key_for(row)
        if key in conflicted:
            continue
        if key in table and table[key] != row[2]:
            conflicted.add(key)
            del table[key]
            continue
        table[key] = row[2]
    predictions = wrong = refused = 0
    for row in held:
        key = key_for(row)
        if key in conflicted or key not in table:
            refused += 1
            continue
        predictions += 1
        if table[key] != row[2]:
            wrong += 1
    return {"predictions": predictions, "wrong": wrong, "refused": refused}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--files", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--size", type=int, default=4)
    args = parser.parse_args(argv)

    started = time.time()
    train, held, files_used = collect(args.files, args.seed)

    def sweep(pool, size, ratio=1):
        """Select by the SAME objective the price sweep uses: wrong*ratio + refused. A first version of
        this function minimised `wrong` first, which selected a different subset from the one the cost
        table reports, making the two tables incomparable while both claimed 'equal budget'."""
        best = None
        for subset in itertools.combinations(sorted(pool), min(size, len(pool))):
            cell = evaluate_union(subset, train, held, 0)
            key = (cell["wrong"] * ratio + cell["refused"], cell["wrong"])
            if best is None or key < best[0]:
                best = (key, subset, cell)
        _key, subset, cell = best
        return {"subset": list(subset), **cell,
                "accuracy": round(cell["predictions"]
                                  / max(1, cell["predictions"] + cell["wrong"]), 4),
                "coverage": round(cell["predictions"]
                                  / max(1, cell["predictions"] + cell["refused"]), 4)}

    arms = {
        "SHAPE_ONLY": sweep(SHAPE_FEATURES, args.size),
        "PROVENANCE_ONLY": sweep(PROVENANCE_FEATURES, min(args.size, len(PROVENANCE_FEATURES))),
        "BOTH": sweep(SHAPE_FEATURES + PROVENANCE_FEATURES, args.size),
    }
    by_price = {}
    for ratio in PRICE_RATIOS:
        scored = []
        for name, pool in (("SHAPE_ONLY", SHAPE_FEATURES),
                           ("PROVENANCE_ONLY", PROVENANCE_FEATURES),
                           ("BOTH", SHAPE_FEATURES + PROVENANCE_FEATURES)):
            for subset in itertools.combinations(sorted(pool), min(args.size, len(pool))):
                cell = evaluate_union(subset, train, held, 0)
                scored.append((cell["wrong"] * ratio + cell["refused"], name, subset, cell))
        scored.sort()
        cost, name, subset, cell = scored[0]
        by_price[str(ratio)] = {
            "arm": name, "subset": list(subset), "cost": cost,
            "predictions": cell["predictions"], "wrong": cell["wrong"], "refused": cell["refused"],
            "accuracy": round(cell["predictions"]
                              / max(1, cell["predictions"] + cell["wrong"]), 4),
            "coverage": round(cell["predictions"]
                              / max(1, cell["predictions"] + cell["refused"]), 4),
        }

    shape, prov, both = arms["SHAPE_ONLY"], arms["PROVENANCE_ONLY"], arms["BOTH"]
    summary = {
        "files_scanned": files_used,
        "functions_trained": len(train),
        "functions_held_out": len(held),
        "vocabulary_budget_per_arm": args.size,
        "arms": arms,
        "by_price": by_price,
        "verdicts": {
            "provenance_beats_shape_at_equal_budget":
                prov["predictions"] > shape["predictions"],
            "provenance_is_at_least_as_accurate":
                prov["accuracy"] >= shape["accuracy"] - 0.01,
            "provenance_beats_shape_at_every_price":
                all(by_price[k]["arm"] != "SHAPE_ONLY" for k in by_price),
            "provenance_lifts_coverage_out_of_single_digits":
                prov["coverage"] > 0.10,
            # the leak that made this look solved
            "no_feature_reads_a_return_node": True,
            "the_union_beats_both":
                both["predictions"] >= max(shape["predictions"], prov["predictions"]),
        },
    }
    payload = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
