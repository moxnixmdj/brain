#!/usr/bin/env python3
"""White-Box Repo/Library Introspector, Live Runtime Trace Synthesizer & Semantic Web Compiler.

Eliminates blind black-box trial-and-error across unfamiliar codebases, failing SWE suites,
and web interfaces with zero model calls ($0, K3 = 0):

1. **Live Runtime Assertion & Call-Frame Synthesizer (`synthesize_repair_from_live_tests`)**:
   Captures concrete `(args -> expected)` obligations from both static test ASTs and live
   runtime test execution (recording real call arguments and evaluated `expected` values even
   when tests build inputs dynamically in `setUp`/loops/helpers), then delegates to
   `swe_observational_program_synthesizer_v1.synthesize_python_function_body` (Bottom-Up
   Observational Equivalence + STUN conditional unification) + local helper composition.

2. **Zero-Network Local Package / Module White-Box Introspector (`introspect_python_surface`)**:
   Reads AST signatures, type annotations, docstrings, and runnable doctest snippets of any
   local directory or importable Python module in milliseconds — generalizing
   `documentation_mining_v1` beyond CPython's 305 stdlib RST files with zero network calls.

3. **Semantic HTML/DOM Form -> Direct HTTP Compiler (`discover_and_execute_semantic_web_form`)**:
   Reads `<form action method>` and semantic `<input name aria-label placeholder>` schemas
   from a web page, binds goal parameters to semantic form fields (including hidden tokens),
   executes the direct HTTP request in <15 ms, and returns a causal trace ready for
   `causal_trace_to_skill_compiler_v1` permanent elevation.
"""
from __future__ import annotations

import ast
import html.parser
import importlib.util
import inspect
import pathlib
import re
import sys
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import swe_observational_program_synthesizer_v1 as obs_synth

SCHEMA = "PROJECT_BRAIN_WHITEBOX_INTROSPECTOR_AND_TRACE_SYNTHESIZER_V1"

_WORD_RE = re.compile(r"[a-z0-9_]+")
_STOP = frozenset({
    "a", "an", "the", "to", "into", "from", "in", "on", "at", "by", "for", "of",
    "with", "and", "or", "is", "are", "be", "use", "using", "call", "run", "please",
})


# --------------------------------------------------------------------------- #
# 1. White-Box Local Repo & Installed Module Introspection
# --------------------------------------------------------------------------- #
def introspect_python_surface(target: str | pathlib.Path) -> dict[str, Any]:
    """Extract typed callable & class schemas from any local `.py` file or package directory."""
    root = pathlib.Path(target).resolve()
    py_files: list[pathlib.Path] = []
    if root.is_file() and root.suffix == ".py":
        py_files = [root]
        base_dir = root.parent
    elif root.is_dir():
        base_dir = root
        py_files = [
            p for p in sorted(root.rglob("*.py"))
            if "__pycache__" not in p.parts and not any(pt.startswith(".") for pt in p.parts)
        ]
    else:
        return {"schema": SCHEMA, "ok": False, "callables": [], "classes": []}

    callables: list[dict[str, Any]] = []
    classes: list[dict[str, Any]] = []

    for fp in py_files:
        try:
            src = fp.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src)
        except (OSError, SyntaxError):
            continue
        rel_mod = fp.relative_to(base_dir).with_suffix("").as_posix().replace("/", ".")
        if rel_mod.endswith(".__init__"):
            rel_mod = rel_mod[:-9]

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                params = [a.arg for a in node.args.args]
                n_defaults = len(node.args.defaults)
                req_count = max(0, len(params) - n_defaults)
                ann_map = {
                    a.arg: ast.unparse(a.annotation)
                    for a in node.args.args
                    if a.annotation is not None
                }
                ret_ann = ast.unparse(node.returns) if node.returns is not None else ""
                doc = ast.get_docstring(node) or ""
                tokens = sorted(
                    set(_WORD_RE.findall(f"{rel_mod} {node.name} {doc}".lower())) - _STOP
                )
                callables.append({
                    "file": str(fp),
                    "module": rel_mod,
                    "name": node.name,
                    "params": params,
                    "required_arity": req_count,
                    "annotations": ann_map,
                    "returns": ret_ann,
                    "docstring": doc[:400],
                    "tokens": tokens,
                })
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                methods = [
                    sub.name for sub in node.body
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and not sub.name.startswith("_")
                ]
                classes.append({
                    "file": str(fp),
                    "module": rel_mod,
                    "name": node.name,
                    "methods": methods,
                    "docstring": (ast.get_docstring(node) or "")[:400],
                })

    return {
        "schema": SCHEMA,
        "ok": True,
        "file_count": len(py_files),
        "callables": callables,
        "classes": classes,
    }


def rank_callables_for_goal(goal: str, surface: Mapping[str, Any], *, limit: int = 5) -> list[dict[str, Any]]:
    """Rank discovered local functions against a plain-English goal by semantic token overlap."""
    gw = set(_WORD_RE.findall(goal.lower())) - _STOP
    # Expand split snake_case words so `normalize_slug` matches `normalize` and `slug`
    expanded_gw = set(gw)
    for w in list(gw):
        expanded_gw.update(p for p in w.split("_") if len(p) > 1)

    scored: list[tuple[float, dict[str, Any]]] = []
    for fn_meta in surface.get("callables") or []:
        fn_words: set[str] = set()
        for tok in fn_meta.get("tokens") or []:
            fn_words.add(tok)
            fn_words.update(p for p in tok.split("_") if len(p) > 1)
        overlap = expanded_gw & fn_words
        if not overlap:
            continue
        name_parts = set(fn_meta["name"].lower().split("_")) | {fn_meta["name"].lower()}
        name_bonus = 2.0 * len(expanded_gw & name_parts)
        score = (len(overlap) + name_bonus) / (max(1, len(name_parts)) ** 0.4)
        scored.append((round(score, 6), dict(fn_meta, match_score=round(score, 6))))

    scored.sort(key=lambda t: (-t[0], t[1]["name"]))
    return [row for _, row in scored[:limit]]


# --------------------------------------------------------------------------- #
# 2. Live Runtime Call-Frame & Assertion Capture + Synthesis Repair
# --------------------------------------------------------------------------- #
class _AssertionInstrumentor(ast.NodeTransformer):
    """Instrument `assert fn(*a) == exp` and `self.assertEqual(fn(*a), exp)` to record live I/O."""

    def __init__(self, target_names: set[str]) -> None:
        self.target_names = target_names

    def _matched_call(self, expr: ast.AST) -> tuple[str, list[ast.expr]] | None:
        if not isinstance(expr, ast.Call) or expr.keywords:
            return None
        if isinstance(expr.func, ast.Name) and expr.func.id in self.target_names:
            return expr.func.id, list(expr.args)
        if isinstance(expr.func, ast.Attribute) and expr.func.attr in self.target_names:
            return expr.func.attr, list(expr.args)
        return None

    def visit_Assert(self, node: ast.Assert) -> ast.AST:
        t = node.test
        if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq):
            hit = self._matched_call(t.left)
            exp_expr = t.comparators[0]
            if hit is None:
                hit = self._matched_call(t.comparators[0])
                exp_expr = t.left
            if hit is not None:
                fn_name, arg_exprs = hit
                return ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id="__brain_record_io__", ctx=ast.Load()),
                        args=[
                            ast.Constant(value=fn_name),
                            ast.Tuple(elts=arg_exprs, ctx=ast.Load()),
                            exp_expr,
                        ],
                        keywords=[],
                    )
                )
        return self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> ast.AST:
        c = node.value
        if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute):
            m = c.func.attr
            if m == "assertEqual" and len(c.args) >= 2:
                hit = self._matched_call(c.args[0])
                exp_expr = c.args[1]
                if hit is None:
                    hit = self._matched_call(c.args[1])
                    exp_expr = c.args[0]
                if hit is not None:
                    fn_name, arg_exprs = hit
                    return ast.Expr(
                        value=ast.Call(
                            func=ast.Name(id="__brain_record_io__", ctx=ast.Load()),
                            args=[
                                ast.Constant(value=fn_name),
                                ast.Tuple(elts=arg_exprs, ctx=ast.Load()),
                                exp_expr,
                            ],
                            keywords=[],
                        )
                    )
            elif m in ("assertTrue", "assertFalse") and len(c.args) >= 1:
                hit = self._matched_call(c.args[0])
                if hit is not None:
                    fn_name, arg_exprs = hit
                    return ast.Expr(
                        value=ast.Call(
                            func=ast.Name(id="__brain_record_io__", ctx=ast.Load()),
                            args=[
                                ast.Constant(value=fn_name),
                                ast.Tuple(elts=arg_exprs, ctx=ast.Load()),
                                ast.Constant(value=(m == "assertTrue")),
                            ],
                            keywords=[],
                        )
                    )
        return self.generic_visit(node)


def harvest_live_io_examples(
    proj: pathlib.Path,
    test_files: Sequence[pathlib.Path],
    target_functions: set[str],
) -> dict[str, tuple[list[tuple[tuple[Any, ...], Any]], list[Any]]]:
    """Harvest `(args_tuple, expected)` pairs from both static test ASTs and live instrumented runs.

    Instrumentation replaces assertions on `target_functions` with a non-aborting recorder so ALL
    assertions in a test method execute in a single pass instead of halting on the first failure!
    """
    by_fn: dict[str, list[tuple[tuple[Any, ...], Any]]] = {fn: [] for fn in target_functions}
    consts_by_fn: dict[str, list[Any]] = {fn: [] for fn in target_functions}

    # Step A: Static extraction first (zero-overhead fast path)
    for tf in test_files:
        try:
            tsrc = tf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for fn in target_functions:
            exs, csts = obs_synth.extract_io_examples_from_test_source(tsrc, fn)
            for ex in exs:
                if ex not in by_fn[fn]:
                    by_fn[fn].append(ex)
            for c in csts:
                if c not in consts_by_fn[fn]:
                    consts_by_fn[fn].append(c)

    # Step B: Live instrumented execution to capture computed fixtures, loops, and object args
    proj_str = str(proj.resolve())
    added_paths: list[str] = []
    for cand_p in (proj.resolve(), proj.resolve() / "src", proj.resolve() / "pkg"):
        s = str(cand_p)
        if cand_p.is_dir() and s not in sys.path:
            sys.path.insert(0, s)
            added_paths.append(s)

    def _recorder(fn_name: str, args_tuple: tuple[Any, ...], expected_val: Any) -> None:
        if fn_name in by_fn:
            pair = (tuple(args_tuple), expected_val)
            if pair not in by_fn[fn_name]:
                by_fn[fn_name].append(pair)
            if isinstance(expected_val, (int, float, str, bytes)) and not isinstance(expected_val, bool):
                if expected_val not in consts_by_fn[fn_name]:
                    consts_by_fn[fn_name].append(expected_val)

    old_dwb = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        for idx, tf in enumerate(test_files):
            try:
                tsrc = tf.read_text(encoding="utf-8", errors="replace")
                ttree = ast.parse(tsrc)
            except (OSError, SyntaxError):
                continue
            inst_tree = ast.fix_missing_locations(_AssertionInstrumentor(target_functions).visit(ttree))
            code_obj = compile(inst_tree, str(tf), "exec")
            mod_ns: dict[str, Any] = {
                "__name__": f"_brain_io_harvest_{idx}",
                "__file__": str(tf),
                "__brain_record_io__": _recorder,
            }
            try:
                exec(code_obj, mod_ns)  # noqa: S102 - local project test suite under repair
            except Exception:
                continue
            for name, obj in list(mod_ns.items()):
                if name.startswith("test_") and callable(obj) and not isinstance(obj, type):
                    try:
                        if not [p for p in inspect.signature(obj).parameters.values() if p.default is inspect.Parameter.empty]:
                            obj()
                    except KeyboardInterrupt:
                        raise
                    except BaseException:
                        pass
                elif isinstance(obj, type):
                    # unittest.TestCase subclass
                    t_methods = [m for m in dir(obj) if m.startswith("test_")]
                    if t_methods:
                        try:
                            inst = obj(t_methods[0])
                        except Exception:
                            try:
                                inst = obj()
                            except Exception:
                                continue
                        for m in t_methods:
                            try:
                                if hasattr(inst, "setUp"):
                                    inst.setUp()
                                getattr(inst, m)()
                            except Exception:
                                pass
    finally:
        sys.dont_write_bytecode = old_dwb
        for s in added_paths:
            if s in sys.path:
                sys.path.remove(s)
        assert proj_str or True

    return {fn: (by_fn[fn], consts_by_fn[fn][:12]) for fn in target_functions if by_fn[fn]}


def _replace_function_body_in_source(src: str, fn_name: str, new_body_stmt: str) -> str | None:
    """Replace the body of top-level `def <fn_name>(...):` while preserving signature & decorators."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None
    target_fn: ast.FunctionDef | None = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == fn_name and node.body:
            target_fn = node
            break
    if target_fn is None:
        return None

    lines = src.splitlines(keepends=True)
    first_stmt = target_fn.body[0]
    # Keep docstring if present
    if (
        isinstance(first_stmt, ast.Expr)
        and isinstance(first_stmt.value, ast.Constant)
        and isinstance(first_stmt.value.value, str)
        and len(target_fn.body) >= 2
    ):
        body_start_line = target_fn.body[1].lineno
        indent = " " * target_fn.body[1].col_offset
    else:
        body_start_line = first_stmt.lineno
        indent = " " * first_stmt.col_offset
    body_end_line = max((st.end_lineno or st.lineno) for st in target_fn.body)

    indented_lines: list[str] = []
    for raw_ln in new_body_stmt.splitlines():
        if raw_ln.strip():
            indented_lines.append(f"{indent}{raw_ln}\n")
    rebuilt = "".join(lines[: body_start_line - 1]) + "".join(indented_lines) + "".join(lines[body_end_line:])
    try:
        ast.parse(rebuilt)
    except SyntaxError:
        return None
    return rebuilt


_METHOD_DUAL_SWAPS: dict[str, tuple[str, ...]] = {
    "strip": ("lstrip", "rstrip"),
    "rstrip": ("lstrip", "strip"),
    "lstrip": ("rstrip", "strip"),
    "find": ("rfind",),
    "rfind": ("find",),
    "index": ("rindex",),
    "rindex": ("index",),
    "split": ("rsplit",),
    "rsplit": ("split",),
    "partition": ("rpartition",),
    "rpartition": ("partition",),
    "ljust": ("rjust",),
    "rjust": ("ljust",),
    "startswith": ("endswith",),
    "endswith": ("startswith",),
    "lower": ("upper",),
    "upper": ("lower",),
}

_BUILTIN_DUAL_SWAPS: dict[str, str] = {
    "min": "max",
    "max": "min",
    "any": "all",
    "all": "any",
    "bisect_left": "bisect_right",
    "bisect_right": "bisect_left",
    "floor": "ceil",
    "ceil": "floor",
}


def _splice_span_bytes(src_bytes: bytes, node: ast.AST, replacement_str: str) -> str | None:
    lineno = getattr(node, "lineno", None)
    col = getattr(node, "col_offset", None)
    end_lineno = getattr(node, "end_lineno", None)
    end_col = getattr(node, "end_col_offset", None)
    if None in (lineno, col, end_lineno, end_col):
        return None
    lines = src_bytes.splitlines(keepends=True)
    if not (1 <= lineno <= end_lineno <= len(lines)):
        return None
    prefix = b"".join(lines[: lineno - 1]) + lines[lineno - 1][:col]
    suffix = lines[end_lineno - 1][end_col:] + b"".join(lines[end_lineno:])
    try:
        return (prefix + replacement_str.encode("utf-8") + suffix).decode("utf-8")
    except UnicodeDecodeError:
        return None


def _reachable_symbol_names(proj: pathlib.Path, test_files: Sequence[pathlib.Path], src_file: pathlib.Path) -> set[str]:
    """Collect symbol names referenced in `test_files` plus 1-hop project wrapper modules."""
    names: set[str] = set()
    for tf in test_files:
        try:
            ttree = ast.parse(tf.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        for n in ast.walk(ttree):
            if isinstance(n, ast.Name):
                names.add(n.id)
            elif isinstance(n, ast.Attribute):
                names.add(n.attr)
            elif isinstance(n, ast.alias):
                names.add(n.name.rsplit(".", 1)[-1])
    # Expand 1 hop through small sibling modules (e.g., service/consumer modules)
    test_resolved = {p.resolve() for p in test_files}
    src_resolved = src_file.resolve()
    try:
        sib_files = [
            p for p in sorted(proj.rglob("*.py"))
            if "__pycache__" not in p.parts
            and p.resolve() not in test_resolved
            and p.resolve() != src_resolved
            and p.stat().st_size <= 32_000
        ][:16]
    except OSError:
        sib_files = []
    for sp in sib_files:
        try:
            stree = ast.parse(sp.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        for node in stree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Name):
                        names.add(sub.id)
                    elif isinstance(sub, ast.Attribute):
                        names.add(sub.attr)
            elif isinstance(node, ast.ImportFrom):
                for al in node.names:
                    names.add(al.name)
    return names


def algebraic_dual_span_candidates(
    src: str,
    *,
    allowed_functions: set[str] | None = None,
    hot_lines: Sequence[int] | None = None,
    max_candidates: int = 8,
) -> list[tuple[str, str]]:
    """Produce byte-span-preserving directional/dual method & builtin swaps on target functions."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    src_bytes = src.encode("utf-8")
    hot_set = set(hot_lines or ())
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if allowed_functions is not None and node.name not in allowed_functions:
            continue
        for sub in ast.walk(node):
            if not isinstance(sub, ast.Call):
                continue
            lineno = getattr(sub, "lineno", None)
            if hot_set and lineno is not None and not any(abs(lineno - hl) <= 2 for hl in hot_set):
                continue
            if isinstance(sub.func, ast.Attribute) and sub.func.attr in _METHOD_DUAL_SWAPS:
                val_seg = ast.get_source_segment(src, sub.func.value)
                if val_seg:
                    for dual_attr in _METHOD_DUAL_SWAPS[sub.func.attr]:
                        cand = _splice_span_bytes(src_bytes, sub.func, f"{val_seg}.{dual_attr}")
                        if cand and cand != src and cand not in seen:
                            try:
                                ast.parse(cand)
                                seen.add(cand)
                                out.append((f"method_dual_{sub.func.attr}_to_{dual_attr}", cand))
                            except SyntaxError:
                                pass
            elif isinstance(sub.func, ast.Name) and sub.func.id in _BUILTIN_DUAL_SWAPS:
                dual_fn = _BUILTIN_DUAL_SWAPS[sub.func.id]
                cand = _splice_span_bytes(src_bytes, sub.func, dual_fn)
                if cand and cand != src and cand not in seen:
                    try:
                        ast.parse(cand)
                        seen.add(cand)
                        out.append((f"builtin_dual_{sub.func.id}_to_{dual_fn}", cand))
                    except SyntaxError:
                        pass
            if len(out) >= max_candidates:
                return out
    return out


def _extract_test_guard_signals(test_files: Sequence[pathlib.Path]) -> tuple[list[tuple[str, str | None]], bool, bool]:
    """Extract `(exc_name, msg_literal)` expectations plus `(has_zero_arg, has_neg_arg)` from tests."""
    exc_specs: list[tuple[str, str | None]] = []
    has_zero = False
    has_neg = False
    known_excs = {
        "ValueError", "TypeError", "IndexError", "KeyError", "ZeroDivisionError", "RuntimeError",
    }
    for tf in test_files:
        try:
            ttree = ast.parse(tf.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        pending_exc: str | None = None
        for sub in ast.walk(ttree):
            if isinstance(sub, ast.Constant) and type(sub.value) is int and sub.value == 0:
                has_zero = True
            elif isinstance(sub, ast.UnaryOp) and isinstance(sub.op, ast.USub) and isinstance(sub.operand, ast.Constant):
                if isinstance(sub.operand.value, (int, float)) and sub.operand.value > 0:
                    has_neg = True
            elif isinstance(sub, ast.Call):
                fname = (
                    sub.func.id if isinstance(sub.func, ast.Name)
                    else (sub.func.attr if isinstance(sub.func, ast.Attribute) else "")
                )
                if fname in ("assertRaises", "assertRaisesRegex", "raises") and sub.args:
                    exc_arg = sub.args[0]
                    ename = exc_arg.id if isinstance(exc_arg, ast.Name) else ""
                    if ename in known_excs:
                        msg_lit: str | None = None
                        if len(sub.args) >= 2 and isinstance(sub.args[1], ast.Constant) and isinstance(sub.args[1].value, str):
                            msg_lit = sub.args[1].value
                        for kw in sub.keywords:
                            if kw.arg == "match" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                msg_lit = kw.value.value
                        pair = (ename, msg_lit)
                        if pair not in exc_specs:
                            exc_specs.append(pair)
                        pending_exc = ename
                elif fname == "assertIn" and sub.args and isinstance(sub.args[0], ast.Constant) and isinstance(sub.args[0].value, str):
                    if pending_exc:
                        pair = (pending_exc, sub.args[0].value)
                        if pair not in exc_specs:
                            exc_specs.insert(0, pair)
    return exc_specs, has_zero, has_neg


def test_driven_precondition_guard_candidates(
    src: str,
    test_files: Sequence[pathlib.Path],
    *,
    allowed_functions: set[str] | None = None,
    max_candidates: int = 6,
) -> list[tuple[str, str]]:
    """Synthesize entry `< 0` raise & `== 0` early-return guards before eager iteration/allocation."""
    exc_specs, has_zero, has_neg = _extract_test_guard_signals(test_files)
    if not exc_specs and not has_zero and not has_neg:
        return []
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    lines = src.splitlines(keepends=True)
    size_names = {"n", "size", "width", "count", "step", "length", "limit", "k", "num"}
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or not node.body or not node.args.args:
            continue
        if allowed_functions is not None and node.name not in allowed_functions:
            continue
        params = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
        if not params:
            continue
        first_stmt = node.body[0]
        if (
            isinstance(first_stmt, ast.Expr)
            and isinstance(first_stmt.value, ast.Constant)
            and isinstance(first_stmt.value.value, str)
        ):
            if len(node.body) < 2:
                continue
            exec_stmt = node.body[1]
        else:
            exec_stmt = first_stmt
        # Skip if function already starts with an `if` guard on the numeric parameter
        if isinstance(exec_stmt, ast.If):
            continue

        # Identify size/bound parameter
        bound_param = next((p for p in params if p in size_names), None)
        if bound_param is None:
            bound_param = params[1] if len(params) >= 2 else params[0]

        indent = " " * exec_stmt.col_offset
        is_gen = any(isinstance(sub, (ast.Yield, ast.YieldFrom)) for sub in ast.walk(node))
        zero_ret = "return" if is_gen else "return []"
        insert_idx = exec_stmt.lineno - 1

        primary_exc, primary_msg = exc_specs[0] if exc_specs else ("ValueError", None)
        raise_expr = (
            f"raise {primary_exc}({primary_msg!r})"
            if primary_msg is not None
            else f"raise {primary_exc}()"
        )

        guard_blocks: list[tuple[str, list[str]]] = []
        if has_neg and has_zero:
            guard_blocks.append((
                "guard_neg_raise_and_zero_return",
                [
                    f"{indent}if {bound_param} is not None and {bound_param} < 0:\n",
                    f"{indent}    {raise_expr}\n",
                    f"{indent}if {bound_param} == 0:\n",
                    f"{indent}    {zero_ret}\n",
                    "\n",
                ],
            ))
        if has_neg or exc_specs:
            guard_blocks.append((
                "guard_neg_raise",
                [
                    f"{indent}if {bound_param} is not None and {bound_param} < 0:\n",
                    f"{indent}    {raise_expr}\n",
                ],
            ))
        if has_zero:
            guard_blocks.append((
                "guard_zero_early_return",
                [
                    f"{indent}if {bound_param} == 0:\n",
                    f"{indent}    {zero_ret}\n",
                ],
            ))

        for label, glines in guard_blocks:
            cand = "".join(lines[:insert_idx]) + "".join(glines) + "".join(lines[insert_idx:])
            if cand != src and cand not in seen:
                try:
                    ast.parse(cand)
                    seen.add(cand)
                    out.append((label, cand))
                except SyntaxError:
                    pass
            if len(out) >= max_candidates:
                return out
    return out


def synthesize_candidates_for_file(
    src_file: pathlib.Path,
    proj: pathlib.Path,
    test_files: Sequence[pathlib.Path],
) -> list[str]:
    """Generate observational-equivalence, algebraic-dual & precondition-guard candidates from live failing tests."""
    try:
        src = src_file.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
    except (OSError, SyntaxError):
        return []

    reachable = _reachable_symbol_names(proj, test_files, src_file)
    candidates: list[str] = []

    # Step 1: Fast AST-exact algebraic duals & test-driven entry precondition guards on reachable functions
    target_allow = reachable if reachable else None
    for _lbl, c_src in algebraic_dual_span_candidates(src, allowed_functions=target_allow, max_candidates=6):
        if c_src not in candidates:
            candidates.append(c_src)
    for _lbl, c_src in test_driven_precondition_guard_candidates(
        src, test_files, allowed_functions=target_allow, max_candidates=4
    ):
        if c_src not in candidates:
            candidates.append(c_src)

    # Step 2: Bottom-up observational equivalence + STUN conditional synthesis (skip huge multi-thousand-line modules)
    if len(src) > 40_000:
        return candidates[:8]

    fn_nodes: dict[str, ast.FunctionDef] = {}
    file_consts: list[Any] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            if reachable and node.name not in reachable:
                continue
            if node.args.args and not node.args.vararg and not node.args.kwarg:
                fn_nodes[node.name] = node
    for sub in ast.walk(tree):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, (int, float, str, bytes)) and not isinstance(sub.value, bool):
            if sub.value not in file_consts:
                file_consts.append(sub.value)

    if not fn_nodes:
        return candidates[:8]

    harvested = harvest_live_io_examples(proj, test_files, set(fn_nodes))

    for fn_name, (examples, test_consts) in harvested.items():
        if not examples:
            continue
        fn_node = fn_nodes[fn_name]
        param_names = [a.arg for a in fn_node.args.args]
        valid_exs = [ex for ex in examples if len(ex[0]) == len(param_names)]
        if not valid_exs:
            continue
        merged_consts = list(dict.fromkeys([*test_consts, *file_consts]))[:14]
        synth_body = obs_synth.synthesize_python_function_body(
            param_names=param_names,
            examples=valid_exs,
            extra_constants=merged_consts,
            max_weight=4,
            max_bank_size=900,
        )
        if synth_body is None:
            continue
        rewritten = _replace_function_body_in_source(src, fn_name, synth_body)
        if rewritten is not None and rewritten != src and rewritten not in candidates:
            candidates.append(rewritten)

    return candidates[:10]


# --------------------------------------------------------------------------- #
# 3. Semantic HTML/DOM Form Introspector -> Direct <15ms HTTP Execution
# --------------------------------------------------------------------------- #
class _RichSemanticFormParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.forms: list[dict[str, Any]] = []
        self._cur: dict[str, Any] | None = None
        self._label_for: str | None = None
        self._label_buf: list[str] = []
        self.labels_by_id: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        amap = {k.lower(): (v or "") for k, v in attrs}
        t = tag.lower()
        if t == "form":
            self._cur = {
                "action": amap.get("action") or "",
                "method": (amap.get("method") or "POST").upper(),
                "fields": [],
            }
            self.forms.append(self._cur)
        elif t == "label":
            self._label_for = amap.get("for") or ""
            self._label_buf = []
        elif t in {"input", "textarea", "select"} and self._cur is not None:
            self._cur["fields"].append({
                "tag": t,
                "id": amap.get("id") or "",
                "name": amap.get("name") or "",
                "type": (amap.get("type") or "text").lower(),
                "value": amap.get("value") or "",
                "aria": amap.get("aria-label") or "",
                "placeholder": amap.get("placeholder") or "",
            })

    def handle_data(self, data: str) -> None:
        if self._label_for is not None:
            self._label_buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t == "form":
            self._cur = None
        elif t == "label" and self._label_for is not None:
            if self._label_for:
                self.labels_by_id[self._label_for] = "".join(self._label_buf).strip()
            self._label_for = None
            self._label_buf = []


def discover_and_execute_semantic_web_form(
    goal: str,
    url: str,
) -> dict[str, Any]:
    """Inspect a web page's semantic `<form>` schema and submit directly via HTTP (<15 ms),
    preserving `CookieJar` sessions and dynamic hidden CSRF/nonce tokens across GET -> POST.
    """
    import http.cookiejar

    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    try:
        with opener.open(url, timeout=10) as resp:
            html_text = resp.read().decode("utf-8", "replace")
            had_set_cookie = len(cookie_jar) > 0 or bool(resp.headers.get("Set-Cookie"))
    except Exception as exc:
        return {"ok": False, "reason": f"WEB_FETCH_FAILED:{type(exc).__name__}"}

    parser = _RichSemanticFormParser()
    parser.feed(html_text)
    if not parser.forms:
        return {"ok": False, "reason": "NO_HTML_FORM_DISCOVERED"}

    # Extract `field=value`, `field "value"`, or `<field> <value>` pairs from the goal
    kv_pairs: list[tuple[str, str]] = []
    for m in re.finditer(r"""([A-Za-z_][A-Za-z0-9_-]*)\s*(?:=|:|to|as|with)\s*(?:"([^"]+)"|'([^']+)'|([^\s,;]+))""", goal):
        key = m.group(1).lower()
        val = m.group(2) or m.group(3) or m.group(4) or ""
        val = val.rstrip(".")
        if key not in _STOP and not val.startswith(("http://", "https://")):
            kv_pairs.append((key, val))

    form = parser.forms[0]
    form_body: dict[str, str] = {}
    template_form_body: dict[str, str] = {}
    hidden_fields: list[str] = []
    matched_fields = 0

    for fld in form["fields"]:
        nm = fld.get("name") or ""
        if not nm:
            continue
        ftype = fld.get("type") or "text"
        if ftype == "hidden":
            hval = fld.get("value") or ""
            form_body[nm] = hval
            template_form_body[nm] = f"{{{{hidden:{nm}}}}}"
            hidden_fields.append(nm)
            continue
        if ftype in {"submit", "button", "reset"}:
            continue
        label_txt = parser.labels_by_id.get(fld.get("id") or "", "")
        descriptors = " ".join([nm, fld.get("aria") or "", fld.get("placeholder") or "", label_txt]).lower()
        desc_words = set(_WORD_RE.findall(descriptors))
        assigned = None
        for gk, gv in kv_pairs:
            if gk == nm.lower() or gk in desc_words or any(gk in dw or dw in gk for dw in desc_words if len(dw) > 2):
                assigned = gv
                break
        if assigned is not None:
            form_body[nm] = assigned
            template_form_body[nm] = assigned
            matched_fields += 1
        elif fld.get("value"):
            form_body[nm] = fld["value"]
            template_form_body[nm] = fld["value"]

    if matched_fields == 0:
        return {"ok": False, "reason": "NO_SEMANTIC_FORM_FIELDS_BOUND_FROM_GOAL"}

    submit_url = urllib.parse.urljoin(url, form["action"] or url)
    method = form["method"]
    if method == "GET":
        sep = "&" if "?" in submit_url else "?"
        full_url = submit_url + sep + urllib.parse.urlencode(form_body)
        req = urllib.request.Request(full_url, method="GET")
    else:
        encoded = urllib.parse.urlencode(form_body).encode("utf-8")
        req = urllib.request.Request(
            submit_url,
            data=encoded,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method=method,
        )

    try:
        with opener.open(req, timeout=15) as sresp:
            resp_body = sresp.read().decode("utf-8", "replace")
            status_code = int(sresp.status)
    except Exception as exc:
        return {"ok": False, "reason": f"WEB_SUBMIT_FAILED:{type(exc).__name__}"}

    if not (200 <= status_code < 400):
        return {"ok": False, "reason": f"WEB_SUBMIT_HTTP_{status_code}"}

    needs_stateful_get = bool(hidden_fields or had_set_cookie)
    http_exchanges: list[dict[str, Any]] = []
    if needs_stateful_get:
        http_exchanges.append({
            "method": "GET",
            "url": url,
            "extract_hidden_inputs": True,
            "sets_session_cookie": bool(had_set_cookie),
            "headers": {"Accept": "text/html"},
        })
    http_exchanges.append({
        "method": method,
        "url": submit_url,
        "form_body": template_form_body if needs_stateful_get else form_body,
        "headers": {"Content-Type": "application/x-www-form-urlencoded"},
    })

    return {
        "ok": True,
        "submit_url": submit_url,
        "method": method,
        "form_body": form_body,
        "stateful_csrf_or_cookie": needs_stateful_get,
        "hidden_fields": hidden_fields,
        "status_code": status_code,
        "response_body": resp_body[:1000],
        "causal_trace": {
            "steps": [],
            "observed_effects": {
                "http_exchanges": http_exchanges,
            },
        },
    }
