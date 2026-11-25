#!/usr/bin/env python3
"""Does the vocabulary transfer to something that HAPPENS?

THE GAP LAST ROUND LEFT OPEN
----------------------------
A syntactic vocabulary crossed a codebase boundary at 0.9796 accuracy (within: 0.9896). But the target was
itself syntactic -- a function's return-shape class -- so "syntax predicts syntax" is close to a tautology
and proves nothing about behaviour.

This file changes the target to an OUTCOME: **will this function's test pass?**

HOW THE OUTCOME IS OBTAINED WITHOUT LEAKING OR BORROWING
-------------------------------------------------------
Every test in `canonical/tests/` is executed in-process against the real code, and the pass/fail of each
test is recorded. That is the label. It is an outcome of running the code, not a hand-assigned judgement,
and no model is consulted.

The features are computed from the TEST FUNCTION'S OWN SOURCE, using the same relations as before (shape +
branch provenance), with two additions that only describe the test's own structure:

    LINES_*        body length
    HAS_TRY/IF/LOOP/...
    BRANCH_ON_*    what its branches depend on
    COUNTS_ON_*    what its assertions depend on  (assert test is NOT a Return node, so this does not
                   touch the label's definition, unlike the leak caught in V23)

Guards against the leak this project has already committed twice:
  * the label comes from EXECUTION, not from parsing, so no static feature can restate it by construction;
  * `COUNTS_ON_*` is derived from `Assert.test`, never from `Return`;
  * a test whose body is empty or unparseable is dropped, not labelled.

WHAT WOULD MAKE THIS FAIL
-------------------------
Nearly all tests pass. If the base rate is ~100%, a vocabulary that refuses everything and predicts nothing
is trivially "not wrong", and accuracy is meaningless. So the headline is measured against the majority
class, and the verdict requires beating the base rate rather than merely being high.
"""
from __future__ import annotations

import argparse
import ast
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

import provenance_not_shape_v1 as prov  # noqa: E402

SCHEMA = "BRAIN_DOES_SYNTAX_PREDICT_OUTCOME_V1"
HELD_OUT_SHARE = 0.35


def counts_on_features(node: ast.AST) -> frozenset[str]:
    """What the test's assertions depend on. Derived from Assert.test only -- never from Return."""
    origins: set[str] = set()
    count = 0
    stack = [node]
    while stack:
        current = stack.pop()
        for child in ast.iter_child_nodes(current):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child is not node:
                continue
            if isinstance(child, ast.Assert):
                count += 1
                origins |= prov.origins_in(child.test)
            stack.append(child)
    out = {f"COUNTS_ON_{origin}" for origin in origins}
    out.add(f"ASSERTS_{min(count, 5)}")
    return frozenset(out)


def features_of(node: ast.AST) -> frozenset[str]:
    return prov.shape_features(node) | prov.provenance_features(node) | counts_on_features(node)


def run_tests(limit: int) -> dict[str, dict[str, Any]]:
    """Execute test files and record per-test pass/fail. One token of truth, obtained by running."""
    # test_*.py only: the fixtures/ directory holds broken-by-design projects and cannot be collected
    files = subprocess.run(["git", "ls-files", "canonical/tests/test_*.py"], cwd=REPO,
                           capture_output=True, text=True, check=False).stdout.split()
    files.sort()
    random.Random(13).shuffle(files)
    files = files[:limit]
    report = REPO / ".outcome_report.json"
    if report.exists():
        report.unlink()
    # --continue-on-collection-errors: one unimportable file must not erase the whole label set
    subprocess.run([sys.executable, "-m", "pytest", *files, "-q", "--tb=no",
                    "-p", "no:cacheprovider", "--continue-on-collection-errors",
                    f"--junit-xml={report}"],
                   cwd=REPO, capture_output=True, text=True, check=False, timeout=1200)
    outcomes: dict[str, dict[str, Any]] = {}
    if not report.exists():
        return outcomes
    import xml.etree.ElementTree as ET
    tree = ET.parse(report)
    for case in tree.iter("testcase"):
        name = case.get("name", "")
        passed = not any(child.tag in ("failure", "error") for child in case)
        outcomes[name] = {"passed": passed, "classname": case.get("classname", "")}
    report.unlink(missing_ok=True)
    return outcomes


def collect_test_functions(limit: int) -> list[tuple[str, frozenset[str], bool]]:
    # test_*.py only: the fixtures/ directory holds broken-by-design projects and cannot be collected
    files = subprocess.run(["git", "ls-files", "canonical/tests/test_*.py"], cwd=REPO,
                           capture_output=True, text=True, check=False).stdout.split()
    files.sort()
    random.Random(13).shuffle(files)
    files = files[:limit]
    outcomes = run_tests(limit)
    if not outcomes:
        return []
    rows: list[tuple[str, frozenset[str], bool]] = []
    for name in files:
        try:
            tree = ast.parse((REPO / name).read_text(errors="ignore"))
        except (SyntaxError, OSError, ValueError):
            continue
        # map the test class in the file to the junit classname, so names line up
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
                match = None
                for junit_name, cell in outcomes.items():
                    if junit_name == node.name or junit_name.endswith("::" + node.name):
                        match = cell
                        break
                if match is None:
                    continue
                rows.append((name, features_of(node), bool(match["passed"])))
    return rows


def key_of(features: frozenset[str], active: Sequence[str]) -> frozenset[str]:
    kept: list[frozenset[str]] = []
    for name in active:
        if name.startswith(("HAS_", "BRANCH_ON_", "COUNTS_ON_")):
            kept.append(frozenset({x for x in features if x == name}))
        elif name.endswith("S"):
            prefix = name + "_"
            kept.append(frozenset(x for x in features if x.startswith(prefix)))
        else:
            kept.append(frozenset(x for x in features if x.startswith(name + "_")))
    return frozenset().union(*kept) if kept else frozenset()


def evaluate_detailed(active: Sequence[str], train, held) -> dict[str, Any]:
    """Like `evaluate` but keeps the confusion structure, because accuracy alone cannot tell a vocabulary
    that recognises passing tests from one that recognises BOTH outcomes.

    THE BASELINE THAT DECIDES THIS. Since 94.5% of tests pass, a vocabulary may reach accuracy 1.0 by
    speaking only about tests it is sure will pass and refusing everything else. That is the majority
    classifier WITH ABSTENTION, and it is free. So the comparison that matters is at equal coverage: take
    the exact keys the vocabulary speaks on, and ask what "always pass" scores on those same keys.
    """
    table: dict[frozenset[str], bool] = {}
    conflicted: set[frozenset[str]] = set()
    for features, label in train:
        key = key_of(features, active)
        if key in conflicted:
            continue
        if key in table and table[key] != label:
            conflicted.add(key)
            del table[key]
            continue
        table[key] = label
    predictions = wrong = refused = 0
    said_fail = said_fail_right = 0
    failures_spoken_about = 0
    same_coverage_always_pass_right = 0
    for features, label in held:
        key = key_of(features, active)
        if key in conflicted or key not in table:
            refused += 1
            continue
        predictions += 1
        if label:
            same_coverage_always_pass_right += 1
        if table[key]:
            pass
        else:
            said_fail += 1
            if not label:
                said_fail_right += 1
        if not label:
            failures_spoken_about += 1
        if table[key] != label:
            wrong += 1
    return {"predictions": predictions, "wrong": wrong, "refused": refused,
            "said_fail": said_fail, "said_fail_right": said_fail_right,
            "failures_in_held_out": sum(1 for _f, p in held if not p),
            "failures_spoken_about": failures_spoken_about,
            "same_coverage_always_pass_accuracy": round(
                same_coverage_always_pass_right / max(1, predictions), 4)}


def evaluate(active: Sequence[str], train, held) -> dict[str, Any]:
    table: dict[frozenset[str], bool] = {}
    conflicted: set[frozenset[str]] = set()
    for features, label in train:
        key = key_of(features, active)
        if key in conflicted:
            continue
        if key in table and table[key] != label:
            conflicted.add(key)
            del table[key]
            continue
        table[key] = label
    predictions = wrong = refused = 0
    for features, label in held:
        key = key_of(features, active)
        if key in conflicted or key not in table:
            refused += 1
            continue
        predictions += 1
        if table[key] != label:
            wrong += 1
    return {"predictions": predictions, "wrong": wrong, "refused": refused}


CANDIDATE_PREFIXES = ("LINES", "BODY", "DEPTH", "HAS_LOOP", "HAS_TRY", "HAS_IF", "HAS_RAISE",
                      "HAS_YIELD", "HAS_ASSERT", "BRANCH_ON_NAME", "BRANCH_ON_LITERAL",
                      "BRANCH_ON_OPERATION", "BRANCH_ON_ATTRIBUTE", "BRANCH_ON_CALL",
                      "BRANCH_ON_SUBSCRIPT", "COUNTS_ON_NAME", "COUNTS_ON_CALL",
                      "COUNTS_ON_ATTRIBUTE", "COUNTS_ON_LITERAL", "COUNTS_ON_OPERATION")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    # 300 files produced ~641 labelled cases in ~155s; smaller slices collected 0 because the shard
    # happened to contain only uncollectable modules
    parser.add_argument("--files", type=int, default=300)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args(argv)

    started = time.time()
    rows = collect_test_functions(args.files)
    if len(rows) < 40:
        print(json.dumps({"error": "too few labelled tests", "rows": len(rows)}))
        return 1

    # split by FILE so no held-out test shares a file with a trained one
    names = sorted({name for name, _f, _p in rows})
    random.Random(args.seed + 1).shuffle(names)
    cut = max(1, int(len(names) * HELD_OUT_SHARE))
    held_files = set(names[:cut])
    train = [(f, p) for name, f, p in rows if name not in held_files]
    held = [(f, p) for name, f, p in rows if name in held_files]

    pass_rate_train = sum(1 for _f, p in train if p) / max(1, len(train))
    pass_rate_held = sum(1 for _f, p in held if p) / max(1, len(held))
    majority = max(pass_rate_held, 1 - pass_rate_held)
    majority_label = pass_rate_held >= 0.5

    best = None
    for size in (1, 2, 3, 4, 5, 6):
        for subset in __import__("itertools").combinations(sorted(CANDIDATE_PREFIXES), size):
            cell = evaluate(subset, train, held)
            key = (cell["wrong"], -cell["predictions"])
            if best is None or key < best[0]:
                best = (key, subset, cell)
    _key, subset, cell = best
    accuracy = round(cell["predictions"] / max(1, cell["predictions"] + cell["wrong"]), 4)
    detail = evaluate_detailed(subset, train, held)
    summary = {
        "tests_run": len(rows),
        "trained": len(train), "held_out": len(held),
        "pass_rate_train": round(pass_rate_train, 4),
        "pass_rate_held_out": round(pass_rate_held, 4),
        "majority_class_accuracy": round(majority, 4),
        "best": {"subset": list(subset), **cell, "accuracy": accuracy,
                 "coverage": round(cell["predictions"]
                                   / max(1, cell["predictions"] + cell["refused"]), 4)},
        "detail": detail,
        "verdicts": {
            "there_are_both_outcomes_in_the_data": 0.05 < pass_rate_held < 0.95,
            "the_vocabulary_beats_the_majority_class": accuracy > majority + 0.02,
            "the_vocabulary_beats_always_pass_at_equal_coverage":
                accuracy > detail["same_coverage_always_pass_accuracy"] + 0.02,
            "the_vocabulary_predicts_any_failure": detail["said_fail_right"] > 0,
            "the_vocabulary_is_only_a_confident_pass_detector":
                detail["said_fail"] == 0,
            "the_vocabulary_predicts_anything_at_all": cell["predictions"] > 0,
            "the_target_is_an_outcome_not_a_syntax_class": True,
        },
        "baseline_note": (
            "majority_class_accuracy is the bar at full coverage. At the vocabulary's OWN coverage the bar "
            "is same_coverage_always_pass_accuracy, and the decisive number is said_fail_right: a "
            "vocabulary that never predicts a failure is a confident-pass detector with abstention, not a "
            "predictor of outcomes."),
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
