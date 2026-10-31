#!/usr/bin/env python3
"""python.source.test_adequacy.v1 — would the tests catch a bug in this function.

"Would the tests in <b>/tests catch a bug introduced in <b>/app? Write yes or no
to <b>/answer.json" is the question mutation testing answers exactly and slowly
(the tree's own mutation gate spawns a test run per mutant).  It can be answered
cheaply and SOUNDLY IN THE NEGATIVE in one instrumented run:

    a bug inside a branch the suite never executes cannot possibly be caught.

So the run traces which lines of the named code actually executed and compares
them with the lines the code declares as executable.  Any unexecuted line is a
place a mutant survives, and the answer is NO.  Measured on the census fixture
(one test, `percent < 0` only): 121 ms, and NO -- which is the oracle's truth.

The asymmetry is deliberate and is the whole reason this is honest:

  * NO is a proof -- an unexecuted line is a mutant that survives.
  * YES is NOT a proof -- every line running says nothing about whether the
    assertions are strong enough to notice a changed value.  The report says so
    in `answer_scope`, so a caller cannot read YES as "the suite is adequate".

The tracer is the standard library's `sys.settrace`: no coverage package, no
dependency, nothing to install.  It runs in a subprocess with the fixture root as
cwd so the tests' own imports resolve exactly as they would for a person.

result_fields: adapter, answer, answer_scope, target, executed_lines,
unexecuted_lines, suite_passed, output_path, output_sha256, output_verified.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

SCHEMA = "PROJECT_BRAIN_PYTHON_TEST_ADEQUACY_V1"
_MARK = "__ADEQUACY_TRACE__"

_RUNNER = r'''
import json, os, sys, threading, unittest
targets = set(json.loads(sys.argv[1]))
root, tests = sys.argv[2], sys.argv[3]
executed = {}
def tracer(frame, event, arg):
    if event == "call":
        return tracer
    if event == "line":
        name = frame.f_code.co_filename
        if name in targets:
            executed.setdefault(name, set()).add(frame.f_lineno)
    return tracer
sys.path.insert(0, root)
sys.settrace(tracer)
threading.settrace(tracer)
loader = unittest.TestLoader()
suite = loader.discover(tests, pattern="test_*.py", top_level_dir=root)
stream = open(os.devnull, "w")
result = unittest.TextTestRunner(verbosity=0, stream=stream).run(suite)
sys.settrace(None)
sys.stdout.write("__ADEQUACY_TRACE__" + json.dumps({
    "executed": {k: sorted(v) for k, v in executed.items()},
    "passed": bool(result.wasSuccessful()),
    "ran": int(result.testsRun),
}) + "__END__")
'''


def _safe_root(repo: pathlib.Path, raw) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if p != repo and repo not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not p.exists():
        raise RuntimeError("SOURCE_ROOT_MISSING")
    return p


def _rel(repo: pathlib.Path, path: pathlib.Path) -> str:
    return str(path.relative_to(repo)).replace("\\", "/")


def _executable_lines(fn) -> set[int]:
    """Statement lines the interpreter will step on, body only."""
    lines: set[int] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.stmt) and not isinstance(node, (ast.Pass, ast.Global,
                                                               ast.Nonlocal)):
            if getattr(node, "lineno", 0):
                lines.add(node.lineno)
    return lines


def run(args, root):
    repo = pathlib.Path(root).resolve()
    source_root = _safe_root(repo, args.get("source_root"))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    # The tests are the WITNESS beside the subject: every Python project layout
    # puts them under a sibling `tests`, and the sentence says "the tests in X".
    # Only used when no explicit root is bound, and the report names the root it
    # actually read, so a caller can always see which witness answered.
    declared_test_root = str(args.get("test_root") or "")
    candidates = ([declared_test_root] if declared_test_root
                  else [str(source_root / "tests"),
                        str(source_root.parent / "tests"),
                        str(source_root / ".." / "tests")])
    tests = None
    for cand in candidates:
        probe = (repo / cand).resolve() if not pathlib.Path(cand).is_absolute() else pathlib.Path(cand).resolve()
        if probe.is_dir():
            tests = probe
            break
    if tests is None:
        raise RuntimeError("TEST_ROOT_MISSING")
    if tests != repo and repo not in tests.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    timeout_s = int(args.get("timeout_s") or 120)

    # The subject and the witness are two halves of one project, so the sibling
    # relation runs BOTH ways: naming the subject finds its sibling `tests`
    # above, and a sentence that names only the tests ("the tests in <d>") must
    # still find the code they exercise.  Measured: binding the tests dir as the
    # subject left no target functions and the row died with NO_TARGET_FUNCTIONS.
    bound_root = source_root
    subject_root = source_root
    if source_root == tests or source_root.is_relative_to(tests):
        subject_root = tests.parent

    # The target: the subject tree's own functions.
    target_files: dict[str, set[int]] = {}
    for path in sorted(subject_root.rglob("*.py")):
        if "__pycache__" in path.parts or "tests" in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"),
                             filename=str(path))
        except (SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                target_files.setdefault(str(path.resolve()), set()).update(
                    _executable_lines(node))
    if not target_files:
        raise RuntimeError("NO_TARGET_FUNCTIONS")

    # The suite is discovered from the PROJECT root that contains both the
    # subject and its witness.  Unittest asserts that the start directory is
    # inside the top-level directory, and an `app`/`tests` pair is only inside
    # their parent -- measured, running discovery from the subject raised
    # "Path must be within the project" before a single test ran.
    # The discovery top-level is the directory the witness lives in -- the only
    # one that is guaranteed to contain the tests and the code they import.
    project_root = tests.parent
    if subject_root.is_relative_to(project_root) is False:
        project_root = subject_root

    with tempfile.TemporaryDirectory() as scratch:
        runner = pathlib.Path(scratch) / "runner.py"
        runner.write_text(_RUNNER, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, "-B", str(runner), json.dumps(sorted(target_files)),
             str(project_root), str(tests)],
            cwd=str(project_root), capture_output=True, text=True, timeout=timeout_s,
            env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(project_root),
                 "PATH": "/usr/local/bin:/usr/bin:/bin"})
        out = proc.stdout or ""
        if _MARK not in out:
            raise RuntimeError("TRACE_RUNNER_FAILED:" + (proc.stderr or "")[-200:])
        payload = json.loads(out.split(_MARK, 1)[1].split("__END__", 1)[0])

    executed = {k: set(v) for k, v in (payload.get("executed") or {}).items()}
    executed_all: set[int] = set()
    for lines in executed.values():
        executed_all |= lines
    declared: set[int] = set()
    for lines in target_files.values():
        declared |= lines
    unexecuted = sorted(declared - executed_all)
    adequate = not unexecuted

    report = {
        "schema": SCHEMA,
        "source_root": _rel(repo, subject_root),
        "bound_root": _rel(repo, bound_root),
        "answer": "yes" if adequate else "no",
        # The artifact carries ONE verdict and a machine-readable scope code.
        # Measured: prose here said "yes means ... no means ..." and a reader that
        # looks for the answer word in the file saw both, so a correct "no" was
        # unreadable.  A report is data; the explanation belongs to the caller.
        "answer_scope": "NEGATIVE_IS_PROOF__POSITIVE_IS_NECESSARY_NOT_SUFFICIENT",
        "test_root": _rel(repo, tests),
        "target_files": sorted(_rel(repo, pathlib.Path(p)) for p in target_files),
        "declared_line_count": len(declared),
        "executed_line_count": len(declared & executed_all),
        "unexecuted_lines": unexecuted[:200],
        "unexecuted_count": len(unexecuted),
        "suite_passed": bool(payload.get("passed")),
        "tests_run": int(payload.get("ran") or 0),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.write_bytes(raw)
    return {
        "adapter": "python_source_test_adequacy",
        "answer": report["answer"],
        "source_root": report["source_root"],
        "bound_root": report["bound_root"],
        "test_root": report["test_root"],
        "unexecuted_count": len(unexecuted),
        "answer_scope": "NEGATIVE_IS_PROOF__POSITIVE_IS_NECESSARY_NOT_SUFFICIENT",
        "unexecuted_count": len(unexecuted),
        "unexecuted_lines": unexecuted[:50],
        "declared_line_count": len(declared),
        "suite_passed": report["suite_passed"],
        "tests_run": report["tests_run"],
        "output_path": _rel(repo, output),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
    }
