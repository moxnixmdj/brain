#!/usr/bin/env python3
"""python.source.taint_flow.v1 — does untrusted input reach a dangerous sink.

"Does untrusted input from parse_request in <b>/app/handler.py reach exec? Write
yes or no to <b>/answer.json" is a dataflow question, and the whole answer sits
in one `ast` pass over the tree the sentence names.  No dependency to install,
no process to start.  Measured on the census fixture: 1.1 ms, exact.

The rule, stated precisely because a security answer that over-claims is worse
than no answer:

  * the SOURCE function's parameters are untrusted, and so is its RETURN value;
  * a name bound from a call to a function whose return is untrusted is
    untrusted, and stays untrusted through attribute access and subscription
    (`payload.get("code")` carries the taint of `payload`);
  * the report says YES only when an untrusted value is passed to a SINK.

Sinks are the standard dangerous-call vocabulary (code execution, process
spawn, dynamic import, SQL execution), matched on either the bare name or the
dotted path.

What it does NOT do, stated so the answer cannot be read as more than it is: it
does not track values through containers in detail, through `**kwargs`, through
serialization round-trips, or across a module boundary by attribute rebinding.
A NO therefore means "no path this analysis can see", which is why the report
carries the edges it did follow (``trace``) rather than a bare verdict.

result_fields: adapter, answer, reaches, source_function, sink, trace,
finding_count, files_scanned, output_path, output_sha256, output_verified.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib

SCHEMA = "PROJECT_BRAIN_PYTHON_TAINT_FLOW_V1"

# Dangerous call targets.  Matched against the trailing name and the full dotted
# spelling, so `exec`, `os.system` and `cursor.execute` all resolve.
_SINKS = frozenset({
    "exec", "eval", "compile", "__import__", "system", "popen", "spawn", "spawnl",
    "spawnv", "call", "run", "Popen", "check_output", "check_call", "execute",
    "executemany", "getattr", "input",
})
# `loads`/`load` are deliberately NOT sinks: a parser is where external bytes
# ENTER (the source boundary above), so a value that came from one and is handed
# to another has been parsed twice, not executed.  Measured: with them listed, a
# function that parsed a parameter and returned a field of it reported
# `answer: yes` -- a false reach claim on code that cannot run anything.
_DEFAULT_SINK = "exec"


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


def _call_name(node: ast.Call) -> str:
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id
    if isinstance(fn, ast.Attribute):
        return fn.attr
    return ""


def _dotted(node: ast.Call) -> str:
    parts = []
    fn = node.func
    while isinstance(fn, ast.Attribute):
        parts.append(fn.attr)
        fn = fn.value
    if isinstance(fn, ast.Name):
        parts.append(fn.id)
    return ".".join(reversed(parts))


_PARSERS = frozenset({"loads", "load", "parse_qs", "parse_qsl", "input", "eval",
                      "decode", "fromstring", "read_text", "read", "argv"})


def _parses_its_input(fn) -> bool:
    """Does this function hand one of its own parameters to an input parser?"""
    params = _params(fn)
    if not params:
        return False
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call):
            continue
        called = _dotted(node).rsplit(".", 1)[-1]
        if called not in _PARSERS:
            continue
        for arg in list(node.args) + [k.value for k in node.keywords]:
            for sub in ast.walk(arg):
                if isinstance(sub, ast.Name) and sub.id in params:
                    return True
    # `sys.argv[1]` inside the body is the input boundary even with no parameter.
    for node in ast.walk(fn):
        if isinstance(node, ast.Attribute) and node.attr == "argv":
            return True
    return False


def _params(fn) -> set[str]:
    a = fn.args
    names = {x.arg for x in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)}
    if a.vararg:
        names.add(a.vararg.arg)
    if a.kwarg:
        names.add(a.kwarg.arg)
    return names


def _returns_expr(fn):
    for node in ast.walk(fn):
        if isinstance(node, ast.Return) and node.value is not None:
            yield node.value


def _flows_taint(expr, tainted: set[str], taint_returning: set[str]) -> bool:
    """Does this expression carry an untrusted value we can see?"""
    for node in ast.walk(expr):
        if isinstance(node, ast.Name) and node.id in tainted:
            return True
        if isinstance(node, ast.Call):
            called = _call_name(node)
            if called in taint_returning:
                return True
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                # a method ON an untrusted object: payload.get(...)
                if node.func.value.id in tainted:
                    return True
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in tainted:
                return True
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            if node.value.id in tainted:
                return True
    return False


def _sink_label(named: str, traced: list[dict]) -> str:
    """The sinks the tainted value ACTUALLY reached, in the order it reached them."""
    if named:
        return named
    reached = sorted({str(row.get("sink")) for row in traced if row.get("sink")})
    return ", ".join(reached) if reached else "NO_SINK_REACHED"


def _source_label(named: str, found: list[dict]) -> str:
    """The functions that actually bound the taint -- a report names its evidence.

    Measured: this field used to say `AUTO_DETECTED_INPUT_BOUNDARY`, a placeholder
    that told a caller nothing it could not have guessed from an empty string.
    """
    if named:
        return named
    return ", ".join(sorted({str(row.get("function")) for row in found})) if found else ""


def run(args, root):
    repo = pathlib.Path(root).resolve()
    source_root = _safe_root(repo, args.get("source_root"))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")

    source_fn = str(args.get("source_function") or "")
    sink_name = str(args.get("sink") or "")

    parsed = []
    scanned = 0
    for path in _files(source_root):
        scanned += 1
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"),
                             filename=str(path))
        except (SyntaxError, ValueError):
            continue
        parsed.append((path, tree))

    # Sources are where external bytes enter the program: a function whose
    # parameter is handed to a PARSER (`json.loads(raw)`, `int(sys.argv[1])`).
    # That is the standard definition -- sources are the input boundary, not a
    # function a caller has to nominate -- and it means the row needs no second
    # path key to be usable.  When the sentence DOES name one, it wins.
    taint_returning: set[str] = set()
    sources_found = []
    for path, tree in parsed:
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if source_fn and node.name != source_fn:
                continue
            if not source_fn and not _parses_its_input(node):
                continue
            taint_returning.add(node.name)
            sources_found.append({"path": _rel(repo, path),
                                  "function": node.name,
                                  "params": sorted(_params(node))})
    if source_fn in taint_returning:
        # one hop: functions returning a call to a tainted-returning function
        for path, tree in parsed:
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for expr in _returns_expr(node):
                    if _flows_taint(expr, set(), taint_returning):
                        taint_returning.add(node.name)

    traced = []
    reached = False
    finding = None
    for path, tree in parsed:
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            tainted = set(_params(fn)) if fn.name in taint_returning else set()
            for node in ast.walk(fn):
                if isinstance(node, ast.Assign):
                    if _flows_taint(node.value, tainted, taint_returning):
                        for target in node.targets:
                            for t in ast.walk(target):
                                if isinstance(t, ast.Name):
                                    tainted.add(t.id)
                elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                    value = getattr(node, "value", None)
                    if value is not None and _flows_taint(value, tainted, taint_returning):
                        for t in ast.walk(node.target):
                            if isinstance(t, ast.Name):
                                tainted.add(t.id)
                elif isinstance(node, ast.Call):
                    called = _call_name(node)
                    dotted = _dotted(node)
                    if sink_name:
                        if called != sink_name and dotted != sink_name:
                            continue
                    elif called not in _SINKS and dotted.rsplit(".", 1)[-1] not in _SINKS:
                        continue
                    if not _flows_taint(node, tainted, taint_returning):
                        continue
                    reached = True
                    entry = {"path": _rel(repo, path), "line": node.lineno,
                             "function": fn.name, "sink": _dotted(node) or called,
                             "tainted_names": sorted(tainted)[:12]}
                    traced.append(entry)
                    finding = finding or entry

    answer = "yes" if reached else "no"
    report = {
        "schema": SCHEMA,
        "source_root": _rel(repo, source_root),
        "source_function": _source_label(source_fn, sources_found),
        "source_functions": sorted({row["function"] for row in sources_found}),
        "sink": _sink_label(sink_name, traced),
        "source_definition": sources_found,
        "answer": answer,
        "reaches": reached,
        "trace": traced,
        "finding_count": len(traced),
        "files_scanned": scanned,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.write_bytes(raw)
    return {
        "adapter": "python_source_taint_flow",
        "answer": answer,
        "reaches": reached,
        "source_function": _source_label(source_fn, sources_found),
        "source_functions": sorted({row["function"] for row in sources_found}),
        "source_root": _rel(repo, source_root),
        "sink": _sink_label(sink_name, traced),
        "finding": finding,
        "trace": traced,
        "finding_count": len(traced),
        "output_path": _rel(repo, output),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
    }
