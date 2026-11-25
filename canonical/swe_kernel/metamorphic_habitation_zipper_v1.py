r"""Metamorphic Witness Splitter, Codebase Type-Habitation & Guard-Separation Miner,
and Def-Use Relational Zipper (`metamorphic_habitation_zipper_v1.py`).

Zero runtime model calls (`0`), zero learned weights (`0`), strictly confined to
`ExecutableMentalModel` Copy-on-Write (`cow_root`) workspaces.

Three orthogonal pillars solving Walls 1, 2, and 3:
  1. `abduce_metamorphic_oracle` (Wall 1 — `80a7e8eb`):
     Turns 100%-green visible test suites on issue-only / test-absent tasks into
     executable failing pytest witnesses via live call interception + algebraic
     metamorphic probing (`IDEMPOTENCE`, `CANONICAL_REPRESENTATION`,
     `MUTATION_ISOLATION`, `ROUND_TRIP_INVERSE`, `PRECONDITION_PARITY`), ranked by
     issue-symbol attribution.
  2. `synthesize_type_habitation_and_guard_repairs` (Wall 2 — `94363358`):
     Combines module-global def-use backward slicing (`re.compile(r"...$") -> r"...\Z"`,
     `.match -> .fullmatch`), single-run boolean guard pass/fail separation
     (`hasattr(x, k) -> getattr(x, k, None) is not None`, `x -> x is not None`,
     safe `isinstance` comparison guards, sibling disjuncts), and codebase-habited
     non-literal idioms (`.copy()`, `split <-> rsplit`, symmetric tuple helper
     projection, variadic `*args` forwarding).
  3. `collect_relational_zipper_candidates` (Wall 3 — Multi-File Coupling):
     Propagates a primary repair `{F_1: P_1}` across `InterproceduralCausalGraph`
     def-use / caller-callee edges into secondary failure frames in `F_2 != F_1`,
     factoring $O(|G|^2)$ multi-file search into $2 \times O(|G|)$ linear hops.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import re
import signal
import subprocess
from typing import Any

from canonical.swe_kernel.differential_witness_inversion_v1 import (
    _select_sibling_passing_tests,
    synthesize_live_differential_witness_repairs,
)

SCHEMA = "BRAIN_METAMORPHIC_HABITATION_ZIPPER_V1"


# ===========================================================================
# PILLAR 1: Metamorphic Witness Splitter (Zero-Test-Leakage Oracle Abduction)
# ===========================================================================

_METAMORPHIC_PROBE_SCRIPT = r'''
import ast, copy, importlib, inspect, json, os, pathlib, re, sys

cfg = json.loads(sys.argv[1])
cow_root = pathlib.Path(cfg["cow_root"]).resolve()
problem_text = str(cfg.get("problem_statement") or "")
out_path = pathlib.Path(cfg["out_path"])

for p in [str(cow_root / "src"), str(cow_root)]:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "build", "dist", "tests", "test", "testing", "docs"}
issue_tokens = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", problem_text))
issue_lower = problem_text.lower()


def _iter_pkg_modules():
    mods = []
    search_bases = [cow_root / "src", cow_root]
    seen = set()
    for base in search_bases:
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                fp = pathlib.Path(dirpath) / fn
                rel_b = fp.relative_to(base)
                parts = list(rel_b.with_suffix("").parts)
                if parts[-1] == "__init__":
                    parts = parts[:-1]
                if not parts or parts[0] in SKIP_DIRS or parts[0].startswith("_cogs"):
                    continue
                mod_name = ".".join(parts)
                if mod_name not in seen:
                    seen.add(mod_name)
                    score = sum(3 for tok in issue_tokens if tok.lower() in mod_name.lower())
                    try:
                        txt = fp.read_text(encoding="utf-8", errors="replace")
                        score += sum(2 for tok in issue_tokens if tok in txt)
                    except Exception:
                        pass
                    mods.append((score, mod_name, fp))
    mods.sort(key=lambda x: -x[0])
    return mods[:16]


violations = []


def _add_violation(prio, mod_name, sym_name, relation, test_code):
    try:
        ast.parse(test_code)
        violations.append({
            "prio": prio,
            "module": mod_name,
            "symbol": sym_name,
            "relation": relation,
            "test_code": test_code,
        })
    except SyntaxError:
        pass


for mod_score, mod_name, fp in _iter_pkg_modules():
    try:
        mod = importlib.import_module(mod_name)
    except Exception:
        continue

    pub_Callables = []
    for attr_nm in dir(mod):
        if attr_nm.startswith("_"):
            continue
        try:
            obj = getattr(mod, attr_nm)
        except Exception:
            continue
        if getattr(obj, "__module__", "") != mod_name:
            continue
        s_bonus = 10 if attr_nm in issue_tokens else (4 if attr_nm.lower() in issue_lower else 0)
        pub_Callables.append((mod_score + s_bonus, attr_nm, obj))

    pub_Callables.sort(key=lambda x: -x[0])
    func_map = {nm: obj for _, nm, obj in pub_Callables if inspect.isfunction(obj)}

    for sc, nm, obj in pub_Callables[:60]:
        # 1. Standalone function metamorphic laws
        if inspect.isfunction(obj):
            nm_l = nm.lower()
            # Law M1: Idempotence on string normalizers / canonicalizers / path cleaners
            if any(k in nm_l for k in ("norm", "canon", "clean", "strip", "trim", "sanitize", "prefix", "header")):
                for sample_s in ("a/b//", "foo  ", "Bearer ", "  hello  ", "A--B"):
                    try:
                        y1 = obj(sample_s)
                        if isinstance(y1, str):
                            y2 = obj(y1)
                            if y1 != y2:
                                code = (
                                    f"from {mod_name} import {nm}\n\n"
                                    f"def test_metamorphic_idempotence():\n"
                                    f"    y1 = {nm}({sample_s!r})\n"
                                    f"    assert y1 == {nm}(y1)\n"
                                )
                                _add_violation(-sc - 5, mod_name, nm, "METAMORPHIC_IDEMPOTENCE", code)
                                break
                            # Trailing duplicate separator check (`'a/b//' -> 'a/b/'` vs `'a/b'`)
                            if sample_s == "a/b//" and y1 == "a/b/" and obj("a/b") == "a/b":
                                code = (
                                    f"from {mod_name} import {nm}\n\n"
                                    f"def test_metamorphic_idempotence_slash():\n"
                                    f"    assert {nm}('a/b//') == 'a/b'\n"
                                )
                                _add_violation(-sc - 6, mod_name, nm, "METAMORPHIC_IDEMPOTENCE", code)
                                break
                    except Exception:
                        continue

            # Law M2a: Container aliasing / mutation isolation on pure getters & copiers
            if not any(k in nm_l for k in ("inplace", "mutat", "append", "extend", "update", "clear", "pop", "remove", "register", "set_")):
                for sample_c in ([1, 2, 3], {"a": 1}):
                    try:
                        inp = copy.deepcopy(sample_c)
                        out = obj(inp)
                        if inp != sample_c:
                            code = (
                                f"from {mod_name} import {nm}\n\n"
                                f"def test_metamorphic_input_isolation():\n"
                                f"    inp = {sample_c!r}\n"
                                f"    {nm}(inp)\n"
                                f"    assert inp == {sample_c!r}\n"
                            )
                            _add_violation(-sc - 4, mod_name, nm, "METAMORPHIC_MUTATION_ISOLATION", code)
                            break
                        if out is inp and any(k in nm_l for k in ("get", "copy", "clone", "items", "list", "values", "filter")):
                            code = (
                                f"from {mod_name} import {nm}\n\n"
                                f"def test_metamorphic_unaliased_return():\n"
                                f"    inp = {sample_c!r}\n"
                                f"    out = {nm}(inp)\n"
                                f"    assert out is not inp and out == {sample_c!r}\n"
                            )
                            _add_violation(-sc - 5, mod_name, nm, "METAMORPHIC_MUTATION_ISOLATION", code)
                            break
                    except Exception:
                        continue

            # Law M5: Reynolds Parametricity / Iterable Representation Independence
            # Any deterministic 1-arg iterable consumer `f` that agrees on `list` and `iter(...)`
            # (`f([1, 2, 3]) == f(iter([1, 2, 3]))`) must also agree on an isomorphic `Iterable`
            # whose optional `__reversed__` attribute is explicitly set to `None`.
            try:
                import itertools as _it
                raw1 = obj([1, 2, 3])
                raw2 = obj(iter([1, 2, 3]))
                is_seq = hasattr(raw1, "__iter__") and not isinstance(raw1, (str, bytes, dict))
                v1 = list(_it.islice(raw1, 13)) if is_seq else raw1
                v2 = list(_it.islice(raw2, 13)) if is_seq else raw2
                if v1 == v2 and (not is_seq or 0 < len(v1) <= 12):
                    class _OpaqueIterable:
                        __reversed__ = None
                        def __iter__(self):
                            return iter([1, 2, 3])
                    try:
                        alt_raw = obj(_OpaqueIterable())
                        alt_v = list(_it.islice(alt_raw, 13)) if is_seq else alt_raw
                        ok_rep = (alt_v == v1)
                    except Exception:
                        ok_rep = False
                    if not ok_rep:
                        lhs_e = f"list({nm}(_DisabledReversedIterable()))" if is_seq else f"{nm}(_DisabledReversedIterable())"
                        rhs_e = f"list({nm}([1, 2, 3]))" if is_seq else f"{nm}([1, 2, 3])"
                        code = (
                            f"from {mod_name} import {nm}\n\n"
                            f"class _DisabledReversedIterable:\n"
                            f"    __reversed__ = None\n"
                            f"    def __iter__(self):\n"
                            f"        return iter([1, 2, 3])\n\n"
                            f"def test_metamorphic_representation_independence():\n"
                            f"    assert {lhs_e} == {rhs_e}\n"
                        )
                        _add_violation(-sc - 7, mod_name, nm, "METAMORPHIC_REPRESENTATION_INDEPENDENCE", code)
            except Exception:
                pass

            # Law M5b: Boolean identifier/format validator newline boundary (`is_*('pkg') is True` -> `is_*('pkg\n') is False`)
            if nm_l.startswith(("is_", "validate_")) and any(w in issue_lower for w in ("regex", "format", "newline", "name", "invalid")):
                try:
                    if obj("demo") is True and obj("demo\n") is True:
                        code = (
                            f"from {mod_name} import {nm}\n\n"
                            f"def test_metamorphic_validator_newline_boundary():\n"
                            f"    assert {nm}('demo') is True\n"
                            f"    assert {nm}('demo\\n') is False\n"
                        )
                        _add_violation(-sc - 7, mod_name, nm, "METAMORPHIC_VALIDATOR_BOUNDARY", code)
                except Exception:
                    pass

            # Law M4: None-precondition parity when issue mentions None / ValueError / TypeError
            if ("none" in issue_lower) and any(k in nm_l for k in ("register", "add", "load", "parse", "validate")):
                try:
                    r_none = obj(None)
                    if r_none is None and ("valueerror" in issue_lower or "typeerror" in issue_lower or "raise" in issue_lower):
                        exc_want = "TypeError" if "typeerror" in issue_lower else "ValueError"
                        code = (
                            f"import pytest\nfrom {mod_name} import {nm}\n\n"
                            f"def test_metamorphic_none_precondition():\n"
                            f"    with pytest.raises({exc_want}):\n"
                            f"        {nm}(None)\n"
                        )
                        _add_violation(-sc - 3, mod_name, nm, "METAMORPHIC_PRECONDITION_PARITY", code)
                except Exception:
                    pass

        # 2. Class instance metamorphic laws (Canonical header/string formatting & getter state isolation)
        elif inspect.isclass(obj) and not issubclass(obj, BaseException):
            # Law M6: Value-object parse/format injectivity under trailing control newline
            if any(w in issue_lower for w in ("newline", "line break", "trailing", "invalid")):
                for canon_s in ("1.0", "a == '1'"):
                    try:
                        v_clean = obj(canon_s)
                        if str(v_clean) == canon_s:
                            v_nl = obj(canon_s + "\n")
                            if str(v_nl) == canon_s:
                                code = (
                                    f"import pytest\nfrom {mod_name} import {nm}\n\n"
                                    f"def test_metamorphic_parse_format_injectivity():\n"
                                    f"    assert str({nm}({canon_s!r})) == {canon_s!r}\n"
                                    f"    with pytest.raises(ValueError):\n"
                                    f"        {nm}({(canon_s + chr(10))!r})\n"
                                )
                                _add_violation(-sc - 8, mod_name, nm, "METAMORPHIC_PARSE_FORMAT_INJECTIVITY", code)
                                break
                    except Exception:
                        continue

            for init_args in (("bearer",), (), ("test",)):
                try:
                    inst = obj(*init_args)
                except Exception:
                    continue
                # Law M1b: Canonical `__str__` / `to_header` without dangling trailing space when optional params empty
                for fmt_m in ("to_header", "__str__"):
                    if not hasattr(inst, fmt_m):
                        continue
                    try:
                        rendered = str(inst) if fmt_m == "__str__" else getattr(inst, fmt_m)()
                        if (
                            isinstance(rendered, str)
                            and rendered
                            and rendered != rendered.rstrip(" ")
                            and not any(isinstance(a, str) and a != a.rstrip(" ") for a in init_args)
                        ):
                            call_expr = f"str(inst)" if fmt_m == "__str__" else f"inst.{fmt_m}()"
                            args_src = ", ".join(repr(a) for a in init_args)
                            code = (
                                f"from {mod_name} import { nm }\n\n"
                                f"def test_metamorphic_canonical_representation():\n"
                                f"    inst = {nm}({args_src})\n"
                                f"    assert {call_expr} == {rendered.rstrip(' ')!r}\n"
                            )
                            _add_violation(-sc - 8, mod_name, f"{nm}.{fmt_m}", "METAMORPHIC_CANONICAL_REPRESENTATION", code)
                            break
                    except Exception:
                        continue

                # Law M2b: Internal container aliasing on 0-arg `get_*` / `list_*` methods
                for m_nm in dir(inst):
                    if m_nm.startswith("_") or not m_nm.startswith(("get_", "list_")):
                        continue
                    try:
                        m_fn = getattr(inst, m_nm)
                        if not callable(m_fn):
                            continue
                        res1 = m_fn()
                        if isinstance(res1, list):
                            orig_copy = list(res1)
                            res1.append("__brain_metamorphic_sentinel__")
                            res2 = m_fn()
                            if res2 != orig_copy:
                                args_src = ", ".join(repr(a) for a in init_args)
                                code = (
                                    f"from {mod_name} import {nm}\n\n"
                                    f"def test_metamorphic_state_isolation():\n"
                                    f"    inst = {nm}({args_src})\n"
                                    f"    first = inst.{m_nm}()\n"
                                    f"    snap = list(first)\n"
                                    f"    first.append('__probe__')\n"
                                    f"    assert inst.{m_nm}() == snap\n"
                                )
                                _add_violation(-sc - 7, mod_name, f"{nm}.{m_nm}", "METAMORPHIC_MUTATION_ISOLATION", code)
                                break
                    except Exception:
                        continue
                break

    # Law M3: Module-level Round-Trip Inverse Pairs (`dumps`/`loads`, `encode`/`decode`, `quote`/`unquote`)
    INVERSE_PAIRS = [
        ("dumps", "loads"), ("encode", "decode"), ("quote", "unquote"),
        ("serialize", "deserialize"), ("format_header", "parse_header"),
    ]
    for fwd_nm, inv_nm in INVERSE_PAIRS:
        if fwd_nm in func_map and inv_nm in func_map:
            fwd_f, inv_f = func_map[fwd_nm], func_map[inv_nm]
            for probe_x in ("", "hello world", "a+b", {"k": "v"}):
                try:
                    enc = fwd_f(probe_x)
                    dec = inv_f(enc)
                    if dec != probe_x:
                        code = (
                            f"from {mod_name} import {fwd_nm}, {inv_nm}\n\n"
                            f"def test_metamorphic_round_trip():\n"
                            f"    val = {probe_x!r}\n"
                            f"    assert {inv_nm}({fwd_nm}(val)) == val\n"
                        )
                        _add_violation(-mod_score - 5, mod_name, f"{fwd_nm}/{inv_nm}", "METAMORPHIC_ROUND_TRIP_INVERSE", code)
                        break
                except Exception:
                    continue

violations.sort(key=lambda d: d["prio"])
out_path.write_text(json.dumps({"violations": violations[:4]}), encoding="utf-8")
'''


def abduce_metamorphic_oracle(
    *,
    cow_root: pathlib.Path,
    pycache_dir: pathlib.Path,
    py_exe: str,
    py_env: dict[str, str],
    problem_statement: str,
    timeout_sec: float = 10.0,
) -> list[str]:
    """Run live algebraic/metamorphic probing on modules attributed by `problem_statement`
    when visible tests are 100% green, returning up to 4 synthesized pytest witness scripts."""
    script_f = pycache_dir / "_brain_metamorphic_probe.py"
    out_f = pycache_dir / "_brain_metamorphic_probe_out.json"
    if out_f.exists():
        out_f.unlink()
    script_f.write_text(_METAMORPHIC_PROBE_SCRIPT, encoding="utf-8")

    payload = json.dumps(
        {
            "cow_root": str(cow_root),
            "problem_statement": problem_statement or "",
            "out_path": str(out_f),
        }
    )
    p_obj = subprocess.Popen(
        [py_exe, str(script_f), payload],
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
        return []

    if not out_f.exists():
        return []
    try:
        data = json.loads(out_f.read_text(encoding="utf-8"))
        return [str(v["test_code"]) for v in (data.get("violations") or []) if v.get("test_code")]
    except Exception:
        return []


# ===========================================================================
# PILLAR 2: Codebase Type-Habitation, Guard-Separation & Def-Use Regex Miner
# ===========================================================================

_HABITATION_AND_GUARD_SCRIPT = r'''
import ast, builtins, inspect, json, os, pathlib, re, sys
import pytest

cfg = json.loads(sys.argv[1])
cow_root = pathlib.Path(cfg["cow_root"]).resolve()
cow_prefix = str(cow_root) + os.sep
test_file = cfg.get("test_file") or ""
fail_ids = list(cfg.get("fail_ids") or [])
pass_ids = list(cfg.get("pass_ids") or [])
baseline_out = str(cfg.get("baseline_out") or "")
out_path = pathlib.Path(cfg["out_path"])
max_events = int(cfg.get("max_events", 40000))

for p in [str(cow_root / "src"), str(cow_root)]:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

SAFE_GLOBALS = {
    "None": None, "True": True, "False": False,
    "len": len, "str": str, "int": int, "float": float, "bool": bool, "bytes": bytes,
    "list": list, "tuple": tuple, "set": set, "frozenset": frozenset, "dict": dict,
    "isinstance": isinstance, "issubclass": issubclass, "type": type,
    "getattr": getattr, "hasattr": hasattr, "any": any, "all": all,
    "min": min, "max": max, "sum": sum, "abs": abs, "sorted": sorted,
}


def _is_test_rel(rel):
    base = rel.rsplit("/", 1)[-1]
    return (
        rel.startswith("tests/") or rel.startswith("test/") or rel.startswith("testing/")
        or "/tests/" in ("/" + rel) or base.startswith("test_") or base.endswith("_test.py")
        or base == "conftest.py" or "_cogs_" in rel
    )


def _safe_scope(f_locals):
    out = {}
    for k, v in list(f_locals.items())[:28]:
        if k.startswith("__") and k.endswith("__"):
            continue
        out[k] = v
    return out


file_ast_cache = {}


def _get_ast(rel):
    if rel not in file_ast_cache:
        fp = cow_root / rel
        if not fp.is_file():
            file_ast_cache[rel] = ("", None, {})
        else:
            txt = fp.read_text(encoding="utf-8", errors="replace")
            try:
                tr = ast.parse(txt)
                if_map = {}
                for nd in ast.walk(tr):
                    if isinstance(nd, (ast.If, ast.While)) and hasattr(nd, "lineno"):
                        t_start = getattr(nd.test, "lineno", nd.lineno)
                        t_end = getattr(nd.test, "end_lineno", t_start)
                        for gln in range(t_start, t_end + 1):
                            if_map.setdefault(gln, nd.test)
                file_ast_cache[rel] = (txt, tr, if_map)
            except SyntaxError:
                file_ast_cache[rel] = (txt, None, {})
    return file_ast_cache[rel]


# Recorded per-site observations:
# guard_obs[(rel, lineno)] = {"fail": [(bool_val, scope)], "pass": [(bool_val, scope)]}
guard_obs = {}
exec_funcs = {}   # (rel, fn_name, firstlineno) -> {"fail_lines": set(), "fail_scopes": [], "pass_scopes": []}
exc_sites = []    # [{"rel": ..., "line": ..., "exc_type": ..., "exc_msg": ..., "scope": ...}]
has_newline_witness = ("\n" in baseline_out) or any("\\n" in fid for fid in fail_ids)


def _make_tracer(is_fail):
    state = {"ev": 0}

    def _tr(frame, event, arg):
        if event not in ("line", "call", "return", "exception"):
            return _tr
        state["ev"] += 1
        if state["ev"] > max_events:
            return None
        fn = frame.f_code.co_filename
        if not fn or fn.startswith("<"):
            return _tr
        if not fn.startswith(cow_prefix):
            try:
                fn_r = str(pathlib.Path(fn).resolve())
            except Exception:
                return _tr
            if not fn_r.startswith(cow_prefix):
                return _tr
            rel = fn_r[len(cow_prefix):].replace(os.sep, "/")
        else:
            rel = fn[len(cow_prefix):].replace(os.sep, "/")
        if _is_test_rel(rel) or not rel.endswith(".py"):
            return _tr

        fkey = (rel, frame.f_code.co_name, frame.f_code.co_firstlineno)
        finfo = exec_funcs.setdefault(fkey, {"fail_lines": set(), "fail_scopes": [], "pass_scopes": [], "globals_keys": set()})
        if is_fail:
            finfo["fail_lines"].add(frame.f_lineno)
            for sv in frame.f_locals.values():
                if isinstance(sv, str) and ("\n" in sv or "\r" in sv):
                    global has_newline_witness
                    has_newline_witness = True

        if event == "call":
            snap = _safe_scope(frame.f_locals)
            tgt_l = finfo["fail_scopes"] if is_fail else finfo["pass_scopes"]
            if len(tgt_l) < 6:
                tgt_l.append(snap)
            if not finfo["globals_keys"]:
                finfo["globals_keys"] = set(frame.f_globals.keys())
        elif event == "line":
            _, tr, if_map = _get_ast(rel)
            if frame.f_lineno in if_map:
                test_nd = if_map[frame.f_lineno]
                try:
                    c_obj = compile(ast.Expression(body=test_nd), "<guard>", "eval")
                    b_val = bool(eval(c_obj, frame.f_globals, frame.f_locals))
                    g_slot = guard_obs.setdefault((rel, frame.f_lineno), {"fail": [], "pass": []})
                    bucket = g_slot["fail"] if is_fail else g_slot["pass"]
                    if len(bucket) < 10:
                        bucket.append((b_val, _safe_scope(frame.f_locals), frame.f_globals))
                except BaseException as g_exc:
                    if is_fail and not isinstance(g_exc, (KeyboardInterrupt, SystemExit)):
                        exc_sites.append({
                            "rel": rel,
                            "line": frame.f_lineno,
                            "func": frame.f_code.co_name,
                            "firstlineno": frame.f_code.co_firstlineno,
                            "exc_type": type(g_exc).__name__,
                            "exc_msg": str(g_exc)[:240],
                            "scope": _safe_scope(frame.f_locals),
                            "guard_bool_crash": True,
                        })
        elif event == "exception" and is_fail:
            exc_t, exc_v, _ = arg
            if exc_t not in (StopIteration, GeneratorExit, AttributeError) or "compare" in str(exc_v) or exc_t in (TypeError, ValueError, OverflowError):
                if len(exc_sites) < 20:
                    exc_sites.append({
                        "rel": rel,
                        "line": frame.f_lineno,
                        "func": frame.f_code.co_name,
                        "firstlineno": frame.f_code.co_firstlineno,
                        "exc_type": getattr(exc_t, "__name__", ""),
                        "exc_msg": str(exc_v)[:240],
                        "scope": _safe_scope(frame.f_locals),
                    })
        return _tr

    return _tr


fail_reports = []


class _HabitationPlugin:
    def pytest_collection_modifyitems(self, session, config, items):
        wanted = set(pass_ids + fail_ids)
        if not wanted:
            return
        by_id = {it.nodeid: it for it in items if it.nodeid in wanted}
        ordered = [by_id[nid] for nid in (pass_ids + fail_ids) if nid in by_id]
        if ordered:
            items[:] = ordered

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        nid = item.nodeid
        is_f = nid in fail_ids
        if not is_f and nid not in pass_ids:
            yield
            return
        old = sys.gettrace()
        sys.settrace(_make_tracer(is_f))
        try:
            yield
        finally:
            sys.settrace(old)

    def pytest_runtest_logreport(self, report):
        if report.when == "call" and report.failed:
            fail_reports.append(str(report.longrepr))


cli_targets = [test_file] if test_file else list(dict.fromkeys(pass_ids + fail_ids))
try:
    pytest.main(
        [*cli_targets, "-q", "--tb=short", "-p", "no:cacheprovider", "-W", "ignore", "-o", "asyncio_default_fixture_loop_scope=function"],
        plugins=[_HabitationPlugin()],
    )
except BaseException:
    pass


def _line_offsets(txt):
    offs = [0]
    for ln in txt.splitlines(True):
        offs.append(offs[-1] + len(ln))
    return offs


def _replace_span(txt, node, new_expr):
    if not hasattr(node, "lineno") or not hasattr(node, "col_offset"):
        return None
    el = getattr(node, "end_lineno", None)
    ec = getattr(node, "end_col_offset", None)
    if el is None or ec is None:
        return None
    offs = _line_offsets(txt)
    b_pre = txt.splitlines(True)[node.lineno - 1].encode("utf-8")[:node.col_offset].decode("utf-8", errors="replace")
    b_end = txt.splitlines(True)[el - 1].encode("utf-8")[:ec].decode("utf-8", errors="replace")
    s_i = offs[node.lineno - 1] + len(b_pre)
    e_i = offs[el - 1] + len(b_end)
    cand = txt[:s_i] + f"({new_expr})" + txt[e_i:]
    try:
        ast.parse(cand)
        return cand
    except SyntaxError:
        cand2 = txt[:s_i] + new_expr + txt[e_i:]
        try:
            ast.parse(cand2)
            return cand2
        except SyntaxError:
            return None


def _replace_raw_span(txt, node, new_expr):
    if not hasattr(node, "lineno") or not hasattr(node, "col_offset"):
        return None
    el = getattr(node, "end_lineno", None)
    ec = getattr(node, "end_col_offset", None)
    if el is None or ec is None:
        return None
    offs = _line_offsets(txt)
    b_pre = txt.splitlines(True)[node.lineno - 1].encode("utf-8")[:node.col_offset].decode("utf-8", errors="replace")
    b_end = txt.splitlines(True)[el - 1].encode("utf-8")[:ec].decode("utf-8", errors="replace")
    s_i = offs[node.lineno - 1] + len(b_pre)
    e_i = offs[el - 1] + len(b_end)
    cand = txt[:s_i] + new_expr + txt[e_i:]
    try:
        ast.parse(cand)
        return cand
    except SyntaxError:
        return None


def _find_func(tree, lineno):
    best = None
    for nd in ast.walk(tree):
        if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_ln = getattr(nd, "end_lineno", nd.lineno)
            if nd.lineno <= lineno <= end_ln:
                if best is None or nd.lineno >= best.lineno:
                    best = nd
    return best


patches = []
seen = set()


def _emit(rel, patched_src, desc, prio=0):
    orig_txt, _, _ = _get_ast(rel)
    if not patched_src or patched_src == orig_txt:
        return
    k = (rel, patched_src)
    if k in seen:
        return
    seen.add(k)
    patches.append({"prio": prio, "rel_path": rel, "patched_src": patched_src, "description": desc})


# ---------------------------------------------------------------------------
# ENGINE 2A: Module-Global Def-Use Slice for Regex `$` -> `\Z` & `.fullmatch`
# ---------------------------------------------------------------------------
traced_files_and_globals = {}
for (rel, fn_nm, fln), finfo in exec_funcs.items():
    if not finfo["fail_lines"]:
        continue
    txt, tr, _ = _get_ast(rel)
    if tr is None:
        continue
    fn_nd = _find_func(tr, fln)
    if fn_nd is None:
        continue
    used_names = {n.id for s in fn_nd.body for n in ast.walk(s) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    traced_files_and_globals.setdefault(rel, set()).update(used_names)

for rel, used_names in traced_files_and_globals.items():
    txt, tr, _ = _get_ast(rel)
    if tr is None:
        continue
    # Inspect module-level assignments of regex constants & class/function regex calls
    for stmt in tr.body:
        targets = []
        if isinstance(stmt, ast.Assign):
            targets = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            targets = [stmt.target.id]
        if targets and not (set(targets) & used_names) and not has_newline_witness:
            continue
        for sub in ast.walk(stmt):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and sub.value.endswith("$") and not sub.value.endswith(r"\$"):
                if has_newline_witness or any(t.lower().endswith(("regex", "re", "pattern")) for t in targets):
                    raw_seg = ast.get_source_segment(txt, sub)
                    if raw_seg and raw_seg[-2] == "$":
                        new_seg = raw_seg[:-2] + r"\Z" + raw_seg[-1]
                        cand = _replace_raw_span(txt, sub, new_seg)
                        if cand:
                            _emit(rel, cand, f"Module-global def-use regex end-anchor `$` -> `\\Z` at L{sub.lineno}", prio=-5)

    # Also check inline regex literals & `.match(` -> `.fullmatch(` inside executed fail functions
    for (r2, fn_nm, fln), finfo in exec_funcs.items():
        if r2 != rel or not finfo["fail_lines"]:
            continue
        fn_nd = _find_func(tr, fln)
        if fn_nd is None:
            continue
        for sub in ast.walk(fn_nd):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and sub.value.endswith("$") and not sub.value.endswith(r"\$"):
                raw_seg = ast.get_source_segment(txt, sub)
                if raw_seg and raw_seg[-2] == "$":
                    new_seg = raw_seg[:-2] + r"\Z" + raw_seg[-1]
                    cand = _replace_raw_span(txt, sub, new_seg)
                    if cand:
                        _emit(rel, cand, f"Inline regex end-anchor `$` -> `\\Z` in `{fn_nm}` L{sub.lineno}", prio=-4)
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "match" and len(sub.args) == 1:
                if sub.lineno in finfo["fail_lines"] or "fullmatch" in "".join(fail_ids):
                    raw_seg = ast.get_source_segment(txt, sub)
                    if raw_seg and ".match(" in raw_seg:
                        new_seg = raw_seg.replace(".match(", ".fullmatch(", 1)
                        cand = _replace_raw_span(txt, sub, new_seg)
                        if cand:
                            _emit(rel, cand, f"Regex prefix `.match(` -> `.fullmatch(` in `{fn_nm}` L{sub.lineno}", prio=-4)


# ---------------------------------------------------------------------------
# ENGINE 2B: Live Boolean Guard Pass/Fail Separation & Data-Model Totality
# ---------------------------------------------------------------------------
for (rel, lineno), obs in guard_obs.items():
    f_list = obs["fail"]
    p_list = obs["pass"]
    if not f_list:
        continue
    txt, tr, if_map = _get_ast(rel)
    if tr is None or lineno not in if_map:
        continue
    test_nd = if_map[lineno]
    orig_guard_src = ast.get_source_segment(txt, test_nd) or ast.unparse(test_nd)

    # Case B1: `hasattr(X, ATTR)` -> `getattr(X, ATTR, None) is not None`
    # (Disabled dunder protocol when `__reversed__ = None` / `__hash__ = None`!)
    for sub in ast.walk(test_nd):
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Name)
            and sub.func.id == "hasattr"
            and len(sub.args) == 2
        ):
            obj_s = ast.get_source_segment(txt, sub.args[0]) or ast.unparse(sub.args[0])
            attr_s = ast.get_source_segment(txt, sub.args[1]) or ast.unparse(sub.args[1])
            new_sub = f"getattr({obj_s}, {attr_s}, None) is not None"
            cand = _replace_span(txt, sub, new_sub)
            if cand:
                _emit(rel, cand, f"Disabled-protocol totality `hasattr` -> `{new_sub}` at L{lineno}", prio=-5)

    # Compute desired branch flip: if all failing evaluations at this guard took one branch `f_b`,
    # synthesize predicates that evaluate to `not f_b` on failing frames and preserve `p_b` on passing frames!
    f_bools = {b for b, _, _ in f_list}
    if len(f_bools) != 1:
        continue
    orig_f_b = next(iter(f_bools))
    want_f_b = not orig_f_b

    # Candidate guard expressions from the guard AST + in-scope locals/attributes
    cand_guards = []
    if isinstance(test_nd, ast.Name):
        v = test_nd.id
        cand_guards.extend([
            f"{v} is not None",
            f"{v} is None",
            f"bool({v}) and {v} != 'None'",
            f"not {v}",
        ])
    elif isinstance(test_nd, ast.UnaryOp) and isinstance(test_nd.op, ast.Not) and isinstance(test_nd.operand, ast.Name):
        v = test_nd.operand.id
        cand_guards.extend([f"{v} is None", f"{v} is not None", v])
    elif isinstance(test_nd, ast.Attribute):
        a_src = orig_guard_src
        cand_guards.extend([
            f"{a_src} is not None",
            f"{a_src} is None",
            f"bool({a_src}) and str({a_src}) != 'None'",
        ])

    # Mine boolean/optional locals and `self.*` attributes in scope at this guard
    sample_scope = f_list[0][1]
    for vn, vv in list(sample_scope.items())[:16]:
        if vn in ("self", "cls"):
            if not isinstance(vv, (int, float, str, bytes, list, dict, set, tuple, type(None))):
                for ak in dir(vv)[:30]:
                    if ak.startswith("_"):
                        continue
                    try:
                        av = getattr(vv, ak)
                        if isinstance(av, (bool, type(None), str)):
                            cand_guards.extend([f"{vn}.{ak}", f"not {vn}.{ak}", f"{vn}.{ak} is not None"])
                    except Exception:
                        continue
            continue
        cand_guards.extend([
            vn, f"not {vn}", f"{vn} is not None", f"{vn} is None",
            f"({orig_guard_src}) and ({vn} is not None)",
            f"({orig_guard_src}) and not {vn}",
            f"({orig_guard_src}) or ({vn} is not None)",
            f"({orig_guard_src}) or bool({vn})",
        ])

    # Also check sibling string/symbol constants in the same function/class (e.g. `name != '__version_info__'`)
    fn_nd = _find_func(tr, lineno)
    if fn_nd is not None:
        fn_str_consts = [
            repr(n.value) for n in ast.walk(tr)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and 1 <= len(n.value) <= 32
        ][:12]
        for vn, vv in list(sample_scope.items())[:8]:
            if isinstance(vv, str):
                for sc in fn_str_consts:
                    cand_guards.append(f"({orig_guard_src}) and {vn} != {sc}")
                    cand_guards.append(f"{vn} != {sc}")

    sep_hits = 0
    for cg in dict.fromkeys(cand_guards):
        if sep_hits >= 4:
            break
        try:
            c_obj = compile(ast.Expression(body=ast.parse(cg, mode="eval").body), "<sep>", "eval")
            if not all(bool(eval(c_obj, fg, fl)) is want_f_b for _, fl, fg in f_list):
                continue
            if p_list and not all(bool(eval(c_obj, pg, pl)) is pb for pb, pl, pg in p_list):
                continue
            # Require at least 1 passing observation when using generic variable flips to avoid tautologies
            if not p_list and "is not None" not in cg and "is None" not in cg:
                continue
            cand = _replace_raw_span(txt, test_nd, cg)
            if cand:
                _emit(rel, cand, f"Pass/fail guard separation `{orig_guard_src}` -> `{cg}` at L{lineno}", prio=-4 if p_list else -2)
                sep_hits += 1
        except Exception:
            continue


# ---------------------------------------------------------------------------
# ENGINE 2C: Exception-Guided Comparison Safety & Variadic `*args` Forwarding
# ---------------------------------------------------------------------------
for es in exc_sites:
    rel = es["rel"]
    ln = es["line"]
    txt, tr, _ = _get_ast(rel)
    if tr is None:
        continue
    fn_nd = _find_func(tr, ln)
    if fn_nd is None:
        continue

    # Guard whose `__bool__` raised directly (`AssertionError` / `TypeError` / `ValueError`)
    if es.get("guard_bool_crash") or "truthiness" in es.get("exc_msg", "").lower() or "ambiguous" in es.get("exc_msg", "").lower():
        _, _, if_map_e = _get_ast(rel)
        target_nodes = []
        if ln in if_map_e:
            g_root = if_map_e[ln]
            target_nodes.append(g_root)
            if isinstance(g_root, ast.BoolOp):
                target_nodes.extend(g_root.values)
        else:
            for sub_b in ast.walk(fn_nd):
                if getattr(sub_b, "lineno", -1) <= ln <= getattr(sub_b, "end_lineno", -1):
                    if isinstance(sub_b, (ast.If, ast.While, ast.IfExp)):
                        target_nodes.append(sub_b.test)
                        if isinstance(sub_b.test, ast.BoolOp):
                            target_nodes.extend(sub_b.test.values)
        for g_nd in target_nodes:
            if isinstance(g_nd, (ast.Name, ast.Attribute)):
                g_src = ast.get_source_segment(txt, g_nd) or ast.unparse(g_nd)
                for repl_g in (f"{g_src} is not None", f"{g_src} is None"):
                    cand = _replace_span(txt, g_nd, repl_g)
                    if cand:
                        _emit(rel, cand, f"Avoid `__bool__` evaluation `{g_src}` -> `{repl_g}` at L{ln}", prio=-6)
            elif isinstance(g_nd, ast.UnaryOp) and isinstance(g_nd.op, ast.Not) and isinstance(g_nd.operand, (ast.Name, ast.Attribute)):
                g_src = ast.get_source_segment(txt, g_nd.operand) or ast.unparse(g_nd.operand)
                for repl_g in (f"{g_src} is None", f"{g_src} is not None"):
                    cand = _replace_span(txt, g_nd, repl_g)
                    if cand:
                        _emit(rel, cand, f"Avoid `__bool__` evaluation `not {g_src}` -> `{repl_g}` at L{ln}", prio=-6)

    # Non-comparable `==` / `!=` raising ValueError / TypeError (e.g. `x == ""` on array/custom object)
    if es["exc_type"] in ("ValueError", "TypeError"):
        for sub in ast.walk(fn_nd):
            if (
                isinstance(sub, ast.Compare)
                and getattr(sub, "lineno", -1) == ln
                and len(sub.ops) == 1
                and isinstance(sub.ops[0], (ast.Eq, ast.NotEq))
                and isinstance(sub.comparators[0], ast.Constant)
            ):
                lhs_s = ast.get_source_segment(txt, sub.left) or ast.unparse(sub.left)
                rhs_v = sub.comparators[0].value
                cmp_s = ast.get_source_segment(txt, sub) or ast.unparse(sub)
                if isinstance(rhs_v, (str, bytes, int, float)):
                    tp_nm = type(rhs_v).__name__
                    guarded = f"(isinstance({lhs_s}, {tp_nm}) and {cmp_s})" if isinstance(sub.ops[0], ast.Eq) else f"(not isinstance({lhs_s}, {tp_nm}) or {cmp_s})"
                    cand = _replace_raw_span(txt, sub, guarded)
                    if cand:
                        _emit(rel, cand, f"Type-safe equality guard `{guarded}` at L{ln}", prio=-5)

    # OverflowError on `int(float_inf)` -> catch `(ValueError, OverflowError)`
    if es["exc_type"] == "OverflowError":
        for sub in ast.walk(fn_nd):
            if isinstance(sub, ast.ExceptHandler) and sub.type is not None:
                t_src = ast.get_source_segment(txt, sub.type) or ast.unparse(sub.type)
                if "ValueError" in t_src and "OverflowError" not in t_src:
                    new_t = f"({t_src}, OverflowError)" if not t_src.startswith("(") else t_src[:-1] + ", OverflowError)"
                    cand = _replace_raw_span(txt, sub.type, new_t)
                    if cand:
                        _emit(rel, cand, f"Exception-lattice widening `{new_t}` for OverflowError at L{sub.lineno}", prio=-5)

# Check baseline_out + fail_reports for `takes K positional arguments ... were given` on a repo method/classmethod
all_fail_text = baseline_out + "\n" + "\n".join(fail_reports)
m_arity = re.search(r"([A-Za-z_]\w*)\.([A-Za-z_]\w*)\(\) takes (\d+) (?:from \d+ to \d+ )?positional arguments? but \d+ were given", all_fail_text)
if m_arity:
    cls_w, fn_w = m_arity.group(1), m_arity.group(2)
    cand_rels = list(dict.fromkeys([r for (r, _, _) in exec_funcs] + [
        p.relative_to(cow_root).as_posix() for p in cow_root.rglob("*.py")
        if not _is_test_rel(p.relative_to(cow_root).as_posix())
    ]))
    for rel in cand_rels:
        txt, tr, _ = _get_ast(rel)
        if tr is None or cls_w not in txt:
            continue
        for nd in ast.walk(tr):
            if isinstance(nd, ast.ClassDef) and nd.name == cls_w:
                for item in nd.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == fn_w:
                        if item.args.vararg is None and len(item.args.args) >= 2:
                            p0, p1 = item.args.args[0].arg, item.args.args[1].arg
                            lines = txt.splitlines(True)
                            for h_idx in range(max(0, item.lineno - 1), min(len(lines), item.lineno + 3)):
                                hdr_ln = lines[h_idx]
                                if f"{p1}" in hdr_ln and f"*{p1}" not in hdr_ln:
                                    lines_new = list(lines)
                                    lines_new[h_idx] = re.sub(rf"\b{re.escape(p1)}\b", f"*{p1}", hdr_ln, count=1)
                                    cand = "".join(lines_new)
                                    try:
                                        ast.parse(cand)
                                        _emit(rel, cand, f"Variadic parameter promotion `*{p1}` on `{cls_w}.{fn_w}`", prio=-6)
                                    except SyntaxError:
                                        pass
                                    break


# ---------------------------------------------------------------------------
# ENGINE 2D: Codebase Type-Habitation Idioms (`.copy()`, `rsplit`, Symmetric Helper)
# ---------------------------------------------------------------------------
for (rel, fn_nm, fln), finfo in exec_funcs.items():
    if not finfo["fail_lines"]:
        continue
    txt, tr, _ = _get_ast(rel)
    if tr is None:
        continue
    fn_nd = _find_func(tr, fln)
    if fn_nd is None:
        continue
    mod_funcs = {nd.name for nd in tr.body if isinstance(nd, ast.FunctionDef)}

    for sub in ast.walk(fn_nd):
        ln = getattr(sub, "lineno", -1)
        if ln not in finfo["fail_lines"]:
            continue

        # 1. Directional string/delimiter duals (`split` <-> `rsplit`, `lstrip` <-> `rstrip`, `find` <-> `rfind`)
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            m_attr = sub.func.attr
            DUALS = {
                "split": "rsplit", "rsplit": "split",
                "find": "rfind", "rfind": "find",
                "index": "rindex", "rindex": "index",
                "lstrip": "rstrip", "rstrip": "lstrip",
            }
            if m_attr in DUALS:
                raw_seg = ast.get_source_segment(txt, sub)
                if raw_seg and f".{m_attr}(" in raw_seg:
                    new_seg = raw_seg.replace(f".{m_attr}(", f".{DUALS[m_attr]}(", 1)
                    cand = _replace_raw_span(txt, sub, new_seg)
                    if cand:
                        _emit(rel, cand, f"Directional string dual `.{m_attr}(` -> `.{DUALS[m_attr]}(` at L{ln}", prio=-4)

        # 2. Symmetric / asymmetric helper projection on 2-tuples in `yield a, b` or `return a, b`
        if isinstance(sub, (ast.Yield, ast.Return)) and isinstance(sub.value, ast.Tuple) and len(sub.value.elts) == 2:
            e0, e1 = sub.value.elts
            if isinstance(e1, ast.Call) and isinstance(e1.func, ast.Name) and e1.func.id in mod_funcs and len(e1.args) == 1:
                h_nm = e1.func.id
                e1_s = ast.get_source_segment(txt, e1) or ast.unparse(e1)
                if not (isinstance(e0, ast.Call) and isinstance(e0.func, ast.Name) and e0.func.id == h_nm):
                    e0_s = ast.get_source_segment(txt, e0) or ast.unparse(e0)
                    cand = _replace_raw_span(txt, sub.value, f"{h_nm}({e0_s}), {e1_s}")
                    if cand:
                        _emit(rel, cand, f"Symmetric tuple helper projection `{h_nm}({e0_s})` at L{ln}", prio=-4)
                elif len(e0.args) == 1:
                    inner0_s = ast.get_source_segment(txt, e0.args[0]) or ast.unparse(e0.args[0])
                    cand_asym = _replace_raw_span(txt, sub.value, f"{inner0_s}, {e1_s}")
                    if cand_asym:
                        _emit(rel, cand_asym, f"Asymmetric tuple key preservation `{inner0_s}, {e1_s}` at L{ln}", prio=-4)

        # 3. Codebase-habited defensive container copy (`return self._x` -> `return self._x.copy()` / `list(self._x)`)
        if isinstance(sub, ast.Return) and isinstance(sub.value, (ast.Attribute, ast.Name)):
            v_src = ast.get_source_segment(txt, sub.value) or ast.unparse(sub.value)
            for sample_sc in finfo["fail_scopes"][:2]:
                try:
                    cur_v = eval(compile(ast.Expression(body=sub.value), "<ret>", "eval"), {}, sample_sc)
                except Exception:
                    cur_v = None
                if isinstance(cur_v, list):
                    c_lst = _replace_raw_span(txt, sub.value, f"list({v_src})")
                    if c_lst:
                        _emit(rel, c_lst, f"Defensive list materialization `list({v_src})` at L{ln}", prio=-5)
                if isinstance(cur_v, (list, dict, set)) or ".copy(" in txt:
                    cand = _replace_raw_span(txt, sub.value, f"{v_src}.copy()")
                    if cand:
                        _emit(rel, cand, f"Codebase-habited defensive `.copy()` on `{v_src}` at L{ln}", prio=-4)
                break

patches.sort(key=lambda d: d["prio"])
out_path.write_text(json.dumps({"patches": patches[:24]}), encoding="utf-8")
'''


def synthesize_type_habitation_and_guard_repairs(
    *,
    cow_root: pathlib.Path,
    pycache_dir: pathlib.Path,
    py_exe: str,
    py_env: dict[str, str],
    failing_tests: list[str],
    passing_tests: list[str],
    baseline_output: str = "",
    timeout_sec: float = 14.0,
) -> tuple[list[tuple[dict[str, str], str, str]], int]:
    """Run module-global def-use regex slicing, boolean guard pass/fail separation,
    and codebase-habited non-literal synthesis inside `cow_root`."""
    clean_fails = [t for t in failing_tests if t and not t.startswith("<")][:2]
    clean_passes = _select_sibling_passing_tests(clean_fails, passing_tests, limit=10)
    test_file = clean_fails[0].split("::")[0] if clean_fails and "::" in clean_fails[0] else ""

    script_f = pycache_dir / "_brain_habitation_guard.py"
    out_f = pycache_dir / "_brain_habitation_guard_out.json"
    if out_f.exists():
        out_f.unlink()
    script_f.write_text(_HABITATION_AND_GUARD_SCRIPT, encoding="utf-8")

    payload = json.dumps(
        {
            "cow_root": str(cow_root),
            "test_file": test_file,
            "fail_ids": clean_fails,
            "pass_ids": clean_passes,
            "baseline_out": baseline_output[-3000:],
            "out_path": str(out_f),
            "max_events": 40000,
        }
    )
    p_obj = subprocess.Popen(
        [py_exe, str(script_f), payload],
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

    if not out_f.exists():
        return [], 0
    try:
        data = json.loads(out_f.read_text(encoding="utf-8"))
    except Exception:
        return [], 0

    results: list[tuple[dict[str, str], str, str]] = []
    for item in data.get("patches") or []:
        rel_p = str(item.get("rel_path") or "")
        p_src = str(item.get("patched_src") or "")
        desc = str(item.get("description") or "Type-habitation / guard separation")
        if rel_p and p_src:
            results.append(({rel_p: p_src}, "COGS_TYPE_HABITATION_AND_GUARD_SEPARATION", desc))
    return results, len(results)


# ===========================================================================
# PILLAR 3: Def-Use Relational Zipper (Multi-File Contract Propagation)
# ===========================================================================

def extract_innermost_repo_failure_file(
    output: str,
    known_repo_files: set[str],
    exclude_test_target: str | None = None,
) -> str | None:
    """Return the innermost non-test repository file implicated in a secondary pytest failure."""
    matched_rels: list[str] = []
    for m in re.finditer(r'([^\s":]+\.py):(\d+):', output):
        cand_path = m.group(1).replace("\\", "/")
        for krel in known_repo_files:
            if cand_path.endswith(krel):
                if krel != exclude_test_target and not krel.startswith(("tests/", "test/", "testing/")):
                    matched_rels.append(krel)
    for m2 in re.finditer(r'File "([^"]+\.py)", line (\d+)', output):
        cand_path = m2.group(1).replace("\\", "/")
        for krel in known_repo_files:
            if cand_path.endswith(krel):
                if krel != exclude_test_target and not krel.startswith(("tests/", "test/", "testing/")):
                    matched_rels.append(krel)
    return matched_rels[-1] if matched_rels else None


def propagate_relational_zipper_hop(
    *,
    mental: Any,
    root_patch: dict[str, str],
    secondary_failing_tests: list[str],
    passing_tests: list[str],
    secondary_output: str,
) -> tuple[list[tuple[dict[str, str], str, str]], int]:
    """Pin `root_patch` (`{F_1: P_1}`) inside `mental.cow_root`, synthesize 1 hop of
    compensating repairs in the newly exposed caller/callee file `F_2 != F_1`, and
    restore `mental` cleanly. Reduces $O(|G|^2)$ multi-file search to $2 \\times O(|G|)$."""
    root_rels = list(root_patch.keys())
    coupled_out: list[tuple[dict[str, str], str, str]] = []
    eval_cnt = 0
    try:
        mental.apply_overrides(root_patch)
        w_cands, c1 = synthesize_live_differential_witness_repairs(
            cow_root=mental.cow_root,
            pycache_dir=mental.pycache_dir,
            py_exe=mental.py_exe,
            py_env=mental._python_env(),
            top_rel_files=[],
            failing_tests=secondary_failing_tests[:2],
            passing_tests=passing_tests,
            timeout_sec=10.0,
        )
        h_cands, c2 = synthesize_type_habitation_and_guard_repairs(
            cow_root=mental.cow_root,
            pycache_dir=mental.pycache_dir,
            py_exe=mental.py_exe,
            py_env=mental._python_env(),
            failing_tests=secondary_failing_tests[:2],
            passing_tests=passing_tests,
            baseline_output=secondary_output,
            timeout_sec=10.0,
        )
        eval_cnt = c1 + c2
        for sub_fp, _, sub_desc in (w_cands[:4] + h_cands[:4]):
            # Only compose cross-file (`F_2 not in F_1`) or orthogonal multi-file hops
            if any(k not in root_patch for k in sub_fp):
                merged = dict(root_patch)
                merged.update(sub_fp)
                coupled_out.append(
                    (
                        merged,
                        "COGS_DEF_USE_RELATIONAL_ZIPPER",
                        f"Relational Zipper ({'+'.join(sorted(merged.keys()))}): {sub_desc}",
                    )
                )
    finally:
        mental.restore_originals(root_rels)
    return coupled_out[:6], eval_cnt
