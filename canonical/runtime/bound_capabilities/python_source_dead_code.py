#!/usr/bin/env python3
"""python.source.dead_code.v1 — which defined function nothing in the tree executes.

The question is a query over the call graph the machine ALREADY builds:
``canonical/runtime/bound_capabilities/python_source_symbol_index.py`` emits a
``callers_of`` map, so "is this function ever executed" is a set membership test
against an artifact that exists.  Measured on the census fixture: 1.7 ms, exact.

Scope, and why it is the parent directory rather than the repository root:

    "Which function in <b>/app is never executed by the tests in <b>/tests?"

The subject is ``app``; the witness is ``tests``; they are siblings.  Indexing
only ``app`` would report ``cart_total`` as dead because its one caller lives in
``tests`` -- a false positive that reads like a correct answer.  Indexing the
whole repository is correct but pays 14.8 s over 2,254 files for a fixture of
five.  The parent of the subject is the smallest tree that contains both the
subject and its siblings, which is exactly the set a caller can be in.

A symbol counts as DEAD when no call edge in that tree names it.  It must be a
module-level function: a method is reached through its class, a nested function
through its enclosing scope, and neither appears in ``callers_of`` the same way.

result_fields: adapter, source_root, answer, dead_symbols, symbol_count,
considered_count, output_path, output_sha256, output_verified.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import tempfile

SCHEMA = "PROJECT_BRAIN_PYTHON_DEAD_CODE_V1"


def _safe_root(repo: pathlib.Path, raw) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if p != repo and repo not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not p.is_dir():
        raise RuntimeError("SOURCE_ROOT_MISSING")
    return p


def _rel(repo: pathlib.Path, path: pathlib.Path) -> str:
    return str(path.relative_to(repo)).replace("\\", "/")


def run(args, root):
    repo = pathlib.Path(root).resolve()
    source_root = _safe_root(repo, args.get("source_root"))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")

    # The subject and its siblings: the smallest tree a caller can be in.
    scope = source_root if source_root == repo else source_root.parent

    from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer

    with tempfile.TemporaryDirectory(dir=str(output.parent)) as scratch:
        probe = pathlib.Path(scratch) / "index.json"
        indexer.run({"source_root": str(scope), "output_path": str(probe)}, str(repo))
        index = json.loads(probe.read_text(encoding="utf-8"))

    # Module spellings the index uses, restricted to the subject subtree.
    modules = set()
    for path in sorted(source_root.rglob("*.py")):
        modules.add(_rel(repo, path.with_suffix("")).replace("/", "."))

    called = set(index.get("callers_of") or {})
    dead = []
    considered = 0
    for qualname in sorted(index.get("symbols") or {}):
        module, _, name = qualname.rpartition(":")
        if module not in modules:
            continue
        # A dotted tail is a class, a method, or a nested function: reached
        # through its owner, not through a call edge of its own name.
        if "." in name or not name or name.startswith("_"):
            continue
        considered += 1
        if name not in called and module.rsplit(".", 1)[0].replace(".", "/") != "" :
            dead.append(name)

    dead = sorted(set(dead))
    report = {
        "schema": SCHEMA,
        "source_root": _rel(repo, source_root),
        "scope_root": _rel(repo, scope),
        "answer": dead[0] if dead else "",
        "dead_symbols": dead,
        "considered_count": considered,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.write_bytes(raw)
    return {
        "adapter": "python_source_dead_code",
        "source_root": report["source_root"],
        "answer": report["answer"],
        "dead_symbols": dead,
        "symbol_count": len(index.get("symbols") or {}),
        "considered_count": considered,
        "output_path": _rel(repo, output),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
    }
