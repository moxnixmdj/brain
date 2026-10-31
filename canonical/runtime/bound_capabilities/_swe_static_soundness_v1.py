"""Shared active-registry loader and deterministic stdlib Python static/type/security analyzer.

Zero external binary dependencies, zero subprocess calls, <5ms per module.
Catches:
- UNDEFINED_NAME (lexical scope + closure + comprehension + module prepass)
- CALL_ARITY_MISMATCH & UNKNOWN_KEYWORD_ARG against resolved Python signatures
- ANNOTATION_LITERAL_MISMATCH (`x: int = "s"`, `def f() -> int: return "s"`)
- ZERO_DIVISION_LITERAL & INCOMPATIBLE_LITERAL_BINOP (`"a" + 1`)
- UNREACHABLE_STATEMENT, DUPLICATE_DICT_KEY, DANGEROUS_DYNAMIC_EXEC (`eval`/`shell=True`)
"""
from __future__ import annotations

import ast
import builtins
import json
import pathlib
from typing import Any

_BUILTINS = frozenset(dir(builtins)) | {"__file__", "__name__", "__doc__", "__package__", "__all__", "__annotations__"}

_PRIM_MAP: dict[str, tuple[type, ...]] = {
    "int": (int,),
    "float": (int, float),
    "str": (str,),
    "bytes": (bytes,),
    "bool": (bool,),
    "list": (list,),
    "dict": (dict,),
    "set": (set,),
    "tuple": (tuple,),
    "None": (type(None),),
}


def active_bound_registry_path(repo: pathlib.Path) -> pathlib.Path:
    primary = repo / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    if primary.is_file():
        head = primary.read_bytes()[:8].lstrip()
        if head.startswith(b"{"):
            return primary
    snap = repo / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json"
    if snap.is_file():
        return snap
    return primary


def load_active_bound_registry(repo: pathlib.Path) -> dict[str, Any]:
    path = active_bound_registry_path(repo)
    doc = dict(json.loads(path.read_text(encoding="utf-8")))
    caps = dict(doc.get("capabilities") or {})
    snap = repo / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json"
    if snap.is_file() and snap != path:
        sdoc = json.loads(snap.read_text(encoding="utf-8"))
        caps.update(sdoc.get("capabilities") or {})
    doc["capabilities"] = caps
    return doc


def _matches_prim_annotation(ann_str: str, val: Any) -> bool:
    ann = ann_str.strip()
    if "Any" in ann or "|" in ann or "Optional" in ann or "Union" in ann:
        if val is None and ("None" in ann or "Optional" in ann):
            return True
        for base, types in _PRIM_MAP.items():
            if base in ann and isinstance(val, types):
                if base == "int" and isinstance(val, bool):
                    continue
                return True
        return True
    base = ann.split("[", 1)[0].strip()
    allowed = _PRIM_MAP.get(base)
    if allowed is None:
        return True
    if base in ("int", "float") and isinstance(val, bool):
        return False
    return isinstance(val, allowed)


def _sig_spec(fn: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool = False) -> dict[str, Any]:
    pos = [a.arg for a in fn.args.posonlyargs] + [a.arg for a in fn.args.args]
    if is_method and pos and pos[0] in ("self", "cls"):
        pos = pos[1:]
    n_defaults = len(fn.args.defaults)
    min_pos = max(0, len(pos) - n_defaults)
    max_pos = None if fn.args.vararg is not None else len(pos)
    kw_names = {a.arg for a in fn.args.args[len(fn.args.args) - len(pos):]} | {a.arg for a in fn.args.kwonlyargs}
    req_kw = {
        a.arg
        for a, d in zip(fn.args.kwonlyargs, fn.args.kw_defaults)
        if d is None
    }
    ret_ann = ast.unparse(fn.returns) if fn.returns is not None else None
    return {
        "min_pos": min_pos,
        "max_pos": max_pos,
        "has_kwarg": fn.args.kwarg is not None,
        "kw_names": kw_names,
        "req_kw": req_kw,
        "ret_ann": ret_ann,
    }


def _collect_bound_names(target: ast.AST, out: set[str]) -> None:
    for sub in ast.walk(target):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, (ast.Store, ast.Del)):
            out.add(sub.id)


def analyze_python_module_ast(tree: ast.Module, rel_path: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    mod_scope: set[str] = set()
    func_sigs: dict[str, dict[str, Any]] = {}

    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            mod_scope.add(stmt.name)
            func_sigs[stmt.name] = _sig_spec(stmt, is_method=False)
        elif isinstance(stmt, ast.ClassDef):
            mod_scope.add(stmt.name)
            for sub in stmt.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name == "__init__":
                    func_sigs[stmt.name] = _sig_spec(sub, is_method=True)
        elif isinstance(stmt, ast.Import):
            for a in stmt.names:
                mod_scope.add(a.asname or a.name.split(".")[0])
        elif isinstance(stmt, ast.ImportFrom):
            for a in stmt.names:
                if a.name == "*":
                    # Star import makes unknown names non-provable statically
                    mod_scope.add("*")
                else:
                    mod_scope.add(a.asname or a.name)
        elif isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                _collect_bound_names(t, mod_scope)
        elif isinstance(stmt, ast.AnnAssign):
            _collect_bound_names(stmt.target, mod_scope)
        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            _collect_bound_names(stmt.target, mod_scope)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            for item in stmt.items:
                if item.optional_vars is not None:
                    _collect_bound_names(item.optional_vars, mod_scope)

    has_star_import = "*" in mod_scope

    def _check_block_reachability(stmts: list[ast.stmt]) -> None:
        terminated = False
        for s in stmts:
            if terminated:
                findings.append({
                    "file": rel_path,
                    "line": getattr(s, "lineno", 1),
                    "code": "UNREACHABLE_STATEMENT",
                    "severity": "warning",
                    "message": "Statement is unreachable after terminal return/raise/break/continue.",
                })
                break
            if isinstance(s, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                terminated = True

    class _Checker(ast.NodeVisitor):
        def __init__(self) -> None:
            self.scopes: list[set[str]] = [set(mod_scope)]
            self.ret_ann_stack: list[str | None] = []

        def _is_defined(self, name: str) -> bool:
            if has_star_import or name in _BUILTINS:
                return True
            return any(name in sc for sc in reversed(self.scopes))

        def visit_Module(self, node: ast.Module) -> None:
            _check_block_reachability(node.body)
            self.generic_visit(node)

        def _visit_fn(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
            # Visit decorators and defaults in outer scope
            for dec in node.decorator_list:
                self.visit(dec)
            for d in node.args.defaults:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    findings.append({
                        "file": rel_path,
                        "line": getattr(d, "lineno", node.lineno),
                        "code": "MUTABLE_DEFAULT_ARG",
                        "severity": "warning",
                        "message": f"Function '{node.name}' uses mutable literal default argument.",
                    })
                self.visit(d)
            for kd in node.args.kw_defaults:
                if kd is not None:
                    self.visit(kd)

            local: set[str] = {node.name}
            for a in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
                local.add(a.arg)
            if node.args.vararg:
                local.add(node.args.vararg.arg)
            if node.args.kwarg:
                local.add(node.args.kwarg.arg)
            for sub in ast.walk(node):
                if sub is node:
                    continue
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and sub in node.body:
                    local.add(sub.name)
                elif isinstance(sub, ast.Name) and isinstance(sub.ctx, (ast.Store, ast.Del)):
                    local.add(sub.id)
                elif isinstance(sub, ast.ExceptHandler) and sub.name:
                    local.add(sub.name)
                elif isinstance(sub, (ast.Import, ast.ImportFrom)):
                    for al in sub.names:
                        local.add(al.asname or al.name.split(".")[0])

            _check_block_reachability(node.body)
            ret_ann = ast.unparse(node.returns) if node.returns is not None else None
            self.scopes.append(local)
            self.ret_ann_stack.append(ret_ann)
            for stmt in node.body:
                self.visit(stmt)
            self.ret_ann_stack.pop()
            self.scopes.pop()

        visit_FunctionDef = _visit_fn
        visit_AsyncFunctionDef = _visit_fn

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            for b in node.bases:
                self.visit(b)
            cls_scope = {
                s.name for s in node.body
                if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            }
            for s in node.body:
                if isinstance(s, ast.Assign):
                    for t in s.targets:
                        _collect_bound_names(t, cls_scope)
            self.scopes.append(cls_scope)
            for s in node.body:
                self.visit(s)
            self.scopes.pop()

        def visit_Lambda(self, node: ast.Lambda) -> None:
            lscope = {a.arg for a in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)}
            if node.args.vararg:
                lscope.add(node.args.vararg.arg)
            if node.args.kwarg:
                lscope.add(node.args.kwarg.arg)
            self.scopes.append(lscope)
            self.visit(node.body)
            self.scopes.pop()

        def _visit_comp(self, generators: list[ast.comprehension], *exprs: ast.AST) -> None:
            cscope: set[str] = set()
            for gen in generators:
                self.visit(gen.iter)
                _collect_bound_names(gen.target, cscope)
                self.scopes.append(set(cscope))
                for cond in gen.ifs:
                    self.visit(cond)
                self.scopes.pop()
            self.scopes.append(cscope)
            for ex in exprs:
                self.visit(ex)
            self.scopes.pop()

        def visit_ListComp(self, node: ast.ListComp) -> None:
            self._visit_comp(node.generators, node.elt)

        def visit_SetComp(self, node: ast.SetComp) -> None:
            self._visit_comp(node.generators, node.elt)

        def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
            self._visit_comp(node.generators, node.elt)

        def visit_DictComp(self, node: ast.DictComp) -> None:
            self._visit_comp(node.generators, node.key, node.value)

        def visit_Name(self, node: ast.Name) -> None:
            if isinstance(node.ctx, ast.Load) and not self._is_defined(node.id):
                findings.append({
                    "file": rel_path,
                    "line": node.lineno,
                    "code": "UNDEFINED_NAME",
                    "severity": "error",
                    "message": f"Undefined name '{node.id}'.",
                })

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            if node.value is not None and isinstance(node.value, ast.Constant):
                ann = ast.unparse(node.annotation)
                if not _matches_prim_annotation(ann, node.value.value):
                    findings.append({
                        "file": rel_path,
                        "line": node.lineno,
                        "code": "ANNOTATION_LITERAL_MISMATCH",
                        "severity": "error",
                        "message": f"Literal {node.value.value!r} incompatible with annotation '{ann}'.",
                    })
            self.generic_visit(node)

        def visit_Return(self, node: ast.Return) -> None:
            if self.ret_ann_stack and self.ret_ann_stack[-1] is not None:
                ann = self.ret_ann_stack[-1]
                val = node.value.value if isinstance(node.value, ast.Constant) else (None if node.value is None else ...)
                if val is not ... and not _matches_prim_annotation(ann, val):
                    findings.append({
                        "file": rel_path,
                        "line": node.lineno,
                        "code": "RETURN_TYPE_MISMATCH",
                        "severity": "error",
                        "message": f"Return literal {val!r} incompatible with return annotation '{ann}'.",
                    })
            self.generic_visit(node)

        def visit_BinOp(self, node: ast.BinOp) -> None:
            if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and isinstance(node.right, ast.Constant):
                if node.right.value == 0 and not isinstance(node.right.value, bool):
                    findings.append({
                        "file": rel_path,
                        "line": node.lineno,
                        "code": "ZERO_DIVISION_LITERAL",
                        "severity": "error",
                        "message": "Division or modulo by literal zero.",
                    })
            if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
                lv, rv = node.left.value, node.right.value
                if isinstance(node.op, ast.Add) and (
                    (isinstance(lv, str) and not isinstance(rv, str))
                    or (not isinstance(lv, str) and isinstance(rv, str))
                ):
                    findings.append({
                        "file": rel_path,
                        "line": node.lineno,
                        "code": "INCOMPATIBLE_LITERAL_BINOP",
                        "severity": "error",
                        "message": f"Incompatible literal '+' operands: {type(lv).__name__} and {type(rv).__name__}.",
                    })
            self.generic_visit(node)

        def visit_Dict(self, node: ast.Dict) -> None:
            seen_keys: set[tuple[type, Any]] = set()
            for k in node.keys:
                if isinstance(k, ast.Constant):
                    sig = (type(k.value), k.value)
                    if sig in seen_keys:
                        findings.append({
                            "file": rel_path,
                            "line": getattr(k, "lineno", node.lineno),
                            "code": "DUPLICATE_DICT_KEY",
                            "severity": "warning",
                            "message": f"Duplicate dictionary literal key {k.value!r}.",
                        })
                    seen_keys.add(sig)
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            if isinstance(node.func, ast.Name):
                fname = node.func.id
                if fname in ("eval", "exec"):
                    findings.append({
                        "file": rel_path,
                        "line": node.lineno,
                        "code": "DANGEROUS_DYNAMIC_EXEC",
                        "severity": "warning",
                        "message": f"Dynamic code execution via '{fname}(...)' requires explicit security review.",
                    })
                sig = func_sigs.get(fname)
                has_star = any(isinstance(a, ast.Starred) for a in node.args)
                has_kwstar = any(kw.arg is None for kw in node.keywords)
                if sig is not None and not has_star and not has_kwstar:
                    npos = len(node.args)
                    kw_given = {kw.arg for kw in node.keywords if kw.arg is not None}
                    if sig["max_pos"] is not None and npos > sig["max_pos"]:
                        findings.append({
                            "file": rel_path,
                            "line": node.lineno,
                            "code": "CALL_ARITY_MISMATCH",
                            "severity": "error",
                            "message": f"Call to '{fname}' passes {npos} positional args; max is {sig['max_pos']}.",
                        })
                    elif npos + len(kw_given & sig["kw_names"]) < sig["min_pos"]:
                        findings.append({
                            "file": rel_path,
                            "line": node.lineno,
                            "code": "CALL_ARITY_MISMATCH",
                            "severity": "error",
                            "message": f"Call to '{fname}' passes too few arguments (min {sig['min_pos']}).",
                        })
                    if not sig["has_kwarg"]:
                        bad_kw = sorted(kw_given - sig["kw_names"])
                        if bad_kw:
                            findings.append({
                                "file": rel_path,
                                "line": node.lineno,
                                "code": "UNKNOWN_KEYWORD_ARG",
                                "severity": "error",
                                "message": f"Call to '{fname}' passes unexpected keyword arg(s): {bad_kw}.",
                            })
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    findings.append({
                        "file": rel_path,
                        "line": node.lineno,
                        "code": "SHELL_TRUE_EXECUTION",
                        "severity": "warning",
                        "message": "subprocess call with shell=True.",
                    })
            self.generic_visit(node)

    _Checker().visit(tree)
    findings.sort(key=lambda r: (r["file"], int(r["line"]), r["code"]))
    return findings


def analyze_python_static_soundness(
    repo: pathlib.Path,
    source_root: pathlib.Path | None = None,
    max_files: int = 100,
) -> dict[str, Any]:
    target = source_root if source_root is not None else repo
    py_files = [target] if target.is_file() else sorted(target.rglob("*.py"))[:max_files]
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    checked = 0
    for f in py_files:
        if not f.is_file():
            continue
        rel = str(f.relative_to(repo)).replace("\\", "/") if repo in f.resolve().parents else f.name
        checked += 1
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError as exc:
            errors.append({
                "file": rel,
                "line": exc.lineno or 1,
                "code": "SYNTAX_ERROR",
                "severity": "error",
                "message": str(exc.msg),
            })
            continue
        for item in analyze_python_module_ast(tree, rel):
            if item["severity"] == "error":
                errors.append(item)
            else:
                warnings.append(item)
    return {
        "files_checked": checked,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "sound": len(errors) == 0,
    }
