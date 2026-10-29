"""Bounded execution evidence for explicitly named Python test files.

Pytest's existing JUnit parser supplies fixture-aware test outcomes. When
pytest is unavailable, an instrumented stdlib unittest run can attest actual
unittest cases; a narrow opcode-traced fallback supports assertion scripts.
An unavailable or skipped-only file never becomes a pass. These subprocesses
are not an OS sandbox and do not establish complete test coverage.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import pathlib
import subprocess
import time
from typing import Any


def _load_full_gate():
    path = pathlib.Path(__file__).with_name("python_repo_diff_apply_full_testgate.py")
    spec = importlib.util.spec_from_file_location("_brain_evidence_full_gate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("PYTEST_REPORT_PARSER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_FULL_GATE = _load_full_gate()

# A child interpreter performs the fallback to preserve its dependency and
# optimization environment. TestResult tracks skips and expected failures;
# console text such as a fake "Ran N tests" is not execution evidence.
_UNITTEST_WITNESS = r'''
import importlib.util, inspect, json, pathlib, sys, unittest
report = pathlib.Path(sys.argv[1])
targets = sys.argv[2:]
rows = []
for index, rel in enumerate(targets):
    path = pathlib.Path(rel).resolve()
    row = {"path": rel, "executed": 0, "passed": 0, "failed": 0, "skipped": 0, "error": ""}
    try:
        if str(path.parent) not in sys.path:
            sys.path.insert(0, str(path.parent))
        name = "__brain_unittest_evidence_%d__" % index
        spec = importlib.util.spec_from_file_location(name, str(path))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        # A stdlib runner cannot handle pytest-style functions or classes.
        omitted = any(name.startswith("test_") and callable(obj)
                      for name, obj in vars(mod).items())
        for name, obj in vars(mod).items():
            if inspect.isclass(obj) and name.startswith("Test") and not issubclass(obj, unittest.TestCase):
                omitted = omitted or any(key.startswith("test_") for key in vars(obj))
        if omitted:
            row["error"] = "PYTEST_STYLE_TESTS_REQUIRE_PYTEST"
        else:
            suite = unittest.TestLoader().loadTestsFromModule(mod)
            result = unittest.TestResult()
            suite.run(result)
            skipped = len(result.skipped) + len(result.expectedFailures)
            failed = len(result.failures) + len(result.errors) + len(result.unexpectedSuccesses)
            executed = max(0, result.testsRun - skipped)
            row.update(executed=executed, passed=max(0, executed-failed), failed=failed, skipped=skipped)
    except BaseException as exc:
        row["error"] = type(exc).__name__
    rows.append(row)
report.write_text(json.dumps({"schema":"BRAIN_UNITTEST_WITNESS_V1", "rows":rows}), encoding="utf-8")
'''

# Line coverage alone can falsely count `if False: assert ...` on the same
# line. Opcode positions instead witness evaluation within an assert's test
# expression. Constant-folded assertions and older interpreters without
# instruction positions are conservatively unverified.
_ASSERTION_WITNESS = r'''
import ast, dis, inspect, json, pathlib, runpy, sys, unittest
report = pathlib.Path(sys.argv[1])
targets = sys.argv[2:]
rows = []

def within(pos, span):
    if (pos is None or pos.lineno is None or pos.end_lineno is None or
        pos.col_offset is None or pos.end_col_offset is None):
        return False
    return (span[0], span[1]) <= (pos.lineno, pos.col_offset) and (pos.end_lineno, pos.end_col_offset) <= (span[2], span[3])

for rel in targets:
    target = pathlib.Path(rel).resolve()
    row = {"path": rel, "executed": 0, "passed": 0, "failed": 0, "skipped": 0, "assertion_sites": 0, "error": ""}
    try:
        tree = ast.parse(target.read_bytes(), filename=str(target))
        assertions = [n for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        spans = [(n.test.lineno, n.test.col_offset, n.test.end_lineno, n.test.end_col_offset)
                 for n in assertions]
        statement_spans = [(n.lineno, n.col_offset, n.end_lineno, n.end_col_offset) for n in assertions]
        seen, offsets, statement_offsets, assertion_errors = set(), {}, {}, []
        def trace(frame, event, arg):
            if frame.f_code.co_filename != str(target):
                return None
            if event == "call":
                frame.f_trace_opcodes = True
                if frame.f_code not in offsets:
                    instructions = list(dis.get_instructions(frame.f_code))
                    offsets[frame.f_code] = {
                        ins.offset: [i for i, span in enumerate(spans) if within(getattr(ins, "positions", None), span)]
                        for ins in instructions
                    }
                    statement_offsets[frame.f_code] = {
                        ins.offset for ins in instructions
                        if any(within(getattr(ins, "positions", None), span) for span in statement_spans)
                    }
                return trace
            if event == "opcode":
                seen.update(offsets[frame.f_code].get(frame.f_lasti, ()))
            elif event == "exception" and (arg[0] is AssertionError or frame.f_lasti in statement_offsets[frame.f_code]):
                # An exception raised while computing the asserted expression
                # is not a passing assertion, even if the script catches it.
                assertion_errors.append(True)
            return trace
        if str(target.parent) not in sys.path:
            sys.path.insert(0, str(target.parent))
        saved_argv = sys.argv
        sys.argv = [str(target)]
        sys.settrace(trace)
        try:
            namespace = runpy.run_path(str(target), run_name="__main__")
        finally:
            sys.settrace(None)
            sys.argv = saved_argv
        # Imports can expose collectable cases despite a test-free AST; don't
        # let a passing top-level assert hide an imported unittest class.
        collectable = any(name.startswith("test_") and callable(obj)
                          for name, obj in namespace.items())
        for name, obj in namespace.items():
            if inspect.isclass(obj):
                if issubclass(obj, unittest.TestCase):
                    collectable = True
                elif name.startswith("Test") and any(key.startswith("test_") for key in dir(obj)):
                    collectable = True
        row["assertion_sites"] = len(seen)
        if collectable:
            row.update(failed=1, error="COLLECTABLE_TESTS_PRESENT")
        elif assertion_errors:
            row.update(failed=1, error="ASSERTION_ERROR_OBSERVED")
        elif seen:
            row.update(executed=1, passed=1)
    except BaseException as exc:
        sys.settrace(None)
        row.update(failed=1, error=type(exc).__name__)
    rows.append(row)
report.write_text(json.dumps({"schema":"BRAIN_ASSERTION_WITNESS_V1", "rows":rows}), encoding="utf-8")
'''


def _run(argv: list[str], cwd: pathlib.Path, env: dict[str, str], deadline: float) -> dict[str, Any]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return {"returncode": None, "timed_out": True, "stdout": "", "stderr": ""}
    try:
        proc = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, timeout=remaining)
        return {"returncode": proc.returncode, "timed_out": False,
                "stdout": proc.stdout or "", "stderr": proc.stderr or ""}
    except subprocess.TimeoutExpired:
        return {"returncode": None, "timed_out": True, "stdout": "", "stderr": ""}
    except OSError as exc:
        return {"returncode": None, "timed_out": False, "stdout": "", "stderr": type(exc).__name__}


def _pytest_rows(path: pathlib.Path, workspace: pathlib.Path, targets: list[str]) -> dict[str, dict[str, Any]]:
    """Reuse the full gate's validated, file-attributed JUnit evidence."""
    return {rel: {**row, "kind": "PYTEST_JUNIT"}
            for rel, row in _FULL_GATE._pytest_file_evidence(path, workspace, targets).items()}


def _script_candidate(path: pathlib.Path) -> bool:
    """Recognize simple assertion scripts, not uncollected pytest test suites."""
    try:
        tree = ast.parse(path.read_bytes(), filename=str(path))
    except (OSError, SyntaxError, ValueError):
        return False
    nodes = list(ast.walk(tree))
    if not any(isinstance(node, ast.Assert) for node in nodes):
        return False
    return not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
        or isinstance(node, ast.ClassDef) and node.name.startswith("Test")
        for node in nodes
    )


def _simple_assertion_script(workspace: pathlib.Path, rel: str) -> bool:
    """Fast-path only obvious scripts with no possible static pytest cases."""
    path = workspace / rel
    if not _script_candidate(path):
        return False
    if _has_pytest_context(workspace, rel):
        return False
    try:
        nodes = list(ast.walk(ast.parse(path.read_bytes(), filename=str(path))))
    except (OSError, SyntaxError, ValueError):
        return False
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            return False
        if isinstance(node, ast.ImportFrom) and (node.module in {"pytest", "unittest"}
                or any(alias.name == "*" or (alias.asname or alias.name).startswith("test_") for alias in node.names)):
            return False
        if isinstance(node, ast.Import) and any(alias.name.split(".")[0] in {"pytest", "unittest"}
                                                for alias in node.names):
            return False
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in {"exec", "eval", "__import__", "globals", "locals"}):
            return False
    return True


def _has_pytest_context(workspace: pathlib.Path, rel: str) -> bool:
    # Without pytest, custom discovery or fixtures cannot be safely inferred.
    if os.environ.get("PYTEST_PLUGINS"):
        return True
    names = {"conftest.py", "pytest.ini", "pyproject.toml", "tox.ini", "setup.cfg"}
    parent = (workspace / rel).parent
    while parent == workspace or workspace in parent.parents:
        if any((parent / name).exists() for name in names):
            return True
        if parent == workspace:
            break
        parent = parent.parent
    return False


def _witness_rows(python: str, code: str, schema: str, kind: str, paths: list[str],
                  workspace: pathlib.Path, temp_dir: pathlib.Path, env: dict[str, str],
                  deadline: float) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if not paths:
        return {}, {"returncode": 0, "timed_out": False}
    report = temp_dir / ("unittest.json" if kind == "STDLIB_UNITTEST" else "assertions.json")
    proc = _run([python, "-c", code, str(report)] + paths, workspace, env, deadline)
    rows: dict[str, dict[str, Any]] = {}
    try:
        data = json.loads(report.read_text(encoding="utf-8"))
        if proc["returncode"] != 0 or proc["timed_out"] or data.get("schema") != schema:
            raise ValueError("INVALID_WITNESS")
        for raw in data["rows"]:
            if not isinstance(raw, dict) or raw.get("path") not in paths or raw["path"] in rows:
                raise ValueError("INVALID_WITNESS_ROW")
            for key in ("executed", "passed", "failed", "skipped"):
                if type(raw.get(key)) is not int or raw[key] < 0:
                    raise ValueError("INVALID_WITNESS_COUNT")
            if raw["passed"] + raw["failed"] > raw["executed"] and not raw.get("error"):
                raise ValueError("INCONSISTENT_WITNESS_COUNT")
            rows[raw["path"]] = {**raw, "kind": kind}
        if set(rows) != set(paths):
            raise ValueError("MISSING_WITNESS_ROW")
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        rows = {}
    return rows, {"returncode": proc["returncode"], "timed_out": proc["timed_out"]}


def _outcome(rows: dict[str, dict[str, Any]], test_paths: list[str], infrastructure_ok: bool,
             proc: dict[str, Any], report: dict[str, Any], pytest_available: bool | None,
             fallback: dict[str, Any] | None, assertion_run: dict[str, Any] | None,
             fast_path: bool = False) -> dict[str, Any]:
    path_rows = [rows.get(rel, {"path": rel, "kind": "UNAVAILABLE", "executed": 0,
                                "passed": 0, "failed": 0, "skipped": 0}) for rel in test_paths]
    count = sum(row["executed"] for row in path_rows)
    kinds = sorted({row["kind"] for row in path_rows if row["executed"] > 0})
    ok = (infrastructure_ok and bool(path_rows) and all(
        row["passed"] > 0 and row["failed"] == 0 and not row.get("error") for row in path_rows
    ))
    return {
        "oracle_status": "PASS" if ok else "FAIL_OR_UNAVAILABLE",
        "oracle_kind": kinds[0] if len(kinds) == 1 else "MIXED" if kinds else "UNAVAILABLE",
        "oracle_fast_path": fast_path,
        "test_count": count,
        "test_count_basis": "PYTEST_OR_UNITTEST_CASES_PLUS_ONE_PER_ASSERTION_SCRIPT",
        "path_evidence": path_rows,
        "pytest_returncode": proc["returncode"],
        "pytest_timed_out": proc["timed_out"],
        "pytest_available": pytest_available,
        "pytest_report_available": report["available"],
        "pytest_collected": report["collected"],
        "pytest_skipped": report["skipped"],
        "unittest_witness": fallback,
        "assertion_witness": assertion_run,
    }


def collect(workspace: pathlib.Path, source_root: pathlib.Path, test_paths: list[str], python: str,
            temp_dir: pathlib.Path, deadline: float) -> dict[str, Any]:
    """Independently attest declared files within the caller's wall-clock budget."""
    env = _FULL_GATE._pytest_env(source_root, workspace)
    env["PYTHONHASHSEED"] = "0"
    if test_paths and all(_simple_assertion_script(workspace, rel) for rel in test_paths):
        # Avoid a pytest process that would only return "no tests collected";
        # a small stdlib trace directly attests these restricted scripts.
        rows, assertion_run = _witness_rows(python, _ASSERTION_WITNESS, "BRAIN_ASSERTION_WITNESS_V1",
                                           "ASSERTION_SCRIPT_TRACE", test_paths, workspace, temp_dir, env, deadline)
        ok = assertion_run["returncode"] == 0 and not assertion_run["timed_out"]
        return _outcome(rows, test_paths, ok, {"returncode": None, "timed_out": False},
                        {"available": False, "collected": 0, "skipped": 0}, None, None, assertion_run, True)
    report_path = temp_dir / "pytest.xml"
    argv = [python, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir=.",
            "-o", "addopts=", "-o", "junit_family=legacy", "--junitxml=" + str(report_path)] + test_paths
    proc = _run(argv, workspace, env, deadline)
    report = _FULL_GATE._pytest_report(report_path)
    pytest_missing = (proc["returncode"] not in (None, 0, 5)
                      and proc["stderr"].strip().endswith(": No module named pytest")
                      and not report_path.exists())
    rows: dict[str, dict[str, Any]] = {}
    fallback = None
    infrastructure_ok = True
    if pytest_missing:
        eligible = [rel for rel in test_paths if not _has_pytest_context(workspace, rel)]
        rows, fallback = _witness_rows(python, _UNITTEST_WITNESS, "BRAIN_UNITTEST_WITNESS_V1",
                                      "STDLIB_UNITTEST", eligible, workspace, temp_dir, env, deadline)
        infrastructure_ok = bool(fallback and fallback["returncode"] == 0 and not fallback["timed_out"])
    elif proc["returncode"] in (0, 5) and not proc["timed_out"]:
        if report["available"]:
            rows = _pytest_rows(report_path, workspace, test_paths)
        elif proc["returncode"] != 5:
            infrastructure_ok = False
    else:
        # Record real failed cases when available, but never override a pytest
        # failure or collection error with an assertion-script fallback.
        if report["available"]:
            rows = _pytest_rows(report_path, workspace, test_paths)
        infrastructure_ok = False

    missing = [rel for rel in test_paths if rel not in rows or
               (rows[rel]["executed"] == 0 and rows[rel]["skipped"] == 0 and not rows[rel].get("error"))]
    scripts = [rel for rel in missing if _script_candidate(workspace / rel)
               and not (pytest_missing and _has_pytest_context(workspace, rel))]
    assertion_run = None
    if infrastructure_ok and scripts:
        script_rows, assertion_run = _witness_rows(python, _ASSERTION_WITNESS, "BRAIN_ASSERTION_WITNESS_V1",
                                                   "ASSERTION_SCRIPT_TRACE", scripts, workspace, temp_dir,
                                                   env, deadline)
        rows.update(script_rows)
        infrastructure_ok = bool(assertion_run["returncode"] == 0 and not assertion_run["timed_out"])

    return _outcome(rows, test_paths, infrastructure_ok, proc, report, not pytest_missing, fallback, assertion_run)
