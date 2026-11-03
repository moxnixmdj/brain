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


def _eval_compiled(
    code_obj: Any,
    param_names: Sequence[str],
    inputs: Sequence[tuple[Any, ...]],
    extra_builtins: Mapping[str, Any] | None = None,
) -> tuple[bool, tuple[Any, ...], list[Any]]:
    sigs: list[Any] = []
    raws: list[Any] = []
    builtins_ns = _SAFE_EVAL_BUILTINS if not extra_builtins else {**_SAFE_EVAL_BUILTINS, **extra_builtins}
    for row in inputs:
        env = dict(zip(param_names, row))
        try:
            v = eval(code_obj, {"__builtins__": builtins_ns}, env)  # noqa: S307 - pure AST-constructed expression with closed builtins
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


def _materialize_concept_helpers(
    body_src: str,
    concept_entries: Mapping[str, Any],
    concept_library: Any | None,
) -> str:
    """Emit self-contained local helper `def`s for any learned `concept_*` calls used in `body_src`."""
    if not concept_entries:
        return body_src
    try:
        wrapped = ast.parse("def _tmp():\n" + "\n".join("    " + ln for ln in body_src.splitlines()))
    except SyntaxError:
        return body_src
    used_ids: list[str] = []
    for nd in ast.walk(wrapped):
        if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Name) and nd.func.id in concept_entries:
            if nd.func.id not in used_ids:
                used_ids.append(nd.func.id)
    if not used_ids:
        return body_src

    expanded: list[str] = []
    queue = list(used_ids)
    while queue:
        cid = queue.pop(0)
        if cid in expanded or cid not in concept_entries:
            continue
        entry = concept_entries[cid]
        try:
            c_src = (
                entry.render_helper_def()
                if getattr(entry, "is_stmt_fn", False) and hasattr(entry, "render_helper_def")
                else entry.body_expr
            )
            c_tree = ast.parse(c_src) if getattr(entry, "is_stmt_fn", False) else ast.parse(c_src, mode="eval")
            for sub in ast.walk(c_tree):
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id in concept_entries:
                    if sub.func.id not in expanded and sub.func.id != cid:
                        queue.insert(0, sub.func.id)
        except SyntaxError:
            pass
        expanded.append(cid)

    ordered: list[str] = []
    for cid in reversed(expanded):
        if cid not in ordered:
            ordered.append(cid)

    helper_lines: list[str] = []
    for cid in ordered:
        entry = concept_entries[cid]
        if getattr(entry, "is_stmt_fn", False) and hasattr(entry, "render_helper_def"):
            helper_lines.append(entry.render_helper_def())
        else:
            p_sig = ", ".join(entry.param_names)
            helper_lines.append(f"def {cid}({p_sig}):\n    return {entry.body_expr}")
        if concept_library is not None and hasattr(concept_library, "record_concept_outcome"):
            try:
                concept_library.record_concept_outcome(cid, helped=True)
            except Exception:
                pass
    return "\n".join(helper_lines) + "\n" + body_src


def synthesize_python_function_body(
    param_names: Sequence[str],
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    extra_constants: Sequence[Any] = (),
    max_weight: int = 4,
    max_bank_size: int = 900,
    *,
    concept_library: Any | None = None,
) -> str | None:
    """Synthesize minimal Python statement body (`return ...` or `if ...: return ...`) from I/O pairs."""
    if not examples or not param_names:
        return None
    inputs = [tuple(ex[0]) for ex in examples]
    if any(len(row) != len(param_names) for row in inputs):
        return None
    expected_raw = [ex[1] for ex in examples]
    target_sig = tuple(_freeze_val(v) for v in expected_raw)

    active_lib = concept_library
    if active_lib is None:
        try:
            from canonical.runtime.memory_policy_v1 import can_read_memory
            from canonical.swe_kernel.concept_library_v1 import DEFAULT_LIBRARY_PATH, CompoundingConceptLibrary

            if can_read_memory() and DEFAULT_LIBRARY_PATH.is_file():
                active_lib = CompoundingConceptLibrary(DEFAULT_LIBRARY_PATH)
        except Exception:
            active_lib = None

    concept_entries: dict[str, Any] = {}
    concept_callables: dict[str, Any] = {}
    ordered_concepts: list[Any] = []
    if active_lib is not None and hasattr(active_lib, "concepts") and hasattr(active_lib, "callable_map"):
        try:
            ordered_concepts = list(active_lib.concepts())
            for c_ent in ordered_concepts:
                concept_entries[c_ent.concept_id] = c_ent
            concept_callables = dict(active_lib.callable_map())
        except Exception:
            ordered_concepts = []
            concept_entries = {}
            concept_callables = {}

    # Bank organized by weight: expr_str -> (sig_tuple, raw_outputs)
    seen_sigs: dict[tuple[Any, ...], str] = {}
    by_weight: dict[int, list[tuple[str, list[Any]]]] = {w: [] for w in range(1, max_weight + 1)}

    def _finish(body_code: str) -> str:
        return _materialize_concept_helpers(body_code, concept_entries, active_lib)

    def _try_register(weight: int, expr_src: str) -> str | None:
        if len(seen_sigs) >= max_bank_size:
            return None
        try:
            code = compile(expr_src, "<synth>", "eval")
        except SyntaxError:
            return None
        ok, sig, raws = _eval_compiled(code, param_names, inputs, extra_builtins=concept_callables)
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
            return _finish(f"return {hit}")
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
                return _finish(f"return {hit}")

    seed_consts: list[Any] = [0, 1, 2, -1, 100, True, False, None, "", [], {}]
    for c in extra_constants:
        if c not in seed_consts:
            seed_consts.append(c)
    for c in seed_consts:
        hit = _try_register(1, repr(c))
        if hit is not None:
            return _finish(f"return {hit}")

    # Weight 2..max_weight: learned concepts (G_t), unary transforms, comprehensions, binary ops
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
    bin_ops = ("+", "-", "*", "/", "//", "%", "==", "!=", "<", "<=", ">", ">=", "and", "or")

    def _domain_matches(domain_kind: str, sample_val: Any) -> bool:
        if domain_kind == "numeric":
            return isinstance(sample_val, (int, float)) and not isinstance(sample_val, bool)
        if domain_kind == "string":
            return isinstance(sample_val, str)
        if domain_kind == "sequence":
            return isinstance(sample_val, (list, tuple, set))
        return True

    param_set = set(param_names)
    for w in range(2, max_weight + 1):
        # Learned Concept Library G_t application at weight 2 (atomic concept calls over parameters/constants)
        if ordered_concepts and w == 2:
            arg_pool = list(by_weight.get(1, []))
            for c_ent in ordered_concepts[:16]:
                arity_c = int(c_ent.arity)
                dom_c = str(c_ent.domain_kind)
                # Prioritize parameters first, then minimal constants so bank stays compact and fast
                param_args = [e_a for e_a, r_a in arg_pool if e_a in param_set and r_a and _domain_matches(dom_c, r_a[0])]
                const_args = [e_a for e_a, r_a in arg_pool if e_a not in param_set and r_a and _domain_matches(dom_c, r_a[0])][:2]
                compat_args = (param_args + const_args)[: (5 if arity_c >= 3 else 6)]
                if len(compat_args) < arity_c:
                    continue
                import itertools as _it

                # By construction of anti-unification, distinct holes _v0.._v{k-1} bind distinct arguments!
                for combo in _it.permutations(compat_args, arity_c):
                    if not any(a in param_set for a in combo):
                        continue
                    call_expr = f"{c_ent.concept_id}({', '.join(combo)})"
                    hit = _try_register(w, call_expr)
                    if hit is not None:
                        return _finish(f"return {hit}")
                    if len(seen_sigs) >= max_bank_size:
                        break
                if len(seen_sigs) >= max_bank_size:
                    break

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
                    return _finish(f"return {hit}")
            if isinstance(raws1[0], (list, tuple)) and raws1[0]:
                # Aggregations over object attributes inside list parameter (e.g. sum(x.price * x.qty for x in items))
                elem0 = raws1[0][0]
                if hasattr(elem0, "__dict__"):
                    e_attrs = sorted(k for k in vars(elem0) if not k.startswith("_"))
                    for a1 in e_attrs:
                        hit = _try_register(w, f"sum(_x.{a1} for _x in {e1})")
                        if hit is not None:
                            return _finish(f"return {hit}")
                    if len(e_attrs) >= 2:
                        for i_a, a1 in enumerate(e_attrs):
                            for a2 in e_attrs[i_a + 1:]:
                                hit = _try_register(w, f"sum(_x.{a1} * _x.{a2} for _x in {e1})")
                                if hit is not None:
                                    return _finish(f"return {hit}")

        # Binary combinations w1 + w2 == w (prioritize higher-weight / learned-concept subtrees in outer loop)
        for w1 in range(w - 1, 0, -1):
            w2 = w - w1
            list1 = by_weight.get(w1, [])
            list2 = by_weight.get(w2, [])
            for e1, raws1 in list1:
                for e2, raws2 in list2:
                    if e1 == e2:
                        continue
                    v1, v2 = raws1[0], raws2[0]
                    for op in bin_ops:
                        if op in ("+", "-", "*", "/", "//", "%"):
                            if isinstance(v1, bool) or isinstance(v2, bool):
                                continue
                            if op in ("-", "*", "/", "//", "%") and not (isinstance(v1, (int, float)) and isinstance(v2, (int, float))):
                                continue
                        hit = _try_register(w, f"({e1} {op} {e2})")
                        if hit is not None:
                            return _finish(f"return {hit}" )
                    if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and not isinstance(v1, bool) and not isinstance(v2, bool):
                        for fn2 in ("min", "max"):
                            hit = _try_register(w, f"{fn2}({e1}, {e2})")
                            if hit is not None:
                                return _finish(f"return {hit}")
                    if isinstance(v1, dict):
                        hit = _try_register(w, f"({e1}).get({e2})")
                        if hit is not None:
                            return _finish(f"return {hit}")
                    if len(seen_sigs) >= max_bank_size:
                        break
                if len(seen_sigs) >= max_bank_size:
                    break

    # STUN Stage (Alur et al., CAV 2015): unify partial terms under synthesized predicates!
    # Anti-memorization Occam filter: reject constant expressions forged out of multi-op arithmetic
    # (e.g. `(1 + 2) * 2 == 6`) that read zero parameters and match only a single example.
    allowed_const_reprs = {repr(c) for c in (0, 0.0, 1, -1, 100, True, False, None, "", [], {}, *extra_constants)}

    def _reads_any_param(expr_s: str) -> bool:
        try:
            et = ast.parse(expr_s, mode="eval")
        except SyntaxError:
            return False
        return any(isinstance(nd, ast.Name) and nd.id in param_set for nd in ast.walk(et))

    n_ex = len(examples)
    all_terms: list[tuple[str, tuple[bool, ...], bool]] = []
    for sig, expr_src in seen_sigs.items():
        mask = tuple(sig[i] == target_sig[i] for i in range(n_ex))
        if any(mask):
            reads_p = _reads_any_param(expr_src)
            if not reads_p and expr_src not in allowed_const_reprs and sum(mask) < 2:
                continue
            all_terms.append((expr_src, mask, reads_p))

    # Collect boolean predicates from bank + standard guard predicates
    predicates: list[tuple[str, tuple[bool, ...]]] = []
    seen_pmasks: set[tuple[bool, ...]] = set()

    def _add_pred(p_src: str) -> None:
        try:
            c = compile(f"bool({p_src})", "<pred>", "eval")
        except SyntaxError:
            return
        ok, _, raws = _eval_compiled(c, param_names, inputs, extra_builtins=concept_callables)
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
        ):
            _add_pred(cand_p)
        for c in extra_constants[:6]:
            if isinstance(c, (int, float, str)):
                _add_pred(f"{p} == {c!r}")
                if isinstance(c, (int, float)):
                    _add_pred(f"{p} <= {c!r}")
                    _add_pred(f"{p} < {c!r}")
                    _add_pred(f"{p} >= {c!r}")
    # Also include direct relational boundary guards between two parameters (e.g. `hi <= lo`)
    if len(param_names) >= 2:
        for i_p, pa in enumerate(param_names):
            for pb in param_names[i_p + 1 :]:
                for rel_op in ("==", "<=", "<", ">="):
                    _add_pred(f"{pa} {rel_op} {pb}")

    boundary_pred_count = len(predicates)

    def _reads_all_params(stmt_code: str) -> bool:
        try:
            st_mod = ast.parse(stmt_code)
        except SyntaxError:
            return False
        names = {nd.id for nd in ast.walk(st_mod) if isinstance(nd, ast.Name)}
        return param_set.issubset(names)

    # Stage 3A: Boundary-Guarded 1-level STUN (canonical degenerate boundary guards only;
    # at least one branch — the non-degenerate general law — must depend on ALL parameters)
    for p_src, pmask in predicates[:boundary_pred_count]:
        then_cands = [(e, rp) for e, m, rp in all_terms if all(m[i] for i in range(n_ex) if pmask[i])]
        if not then_cands:
            continue
        else_cands = [(e, rp) for e, m, rp in all_terms if all(m[i] for i in range(n_ex) if not pmask[i])]
        if else_cands:
            e_then, rp_t = min(then_cands, key=lambda x: len(x[0]))
            e_else, rp_e = min(else_cands, key=lambda x: len(x[0]))
            if (rp_t or rp_e) and (_reads_all_params(e_then) or _reads_all_params(e_else)):
                return _finish(f"if {p_src}:\n    return {e_then}\nreturn {e_else}")

    # Stage 3B: Unified Higher-Order Recursion Schemes (HORS: Fold, Hash-Join, Tabulated Fix/DP, AST Algebra)
    # Solomonoff MDL law: a single unified algorithmic recurrence strictly dominates ad-hoc derived case splits.
    hors_body = _synthesize_hors_algorithmic_body(
        param_names=param_names,
        inputs=inputs,
        target_sig=target_sig,
        concept_callables=concept_callables,
    )
    if hors_body is not None:
        return _finish(hors_body)

    # Stage 4: General STUN over parity & synthesized compound predicates
    for p in param_names:
        _add_pred(f"{p} == 1")
        _add_pred(f"{p} % 2 == 0")
    for sig, expr_src in seen_sigs.items():
        if all(t == "bool" for t, _ in sig):
            pmask = tuple(bool(v) for _, v in sig)
            if any(pmask) and not all(pmask) and pmask not in seen_pmasks:
                seen_pmasks.add(pmask)
                predicates.append((expr_src, pmask))

    for p_src, pmask in predicates[boundary_pred_count:]:
        then_cands = [(e, rp) for e, m, rp in all_terms if all(m[i] for i in range(n_ex) if pmask[i])]
        if not then_cands:
            continue
        else_cands = [(e, rp) for e, m, rp in all_terms if all(m[i] for i in range(n_ex) if not pmask[i])]
        if else_cands:
            e_then, rp_t = min(then_cands, key=lambda x: len(x[0]))
            e_else, rp_e = min(else_cands, key=lambda x: len(x[0]))
            if rp_t or rp_e:
                return _finish(f"if {p_src}:\n    return {e_then}\nreturn {e_else}")

    # 2-level STUN: if P1: return E1 / elif P2: return E2 / return E3
    for i, (p1_src, pm1) in enumerate(predicates[:40]):
        t1_cands = [(e, rp) for e, m, rp in all_terms if all(m[k] for k in range(n_ex) if pm1[k])]
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
            t2_cands = [(e, rp) for e, m, rp in all_terms if all(m[k] for k in b2)]
            if not t2_cands:
                continue
            t3_cands = [(e, rp) for e, m, rp in all_terms if all(m[k] for k in b3)]
            if t3_cands:
                e1, rp1 = min(t1_cands, key=lambda x: len(x[0]))
                e2, rp2 = min(t2_cands, key=lambda x: len(x[0]))
                e3, rp3 = min(t3_cands, key=lambda x: len(x[0]))
                if rp1 or rp2 or rp3:
                    return _finish(f"if {p1_src}:\n    return {e1}\nelif {p2_src}:\n    return {e2}\nreturn {e3}")

    return None


def _synthesize_hors_algorithmic_body(
    *,
    param_names: Sequence[str],
    inputs: Sequence[tuple[Any, ...]],
    target_sig: tuple[Any, ...],
    concept_callables: Mapping[str, Any] | None = None,
) -> str | None:
    """Synthesize multi-statement HORS programs verified via `eval_pure_ast_function` (zero `exec`)."""
    from canonical.swe_kernel.concept_library_v1 import (
        build_programmatic_ast_catamorphism_stmts,
        eval_pure_ast_expr,
        eval_pure_ast_function,
    )

    if not inputs or not param_names:
        return None
    params_sig = ", ".join(param_names)

    def _verify_body(body_src: str) -> bool:
        indented = "\n".join("    " + ln for ln in body_src.splitlines())
        try:
            mod = ast.parse(f"def _hors_cand({params_sig}):\n{indented}\n")
            if not mod.body or not isinstance(mod.body[0], ast.FunctionDef):
                return False
            fdef = mod.body[0]
        except SyntaxError:
            return False
        for row, exp_s in zip(inputs, target_sig):
            try:
                out = eval_pure_ast_function(fdef, row, extra_callables=concept_callables, max_steps=25_000)
            except Exception:
                return False
            if _freeze_val(out) != exp_s:
                return False
        return True

    arity = len(param_names)
    p0 = param_names[0]
    first_args0 = [row[0] for row in inputs]

    # 4A. HORS_AST_ALGEBRA: Empirical AST catamorphism when arg0 is str syntax expression
    if arity in (1, 2) and len(inputs) >= 2 and all(isinstance(v, str) and v.strip() for v in first_args0):
        env_p = param_names[1] if arity == 2 else None
        all_denot_match = True
        has_bw = False
        for row, exp_s in zip(inputs, target_sig):
            raw_e = str(row[0]).strip()
            raw_env = dict(row[1]) if arity == 2 and isinstance(row[1], Mapping) else {}
            try:
                pt = ast.parse(raw_e, mode="eval")
                if any(isinstance(sub, (ast.BitAnd, ast.BitOr, ast.BitXor, ast.RShift, ast.Invert)) for sub in ast.walk(pt)):
                    has_bw = True
                val = eval_pure_ast_expr(pt, raw_env)
            except ZeroDivisionError:
                val = 0
            except Exception:
                all_denot_match = False
                break
            if _freeze_val(val) != exp_s:
                all_denot_match = False
                break
        if all_denot_match:
            cata_stmts = build_programmatic_ast_catamorphism_stmts(p0, env_p, has_bitwise=has_bw)
            return "\n".join(ast.unparse(st) for st in cata_stmts)

    # 4B. HORS_FOLD: Stateful folds, deduplication, frequency/group-by, and 2-register prefix/scan DP
    if arity == 1 and all(isinstance(v, (list, tuple, str)) for v in first_args0):
        fold_candidates: list[str] = [
            # Order-preserving linear deduplication (hashable fast-path + unhashable repr fallback)
            f"_seen = set()\n_out = []\nfor _x in {p0}:\n"
            f"    _k = (type(_x), _x) if _x is None or isinstance(_x, (bool, int, float, str, bytes, tuple, frozenset)) else (type(_x), repr(_x))\n"
            f"    if _k not in _seen:\n        _seen.add(_k)\n        _out.append(_x)\nreturn _out",
            # Frequency histogram -> dict or sorted items or mode
            f"_cnt = {{}}\nfor _x in {p0}:\n    _cnt[_x] = _cnt.get(_x, 0) + 1\nreturn _cnt",
            f"_cnt = {{}}\nfor _x in {p0}:\n    _cnt[_x] = _cnt.get(_x, 0) + 1\nreturn sorted(_cnt.items())",
            # Kadane maximum subarray sum (empty-safe 0 & non-empty max)
            f"_cur = 0\n_best = 0\nfor _x in {p0}:\n    _cur = max(0, _cur + _x)\n    _best = max(_best, _cur)\nreturn _best",
            f"if not {p0}:\n    return 0\n_cur = {p0}[0]\n_best = {p0}[0]\nfor _x in {p0}[1:]:\n    _cur = max(_x, _cur + _x)\n    _best = max(_best, _cur)\nreturn _best",
            # Max drawdown (peak - x) and Max single-trade profit (x - valley)
            f"if not {p0}:\n    return 0\n_pk = {p0}[0]\n_dd = 0\nfor _x in {p0}:\n    _pk = max(_pk, _x)\n    _dd = max(_dd, _pk - _x)\nreturn _dd",
            f"if not {p0}:\n    return 0\n_lo = {p0}[0]\n_ gain = 0\n".replace("_ gain", "_gain")
            + f"for _x in {p0}:\n    _gain = max(_gain, _x - _lo)\n    _lo = min(_lo, _x)\nreturn _gain",
            # Longest consecutive equal run / positive streak
            f"if not {p0}:\n    return 0\n_run = 1\n_best = 1\nfor _i in range(1, len({p0})):\n"
            f"    _run = _run + 1 if {p0}[_i] == {p0}[_i - 1] else 1\n    _best = max(_best, _run)\nreturn _best",
            f"_run = 0\n_best = 0\nfor _x in {p0}:\n    _run = _run + 1 if _x > 0 else 0\n    _best = max(_best, _run)\nreturn _best",
            # Key-value pair group-by sum & list aggregation
            f"_grp = {{}}\nfor _k, _v in {p0}:\n    _grp[_k] = _grp.get(_k, 0) + _v\nreturn _grp",
            f"_grp = {{}}\nfor _k, _v in {p0}:\n    _grp.setdefault(_k, []).append(_v)\nreturn _grp",
            # Run-length encoding [(val, count), ...]
            f"if not {p0}:\n    return []\n_out = []\n_cur = {p0}[0]\n_n = 1\nfor _x in {p0}[1:]:\n"
            f"    if _x == _cur:\n        _n += 1\n    else:\n        _out.append((_cur, _n))\n        _cur = _x\n        _n = 1\n_out.append((_cur, _n))\nreturn _out",
        ]
        for cand in fold_candidates:
            if _verify_body(cand):
                return cand

    # 4C. HORS_HASH_JOIN: O(N + M) set-membership filter & relational hash-indexed equijoin
    if arity == 2 and all(isinstance(row[0], (list, tuple)) and isinstance(row[1], (list, tuple, set)) for row in inputs):
        pa, pb = param_names[0], param_names[1]
        join_cands: list[str] = [
            f"_s = set({pb})\nreturn [_x for _x in {pa} if _x in _s]",
            f"_s = set({pb})\nreturn [_x for _x in {pa} if _x not in _s]",
            f"_s = set({pb})\n_seen = set()\n_out = []\nfor _x in {pa}:\n    if _x in _s and _x not in _seen:\n        _seen.add(_x)\n        _out.append(_x)\nreturn _out",
        ]
        # Probe tuple equijoin column indices empirically from non-empty sample rows
        non_empty = [row for row in inputs if row[0] and row[1] and isinstance(row[0][0], tuple) and isinstance(row[1][0], tuple)]
        if non_empty:
            la = min(len(r[0][0]) for r in non_empty)
            lb = min(len(r[1][0]) for r in non_empty)
            for ka in range(min(la, 3)):
                for kb in range(min(lb, 3)):
                    for va in range(min(la, 3)):
                        for vb in range(min(lb, 3)):
                            join_cands.append(
                                f"_idx = {{}}\nfor _r in {pb}:\n    _idx.setdefault(_r[{kb}], []).append(_r[{vb}])\n"
                                f"_out = []\nfor _l in {pa}:\n    for _m in _idx.get(_l[{ka}], ()):\n        _out.append((_l[{va}], _m))\nreturn _out"
                            )
                    join_cands.append(
                        f"_idx = {{}}\nfor _r in {pb}:\n    _idx.setdefault(_r[{kb}], []).append(_r)\n"
                        f"_out = []\nfor _l in {pa}:\n    for _m in _idx.get(_l[{ka}], ()):\n        _out.append((_l, _m))\nreturn _out"
                    )
        for cand in join_cands:
            if _verify_body(cand):
                return cand

    # 4D. HORS_FIX_MEMO: Tabulated structural recursion / Dynamic Programming
    # (i) 1D integer recurrence `f(n)`
    if arity == 1 and all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 60 for v in first_args0):
        obs = {int(row[0]): exp_s[1] for row, exp_s in zip(inputs, target_sig) if exp_s[0] == "int"}
        b0_opts = [obs[0]] if 0 in obs else [0, 1]
        b1_opts = [obs[1]] if 1 in obs else [1, 2, 0]
        b2_opts = [obs[2]] if 2 in obs else [1, 2, 3, 4]
        dp_cands: list[str] = []
        for b0 in b0_opts:
            for b1 in b1_opts:
                for step_expr in ("_dp[_i - 1] + _dp[_i - 2]", "2 * _dp[_i - 1] + _dp[_i - 2]", "_dp[_i - 1] + 2 * _dp[_i - 2]", "_i * _dp[_i - 1]"):
                    dp_cands.append(
                        f"if {p0} <= 0:\n    return {b0}\nif {p0} == 1:\n    return {b1}\n"
                        f"_dp = [{b0}, {b1}] + [0] * ({p0} - 1)\nfor _i in range(2, {p0} + 1):\n    _dp[_i] = {step_expr}\nreturn _dp[{p0}]"
                    )
                for b2 in b2_opts:
                    dp_cands.append(
                        f"if {p0} <= 0:\n    return {b0}\nif {p0} == 1:\n    return {b1}\nif {p0} == 2:\n    return {b2}\n"
                        f"_dp = [{b0}, {b1}, {b2}] + [0] * ({p0} - 2)\nfor _i in range(3, {p0} + 1):\n    _dp[_i] = _dp[_i - 1] + _dp[_i - 2] + _dp[_i - 3]\nreturn _dp[{p0}]"
                    )
        # Catalan DP: C_0 = 1, C_n = sum(C_k * C_{n-1-k})
        dp_cands.append(
            f"if {p0} <= 1:\n    return 1\n_dp = [0] * ({p0} + 1)\n_dp[0] = 1\n_dp[1] = 1\n"
            f"for _i in range(2, {p0} + 1):\n    _s = 0\n    for _k in range(_i):\n        _s += _dp[_k] * _dp[_i - 1 - _k]\n    _dp[_i] = _s\nreturn _dp[{p0}]"
        )
        for cand in dp_cands:
            if _verify_body(cand):
                return cand

    # (ii) Unbounded knapsack / coin-change `(items, target)` DP
    if (
        arity == 2
        and all(isinstance(row[0], (list, tuple)) and isinstance(row[1], int) and not isinstance(row[1], bool) and 0 <= row[1] <= 500 for row in inputs)
    ):
        pc, pt = param_names[0], param_names[1]
        knap_cands = [
            # Min-coins DP (-1 if unreachable)
            f"if {pt} <= 0:\n    return 0\n_inf = {pt} + 1\n_dp = [0] + [_inf] * {pt}\n"
            f"for _a in range(1, {pt} + 1):\n    for _c in {pc}:\n        if 0 < _c <= _a and _dp[_a - _c] + 1 < _dp[_a]:\n            _dp[_a] = _dp[_a - _c] + 1\n"
            f"return -1 if _dp[{pt}] > {pt} else _dp[{pt}]",
            # Combination count DP (ways to sum to target)
            f"_dp = [1] + [0] * max(0, {pt})\nfor _c in {pc}:\n    if _c > 0:\n        for _a in range(_c, {pt} + 1):\n            _dp[_a] += _dp[_a - _c]\nreturn _dp[{pt}] if {pt} >= 0 else 0",
        ]
        for cand in knap_cands:
            if _verify_body(cand):
                return cand

    # (iii) 2-sequence 2D DP (LCS & Levenshtein Edit Distance)
    if arity == 2 and all(isinstance(row[0], (str, list, tuple)) and isinstance(row[1], (str, list, tuple)) for row in inputs):
        pa, pb = param_names[0], param_names[1]
        seq2_cands = [
            # Longest Common Subsequence length
            f"_prev = [0] * (len({pb}) + 1)\nfor _i in range(len({pa})):\n    _cur = [0] * (len({pb}) + 1)\n"
            f"    for _j in range(len({pb})):\n        _cur[_j + 1] = _prev[_j] + 1 if {pa}[_i] == {pb}[_j] else max(_prev[_j + 1], _cur[_j])\n"
            f"    _prev = _cur\nreturn _prev[len({pb})]",
            # Levenshtein Edit Distance
            f"_prev = list(range(len({pb}) + 1))\nfor _i in range(len({pa})):\n    _cur = [_i + 1] + [0] * len({pb})\n"
            f"    for _j in range(len({pb})):\n        _cost = 0 if {pa}[_i] == {pb}[_j] else 1\n"
            f"        _cur[_j + 1] = min(_prev[_j + 1] + 1, _cur[_j] + 1, _prev[_j] + _cost)\n"
            f"    _prev = _cur\nreturn _prev[len({pb})]",
        ]
        for cand in seq2_cands:
            if _verify_body(cand):
                return cand

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
