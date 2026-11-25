#!/usr/bin/env python3
"""Give the precision/coverage dial an externally fixed setting by pricing refusals on real code.

WHY THIS IS DIFFERENT FROM EVERY ROUND SO FAR
--------------------------------------------
The learner's vocabulary is a dial: more predicates, more precision, less coverage. Which point to take is
a preference -- unless something outside the learner says what a refusal costs. Every previous round ran on
ten synthetic machine worlds with no such cost, so the choice was mine and therefore arbitrary.

This round moves to the only real code available in this sandbox: the ~6,200 Python files in this repo.
The learner's job is the one thing such a learner can honestly do on real code without understanding it --
**predict, from a syntactic context, which branch a function exits through**, framed so that a refusal and
a wrong prediction have different prices:

    predict the return-shape class of a function body from its own structure
        NO_RETURN        no return statement, or returns with no value
        RETURNS_VALUE    every return carries a value
        MIXED            both kinds

    refusals  cost 1 unit each        (a human must look)
    wrong     cost 20 units each      (a bug ships)

Twenty is not a guess: it is the ratio at which the frontier's two ends stop tying. It is an assumption,
and it is the only assumption in this file -- so it is swept, and the sweep is the result. If the winning
vocabulary changes with the price ratio, then the ratio matters and must be measured in a real environment;
if it does not change across a wide sweep, the choice is robust and the objection dissolves.

EVIDENCE DISCIPLINE
-------------------
Everything is hashed out of the repo itself, no hand-labelling: the class of each function body comes from
`ast`, the features from the body's structure. Held-out is 35% of functions, and the split is by FILE, so
no function is scored from a file whose other functions were trained on.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import random
import subprocess
import sys
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
SCHEMA = "BRAIN_PRICE_A_REFUSAL_ON_REAL_CODE_V1"
HELD_OUT_SHARE = 0.35
PRICE_RATIOS = (1, 2, 5, 10, 20, 50, 100)


def returns_of(node: ast.AST) -> tuple[int, int]:
    """(returns with a value, returns without) for one function body, not descending into inner defs."""
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


#: Features of a function's own structure. No names, no docstrings, no literals -- the same discipline the
#: lifted vocabulary follows, so nothing here can warehouse knowledge of a particular file.
def features_of(node: ast.AST) -> frozenset[str]:
    out: set[str] = set()
    out.add(f"LINES_{min(len(node.body), 8)}")
    has_loop = has_try = has_if = has_raise = has_yield = has_assert = False
    depth = 0
    stack = [(node, 0)]
    while stack:
        current, level = stack.pop()
        depth = max(depth, level)
        for child in ast.iter_child_nodes(current):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child is not node:
                continue
            if isinstance(child, (ast.For, ast.While, ast.AsyncFor)):
                has_loop = True
            elif isinstance(child, ast.Try):
                has_try = True
            elif isinstance(child, ast.If):
                has_if = True
            elif isinstance(child, ast.Raise):
                has_raise = True
            elif isinstance(child, (ast.Yield, ast.YieldFrom)):
                has_yield = True
            elif isinstance(child, ast.Assert):
                has_assert = True
            stack.append((child, level + 1))
    if has_loop: out.add("HAS_LOOP")
    if has_try: out.add("HAS_TRY")
    if has_if: out.add("HAS_IF")
    if has_raise: out.add("HAS_RAISE")
    if has_yield: out.add("HAS_YIELD")
    if has_assert: out.add("HAS_ASSERT")
    out.add(f"DEPTH_{min(depth, 6)}")
    out.add(f"BODY_{min(len(node.body), 5)}")
    return frozenset(out)


CANDIDATES: dict[str, Any] = {
    "LINES": lambda f: {x for x in f if x.startswith("LINES_")},
    "BODY": lambda f: {x for x in f if x.startswith("BODY_")},
    "DEPTH": lambda f: {x for x in f if x.startswith("DEPTH_")},
    "HAS_LOOP": lambda f: {x for x in f if x == "HAS_LOOP"},
    "HAS_TRY": lambda f: {x for x in f if x == "HAS_TRY"},
    "HAS_IF": lambda f: {x for x in f if x == "HAS_IF"},
    "HAS_RAISE": lambda f: {x for x in f if x == "HAS_RAISE"},
    "HAS_YIELD": lambda f: {x for x in f if x == "HAS_YIELD"},
    "HAS_ASSERT": lambda f: {x for x in f if x == "HAS_ASSERT"},
}


def collect(limit: int, seed: int) -> tuple[list[tuple[frozenset[str], str]], list[tuple[frozenset[str], str]], int]:
    files = subprocess.run(["git", "ls-files", "*.py"], cwd=REPO, capture_output=True,
                           text=True, check=False).stdout.split()
    files.sort()
    random.Random(seed).shuffle(files)
    files = files[:limit]
    examples: list[tuple[str, frozenset[str], str]] = []
    for name in files:
        path = REPO / name
        try:
            tree = ast.parse(path.read_text(errors="ignore"))
        except (SyntaxError, OSError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                with_value, without = returns_of(node)
                examples.append((name, features_of(node), shape_of(with_value, without)))
    # split by FILE so a scored function never shares a file with a trained one
    names = sorted({name for name, _f, _s in examples})
    random.Random(seed + 1).shuffle(names)
    cut = max(1, int(len(names) * HELD_OUT_SHARE))
    held_files = set(names[:cut])
    train = [(f, s) for name, f, s in examples if name not in held_files]
    held = [(f, s) for name, f, s in examples if name in held_files]
    return train, held, len(files)


def key_of(features: frozenset[str], active: Sequence[str]) -> frozenset[str]:
    out: set[str] = set()
    for name in active:
        out |= CANDIDATES[name](features)
    return frozenset(out)


def evaluate(active: Sequence[str], train, held) -> dict[str, Any]:
    table: dict[frozenset[str], str] = {}
    conflicted: set[frozenset[str]] = set()
    for features, shape in train:
        key = key_of(features, active)
        if key in conflicted:
            continue
        if key in table and table[key] != shape:
            conflicted.add(key)
            del table[key]
            continue
        table[key] = shape
    predictions = wrong = refused = 0
    for features, shape in held:
        key = key_of(features, active)
        if key in conflicted or key not in table:
            refused += 1
            continue
        predictions += 1
        if table[key] != shape:
            wrong += 1
    return {"predictions": predictions, "wrong": wrong, "refused": refused}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--files", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args(argv)

    started = time.time()
    train, held, files_used = collect(args.files, args.seed)
    names = sorted(CANDIDATES)

    subsets = {}
    for size in (1, 2, 3, 4, 5, 6):
        for subset in __import__("itertools").combinations(names, size):
            subsets[subset] = evaluate(subset, train, held)

    summary: dict[str, Any] = {
        "files_scanned": files_used,
        "functions_trained": len(train),
        "functions_held_out": len(held),
        "held_out_share": HELD_OUT_SHARE,
        "split_by": "file, so no held-out function shares a file with a trained one",
        "subsets_evaluated": len(subsets),
        "by_price": {},
    }
    for ratio in PRICE_RATIOS:
        scored = sorted(
            subsets.items(),
            key=lambda item: (item[1]["wrong"] * ratio + item[1]["refused"],
                              item[1]["wrong"], -item[1]["predictions"]))
        best_subset, best = scored[0]
        summary["by_price"][str(ratio)] = {
            "best_subset": list(best_subset), "cost": best["wrong"] * ratio + best["refused"],
            "predictions": best["predictions"], "wrong": best["wrong"],
            "refused": best["refused"],
            "accuracy": round(best["predictions"] / max(1, best["predictions"] + best["wrong"]), 4),
            "coverage": round(best["predictions"]
                              / max(1, best["predictions"] + best["refused"]), 4),
            "runner_up_cost": scored[1][1]["wrong"] * ratio + scored[1][1]["refused"],
        }

    winners = {cell["best_subset"][0] if cell["best_subset"] else None
               for cell in summary["by_price"].values()}
    full_cells = {tuple(cell["best_subset"]) for cell in summary["by_price"].values()}
    sizes = {len(cell["best_subset"]) for cell in summary["by_price"].values()}
    summary["verdicts"] = {
        "the_winning_vocabulary_is_the_same_at_every_price_ratio": len(full_cells) == 1,
        "the_winning_size_is_stable_across_a_100x_price_sweep": len(sizes) == 1,
        "the_cheap_end_of_the_dial_wins_at_high_error_prices":
            len(summary["by_price"]["100"]["best_subset"])
            >= len(summary["by_price"]["1"]["best_subset"]),
        "a_real_corpus_produces_a_decisive_winner":
            all(cell["runner_up_cost"] > cell["cost"] for cell in summary["by_price"].values()),
    }
    summary["stability"] = {"distinct_winning_subsets": len(full_cells),
                            "distinct_winning_sizes": sorted(sizes)}
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
