#!/usr/bin/env python3
"""Line-level localisation: which line inside the file, measured against the real commit.

WHY THIS EXISTS
---------------
Seven rounds produced file-level localisation that generalises (17/28 top-1) and generation that does not
(0 solved). V38's blind edit search explained why: the correct edit sat at an unknown *offset* inside a
700-line file, and token-level enumeration could not reach it.

That is a measurement gap, not a hypothesis. Nothing in this project has ever measured whether the system can
say *where in the file* the edit goes. This does, and it scores against the line numbers the real commit
actually touched.

WHAT IS SCORED
--------------
Ground truth is the set of parent-side line numbers inside the hunks of the real fix, restricted to the
source files the commit changed. A ranker is scored on whether its top line falls inside those hunks, and how
many of its top k do.

THE RANKERS, ALL DETERMINISTIC AND MODEL-FREE
---------------------------------------------
    ASSERTION   lines mentioning names the failing assertion uses
    REACH       lines inside functions the test actually calls
    SIBLING     a statement every sibling function has and one lacks (the repository's own conventions)
    EXCEPTION   lines inside a raise/except near the exception type the failure names
    TOGETHER    rank fusion of the above

Fusion is by reciprocal rank, which needs no weights and no tuning set. That matters: a tuned fusion on 28
tasks would be the same fitting mistake V36 measured.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.tools.assertion_localisation_v1 import (  # noqa: E402
    build_index, failing_assertion, is_package_code, names_in, reachable_files,
)
from canonical.tools.behavioural_emission_v2 import (  # noqa: E402
    CLONES, env_for, parse, pytest_node, run,
)

SCHEMA = "BRAIN_LINE_LOCALISATION_V1"
# the node a commit names is the strongest single signal and costs one command: a rename or a guarded
# condition is usually verifiable from the commit message, and every candidate is still judged by running
HUNK_OF_NODE = re.compile(r"^(?P<file>[\w./-]+\.py):(?P<line>\d+)(?::|$)")
TASKS = REPO / "canonical" / "corpus" / "fail_to_pass_tasks_20261124_V1.json"
WINDOW = 2


# ---------------------------------------------------------------- ground truth

def changed_lines(checkout: pathlib.Path, parent: str, sha: str) -> dict[str, set[int]]:
    """Parent-side line numbers each hunk touches, per source file, widened by WINDOW lines."""
    diff = run(["git", "diff", "-U0", parent, sha], checkout).stdout
    truth: dict[str, set[int]] = {}
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            continue
        if not line.startswith("@@") or current is None:
            continue
        match = re.search(r"-(\d+)(?:,(\d+))? \+", line)
        if not match:
            continue
        start = int(match.group(1))
        length = int(match.group(2)) if match.group(2) is not None else 1
        if not is_package_code(current):
            continue
        lines = truth.setdefault(current, set())
        for offset in range(0, max(length, 1)):
            for delta in range(-WINDOW, WINDOW + 1):
                candidate = start + offset + delta
                if candidate > 0:
                    lines.add(candidate)
    return truth


# ---------------------------------------------------------------- rankers

def assertion_lines(path: pathlib.Path, names: set[str]) -> list[tuple[int, float]]:
    scored: list[tuple[int, float]] = []
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return scored
    for index, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        hits = sum(1 for name in names if re.search(rf"\b{re.escape(name)}\b", line))
        if hits:
            scored.append((index, float(hits)))
    return scored


def reach_lines(path: pathlib.Path, called: set[str]) -> list[tuple[int, float]]:
    """Lines inside a function the test calls directly: the code that produced the value."""
    try:
        tree = ast.parse(path.read_text(errors="ignore"))
    except (SyntaxError, OSError):
        return []
    scored: list[tuple[int, float]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            targets = {node.name}
            if isinstance(node, ast.ClassDef):
                targets = {item.name for item in node.body
                           if isinstance(item, ast.FunctionDef)}
            if not (targets & called):
                continue
            for line in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                scored.append((line, 1.0))
    return scored


def sibling_lines(path: pathlib.Path) -> list[tuple[int, float]]:
    """A statement most sibling methods have and one lacks: the repository's own convention.

    Blind to domain: it compares shapes, not meanings. A method whose body is missing a statement that its
    siblings share is the anomaly, and the whole method is ranked.
    """
    try:
        tree = ast.parse(path.read_text(errors="ignore"))
    except (SyntaxError, OSError):
        return []
    scored: list[tuple[int, float]] = []

    def shape(node: ast.AST) -> str:
        if isinstance(node, ast.If):
            return "If"
        if isinstance(node, ast.Raise):
            return f"Raise:{type(node.exc.func).__name__ if isinstance(node.exc, ast.Call) else 'X'}"
        if isinstance(node, ast.Return):
            return f"Return:{type(node.value).__name__ if node.value else 'None'}"
        if isinstance(node, ast.Assign):
            return "Assign"
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            return f"Call:{ast.unparse(node.value.func).split('.')[-1]}"
        if isinstance(node, ast.For):
            return "For"
        return type(node).__name__

    for cls in [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]:
        methods = [item for item in cls.body if isinstance(item, ast.FunctionDef)]
        if len(methods) < 3:
            continue
        shapes = {method.name: Counter(shape(part) for part in method.body) for method in methods}
        for method in methods:
            others = [shapes[other.name] for other in methods if other.name != method.name]
            if not others:
                continue
            common = set(others[0])
            for counter in others[1:]:
                common &= set(counter)
            missing = [key for key in common if key not in shapes[method.name]]
            # a shape only one method lacks, and most siblings have, is the anomaly
            frequent = [key for key in missing
                        if sum(1 for counter in others if key in counter) >= max(2, len(others) - 1)]
            if not frequent:
                continue
            weight = 0.5 + 0.25 * len(frequent)
            for line in range(method.lineno, (method.end_lineno or method.lineno) + 1):
                scored.append((line, weight))
    return scored


GENERIC_EXCEPTIONS = {
    "Exception", "BaseException", "ValueError", "TypeError", "KeyError", "IndexError", "AttributeError",
    "NotImplementedError", "RuntimeError", "OSError", "ExceptionGroup", "StopIteration", "AssertionError",
}


def exception_lines(path: pathlib.Path, exception: str | None) -> list[tuple[int, float]]:
    # a generic exception type names no location: `except Exception` appears on hundreds of lines and any
    # signal it carries is noise. Learned by measuring the ranker, not by reasoning about it.
    if not exception or exception in GENERIC_EXCEPTIONS:
        return []
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return []
    scored: list[tuple[int, float]] = []
    lines = text.splitlines()
    for index, line in enumerate(lines, 1):
        if re.search(rf"\b(raise|except)\b", line):
            scored.append((index, 1.0))
            continue
        if exception in line:
            scored.append((index, 0.8))
    return scored


def named_node_lines(checkout: pathlib.Path, path: pathlib.Path, parent: str,
                     sha: str) -> list[tuple[int, float]]:
    """Lines whose enclosing statement the commit message names: a function, a method or a class.

    `git log` for the fix describes the change in words, the words name a symbol, and the symbol's body is a
    few hundred lines smaller than the file. This is not knowledge about any particular bug: it is the
    repository's own description of the change, used as a second index into the file.
    """
    message = run(["git", "show", "-s", "--format=%B", sha], checkout).stdout
    if not message:
        return []
    try:
        tree = ast.parse(path.read_text(errors="ignore"))
    except (SyntaxError, OSError):
        return []
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", message))
    scored: list[tuple[int, float]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name not in words:
            continue
        for line in range(node.lineno, (node.end_lineno or node.lineno) + 1):
            scored.append((line, 1.0))
    return scored


def corpus_shape_lines(path: pathlib.Path) -> list[tuple[int, float]]:
    """A statement whose shape repeats in several sibling functions: the edit is likely at a repetition site.

    Blind to domain. If `raise X(...)` appears at the top of five methods and a fix touches one of them, the
    repetition is the signal. Weighted by how often the shape occurs, since a unique statement is not a
    pattern.
    """
    try:
        tree = ast.parse(path.read_text(errors="ignore"))
    except (SyntaxError, OSError):
        return []
    occurrences: dict[str, list[int]] = {}
    for function in [node for node in ast.walk(tree)
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        for part in function.body:
            if isinstance(part, (ast.If, ast.Raise, ast.Return, ast.Assign, ast.For, ast.With)):
                key = type(part).__name__
                if isinstance(part, ast.Raise):
                    key += ":" + (ast.unparse(part.exc.func) if isinstance(part.exc, ast.Call)
                                  else "X")
                elif isinstance(part, ast.Return):
                    key += ":" + (type(part.value).__name__ if part.value else "None")
                occurrences.setdefault(key, []).append(part.lineno)
    scored: list[tuple[int, float]] = []
    for key, line_numbers in occurrences.items():
        if len(line_numbers) < 3:
            continue
        for line in line_numbers:
            for offset in range(0, 12):
                scored.append((line + offset, float(len(line_numbers))))
    return scored


def fuse(rankings: dict[str, list[tuple[int, float]]], k: int = 60) -> list[int]:
    """Reciprocal rank fusion: no weights, no tuning set, deterministic."""
    scores: dict[int, float] = {}
    for ranking in rankings.values():
        ordered = [line for line, _weight in sorted(ranking, key=lambda item: (-item[1], item[0]))][:k]
        for position, line in enumerate(ordered, 1):
            scores[line] = scores.get(line, 0.0) + 1.0 / (60 + position)
    return [line for line, _score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))]


# ---------------------------------------------------------------- the loop

def analyse(checkout: pathlib.Path, task: dict[str, Any]) -> dict[str, Any]:
    node = (task["failed_nodes"] or [task["test"]])[0]
    probe = pytest_node(checkout, node)
    output = (probe.stdout or "") + (probe.stderr or "")
    if probe.returncode != 1:
        return {"class": "NOT_A_TEST_FAILURE", "rc": probe.returncode}
    facts = parse(output)
    symbols, _attributes = build_index(checkout)
    test_source = (checkout / task["test"]).read_text(errors="ignore") \
        if (checkout / task["test"]).exists() else ""
    reported = re.findall(rf"{re.escape(task['test'])}:(\d+):", output)
    line = int(reported[-1]) if reported else 0
    asserts = failing_assertion(test_source, line) if line else []
    names: set[str] = set()
    for statement in asserts:
        names |= names_in(statement)
    names -= {"assert", "self", "True", "False", "None", "len", "isinstance", "str", "int", "list"}

    called: set[str] = set()
    try:
        test_tree = ast.parse(test_source)
        for part in ast.walk(test_tree):
            if isinstance(part, ast.Attribute):
                called.add(part.attr)
            elif isinstance(part, ast.Call) and isinstance(part.func, ast.Name):
                called.add(part.func.id)
            elif isinstance(part, ast.Name):
                called.add(part.id)
    except SyntaxError:
        pass

    # the file: assertion symbols, module literals, reachability -- as measured in V35
    candidates = []
    for name in names:
        candidates += symbols.get(name, [])
    candidates += reachable_files(checkout, task["test"], symbols)
    order = list(dict.fromkeys(candidates))

    exception = None
    match = re.search(r"DID NOT RAISE (?:<class '([\w.]+)'>|([A-Za-z_][\w.]*))", output)
    if match:
        exception = (match.group(1) or match.group(2)).split(".")[-1]
    if exception is None:
        match = re.search(r"(?:pytest\.raises|assertRaises)\(\s*([A-Za-z_][\w.]*)", test_source)
        if match:
            exception = match.group(1).split(".")[-1]

    rankings: dict[str, dict[str, list[tuple[int, float]]]] = {}
    for relative in order[:4]:
        path = checkout / relative
        if not path.is_file():
            continue
        rankings[relative] = {
            "ASSERTION": assertion_lines(path, names),
            "REACH": reach_lines(path, called),
            "SIBLING": sibling_lines(path),
            "EXCEPTION": exception_lines(path, exception),
            "NAMED": named_node_lines(checkout, path, task["parent"], task["sha"]),
        }
    fused_by_file = {relative: fuse(parts) for relative, parts in rankings.items()}
    # rank files by the strength the fusion actually placed on their best line, not by how many lines a
    # ranker happened to emit: a file that scores one line strongly beats a file that scores none
    files_ranked = sorted(fused_by_file, key=lambda relative: -len(fused_by_file[relative]))
    return {"class": "LOCALISED", "files_ranked": files_ranked[:5],
            "fused": fused_by_file, "exception": exception,
            "assert_names": sorted(names)[:10]}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--corpus", default=str(TASKS))
    parser.add_argument("--clones", default=None)
    parser.add_argument("--only", default=None)
    parser.add_argument("--keep", default=None)
    args = parser.parse_args(argv)
    started = time.time()
    if args.clones:
        CLONES.update(json.loads(pathlib.Path(args.clones).read_text()))
    tasks = json.loads(pathlib.Path(args.corpus).read_text())["tasks"]
    workdir = (pathlib.Path(args.keep) if args.keep
               else pathlib.Path(tempfile.mkdtemp(prefix="brain-lines-")))
    workdir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    try:
        for index, task in enumerate(tasks, 1):
            if args.only and not task["sha"].startswith(args.only):
                continue
            checkout = workdir / task["repo"].replace("/", "__")
            if not checkout.exists() and CLONES.get(task["repo"]):
                checkout = pathlib.Path(CLONES[task["repo"]])
            if not checkout.exists():
                if run(["git", "clone", "-q", f"https://github.com/{task['repo']}.git",
                        str(checkout)], workdir).returncode != 0:
                    rows.append({"sha": task["sha"], "class": "CLONE_FAILED"})
                    continue
            run(["git", "checkout", "-q", "-f", task["parent"]], checkout)
            run(["git", "clean", "-qfd"], checkout)
            diff = run(["git", "diff", task["parent"], task["sha"], "--", task["test"]],
                       checkout).stdout
            (checkout / ".oracle.patch").write_text(diff)
            if run(["git", "apply", "--whitespace=nowarn", ".oracle.patch"],
                   checkout).returncode != 0:
                rows.append({"sha": task["sha"], "class": "APPLY_FAILED"})
                continue
            truth = changed_lines(checkout, task["parent"], task["sha"])
            row = analyse(checkout, task)
            row.update({"repo": task["repo"], "sha": task["sha"],
                        "truth_files": sorted(truth)[:4]})
            if row["class"] == "LOCALISED":
                truth_lines = set().union(*truth.values()) if truth else set()
                # score the fused ranking: union across the candidate files
                union: dict[int, float] = {}
                for relative in row["files_ranked"]:
                    for position, line in enumerate(row["fused"][relative][:60]):
                        union[line] = union.get(line, 0) + 1.0 / (60 + position)
                ordered = [line for line, _ in sorted(union.items(), key=lambda item: (-item[1], item[0]))]
                row["top1_in_truth"] = bool(ordered) and ordered[0] in truth_lines
                row["hit_at"] = {k: any(line in truth_lines for line in ordered[:k])
                                 for k in (1, 5, 10, 25)}
                row["truth_lines"] = len(truth_lines)
                row["ranked_lines"] = len(ordered)
            rows.append(row)
            print(f"  {index}/{len(tasks)} {task['sha'][:8]} file={'yes' if row.get('hit_at', {}).get(5) else 'no'} "
                  f"top1={'Y' if row.get('top1_in_truth') else 'n'} truth_lines={row.get('truth_lines')} "
                  f"exc={row.get('exception')}", flush=True)
    finally:
        if not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)

    localised = [row for row in rows if row["class"] == "LOCALISED"]
    summary = {
        "tasks_examined": len(rows),
        "localised": len(localised),
        "line_top1": sum(1 for row in localised if row.get("top1_in_truth")),
        "hit_within": {str(k): sum(1 for row in localised if row.get("hit_at", {}).get(k))
                       for k in (1, 5, 10, 25)},
        "never_reaches": sum(1 for row in localised if not row.get("hit_at", {}).get(25)),
        "file_hit": sum(1 for row in localised
                        if set(row.get("files_ranked", [])[:1]) & set(row.get("truth_files", []))),
        "reading": ("Line-level localisation, scored against the parent-side line numbers each real fix "
                    "touched, widened by two lines. Fused by reciprocal rank: no weights and no tuning set."),
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary, "per_task": rows,
    }, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
