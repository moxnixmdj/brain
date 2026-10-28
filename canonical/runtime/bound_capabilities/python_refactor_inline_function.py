# PROJECT_BRAIN
"""python.refactor.inline_function.v1 — the inverse of extract_function, with the
same byte-exact splice law and a test referee.

A module-level function is inlined into every call site that provably names it,
each site replaced by the function's body with its parameters bound to the
arguments **once**, at the site's own indentation.  When the last call site is
gone the now-unused definition is deleted; if any caller remains (a shadowed
name, a call the law refused) the definition stays, because deleting it would
break the module.

Inlining law (what a senior engineer checks before promising an inline):

* parameters bind by assignment at the site — `a = <arg expression>` — so an
  argument expression is evaluated exactly once, and a body that mutates a
  parameter is still correct.  Positional and keyword arguments bind
  positionally/by name; defaults are materialised from the function's own
  source.  `*args` / `**kwargs` at a site refuse: the arity is not knowable
  without running the code.
* a parameter name that is already live at the site is RENAMED (`_inl_<name>`)
  rather than allowed to clobber the caller's local; the rename is applied to
  the parameter's `Name` nodes only.
* `return` must be the body's final top-level statement — a body whose return
  is inside a branch cannot be spliced into a statement list without inventing
  control flow (a flag and an indent), so it is refused, named.
* refuse, each naming the act: decorators (they wrap), `async` definitions,
  `yield`/`await`, recursion, nested `def`/`class`/`lambda` in the body (a
  second scope whose names the rename law does not reach), `global`/`nonlocal`,
  method calls (`self.f(...)` is a different call), call sites that are not a
  single-line assignment / expression statement / `return`, and a target
  function with no call site at all.
* verification: the rebuilt module must parse, the inlined sites must no longer
  name the function, and the named suite runs post-edit.  A red suite restores
  every original byte.

Inputs (kwargs, repo-confined):
  source_root, module, qualname              function coordinate (module-level)
  call_lines                                 optional 1-based lines of the sites
                                             to inline (default: every site)
  remove_function                            delete the def once unused (default true)
  output_path                                summary artifact
  run_tests, python_executable, timeout_s

result_fields: adapter, module, qualname, inlined_sites, sites_refused,
parameters_bound, renames, function_removed, edit_count, files_edited, gate,
complete, output_path, output_sha256, output_verified, verified.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

from canonical.runtime.bound_capabilities.python_refactor_rename_parameter import (
    _safe_path as _shared_safe_path,
)
from canonical.runtime.bound_capabilities.python_refactor_rename_parameter import (
    _sha256,
)


class InlineError(RuntimeError):
    """A refusal.  Not SystemExit: an adapter that exits the process takes the caller with it,
    and the door can only report that as CAPABILITY_EXITED_PROCESS -- the reason is lost."""


def _fail(reason: str) -> None:
    raise InlineError(reason)


def _safe_path(root, path, must_exist: bool = False):
    """The shared path law, minus its SystemExit: a refusal must not kill the caller."""
    try:
        return _shared_safe_path(root, path, must_exist=must_exist)
    except SystemExit as exc:  # the shared guard reports with SystemExit
        raise InlineError(str(exc)) from None


def _fn_lookup(tree: ast.Module, parts: list[str]):
    """Resolve a dotted qualname to a def, or None when it is not module-level."""
    scope: list = tree.body
    node = None
    for i, part in enumerate(parts):
        node = None
        for s in scope:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                    and s.name == part:
                node = s
                break
        if node is None:
            return None
        if i < len(parts) - 1:
            scope = node.body
    return node


def _body_lines(fn) -> tuple[int, int]:
    """The inclusive line span of the body's statements (not the `def` line)."""
    first = fn.body[0]
    first_line = min([first.lineno] + [d.lineno for d in getattr(first, "decorator_list", [])])
    return first_line, fn.body[-1].end_lineno


def _scope_names(node) -> set[str]:
    """Every identifier that could be live in this scope, however bound."""
    names: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            names.add(sub.id)
        elif isinstance(sub, ast.arg):
            names.add(sub.arg)
        elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(sub.name)
        elif isinstance(sub, ast.alias):
            names.add((sub.asname or sub.name).split(".")[0])
        elif isinstance(sub, ast.ExceptHandler) and sub.name:
            names.add(sub.name)
    return names


def _has_nested_scope(body: list) -> bool:
    for s in body:
        for sub in ast.walk(s):
            if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp,
                                ast.GeneratorExp)):
                return True
    return False


def _enclosing_stmt(tree, call) -> ast.stmt | None:
    """The statement a call node sits in, at the statement-list level."""
    found = [None]

    def visit(node, current):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                visit(child, child)
            else:
                if child is call:
                    found[0] = current
                visit(child, current)
        if node is call:
            found[0] = current

    visit(tree, None)
    return found[0]


def _bind_arguments(fn, call, text) -> list[tuple[str, str]] | None:
    """[(param, argument source)] for a call that binds this function's params."""
    args = list(call.args)
    if any(isinstance(a, ast.Starred) for a in args) or any(k.arg is None for k in call.keywords):
        return None
    params = list(fn.args.posonlyargs) + list(fn.args.args)
    defaults = list(fn.args.defaults)
    if fn.args.kwonlyargs or fn.args.vararg or fn.args.kwarg:
        return None
    bound: dict[str, str] = {}
    for param, value in zip(params, args):
        bound[param.arg] = ast.get_source_segment(text, value)
    for kw in call.keywords:
        if kw.arg not in [p.arg for p in params]:
            return None
        if kw.arg in bound:
            return None
        bound[kw.arg] = ast.get_source_segment(text, kw.value)
    missing = [p.arg for p in params if p.arg not in bound]
    if missing:
        # defaults are materialised from the function's own source, positionally from the right
        for i, dflt in enumerate(reversed(defaults)):
            param = params[len(params) - 1 - i]
            if param.arg in missing:
                bound[param.arg] = ast.get_source_segment(text, dflt)
                missing.remove(param.arg)
        if missing:
            return None
    if any(bound.get(p.arg) is None for p in params):
        return None
    return [(p.arg, bound[p.arg]) for p in params]


def _rename_body(body_text: str, body_first_line: int, renames: dict[str, str],
                 body_nodes: list) -> str:
    """Replace `Name` nodes for renamed parameters, right to left, byte-exactly."""
    offsets = [0]
    for line in body_text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    spans: list[tuple[int, int, str]] = []
    last_line = body_first_line + len(offsets) - 2
    for node in body_nodes:
        # only names AT the copied lines are renamed; a name in the trailing `return` lives in
        # the value the site receives, and renaming it into an empty body wrote a stray
        # `_inl_n` line (measured: INLINE_BODY_DEDENT_UNSAFE)
        if not (body_first_line <= (getattr(node, "lineno", 0) or 0) <= last_line):
            continue
        if isinstance(node, ast.Name) and node.id in renames:
            start = offsets[node.lineno - body_first_line] + node.col_offset
            spans.append((start, start + len(node.id), renames[node.id]))
    for start, end, new in sorted(spans, reverse=True):
        body_text = body_text[:start] + new + body_text[end:]
    return body_text


def _value_source(text, node, renames: dict[str, str]) -> str | None:
    """The return value as source, with parameter references renamed to the site's bindings.

    The expression was written inside the callee, so it names the callee's parameters.  At the
    site those names are the bindings -- renamed ones included -- and copying the expression
    unchanged reads whatever the caller happens to have under the old name (measured: an inline
    whose answer depended on the caller's `n` and was right only by coincidence).
    """
    source = ast.get_source_segment(text, node)
    if source is None:
        return None
    if not renames:
        return source
    spans = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id in renames and sub.lineno == node.lineno:
            start = sub.col_offset - node.col_offset
            spans.append((start, start + len(sub.id), renames[sub.id]))
    for start, end, new in sorted(spans, reverse=True):
        source = source[:start] + new + source[end:]
    return source


def _external_references(src_abs: Path, module_abs: Path, name: str) -> list[str]:
    """Other modules that name this function — an import, a call, or a rebinding.

    Deleting the definition is only safe when the module was its only user; a
    test file or a sibling module that does `from .calc import sub` would break.
    """
    found: list[str] = []
    for path in sorted(src_abs.rglob("*.py")):
        if path == module_abs:
            continue
        try:
            other = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        hit = False
        for sub in ast.walk(other):
            if isinstance(sub, ast.Name) and sub.id == name or isinstance(sub, ast.alias) and (sub.asname or sub.name.split(".")[-1]) == name:
                hit = True
        if hit:
            found.append(str(path.relative_to(src_abs)))
    return found


def run(args, root):
    repo = Path(root).resolve()
    args = dict(args or {})
    src_rel = str(args.get("source_root") or "")
    src_abs = _safe_path(repo, src_rel, must_exist=True)
    if not src_abs.is_dir():
        _fail("SOURCE_ROOT_NOT_DIRECTORY")
    module_rel = str(args.get("module") or "")
    if not module_rel.endswith(".py"):
        _fail("MODULE_MUST_BE_PY")
    module_abs = _safe_path(src_abs, module_rel, must_exist=True)
    qualname = str(args.get("qualname") or "")
    if not qualname:
        _fail("QUALNAME_REQUIRED")
    out_rel = str(args.get("output_path") or "")
    out_abs = _safe_path(repo, out_rel)
    python_exe = str(args.get("python_executable") or sys.executable)
    timeout_s = int(args.get("timeout_s") or 300)
    run_tests = list(args.get("run_tests") or [])
    remove_function = args.get("remove_function")
    remove_function = True if remove_function is None else bool(remove_function)
    wanted_lines = [int(x) for x in (args.get("call_lines") or [])]

    original_bytes = module_abs.read_bytes()
    text = original_bytes.decode("utf-8")
    lines = text.splitlines(keepends=True)
    try:
        tree = ast.parse(text, filename=module_rel)
    except SyntaxError as exc:
        _fail("SYNTAX_ERROR_IN_FILE:" + module_rel + ":" + str(exc))

    parts = qualname.split(".")
    fn = _fn_lookup(tree, parts)
    if fn is None:
        _fail("SYMBOL_NOT_FOUND:" + qualname)
    if len(parts) > 1:
        _fail("NESTED_FUNCTION_UNSUPPORTED:" + qualname)
    if isinstance(fn, ast.AsyncFunctionDef):
        _fail("ASYNC_FUNCTION_UNSUPPORTED:" + qualname)
    if not isinstance(fn, ast.FunctionDef):
        _fail("NOT_A_FUNCTION:" + qualname)
    if fn.decorator_list:
        _fail("DECORATED_FUNCTION_UNSUPPORTED:" + qualname)
    if _has_nested_scope(fn.body):
        _fail("INLINE_BODY_HAS_NESTED_SCOPE:" + qualname)
    for sub in ast.walk(fn):
        if isinstance(sub, (ast.Yield, ast.YieldFrom, ast.Await)):
            _fail("INLINE_BODY_IS_A_GENERATOR")
        if isinstance(sub, (ast.Global, ast.Nonlocal)):
            _fail("INLINE_BODY_HAS_GLOBAL_OR_NONLOCAL")
        if isinstance(sub, ast.Name) and sub.id == fn.name:
            _fail("RECURSIVE_FUNCTION_UNSUPPORTED:" + qualname)
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str) \
                and sub.end_lineno != sub.lineno:
            _fail("INLINE_BODY_HAS_MULTILINE_STRING")

    returns = [s for s in ast.walk(fn) if isinstance(s, ast.Return)]
    if len(returns) > 1:
        _fail("INLINE_MULTIPLE_RETURNS:" + str(len(returns)))
    ret_stmt = returns[0] if returns else None
    if ret_stmt is not None and fn.body[-1] is not ret_stmt:
        _fail("INLINE_BODY_HAS_BRANCHING_RETURN")

    # every call site in this module that is a plain name reference
    sites = []
    remaining_unknown = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != fn.name:
            continue
        stmt = _enclosing_stmt(tree, node)
        if stmt is None or getattr(node, "lineno", None) is None:
            remaining_unknown.append("UNKNOWN_SITE")
            continue
        if stmt.lineno != stmt.end_lineno:
            remaining_unknown.append("MULTILINE_SITE:%d" % stmt.lineno)
            continue
        if not isinstance(stmt, (ast.Assign, ast.AugAssign, ast.Expr, ast.Return)):
            remaining_unknown.append("CALL_SITE_NOT_INLINABLE_STATEMENT:%d" % stmt.lineno)
            continue
        if isinstance(stmt, ast.AugAssign) and not isinstance(stmt.target, ast.Name):
            remaining_unknown.append("CALL_SITE_NOT_INLINABLE_STATEMENT:%d" % stmt.lineno)
            continue
        if isinstance(stmt, ast.Assign) and not (
                len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name)):
            remaining_unknown.append("CALL_SITE_NOT_INLINABLE_STATEMENT:%d" % stmt.lineno)
            continue
        if isinstance(stmt, (ast.Assign, ast.AugAssign, ast.Return)) and stmt.value is not node:
            remaining_unknown.append("CALL_SITE_INSIDE_EXPRESSION:%d" % stmt.lineno)
            continue
        bound = _bind_arguments(fn, node, text)
        if bound is None:
            remaining_unknown.append("CALL_SITE_ARITY_NOT_BINDABLE:%d" % stmt.lineno)
            continue
        sites.append((stmt, node, bound))
    sites.sort(key=lambda s: s[0].lineno)
    if not sites:
        _fail("INLINE_NO_CALL_SITES:" + qualname + ":" + ",".join(remaining_unknown[:3]))
    if wanted_lines:
        chosen = [s for s in sites if s[0].lineno in wanted_lines]
        if len(chosen) != len(wanted_lines):
            got = {s[0].lineno for s in chosen}
            _fail("CALL_LINE_IS_NOT_A_BINDABLE_SITE:" +
                  ",".join(str(n) for n in wanted_lines if n not in got))
        sites = chosen

    body_first, body_last = _body_lines(fn)
    if ret_stmt is not None:
        # the final `return` is not copied -- its VALUE is what the site receives, emitted
        # below at the site's own shape; copying it too is what put `return n * 2` in the middle
        # of a loop body (measured: the code ran, the answer was wrong, PASS_BLIND)
        body_last = fn.body[-2].end_lineno if len(fn.body) > 1 else body_first - 1
    base_indent = fn.body[0].col_offset
    body_text = "".join(lines[body_first - 1:body_last])
    body_nodes = [n for stmt in fn.body for n in ast.walk(stmt)]

    module_names = _scope_names(tree)

    edits: list[tuple[int, list[str]]] = []
    site_report = []
    renames_all: dict[str, str] = {}
    for stmt, node, bound in sites:
        scope_root = tree
        # the enclosing scope: a call inside a function sees that function's names
        for cand in ast.walk(tree):
            if isinstance(cand, (ast.FunctionDef, ast.AsyncFunctionDef)) and \
                    cand.lineno <= stmt.lineno <= (cand.end_lineno or cand.lineno) and cand is not fn:
                scope_root = cand
        live = _scope_names(scope_root)
        renames: dict[str, str] = {}
        for param, _ in bound:
            if param in live:
                fresh = "_inl_" + param
                n = 1
                while fresh in module_names or fresh in live:
                    n += 1
                    fresh = "_inl_%s%d" % (param, n)
                renames[param] = fresh
                module_names.add(fresh)
        renamed_body = _rename_body(body_text, body_first, renames, body_nodes) if renames \
            else body_text

        indent = " " * stmt.col_offset
        out: list[str] = []
        for param, value in bound:
            out.append(indent + (renames.get(param, param)) + " = " + value + "\n")
        for line in renamed_body.splitlines(keepends=True):
            if not line.strip():
                out.append("\n")
                continue
            if line[:base_indent].strip() != "":
                _fail("INLINE_BODY_DEDENT_UNSAFE:%d" % stmt.lineno)
            out.append(indent + line[base_indent:])
        if ret_stmt is not None:
            if ret_stmt.value is not None and ret_stmt.value.end_lineno != ret_stmt.value.lineno \
                    and ret_stmt.lineno != ret_stmt.end_lineno:
                _fail("INLINE_RETURN_VALUE_IS_MULTILINE")
            value_src = _value_source(text, ret_stmt.value, renames) if ret_stmt.value else None
            if isinstance(stmt, ast.Assign):
                if value_src is None:
                    _fail("INLINE_FUNCTION_RETURNS_NOTHING:%d" % stmt.lineno)
                out.append(indent + ast.unparse(stmt.targets[0]) + " = " + value_src + "\n")
            elif isinstance(stmt, ast.AugAssign):
                if value_src is None:
                    _fail("INLINE_FUNCTION_RETURNS_NOTHING:%d" % stmt.lineno)
                op = lines[stmt.lineno - 1][stmt.target.end_col_offset:stmt.value.col_offset].strip()
                if not op.endswith("="):
                    _fail("CALL_SITE_NOT_INLINABLE_STATEMENT:%d" % stmt.lineno)
                out.append(indent + stmt.target.id + " " + op + " " + value_src + "\n")
            elif isinstance(stmt, ast.Return):
                out.append(indent + ("return " + value_src if value_src else "return") + "\n")
            else:
                if value_src is not None:
                    out.append(indent + value_src + "\n")
        else:
            if isinstance(stmt, (ast.Assign, ast.AugAssign, ast.Return)):
                _fail("INLINE_FUNCTION_RETURNS_NOTHING:%d" % stmt.lineno)
        # a trailing comment on the call line survives the splice
        line_text = lines[stmt.lineno - 1]
        tail = line_text[stmt.end_col_offset:]
        if "#" in tail:
            comment = tail[tail.index("#"):].rstrip("\n")
            if out:
                out[-1] = out[-1].rstrip("\n") + "  " + comment + "\n"
        edits.append((stmt.lineno, out))
        site_report.append({"line": stmt.lineno, "params_bound": [p for p, _ in bound]})
        renames_all.update(renames)

    # splice bottom-up so earlier line numbers stay valid
    rebuilt = list(lines)
    for lineno, out in sorted(edits, key=lambda e: e[0], reverse=True):
        rebuilt[lineno - 1:lineno] = out
    new_text = "".join(rebuilt)
    try:
        ast.parse(new_text)
    except SyntaxError as exc:
        _fail("SPAN_INTEGRITY:rebuilt_module_unparseable:" + str(exc))

    # does the definition still have a caller?
    post = ast.parse(new_text)
    still_called = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                       and n.func.id == fn.name for n in ast.walk(post))
    function_removed = False
    external = _external_references(src_abs, module_abs, fn.name)
    if remove_function and not still_called and not external:
        start = fn.lineno
        end = fn.end_lineno
        plines = new_text.splitlines(keepends=True)
        del plines[start - 1:end]
        # collapse the blank run the def left behind: module-level blocks are separated by
        # exactly two blank lines, and a deletion must not leave a longer gap behind
        collapsed: list[str] = []
        for line in plines:
            if line.strip() == "" and collapsed and collapsed[-1].strip() == "" \
                    and len(collapsed) >= 2 and collapsed[-2].strip() == "":
                continue
            collapsed.append(line)
        candidate = "".join(collapsed)
        try:
            ast.parse(candidate)
            new_text = candidate
            function_removed = True
        except SyntaxError:
            function_removed = False

    module_abs.write_text(new_text, encoding="utf-8")

    evidence: dict = {"run_tests": run_tests, "sites_refused": remaining_unknown}
    gate = "PASS"
    if run_tests:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        try:
            proc = subprocess.run([python_exe, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
                                  + run_tests, cwd=src_abs, capture_output=True, text=True,
                                  timeout=timeout_s, env=env, check=False)
        except subprocess.TimeoutExpired:
            module_abs.write_bytes(original_bytes)
            _fail("TIMEOUT:inlining fully rolled back")
        evidence["pytest_rc"] = proc.returncode
        evidence["pytest_tail"] = proc.stdout.strip().splitlines()[-3:]
        if proc.returncode != 0:
            module_abs.write_bytes(original_bytes)
            _fail("TESTS_RED_AFTER_EDIT:inlining fully rolled back:" +
                  ";".join((proc.stdout.strip().splitlines() or ["<no output>"])[-2:])[:300])
        verified = True
    else:
        gate = "PASS_BLIND"
        verified = False

    artifact = {
        "schema": "brain.python.refactor.inline_function.v1/1",
        "source_root": src_rel,
        "module": module_rel,
        "qualname": qualname,
        "inlined_sites": [s["line"] for s in site_report],
        "parameters_bound": {str(s["line"]): s["params_bound"] for s in site_report},
        "renames": renames_all,
        "sites_refused": remaining_unknown,
        "function_removed": function_removed,
        "external_references": external,
        "edit_count": len(edits),
        "files_edited": [module_rel],
        "verification": evidence,
        "gate": gate,
        "law": ("each call site becomes the callee's body with its parameters bound once, "
                "at the site's indentation; a name already live at the site is renamed; "
                "the definition is deleted only once no call names it; the rebuilt module "
                "must parse and the named suite must stay green or every byte is restored"),
        "complete": True,
    }
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    text_out = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
    out_abs.write_text(text_out, encoding="utf-8")
    return {
        "adapter": "python_refactor_inline_function",
        "module": module_rel,
        "qualname": qualname,
        "inlined_sites": [s["line"] for s in site_report],
        "renames": renames_all,
        "sites_refused": remaining_unknown,
        "function_removed": function_removed,
        "external_references": external,
        "edit_count": len(edits),
        "files_edited": [module_rel],
        "gate": gate,
        "complete": True,
        "output_path": out_rel,
        "output_sha256": _sha256(text_out.encode("utf-8")),
        "output_verified": json.loads(out_abs.read_text(encoding="utf-8")) == artifact,
        "verified": verified,
    }


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--source_root", required=True)
    p.add_argument("--module", required=True)
    p.add_argument("--qualname", required=True)
    p.add_argument("--call_lines", nargs="*", type=int, default=None)
    p.add_argument("--output_path", required=True)
    p.add_argument("--run_tests", nargs="*", default=None)
    p.add_argument("--timeout_s", type=int, default=300)
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
