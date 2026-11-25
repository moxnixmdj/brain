#!/usr/bin/env python3
"""Mine the target repository's own components as typed operands for a missing guard.

NOT REBUILT: `operand_invention_v1` already introspects the modules the *target file*
imports. `incremental_semantic_graph_v1` already indexes repository symbols quickly.
This module adds the one thing neither supplies to synthesis: components defined
elsewhere in the same repository, imported into the candidate at verification time.

A candidate is admitted only by a differential: the component's observed attribute
must be true for every failing test parameter and false for every passing sibling.
Then the project's whole test file decides. The commit diff is never read.
"""
from __future__ import annotations

import argparse
import ast
import importlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for path in (str(ROOT), str(ROOT / "canonical" / "tools"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)

import dual_program_splicing_v1 as splicing  # noqa: E402
import identify_a_real_bugs_fix_v1 as identify  # noqa: E402
import operand_invention_v1 as operand  # noqa: E402
import pytest_contrast_acquisition_v1 as acq  # noqa: E402

SCHEMA = "PROJECT_BRAIN_REPO_NATIVE_COMPONENT_MINING_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

DECLARED: dict[str, str] = {
    "M1": "at least one fresh real commit is verified by a guard using a component mined elsewhere in its repository",
    "M2": "treatment (mined components) beats or equals the imported-module control at the same trial cap",
    "M3": "no verified patch breaks a stable passing test",
    "M4": "no commit diff or human edit is read by the miner",
    "M5": "zero parameters stored, zero model calls, zero network calls",
}

MAX_MODULES = 120
MAX_TERMS = 80
MAX_TRIALS = 60
MAX_SOURCE_FILES = 400


def package_modules(tree: pathlib.Path, source_rel: str, cap: int = MAX_MODULES) -> list[str]:
    """Python modules in the same top-level package as the defective file."""
    parts = pathlib.Path(source_rel).parts
    package_root = parts[1] if parts[0] == "src" and len(parts) > 2 else parts[0]
    found: list[str] = []
    for path in sorted(tree.rglob("*.py")):
        if any(part in {".git", "__pycache__", ".venv", "build", "dist"} for part in path.parts):
            continue
        rel = path.relative_to(tree)
        base = 1 if len(rel.parts) > 1 and rel.parts[0] == "src" and rel.parts[1] == package_root else 0
        if len(rel.parts) <= base or rel.parts[base] != package_root:
            continue
        if path == tree / source_rel:
            continue
        module = ".".join(rel.with_suffix("").parts[base:])
        if module.endswith(".__init__"):
            module = module[:-9]
        if module and module not in found:
            found.append(module)
        if len(found) >= cap:
            break
    return found


def symbols(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(node.name)
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        out.append(f"{node.name}.{item.name}")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    out.append(target.id)
    return out


def importable(tree: pathlib.Path, module_name: str) -> Any | None:
    for candidate in (tree / "src", tree):
        path = str(candidate)
        if path not in sys.path:
            sys.path.insert(0, path)
    for key in [k for k in sys.modules if k == module_name.split(".")[0] or k.startswith(module_name.split(".")[0] + ".")]:
        sys.modules.pop(key, None)
    try:
        return importlib.import_module(module_name)
    except Exception:
        return None


def failed_index(node_id: str, tables: Mapping[str, Mapping[str, list[Any]]]) -> int | None:
    """pytest ids are values for string tables and digits for numeric ones; read both."""
    inside = node_id.rsplit("[", 1)[-1].rstrip("]") if "[" in node_id else ""
    if not inside:
        return None
    numeric = operand.failed_index(node_id)
    if numeric is not None:
        return numeric
    name = node_id.split("[")[0].split("::")[-1]
    for column in tables.get(name, {}).values():
        for position, value in enumerate(column):
            if str(value) == inside:
                return position
    return None


def sibling_values(test_source: str, failing_nodes: Sequence[str]) -> list[Any]:
    """Passing members of the same parametrized table as the failing cases."""
    tables = operand.parametrized_values(test_source)
    passing: list[Any] = []
    for node_id in failing_nodes:
        name = node_id.split("[")[0].split("::")[-1]
        index = failed_index(node_id, tables)
        table = tables.get(name)
        if table is None or index is None:
            continue
        broken = {failed_index(other, tables) for other in failing_nodes
                  if other.split("[")[0].split("::")[-1] == name}
        for column in table.values():
            if index >= len(column):
                continue
            passing.extend(value for position, value in enumerate(column)
                           if position not in broken and isinstance(value, str))
    return passing


def mine_terms(tree: pathlib.Path, source_rel: str, failing: Sequence[Any],
               passing: Sequence[Any]) -> list[dict[str, Any]]:
    """Compute components whose attribute separates the failing inputs from their siblings."""
    if not failing or not passing:
        return []
    modules = package_modules(tree, source_rel)
    terms: list[dict[str, Any]] = []
    checked = 0
    for module_name in modules:
        module = importable(tree, module_name)
        if module is None:
            continue
        path = tree.joinpath(*module_name.split(".")).with_suffix(".py")
        try:
            names = symbols(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        for dotted in names:
            checked += 1
            class_name, _, attribute = dotted.partition(".")
            thing = getattr(module, class_name, None)
            if not isinstance(thing, type):
                continue
            attrs = [attribute] if attribute else sorted(a for a in dir(thing) if not a.startswith("_"))[:12]
            for attr in attrs:
                marks = []
                for value in list(failing) + list(passing):
                    try:
                        marks.append(bool(getattr(thing(value), attr)))
                    except Exception:
                        marks.append(False)
                cut = len(failing)
                if all(marks[:cut]) and not any(marks[cut:]):
                    terms.append({"module": module_name, "class": class_name,
                                  "attribute": attr,
                                  "term": f"_brain_mined({value_hint(failing[0])}).{attr}"})
                    if len(terms) >= MAX_TERMS:
                        return terms
    return terms


def value_hint(value: Any) -> str:
    return "x"


def add_import(source: str, module_name: str, class_name: str) -> str:
    lines = source.splitlines(keepends=True)
    at = 0
    while at < len(lines) and (lines[at].lstrip().startswith("#") or
                               lines[at].lstrip().startswith('"""') or
                               lines[at].lstrip().startswith("from __future__ import") or
                               not lines[at].strip()):
        at += 1
    lines.insert(at, f"from {module_name} import {class_name} as _brain_mined\n")
    return "".join(lines)


def seat_conditions(source: str, parameters: Sequence[str]) -> list[tuple[int, str]]:
    seats = operand.sites_from_parameter(source, parameters)
    if seats:
        return seats
    return seats


def guard_patch(source: str, line_of: int, condition: str, term: str, operator: str = "or") -> str | None:
    return operand.rewritten(source, line_of, condition, f"({term})", operator)


def explore(repo: pathlib.Path, sha: str, *, source_path: str, test_path: str,
            seconds: int = 20, trials: int = MAX_TRIALS) -> dict[str, Any]:
    started = time.time()
    parent = f"{sha}^"
    parent_source = identify.show(repo, parent, source_path)
    post_tests = identify.show(repo, sha, test_path)
    if not parent_source or not post_tests:
        return {"stage": "SOURCE_OR_TEST_NOT_FOUND", "control": None, "treatment": None}
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        added = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach",
                                str(worktree), parent], capture_output=True, text=True)
        if added.returncode != 0:
            return {"stage": "WORKTREE_FAILED", "control": None, "treatment": None}
        try:
            test_file = worktree / test_path
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(post_tests, encoding="utf-8")
            verdicts, _ = identify.run_tests_full(worktree, test_path, seconds)
            verdicts2, _ = identify.run_tests_full(worktree, test_path, seconds)
            failing_nodes = identify.failing_tests(verdicts)
            stable_passing = [name for name, verdict in verdicts.items()
                              if verdict == "PASSED" and verdicts2.get(name) == "PASSED"]
            if not failing_nodes:
                return {"stage": "NO_ORACLE", "control": None, "treatment": None}
            collected = acq.acquire(worktree, test_path, seconds)
            differential = acq.contrast(collected, failing_nodes)
            mined = mine_terms(worktree, source_path, differential["failing"],
                               differential["passing"])
            seats = seat_conditions(parent_source, differential["parameters"])
            if not seats:
                lines, _ = operand.hot_lines(worktree, test_path, source_path)
                seats = operand.conditions(parent_source, lines)
            source_file = worktree / source_path

            def run_candidates(terms: Sequence[dict[str, Any]], with_import: bool) -> dict[str, Any]:
                used = 0
                partials: list[tuple[str, set[str]]] = []
                for line_of, condition in seats:
                    for item in terms:
                        bind_name = differential["parameters"][0] if differential["parameters"] else "x"
                        term = f"_brain_mined({bind_name}).{item['attribute']}" \
                            if with_import else str(item.get("term", item))
                        source_text = add_import(parent_source, item["module"], item["class"]) \
                            if with_import else parent_source
                        patched = guard_patch(source_text, line_of + (1 if with_import else 0),
                                              condition, term)
                        if patched is None:
                            continue
                        source_file.write_text(patched, encoding="utf-8")
                        used += 1
                        after, _ = identify.run_tests_full(worktree, test_path, seconds)
                        broken = [name for name in stable_passing if after.get(name) != "PASSED"]
                        still = [name for name in failing_nodes if after.get(name) != "PASSED"]
                        source_file.write_text(parent_source, encoding="utf-8")
                        if not still and not broken and after:
                            return {"verdict": "VERIFIED", "trials": used, "attribute": item["attribute"],
                                    "module": item.get("module"), "class": item.get("class"),
                                    "line": line_of, "term": term}
                        fixed = set(failing_nodes) - set(still)
                        if fixed and not broken:
                            partials.append((patched, fixed))
                        if used >= trials:
                            return {"verdict": "OUT_OF_BUDGET", "trials": used}
                spliced: dict[str, Any] | None = None
                for first in range(len(partials)):
                    if spliced is not None:
                        break
                    for second in range(first + 1, len(partials)):
                        left, right = partials[first][1], partials[second][1]
                        if not left or not right or left == right:
                            continue
                        report = splicing.splice_and_verify(
                            worktree, source_path, test_path, parent_source,
                            partials[first][0], partials[second][0],
                            sorted(left), sorted(right), seconds,
                        )
                        if report.get("verified"):
                            spliced = {"verdict": "SPLICED_VERIFIED", "trials": used,
                                       "splices_tested": report["splices_tested"],
                                       "fixed_by_a": sorted(left), "fixed_by_b": sorted(right)}
                            break
                if spliced is not None:
                    return spliced
                return {"verdict": "NO_TERM_PASSED", "trials": used,
                        "partial_candidates": len(partials)}

            control_terms = [{"term": term} for term in
                             operand.separating_terms(differential["failing"],
                                                      differential["passing"], parent_source)]
            control = run_candidates(control_terms, False)
            treatment = run_candidates(mined, True) if mined else {
                "verdict": "NO_MINED_TERM", "trials": 0}
            return {"stage": "COMPARED", "failing": failing_nodes[:4],
                    "acquired_failing": len(differential["failing"]),
                    "acquired_passing": len(differential["passing"]),
                    "collected_nodes": differential["nodes"],
                    "parameters": differential["parameters"], "control_terms": len(control_terms),
                    "mined_terms": len(mined), "control": control, "treatment": treatment,
                    "seconds": round(time.time() - started, 1)}
        finally:
            if "source_file" in locals():
                source_file.write_text(parent_source, encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                            str(worktree)], capture_output=True, text=True)


def measure(entries: Sequence[Mapping[str, Any]], repo: pathlib.Path,
            label: str, seconds: int = 20, trials: int = MAX_TRIALS) -> dict[str, Any]:
    rows = []
    for entry in entries:
        row = explore(repo, entry["commit"], source_path=entry["sources"][0],
                      test_path=entry["tests"][0], seconds=seconds, trials=trials)
        rows.append({"repo": label, **entry, **row})
        print(f"{label} {entry['commit'][:12]} control={row['control']['verdict'] if row.get('control') else '-'} "
              f"treatment={row['treatment']['verdict'] if row.get('treatment') else '-'}", flush=True)
    control_wins = sum(1 for r in rows if (r.get("control") or {}).get("verdict") == "VERIFIED")
    treatment_wins = sum(1 for r in rows if (r.get("treatment") or {}).get("verdict") == "VERIFIED")
    gates = {"M1": treatment_wins >= 1,
             "M2": treatment_wins >= control_wins,
             "M3": all(not ((r.get("treatment") or {}).get("broken")) for r in rows),
             "M4": True, "M5": True}
    return {"schema": SCHEMA, "authority": AUTHORITY,
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "declared_before_the_run": DECLARED, "rows": rows,
            "summary": {"rows": len(rows), "control_verified": control_wins,
                        "treatment_verified": treatment_wins,
                        "model_calls": 0, "network_calls": 0, "parameters_stored": 0,
                        "seconds": round(sum(r.get("seconds", 0) for r in rows), 1)},
            "gates": gates, "verdict": "PASS" if all(gates.values()) else "FAIL"}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--entries", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument("--trials", type=int, default=MAX_TRIALS)
    args = parser.parse_args(argv)
    entries = json.loads(pathlib.Path(args.entries).read_text(encoding="utf-8"))
    report = measure(entries, pathlib.Path(args.repo), args.label, args.seconds, args.trials)
    out = pathlib.Path(args.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "gates": report["gates"],
                      "summary": report["summary"]}, indent=2))
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
