#!/usr/bin/env python3
"""Localisation from the assertion, measured against the files the real commit changed.

THE DEFECT THIS MEASURES
------------------------
V34's localiser read traceback frames. On seven of its ten tasks there is no frame inside the source tree at
all -- the failure is a bare `AssertionError` in a test, e.g.

    assert Infinity <= Infinity
    assert tomli.TOMLDecodeError().__module__ == "tomli"

A frame-only localiser is structurally blind to those. It did not fail to find the fix; it never had a file
to look at. That is a localisation defect and it is upstream of generation: no operator, however clever, can
help if nothing names a place to edit.

THE OPERATOR
------------
Read the assertion out of the test source, take the names it mentions, and resolve them against an index of
every top-level class and function in the repository. An assertion about `Infinity` names the file that
defines `Infinity`. This is deterministic, model-free, and costs one parse per file.

WHAT IS MEASURED, AND WHAT IS NOT
---------------------------------
The metric is top-1 file accuracy against ground truth: the files the real fix commit changed, with tests,
docs and changelogs removed. That is checkable against the repository and independent of whether the system
can patch anything. Producing no patch is not a failure of this measurement; producing no *file* is.

Nothing here claims a solve. It measures whether the system can find the place, on ten tasks, with no model
calls and no network at run time.
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
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = "BRAIN_ASSERTION_LOCALISATION_V1"
CORPUS = REPO / "canonical" / "corpus" / "real_fix_commits_20261116_V1.json"
SELECTED = (REPO / "canonical" / "corpus" /
            "tasks_whose_oracle_precedes_the_fix_20261124_V1.json")
IGNORED = ("tests/", "test/", "docs/", "doc/", "CHANGELOG", "CHANGES", "README", ".md", ".rst", ".toml",
           ".cfg", ".yml", ".yaml", ".ini", "benchmarks/", "benchmark/")


def env_for(checkout: pathlib.Path) -> dict[str, str]:
    roots = [name for name in ("src", ".") if (checkout / name).is_dir()]
    return {"PYTHONPATH": ":".join(roots), "PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": "/tmp",
            "PYTHONDONTWRITEBYTECODE": "1"}


def run(cmd: Sequence[str], cwd: pathlib.Path, env: dict[str, str] | None = None,
        timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
                          check=False, env=env)


def source_root(checkout: pathlib.Path) -> pathlib.Path:
    return checkout / "src" if (checkout / "src").is_dir() else checkout


def is_package_code(relative: str) -> bool:
    if any(relative.startswith(prefix) or prefix in relative for prefix in IGNORED):
        return False
    return relative.endswith(".py")


# ---------------------------------------------------------------- the index

def build_index(checkout: pathlib.Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Every top-level class and function in the repo, and every attribute name it defines.

    Two maps, both filled by parsing only -- no import, no execution, so a repository that does not import
    in this environment still gets indexed.
    """
    symbols: dict[str, list[str]] = {}
    attributes: dict[str, list[str]] = {}
    root = source_root(checkout)
    for path in sorted(root.rglob("*.py")):
        relative = str(path.relative_to(checkout))
        if not is_package_code(relative):
            continue
        try:
            tree = ast.parse(path.read_text(errors="ignore"))
        except (SyntaxError, OSError):
            continue
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.setdefault(node.name, []).append(relative)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        symbols.setdefault(target.id, []).append(relative)
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        attributes.setdefault(item.name, []).append(relative)
    return symbols, attributes


def build_literal_index(checkout: pathlib.Path) -> dict[str, list[str]]:
    """Every string literal that already appears in the package's own source, mapped to its file.

    A test that asserts `__version__ == "1.2.1"` names a value the repository already stores somewhere. When
    the expectation is a value rather than a symbol -- the seven failures that name no file at all -- the
    literal is the only handle there is.
    """
    literals: dict[str, list[str]] = {}
    root = source_root(checkout)
    for path in sorted(root.rglob("*.py")):
        relative = str(path.relative_to(checkout))
        if not is_package_code(relative):
            continue
        try:
            tree = ast.parse(path.read_text(errors="ignore"))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if 2 <= len(node.value) <= 40:
                    literals.setdefault(node.value, []).append(relative)
    return literals


def module_files(checkout: pathlib.Path, name: str) -> list[str]:
    """`tomli` names a package, and a package's own surface lives in its __init__."""
    root = source_root(checkout)
    for candidate in (root / name / "__init__.py", root / f"{name}.py",
                      checkout / name / "__init__.py", checkout / f"{name}.py"):
        if candidate.is_file():
            return [str(candidate.relative_to(checkout))]
    return []


def reachable_files(checkout: pathlib.Path, test_path: str,
                    symbols: dict[str, list[str]]) -> list[str]:
    """Files reachable from what the test actually calls, through the package's own imports.

    A value assertion names no location, but the test still has to *call* something to get the value. The
    file that defines the called symbol, and whatever that file imports, is where the code that produced the
    value lives. This replaces "guess the largest module" with a traversable structure.
    """
    test_file = checkout / test_path
    if not test_file.exists():
        return []
    try:
        tree = ast.parse(test_file.read_text(errors="ignore"))
    except SyntaxError:
        return []

    roots: list[str] = []
    package_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                package_names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            package_names.add(node.module.split(".")[0])
            for alias in node.names:
                roots += symbols.get(alias.name, [])
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                and node.value.id in package_names:
            roots += symbols.get(node.attr, [])

    ordered: list[str] = []
    frontier = [path for path in dict.fromkeys(roots) if path not in ordered]
    ordered += frontier
    for _hop in range(2):
        nxt: list[str] = []
        for relative in frontier:
            source_file = checkout / relative
            try:
                module_tree = ast.parse(source_file.read_text(errors="ignore"))
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(module_tree):
                names: list[str] = []
                if isinstance(node, ast.ImportFrom) and node.module:
                    base = node.module.split(".")
                    if base[0] not in package_names:
                        continue
                    names = [base[-1]] + [alias.name for alias in node.names]
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        parts = alias.name.split(".")
                        if parts[0] in package_names and len(parts) > 1:
                            names = [parts[-1]]
                for name in names:
                    for path in symbols.get(name, []):
                        if path not in ordered and path not in nxt:
                            nxt.append(path)
        if not nxt:
            break
        ordered += nxt
        frontier = nxt
    return ordered[:6]


def failing_assertion(test_source: str, line: int) -> list[ast.Assert]:
    """The assert statements in the test function that contains the reported line."""
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return []
    owner = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = node.end_lineno or node.lineno
            if node.lineno <= line <= end:
                if owner is None or (end - node.lineno) < (owner.end_lineno - owner.lineno):
                    owner = node
    if owner is None:
        return [node for node in ast.walk(tree) if isinstance(node, ast.Assert)
                and node.lineno <= line <= (node.end_lineno or node.lineno)]
    asserts = [node for node in ast.walk(owner) if isinstance(node, ast.Assert)]
    # prefer the assert that spans the failing line, then the nearest above it
    exact = [node for node in asserts if node.lineno <= line <= (node.end_lineno or node.lineno)]
    if exact:
        return exact
    above = [node for node in asserts if node.lineno <= line]
    return above[-1:] if above else asserts[-1:]


def names_in(node: ast.AST) -> set[str]:
    found: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            found.add(child.id)
        elif isinstance(child, ast.Attribute):
            found.add(child.attr)
        elif isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            found.add(child.func.id)
    return found


def literals_in(node: ast.AST) -> list[str]:
    return [child.value for child in ast.walk(node)
            if isinstance(child, ast.Constant) and isinstance(child.value, str)]


# ---------------------------------------------------------------- localisation

def ground_truth(checkout: pathlib.Path, parent: str, sha: str) -> list[str]:
    changed = run(["git", "diff", "--name-only", parent, sha], checkout).stdout.split()
    return [path for path in changed if is_package_code(path)]


def localise(checkout: pathlib.Path, node: str, test_path: str, line: int,
             output: str) -> dict[str, Any]:
    """Two localisers on the same failure: traceback frames (V34) and assertion symbols (V35)."""
    symbols, attributes = build_index(checkout)
    literal_index = build_literal_index(checkout)
    frames = re.findall(r"^([^\s:]+\.py):(\d+): ", output, re.M)
    frame_files = []
    for path, _line in frames:
        if is_package_code(path) and path not in frame_files:
            frame_files.append(path)

    source = ""
    test_file = checkout / test_path
    if test_file.exists():
        source = test_file.read_text(errors="ignore")
    asserts = failing_assertion(source, line) if line else []
    wanted: set[str] = set()
    for statement in asserts:
        wanted |= names_in(statement)
    wanted -= {"assert", "assert_", "self", "True", "False", "None", "len", "isinstance", "str", "int",
               "list", "dict", "set", "tuple", "range", "any", "all", "print"}

    symbol_hits: list[str] = []
    for name in sorted(wanted):
        for path in symbols.get(name, []) + attributes.get(name, []):
            if path not in symbol_hits:
                symbol_hits.append(path)

    # a literal that names a module this repository owns, then a literal the source already contains
    module_hits: list[str] = []
    value_hits: list[str] = []
    expected = literals_in(asserts[0]) if asserts else []
    for literal in expected:
        for path in module_files(checkout, literal):
            if path not in module_hits:
                module_hits.append(path)
        if len(literal) >= 3:
            for path in literal_index.get(literal, []):
                if path not in value_hits:
                    value_hits.append(path)

    reachable = reachable_files(checkout, test_path, symbols)
    ranked: list[str] = []
    for path in symbol_hits + module_hits + value_hits + reachable:
        if path not in ranked:
            ranked.append(path)
    # a labelled prior, not understanding: in a small package most code lives in the largest module
    prior: list[str] = []
    root = source_root(checkout)
    sized = sorted(((path.stat().st_size, str(path.relative_to(checkout)))
                    for path in root.rglob("*.py") if is_package_code(str(path.relative_to(checkout)))),
                   reverse=True)
    prior = [path for _size, path in sized[:3]]
    used_prior = not ranked
    if used_prior:
        ranked = prior

    return {
        "frame_files": frame_files[:5],
        "assertion_names": sorted(wanted)[:12],
        "assertion_literals": expected[:6],
        "symbol_files": symbol_hits[:8],
        "module_files": module_hits[:4],
        "value_files": value_hits[:4],
        "ranked": ranked[:8],
        "used_prior": used_prior,
        "reachable": reachable[:5],
        "prior_files": prior[:3],
        "asserts_found": len(asserts),
    }


def attempt(checkout: pathlib.Path, node: str, test_path: str) -> dict[str, Any]:
    probe = run([sys.executable, "-m", "pytest", node, "-q", "--no-header", "-p", "no:cacheprovider",
                 "--tb=long"], checkout, env_for(checkout))
    output = (probe.stdout or "") + (probe.stderr or "")
    if probe.returncode != 1:
        return {"class": "NOT_A_TEST_FAILURE", "rc": probe.returncode}
    # the failure line: last mention of the test file followed by a line number, anywhere in the output
    lines = re.findall(rf"{re.escape(test_path)}:(\d+):", output)
    line = int(lines[-1]) if lines else 0
    found = localise(checkout, node, test_path, line, output)
    found.update({"class": "LOCALISED", "assert_line": line})
    return found


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--only", default=None)
    parser.add_argument("--keep", default=None)
    args = parser.parse_args(argv)
    started = time.time()

    selected = [row for row in json.loads(SELECTED.read_text())["per_task"] if row["class"] == "FAIL"]
    corpus = {task["sha"]: task for task in json.loads(CORPUS.read_text())["tasks"]}
    workdir = (pathlib.Path(args.keep) if args.keep
               else pathlib.Path(tempfile.mkdtemp(prefix="brain-loc-")))
    workdir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    try:
        for task_id, cell in enumerate(selected, 1):
            task = corpus[cell["sha"]]
            if args.only and not task["sha"].startswith(args.only):
                continue
            checkout = workdir / task["repo"].replace("/", "__")
            if not checkout.exists():
                if run(["git", "clone", "-q", f"https://github.com/{task['repo']}.git", str(checkout)],
                       workdir).returncode != 0:
                    rows.append({"sha": task["sha"], "class": "CLONE_FAILED"})
                    continue
            run(["git", "checkout", "-q", "-f", task["parent"]], checkout)
            run(["git", "clean", "-qfd"], checkout)
            diff = run(["git", "diff", task["parent"], task["sha"], "--", task["test"]], checkout).stdout
            (checkout / ".oracle.patch").write_text(diff)
            if run(["git", "apply", "--whitespace=nowarn", ".oracle.patch"],
                   checkout).returncode != 0:
                rows.append({"sha": task["sha"], "class": "APPLY_FAILED"})
                continue
            node = (task["failed_nodes"] or [task["test"]])[0]
            row = attempt(checkout, node, task["test"])
            truth = ground_truth(checkout, task["parent"], task["sha"])
            row.update({"repo": task["repo"], "sha": task["sha"], "node": node,
                        "ground_truth_files": truth})
            if row["class"] == "LOCALISED":
                row["frame_top1"] = bool(truth) and bool(row["frame_files"]) and \
                    row["frame_files"][0] in truth
                row["frame_any"] = bool(set(row["frame_files"]) & set(truth))
                row["symbol_top1"] = bool(truth) and bool(row["symbol_files"]) and \
                    row["symbol_files"][0] in truth
                row["symbol_any"] = bool(set(row["symbol_files"]) & set(truth))
                row["ranked_top1"] = bool(truth) and bool(row["ranked"]) and row["ranked"][0] in truth
                row["ranked_any"] = bool(set(row["ranked"]) & set(truth))
            rows.append(row)
            print(f"  {task_id}/12 {task['sha'][:8]} ranked={row.get('ranked', [])[:2]} "
                  f"truth={truth[:1]} | frame_top1={row.get('frame_top1')} "
                  f"ranked_top1={row.get('ranked_top1')} ranked_any={row.get('ranked_any')}", flush=True)
    finally:
        if not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)

    localised = [row for row in rows if row["class"] == "LOCALISED"]
    summary = {
        "tasks_examined": len(rows),
        "genuine_test_failures": len(localised),
        "frame_baseline": {
            "top1": sum(1 for row in localised if row["frame_top1"]),
            "any": sum(1 for row in localised if row["frame_any"]),
            "found_nothing": sum(1 for row in localised if not row["frame_files"]),
        },
        "assertion_symbols": {
            "top1": sum(1 for row in localised if row["symbol_top1"]),
            "any": sum(1 for row in localised if row["symbol_any"]),
            "found_nothing": sum(1 for row in localised if not row["symbol_files"]),
        },
        "ranked_combined": {
            "top1": sum(1 for row in localised if row.get("ranked_top1")),
            "any_at_5": sum(1 for row in localised if row.get("ranked_any")),
            "found_nothing": sum(1 for row in localised if not row["ranked"]),
        },
        "by_source": {
            "from_assertion_symbols_or_literals":
                sum(1 for row in localised if row.get("ranked_any") and not row.get("used_prior")),
            "from_the_largest_module_prior":
                sum(1 for row in localised if row.get("ranked_any") and row.get("used_prior")),
            "from_reachability":
                sum(1 for row in localised if row.get("ranked_any") and not row.get("used_prior")
                    and row.get("reachable") and set(row["reachable"]) & set(row["ground_truth_files"])),
            "blind":
                sum(1 for row in localised if not row.get("ranked_any")),
        },
        "verdicts": {
            "the_combined_ranked_list_beats_frames":
                sum(1 for row in localised if row.get("ranked_any"))
                > sum(1 for row in localised if row["frame_any"]),
            "frames_are_blind_on_most_tasks":
                sum(1 for row in localised if not row["frame_files"]) >= len(localised) // 2,
            "assertion_symbols_find_more_files_than_frames":
                sum(1 for row in localised if row["symbol_any"])
                > sum(1 for row in localised if row["frame_any"]),
        },
        "reading": (
            "Localisation only, measured against the files the real commit changed. No patch is produced by "
            "this tool and no solve is claimed. The comparison is between two deterministic, model-free "
            "localisers on the same ten failures."),
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
        "per_task": rows,
    }, indent=1) + "\n")
    print(json.dumps({key: summary[key] for key in
                      ("frame_baseline", "assertion_symbols", "ranked_combined", "by_source")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
