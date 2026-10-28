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

Two ways to build the map:

* ``trace()`` -- one interpreter + one pytest session per test file.  Sound
  attribution (nothing imported by an earlier file can hide), slower.
* ``SESSION_PLUGIN_SOURCE`` / ``map_from_session()`` -- a pytest plugin that
  rides along an existing full run (the issue-to-PR orchestrator already runs
  the whole suite once) and attributes call events plus newly imported
  modules to the test file that is current at collection and run time.  Same
  leak pytest-testmon accepts: a module imported by an earlier file and only
  read, never called, by a later one is not attributed.

Either way the map is reused across every change until the test file itself
changes.  That is the speed law: trace once, slice many.

Maps may be keyed relative to a traced tree (``tree_root``, repo-relative);
the selector translates.  ``tree_root == ""`` means repo-relative keys.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
from typing import Any, Mapping

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


SESSION_PLUGIN_SOURCE = r'''
import json, os, sys, threading
OUT = os.environ["BRAIN_DEP_TRACE_OUT"]
ROOT = os.environ.get("BRAIN_DEP_TRACE_ROOT", "")
_cur = None
_files = {}
_snap = {}
_newmods = {}
_status = {}
def _tr(frame, event, arg):
    if event == "call":
        c = _cur
        if c is not None:
            f = frame.f_code.co_filename
            if f.endswith(".py") and not f.startswith("<") and f.startswith(ROOT):
                _files[c].add(f)
    return None
def _set(path):
    global _cur
    if _cur is not None:
        _newmods[_cur].update(set(sys.modules) - _snap[_cur])
    _cur = path
    _files.setdefault(path, set())
    _newmods.setdefault(path, set())
    _snap[path] = set(sys.modules)
def _p(obj):
    p = getattr(obj, "path", None)
    if p is None:
        p = getattr(obj, "fspath", None)
    return str(p) if p is not None else None
def pytest_sessionstart(session):
    sys.settrace(_tr); threading.settrace(_tr)
def pytest_collectstart(collector):
    p = _p(collector)
    if p and p.endswith(".py"):
        _set(p)
def pytest_collectreport(report):
    if report.failed:
        p = report.nodeid.split("::", 1)[0]
        _status[p] = "COLLECTION_ERROR"
def pytest_runtest_protocol(item, nextitem):
    p = _p(item)
    if p:
        _set(p)
    return None
def pytest_sessionfinish(session, exitstatus):
    sys.settrace(None); threading.settrace(None)
    if _cur is not None:
        _newmods[_cur].update(set(sys.modules) - _snap[_cur])
    tests = {}
    for p, files in _files.items():
        for m in _newmods.get(p, ()):
            mod = sys.modules.get(m)
            f = getattr(mod, "__file__", None) if mod is not None else None
            if isinstance(f, str) and f.endswith(".py") and f.startswith(ROOT):
                files.add(f)
        tests[p] = {"files": sorted(files)}
    for p, st in _status.items():
        full = os.path.join(str(session.config.rootpath), p)
        tests.setdefault(full, {"files": []})["status"] = st
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"exitstatus": int(exitstatus), "tests": tests}, fh)
'''


def _sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def map_from_session(repo: str | os.PathLike[str], tree_root: str, payload: Mapping[str, Any],
                     test_files: list[str] | None = None) -> dict:
    """Turn a session plugin payload into a map keyed relative to ``tree_root``.

    ``test_files`` (tree-relative) names every file the run was supposed to
    cover; any of them absent from the payload is recorded as UNTRACED so the
    selector fails closed on it.
    """
    root = pathlib.Path(repo).resolve()
    tree = (root / tree_root).resolve() if tree_root else root
    if tree != root and root not in tree.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    exit_ok = int(payload.get("exitstatus", 99)) in (0, 1)
    tests: dict[str, dict] = {}
    for abs_test, row in (payload.get("tests") or {}).items():
        tp = pathlib.Path(abs_test).resolve()
        if tree not in tp.parents or not tp.is_file():
            continue
        name = tp.name
        if not (name.startswith("test_") or name.endswith("_test.py")):
            continue
        rel = tp.relative_to(tree).as_posix()
        files = {}
        for f in row.get("files") or []:
            fp = pathlib.Path(f).resolve()
            if tree in fp.parents and fp.is_file():
                files[fp.relative_to(tree).as_posix()] = _sha(fp)
        status = row.get("status") or ("TRACED" if exit_ok else "PYTEST_EXIT:" + str(payload.get("exitstatus")))
        tests[rel] = {"test_sha256": _sha(tp), "status": status, "files": files}
    for rel in test_files or []:
        tests.setdefault(rel, {"test_sha256": None, "status": "UNTRACED", "files": {}})
    return {"schema": SCHEMA, "repository_relative": not tree_root, "tree_root": tree_root,
            "source_root": tree_root,
            "tracer": "pytest session plugin: sys.settrace(call) + sys.modules delta per current test file",
            "tests": tests}


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


def _tree_rel(tree_root: str, rel: str) -> str | None:
    if not tree_root:
        return rel
    prefix = tree_root.rstrip("/") + "/"
    return rel[len(prefix):] if rel.startswith(prefix) else None


def decide(repo: str | os.PathLike[str], mapping: dict, test_rel: str, changed: set[str]) -> tuple[bool, str]:
    """(select?, reason) for one test under the recorded map.  Unknown -> select.

    ``test_rel`` and ``changed`` are repo-relative; a map with ``tree_root`` is
    consulted relative to that tree."""
    root = pathlib.Path(repo).resolve()
    tree_root = str(mapping.get("tree_root") or "")
    key = _tree_rel(tree_root, test_rel)
    row = (mapping.get("tests") or {}).get(key) if key is not None else None
    if not row:
        return True, "NO_DYNAMIC_TRACE_FAIL_CLOSED"
    if row.get("status") != "TRACED":
        return True, "DYNAMIC_TRACE_INCOMPLETE_FAIL_CLOSED:" + str(row.get("status"))
    path = root / test_rel
    if not path.is_file() or _sha(path) != row.get("test_sha256"):
        return True, "DYNAMIC_TRACE_STALE_FAIL_CLOSED"
    changed_in_tree = {c for c in (_tree_rel(tree_root, x) for x in changed) if c is not None}
    hit = sorted(set(row.get("files") or {}) & changed_in_tree)
    if hit:
        return True, "DYNAMIC_DEPENDENCY_TRACED:" + ",".join(hit)
    return False, "NOT_EXECUTED_IN_TRACE"
