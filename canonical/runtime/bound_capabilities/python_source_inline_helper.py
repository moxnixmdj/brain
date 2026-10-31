#!/usr/bin/env python3
"""python.refactor.inline_helper.v1 — a one-use helper becomes its own body.

"Inline the single-use helper _price_with_tax in <b>/app/service.py into its only
caller" is the oldest refactor in the book, and the book already gives the rule:
substitute the arguments for the parameters, then delete the definition.  What
makes it safe in an automated tool is not the substitution -- it is knowing when
the substitution is *legal*, and that has a precise answer:

  1. ONE call site in the whole tree.  (Two callers is not "inline", it is "delete
     a function two callers need".)
  2. Every argument at that site is RE-EVALUABLE: a name, a literal, a subscript,
     an attribute, or an arithmetic combination of those.  A call, a lambda, an
     await, a comprehension or an assignment expression is evaluated for its
     effects and MUST NOT be duplicated -- substituting `f()` for two parameter
     uses would run it twice, which is exactly the class of bug an inliner is
     famous for introducing.
  3. The body is a single `return <expression>`.  A helper with branches is not a
     value; inlining it is a different task, and this adapter refuses it rather
     than flattening control flow.
  4. No `*args`/`**kwargs`, and defaults only when the call passes every parameter
     positionally, so the substitution is total.

Then the proof, which is the only reason any of this is trustworthy: the file must
parse, the helper's name must appear NOWHERE afterwards, and the project's suite
must be green.  Every original byte is restored on failure.

The caller's expression text is re-parenthesised when it is not atomic, so
`sum(_f(i["p"], rate) ...)` becomes `sum(((i["p"] + i["p"] * rate // 100)) ...)`
and operator precedence can never change the answer.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import pathlib
import re
import subprocess
import sys

SCHEMA = "PROJECT_BRAIN_PYTHON_INLINE_HELPER_V1"
CAPABILITY_ID = "python.refactor.inline_helper.v1"
PROVIDES = ["python.refactor.inline_helper", "python.refactor.single_use_inlined"]
REQUIRES: list[str] = []

_RE_EVALUABLE = (ast.Name, ast.Constant, ast.Subscript, ast.Attribute, ast.BinOp,
                 ast.UnaryOp, ast.Tuple, ast.List, ast.Compare, ast.BoolOp)


def _safe_root(repo: pathlib.Path, raw) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if p != repo and repo not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not p.exists():
        raise RuntimeError("SOURCE_ROOT_MISSING")
    return p


def _rel(repo: pathlib.Path, path: pathlib.Path) -> str:
    return str(path.relative_to(repo)).replace("\\", "/")


def _files(root: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in sorted(root.rglob("*.py"))
            if "__pycache__" not in p.parts and ".git" not in p.parts]


def _reevaluable(node) -> bool:
    """Could this expression be evaluated twice with the same result and no effect?"""
    if isinstance(node, ast.Call):
        return False
    if isinstance(node, (ast.Lambda, ast.Await, ast.Yield, ast.YieldFrom, ast.NamedExpr)):
        return False
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        return False
    for child in ast.iter_child_nodes(node):
        # `ctx` is a Load/Store marker, not an expression; asking whether it can be
        # re-evaluated is a category error and made every Name look unsafe.
        if isinstance(child, ast.expr_context):
            continue
        if not _reevaluable(child):
            return False
    return isinstance(node, _RE_EVALUABLE) or isinstance(node, ast.expr) and not any(
        isinstance(child, ast.Call) for child in ast.walk(node))


def _helper(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _single_return(fn) -> ast.expr | None:
    if fn.decorator_list or getattr(fn, "args", None) is None:
        return None
    args = fn.args
    if args.vararg or args.kwarg or args.posonlyargs or args.kwonlyargs:
        return None
    if not (len(fn.body) == 1 and isinstance(fn.body[0], ast.Return)
            and fn.body[0].value is not None):
        return None
    return fn.body[0].value


def _suite(project_root: pathlib.Path, tests: pathlib.Path, timeout_s: int) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover",
             "-s", str(tests), "-t", str(project_root)],
            cwd=str(project_root), capture_output=True, text=True, timeout=timeout_s,
            env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(project_root),
                 "PATH": "/usr/local/bin:/usr/bin:/bin"})
    except subprocess.TimeoutExpired:
        return False, "SUITE_TIMEOUT"
    return proc.returncode == 0, ((proc.stdout or "") + (proc.stderr or ""))[-300:]


def _offset_table(text: str) -> list[int]:
    table = [0]
    for line in text.splitlines(keepends=True):
        table.append(table[-1] + len(line))
    return table


def run(args, root):
    repo = pathlib.Path(root).resolve()
    source_root = _safe_root(repo, args.get("source_root"))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    helper_name = str(args.get("helper_name") or "").strip()
    timeout_s = int(args.get("timeout_s") or 60)

    # The project is the directory holding both the subject and its tests.  When
    # the subject IS the repository the project is the repository -- measured:
    # taking the parent of the repo root pointed discovery at /home/user/tests.
    project_root = (source_root.parent
                    if source_root != repo and source_root.name not in ("", ".")
                    else source_root)
    tests = project_root / "tests"
    if not tests.is_dir():
        raise RuntimeError("TEST_ROOT_MISSING")

    # ONE candidate definition.  The word "single-use" in the sentence is a
    # property of the TREE, not a hint: a helper is single-use iff exactly one
    # call site reaches it.  Measured: selecting on "single return" alone matched
    # the caller too (it also ends in a return), so the tree decides, not the shape.
    sites_by_name: dict[str, int] = {}
    parsed: list[tuple[pathlib.Path, ast.Module, str]] = []
    for path in _files(source_root):
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(path))
        except (OSError, SyntaxError, ValueError):
            continue
        parsed.append((path, tree, text))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                sites_by_name[node.func.id] = sites_by_name.get(node.func.id, 0) + 1

    definitions: list[tuple[pathlib.Path, ast.Module, ast.AST]] = []
    for path, tree, _text in parsed:
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if helper_name:
                if node.name == helper_name:
                    definitions.append((path, tree, node))
                continue
            if _single_return(node) is None:
                continue
            if sites_by_name.get(node.name, 0) != 1:
                continue
            definitions.append((path, tree, node))
    if not definitions:
        raise RuntimeError("NO_SINGLE_RETURN_HELPER_FOUND"
                           + (":" + helper_name if helper_name else ""))
    if len(definitions) > 1:
        raise RuntimeError("HELPER_AMBIGUOUS:" + ",".join(sorted({d[2].name for d in definitions})))
    helper_path, helper_tree, helper = definitions[0]
    name = helper.name
    body_expr = _single_return(helper)
    params = [a.arg for a in helper.args.args]

    # Every call site in the subject, with its argument expressions.
    sites: list[tuple[pathlib.Path, str, ast.Module, ast.Call]] = []
    for path in _files(source_root):
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(path))
        except (OSError, SyntaxError, ValueError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == name:
                sites.append((path, text, tree, node))
    if len(sites) != 1:
        raise RuntimeError("CALL_SITE_COUNT_NOT_ONE:" + str(len(sites)))
    site_path, site_text, _site_tree, call = sites[0]
    if call.keywords or len(call.args) != len(params):
        raise RuntimeError("CALL_DOES_NOT_MATCH_SIGNATURE_POSITIONALLY")

    arg_texts: list[str] = []
    for arg in call.args:
        if not _reevaluable(arg):
            raise RuntimeError("ARGUMENT_IS_NOT_RE_EVALUABLE:" + type(arg).__name__)
        snippet = ast.get_source_segment(site_text, arg)
        if not snippet:
            raise RuntimeError("ARGUMENT_TEXT_UNAVAILABLE")
        arg_texts.append(snippet)

    # Substitute by rebuilding the returned expression with the argument ASTs.
    substituted = copy.deepcopy(body_expr)
    mapping = dict(zip(params, arg_texts))
    for node in ast.walk(substituted):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id in mapping:
            node.id = mapping[node.id]

    # Re-parse the rendered body from its substituted TEXT so the splice uses the
    # caller's own spelling, then render with `ast.unparse` -- the ONLY text this
    # adapter rewrites is the call itself.
    body_text = ast.unparse(body_expr)
    for param, arg_text in mapping.items():
        body_text = re.sub(r"(?<![A-Za-z0-9_.])" + re.escape(param) + r"(?![A-Za-z0-9_])",
                           "(" + arg_text + ")", body_text)
    inlined = "(" + body_text + ")"

    originals: dict[pathlib.Path, bytes] = {}
    edits: list[dict] = []

    def splice(text: str, node, replacement: str) -> str:
        table = _offset_table(text)
        start = table[node.lineno - 1] + node.col_offset
        end = table[node.end_lineno - 1] + node.end_col_offset
        return text[:start] + replacement + text[end:]

    # 1) the call site
    new_site = splice(site_text, call, inlined)
    originals[site_path] = site_path.read_bytes()
    edits.append({"file": _rel(repo, site_path), "line": int(call.lineno),
                  "edit": "CALL_REPLACED_BY_BODY", "inlined": inlined})

    # 2) the helper definition, and its definition only
    table = _offset_table(site_text)
    if site_path == helper_path:
        helper_text = new_site
        # offsets moved after the call replacement: re-parse to find the def again.
        new_tree = ast.parse(helper_text, filename=str(helper_path))
        again = _helper(new_tree, name)
        if again is None:
            raise RuntimeError("HELPER_DISAPPEARED_AFTER_CALL_REPLACEMENT")
        start = table[again.lineno - 1] + again.col_offset
        end = table[again.end_lineno - 1] + again.end_col_offset
        tail = helper_text[end:]
        while tail.startswith("\n\n"):
            tail = tail[1:]
            end += 1
        helper_text = helper_text[:start] + tail
        new_site = helper_text
        edits.append({"file": _rel(repo, site_path), "edit": "DEFINITION_DELETED",
                      "lines": [int(again.lineno), int(again.end_lineno)]})
    try:
        ast.parse(new_site, filename=str(site_path))
    except SyntaxError as exc:
        raise RuntimeError("INLINED_FILE_DOES_NOT_PARSE:" + str(exc.lineno))
    site_path.write_text(new_site, encoding="utf-8")

    # PROOF 1: the helper's name survives nowhere in the subject.
    survivors = [str(p.relative_to(repo)) for p in _files(source_root)
                 if re.search(r"(?<![A-Za-z0-9_.])" + re.escape(name) + r"(?![A-Za-z0-9_])",
                              path_text(p))]
    if survivors:
        for p, b in originals.items():
            p.write_bytes(b)
        raise RuntimeError("HELPER_NAME_SURVIVED_IN:" + ",".join(survivors))

    # PROOF 2: behaviour, by the project's own suite.
    ok, tail_out = _suite(project_root, tests, timeout_s)
    if not ok:
        for p, b in originals.items():
            p.write_bytes(b)
        raise RuntimeError("SUITE_FAILED_AFTER_INLINE:" + tail_out.replace("\n", " ")[-200:])

    report = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "source_root": _rel(repo, source_root),
        "helper": name,
        "parameters": params,
        "arguments": arg_texts,
        "inlined_expression": inlined,
        "edits": edits,
        "files_edited": sorted(_rel(repo, p) for p in originals),
        "suite_passed": True,
        "law": "a single-use helper whose arguments are re-evaluable is inlined by substituting "
               "the arguments for the parameters; a duplicated call is never substituted",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.write_bytes(raw)
    return {
        "adapter": "python_source_inline_helper",
        "answer": name,
        "helper": name,
        "inlined_expression": inlined,
        "edits": edits,
        "files_edited": report["files_edited"],
        "suite_passed": True,
        "output_path": _rel(repo, output),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": True,
    }


def path_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""
