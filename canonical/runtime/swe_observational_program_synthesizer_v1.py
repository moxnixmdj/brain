#!/usr/bin/env python3
"""Deterministic Program Synthesis & Multi-Module Package Builder.

Implements two classical PL/SE synthesis algorithms with zero model calls ($0):
  1. Bottom-Up Observational-Equivalence Enumeration (Udupa et al., PLDI 2013;
     Odena et al., ICLR 2021): enumerates typed Python AST expressions by
     increasing size, evaluates each candidate on concrete input vectors, and
     collapses syntactically distinct expressions that yield identical output
     signatures into a single canonical representative.
  2. STUN — Synthesis Through Unification (Alur et al., CAV 2015): when no
     single branch-free term satisfies all I/O examples, synthesizes partial
     branch terms and unifies them under synthesized atomic predicates into a
     minimal if/elif/else decision tree.
  3. Topological Multi-Module Package Builder: realizes a dependency-ordered
     multi-file Python package, resolves `SYNTHESIZE` function bodies against
     the suite's I/O assertions, checks AST static soundness, and verifies the
     resulting package atomically.
"""
from __future__ import annotations

import ast
import math
import pathlib
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_SWE_OBSERVATIONAL_PROGRAM_SYNTHESIZER_V1"

_SAFE_EVAL_BUILTINS: dict[str, Any] = {
    "__build_class__": __import__("builtins").__build_class__,
    "__name__": "__synth__",
    "object": object,
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "frozenset": frozenset,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def _freeze_val(val: Any, _depth: int = 0) -> Any:
    """Hashable canonical signature for observational equivalence."""
    if _depth > 5:
        return ("DEPTH_CAP", type(val).__name__)
    if val is None or isinstance(val, (bool, int, str, bytes)):
        return (type(val).__name__, val)
    if isinstance(val, float):
        if math.isnan(val):
            return ("float", "NaN")
        return ("float", round(val, 9))
    if isinstance(val, (tuple, list)):
        if len(val) > 64:
            return (type(val).__name__, len(val), tuple(_freeze_val(x, _depth + 1) for x in val[:16]))
        return (type(val).__name__, tuple(_freeze_val(x, _depth + 1) for x in val))
    if isinstance(val, (set, frozenset)):
        items = sorted((_freeze_val(x, _depth + 1) for x in val), key=repr)
        return (type(val).__name__, tuple(items[:64]))
    if isinstance(val, dict):
        items = sorted(((_freeze_val(k, _depth + 1), _freeze_val(v, _depth + 1)) for k, v in val.items()), key=repr)
        return ("dict", tuple(items[:64]))
    if hasattr(val, "__dict__"):
        items = sorted((k, _freeze_val(v, _depth + 1)) for k, v in vars(val).items() if not k.startswith("_"))
        return ("obj:" + type(val).__name__, tuple(items))
    return ("repr:" + type(val).__name__, repr(val)[:120])


def _eval_compiled(code_obj: Any, param_names: Sequence[str], inputs: Sequence[tuple[Any, ...]]) -> tuple[bool, tuple[Any, ...], list[Any]]:
    sigs: list[Any] = []
    raws: list[Any] = []
    for row in inputs:
        env = dict(zip(param_names, row))
        try:
            v = eval(code_obj, {"__builtins__": _SAFE_EVAL_BUILTINS}, env)  # noqa: S307 - pure AST-constructed expression with closed builtins
        except Exception:
            return False, (), []
        sigs.append(_freeze_val(v))
        raws.append(v)
    return True, tuple(sigs), raws


def extract_io_examples_from_test_source(
    test_source: str,
    fn_name: str,
    context_ns: Mapping[str, Any] | None = None,
) -> tuple[list[tuple[tuple[Any, ...], Any]], list[Any]]:
    """Extract `(args_tuple, expected_value)` pairs + domain constants from test AST."""
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return [], []
    ns = {"__builtins__": _SAFE_EVAL_BUILTINS}
    if context_ns:
        ns.update(context_ns)

    examples: list[tuple[tuple[Any, ...], Any]] = []
    constants: list[Any] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)) and not isinstance(node.value, bool):
            if isinstance(node.value, str) and len(node.value) <= 24:
                constants.append(node.value)
            elif isinstance(node.value, (int, float)):
                constants.append(node.value)

    def _eval_arg_expr(expr: ast.AST) -> tuple[bool, Any]:
        try:
            c = compile(ast.Expression(expr), "<test_example>", "eval")
            return True, eval(c, ns, {})  # noqa: S307 - closed test literal/model namespace
        except Exception:
            return False, None

    def _match_fn_call(expr: ast.AST) -> tuple[bool, tuple[Any, ...]]:
        if not isinstance(expr, ast.Call):
            return False, ()
        callee_ok = (
            (isinstance(expr.func, ast.Name) and expr.func.id == fn_name)
            or (isinstance(expr.func, ast.Attribute) and expr.func.attr == fn_name)
        )
        if not callee_ok or expr.keywords:
            return False, ()
        vals: list[Any] = []
        for a in expr.args:
            ok, v = _eval_arg_expr(a)
            if not ok:
                return False, ()
            vals.append(v)
        return True, tuple(vals)

    for node in ast.walk(tree):
        # unittest: self.assertEqual(fn(...), expected) / assertTrue / assertFalse / assertIsNone
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            mname = node.func.attr
            if mname == "assertEqual" and len(node.args) >= 2:
                ok_c, call_args = _match_fn_call(node.args[0])
                ok_e, exp_val = _eval_arg_expr(node.args[1])
                if ok_c and ok_e:
                    examples.append((call_args, exp_val))
                    continue
                ok_c2, call_args2 = _match_fn_call(node.args[1])
                ok_e2, exp_val2 = _eval_arg_expr(node.args[0])
                if ok_c2 and ok_e2:
                    examples.append((call_args2, exp_val2))
            elif mname in ("assertTrue", "assertFalse") and len(node.args) >= 1:
                ok_c, call_args = _match_fn_call(node.args[0])
                if ok_c:
                    examples.append((call_args, mname == "assertTrue"))
            elif mname == "assertIsNone" and len(node.args) >= 1:
                ok_c, call_args = _match_fn_call(node.args[0])
                if ok_c:
                    examples.append((call_args, None))
        # pytest/plain: assert fn(...) == expected
        elif isinstance(node, ast.Assert):
            t = node.test
            if isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq):
                ok_c, call_args = _match_fn_call(t.left)
                ok_e, exp_val = _eval_arg_expr(t.comparators[0])
                if ok_c and ok_e:
                    examples.append((call_args, exp_val))
            else:
                ok_c, call_args = _match_fn_call(t)
                if ok_c:
                    examples.append((call_args, True))

    dedup_consts: list[Any] = []
    seen_c: set[Any] = set()
    for c in constants:
        fk = _freeze_val(c)
        if fk not in seen_c:
            seen_c.add(fk)
            dedup_consts.append(c)
    return examples, dedup_consts[:12]


def synthesize_python_function_body(
    param_names: Sequence[str],
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    extra_constants: Sequence[Any] = (),
    max_weight: int = 4,
    max_bank_size: int = 900,
) -> str | None:
    """Synthesize minimal Python statement body (`return ...` or `if ...: return ...`) from I/O pairs."""
    if not examples or not param_names:
        return None
    inputs = [tuple(ex[0]) for ex in examples]
    if any(len(row) != len(param_names) for row in inputs):
        return None
    expected_raw = [ex[1] for ex in examples]
    target_sig = tuple(_freeze_val(v) for v in expected_raw)

    # Bank organized by weight: expr_str -> (sig_tuple, raw_outputs)
    seen_sigs: dict[tuple[Any, ...], str] = {}
    by_weight: dict[int, list[tuple[str, list[Any]]]] = {w: [] for w in range(1, max_weight + 1)}

    def _try_register(weight: int, expr_src: str) -> str | None:
        if len(seen_sigs) >= max_bank_size:
            return None
        try:
            code = compile(expr_src, "<synth>", "eval")
        except SyntaxError:
            return None
        ok, sig, raws = _eval_compiled(code, param_names, inputs)
        if not ok:
            return None
        if sig == target_sig:
            return expr_src
        if sig not in seen_sigs:
            seen_sigs[sig] = expr_src
            by_weight[weight].append((expr_src, raws))
        return None

    # Weight 1: parameters, parameter attributes, base & harvested constants
    for p in param_names:
        hit = _try_register(1, p)
        if hit is not None:
            return f"return {hit}"
        # Discover object attributes on sample values
        attr_names: set[str] = set()
        idx = list(param_names).index(p)
        for row in inputs:
            val = row[idx]
            if hasattr(val, "__dict__"):
                attr_names.update(k for k in vars(val) if not k.startswith("_"))
        for attr in sorted(attr_names):
            hit = _try_register(1, f"{p}.{attr}")
            if hit is not None:
                return f"return {hit}"

    seed_consts: list[Any] = [0, 1, 2, -1, 100, True, False, None, "", [], {}]
    for c in extra_constants:
        if c not in seed_consts:
            seed_consts.append(c)
    for c in seed_consts:
        hit = _try_register(1, repr(c))
        if hit is not None:
            return f"return {hit}"

    # Weight 2..max_weight: unary transforms, comprehensions, binary ops
    unary_templates = (
        "len({0})",
        "sum({0})",
        "abs({0})",
        "min({0})",
        "max({0})",
        "sorted({0})",
        "list(set({0}))",
        "-({0})",
        "not ({0})",
        "({0}).strip()",
        "({0}).lower()",
        "({0}).upper()",
        "({0}).split()",
        "({0})[::-1]",
        "[x for x in {0} if x]",
    )
    bin_ops = ("+", "-", "*", "//", "%", "==", "!=", "<", "<=", ">", ">=", "and", "or")

    for w in range(2, max_weight + 1):
        # Unary over weight w-1
        for e1, raws1 in list(by_weight.get(w - 1, [])):
            for tmpl in unary_templates:
                # Type-screen using first sample value to avoid pointless evals
                v0 = raws1[0]
                if "strip" in tmpl or "lower" in tmpl or "upper" in tmpl or "split" in tmpl:
                    if not isinstance(v0, str):
                        continue
                if tmpl == "({0})[::-1]" and not isinstance(v0, (str, list, tuple)):
                    continue
                if tmpl.startswith(("len(", "sorted(", "[x for")) and not isinstance(v0, (str, list, tuple, set, dict)):
                    continue
                if tmpl.startswith("sum(") and not isinstance(v0, (list, tuple, set)):
                    continue
                if tmpl.startswith(("abs(", "-(")) and (isinstance(v0, bool) or not isinstance(v0, (int, float))):
                    continue
                hit = _try_register(w, tmpl.format(e1))
                if hit is not None:
                    return f"return {hit}"
            if isinstance(raws1[0], (list, tuple)) and raws1[0]:
                # Aggregations over object attributes inside list parameter (e.g. sum(x.price * x.qty for x in items))
                elem0 = raws1[0][0]
                if hasattr(elem0, "__dict__"):
                    e_attrs = sorted(k for k in vars(elem0) if not k.startswith("_"))
                    for a1 in e_attrs:
                        hit = _try_register(w, f"sum(_x.{a1} for _x in {e1})")
                        if hit is not None:
                            return f"return {hit}"
                    if len(e_attrs) >= 2:
                        for i_a, a1 in enumerate(e_attrs):
                            for a2 in e_attrs[i_a + 1:]:
                                hit = _try_register(w, f"sum(_x.{a1} * _x.{a2} for _x in {e1})")
                                if hit is not None:
                                    return f"return {hit}"

        # Binary combinations w1 + w2 == w
        for w1 in range(1, w):
            w2 = w - w1
            list1 = by_weight.get(w1, [])
            list2 = by_weight.get(w2, [])
            for e1, raws1 in list1:
                for e2, raws2 in list2:
                    if e1 == e2:
                        continue
                    v1, v2 = raws1[0], raws2[0]
                    for op in bin_ops:
                        if op in ("+", "-", "*", "//", "%"):
                            if isinstance(v1, bool) or isinstance(v2, bool):
                                continue
                            if op in ("-", "*", "//", "%") and not (isinstance(v1, (int, float)) and isinstance(v2, (int, float))):
                                continue
                        hit = _try_register(w, f"({e1} {op} {e2})")
                        if hit is not None:
                            return f"return {hit}"
                    if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and not isinstance(v1, bool) and not isinstance(v2, bool):
                        for fn2 in ("min", "max"):
                            hit = _try_register(w, f"{fn2}({e1}, {e2})")
                            if hit is not None:
                                return f"return {hit}"
                    if isinstance(v1, dict):
                        hit = _try_register(w, f"({e1}).get({e2})")
                        if hit is not None:
                            return f"return {hit}"
                    if len(seen_sigs) >= max_bank_size:
                        break
                if len(seen_sigs) >= max_bank_size:
                    break

    # STUN Stage (Alur et al., CAV 2015): unify partial terms under synthesized predicates!
    n_ex = len(examples)
    all_terms: list[tuple[str, tuple[bool, ...]]] = []
    for sig, expr_src in seen_sigs.items():
        mask = tuple(sig[i] == target_sig[i] for i in range(n_ex))
        if any(mask):
            all_terms.append((expr_src, mask))

    # Collect boolean predicates from bank + standard guard predicates
    predicates: list[tuple[str, tuple[bool, ...]]] = []
    seen_pmasks: set[tuple[bool, ...]] = set()

    def _add_pred(p_src: str) -> None:
        try:
            c = compile(f"bool({p_src})", "<pred>", "eval")
        except SyntaxError:
            return
        ok, _, raws = _eval_compiled(c, param_names, inputs)
        if not ok:
            return
        pmask = tuple(bool(x) for x in raws)
        if any(pmask) and not all(pmask) and pmask not in seen_pmasks:
            seen_pmasks.add(pmask)
            predicates.append((p_src, pmask))

    for p in param_names:
        for cand_p in (
            f"{p} is None",
            f"not {p}",
            f"len({p}) == 0",
            f"{p} <= 0",
            f"{p} < 0",
            f"{p} == 0",
            f"{p} == 1",
            f"{p} % 2 == 0",
        ):
            _add_pred(cand_p)
        for c in extra_constants[:6]:
            if isinstance(c, (int, float, str)):
                _add_pred(f"{p} == {c!r}")
                if isinstance(c, (int, float)):
                    _add_pred(f"{p} <= {c!r}")
                    _add_pred(f"{p} < {c!r}")
                    _add_pred(f"{p} >= {c!r}")

    for sig, expr_src in seen_sigs.items():
        if all(t == "bool" for t, _ in sig):
            pmask = tuple(bool(v) for _, v in sig)
            if any(pmask) and not all(pmask) and pmask not in seen_pmasks:
                seen_pmasks.add(pmask)
                predicates.append((expr_src, pmask))

    # 1-level STUN: if P: return E_then else: return E_else
    for p_src, pmask in predicates:
        then_cands = [e for e, m in all_terms if all(m[i] for i in range(n_ex) if pmask[i])]
        if not then_cands:
            continue
        else_cands = [e for e, m in all_terms if all(m[i] for i in range(n_ex) if not pmask[i])]
        if else_cands:
            e_then = min(then_cands, key=len)
            e_else = min(else_cands, key=len)
            return f"if {p_src}:\n    return {e_then}\nreturn {e_else}"

    # 2-level STUN: if P1: return E1 / elif P2: return E2 / return E3
    for i, (p1_src, pm1) in enumerate(predicates[:40]):
        t1_cands = [e for e, m in all_terms if all(m[k] for k in range(n_ex) if pm1[k])]
        if not t1_cands:
            continue
        rem_indices = [k for k in range(n_ex) if not pm1[k]]
        for p2_src, pm2 in predicates[:40]:
            if p1_src == p2_src:
                continue
            b2 = [k for k in rem_indices if pm2[k]]
            b3 = [k for k in rem_indices if not pm2[k]]
            if not b2 or not b3:
                continue
            t2_cands = [e for e, m in all_terms if all(m[k] for k in b2)]
            if not t2_cands:
                continue
            t3_cands = [e for e, m in all_terms if all(m[k] for k in b3)]
            if t3_cands:
                e1 = min(t1_cands, key=len)
                e2 = min(t2_cands, key=len)
                e3 = min(t3_cands, key=len)
                return f"if {p1_src}:\n    return {e1}\nelif {p2_src}:\n    return {e2}\nreturn {e3}"

    return None


def architect_multi_module_package(
    repo: pathlib.Path,
    package_root: pathlib.Path,
    modules_spec: Sequence[Mapping[str, Any]],
    tests_spec: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build a multi-module Python package in topological order, synthesizing `SYNTHESIZE` bodies."""
    from canonical.runtime.bound_capabilities import _swe_static_soundness_v1 as soundness

    repo = repo.resolve()
    pkg = package_root.resolve()
    if pkg != repo and repo not in pkg.parents:
        raise RuntimeError("PACKAGE_OUTSIDE_REPOSITORY")

    # Backup existing files for atomic rollback
    existed_before = pkg.exists()
    backups: dict[pathlib.Path, bytes | None] = {}

    def _record_backup(p: pathlib.Path) -> None:
        if p not in backups:
            backups[p] = p.read_bytes() if p.is_file() else None

    def _rollback() -> None:
        for p, orig in backups.items():
            if orig is None:
                p.unlink(missing_ok=True)
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(orig)
        if not existed_before and pkg.exists():
            import shutil as _sh
            _sh.rmtree(pkg, ignore_errors=True)

    # Topological sort over declared `depends_on` module paths
    by_rel: dict[str, Mapping[str, Any]] = {str(m["path"]): m for m in modules_spec}
    visited: set[str] = set()
    visiting: set[str] = set()
    ordered: list[str] = []

    def _dfs(rel_p: str) -> None:
        if rel_p in visited:
            return
        if rel_p in visiting:
            raise RuntimeError(f"ARCHITECT_DEPENDENCY_CYCLE:{rel_p}")
        visiting.add(rel_p)
        spec_m = by_rel.get(rel_p) or {}
        for dep in (spec_m.get("depends_on") or ()):
            if str(dep) in by_rel:
                _dfs(str(dep))
        visiting.remove(rel_p)
        visited.add(rel_p)
        ordered.append(rel_p)

    for rel_p in sorted(by_rel):
        _dfs(rel_p)

    combined_test_src = "\n\n".join(str(t.get("source") or "") for t in tests_spec)
    written_files: list[str] = []
    synthesized_functions: list[str] = []

    try:
        # Write tests first so I/O contracts can be mined
        for t_row in tests_spec:
            t_path = (pkg / str(t_row["path"])).resolve()
            if pkg not in t_path.parents:
                raise RuntimeError("TEST_PATH_OUTSIDE_PACKAGE")
            _record_backup(t_path)
            t_path.parent.mkdir(parents=True, exist_ok=True)
            t_path.write_text(str(t_row["source"]), encoding="utf-8")
            written_files.append(t_path.relative_to(repo).as_posix())

        ns_accum: dict[str, Any] = {"__builtins__": _SAFE_EVAL_BUILTINS}
        for rel_p in ordered:
            m_row = by_rel[rel_p]
            m_path = (pkg / rel_p).resolve()
            if pkg not in m_path.parents:
                raise RuntimeError("MODULE_PATH_OUTSIDE_PACKAGE")
            _record_backup(m_path)
            m_path.parent.mkdir(parents=True, exist_ok=True)

            if "source" in m_row and m_row["source"] is not None:
                src_text = str(m_row["source"])
            else:
                chunks: list[str] = []
                for imp in (m_row.get("imports") or ()):
                    chunks.append(str(imp))
                if chunks:
                    chunks.append("")
                for cls_src in (m_row.get("classes") or ()):
                    chunks.append(str(cls_src).rstrip() + "\n")
                # Execute classes into ns_accum so example extraction can construct domain objects
                cls_only_src = "\n\n".join(str(c).rstrip() for c in (m_row.get("classes") or ()))
                if cls_only_src.strip():
                    try:
                        exec(compile(cls_only_src, str(m_path), "exec"), ns_accum, ns_accum)  # noqa: S102
                    except Exception:
                        pass
                for fn_spec in (m_row.get("functions") or ()):
                    fname = str(fn_spec["name"])
                    params = [str(p) for p in fn_spec.get("params") or ()]
                    sig_str = "(" + ", ".join(params) + ")"
                    body = fn_spec.get("body")
                    if not body or str(body).strip() == "SYNTHESIZE":
                        exs, consts = extract_io_examples_from_test_source(combined_test_src, fname, ns_accum)
                        synth_body = synthesize_python_function_body(params, exs, consts)
                        if not synth_body:
                            raise RuntimeError(f"SYNTHESIS_UNRESOLVED:{fname}")
                        body = synth_body
                        synthesized_functions.append(f"{rel_p}:{fname}")
                    indented = "\n".join("    " + ln for ln in str(body).splitlines())
                    fn_code = f"def {fname}{sig_str}:\n{indented}\n"
                    chunks.append(fn_code)
                    try:
                        exec(compile(fn_code, str(m_path), "exec"), ns_accum, ns_accum)  # noqa: S102
                    except Exception:
                        pass
                src_text = "\n".join(chunks).rstrip() + "\n"

            ast.parse(src_text, filename=str(m_path))
            m_path.write_text(src_text, encoding="utf-8")
            written_files.append(m_path.relative_to(repo).as_posix())

        snd = soundness.analyze_python_static_soundness(pkg)
        if not snd.get("sound"):
            raise RuntimeError(f"STATIC_SOUNDNESS_FAILED:{snd.get('errors')}")

        return {
            "schema": SCHEMA,
            "sound": True,
            "modules_ordered": ordered,
            "files_written": sorted(set(written_files)),
            "synthesized_functions": synthesized_functions,
        }
    except Exception:
        _rollback()
        raise
