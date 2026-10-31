"""Shared active-registry loader and deterministic stdlib Python static/type/security/coverage analyzer.

Zero external binary dependencies, zero model cognition, <5ms per module for static passes.
Catches:
- UNDEFINED_NAME (lexical scope + closure + comprehension + module prepass) -> Ruff F821
- UNUSED_IMPORT -> Ruff F401, DUPLICATE_DICT_KEY -> Ruff F601, E711/E712/E501
- CALL_ARITY_MISMATCH & UNKNOWN_KEYWORD_ARG & GRADUAL_TYPE_SOUNDNESS -> mypy operator/return-value/assignment/arg-type/call-arg
- AST SECURITY & SECRET SCANNING -> Bandit B404/B602/B605/B307/B102/B301/B506/B324/B105-B107
- EXACT BYTECODE + sys.settrace STATEMENT COVERAGE & UNIVERSAL STDLIB TEST RUNNER (unittest + plain test_* functions/classes)
"""
from __future__ import annotations

import ast
import builtins
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import symtable
from typing import Any
from collections import deque

from canonical.runtime.root3_runtime_process_universe_v2 import _aliases, _qname

_BUILTINS = frozenset(dir(builtins)) | {
    "__file__", "__name__", "__doc__", "__package__", "__all__", "__annotations__", "__spec__", "__loader__",
}

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

_PY_OK_CACHE: dict[str, bool] = {}
_PYTEST_OK_CACHE: dict[str, bool] = {}

_SECRET_VAR_RE = re.compile(
    r"(?:^|_)(?:password|passwd|pwd|secret|api_key|apikey|access_token|auth_token|private_key)(?:$|_)",
    re.IGNORECASE,
)
_ISSUER_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("B105", re.compile(r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA)[0-9A-Z]{16}\b")),
    ("B105", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("B105", re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,}\b")),
    ("B105", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("B105", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
)


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


def python_interpreter_works(python_exe: str, timeout_s: int = 10) -> bool:
    """True iff ``python_exe`` is a working Python 3 interpreter (cached, 0ms on sys.executable)."""
    exe = str(python_exe or "")
    if not exe:
        return False
    try:
        key = os.path.realpath(exe)
        if key == os.path.realpath(sys.executable) and os.path.isfile(key):
            return True
    except OSError:
        key = exe
    cached = _PY_OK_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        proc = subprocess.run(
            [exe, "-c", "import sys; raise SystemExit(0 if sys.version_info[0] >= 3 else 1)"],
            capture_output=True,
            text=True,
            timeout=min(max(timeout_s, 1), 15),
        )
        ok = proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    _PY_OK_CACHE[key] = ok
    return ok


def has_pytest(python_exe: str, timeout_s: int = 10) -> bool:
    """True iff ``python_exe -m pytest`` is importable (cached, 0ms on sys.executable)."""
    exe = str(python_exe or "")
    if not python_interpreter_works(exe, timeout_s):
        return False
    try:
        key = os.path.realpath(exe)
        if key == os.path.realpath(sys.executable):
            cached = _PYTEST_OK_CACHE.get(key)
            if cached is None:
                cached = importlib.util.find_spec("pytest") is not None
                _PYTEST_OK_CACHE[key] = cached
            return cached
    except OSError:
        key = exe
    cached = _PYTEST_OK_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        proc = subprocess.run(
            [exe, "-c", "import pytest"],
            capture_output=True,
            text=True,
            timeout=min(max(timeout_s, 1), 15),
        )
        ok = proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        ok = False
    _PYTEST_OK_CACHE[key] = ok
    return ok


_STDLIB_TEST_HARNESS = r"""
import importlib.util, inspect, os, pathlib, sys, traceback, unittest

cwd = pathlib.Path.cwd().resolve()
if str(cwd) not in sys.path:
    sys.path.insert(0, str(cwd))
if (cwd / "src").is_dir() and str(cwd / "src") not in sys.path:
    sys.path.insert(0, str(cwd / "src"))

targets = list(sys.argv[1:])
sys.argv[:] = [sys.argv[0]]
files = []
if targets:
    for raw in targets:
        t = raw.split("::", 1)[0]
        p = (cwd / t).resolve()
        if p.is_file() and p.suffix == ".py":
            files.append(p)
        elif p.is_dir():
            for sub in sorted(p.rglob("*.py")):
                if "__pycache__" not in sub.parts and (sub.name.startswith("test_") or sub.name.endswith("_test.py")):
                    files.append(sub)
else:
    for sub in sorted(cwd.rglob("*.py")):
        if "__pycache__" not in sub.parts and ".git" not in sub.parts and (sub.name.startswith("test_") or sub.name.endswith("_test.py")):
            files.append(sub)

seen = set()
ordered = []
for f in files:
    if f not in seen:
        seen.add(f)
        ordered.append(f)

passed = 0
failed = 0
errors = []

for idx, path in enumerate(ordered):
    parent = str(path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    mod_name = f"_brain_test_mod_{idx}_{path.stem}"
    try:
        spec = importlib.util.spec_from_file_location(mod_name, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
    except BaseException:
        failed += 1
        errors.append(traceback.format_exc())
        continue

    suite = unittest.defaultTestLoader.loadTestsFromModule(mod)
    if suite.countTestCases() > 0:
        res = unittest.TestResult()
        suite.run(res)
        n_bad = len(res.failures) + len(res.errors)
        failed += n_bad
        passed += max(0, res.testsRun - n_bad)
        for _tc, tb in res.failures + res.errors:
            errors.append(tb)

    for name, obj in list(vars(mod).items()):
        if name.startswith("test_") and inspect.isfunction(obj):
            try:
                obj()
                passed += 1
            except unittest.SkipTest:
                pass
            except BaseException:
                failed += 1
                errors.append(traceback.format_exc())
        elif name.startswith("Test") and inspect.isclass(obj) and not issubclass(obj, unittest.TestCase):
            for mname, mobj in inspect.getmembers(obj, predicate=inspect.isfunction):
                if mname.startswith("test_"):
                    try:
                        inst = obj()
                        if hasattr(inst, "setup_method"):
                            inst.setup_method()
                        try:
                            getattr(inst, mname)()
                        finally:
                            if hasattr(inst, "teardown_method"):
                                inst.teardown_method()
                        passed += 1
                    except unittest.SkipTest:
                        pass
                    except BaseException:
                        failed += 1
                        errors.append(traceback.format_exc())

if errors:
    sys.stderr.write("\n".join(errors[-3:]) + "\n")
print(f"{passed} passed, {failed} failed")
if failed > 0:
    raise SystemExit(1)
if passed == 0:
    sys.stderr.write("no tests ran\n")
    raise SystemExit(5)
raise SystemExit(0)
"""


def universal_test_argv(python_exe: str, targets: list[str] | None = None) -> list[str]:
    """Return pytest argv if installed, else stdlib unittest+plain-test universal runner argv."""
    tlist = [str(x) for x in (targets or []) if str(x)]
    if has_pytest(python_exe):
        return [python_exe, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + tlist
    return [python_exe, "-B", "-c", _STDLIB_TEST_HARNESS] + tlist


def run_universal_tests(
    python_exe: str,
    cwd: pathlib.Path,
    targets: list[str] | None = None,
    timeout_s: int = 120,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    run_env = dict(os.environ if env is None else env)
    run_env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        universal_test_argv(python_exe, targets),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        env=run_env,
    )


_STDLIB_COVERAGE_HARNESS = r"""
import dis, importlib.util, inspect, json, os, pathlib, sys, traceback, types, unittest

cwd = pathlib.Path.cwd().resolve()
out_json = pathlib.Path(sys.argv[1]).resolve()
targets = list(sys.argv[2:])
sys.argv[:] = [sys.argv[0]]

if str(cwd) not in sys.path:
    sys.path.insert(0, str(cwd))
if (cwd / "src").is_dir() and str(cwd / "src") not in sys.path:
    sys.path.insert(0, str(cwd / "src"))

if targets:
    test_files = []
    for raw in targets:
        p = (cwd / raw).resolve()
        if p.is_file() and p.suffix == ".py":
            test_files.append(p)
else:
    test_files = [
        p for p in sorted(cwd.rglob("*.py"))
        if "__pycache__" not in p.parts and ".git" not in p.parts
        and (p.name.startswith("test_") or p.name.endswith("_test.py"))
    ]

traced: dict[str, set[int]] = {}
cwd_prefix = str(cwd) + os.sep

def _tracer(frame, event, arg):
    if event == "line":
        fn = frame.f_code.co_filename
        if fn:
            try:
                rp = os.path.realpath(fn)
            except OSError:
                rp = fn
            if rp.startswith(cwd_prefix):
                s = traced.get(rp)
                if s is None:
                    s = set()
                    traced[rp] = s
                s.add(frame.f_lineno)
    return _tracer

passed = 0
failed = 0
errors = []

sys.settrace(_tracer)
try:
    for idx, path in enumerate(test_files):
        parent = str(path.parent)
        if parent not in sys.path:
            sys.path.insert(0, parent)
        mod_name = f"_brain_cov_mod_{idx}_{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(mod_name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
        except BaseException:
            failed += 1
            errors.append(traceback.format_exc())
            continue

        suite = unittest.defaultTestLoader.loadTestsFromModule(mod)
        if suite.countTestCases() > 0:
            res = unittest.TestResult()
            suite.run(res)
            n_bad = len(res.failures) + len(res.errors)
            failed += n_bad
            passed += max(0, res.testsRun - n_bad)
            for _tc, tb in res.failures + res.errors:
                errors.append(tb)

        for name, obj in list(vars(mod).items()):
            if name.startswith("test_") and inspect.isfunction(obj):
                try:
                    obj()
                    passed += 1
                except unittest.SkipTest:
                    pass
                except BaseException:
                    failed += 1
                    errors.append(traceback.format_exc())
            elif name.startswith("Test") and inspect.isclass(obj) and not issubclass(obj, unittest.TestCase):
                for mname, mobj in inspect.getmembers(obj, predicate=inspect.isfunction):
                    if mname.startswith("test_"):
                        try:
                            inst = obj()
                            getattr(inst, mname)()
                            passed += 1
                        except unittest.SkipTest:
                            pass
                        except BaseException:
                            failed += 1
                            errors.append(traceback.format_exc())
finally:
    sys.settrace(None)

def _executable_lines(py_path: pathlib.Path) -> set[int]:
    src = py_path.read_text(encoding="utf-8", errors="replace")
    code_obj = compile(src, str(py_path), "exec")
    lines: set[int] = set()
    stack = [code_obj]
    while stack:
        co = stack.pop()
        for _off, ln in dis.findlinestarts(co):
            if ln is not None and ln >= 1:
                lines.add(int(ln))
        for c in co.co_consts:
            if isinstance(c, types.CodeType):
                stack.append(c)
    return lines

files_doc = {}
for rp, exec_set in sorted(traced.items()):
    if not exec_set:
        continue
    p = pathlib.Path(rp)
    if not p.is_file() or p.suffix != ".py":
        continue
    rel = p.relative_to(cwd).as_posix()
    try:
        all_exec = _executable_lines(p)
    except SyntaxError:
        continue
    executed = sorted(all_exec & exec_set)
    missing = sorted(all_exec - exec_set)
    files_doc[rel] = {
        "executed_lines": executed,
        "missing_lines": missing,
    }

out_json.write_text(json.dumps({"files": files_doc, "passed": passed, "failed": failed}, sort_keys=True), encoding="utf-8")
if errors:
    sys.stderr.write("\n".join(errors[-3:]) + "\n")
if failed > 0 or passed == 0:
    raise SystemExit(1)
raise SystemExit(0)
"""


def measure_coverage_stdlib(
    python_exe: str,
    scratch: pathlib.Path,
    out_json: pathlib.Path,
    timeout_s: int = 120,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run discovered tests under sys.settrace + dis.findlinestarts and emit coverage.py-compatible JSON."""
    run_env = dict(os.environ if env is None else env)
    run_env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [python_exe, "-B", "-c", _STDLIB_COVERAGE_HARNESS, str(out_json)],
        cwd=str(scratch),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        env=run_env,
    )


def _matches_prim_annotation(ann_str: str, val: Any) -> bool | None:
    """Match supported literal annotations without executing annotation code.

    None means unknown, NOT valid. Union alternatives use three-valued OR so
    an unsupported alias cannot become either a false rejection or a proof.
    """
    try:
        annotation = ast.parse(ann_str.strip(), mode="eval").body
    except (SyntaxError, ValueError):
        return None

    def name(node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in {"typing", "typing_extensions", "builtins"}:
                return node.attr
        return ""

    def union(results: list[bool | None]) -> bool | None:
        if any(result is True for result in results):
            return True
        return None if any(result is None for result in results) else False

    def match(node: ast.AST, depth: int = 0) -> bool | None:
        if depth > 16:
            return None
        if isinstance(node, ast.Constant):
            if node.value is None:
                return val is None
            if isinstance(node.value, str):
                try:
                    return match(ast.parse(node.value, mode="eval").body, depth + 1)
                except (SyntaxError, ValueError):
                    return None
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return union([match(node.left, depth + 1), match(node.right, depth + 1)])
        kind = name(node)
        if kind == "Any":
            return True
        if isinstance(node, ast.Subscript):
            kind = name(node.value)
            parts = list(node.slice.elts) if isinstance(node.slice, ast.Tuple) else [node.slice]
            if kind == "Optional" and len(parts) == 1:
                return True if val is None else match(parts[0], depth + 1)
            if kind == "Union":
                return union([match(part, depth + 1) for part in parts])
            if kind == "Annotated" and parts:
                return match(parts[0], depth + 1)
            if kind == "Literal":
                try:
                    literals = [ast.literal_eval(part) for part in parts]
                except (ValueError, TypeError, SyntaxError):
                    return None
                return any(type(val) is type(literal) and val == literal for literal in literals)
            allowed = _PRIM_MAP.get(kind)
            return False if allowed is not None and not isinstance(val, allowed) else None
        allowed = _PRIM_MAP.get(kind)
        if allowed is None:
            return None
        if kind in {"int", "float"} and isinstance(val, bool):
            return False
        return isinstance(val, allowed)

    return match(annotation)


def _sig_spec(fn: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool = False) -> dict[str, Any]:
    pos = [a.arg for a in fn.args.posonlyargs] + [a.arg for a in fn.args.args]
    pos_anns = [ast.unparse(a.annotation) if a.annotation else None for a in (*fn.args.posonlyargs, *fn.args.args)]
    if is_method and pos and pos[0] in ("self", "cls"):
        pos = pos[1:]
        pos_anns = pos_anns[1:]
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
        "pos_anns": pos_anns,
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
                compatible = _matches_prim_annotation(ann, node.value.value)
                if compatible is None:
                    findings.append({"file": rel_path, "line": node.lineno,
                                     "code": "ANNOTATION_NOT_CHECKED", "severity": "warning",
                                     "message": f"Literal annotation '{ann}' is outside supported checks."})
                if compatible is False:
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
                compatible = _matches_prim_annotation(ann, val) if val is not ... else True
                if compatible is None:
                    findings.append({"file": rel_path, "line": node.lineno,
                                     "code": "ANNOTATION_NOT_CHECKED", "severity": "warning",
                                     "message": f"Return annotation '{ann}' is outside supported checks."})
                if compatible is False:
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


def lint_python_source(text: str, rel_path: str) -> list[dict[str, Any]]:
    """Deterministic Ruff-equivalent F/E/W lint pass over a parsed Python module."""
    tree = ast.parse(text, filename=rel_path)
    rows: list[dict[str, Any]] = []
    for item in analyze_python_module_ast(tree, rel_path):
        if item["code"] == "UNDEFINED_NAME":
            rows.append({
                "file": rel_path,
                "line": int(item["line"]),
                "code": "F821",
                "message": item["message"],
            })
        elif item["code"] == "DUPLICATE_DICT_KEY":
            rows.append({
                "file": rel_path,
                "line": int(item["line"]),
                "code": "F601",
                "message": item["message"],
            })

    # Unused imports (F401) outside __init__.py unless exported in __all__
    if not rel_path.endswith("__init__.py"):
        loaded_names = {
            sub.id for sub in ast.walk(tree)
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load)
        }
        exported_all: set[str] = set()
        for st in tree.body:
            if isinstance(st, ast.Assign):
                for t in st.targets:
                    if isinstance(t, ast.Name) and t.id == "__all__" and isinstance(st.value, (ast.List, ast.Tuple)):
                        for elt in st.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                exported_all.add(elt.value)
        for st in tree.body:
            if isinstance(st, (ast.Import, ast.ImportFrom)):
                if isinstance(st, ast.ImportFrom) and st.module == "__future__":
                    continue
                for alias in st.names:
                    if alias.name == "*":
                        continue
                    bound = alias.asname or alias.name.split(".")[0]
                    if bound not in loaded_names and bound not in exported_all and not bound.startswith("_"):
                        rows.append({
                            "file": rel_path,
                            "line": int(st.lineno),
                            "code": "F401",
                            "message": f"'{alias.name}' imported but unused",
                        })

    for idx, raw_line in enumerate(text.splitlines(), 1):
        if len(raw_line) > 100:
            rows.append({
                "file": rel_path,
                "line": idx,
                "code": "E501",
                "message": f"Line too long ({len(raw_line)} > 100)",
            })

    rows.sort(key=lambda r: (r["file"], int(r["line"]), r["code"]))
    return rows


def _norm_base_type(ann_str: str | None) -> str | None:
    if not ann_str:
        return None
    s = ann_str.strip()
    if "|" in s or s.startswith(("Optional[", "Union[", "Any")):
        return None
    base = s.split("[", 1)[0].strip().split(".")[-1]
    if base in ("int", "float", "str", "bytes", "bool", "list", "dict", "set", "tuple", "None"):
        return base
    return None


def _compatible_types(expected: str | None, actual: str | None) -> bool:
    if expected is None or actual is None:
        return True
    if expected == actual:
        return True
    if expected == "float" and actual == "int":
        return True
    return False


def typecheck_python_source(text: str, rel_path: str) -> list[dict[str, Any]]:
    """Bidirectional AST gradual type checker emitting mypy-compatible error/note rows."""
    tree = ast.parse(text, filename=rel_path)
    rows: list[dict[str, Any]] = []
    func_sigs: dict[str, dict[str, Any]] = {}
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_sigs[stmt.name] = _sig_spec(stmt, is_method=False)

    def _infer_expr(expr: ast.AST, env: dict[str, str]) -> str | None:
        if isinstance(expr, ast.Constant):
            v = expr.value
            if v is None:
                return "None"
            if isinstance(v, bool):
                return "bool"
            if isinstance(v, int):
                return "int"
            if isinstance(v, float):
                return "float"
            if isinstance(v, str):
                return "str"
            if isinstance(v, bytes):
                return "bytes"
            return None
        if isinstance(expr, ast.Name):
            return env.get(expr.id)
        if isinstance(expr, ast.List):
            return "list"
        if isinstance(expr, ast.Dict):
            return "dict"
        if isinstance(expr, ast.Set):
            return "set"
        if isinstance(expr, ast.Tuple):
            return "tuple"
        if isinstance(expr, ast.UnaryOp):
            inner = _infer_expr(expr.operand, env)
            if isinstance(expr.op, ast.Not):
                return "bool"
            return inner
        if isinstance(expr, ast.Compare) or isinstance(expr.op if isinstance(expr, ast.BoolOp) else None, (ast.And, ast.Or)):
            if isinstance(expr, ast.Compare):
                return "bool"
        if isinstance(expr, ast.BinOp):
            lt = _infer_expr(expr.left, env)
            rt = _infer_expr(expr.right, env)
            if lt is not None and rt is not None:
                lb = _norm_base_type(lt)
                rb = _norm_base_type(rt)
                if lb is not None and rb is not None:
                    if isinstance(expr.op, ast.Add):
                        if (lb == "str") != (rb == "str") or (lb == "bytes") != (rb == "bytes"):
                            rows.append({
                                "file": rel_path,
                                "line": int(expr.lineno),
                                "code": "operator",
                                "severity": "error",
                                "message": f"Unsupported operand types for + (\"{lb}\" and \"{rb}\")",
                            })
                            return None
                        if lb == "str" and rb == "str":
                            return "str"
                        if lb in ("int", "float", "bool") and rb in ("int", "float", "bool"):
                            return "float" if "float" in (lb, rb) else "int"
                    elif isinstance(expr.op, (ast.Sub, ast.Div, ast.FloorDiv)):
                        if lb in ("str", "bytes", "list", "dict", "tuple") or rb in ("str", "bytes", "list", "dict", "tuple"):
                            rows.append({
                                "file": rel_path,
                                "line": int(expr.lineno),
                                "code": "operator",
                                "severity": "error",
                                "message": f"Unsupported operand types for arithmetic (\"{lb}\" and \"{rb}\")",
                            })
                            return None
                        if isinstance(expr.op, ast.Div):
                            return "float"
                        return "float" if "float" in (lb, rb) else "int"
                    elif isinstance(expr.op, ast.Mult):
                        if lb in ("int", "float") and rb in ("int", "float"):
                            return "float" if "float" in (lb, rb) else "int"
                        if (lb == "str" and rb == "int") or (lb == "int" and rb == "str"):
                            return "str"
                        if lb == "str" and rb == "str":
                            rows.append({
                                "file": rel_path,
                                "line": int(expr.lineno),
                                "code": "operator",
                                "severity": "error",
                                "message": "can't multiply sequence by non-int of type \"str\"",
                            })
                            return None
            return None
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name):
            fname = expr.func.id
            for a in expr.args:
                _infer_expr(a, env)
            for kw in expr.keywords:
                _infer_expr(kw.value, env)
            if fname == "len":
                return "int"
            if fname == "str":
                return "str"
            if fname == "int":
                return "int"
            if fname == "float":
                return "float"
            if fname == "bool":
                return "bool"
            if fname == "sum" and expr.args:
                at = env.get(expr.args[0].id) if isinstance(expr.args[0], ast.Name) else None
                if at and "float" in at:
                    return "float"
                if at and "int" in at:
                    return "int"
            sig = func_sigs.get(fname)
            if sig is not None:
                has_star = any(isinstance(a, ast.Starred) for a in expr.args)
                has_kwstar = any(kw.arg is None for kw in expr.keywords)
                if not has_star and not has_kwstar:
                    npos = len(expr.args)
                    kw_given = {kw.arg for kw in expr.keywords if kw.arg is not None}
                    if (sig["max_pos"] is not None and npos > sig["max_pos"]) or (npos + len(kw_given & sig["kw_names"]) < sig["min_pos"]):
                        rows.append({
                            "file": rel_path,
                            "line": int(expr.lineno),
                            "code": "call-arg",
                            "severity": "error",
                            "message": f"Wrong argument count in call to \"{fname}\"",
                        })
                    for idx, arg_node in enumerate(expr.args):
                        if idx < len(sig["pos_anns"]) and sig["pos_anns"][idx]:
                            exp_b = _norm_base_type(sig["pos_anns"][idx])
                            act_b = _norm_base_type(_infer_expr(arg_node, env))
                            if not _compatible_types(exp_b, act_b):
                                rows.append({
                                    "file": rel_path,
                                    "line": int(expr.lineno),
                                    "code": "arg-type",
                                    "severity": "error",
                                    "message": f"Argument {idx + 1} to \"{fname}\" has incompatible type \"{act_b}\"; expected \"{exp_b}\"",
                                })
                return sig["ret_ann"]
        return None

    def _check_stmts(stmts: list[ast.stmt], env: dict[str, str], ret_ann: str | None) -> None:
        for st in stmts:
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fn_env = dict(env)
                for a in (*st.args.posonlyargs, *st.args.args, *st.args.kwonlyargs):
                    if a.annotation is not None:
                        fn_env[a.arg] = ast.unparse(a.annotation)
                fn_ret = ast.unparse(st.returns) if st.returns is not None else None
                _check_stmts(st.body, fn_env, fn_ret)
            elif isinstance(st, ast.ClassDef):
                _check_stmts(st.body, dict(env), None)
            elif isinstance(st, ast.AnnAssign):
                ann_str = ast.unparse(st.annotation)
                exp_b = _norm_base_type(ann_str)
                if st.value is not None:
                    act_t = _infer_expr(st.value, env)
                    act_b = _norm_base_type(act_t)
                    if isinstance(st.value, ast.Constant):
                        comp = _matches_prim_annotation(ann_str, st.value.value)
                        if comp is False:
                            rows.append({
                                "file": rel_path,
                                "line": int(st.lineno),
                                "code": "assignment",
                                "severity": "error",
                                "message": f"Incompatible types in assignment (expression has type \"{type(st.value.value).__name__}\", variable has type \"{ann_str}\")",
                            })
                    elif not _compatible_types(exp_b, act_b):
                        rows.append({
                            "file": rel_path,
                            "line": int(st.lineno),
                            "code": "assignment",
                            "severity": "error",
                            "message": f"Incompatible types in assignment (expression has type \"{act_b}\", variable has type \"{ann_str}\")",
                        })
                if isinstance(st.target, ast.Name):
                    env[st.target.id] = ann_str
            elif isinstance(st, ast.Assign):
                val_t = _infer_expr(st.value, env)
                if len(st.targets) == 1 and isinstance(st.targets[0], ast.Name) and val_t:
                    env[st.targets[0].id] = val_t
            elif isinstance(st, ast.Return):
                act_t = _infer_expr(st.value, env) if st.value is not None else "None"
                if ret_ann is not None:
                    if st.value is not None and isinstance(st.value, ast.Constant):
                        comp = _matches_prim_annotation(ret_ann, st.value.value)
                        if comp is False:
                            rows.append({
                                "file": rel_path,
                                "line": int(st.lineno),
                                "code": "return-value",
                                "severity": "error",
                                "message": f"Incompatible return value type (got \"{type(st.value.value).__name__}\", expected \"{ret_ann}\")",
                            })
                    else:
                        exp_b = _norm_base_type(ret_ann)
                        act_b = _norm_base_type(act_t)
                        if not _compatible_types(exp_b, act_b):
                            rows.append({
                                "file": rel_path,
                                "line": int(st.lineno),
                                "code": "return-value",
                                "severity": "error",
                                "message": f"Incompatible return value type (got \"{act_b}\", expected \"{ret_ann}\")",
                            })
            elif isinstance(st, ast.Expr):
                _infer_expr(st.value, env)
            elif isinstance(st, (ast.If, ast.For, ast.AsyncFor, ast.While)):
                if hasattr(st, "test"):
                    _infer_expr(st.test, env)
                if hasattr(st, "iter"):
                    _infer_expr(st.iter, env)
                _check_stmts(st.body, dict(env), ret_ann)
                if st.orelse:
                    _check_stmts(st.orelse, dict(env), ret_ann)
            elif isinstance(st, (ast.With, ast.AsyncWith)):
                _check_stmts(st.body, dict(env), ret_ann)
            elif isinstance(st, ast.Try):
                _check_stmts(st.body, dict(env), ret_ann)
                for h in st.handlers:
                    _check_stmts(h.body, dict(env), ret_ann)
                if st.orelse:
                    _check_stmts(st.orelse, dict(env), ret_ann)
                if st.finalbody:
                    _check_stmts(st.finalbody, dict(env), ret_ann)

    _check_stmts(tree.body, {}, None)
    # Also surface undefined names as mypy name-defined errors
    for item in analyze_python_module_ast(tree, rel_path):
        if item["code"] == "UNDEFINED_NAME":
            rows.append({
                "file": rel_path,
                "line": int(item["line"]),
                "code": "name-defined",
                "severity": "error",
                "message": item["message"],
            })

    dedup: dict[tuple[str, int, str], dict[str, Any]] = {}
    for r in rows:
        dedup.setdefault((r["file"], int(r["line"]), r["code"]), r)
    return sorted(dedup.values(), key=lambda r: (r["file"], int(r["line"]), r["code"]))


def _security_import_names(tree: ast.Module, text: str, filename: str) -> dict[ast.Name, str | None]:
    """Qualify stable module imports only; retain legacy spelling heuristics elsewhere.

    CPython decides lexical scope. We do not infer dynamic imports, arbitrary
    assignments or function-local import values, and never execute subject code.
    """
    direct = [node for node in tree.body if isinstance(node, ast.Import) or
              isinstance(node, ast.ImportFrom) and node.level == 0]
    aliases = _aliases(ast.Module(body=direct, type_ignores=[]))
    roots = {"os", "pickle", "cPickle", "dill", "marshal", "yaml", "hashlib", "builtins"}
    # Identity mappings already work through the legacy direct-spelling rules.
    # Avoid another parse and scope walk for ordinary, unaliased module imports.
    aliases = {name: target for name, target in aliases.items()
               if name != target and target.split(".")[0] in roots}
    if not aliases:
        return {}
    try:
        module = symtable.symtable(text, filename, "exec")
    except SyntaxError:
        return {}  # Preserve the existing AST-only checks on incomplete programs.

    # A conditional/relative import or star import must not silently replace a
    # top-level binding. Do not collect imports from unrelated function scopes.
    bindings: dict[str, set[str]] = {}
    wildcard = False

    class Imports(ast.NodeVisitor):
        def visit_Import(self, node):
            self.record(node)

        def visit_ImportFrom(self, node):
            nonlocal wildcard
            if any(alias.name == "*" for alias in node.names):
                wildcard = True
            self.record(node)

        def record(self, node):
            for name, target in _aliases(ast.Module(body=[node], type_ignores=[])).items():
                if isinstance(node, ast.ImportFrom) and node.level:
                    target = "." * node.level + target
                bindings.setdefault(name, set()).add(target)

        def visit_FunctionDef(self, node):
            pass

        visit_AsyncFunctionDef = visit_FunctionDef
        visit_ClassDef = visit_FunctionDef
        visit_Lambda = visit_FunctionDef

    Imports().visit(tree)
    global_writes = set()
    pending = list(module.get_children())
    while pending:
        child = pending.pop()
        pending.extend(child.get_children())
        global_writes.update(symbol.get_name() for symbol in child.get_symbols()
                             if symbol.is_global() and (symbol.is_assigned() or symbol.is_imported()))
    stable = {name: target for name, target in aliases.items()
              if not wildcard and len(bindings.get(name, ())) == 1
              and not module.lookup(name).is_assigned() and name not in global_writes}
    if not stable:
        return {}
    resolved: dict[ast.Name, str | None] = {}

    class Names(ast.NodeVisitor):
        def __init__(self):
            self.table = module
            self.children = {}

        def enter(self, node, name, body):
            parent = self.table
            if parent is None:
                child = None
            else:
                parent_id = parent.get_id()
                if parent_id not in self.children:
                    index = {}
                    for item in parent.get_children():
                        index.setdefault((item.get_name(), item.get_lineno()), deque()).append(item)
                    self.children[parent_id] = index
                matches = self.children[parent_id].get((name, node.lineno))
                child = matches.popleft() if matches else None
            self.table = child
            for item in body:
                self.visit(item)
            self.table = parent

        def visit_Name(self, node):
            if not isinstance(node.ctx, ast.Load) or node.id not in stable:
                return
            if self.table is None:
                resolved[node] = None
                return
            # Class bodies use LOAD_NAME and can fall back to globals before
            # class assignment. Leave their legacy heuristic unchanged.
            if self.table.get_type() == "class":
                return
            try:
                symbol = self.table.lookup(node.id)
            except KeyError:
                resolved[node] = None
                return
            resolved[node] = stable[node.id] if symbol.is_global() else None

        def visit_FunctionDef(self, node):
            for expression in node.args.defaults + node.args.kw_defaults:
                if expression is not None:
                    self.visit(expression)
            for arg in (*node.args.posonlyargs, *node.args.args, node.args.vararg,
                        node.args.kwarg, *node.args.kwonlyargs):
                if arg is not None and arg.annotation is not None:
                    self.visit(arg.annotation)
            if node.returns is not None:
                self.visit(node.returns)
            for expression in node.decorator_list:
                self.visit(expression)
            self.enter(node, node.name, node.body)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, node):
            for expression in node.args.defaults + node.args.kw_defaults:
                if expression is not None:
                    self.visit(expression)
            self.enter(node, "lambda", [node.body])

        def visit_ClassDef(self, node):
            for expression in node.bases + [kw.value for kw in node.keywords] + node.decorator_list:
                self.visit(expression)
            self.enter(node, node.name, node.body)

        def comprehension(self, node, name, values):
            self.visit(node.generators[0].iter)  # evaluated in the enclosing scope
            body = [node.generators[0].target, *node.generators[0].ifs]
            for generator in node.generators[1:]:
                body.extend([generator.iter, generator.target, *generator.ifs])
            self.enter(node, name, [*body, *values])

        def visit_ListComp(self, node):
            self.comprehension(node, "listcomp", [node.elt])

        def visit_SetComp(self, node):
            self.comprehension(node, "setcomp", [node.elt])

        def visit_DictComp(self, node):
            # CPython's symbol-table pass visits the value before the key,
            # unlike execution order. Same-line lambdas must match that order.
            self.comprehension(node, "dictcomp", [node.value, node.key])

        def visit_GeneratorExp(self, node):
            self.comprehension(node, "genexpr", [node.elt])

    Names().visit(tree)
    return resolved


def _security_qualified_name(node: ast.AST, names: dict[ast.Name, str | None]) -> str | None:
    root = node
    while isinstance(root, ast.Attribute):
        root = root.value
    if isinstance(root, ast.Name):
        target = names.get(root)
        if target is not None:
            return _qname(node, {root.id: target})
    return _qname(node, {})  # Do not remove legacy direct-spelling checks.


def security_scan_python_source(text: str, rel_path: str) -> list[dict[str, Any]]:
    """Bounded AST security patterns and secret signatures, not Bandit equivalence."""
    tree = ast.parse(text, filename=rel_path)
    names = _security_import_names(tree, text, rel_path)
    rows: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        # B404: import subprocess
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess" or alias.name.startswith("subprocess."):
                    rows.append({
                        "file": rel_path,
                        "line": int(node.lineno),
                        "test_id": "B404",
                        "severity": "LOW",
                        "confidence": "HIGH",
                        "message": "Consider possible security implications associated with the subprocess module.",
                    })
        elif isinstance(node, ast.ImportFrom) and (node.module == "subprocess" or (node.module or "").startswith("subprocess.")):
            rows.append({
                "file": rel_path,
                "line": int(node.lineno),
                "test_id": "B404",
                "severity": "LOW",
                "confidence": "HIGH",
                "message": "Consider possible security implications associated with the subprocess module.",
            })
        # Calls: B602, B605, B307, B102, B301, B506, B324, B106
        elif isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    rows.append({
                        "file": rel_path,
                        "line": int(node.lineno),
                        "test_id": "B602",
                        "severity": "HIGH",
                        "confidence": "HIGH",
                        "message": "subprocess call with shell=True identified, security issue.",
                    })
                elif kw.arg and _SECRET_VAR_RE.search(kw.arg) and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str) and kw.value.value:
                    rows.append({
                        "file": rel_path,
                        "line": int(node.lineno),
                        "test_id": "B106",
                        "severity": "LOW",
                        "confidence": "MEDIUM",
                        "message": f"Possible hardcoded password passed to argument '{kw.arg}'.",
                    })
            qualified = _security_qualified_name(node.func, names)
            mod_n, _, attr_n = (qualified or "").rpartition(".")
            rule = None
            if qualified in {"eval", "builtins.eval"}:
                rule = ("B307", "MEDIUM", "Use of possibly insecure function eval() - consider ast.literal_eval.")
            elif qualified in {"exec", "builtins.exec"}:
                rule = ("B102", "MEDIUM", "Use of exec detected.")
            elif mod_n == "os" and attr_n in {"system", "popen"}:
                rule = ("B605", "HIGH", f"Starting a process with a shell via os.{attr_n}.")
            elif mod_n in {"pickle", "cPickle", "dill", "marshal"} and attr_n in {"load", "loads"}:
                rule = ("B301", "MEDIUM", f"Pickle deserialization via {mod_n}.{attr_n} can be unsafe.")
            elif mod_n == "yaml" and attr_n == "load":
                safe = any(kw.arg == "Loader" and _security_qualified_name(kw.value, names)
                           in {"yaml.SafeLoader", "yaml.CSafeLoader"} for kw in node.keywords)
                if not safe:
                    rule = ("B506", "MEDIUM", "Use of unsafe yaml.load without SafeLoader.")
            elif mod_n == "hashlib" and attr_n in {"md5", "sha1"}:
                exempt = any(kw.arg == "usedforsecurity" and isinstance(kw.value, ast.Constant)
                             and kw.value.value is False for kw in node.keywords)
                if not exempt:
                    rule = ("B324", "HIGH", f"Use of weak cryptographic hash {attr_n}.")
            if rule is not None:
                code, severity, message = rule
                rows.append({"file": rel_path, "line": int(node.lineno), "test_id": code,
                             "severity": severity, "confidence": "HIGH", "message": message})
        # B105: hardcoded password/secret assignment
        elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and node.value.value:
            for t in node.targets:
                vname = t.id if isinstance(t, ast.Name) else (t.attr if isinstance(t, ast.Attribute) else "")
                if vname and _SECRET_VAR_RE.search(vname):
                    rows.append({
                        "file": rel_path,
                        "line": int(node.lineno),
                        "test_id": "B105",
                        "severity": "LOW",
                        "confidence": "MEDIUM",
                        "message": f"Possible hardcoded password assigned to '{vname}'.",
                    })
        elif isinstance(node, ast.AnnAssign) and node.value is not None and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and node.value.value:
            vname = node.target.id if isinstance(node.target, ast.Name) else ""
            if vname and _SECRET_VAR_RE.search(vname):
                rows.append({
                    "file": rel_path,
                    "line": int(node.lineno),
                    "test_id": "B105",
                    "severity": "LOW",
                    "confidence": "MEDIUM",
                    "message": f"Possible hardcoded password assigned to '{vname}'.",
                })
        # B107: hardcoded password default argument
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            pos_args = list(node.args.posonlyargs) + list(node.args.args)
            n_def = len(node.args.defaults)
            for arg_node, def_node in zip(pos_args[len(pos_args) - n_def:], node.args.defaults):
                if _SECRET_VAR_RE.search(arg_node.arg) and isinstance(def_node, ast.Constant) and isinstance(def_node.value, str) and def_node.value:
                    rows.append({
                        "file": rel_path,
                        "line": int(getattr(def_node, "lineno", node.lineno)),
                        "test_id": "B107",
                        "severity": "LOW",
                        "confidence": "MEDIUM",
                        "message": f"Possible hardcoded password default for '{arg_node.arg}'.",
                    })

    for lineno, line in enumerate(text.splitlines(), 1):
        for tid, pat in _ISSUER_SECRET_PATTERNS:
            if pat.search(line):
                rows.append({
                    "file": rel_path,
                    "line": lineno,
                    "test_id": tid,
                    "severity": "HIGH",
                    "confidence": "HIGH",
                    "message": "Hardcoded credential token signature detected.",
                })
                break

    dedup: dict[tuple[str, int, str], dict[str, Any]] = {}
    for r in rows:
        dedup.setdefault((r["file"], int(r["line"]), r["test_id"]), r)
    return sorted(dedup.values(), key=lambda r: (r["file"], int(r["line"]), r["test_id"]))


def analyze_python_static_soundness(
    repo: pathlib.Path,
    source_root: pathlib.Path | None = None,
    max_files: int = 100,
) -> dict[str, Any]:
    target = source_root if source_root is not None else repo
    discovered = [target] if target.is_file() else sorted(target.rglob("*.py"))
    py_files = discovered[:max(0, max_files)]
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
    complete = checked > 0 and len(discovered) == checked
    annotations_complete = not any(item["code"] == "ANNOTATION_NOT_CHECKED" for item in warnings)
    return {
        "verification_scope": "BOUNDED_PYTHON_AST_CHECKS",
        "semantic_correctness_verified": False,
        "analysis_complete": complete,
        "annotation_checks_complete": annotations_complete,
        "files_discovered": len(discovered),
        "files_omitted": len(discovered) - checked,
        "files_checked": checked,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "sound": len(errors) == 0 and complete and annotations_complete,
    }
