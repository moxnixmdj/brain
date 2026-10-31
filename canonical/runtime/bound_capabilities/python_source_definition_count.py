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
_DEF_COUNT_CACHE: dict[tuple[str, int, int], tuple[int, int, int]] = {}


def _count_stmts(stmts: list[ast.stmt]) -> tuple[int, int]:
    fn_c = 0
    cls_c = 0
    stack: list[list[ast.stmt]] = [stmts]
    while stack:
        block = stack.pop()
        for node in block:
            if isinstance(node, _FUNCS):
                fn_c += 1
                stack.append(node.body)
            elif isinstance(node, ast.ClassDef):
                cls_c += 1
                stack.append(node.body)
            else:
                body = getattr(node, "body", None)
                if isinstance(body, list):
                    stack.append(body)
                orelse = getattr(node, "orelse", None)
                if isinstance(orelse, list) and orelse:
                    stack.append(orelse)
                finalbody = getattr(node, "finalbody", None)
                if isinstance(finalbody, list) and finalbody:
                    stack.append(finalbody)
                handlers = getattr(node, "handlers", None)
                if isinstance(handlers, list):
                    for h in handlers:
                        if isinstance(getattr(h, "body", None), list):
                            stack.append(h.body)
                cases = getattr(node, "cases", None)
                if isinstance(cases, list):
                    for c in cases:
                        if isinstance(getattr(c, "body", None), list):
                            stack.append(c.body)
    return fn_c, cls_c


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
    import pickle, tempfile
    disk_cache_path = pathlib.Path(tempfile.gettempdir()) / (
        "brain_def_count_v1_" + hashlib.sha256(str(source_root).encode("utf-8")).hexdigest()[:16] + ".pkl"
    )
    if not _DEF_COUNT_CACHE and disk_cache_path.is_file():
        try:
            loaded = pickle.loads(disk_cache_path.read_bytes())
            if isinstance(loaded, dict):
                _DEF_COUNT_CACHE.update(loaded)
        except Exception:
            pass
    cache_dirty = False
    for path in _files(source_root):
        scanned += 1
        try:
            st = path.stat()
            ckey = (str(path), st.st_mtime_ns, st.st_size)
        except OSError:
            unparseable += 1
            continue
        hit = _DEF_COUNT_CACHE.get(ckey)
        if hit is not None:
            f_i, c_i, u_i = hit
            functions += f_i
            classes += c_i
            unparseable += u_i
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"),
                             filename=str(path))
            f_i, c_i = _count_stmts(tree.body)
            u_i = 0
        except (SyntaxError, ValueError):
            f_i, c_i, u_i = 0, 0, 1
        if len(_DEF_COUNT_CACHE) > 8192:
            _DEF_COUNT_CACHE.clear()
        _DEF_COUNT_CACHE[ckey] = (f_i, c_i, u_i)
        cache_dirty = True
        functions += f_i
        classes += c_i
        unparseable += u_i
    if cache_dirty and scanned >= 32:
        try:
            disk_cache_path.write_bytes(pickle.dumps(_DEF_COUNT_CACHE, protocol=pickle.HIGHEST_PROTOCOL))
        except Exception:
            pass

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
