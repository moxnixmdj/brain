# PROJECT_BRAIN
"""Per-test-file dynamic dependency map: which source files actually EXECUTE
when a test file runs.

Regression test selection on recorded dependencies is Ekstazi (Gligoric,
Eloussi, Marinov, ISSTA 2015) and pytest-testmon; this is the Brain-owned,
dependency-free form of the same idea.  Each test file runs alone in a
subprocess under a ``sys.settrace`` *call*-event tracer (module bodies,
functions, methods -- including ones reached through importlib,
``getattr``, ``sys.modules`` and other paths no static import graph sees).
Every executed ``.py`` under the repository is recorded with its SHA-256.

A map entry is trusted by the selector only while the test file's own hash
matches; missing or stale entries select the test (fail closed).  What the
map cannot see: data files, subprocesses, C extensions, ``exec`` of text that
never becomes a code object with a real filename.  The selector says so in
``selection_guarantee``.

Cost: one interpreter + one pytest session per test file, once; the map is
then reused across every change until the test file itself changes.  That
is the speed law: trace once, slice many.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys

SCHEMA = "PROJECT_BRAIN_TEST_DEPENDENCY_MAP_V1"

_TRACER = r'''
import json, pathlib, sys, threading
repo = pathlib.Path(sys.argv[1]).resolve(); target = sys.argv[2]
seen = set()
def tr(frame, event, arg):
    if event == "call":
        f = frame.f_code.co_filename
        if f.endswith(".py") and not f.startswith("<"):
            seen.add(f)
    return None
status = "TRACED"
sys.settrace(tr); threading.settrace(tr)
try:
    import pytest
    rc = pytest.main([target, "-q", "-p", "no:cacheprovider", "-x"])
    if rc not in (0, 1):
        status = "PYTEST_EXIT:" + str(int(rc))
except BaseException as exc:
    status = "TRACE_RAISED:" + type(exc).__name__
finally:
    sys.settrace(None); threading.settrace(None)
out = sorted({str(pathlib.Path(f).resolve().relative_to(repo)).replace("\\", "/")
              for f in seen if repo in pathlib.Path(f).resolve().parents})
print("__BRAIN_DEPS__" + json.dumps({"status": status, "files": out}))
'''


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trace(repo: str | os.PathLike[str], test_files: list[str], *, source_root: str = "",
          python_executable: str | None = None, timeout_s: int = 120) -> dict:
    """Return the dependency map for ``test_files`` (repo-relative posix paths)."""
    root = pathlib.Path(repo).resolve()
    src = (root / source_root).resolve() if source_root else root
    if src != root and root not in src.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    py = python_executable or sys.executable
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    tests: dict[str, dict] = {}
    for rel in sorted(set(test_files)):
        path = (root / rel).resolve()
        if root not in path.parents:
            raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
        row: dict = {"test_sha256": _sha(path) if path.is_file() else None, "status": "", "files": {}}
        if not path.is_file():
            row["status"] = "TEST_FILE_MISSING"
            tests[rel] = row
            continue
        try:
            proc = subprocess.run([py, "-c", _TRACER, str(root), str(path)], cwd=src,
                                  capture_output=True, text=True, timeout=timeout_s, env=env)
        except subprocess.TimeoutExpired:
            row["status"] = "TIMEOUT"
            tests[rel] = row
            continue
        lines = [x for x in proc.stdout.splitlines() if x.startswith("__BRAIN_DEPS__")]
        if not lines:
            row["status"] = "TRACE_OUTPUT_MISSING:rc=" + str(proc.returncode)
            tests[rel] = row
            continue
        payload = json.loads(lines[-1][len("__BRAIN_DEPS__"):])
        row["status"] = payload["status"]
        files = {}
        for f in payload["files"]:
            fp = root / f
            if fp.is_file():
                files[f] = _sha(fp)
        row["files"] = files
        tests[rel] = row
    return {"schema": SCHEMA, "repository_relative": True, "source_root": source_root,
            "tracer": "sys.settrace(call)+threading.settrace per test file subprocess",
            "tests": tests}


def write_map(repo: str | os.PathLike[str], output_path: str, mapping: dict) -> str:
    root = pathlib.Path(repo).resolve()
    out = (root / output_path).resolve()
    if out == root or root not in out.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    out.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(mapping, indent=2, sort_keys=True) + "\n").encode("utf-8")
    out.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def load_map(repo: str | os.PathLike[str], path: str) -> dict:
    root = pathlib.Path(repo).resolve()
    p = (root / path).resolve()
    if root not in p.parents or not p.is_file():
        raise RuntimeError("DEPENDENCY_MAP_MISSING")
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise RuntimeError("DEPENDENCY_MAP_SCHEMA_MISMATCH")
    return data


def decide(repo: str | os.PathLike[str], mapping: dict, test_rel: str, changed: set[str]) -> tuple[bool, str]:
    """(select?, reason) for one test under the recorded map.  Unknown -> select."""
    root = pathlib.Path(repo).resolve()
    row = (mapping.get("tests") or {}).get(test_rel)
    if not row:
        return True, "NO_DYNAMIC_TRACE_FAIL_CLOSED"
    if row.get("status") != "TRACED":
        return True, "DYNAMIC_TRACE_INCOMPLETE_FAIL_CLOSED:" + str(row.get("status"))
    path = root / test_rel
    if not path.is_file() or _sha(path) != row.get("test_sha256"):
        return True, "DYNAMIC_TRACE_STALE_FAIL_CLOSED"
    hit = sorted(set(row.get("files") or {}) & changed)
    if hit:
        return True, "DYNAMIC_DEPENDENCY_TRACED:" + ",".join(hit)
    return False, "NOT_EXECUTED_IN_TRACE"
