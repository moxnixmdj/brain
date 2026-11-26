"""Generalized Live-Frame Differential Witness Inversion (Zero Model Calls, Zero Weights).

Composes live-frame concrete assertion inversion with multi-return/generator (`yield`)/assignment
span localization, differential `(actual -> required)` value morphisms, repo-native `f_globals`
pure helper discovery, Python data-model `__eq__`/`__hash__` homomorphism synthesis, subscript
totalization (`KeyError`), abductive parameter type-validation guards (including PEP-570
positional-only parameters), missing-exception separating guards, and public re-export
`__module__` invariants.
"""
from __future__ import annotations

import importlib
import json
import os
import pathlib
import select
import signal
import subprocess
import sys
import threading
import time
from typing import Any


SCHEMA = "BRAIN_DIFFERENTIAL_WITNESS_INVERSION_V1"


_LIVE_DIFFERENTIAL_WITNESS_SCRIPT = r'''
import ast
import builtins
import collections.abc
import inspect
import json
import os
import pathlib
import re
import sys

import pytest

cfg = json.loads(sys.argv[1])
cow_root = pathlib.Path(cfg["cow_root"]).resolve()
cow_prefix = str(cow_root) + os.sep
test_file = cfg.get("test_file") or ""
fail_ids = list(cfg.get("fail_ids", []))
pass_ids = list(cfg.get("pass_ids", []))
out_path = pathlib.Path(cfg["out_path"])
max_records_per_test = int(cfg.get("max_records", 260))
max_events_per_test = int(cfg.get("max_events", 35000))

PURE_BUILTINS = (
    "len", "str", "int", "float", "bool", "bytes", "tuple", "list", "set",
    "frozenset", "dict", "sorted", "min", "max", "sum", "abs", "any", "all",
    "isinstance", "issubclass", "type", "hash", "ord", "chr", "repr", "getattr", "hasattr",
)
BUILTINS_MAP = {k: getattr(builtins, k) for k in PURE_BUILTINS if hasattr(builtins, k)}

MUTATING_PREFIXES = (
    "set_", "write", "delete", "remove", "update", "save", "clear", "pop",
    "push", "append", "extend", "insert", "unlink", "rmtree", "mkdir", "open",
    "exec", "compile", "eval", "run", "spawn", "fork", "kill",
)

_file_rel_cache = {}
pass_records_by_site = {}   # (rel_path, line_no, kind) -> list[{"value": ..., "scope": ...}]
pass_entry_by_func = {}     # (rel_path, func_name) -> list[dict]
fail_captures = []

_current_mode = [None]
_current_records = []
_current_entries = []
_current_events = [0]


def _rel_if_repo_source(filename):
    if not filename or filename[0] == "<":
        return None
    if filename in _file_rel_cache:
        return _file_rel_cache[filename]
    try:
        resolved = str(pathlib.Path(filename).resolve())
    except Exception:
        resolved = filename
    if not resolved.startswith(cow_prefix):
        _file_rel_cache[filename] = None
        return None
    rel = resolved[len(cow_prefix):].replace(os.sep, "/")
    base = rel.rsplit("/", 1)[-1]
    if (
        rel.startswith((".brain", "tests/", "test/", "docs/"))
        or "/tests/" in ("/" + rel)
        or base.startswith(("test_", "conftest.py", "setup.py"))
        or base.endswith("_test.py")
    ):
        _file_rel_cache[filename] = None
        return None
    _file_rel_cache[filename] = rel
    return rel


def _shallow_safe_scope(f_locals):
    out = {}
    for k, v in list(f_locals.items())[:32]:
        # Keep PEP-484/570 positional-only parameters like `__s`; skip only dunders `__x__`
        if not isinstance(k, str) or (k.startswith("__") and k.endswith("__")):
            continue
        if isinstance(v, (list, dict, set)):
            try:
                out[k] = v.copy()
                continue
            except Exception:
                pass
        out[k] = v
    return out


def _pure_repo_helpers(f_globals):
    helpers = {}
    for gk, gv in list(f_globals.items())[:110]:
        if not isinstance(gk, str) or (gk.startswith("__") and gk.endswith("__")):
            continue
        low = gk.lower()
        if any(low.startswith(p) for p in MUTATING_PREFIXES):
            continue
        if gk in ("re", "math", "operator", "itertools"):
            helpers[gk] = gv
            continue
        if inspect.isclass(gv) and issubclass(gv, BaseException):
            helpers[gk] = gv
            continue
        code = getattr(gv, "__code__", None)
        if code is None or not callable(gv):
            continue
        fn_file = getattr(code, "co_filename", "") or ""
        try:
            fn_res = str(pathlib.Path(fn_file).resolve())
        except Exception:
            fn_res = fn_file
        if not fn_res.startswith(cow_prefix):
            continue
        try:
            sig = inspect.signature(gv)
            req_pos = [
                p for p in sig.parameters.values()
                if p.default is inspect.Parameter.empty
                and p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            ]
            if len(req_pos) == 1:
                helpers[gk] = gv
        except Exception:
            pass
    return helpers


def _tracer(frame, event, arg):
    if _current_events[0] >= max_events_per_test:
        raise TimeoutError("WITNESS_TRACE_EVENT_CAP")
    rel = _rel_if_repo_source(frame.f_code.co_filename)
    if rel is None:
        return None
    _current_events[0] += 1
    func_name = frame.f_code.co_name
    if event == "call":
        snap = _shallow_safe_scope(frame.f_locals)
        if _current_mode[0] == "pass":
            lst = pass_entry_by_func.setdefault((rel, func_name), [])
            if len(lst) < 10:
                lst.append(snap)
        else:
            if len(_current_entries) < 80:
                _current_entries.append({
                    "rel_path": rel,
                    "func": func_name,
                    "firstlineno": frame.f_code.co_firstlineno,
                    "scope": snap,
                    "helpers": _pure_repo_helpers(frame.f_globals),
                })
        return _tracer

    if event in ("return", "exception"):
        kind = "return" if event == "return" else "raise"
        val = arg if event == "return" else (arg[1] if isinstance(arg, tuple) and len(arg) > 1 else None)
        snap = _shallow_safe_scope(frame.f_locals)
        if _current_mode[0] == "pass":
            if kind == "return":
                lst = pass_records_by_site.setdefault((rel, frame.f_lineno, kind), [])
                if len(lst) < 10:
                    lst.append({"value": val, "scope": snap})
        else:
            if len(_current_records) < max_records_per_test:
                _current_records.append({
                    "kind": kind,
                    "rel_path": rel,
                    "func": func_name,
                    "firstlineno": frame.f_code.co_firstlineno,
                    "line": frame.f_lineno,
                    "value": val,
                    "exc_type": type(val).__name__ if (kind == "raise" and val is not None) else None,
                    "scope": snap,
                    "helpers": _pure_repo_helpers(frame.f_globals),
                })
    return _tracer


def _eval_in_test_frame(node, frame):
    try:
        code = compile(ast.Expression(body=node), "<witness>", "eval")
        return True, eval(code, frame.f_globals, frame.f_locals)
    except Exception:
        return False, None


def _find_innermost_stmt(tree, line_no, kinds):
    best = None
    for nd in ast.walk(tree):
        if isinstance(nd, kinds):
            end_ln = getattr(nd, "end_lineno", nd.lineno)
            if nd.lineno <= line_no <= end_ln:
                if best is None or nd.lineno >= best.lineno:
                    best = nd
    return best


def _extract_test_witness(excinfo):
    if excinfo is None:
        return None
    exc_val = getattr(excinfo, "value", None)
    exc_typename = getattr(excinfo, "typename", type(exc_val).__name__ if exc_val is not None else "")

    test_entry = None
    for entry in reversed(list(getattr(excinfo, "traceback", []) or [])):
        epath = str(getattr(entry, "path", "") or "")
        if not epath:
            continue
        try:
            eres = str(pathlib.Path(epath).resolve())
        except Exception:
            eres = epath
        if eres.startswith(cow_prefix):
            rel_e = eres[len(cow_prefix):].replace(os.sep, "/")
            base_e = rel_e.rsplit("/", 1)[-1]
            if rel_e.startswith("tests/") or "/tests/" in ("/" + rel_e) or base_e.startswith("test_") or base_e.endswith("_test.py"):
                test_entry = entry
                break

    msg_str = str(exc_val) if exc_val is not None else ""
    m_dnr = re.search(r"DID NOT RAISE <class '([^']+)'>", msg_str)
    if not m_dnr:
        m_dnr = re.search(r"([A-Za-z_]\w*(?:Error|Exception|Warning|Invalid\w+)) not raised", msg_str)
    if m_dnr:
        exc_cls_short = m_dnr.group(1).rsplit(".", 1)[-1]
        return {
            "mode": "missing_raise",
            "expected_exc": exc_cls_short,
            "required": None,
            "actual": None,
            "have_actual": False,
        }

    if test_entry is None:
        if exc_typename not in ("AssertionError", "Failed"):
            return {
                "mode": "uncaught_exception",
                "exc_type": exc_typename,
                "exc_msg": msg_str[:300],
                "required": None,
                "actual": None,
                "have_actual": False,
            }
        return None

    try:
        test_src = pathlib.Path(str(test_entry.path)).read_text(encoding="utf-8", errors="replace")
        test_tree = ast.parse(test_src)
    except Exception:
        return None

    t_line = int(test_entry.lineno) + 1
    t_frame = test_entry.frame

    if exc_typename not in ("AssertionError", "Failed") and not isinstance(exc_val, AssertionError):
        w_stmt = _find_innermost_stmt(test_tree, t_line, ast.With)
        if w_stmt is not None:
            for item in w_stmt.items:
                c = item.context_expr
                if isinstance(c, ast.Call) and c.args:
                    ok_e, exp_e = _eval_in_test_frame(c.args[0], t_frame)
                    exp_name = getattr(exp_e, "__name__", None) if ok_e else None
                    match_pat = None
                    for kw in c.keywords:
                        if kw.arg == "match":
                            ok_m, m_v = _eval_in_test_frame(kw.value, t_frame)
                            if ok_m and isinstance(m_v, str):
                                match_pat = m_v
                    if exp_name:
                        return {
                            "mode": "wrong_exception",
                            "expected_exc": exp_name,
                            "required": match_pat,
                            "actual": msg_str,
                            "actual_exc": exc_typename,
                            "have_actual": True,
                        }
        return {
            "mode": "uncaught_exception",
            "exc_type": exc_typename,
            "exc_msg": msg_str[:300],
            "required": None,
            "actual": None,
            "have_actual": False,
        }

    a_stmt = _find_innermost_stmt(test_tree, t_line, ast.Assert)
    if a_stmt is not None:
        tn = a_stmt.test
        if isinstance(tn, ast.Compare) and len(tn.ops) == 1 and len(tn.comparators) == 1:
            op = tn.ops[0]
            ok_l, val_l = _eval_in_test_frame(tn.left, t_frame)
            ok_r, val_r = _eval_in_test_frame(tn.comparators[0], t_frame)
            if isinstance(op, (ast.Eq, ast.Is)) and ok_r:
                lhs_src = ast.unparse(tn.left)
                if isinstance(tn.left, ast.Constant) and not isinstance(tn.comparators[0], ast.Constant) and ok_l:
                    return {"mode": "eq", "required": val_l, "actual": val_r, "have_actual": True, "lhs_src": ast.unparse(tn.comparators[0])}
                return {"mode": "eq", "required": val_r, "actual": val_l, "have_actual": ok_l, "lhs_src": lhs_src}
            if isinstance(op, ast.In) and ok_l and ok_r:
                if isinstance(val_r, (list, tuple, set, frozenset)):
                    return {"mode": "elem_in_seq", "required_elem": val_l, "actual": list(val_r), "have_actual": True}
        elif isinstance(tn, ast.UnaryOp) and isinstance(tn.op, ast.Not):
            ok_o, val_o = _eval_in_test_frame(tn.operand, t_frame)
            return {"mode": "eq", "required": False, "actual": bool(val_o) if ok_o else True, "have_actual": True}
        else:
            ok_b, val_b = _eval_in_test_frame(tn, t_frame)
            return {"mode": "eq", "required": True, "actual": bool(val_b) if ok_b else False, "have_actual": True}

    e_stmt = _find_innermost_stmt(test_tree, t_line, ast.Expr)
    if e_stmt is not None and isinstance(e_stmt.value, ast.Call):
        call = e_stmt.value
        mname = call.func.attr if isinstance(call.func, ast.Attribute) else ""
        if mname in ("assertEqual", "assertEquals") and len(call.args) >= 2:
            ok0, v0 = _eval_in_test_frame(call.args[0], t_frame)
            ok1, v1 = _eval_in_test_frame(call.args[1], t_frame)
            if ok1:
                if isinstance(call.args[0], ast.Constant) and not isinstance(call.args[1], ast.Constant) and ok0:
                    return {"mode": "eq", "required": v0, "actual": v1, "have_actual": True, "lhs_src": ast.unparse(call.args[1])}
                arg0_src = ast.unparse(call.args[0])
                is_exc_str = arg0_src.startswith("str(") and ("exc" in arg0_src.lower() or "err" in arg0_src.lower())
                return {
                    "mode": "exc_message_eq" if is_exc_str else "eq",
                    "required": v1,
                    "actual": v0,
                    "have_actual": ok0,
                    "lhs_src": arg0_src,
                }
        elif mname == "assertTrue" and len(call.args) >= 1:
            return {"mode": "eq", "required": True, "actual": False, "have_actual": True}
        elif mname == "assertFalse" and len(call.args) >= 1:
            return {"mode": "eq", "required": False, "actual": True, "have_actual": True}
        elif mname == "assertIn" and len(call.args) >= 2:
            ok0, v0 = _eval_in_test_frame(call.args[0], t_frame)
            ok1, v1 = _eval_in_test_frame(call.args[1], t_frame)
            if ok0 and ok1 and isinstance(v1, (list, tuple, set, frozenset)):
                return {"mode": "elem_in_seq", "required_elem": v0, "actual": list(v1), "have_actual": True}

    w_stmt = _find_innermost_stmt(test_tree, t_line, ast.With)
    if w_stmt is not None:
        for item in w_stmt.items:
            c = item.context_expr
            if isinstance(c, ast.Call):
                for kw in c.keywords:
                    if kw.arg == "match":
                        ok_m, m_v = _eval_in_test_frame(kw.value, t_frame)
                        if ok_m and isinstance(m_v, str):
                            return {"mode": "regex", "required": m_v, "actual": msg_str, "have_actual": True}

    return {"mode": "eq", "required": True, "actual": False, "have_actual": True}


class _WitnessPlugin:
    def pytest_collection_modifyitems(self, items):
        wanted = set(fail_ids) | set(pass_ids)
        if wanted:
            kept = [it for it in items if it.nodeid in wanted]
            pass_set = set(pass_ids)
            kept.sort(key=lambda it: (0 if it.nodeid in pass_set else 1))
            if kept:
                items[:] = kept

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        nid = item.nodeid
        _current_records.clear()
        _current_entries.clear()
        _current_events[0] = 0
        _current_mode[0] = "pass" if nid in set(pass_ids) else "fail"
        sys.settrace(_tracer)
        try:
            yield
        finally:
            sys.settrace(None)

    def pytest_exception_interact(self, node, call, report):
        if getattr(call, "when", "") != "call":
            return
        nid = getattr(node, "nodeid", "")
        if nid in set(pass_ids) or len(fail_captures) >= 2:
            return
        w = _extract_test_witness(getattr(call, "excinfo", None))
        if w is not None:
            fail_captures.append({
                "nodeid": nid,
                "witness": w,
                "records": list(_current_records),
                "entries": list(_current_entries),
            })


def _replace_span(source_text, span_node, new_expr):
    lines = source_text.splitlines(True)
    sl, sc = span_node.lineno, span_node.col_offset
    el, ec = getattr(span_node, "end_lineno", sl), getattr(span_node, "end_col_offset", sc)
    if not (1 <= sl <= el <= len(lines)):
        return None
    rebuilt = (
        lines[: sl - 1]
        + [lines[sl - 1][:sc] + new_expr + lines[el - 1][ec:]]
        + lines[el:]
    )
    cand = "".join(rebuilt)
    if cand == source_text:
        return None
    try:
        ast.parse(cand)
        return cand
    except SyntaxError:
        return None


def _find_enclosing_func(tree, line_no):
    best = None
    for nd in ast.walk(tree):
        if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_ln = getattr(nd, "end_lineno", nd.lineno)
            if nd.lineno <= line_no <= end_ln:
                if best is None or nd.lineno >= best.lineno:
                    best = nd
    return best


def _find_enclosing_class(tree, line_no):
    best = None
    for nd in ast.walk(tree):
        if isinstance(nd, ast.ClassDef):
            end_ln = getattr(nd, "end_lineno", nd.lineno)
            if nd.lineno <= line_no <= end_ln:
                if best is None or nd.lineno >= best.lineno:
                    best = nd
    return best


def _walk_body(fn_node):
    for stmt in fn_node.body:
        for nd in ast.walk(stmt):
            yield nd


def _safe_eval(expr, scope, helpers):
    env_g = {"__builtins__": BUILTINS_MAP}
    if helpers:
        env_g.update(helpers)
    return eval(expr, env_g, scope)


def _vals_equal(a, b, mode="eq"):
    if mode == "regex":
        try:
            return bool(re.search(str(b), str(a)))
        except Exception:
            return False
    try:
        if type(a) is bool or type(b) is bool:
            return type(a) is type(b) and a == b
        return bool(a == b)
    except Exception:
        return False


def _passes_recorded_pass_frames(expr, pass_recs, helpers):
    for pr in pass_recs:
        try:
            pv = _safe_eval(expr, dict(pr["scope"]), helpers)
            if not _vals_equal(pv, pr["value"], "eq"):
                return False
        except Exception:
            return False
    return True


def _synthesize_patches():
    patches = []
    seen = set()
    file_cache = {}

    def _emit(rel_path, new_src, desc, prio=0):
        if not new_src:
            return
        key = (rel_path, new_src)
        if key in seen:
            return
        seen.add(key)
        patches.append({"rel_path": rel_path, "patched_src": new_src, "description": desc, "prio": prio})

    def _get_file(rel_path):
        if rel_path not in file_cache:
            fp = cow_root / rel_path
            if not fp.is_file():
                file_cache[rel_path] = (None, None)
            else:
                txt = fp.read_text(encoding="utf-8", errors="replace")
                try:
                    file_cache[rel_path] = (txt, ast.parse(txt))
                except SyntaxError:
                    file_cache[rel_path] = (None, None)
        return file_cache[rel_path]

    for cap in fail_captures:
        w = cap["witness"]
        mode = w["mode"]
        records = cap["records"]
        entries = cap["entries"]

        # ------------------------------------------------------------------
        # FAMILY 0: Public Package Re-Export `__module__` Invariant
        # ------------------------------------------------------------------
        if (
            mode == "eq"
            and isinstance(w.get("actual"), str)
            and isinstance(w.get("required"), str)
            and w["actual"].startswith(w["required"] + "._")
            and "__module__" in str(w.get("lhs_src") or "")
        ):
            pub_pkg = w["required"]
            priv_full = w["actual"]
            priv_tail = priv_full.split(".")[-1]
            lhs_parts = str(w.get("lhs_src") or "").split(".")
            raw_sym = lhs_parts[-2] if len(lhs_parts) >= 2 and lhs_parts[-1] == "__module__" else ""
            sym_name = re.sub(r"\(.*\)$", "", raw_sym).strip()
            for init_cand in (
                pathlib.Path("src") / pub_pkg.replace(".", "/") / "__init__.py",
                pathlib.Path(pub_pkg.replace(".", "/")) / "__init__.py",
            ):
                rel_init = init_cand.as_posix()
                init_txt, init_tree = _get_file(rel_init)
                if init_tree is None:
                    continue
                for nd in ast.walk(init_tree):
                    if isinstance(nd, ast.ImportFrom) and nd.module in (priv_tail, priv_full):
                        for alias in nd.names:
                            exported = alias.asname or alias.name
                            if not sym_name or exported == sym_name:
                                patched_init = init_txt.rstrip() + f"\n{exported}.__module__ = {pub_pkg!r}\n"
                                try:
                                    ast.parse(patched_init)
                                    _emit(
                                        rel_init,
                                        patched_init,
                                        f"Public re-export `__module__` invariant on `{exported}` in `{rel_init}`",
                                        prio=-4,
                                    )
                                except SyntaxError:
                                    pass

        # ------------------------------------------------------------------
        # FAMILY 1: Uncaught KeyError -> Body Subscript `.get(...)` Totalization
        # ------------------------------------------------------------------
        if mode == "uncaught_exception" and w.get("exc_type") == "KeyError":
            for rec in reversed(records):
                if rec["kind"] != "raise" or rec.get("exc_type") != "KeyError":
                    continue
                src_txt, tree = _get_file(rec["rel_path"])
                if tree is None:
                    continue
                fn_node = _find_enclosing_func(tree, rec["line"])
                if fn_node is None:
                    continue
                for sub in _walk_body(fn_node):
                    if (
                        isinstance(sub, ast.Subscript)
                        and isinstance(sub.ctx, ast.Load)
                        and sub.lineno <= rec["line"] <= getattr(sub, "end_lineno", sub.lineno)
                    ):
                        val_src = ast.get_source_segment(src_txt, sub.value) or ast.unparse(sub.value)
                        slc_src = ast.get_source_segment(src_txt, sub.slice) or ast.unparse(sub.slice)
                        for default_sfx in ("", ", False", ", 0", ", ''"):
                            new_e = f"{val_src}.get({slc_src}{default_sfx})"
                            cand = _replace_span(src_txt, sub, new_e)
                            if cand:
                                _emit(
                                    rec["rel_path"],
                                    cand,
                                    f"Live KeyError subscript totalization L{rec['line']}: `{new_e}`",
                                    prio=-3,
                                )

        # ------------------------------------------------------------------
        # FAMILY 2: Abductive Parameter Type-Validation Guard (incl. PEP-570 posonlyargs)
        # ------------------------------------------------------------------
        if mode in ("exc_message_eq", "wrong_exception", "regex") and isinstance(w.get("required"), str):
            req_msg = w["required"]
            for ent in entries[:8]:
                rel_e = ent["rel_path"]
                fn_nm = ent["func"]
                src_txt, tree = _get_file(rel_e)
                if tree is None:
                    continue
                fn_node = _find_enclosing_func(tree, ent["firstlineno"])
                if fn_node is None or not fn_node.body:
                    continue
                pass_ents = pass_entry_by_func.get((rel_e, fn_nm), [])
                exc_cls = w.get("expected_exc") or "TypeError"
                if exc_cls not in BUILTINS_MAP and exc_cls not in ent["helpers"]:
                    exc_cls = "TypeError"
                first_stmt = fn_node.body[0]
                if isinstance(first_stmt, ast.Expr) and isinstance(first_stmt.value, ast.Constant) and isinstance(first_stmt.value.value, str):
                    first_stmt = fn_node.body[1] if len(fn_node.body) > 1 else first_stmt
                lines = src_txt.splitlines(True)
                ins_idx = first_stmt.lineno - 1
                indent = lines[ins_idx][: len(lines[ins_idx]) - len(lines[ins_idx].lstrip())]

                all_param_args = list(getattr(fn_node.args, "posonlyargs", [])) + list(fn_node.args.args) + list(fn_node.args.kwonlyargs)
                for param_arg in all_param_args:
                    pname = param_arg.arg
                    if pname in ("self", "cls") or pname not in ent["scope"]:
                        continue
                    fail_pval = ent["scope"][pname]
                    fail_t_qual = type(fail_pval).__qualname__
                    fail_t_name = type(fail_pval).__name__

                    good_t_name = None
                    pass_types = {type(pe[pname]).__name__ for pe in pass_ents if pname in pe}
                    if len(pass_types) == 1:
                        cand_gt = next(iter(pass_types))
                        if cand_gt in ("str", "bytes", "int", "float", "dict", "list", "tuple"):
                            good_t_name = cand_gt
                    if good_t_name is None and param_arg.annotation is not None:
                        ann_s = ast.unparse(param_arg.annotation).strip()
                        if ann_s in ("str", "bytes", "int", "float", "dict", "list", "tuple"):
                            good_t_name = ann_s
                    if good_t_name is None:
                        m_exp = re.search(r"\bExpected\s+(str|bytes|int|float|dict|list|tuple)\b", req_msg)
                        if m_exp:
                            good_t_name = m_exp.group(1)

                    if good_t_name and good_t_name != fail_t_name:
                        msg_expr = repr(req_msg)
                        if fail_t_qual in req_msg:
                            escaped = req_msg.replace("\\", "\\\\").replace('"', '\\"').replace("{", "{{").replace("}", "}}")
                            f_body = escaped.replace(fail_t_qual, f"{{type({pname}).__qualname__}}")
                            msg_expr = f'f"{f_body}"'
                        elif fail_t_name in req_msg:
                            escaped = req_msg.replace("\\", "\\\\").replace('"', '\\"').replace("{", "{{").replace("}", "}}")
                            f_body = escaped.replace(fail_t_name, f"{{type({pname}).__name__}}")
                            msg_expr = f'f"{f_body}"'
                        guard_block = f"{indent}if not isinstance({pname}, {good_t_name}):\n{indent}    raise {exc_cls}({msg_expr})\n"
                        cand_src = "".join(lines[:ins_idx] + [guard_block] + lines[ins_idx:])
                        try:
                            ast.parse(cand_src)
                            _emit(
                                rel_e,
                                cand_src,
                                f"Abductive parameter type guard in `{fn_nm}`: `not isinstance({pname}, {good_t_name})`",
                                prio=-4,
                            )
                        except SyntaxError:
                            pass

        # ------------------------------------------------------------------
        # FAMILY 3: Missing-Exception Separating Guard (`DID NOT RAISE <Exc>`)
        # ------------------------------------------------------------------
        if mode == "missing_raise" and w.get("expected_exc"):
            exp_exc = w["expected_exc"]
            for rec in reversed(records):
                if rec["kind"] != "return":
                    continue
                rel_r = rec["rel_path"]
                src_txt, tree = _get_file(rel_r)
                if tree is None:
                    continue
                fn_node = _find_enclosing_func(tree, rec["line"])
                if fn_node is None:
                    continue
                raise_templates = []
                for scope_root in (fn_node, tree):
                    for rn in ast.walk(scope_root):
                        if isinstance(rn, ast.Raise) and rn.exc is not None:
                            r_src = ast.unparse(rn.exc)
                            if r_src.startswith(exp_exc + "(") or r_src == exp_exc:
                                if r_src not in raise_templates:
                                    raise_templates.append(r_src)
                    if raise_templates:
                        break
                if not raise_templates and (exp_exc in rec["helpers"] or exp_exc in BUILTINS_MAP):
                    raise_templates.append(f"{exp_exc}('Invalid value')")
                if not raise_templates:
                    continue

                pass_recs = pass_records_by_site.get((rel_r, rec["line"], "return"), [])
                if not pass_recs:
                    continue
                f_scope = rec["scope"]
                vnames = [k for k in f_scope if k not in ("self", "cls")]
                sep_guards = []
                cand_preds = []
                for vn in vnames[:14]:
                    cand_preds.extend([f"{vn} is None", f"{vn} is not None", f"not {vn}", f"bool({vn})"])
                    fv = f_scope[vn]
                    if isinstance(fv, int):
                        for vn2 in vnames[:14]:
                            if vn2 != vn and isinstance(f_scope.get(vn2), (str, bytes, list, tuple)):
                                cand_preds.append(f"{vn} < len({vn2})")
                                cand_preds.append(f"{vn} != len({vn2})")
                for gp in cand_preds:
                    try:
                        if not bool(_safe_eval(gp, f_scope, rec["helpers"])):
                            continue
                        if any(bool(_safe_eval(gp, pr["scope"], rec["helpers"])) for pr in pass_recs):
                            continue
                        clean_gp = gp[5:-1] if gp.startswith("bool(") and gp.endswith(")") else gp
                        if clean_gp not in sep_guards:
                            sep_guards.append(clean_gp)
                    except Exception:
                        continue
                if sep_guards:
                    lines = src_txt.splitlines(True)
                    r_idx = rec["line"] - 1
                    indent = lines[r_idx][: len(lines[r_idx]) - len(lines[r_idx].lstrip())]
                    for gp in sep_guards[:3]:
                        for r_tmpl in raise_templates[:2]:
                            try:
                                _safe_eval(r_tmpl, f_scope, rec["helpers"])
                            except Exception:
                                if exp_exc in rec["helpers"] or exp_exc in BUILTINS_MAP:
                                    r_tmpl = f"{exp_exc}('Invalid input')"
                                else:
                                    continue
                            ins_line = f"{indent}if {gp}:\n{indent}    raise {r_tmpl}\n"
                            cand_src = "".join(lines[:r_idx] + [ins_line] + lines[r_idx:])
                            try:
                                ast.parse(cand_src)
                                _emit(
                                    rel_r,
                                    cand_src,
                                    f"Missing-exception separating guard L{rec['line']}: `if {gp}: raise {r_tmpl}`",
                                    prio=-2,
                                )
                            except SyntaxError:
                                pass

        # ------------------------------------------------------------------
        # FAMILY 4: Live-Frame Concrete Value, Equality/Hash & Quantifier Inversion
        # ------------------------------------------------------------------
        if mode not in ("eq", "regex", "elem_in_seq"):
            continue

        actual_top = w.get("actual")
        have_actual = bool(w.get("have_actual"))
        required_top = w.get("required_elem") if mode == "elem_in_seq" else w.get("required")

        yield_occurrences = {}
        indexed_records = []
        for rec in records:
            if rec["kind"] != "return":
                continue
            occ_key = (rec["rel_path"], rec["line"])
            occ_idx = yield_occurrences.get(occ_key, 0)
            yield_occurrences[occ_key] = occ_idx + 1
            indexed_records.append((occ_idx, rec))

        seen_site_keys = set()
        prioritized = []
        seq_len_delta = (
            len(required_top) - len(actual_top)
            if (
                have_actual
                and mode == "eq"
                and isinstance(actual_top, (list, tuple))
                and isinstance(required_top, (list, tuple))
            )
            else 0
        )

        for occ_idx, rec in indexed_records:
            skey = (rec["rel_path"], rec["line"], occ_idx)
            if skey in seen_site_keys:
                continue
            seen_site_keys.add(skey)
            rv = rec["value"]
            rank = 3
            target_req = required_top

            if (
                mode == "eq"
                and rec["func"] == "__eq__"
                and rv is False
                and not isinstance(required_top, bool)
            ):
                rank = 0
                target_req = True
            elif mode == "elem_in_seq":
                if type(rv) is bool:
                    rank = 1
                    target_req = not rv
                else:
                    rank = 1
                    target_req = required_top
            elif have_actual and _vals_equal(rv, actual_top, "eq"):
                rank = 0
                target_req = required_top
            elif (
                have_actual
                and isinstance(actual_top, (list, tuple))
                and isinstance(required_top, (list, tuple))
                and len(actual_top) == len(required_top)
                and occ_idx < len(actual_top)
                and _vals_equal(rv, actual_top[occ_idx], "eq")
                and not _vals_equal(actual_top[occ_idx], required_top[occ_idx], "eq")
            ):
                rank = 0
                target_req = required_top[occ_idx]
            elif seq_len_delta != 0 and type(rv) is bool:
                rank = 1
                target_req = True if (seq_len_delta > 0 and rv is False) else (False if (seq_len_delta < 0 and rv is True) else not rv)
            elif type(rv) is bool and not isinstance(required_top, bool):
                rank = 2
                target_req = not rv

            prioritized.append((rank, occ_idx, target_req, rec))

        prioritized.sort(key=lambda t: t[0])

        for rank, occ_idx, req_val, rec in prioritized[:28]:
            rel_path = rec["rel_path"]
            src_txt, tree = _get_file(rel_path)
            if tree is None:
                continue
            fn_node = _find_enclosing_func(tree, rec["line"])
            if fn_node is None:
                continue

            candidate_spans = []
            for nd in _walk_body(fn_node):
                if isinstance(nd, ast.Return) and nd.value is not None:
                    if nd.lineno <= rec["line"] <= getattr(nd, "end_lineno", nd.lineno):
                        candidate_spans.append(("return", nd.value))
                elif isinstance(nd, ast.Expr) and isinstance(nd.value, ast.Yield) and nd.value.value is not None:
                    if nd.lineno <= rec["line"] <= getattr(nd, "end_lineno", nd.lineno):
                        candidate_spans.append(("yield", nd.value.value))

            extra_assign_spans = []
            for skind, sp in candidate_spans:
                if isinstance(sp, ast.Name):
                    v_ret = sp.id
                    assigns = [
                        nd for nd in _walk_body(fn_node)
                        if isinstance(nd, ast.Assign)
                        and len(nd.targets) == 1
                        and isinstance(nd.targets[0], ast.Name)
                        and nd.targets[0].id == v_ret
                        and nd.lineno < rec["line"]
                    ]
                    if len(assigns) == 1:
                        extra_assign_spans.append(("assign", assigns[0].value))
            candidate_spans.extend(extra_assign_spans)
            if not candidate_spans:
                continue

            scope = rec["scope"]
            helpers = rec["helpers"]
            pass_recs = pass_records_by_site.get((rel_path, rec["line"], "return"), [])
            eval_mode = "regex" if mode == "regex" else "eq"

            # Place ALL bare local variable names FIRST before 1-hop object attributes so
            # late-assigned locals (e.g. `shortened_prospective`) are never pushed past slice caps!
            atoms = []
            atom_vals = {}
            for name, val in scope.items():
                atoms.append(name)
                atom_vals[name] = val
            for name, val in scope.items():
                if not isinstance(val, (int, float, bool, str, bytes, list, tuple, set, dict, type(None))):
                    try:
                        for ak in dir(val)[:45]:
                            if ak.startswith("_"):
                                continue
                            try:
                                av = getattr(val, ak)
                                if not callable(av):
                                    at_k = f"{name}.{ak}"
                                    atoms.append(at_k)
                                    atom_vals[at_k] = av
                            except Exception:
                                continue
                    except Exception:
                        pass
            atoms = list(dict.fromkeys(atoms))[:64]

            fn_int_consts = []
            fn_set_consts = []
            for cnd in _walk_body(fn_node):
                if isinstance(cnd, ast.Constant) and isinstance(cnd.value, int) and not isinstance(cnd.value, bool):
                    if cnd.value not in fn_int_consts:
                        fn_int_consts.append(cnd.value)
                elif isinstance(cnd, ast.Set):
                    s_src = ast.get_source_segment(src_txt, cnd) or ast.unparse(cnd)
                    if s_src not in fn_set_consts:
                        fn_set_consts.append(s_src)

            for skind, span in candidate_spans:
                existing_expr = (ast.get_source_segment(src_txt, span) or ast.unparse(span)).strip()
                if not existing_expr:
                    continue
                check_pass = (skind in ("return", "yield")) and len(pass_recs) > 0 and mode != "elem_in_seq"

                proposals = []

                def _try_expr(expr_s, label, hom_pair=None):
                    if len(proposals) >= 10 or expr_s == existing_expr:
                        return
                    try:
                        v_f = _safe_eval(expr_s, dict(scope), helpers)
                    except Exception:
                        return
                    if not _vals_equal(v_f, req_val, eval_mode):
                        return
                    if check_pass and not _passes_recorded_pass_frames(expr_s, pass_recs, helpers):
                        return
                    if all(p[0] != expr_s for p in proposals):
                        proposals.append((expr_s, label, hom_pair))

                # 4a. String Differential Morphism (`(actual_str -> req_str)`)
                cur_val = rec["value"]
                if isinstance(cur_val, str) and isinstance(req_val, str) and cur_val != req_val:
                    if len(cur_val) == len(req_val):
                        diffs = {(ca, cr) for ca, cr in zip(cur_val, req_val) if ca != cr}
                        if len(diffs) == 1:
                            ca, cr = next(iter(diffs))
                            base_s = existing_expr if "\n" not in existing_expr else f"({existing_expr})"
                            _try_expr(f"{base_s}.replace({ca!r}, {cr!r})", f"string char morphism `.replace({ca!r}, {cr!r})`")
                    for sm in ("strip()", "rstrip()", "lstrip()", "lower()", "upper()"):
                        base_s = existing_expr if "\n" not in existing_expr else f"({existing_expr})"
                        _try_expr(f"{base_s}.{sm}", f"string projection `.{sm}`")

                # 4b. Sub-expression homomorphism inside `__eq__` FIRST (highest specificity)
                if isinstance(req_val, bool) and fn_node.name == "__eq__" and len(fn_node.args.args) >= 2:
                    other_nm = fn_node.args.args[1].arg
                    self_attrs = [a[5:] for a in atoms if a.startswith("self.")]
                    for sattr in self_attrs:
                        s_tok = f"self.{sattr}"
                        o_tok = f"{other_nm}.{sattr}"
                        if s_tok in existing_expr and o_tok in existing_expr:
                            for hname, hfn in helpers.items():
                                if callable(hfn) and not inspect.isclass(hfn):
                                    proj_eq = existing_expr.replace(s_tok, f"{hname}({s_tok})").replace(o_tok, f"{hname}({o_tok})")
                                    _try_expr(
                                        proj_eq,
                                        f"`__eq__` canonical homomorphism `{hname}({s_tok})`",
                                        hom_pair=(s_tok, f"{hname}({s_tok})"),
                                    )
                            for sm in ("lower()", "casefold()", "strip()"):
                                proj_eq = existing_expr.replace(s_tok, f"{s_tok}.{sm}").replace(o_tok, f"{o_tok}.{sm}")
                                _try_expr(
                                    proj_eq,
                                    f"`__eq__` string homomorphism `{s_tok}.{sm}`",
                                    hom_pair=(s_tok, f"{s_tok}.{sm}"),
                                )

                # 4c. Existential / universal quantifiers over iterable scope variables + function set literals
                if isinstance(req_val, bool):
                    iter_atoms = [
                        at for at in atoms[:20]
                        if isinstance(atom_vals.get(at), (list, tuple, set, frozenset))
                    ]
                    rhs_containers = list(dict.fromkeys(iter_atoms + fn_set_consts))
                    for ia in iter_atoms:
                        for ib in rhs_containers:
                            if ia != ib:
                                _try_expr(f"any(_x in {ib} for _x in {ia})", f"existential membership `any(_x in {ib} for _x in {ia})`")
                                _try_expr(f"all(_x in {ib} for _x in {ia})", f"universal membership `all(_x in {ib} for _x in {ia})`")

                    # Same-type variable & prefix-slice equality (`a1 == a2`, `a1[:len(a2)] == a2`) BEFORE generic `<` / `!=`
                    for i_a, a1 in enumerate(atoms[:28]):
                        v1 = atom_vals.get(a1)
                        r1 = a1.split(".", 1)[0] if "." in a1 else ""
                        for a2 in atoms[i_a + 1 : 28]:
                            r2 = a2.split(".", 1)[0] if "." in a2 else ""
                            if r1 and r1 == r2:
                                continue
                            v2 = atom_vals.get(a2)
                            if type(v1) is type(v2) and not isinstance(v1, bool):
                                _try_expr(f"{a1} == {a2}", f"same-type equality `{a1} == {a2}`")
                                if isinstance(v1, (list, tuple)) and len(v1) != len(v2):
                                    if len(v1) > len(v2):
                                        _try_expr(f"{a1}[:len({a2})] == {a2}", f"prefix-slice equality `{a1}[:len({a2})] == {a2}`")
                                    else:
                                        _try_expr(f"{a2}[:len({a1})] == {a1}", f"prefix-slice equality `{a2}[:len({a1})] == {a1}`")

                    # Require `pass_recs` evidence before proposing lower-specificity `<` / `<=` / `!=` / boolean atoms
                    if len(pass_recs) >= 1:
                        for at in atoms:
                            if type(atom_vals.get(at)) is bool:
                                _try_expr(at, f"live-frame boolean `{at}`")
                        for i_a, a1 in enumerate(atoms[:20]):
                            v1 = atom_vals.get(a1)
                            for a2 in atoms[i_a + 1 : 20]:
                                v2 = atom_vals.get(a2)
                                if type(v1) is type(v2):
                                    for rop in ("!=", "<=", "<", ">=", ">"):
                                        _try_expr(f"{a1} {rop} {a2}", f"relational `{a1} {rop} {a2}`")
                            if isinstance(v1, (int, float)) and not isinstance(v1, bool):
                                for ic in fn_int_consts[:6]:
                                    for rop in ("==", "!=", "<=", "<", ">=", ">"):
                                        _try_expr(f"{a1} {rop} {ic}", f"bound `{a1} {rop} {ic}`")
                    else:
                        # Even with 0 pass_recs, integer constant bound checks on int variables are high-specificity
                        for a1 in atoms[:20]:
                            v1 = atom_vals.get(a1)
                            if isinstance(v1, int) and not isinstance(v1, bool):
                                for ic in fn_int_consts[:6]:
                                    for rop in ("==", "!=", "<=", "<", ">=", ">"):
                                        _try_expr(f"{a1} {rop} {ic}", f"bound `{a1} {rop} {ic}`")

                # 4d. Non-boolean direct atoms, pure helpers, arithmetic & sequence filtering
                if not isinstance(req_val, bool):
                    for at in atoms:
                        _try_expr(at, f"live-frame atom `{at}`")
                    for hname, hfn in helpers.items():
                        if callable(hfn) and not inspect.isclass(hfn):
                            for at in atoms[:16]:
                                _try_expr(f"{hname}({at})", f"module helper `{hname}({at})`")

                if isinstance(req_val, (int, float)) and not isinstance(req_val, bool):
                    for a1 in atoms[:14]:
                        for a2 in atoms[:14]:
                            if a1 != a2:
                                for bop in ("+", "-", "*", "//", "%"):
                                    _try_expr(f"{a1} {bop} {a2}", f"arithmetic `{a1} {bop} {a2}`")
                if isinstance(req_val, (list, tuple)):
                    ctor = "tuple" if isinstance(req_val, tuple) else ""
                    for a1 in atoms[:14]:
                        if ctor:
                            _try_expr(f"tuple(_x for _x in {a1} if _x)", f"filtered tuple `{a1}`")
                        else:
                            _try_expr(f"[_x for _x in {a1} if _x]", f"filtered list `{a1}`")

                for expr_s, label, hom_pair in proposals[:6]:
                    cand_src = _replace_span(src_txt, span, expr_s)
                    if cand_src:
                        if hom_pair is not None and fn_node.name == "__eq__":
                            cls_node = _find_enclosing_class(tree, fn_node.lineno)
                            if cls_node is not None:
                                old_tok, new_tok = hom_pair
                                cand_tree = ast.parse(cand_src)
                                cand_cls = _find_enclosing_class(cand_tree, fn_node.lineno)
                                if cand_cls is not None:
                                    for m_item in cand_cls.body:
                                        if isinstance(m_item, ast.FunctionDef) and m_item.name == "__hash__":
                                            for h_ret in _walk_body(m_item):
                                                if isinstance(h_ret, ast.Return) and h_ret.value is not None:
                                                    h_orig = ast.get_source_segment(cand_src, h_ret.value) or ast.unparse(h_ret.value)
                                                    if old_tok in h_orig and new_tok not in h_orig:
                                                        coupled = _replace_span(cand_src, h_ret.value, h_orig.replace(old_tok, new_tok))
                                                        if coupled:
                                                            _emit(
                                                                rel_path,
                                                                coupled,
                                                                f"Coupled `__eq__`+`__hash__` data-model homomorphism ({label})",
                                                                prio=-4,
                                                            )
                        _emit(
                            rel_path,
                            cand_src,
                            f"Live differential witness inversion ({label}) at L{span.lineno}",
                            prio=-3 if rank == 0 else -2,
                        )

    patches.sort(key=lambda d: d["prio"])
    return patches[:28]


base_fn_targets = list(dict.fromkeys(nid.split("[")[0] for nid in (pass_ids + fail_ids) if nid))
cli_targets = base_fn_targets if base_fn_targets else ([test_file] if test_file else [])
try:
    pytest.main(
        [*cli_targets, "-q", "--tb=short", "-p", "no:cacheprovider", "-o", "addopts=", "-W", "ignore"],
        plugins=[_WitnessPlugin()],
    )
except BaseException:
    pass

try:
    synthesized = _synthesize_patches()
except Exception:
    synthesized = []

payload_json = json.dumps(
    {
        "captures": len(fail_captures),
        "patches": synthesized,
    }
)
out_fd = cfg.get("out_fd")
if isinstance(out_fd, int) and out_fd >= 0:
    raw_out = payload_json.encode("utf-8")
    mv = memoryview(raw_out)
    sent = 0
    while sent < len(mv):
        sent += os.write(out_fd, mv[sent:])
else:
    out_path.write_text(payload_json, encoding="utf-8")
'''


_COMPILED_WITNESS_CODE = compile(_LIVE_DIFFERENTIAL_WITNESS_SCRIPT, "<brain_live_diff_witness>", "exec")


def synthesize_live_differential_witness_repairs_in_ram(
    cow_root: pathlib.Path,
    failing_tests: list[str],
    passing_tests: list[str],
    *,
    timeout_sec: float = 1.8,
) -> tuple[list[tuple[dict[str, str], str, str]], int]:
    """Zero-disk, zero-cold-start Copy-on-Write (`os.fork()`) live-frame witness inverter (~120-250 ms)."""
    clean_fails = [t for t in failing_tests if t and not t.startswith("<")][:2]
    if not clean_fails or not hasattr(os, "fork") or threading.active_count() > 1:
        return [], 0
    try:
        import pytest as _preloaded_pytest  # noqa: F401
    except Exception:
        return [], 0

    clean_passes = _select_sibling_passing_tests(clean_fails, passing_tests, limit=8)
    test_file = clean_fails[0].split("::")[0] if "::" in clean_fails[0] else ""
    root_abs = cow_root.resolve()

    r_fd, w_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(r_fd)
        try:
            signal.setitimer(signal.ITIMER_REAL, max(0.5, timeout_sec))
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, 1)
            os.dup2(devnull, 2)
            os.close(devnull)
            os.chdir(str(root_abs))
            # Evict any cached repo/test modules before running targeted witness capture
            search_bases = [root_abs / "src", root_abs] if (root_abs / "src").is_dir() else [root_abs]
            pkg_roots = {
                e.stem if e.is_file() else e.name
                for b in search_bases
                if b.is_dir()
                for e in b.iterdir()
                if not e.name.startswith((".", "docs", "build", "dist"))
                and ((e.is_dir() and (e / "__init__.py").is_file()) or (e.is_file() and e.suffix == ".py"))
            }
            pkg_prefixes = tuple(sorted(pkg_roots)) + ("tests", "test_", "conftest")
            for m_k in [k for k in list(sys.modules) if k in pkg_prefixes or k.startswith(tuple(f"{p}." for p in pkg_prefixes))]:
                sys.modules.pop(m_k, None)
            if (root_abs / "src").is_dir():
                if str(root_abs) not in sys.path:
                    sys.path.insert(0, str(root_abs))
                if str(root_abs / "src") not in sys.path:
                    sys.path.insert(0, str(root_abs / "src"))
            elif str(root_abs) not in sys.path:
                sys.path.insert(0, str(root_abs))
            importlib.invalidate_caches()
            os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
            cfg_payload = json.dumps(
                {
                    "cow_root": str(root_abs),
                    "test_file": test_file,
                    "fail_ids": clean_fails,
                    "pass_ids": clean_passes,
                    "out_path": "",
                    "out_fd": w_fd,
                    "max_records": 240,
                    "max_events": 30000,
                }
            )
            sys.argv = ["_brain_live_diff_witness_ram", cfg_payload]
            ns_exec: dict[str, Any] = {"__name__": "__main__"}
            exec(_COMPILED_WITNESS_CODE, ns_exec)  # noqa: S102 -- confined CoW witness child
        except BaseException:
            pass
        finally:
            try:
                signal.setitimer(signal.ITIMER_REAL, 0.0)
                os.close(w_fd)
            except OSError:
                pass
            os._exit(0)

    os.close(w_fd)
    chunks: list[bytes] = []
    deadline = time.perf_counter() + timeout_sec + 0.35
    eof = False
    reaped = False
    while not (eof and reaped):
        rem = deadline - time.perf_counter()
        if rem <= 0:
            try:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            except OSError:
                pass
            try:
                os.close(r_fd)
            except OSError:
                pass
            return [], 0
        if not eof:
            ready, _, _ = select.select([r_fd], [], [], min(0.015, rem))
            if ready:
                try:
                    blk = os.read(r_fd, 65536)
                except OSError:
                    blk = b""
                if blk:
                    chunks.append(blk)
                else:
                    eof = True
        if not reaped:
            try:
                wp, _ = os.waitpid(pid, os.WNOHANG)
                if wp == pid:
                    reaped = True
            except ChildProcessError:
                reaped = True
        if eof and not reaped:
            time.sleep(0.0005)
    try:
        os.close(r_fd)
    except OSError:
        pass
    try:
        data = json.loads(b"".join(chunks).decode("utf-8") or "{}")
    except Exception:
        return [], 0
    raw_patches = data.get("patches") or []
    results: list[tuple[dict[str, str], str, str]] = []
    for item in raw_patches:
        rel_p = str(item.get("rel_path") or "")
        p_src = str(item.get("patched_src") or "")
        desc = str(item.get("description") or "Live differential witness inversion")
        if rel_p and p_src:
            results.append(({rel_p: p_src}, "COGS_LIVE_DIFFERENTIAL_WITNESS_INVERSION", desc))
    return results, len(results)


def _select_sibling_passing_tests(failing_tests: list[str], passing_tests: list[str], limit: int = 8) -> list[str]:
    """Select diverse sibling passing tests from the same test function/class (strided across
    both positive and negative parametrized cases so tautologies are refuted in memory)."""
    clean_p = [t for t in passing_tests if t and not t.startswith("<")]
    if not failing_tests or not clean_p:
        return clean_p[:limit]
    f0 = failing_tests[0]
    func_prefix = f0.split("[")[0]
    cls_prefix = f0.rsplit("::", 1)[0] if "::" in f0 else ""

    same_fn = [p for p in clean_p if p.split("[")[0] == func_prefix]
    if len(same_fn) > limit:
        # Ensure both `True` and `False` parametrized siblings are represented when available
        neg_sibs = [p for p in same_fn if "False]" in p or "-False-" in p]
        pos_sibs = [p for p in same_fn if p not in set(neg_sibs)]
        chosen: list[str] = []
        if neg_sibs and pos_sibs:
            half = max(1, limit // 2)
            s_neg = max(1, len(neg_sibs) // half)
            s_pos = max(1, len(pos_sibs) // (limit - half))
            chosen.extend(neg_sibs[::s_neg][:half])
            chosen.extend(pos_sibs[::s_pos][: limit - len(chosen)])
            return chosen[:limit]
        stride = max(1, len(same_fn) // limit)
        return same_fn[::stride][:limit]

    def _key(p: str) -> tuple[int, int]:
        if p.split("[")[0] == func_prefix:
            return (0, len(p))
        if cls_prefix and p.startswith(cls_prefix + "::"):
            return (1, len(p))
        return (2, len(p))

    return sorted(clean_p, key=_key)[:limit]


def synthesize_live_differential_witness_repairs(
    *,
    cow_root: pathlib.Path,
    pycache_dir: pathlib.Path,
    py_exe: str,
    py_env: dict[str, str],
    top_rel_files: list[str],
    failing_tests: list[str],
    passing_tests: list[str],
    timeout_sec: float = 14.0,
) -> tuple[list[tuple[dict[str, str], str, str]], int]:
    """Run one bounded live-frame witness capture inside `cow_root` and return
    `(list_of_(file_patches, mechanism, description), in_memory_candidates_count)`."""
    clean_fails = [t for t in failing_tests if t and not t.startswith("<")][:2]
    if not clean_fails:
        return [], 0
    clean_passes = _select_sibling_passing_tests(clean_fails, passing_tests, limit=8)
    test_file = clean_fails[0].split("::")[0] if "::" in clean_fails[0] else ""

    script_file = pycache_dir / "_brain_live_diff_witness.py"
    out_file = pycache_dir / "_brain_live_diff_witness_out.json"
    if out_file.exists():
        out_file.unlink()
    script_file.write_text(_LIVE_DIFFERENTIAL_WITNESS_SCRIPT, encoding="utf-8")

    cfg_payload = json.dumps(
        {
            "cow_root": str(cow_root),
            "test_file": test_file,
            "fail_ids": clean_fails,
            "pass_ids": clean_passes,
            "out_path": str(out_file),
            "max_records": 260,
            "max_events": 35000,
        }
    )

    p_obj = subprocess.Popen(
        [py_exe, str(script_file), cfg_payload],
        cwd=cow_root,
        env=py_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        p_obj.communicate(timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p_obj.pid, signal.SIGKILL)
        except OSError:
            p_obj.kill()
        p_obj.communicate()
        return [], 0

    if not out_file.exists():
        return [], 0
    try:
        data = json.loads(out_file.read_text(encoding="utf-8"))
    except Exception:
        return [], 0

    raw_patches = data.get("patches") or []
    results: list[tuple[dict[str, str], str, str]] = []
    for item in raw_patches:
        rel_p = str(item.get("rel_path") or "")
        p_src = str(item.get("patched_src") or "")
        desc = str(item.get("description") or "Live differential witness inversion")
        if rel_p and p_src:
            results.append(({rel_p: p_src}, "COGS_LIVE_DIFFERENTIAL_WITNESS_INVERSION", desc))
    return results, len(results)
