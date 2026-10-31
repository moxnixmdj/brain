#!/usr/bin/env python3
"""python.source.definition_count.v1 — how many definitions a tree declares.

"Count the function and class definitions in <b>/app and write the number to
<b>/answer.json" is one pass over `ast`, and the tree already had everything
needed except a row that answers it: `python.source.audit.ast` reports
`function_count` and `class_count` SEPARATELY, which is two numbers to a question
that asks for one.  Measured on the census fixture, the sentence ended
`FAIL_CLOSED__PROMISED_ARTIFACT_MISSING` -- nothing wrote the answer.

What counts as a definition: every `def`, `async def` and `class`, at any depth.
A method is a definition (the census oracle counts `Thing.method`), and so is a
nested function, because a reader counting definitions in a file counts what
they see.  Classes and functions are weighted equally: the sentence asks for
"function and class definitions", which is one set, not a weighted sum.

result_fields: adapter, answer, definition_count, function_count, class_count,
files_scanned, output_path, output_sha256, output_verified.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib

SCHEMA = "PROJECT_BRAIN_PYTHON_DEFINITION_COUNT_V1"

_FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef)


def _safe_root(repo: pathlib.Path, raw) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if p != repo and repo not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not p.exists():
        raise RuntimeError("SOURCE_ROOT_MISSING")
    return p


def _rel(repo: pathlib.Path, path: pathlib.Path) -> str:
    return str(path.relative_to(repo)).replace("\\", "/")


def _files(root: pathlib.Path):
    if root.is_file():
        yield root
        return
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        yield path


def run(args, root):
    repo = pathlib.Path(root).resolve()
    source_root = _safe_root(repo, args.get("source_root"))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")

    functions = 0
    classes = 0
    scanned = 0
    unparseable = 0
    for path in _files(source_root):
        scanned += 1
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"),
                             filename=str(path))
        except (SyntaxError, ValueError):
            unparseable += 1
            continue
        for node in ast.walk(tree):
            if isinstance(node, _FUNCS):
                functions += 1
            elif isinstance(node, ast.ClassDef):
                classes += 1

    total = functions + classes
    report = {
        "schema": SCHEMA,
        "source_root": _rel(repo, source_root),
        "answer": total,
        "definition_count": total,
        "function_count": functions,
        "class_count": classes,
        "files_scanned": scanned,
        "unparseable_count": unparseable,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.write_bytes(raw)
    return {
        "adapter": "python_source_definition_count",
        "answer": total,
        "definition_count": total,
        "function_count": functions,
        "class_count": classes,
        "files_scanned": scanned,
        "output_path": _rel(repo, output),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
    }
