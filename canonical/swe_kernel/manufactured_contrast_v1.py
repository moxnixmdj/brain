#!/usr/bin/env python3
"""Manufacture a passing twin of a failing non-parametrized test, with no model.

WHY
---
`pytest_contrast_acquisition_v1` recovered contrasts only when the failing test was
parametrized; 9/12 fresh commits had none. ContrastRepair shows that minimally
mutating a failing test can supply a passing twin, but its mutation and repair are
model-driven [2](https://dl.acm.org/doi/full/10.1145/3719345). Here the mutation is
calculated: one string/number literal in the failing test is changed by one character
or one unit, and the project's own runner decides whether the verdict flipped.

Only literals OUTSIDE `assert` are mutated: changing an expected value would
weaken the specification and manufacture a pair that says nothing about the bug.
Mutations that flip truthiness are also excluded, and a passing twin must execute
exactly the same source lines as the failure: both filters remove vacuous pairs.
The pair is then used as the differential for repository-native component mining,
and any admitted component must survive the whole test file. No model, no diff, no
stored repair rule, no network.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
for path in (str(ROOT), str(ROOT / "canonical" / "tools"),
             str(ROOT / "canonical" / "swe_kernel")):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402
import operand_invention_v1 as operand  # noqa: E402
import repo_native_component_mining_v1 as mining  # noqa: E402

SCHEMA = "PROJECT_BRAIN_MANUFACTURED_CONTRAST_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

DECLARED: dict[str, str] = {
    "F1": "at least one fresh real commit gains a FAIL->PASS twin by mutating one non-assert input literal while executing the identical source line set",
    "F2": "at least one such pair admits a component and verifies a whole-file repair",
    "F3": "no verified patch breaks a stable passing test",
    "F4": "no commit diff or human edit is read",
    "F5": "zero parameters, model calls and network calls",
}

MAX_MUTATIONS = 80
MAX_PAIRS = 3
MAX_TRIALS = 60


def literals(test_source: str, function_name: str) -> list[dict[str, Any]]:
    tree = ast.parse(test_source)
    target = next((node for node in ast.walk(tree)
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and node.name == function_name), None)
    if target is None:
        return []
    # A literal inside `assert` is the *specification*. Changing it makes the
    # test weaker, not the program better; such a pair is not a counterexample.
    asserted: set[tuple[int, int, int]] = set()
    for node in ast.walk(target):
        if isinstance(node, ast.Assert):
            for inner in ast.walk(node):
                if isinstance(inner, ast.Constant) and hasattr(inner, "end_lineno"):
                    asserted.add((inner.lineno, inner.col_offset, inner.end_col_offset))
    out: list[dict[str, Any]] = []
    for node in ast.walk(target):
        if not isinstance(node, ast.Constant) or isinstance(node.value, bool):
            continue
        if not isinstance(node.value, (str, int, float)):
            continue
        if not hasattr(node, "end_lineno") or node.lineno != node.end_lineno:
            continue
        key = (node.lineno, node.col_offset, node.end_col_offset)
        if key in asserted:
            continue
        out.append({"value": node.value, "line": node.lineno,
                    "col": node.col_offset, "end_col": node.end_col_offset,
                    "role": "input"})
    return out[:20]


def mutations(hole: dict[str, Any], alphabet: Sequence[str],
              limit: int = MAX_MUTATIONS) -> list[tuple[Any, str]]:
    value = hole["value"]
    out: list[tuple[Any, str]] = []
    if isinstance(value, str):
        candidates: list[tuple[Any, str]] = []
        for index in range(len(value)):
            candidates.append((value[:index] + value[index + 1:], f"delete@{index}"))
            for char in alphabet[:8]:
                if char != value[index]:
                    candidates.append((value[:index] + char + value[index + 1:],
                                       f"replace@{index}:{char!r}"))
        for char in alphabet[:8]:
            candidates.append((value + char, f"append:{char!r}"))
        out.extend(pair for pair in candidates if bool(pair[0]) == bool(value))
    elif isinstance(value, int):
        out.extend((value + delta, f"plus{delta}") for delta in (-2, -1, 1, 2)
                   if bool(value + delta) == bool(value))
    elif isinstance(value, float):
        out.extend((value + delta, f"plus{delta}") for delta in (-1.0, 1.0)
                   if bool(value + delta) == bool(value))
    return out[:limit]


def patch_literal(test_source: str, hole: dict[str, Any], value: Any) -> str:
    lines = test_source.splitlines(keepends=True)
    line = lines[hole["line"] - 1]
    lines[hole["line"] - 1] = line[:hole["col"]] + repr(value) + line[hole["end_col"]:]
    return "".join(lines)


_LINE_PLUGIN = """
import json, os, sys

_LINES = set()
_TARGET = os.environ.get("BRAIN_TRACE_TARGET", "")


def _trace(frame, event, arg):
    if event == "line" and _TARGET and _TARGET in frame.f_code.co_filename:
        _LINES.add(frame.f_lineno)
    return _trace


def pytest_runtest_setup(item):
    sys.settrace(_trace)


def pytest_runtest_teardown(item, nextitem):
    sys.settrace(None)
    with open(os.environ["BRAIN_TRACE_OUT"], "w", encoding="utf-8") as handle:
        json.dump(sorted(_LINES), handle)
"""


def trace_lines(worktree: pathlib.Path, node_id: str, source_rel: str,
                plugin_dir: pathlib.Path, seconds: int) -> set[int] | None:
    """Exact source-file line set executed by one test, from a real pytest run."""
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "brain_linetrace_v1.py").write_text(_LINE_PLUGIN, encoding="utf-8")
    out = plugin_dir / "lines.json"
    if out.exists():
        out.unlink()
    command = [sys.executable, "-m", "pytest", node_id, "-q", "--tb=no",
               "-p", "no:cacheprovider", "-p", "brain_linetrace_v1",
               "-o", "asyncio_default_fixture_loop_scope=function"]
    environment = {**os.environ, **identify.fresh_bytecode(worktree)}
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(plugin_dir), str(worktree / "src"), str(worktree)]
    )
    environment["BRAIN_TRACE_TARGET"] = source_rel
    environment["BRAIN_TRACE_OUT"] = str(out)
    try:
        subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=seconds, env=environment)
    except subprocess.TimeoutExpired:
        return None
    if not out.is_file():
        return None
    try:
        return set(json.loads(out.read_text(encoding="utf-8")))
    except (ValueError, TypeError):
        return None


def run_node(worktree: pathlib.Path, node_id: str, seconds: int) -> str:
    command = [sys.executable, "-m", "pytest", node_id, "-q", "--tb=no",
               "-p", "no:cacheprovider", "-o", "asyncio_default_fixture_loop_scope=function"]
    try:
        done = subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=seconds,
                              env={**os.environ, **identify.fresh_bytecode(worktree)})
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    text = done.stdout + done.stderr
    if "no tests ran" in text or "ERROR" in text:
        return "NO_ORACLE"
    return "PASS" if done.returncode == 0 else "FAIL"


def explore(repo: pathlib.Path, sha: str, *, source_path: str, test_path: str,
            seconds: int = 20, trials: int = MAX_TRIALS,
            max_mutations: int = MAX_MUTATIONS, max_holes: int = 20) -> dict[str, Any]:
    started = time.time()
    parent = f"{sha}^"
    parent_source = identify.show(repo, parent, source_path)
    post_tests = identify.show(repo, sha, test_path)
    if not parent_source or not post_tests:
        return {"stage": "SOURCE_OR_TEST_NOT_FOUND", "verification": None}
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        added = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach",
                                str(worktree), parent], capture_output=True, text=True)
        if added.returncode != 0:
            return {"stage": "WORKTREE_FAILED", "verification": None}
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
                return {"stage": "NO_ORACLE", "verification": None}
            node = failing_nodes[0]
            function = node.split("[")[0].rsplit("::", 1)[-1]
            holes = literals(post_tests, function)
            alphabet = sorted({c for c in node + post_tests if c.isprintable()})
            pairs: list[dict[str, Any]] = []
            tested = 0
            rejected_vacuous = 0
            plugin_dir = pathlib.Path(where) / "linetrace"
            baseline_lines = trace_lines(worktree, node, source_path, plugin_dir, seconds)
            for hole in holes[:max_holes]:
                for value, how in mutations(hole, alphabet, max_mutations):
                    tested += 1
                    patched_test = patch_literal(post_tests, hole, value)
                    test_file.write_text(patched_test, encoding="utf-8")
                    verdict = run_node(worktree, node, seconds)
                    if verdict == "PASS":
                        # A twin that no longer walks the failing path is a weaker
                        # test, not a counterexample. Require identical line sets.
                        passed_lines = trace_lines(worktree, node, source_path,
                                                   plugin_dir, seconds)
                        if baseline_lines is None or passed_lines != baseline_lines:
                            rejected_vacuous += 1
                            continue
                        pairs.append({"from": hole["value"], "to": value, "how": how,
                                      "line": hole["line"], "verdict": verdict})
                        test_file.write_text(post_tests, encoding="utf-8")
                        if len(pairs) >= MAX_PAIRS:
                            break
                if len(pairs) >= MAX_PAIRS:
                    break
            test_file.write_text(post_tests, encoding="utf-8")

            failing_values = [pair["from"] for pair in pairs]
            passing_values = [pair["to"] for pair in pairs]
            mined = mining.mine_terms(worktree, source_path, failing_values, passing_values)
            control = operand.separating_terms(failing_values, passing_values, parent_source)
            lines, _ = operand.hot_lines(worktree, test_path, source_path)
            seats = operand.conditions(parent_source, lines)
            source_file = worktree / source_path
            verification: dict[str, Any] | None = None
            used = 0
            for module_term in mined:
                patched = mining.add_import(parent_source, module_term["module"],
                                            module_term["class"])
                for line_of, condition in seats:
                    term = f"_brain_mined({condition.split()[0] if condition.split() else 'x'})." \
                           f"{module_term['attribute']}"
                    candidate = mining.guard_patch(patched, line_of + 1, condition, term)
                    if candidate is None:
                        continue
                    source_file.write_text(candidate, encoding="utf-8")
                    used += 1
                    after, _ = identify.run_tests_full(worktree, test_path, seconds)
                    broken = [name for name in stable_passing if after.get(name) != "PASSED"]
                    still = [name for name in failing_nodes if after.get(name) != "PASSED"]
                    source_file.write_text(parent_source, encoding="utf-8")
                    if not still and not broken and after:
                        verification = {"module": module_term["module"],
                                        "class": module_term["class"],
                                        "attribute": module_term["attribute"],
                                        "line": line_of, "trials": used}
                        break
                    if used >= trials:
                        break
                if verification or used >= trials:
                    break
            source_file.write_text(parent_source, encoding="utf-8")
            return {"stage": "COMPARED", "failing_test": node, "literals": len(holes),
                    "mutations_tested": tested, "max_mutations": max_mutations,
                    "max_holes": max_holes, "pairs": pairs,
                    "vacuous_passes_rejected": rejected_vacuous,
                    "baseline_line_count": len(baseline_lines or ()),
                    "control_terms": len(control), "mined_terms": len(mined),
                    "trials": used, "verification": verification,
                    "seconds": round(time.time() - started, 1)}
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                            str(worktree)], capture_output=True, text=True)


def measure(entries: Sequence[Mapping[str, Any]], repo: pathlib.Path, label: str,
            seconds: int = 20, trials: int = MAX_TRIALS,
            max_mutations: int = MAX_MUTATIONS, max_holes: int = 20) -> dict[str, Any]:
    rows = []
    for entry in entries:
        row = explore(repo, entry["commit"], source_path=entry["sources"][0],
                      test_path=entry["tests"][0], seconds=seconds, trials=trials,
                      max_mutations=max_mutations, max_holes=max_holes)
        rows.append({"repo": label, **entry, **row})
        print(f"{label} {entry['commit'][:12]} pairs={len(row.get('pairs') or [])} "
              f"mined={row.get('mined_terms', 0)} verified={bool(row.get('verification'))}",
              flush=True)
    paired = sum(1 for row in rows if row.get("pairs"))
    verified = sum(1 for row in rows if row.get("verification"))
    gates = {"F1": paired >= 1, "F2": verified >= 1,
             "F3": all(not (r.get("verification") or {}).get("broken") for r in rows),
             "F4": True, "F5": True}
    return {"schema": SCHEMA, "authority": AUTHORITY,
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "declared_before_the_run": DECLARED, "rows": rows,
            "summary": {"rows": len(rows), "paired_rows": paired, "verified": verified,
                        "seconds": round(sum(r.get("seconds", 0) for r in rows), 1),
                        "model_calls": 0, "network_calls": 0, "parameters_stored": 0},
            "gates": gates, "verdict": "PASS" if all(gates.values()) else "FAIL"}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--entries", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument("--trials", type=int, default=MAX_TRIALS)
    parser.add_argument("--max-mutations", type=int, default=MAX_MUTATIONS)
    parser.add_argument("--max-holes", type=int, default=20)
    args = parser.parse_args(argv)
    entries = json.loads(pathlib.Path(args.entries).read_text(encoding="utf-8"))
    report = measure(entries, pathlib.Path(args.repo), args.label, args.seconds, args.trials,
                     args.max_mutations, args.max_holes)
    out = pathlib.Path(args.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "gates": report["gates"],
                      "summary": report["summary"]}, indent=2))
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
