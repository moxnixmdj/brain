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


_BOT = object()


def _sample_raw(raws: Sequence[Any]) -> Any:
    for x in raws:
        if x is not _BOT:
            return x
    return None


def _eval_compiled(
    code_obj: Any,
    param_names: Sequence[str],
    inputs: Sequence[tuple[Any, ...]],
    extra_builtins: Mapping[str, Any] | None = None,
) -> tuple[bool, tuple[Any, ...], list[Any]]:
    sigs: list[Any] = []
    raws: list[Any] = []
    valid_count = 0
    builtins_ns = _SAFE_EVAL_BUILTINS if not extra_builtins else {**_SAFE_EVAL_BUILTINS, **extra_builtins}
    for row in inputs:
        env = dict(zip(param_names, row))
        try:
            v = eval(code_obj, {"__builtins__": builtins_ns}, env)  # noqa: S307 - pure AST-constructed expression with closed builtins
        except (ZeroDivisionError, IndexError, KeyError, ValueError) as exc:
            # Kleene 3-valued partial-domain bottom `(__BOT__, exc)` so STUN guards (`if not count: return 0`) compose!
            sigs.append(("__BOT__", type(exc).__name__))
            raws.append(_BOT)
            continue
        except Exception:
            return False, (), []
        sigs.append(_freeze_val(v))
        raws.append(v)
        valid_count += 1
    if valid_count == 0:
        return False, (), []
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
                # helped=None, NOT True. This point in the code has only just emitted a body; it
                # has verified nothing. Crediting here was measured to give a concept used solely
                # inside WRONG bodies `verified_hits=1` and a higher own prior (2026-11-04).
                # Verification is the caller's evidence to supply, via `record_concept_outcome`.
                concept_library.record_concept_outcome(cid, helped=None)
            except Exception:
                pass
    return "\n".join(helper_lines) + "\n" + body_src


# Handoff for `collect_admissible=True`: the collected bodies for the most recent call. Cleared at
# the start of each collecting call. Absent unless collection was requested, so ordinary callers
# cannot observe it.
_LAST_ADMISSIBLE: list[str] = []

# Whether the most recent collecting call saw the WHOLE grammar. A capped bank is not a fact about
# the grammar, and reporting "no body reproduces the examples" from a full bank attributes a budget
# failure to the world. Measured 2026-11-04: `2x + 1` IS in the grammar (`((x + 1) + x) / 1`) but is
# only reached after the weight-4 tier overflows a 900-entry bank, so the search said UNRESOLVED.
_LAST_COVERAGE: dict[str, Any] = {}


def last_admissible_bodies() -> list[str]:
    """Bodies collected by the most recent `collect_admissible=True` call."""
    return list(_LAST_ADMISSIBLE)


def last_search_coverage() -> dict[str, Any]:
    """Did the most recent search see the whole grammar, or did it run out of bank?

    `complete=True`  -- the bank never filled and the weight sweep finished, so a body that
                        reproduces the examples does not exist in the grammar at this weight bound.
                        "Not in the grammar" is then a defensible claim.
    `complete=False` -- the bank filled. Absence of a match is a statement about the budget. The
                        caller must NOT report it as a fact about the data.
    """
    return dict(_LAST_COVERAGE)


def _is_statement_block(body_src: str) -> bool:
    """True when `body_src` is already a sequence of statements rather than one expression.

    Only the STUN arms pass statements. Deciding on the TEXT alone is wrong: `return_ratio` and
    `x.returncode` both start with the letters `return` without being statements.
    """
    for line in body_src.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        return stripped.startswith("return ") or stripped == "return" or stripped.endswith(":")
    return False


def synthesize_python_function_body(
    param_names: Sequence[str],
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    extra_constants: Sequence[Any] = (),
    max_weight: int = 4,
    max_bank_size: int = 900,
    *,
    concept_library: Any | None = None,
    collect_admissible: bool = False,
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

    # Populated only when `collect_admissible` is set. The default path is byte-identical: the
    # first match still returns immediately. Adding `collect_admissible` was the honest fix for a
    # vacuous enumeration -- sweeping max_weight still surfaced only one body per weight, because a
    # match returns from inside the search and multiplicity was never observable.
    admissible_bodies: list[str] = []
    global _LAST_COVERAGE
    if collect_admissible:
        _LAST_COVERAGE = {"complete": False, "reason": "did not finish", "bank_size": 0,
                          "bank_capacity": int(max_bank_size)}
        # Clear at the START. Measured 2026-11-04: the 1-level STUN arm below returned a body
        # instead of recording it, so a collecting call could exit without reaching the handoff at
        # the end -- and `last_admissible_bodies()` then reported the PREVIOUS call's bodies to a
        # caller that had every reason to believe it was asking a fresh question. The module
        # answered "12 admissible, PROVISIONAL" for data that admits none. Clearing here makes a
        # stale report impossible regardless of which exit is taken.
        _LAST_ADMISSIBLE.clear()

    def _finish(body_code: str) -> str:
        return _materialize_concept_helpers(body_code, concept_entries, active_lib)

    def _record(expr_src: str) -> None:
        # Two dialects reach this function: an EXPRESSION (from `_try_register`) and a complete
        # BODY (from the STUN arms, which return their own `return`s). Wrapping the second in
        # `return` produced `return if x <= 0:` -- a body that does not compile, recorded as
        # admissible, and then handed to `demand_evidence`, which saw 50 such entries collapse to
        # ONE behaviour signature ("<does not compile>") and reported DETERMINED. Measured
        # 2026-11-04. `_finish` is idempotent for already-`return`ed text, so always routing
        # through it makes the dialect distinction impossible to get wrong.
        body = _finish(expr_src if _is_statement_block(expr_src) else f"return {expr_src}")
        key = " ".join(body.split())
        if key not in {" ".join(b.split()) for b in admissible_bodies}:
            admissible_bodies.append(body)

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
            if collect_admissible:
                _record(expr_src)
                return None
            return expr_src
        if sig not in seen_sigs:
            seen_sigs[sig] = expr_src
            by_weight[weight].append((expr_src, raws))
        return None

    # Weight 1: parameters, parameter attributes, base & harvested constants
    for p in param_names:
        hit = _try_register(1, p)
        if hit is not None:
            if collect_admissible:
                _record(hit)
                continue
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
                if collect_admissible:
                    _record(hit)
                    continue
                return _finish(f"return {hit}")

    seed_consts: list[Any] = [0, 1, 2, -1, 100, True, False, None, "", [], {}]
    for c in extra_constants:
        if c not in seed_consts:
            seed_consts.append(c)
    for c in seed_consts:
        hit = _try_register(1, repr(c))
        if hit is not None:
            if collect_admissible:
                _record(hit)
                continue
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
                if getattr(c_ent, "is_higher_order", False):
                    continue
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
                        if collect_admissible:
                            _record(hit)
                            continue
                        return _finish(f"return {hit}")
                    if len(seen_sigs) >= max_bank_size:
                        break
                if len(seen_sigs) >= max_bank_size:
                    break

        # Unary over weight w-1
        for e1, raws1 in list(by_weight.get(w - 1, [])):
            v0 = _sample_raw(raws1)
            for tmpl in unary_templates:
                # Type-screen using first non-bottom sample value to avoid pointless evals
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
                    if collect_admissible:
                        _record(hit)
                        continue
                    return _finish(f"return {hit}")
            if isinstance(v0, (list, tuple)) and v0:
                # Aggregations over object attributes inside list parameter (e.g. sum(x.price * x.qty for x in items))
                elem0 = v0[0]
                if hasattr(elem0, "__dict__"):
                    e_attrs = sorted(k for k in vars(elem0) if not k.startswith("_"))
                    for a1 in e_attrs:
                        hit = _try_register(w, f"sum(_x.{a1} for _x in {e1})")
                        if hit is not None:
                            if collect_admissible:
                                _record(hit)
                                continue
                            return _finish(f"return {hit}")
                    if len(e_attrs) >= 2:
                        for i_a, a1 in enumerate(e_attrs):
                            for a2 in e_attrs[i_a + 1:]:
                                hit = _try_register(w, f"sum(_x.{a1} * _x.{a2} for _x in {e1})")
                                if hit is not None:
                                    if collect_admissible:
                                        _record(hit)
                                        continue
                                    return _finish(f"return {hit}")

        # Binary combinations w1 + w2 == w (prioritize higher-weight / learned-concept subtrees in outer loop)
        for w1 in range(w - 1, 0, -1):
            w2 = w - w1
            list1 = by_weight.get(w1, [])
            list2 = by_weight.get(w2, [])
            for e1, raws1 in list1:
                v1 = _sample_raw(raws1)
                for e2, raws2 in list2:
                    if e1 == e2:
                        continue
                    v2 = _sample_raw(raws2)
                    for op in bin_ops:
                        if op in ("+", "-", "*", "/", "//", "%"):
                            if isinstance(v1, bool) or isinstance(v2, bool):
                                continue
                            if op in ("-", "*", "/", "//", "%") and not (isinstance(v1, (int, float)) and isinstance(v2, (int, float))):
                                continue
                        hit = _try_register(w, f"({e1} {op} {e2})")
                        if hit is not None:
                            if collect_admissible:
                                _record(hit)
                                continue
                            return _finish(f"return {hit}")
                    if isinstance(v1, (int, float)) and isinstance(v2, (int, float)) and not isinstance(v1, bool) and not isinstance(v2, bool):
                        for fn2 in ("min", "max"):
                            hit = _try_register(w, f"{fn2}({e1}, {e2})")
                            if hit is not None:
                                if collect_admissible:
                                    _record(hit)
                                    continue
                                return _finish(f"return {hit}")
                    if isinstance(v1, dict):
                        hit = _try_register(w, f"({e1}).get({e2})")
                        if hit is not None:
                            if collect_admissible:
                                _record(hit)
                                continue
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
        if not ok or any(x is _BOT for x in raws):
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
            guarded_stun = f"if {p_src}:\n    return {e_then}\nreturn {e_else}"
            if (rp_t or rp_e) and (_reads_all_params(e_then) or _reads_all_params(e_else)):
                if collect_admissible:
                    _record(guarded_stun)
                    continue
                return _finish(guarded_stun)

    # Stage 3B: Constructive Recursion-Scheme Algebra + Levin Universal Search (HORS)
    # Solomonoff-Levin MDL law: constructive recursion morphisms ranked by description bits + log2(steps).
    hors_body = _synthesize_hors_algorithmic_body(
        param_names=param_names,
        inputs=inputs,
        target_sig=target_sig,
        concept_callables=concept_callables,
        ordered_concepts=ordered_concepts,
        concept_library=active_lib,
    )
    if hors_body is not None:
        # MEASURED BUG (merge, 2026-11-04): this early return ignored `collect_admissible`, so a
        # collecting sweep that produced a HORS body returned having recorded NOTHING. The bank read
        # 0/5000 and `demand_evidence` reported SEARCH_TRUNCATED for data whose 12 explanations were
        # sitting one stage away. Every other return site in this function had been guarded; these
        # were not, and the failure was silent because an empty collection is indistinguishable from
        # an empty grammar.
        if collect_admissible:
            _record(hors_body if _is_statement_block(hors_body) else f"return {hors_body}")
        else:
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
            stun1 = f"if {p_src}:\n    return {e_then}\nreturn {e_else}"
            if collect_admissible:
                # Collection records the body UNCONDITIONALLY, even when neither branch mentions a
                # partial-domain term. A piecewise body reproducing every example IS admissible, and
                # an admissible set that omits it understates how many explanations the data permit.
                # This arm was the only early return that ignored the collection flag; failing to
                # record it is the same class of error as failing to see a second explanation.
                _record(stun1)
                continue
            # Default path unchanged: only emit when a branch carries partial-domain evidence.
            if rp_t or rp_e:
                return _finish(stun1)

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
                stun_body = f"if {p1_src}:\n    return {e1}\nelif {p2_src}:\n    return {e2}\nreturn {e3}"
                if collect_admissible:
                    # As above: recorded unconditionally, so a truncated-looking admissible set is
                    # never the artefact of a search heuristic that only emitted partial-domain arms.
                    _record(stun_body)
                    continue
                if rp1 or rp2 or rp3:
                    return _finish(stun_body)

    if collect_admissible:
        # Expose the collection through a module-level handoff. Returning a list here would change
        # the function's contract for every existing caller; the default path is untouched.
        _LAST_ADMISSIBLE.clear()
        _LAST_ADMISSIBLE.extend(admissible_bodies)
        # Completeness is decidable from state the search already keeps: the bank either filled or
        # it did not, and the weight sweep either reached `max_weight` or broke out early. No new
        # enumeration is needed to know whether the enumeration was exhaustive.
        exhausted = len(seen_sigs) >= max_bank_size
        _LAST_COVERAGE = {
            "complete": not exhausted,
            "bank_size": len(seen_sigs),
            "bank_capacity": int(max_bank_size),
            "max_weight": int(max_weight),
            "reason": ("the candidate bank filled before the weight sweep finished, so a missing "
                       "body is a missing BUDGET, not a missing grammar"
                       if exhausted else
                       "the bank did not fill and the sweep finished; absence is a fact about the "
                       "grammar at this weight bound"),
        }
    return None


def _build_product_state_catamorphisms(
    param_names: Sequence[str],
    inputs: Sequence[tuple[Any, ...]],
    target_sig: tuple[Any, ...],
    extra_constants: Sequence[Any] = (),
) -> list[list[ast.stmt]]:
    """Constructive Product-State Catamorphism/Paramorphism AST generator (zero named string templates).

    Builds AST `list[ast.stmt]` bodies by Cartesian composition over:
      - Scalar Product-State Scans `d in {1, 2, 3}`: `(SeedAlgebra x CoordinateStepGrammar x Projection)`
      - Sort-Directed Quotient / Free-Monoid / Relational Hash Homomorphisms inferred from output sorts.
    """
    arity = len(param_names)
    p0 = param_names[0]
    first_args0 = [row[0] for row in inputs]
    expected_sorts = {s[0] for s in target_sig}
    candidates: list[list[ast.stmt]] = []

    def _N(name: str, store: bool = False) -> ast.Name:
        return ast.Name(id=name, ctx=ast.Store() if store else ast.Load())

    def _C(val: Any) -> ast.Constant:
        return ast.Constant(value=val)

    def _B(left: ast.expr, op: ast.operator, right: ast.expr) -> ast.BinOp:
        return ast.BinOp(left=left, op=op, right=right)

    def _Call(fn: str, *args: ast.expr) -> ast.Call:
        return ast.Call(func=_N(fn), args=list(args), keywords=[])

    if arity == 1 and all(isinstance(v, (list, tuple, str)) for v in first_args0):
        # 1. Scalar Product-State Scans (when expected sort is numeric `int` / `float`)
        if expected_sorts.issubset({"int", "float"}):
            # (a) Neutral-seeded 2-register simultaneous tuple transition:
            #     `_s0, _s1 = init0, init1; for _x in p0: _s0, _s1 = step0, step1; return proj`
            s0_steps_neutral: list[tuple[ast.expr, ast.expr]] = [
                # (step0(_s0, _s1, _x), step1(_s0, _s1, _x))
                (_Call("max", _C(0), _B(_N("_s0"), ast.Add(), _N("_x"))), _Call("max", _N("_s1"), _Call("max", _C(0), _B(_N("_s0"), ast.Add(), _N("_x"))))),
                (_N("_s1"), _Call("max", _N("_s1"), _B(_N("_s0"), ast.Add(), _N("_x")))),
                (
                    ast.IfExp(
                        test=ast.Compare(left=_N("_x"), ops=[ast.Gt()], comparators=[_C(0)]),
                        body=_B(_N("_s0"), ast.Add(), _C(1)),
                        orelse=_C(0),
                    ),
                    _Call(
                        "max",
                        _N("_s1"),
                        ast.IfExp(
                            test=ast.Compare(left=_N("_x"), ops=[ast.Gt()], comparators=[_C(0)]),
                            body=_B(_N("_s0"), ast.Add(), _C(1)),
                            orelse=_C(0),
                        ),
                    ),
                ),
            ]
            for e_step0, e_step1 in s0_steps_neutral:
                candidates.append(
                    [
                        ast.Assign(targets=[ast.Tuple(elts=[_N("_s0", True), _N("_s1", True)], ctx=ast.Store())], value=ast.Tuple(elts=[_C(0), _C(0)], ctx=ast.Load())),
                        ast.For(
                            target=_N("_x", True),
                            iter=_N(p0),
                            body=[
                                ast.Assign(
                                    targets=[ast.Tuple(elts=[_N("_s0", True), _N("_s1", True)], ctx=ast.Store())],
                                    value=ast.Tuple(elts=[e_step0, e_step1], ctx=ast.Load()),
                                )
                            ],
                            orelse=[],
                        ),
                        ast.Return(value=_N("_s1")),
                    ]
                )

            # (b) Head-seeded 2-register & 3-register product-state scans (`if not p0: return 0`)
            head0 = ast.Subscript(value=_N(p0), slice=_C(0), ctx=ast.Load())
            tail_slice = ast.Subscript(value=_N(p0), slice=ast.Slice(lower=_C(1), upper=None, step=None), ctx=ast.Load())
            head_seeded_specs: list[tuple[list[ast.expr], list[ast.expr]]] = [
                # (init_tuple, simultaneous_step_tuple)
                ([head0, head0], [_Call("max", _N("_x"), _B(_N("_s0"), ast.Add(), _N("_x"))), _Call("max", _N("_s1"), _Call("max", _N("_x"), _B(_N("_s0"), ast.Add(), _N("_x"))))]),
                ([head0, head0], [_Call("min", _N("_x"), _B(_N("_s0"), ast.Add(), _N("_x"))), _Call("min", _N("_s1"), _Call("min", _N("_x"), _B(_N("_s0"), ast.Add(), _N("_x"))))]),
                ([head0, _C(0)], [_Call("max", _N("_s0"), _N("_x")), _Call("max", _N("_s1"), _B(_Call("max", _N("_s0"), _N("_x")), ast.Sub(), _N("_x")))]),
                ([head0, _C(0)], [_Call("min", _N("_s0"), _N("_x")), _Call("max", _N("_s1"), _B(_N("_x"), ast.Sub(), _Call("min", _N("_s0"), _N("_x"))))]),
                # d = 3 extremal sign-envelope product algebra (min_envelope, max_envelope, global_best)
                (
                    [head0, head0, head0],
                    [
                        _Call("min", _N("_x"), _B(_N("_s0"), ast.Mult(), _N("_x")), _B(_N("_s1"), ast.Mult(), _N("_x"))),
                        _Call("max", _N("_x"), _B(_N("_s0"), ast.Mult(), _N("_x")), _B(_N("_s1"), ast.Mult(), _N("_x"))),
                        _Call("max", _N("_s2"), _Call("max", _N("_x"), _B(_N("_s0"), ast.Mult(), _N("_x")), _B(_N("_s1"), ast.Mult(), _N("_x")))),
                    ],
                ),
            ]
            for inits, steps_t in head_seeded_specs:
                d_dim = len(inits)
                reg_store = [ _N(f"_s{k}", True) for k in range(d_dim) ]
                candidates.append(
                    [
                        ast.If(test=ast.UnaryOp(op=ast.Not(), operand=_N(p0)), body=[ast.Return(value=_C(0))], orelse=[]),
                        ast.Assign(targets=[ast.Tuple(elts=reg_store, ctx=ast.Store())], value=ast.Tuple(elts=inits, ctx=ast.Load())),
                        ast.For(
                            target=_N("_x", True),
                            iter=tail_slice,
                            body=[
                                ast.Assign(
                                    targets=[ast.Tuple(elts=[_N(f"_s{k}", True) for k in range(d_dim)], ctx=ast.Store())],
                                    value=ast.Tuple(elts=steps_t, ctx=ast.Load()),
                                )
                            ],
                            orelse=[],
                        ),
                        ast.Return(value=_N(f"_s{d_dim - 1}")),
                    ]
                )

            # (c) Adjacent-pair relational window paramorphism (`p0[_i] rel p0[_i - 1]`)
            for cmp_op in (ast.Eq(), ast.Gt(), ast.Lt()):
                cur_i = ast.Subscript(value=_N(p0), slice=_N("_i"), ctx=ast.Load())
                prev_i = ast.Subscript(value=_N(p0), slice=_B(_N("_i"), ast.Sub(), _C(1)), ctx=ast.Load())
                next_run = ast.IfExp(
                    test=ast.Compare(left=cur_i, ops=[cmp_op], comparators=[prev_i]),
                    body=_B(_N("_s0"), ast.Add(), _C(1)),
                    orelse=_C(1),
                )
                candidates.append(
                    [
                        ast.If(test=ast.UnaryOp(op=ast.Not(), operand=_N(p0)), body=[ast.Return(value=_C(0))], orelse=[]),
                        ast.Assign(targets=[ast.Tuple(elts=[_N("_s0", True), _N("_s1", True)], ctx=ast.Store())], value=ast.Tuple(elts=[_C(1), _C(1)], ctx=ast.Load())),
                        ast.For(
                            target=_N("_i", True),
                            iter=_Call("range", _C(1), _Call("len", _N(p0))),
                            body=[
                                ast.Assign(targets=[_N("_s0", True)], value=next_run),
                                ast.Assign(targets=[_N("_s1", True)], value=_Call("max", _N("_s1"), _N("_s0"))),
                            ],
                            orelse=[],
                        ),
                        ast.Return(value=_N("_s1")),
                    ]
                )

        # 2. Sort-Directed Free Quotient & Commutative Monoid Homomorphisms (`list` / `dict` outputs)
        if "list" in expected_sorts:
            # Free set-quotient order-preserving homomorphism (hashable key + repr fallback)
            hash_types = ast.Tuple(elts=[_N(t) for t in ("bool", "int", "float", "str", "bytes", "tuple", "frozenset")], ctx=ast.Load())
            key_expr = ast.IfExp(
                test=ast.BoolOp(
                    op=ast.Or(),
                    values=[
                        ast.Compare(left=_N("_x"), ops=[ast.Is()], comparators=[_C(None)]),
                        _Call("isinstance", _N("_x"), hash_types),
                    ],
                ),
                body=ast.Tuple(elts=[_Call("type", _N("_x")), _N("_x")], ctx=ast.Load()),
                orelse=ast.Tuple(elts=[_Call("type", _N("_x")), _Call("repr", _N("_x"))], ctx=ast.Load()),
            )
            candidates.append(
                [
                    ast.Assign(targets=[_N("_seen", True)], value=_Call("set")),
                    ast.Assign(targets=[_N("_out", True)], value=ast.List(elts=[], ctx=ast.Load())),
                    ast.For(
                        target=_N("_x", True),
                        iter=_N(p0),
                        body=[
                            ast.Assign(targets=[_N("_k", True)], value=key_expr),
                            ast.If(
                                test=ast.Compare(left=_N("_k"), ops=[ast.NotIn()], comparators=[_N("_seen")]),
                                body=[
                                    ast.Expr(value=ast.Call(func=ast.Attribute(value=_N("_seen"), attr="add", ctx=ast.Load()), args=[_N("_k")], keywords=[])),
                                    ast.Expr(value=ast.Call(func=ast.Attribute(value=_N("_out"), attr="append", ctx=ast.Load()), args=[_N("_x")], keywords=[])),
                                ],
                                orelse=[],
                            ),
                        ],
                        orelse=[],
                    ),
                    ast.Return(value=_N("_out")),
                ]
            )
            # Adjacent equivalence quotient homomorphism (Run-Length Quotient)
            head0 = ast.Subscript(value=_N(p0), slice=_C(0), ctx=ast.Load())
            tail_s = ast.Subscript(value=_N(p0), slice=ast.Slice(lower=_C(1), upper=None, step=None), ctx=ast.Load())
            candidates.append(
                [
                    ast.If(test=ast.UnaryOp(op=ast.Not(), operand=_N(p0)), body=[ast.Return(value=ast.List(elts=[], ctx=ast.Load()))], orelse=[]),
                    ast.Assign(targets=[_N("_out", True)], value=ast.List(elts=[], ctx=ast.Load())),
                    ast.Assign(targets=[ast.Tuple(elts=[_N("_c", True), _N("_n", True)], ctx=ast.Store())], value=ast.Tuple(elts=[head0, _C(1)], ctx=ast.Load())),
                    ast.For(
                        target=_N("_x", True),
                        iter=tail_s,
                        body=[
                            ast.If(
                                test=ast.Compare(left=_N("_x"), ops=[ast.Eq()], comparators=[_N("_c")]),
                                body=[ast.Assign(targets=[_N("_n", True)], value=_B(_N("_n"), ast.Add(), _C(1)))],
                                orelse=[
                                    ast.Expr(value=ast.Call(func=ast.Attribute(value=_N("_out"), attr="append", ctx=ast.Load()), args=[ast.Tuple(elts=[_N("_c"), _N("_n")], ctx=ast.Load())], keywords=[])),
                                    ast.Assign(targets=[ast.Tuple(elts=[_N("_c", True), _N("_n", True)], ctx=ast.Store())], value=ast.Tuple(elts=[_N("_x"), _C(1)], ctx=ast.Load())),
                                ],
                            )
                        ],
                        orelse=[],
                    ),
                    ast.Expr(value=ast.Call(func=ast.Attribute(value=_N("_out"), attr="append", ctx=ast.Load()), args=[ast.Tuple(elts=[_N("_c"), _N("_n")], ctx=ast.Load())], keywords=[])),
                    ast.Return(value=_N("_out")),
                ]
            )

        if expected_sorts & {"dict", "list"}:
            # Free Commutative Monoid Homomorphism: count histogram & pair group-by (sum / free-list)
            for proj_sorted in (False, True):
                if proj_sorted and "list" not in expected_sorts:
                    continue
                if not proj_sorted and "dict" not in expected_sorts:
                    continue
                ret_e: ast.expr = (
                    _Call("sorted", ast.Call(func=ast.Attribute(value=_N("_m"), attr="items", ctx=ast.Load()), args=[], keywords=[]))
                    if proj_sorted
                    else _N("_m")
                )
                candidates.append(
                    [
                        ast.Assign(targets=[_N("_m", True)], value=ast.Dict(keys=[], values=[])),
                        ast.For(
                            target=_N("_x", True),
                            iter=_N(p0),
                            body=[
                                ast.Assign(
                                    targets=[ast.Subscript(value=_N("_m"), slice=_N("_x"), ctx=ast.Store())],
                                    value=_B(
                                        ast.Call(func=ast.Attribute(value=_N("_m"), attr="get", ctx=ast.Load()), args=[_N("_x"), _C(0)], keywords=[]),
                                        ast.Add(),
                                        _C(1),
                                    ),
                                )
                            ],
                            orelse=[],
                        ),
                        ast.Return(value=ret_e),
                    ]
                )
            if "dict" in expected_sorts:
                # Pair-projection monoids `(k, v) -> sum` and `(k, v) -> list`
                candidates.append(
                    [
                        ast.Assign(targets=[_N("_m", True)], value=ast.Dict(keys=[], values=[])),
                        ast.For(
                            target=ast.Tuple(elts=[_N("_k", True), _N("_v", True)], ctx=ast.Store()),
                            iter=_N(p0),
                            body=[
                                ast.Assign(
                                    targets=[ast.Subscript(value=_N("_m"), slice=_N("_k"), ctx=ast.Store())],
                                    value=_B(
                                        ast.Call(func=ast.Attribute(value=_N("_m"), attr="get", ctx=ast.Load()), args=[_N("_k"), _C(0)], keywords=[]),
                                        ast.Add(),
                                        _N("_v"),
                                    ),
                                )
                            ],
                            orelse=[],
                        ),
                        ast.Return(value=_N("_m")),
                    ]
                )
                candidates.append(
                    [
                        ast.Assign(targets=[_N("_m", True)], value=ast.Dict(keys=[], values=[])),
                        ast.For(
                            target=ast.Tuple(elts=[_N("_k", True), _N("_v", True)], ctx=ast.Store()),
                            iter=_N(p0),
                            body=[
                                ast.Expr(
                                    value=ast.Call(
                                        func=ast.Attribute(
                                            value=ast.Call(
                                                func=ast.Attribute(value=_N("_m"), attr="setdefault", ctx=ast.Load()),
                                                args=[_N("_k"), ast.List(elts=[], ctx=ast.Load())],
                                                keywords=[],
                                            ),
                                            attr="append",
                                            ctx=ast.Load(),
                                        ),
                                        args=[_N("_v")],
                                        keywords=[],
                                    )
                                )
                            ],
                            orelse=[],
                        ),
                        ast.Return(value=_N("_m")),
                    ]
                )

    # 3. Binary Relational Algebra Homomorphisms (`(seq_a, seq_b) -> list`)
    if arity == 2 and all(isinstance(row[0], (list, tuple)) and isinstance(row[1], (list, tuple, set)) for row in inputs):
        pa, pb = param_names[0], param_names[1]
        for cmp_op in (ast.In(), ast.NotIn()):
            candidates.append(
                [
                    ast.Assign(targets=[_N("_s", True)], value=_Call("set", _N(pb))),
                    ast.Return(
                        value=ast.ListComp(
                            elt=_N("_x"),
                            generators=[
                                ast.comprehension(
                                    target=_N("_x", True),
                                    iter=_N(pa),
                                    ifs=[ast.Compare(left=_N("_x"), ops=[cmp_op], comparators=[_N("_s")])],
                                    is_async=0,
                                )
                            ],
                        )
                    ),
                ]
            )
        non_empty = [row for row in inputs if row[0] and row[1] and isinstance(row[0][0], tuple) and isinstance(row[1][0], tuple)]
        if non_empty:
            la = min(len(r[0][0]) for r in non_empty)
            lb = min(len(r[1][0]) for r in non_empty)
            for ka in range(min(la, 3)):
                for kb in range(min(lb, 3)):
                    for va in range(min(la, 3)):
                        for vb in range(min(lb, 3)):
                            candidates.append(
                                [
                                    ast.Assign(targets=[_N("_idx", True)], value=ast.Dict(keys=[], values=[])),
                                    ast.For(
                                        target=_N("_r", True),
                                        iter=_N(pb),
                                        body=[
                                            ast.Expr(
                                                value=ast.Call(
                                                    func=ast.Attribute(
                                                        value=ast.Call(
                                                            func=ast.Attribute(value=_N("_idx"), attr="setdefault", ctx=ast.Load()),
                                                            args=[ast.Subscript(value=_N("_r"), slice=_C(kb), ctx=ast.Load()), ast.List(elts=[], ctx=ast.Load())],
                                                            keywords=[],
                                                        ),
                                                        attr="append",
                                                        ctx=ast.Load(),
                                                    ),
                                                    args=[ast.Subscript(value=_N("_r"), slice=_C(vb), ctx=ast.Load())],
                                                    keywords=[],
                                                )
                                            )
                                        ],
                                        orelse=[],
                                    ),
                                    ast.Assign(targets=[_N("_out", True)], value=ast.List(elts=[], ctx=ast.Load())),
                                    ast.For(
                                        target=_N("_l", True),
                                        iter=_N(pa),
                                        body=[
                                            ast.For(
                                                target=_N("_m", True),
                                                iter=ast.Call(
                                                    func=ast.Attribute(value=_N("_idx"), attr="get", ctx=ast.Load()),
                                                    args=[ast.Subscript(value=_N("_l"), slice=_C(ka), ctx=ast.Load()), ast.Tuple(elts=[], ctx=ast.Load())],
                                                    keywords=[],
                                                ),
                                                body=[
                                                    ast.Expr(
                                                        value=ast.Call(
                                                            func=ast.Attribute(value=_N("_out"), attr="append", ctx=ast.Load()),
                                                            args=[ast.Tuple(elts=[ast.Subscript(value=_N("_l"), slice=_C(va), ctx=ast.Load()), _N("_m")], ctx=ast.Load())],
                                                            keywords=[],
                                                        )
                                                    )
                                                ],
                                                orelse=[],
                                            )
                                        ],
                                        orelse=[],
                                    ),
                                    ast.Return(value=_N("_out")),
                                ]
                            )
    return candidates


def _build_semiring_dynamorphisms(
    param_names: Sequence[str],
    inputs: Sequence[tuple[Any, ...]],
    target_sig: tuple[Any, ...],
) -> list[list[ast.stmt]]:
    """Constructive Semiring Dynamorphism AST generator: `(Semiring x Schedule x IndexSpace)` (zero named templates).

    Composes algebraic Semirings `(TropicalMinPlus, TropicalMaxPlus, CountingRing, BooleanLattice)`
    with iteration schedules (`forward` unbounded vs `reverse` 0/1 single-use!) and index spaces
    (`1D_prefix`, `1D_capacity`, `2D_alignment`).
    """
    arity = len(param_names)
    p0 = param_names[0]
    first_args0 = [row[0] for row in inputs]
    expected_sorts = {s[0] for s in target_sig}
    candidates: list[list[ast.stmt]] = []

    def _N(name: str, store: bool = False) -> ast.Name:
        return ast.Name(id=name, ctx=ast.Store() if store else ast.Load())

    def _C(val: Any) -> ast.Constant:
        return ast.Constant(value=val)

    def _B(left: ast.expr, op: ast.operator, right: ast.expr) -> ast.BinOp:
        return ast.BinOp(left=left, op=op, right=right)

    def _Call(fn: str, *args: ast.expr) -> ast.Call:
        return ast.Call(func=_N(fn), args=list(args), keywords=[])

    # Space A: 1D Integer Prefix Dynamorphisms `(n,) -> int` (linear k-step & Cauchy convolution semiring)
    if arity == 1 and all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 60 for v in first_args0):
        obs = {int(row[0]): exp_s[1] for row, exp_s in zip(inputs, target_sig) if exp_s[0] == "int"}
        b0_opts = [obs[0]] if 0 in obs else [0, 1]
        b1_opts = [obs[1]] if 1 in obs else [1, 2, 0]
        b2_opts = [obs[2]] if 2 in obs else [1, 2, 3, 4]
        dp_i1 = ast.Subscript(value=_N("_dp"), slice=_B(_N("_i"), ast.Sub(), _C(1)), ctx=ast.Load())
        dp_i2 = ast.Subscript(value=_N("_dp"), slice=_B(_N("_i"), ast.Sub(), _C(2)), ctx=ast.Load())
        dp_i3 = ast.Subscript(value=_N("_dp"), slice=_B(_N("_i"), ast.Sub(), _C(3)), ctx=ast.Load())

        step2_exprs: list[ast.expr] = [
            _B(dp_i1, ast.Add(), dp_i2),
            _B(_B(_C(2), ast.Mult(), dp_i1), ast.Add(), dp_i2),
            _B(dp_i1, ast.Add(), _B(_C(2), ast.Mult(), dp_i2)),
            _B(_N("_i"), ast.Mult(), dp_i1),
        ]
        for b0 in b0_opts:
            for b1 in b1_opts:
                for step_e in step2_exprs:
                    candidates.append(
                        [
                            ast.If(test=ast.Compare(left=_N(p0), ops=[ast.LtE()], comparators=[_C(0)]), body=[ast.Return(value=_C(b0))], orelse=[]),
                            ast.If(test=ast.Compare(left=_N(p0), ops=[ast.Eq()], comparators=[_C(1)]), body=[ast.Return(value=_C(b1))], orelse=[]),
                            ast.Assign(
                                targets=[_N("_dp", True)],
                                value=_B(ast.List(elts=[_C(b0), _C(b1)], ctx=ast.Load()), ast.Add(), _B(ast.List(elts=[_C(0)], ctx=ast.Load()), ast.Mult(), _B(_N(p0), ast.Sub(), _C(1)))),
                            ),
                            ast.For(
                                target=_N("_i", True),
                                iter=_Call("range", _C(2), _B(_N(p0), ast.Add(), _C(1))),
                                body=[ast.Assign(targets=[ast.Subscript(value=_N("_dp"), slice=_N("_i"), ctx=ast.Store())], value=step_e)],
                                orelse=[],
                            ),
                            ast.Return(value=ast.Subscript(value=_N("_dp"), slice=_N(p0), ctx=ast.Load())),
                        ]
                    )
                for b2 in b2_opts:
                    candidates.append(
                        [
                            ast.If(test=ast.Compare(left=_N(p0), ops=[ast.LtE()], comparators=[_C(0)]), body=[ast.Return(value=_C(b0))], orelse=[]),
                            ast.If(test=ast.Compare(left=_N(p0), ops=[ast.Eq()], comparators=[_C(1)]), body=[ast.Return(value=_C(b1))], orelse=[]),
                            ast.If(test=ast.Compare(left=_N(p0), ops=[ast.Eq()], comparators=[_C(2)]), body=[ast.Return(value=_C(b2))], orelse=[]),
                            ast.Assign(
                                targets=[_N("_dp", True)],
                                value=_B(ast.List(elts=[_C(b0), _C(b1), _C(b2)], ctx=ast.Load()), ast.Add(), _B(ast.List(elts=[_C(0)], ctx=ast.Load()), ast.Mult(), _B(_N(p0), ast.Sub(), _C(2)))),
                            ),
                            ast.For(
                                target=_N("_i", True),
                                iter=_Call("range", _C(3), _B(_N(p0), ast.Add(), _C(1))),
                                body=[ast.Assign(targets=[ast.Subscript(value=_N("_dp"), slice=_N("_i"), ctx=ast.Store())], value=_B(_B(dp_i1, ast.Add(), dp_i2), ast.Add(), dp_i3))],
                                orelse=[],
                            ),
                            ast.Return(value=ast.Subscript(value=_N("_dp"), slice=_N(p0), ctx=ast.Load())),
                        ]
                    )
        # Cauchy convolution semiring over `(+, *, 0, 1)`
        candidates.append(
            [
                ast.If(test=ast.Compare(left=_N(p0), ops=[ast.LtE()], comparators=[_C(1)]), body=[ast.Return(value=_C(1))], orelse=[]),
                ast.Assign(targets=[_N("_dp", True)], value=_B(ast.List(elts=[_C(1), _C(1)], ctx=ast.Load()), ast.Add(), _B(ast.List(elts=[_C(0)], ctx=ast.Load()), ast.Mult(), _B(_N(p0), ast.Sub(), _C(1))))),
                ast.For(
                    target=_N("_i", True),
                    iter=_Call("range", _C(2), _B(_N(p0), ast.Add(), _C(1))),
                    body=[
                        ast.Assign(targets=[_N("_s", True)], value=_C(0)),
                        ast.For(
                            target=_N("_k", True),
                            iter=_Call("range", _N("_i")),
                            body=[
                                ast.Assign(
                                    targets=[_N("_s", True)],
                                    value=_B(
                                        _N("_s"),
                                        ast.Add(),
                                        _B(
                                            ast.Subscript(value=_N("_dp"), slice=_N("_k"), ctx=ast.Load()),
                                            ast.Mult(),
                                            ast.Subscript(value=_N("_dp"), slice=_B(_B(_N("_i"), ast.Sub(), _C(1)), ast.Sub(), _N("_k")), ctx=ast.Load()),
                                        ),
                                    ),
                                )
                            ],
                            orelse=[],
                        ),
                        ast.Assign(targets=[ast.Subscript(value=_N("_dp"), slice=_N("_i"), ctx=ast.Store())], value=_N("_s")),
                    ],
                    orelse=[],
                ),
                ast.Return(value=ast.Subscript(value=_N("_dp"), slice=_N(p0), ctx=ast.Load())),
            ]
        )

    # Space B: 1D Capacity Semiring Dynamorphisms `(items, target)` — BOTH Forward (Unbounded) AND Reverse (0/1 Single-Use)!
    if (
        arity == 2
        and all(isinstance(row[0], (list, tuple)) and isinstance(row[1], int) and not isinstance(row[1], bool) and 0 <= row[1] <= 500 for row in inputs)
    ):
        pc, pt = param_names[0], param_names[1]
        has_pair_items = any(row[0] and isinstance(row[0][0], (tuple, list)) and len(row[0][0]) == 2 for row in inputs)

        if has_pair_items and expected_sorts.issubset({"int", "float"}):
            # TropicalMaxPlus `(max, +, 0, 0)` over `(weight, value)` items under Reverse (0/1) & Forward (Unbounded) schedules
            for reverse_01 in (True, False):
                cap_iter = _Call("range", _N(pt), _B(_N("_w"), ast.Sub(), _C(1)), _C(-1)) if reverse_01 else _Call("range", _N("_w"), _B(_N(pt), ast.Add(), _C(1)))
                candidates.append(
                    [
                        ast.Assign(targets=[_N("_dp", True)], value=_B(ast.List(elts=[_C(0)], ctx=ast.Load()), ast.Mult(), _B(_Call("max", _C(0), _N(pt)), ast.Add(), _C(1)))),
                        ast.For(
                            target=ast.Tuple(elts=[_N("_w", True), _N("_v", True)], ctx=ast.Store()),
                            iter=_N(pc),
                            body=[
                                ast.If(
                                    test=ast.Compare(left=_N("_w"), ops=[ast.Gt()], comparators=[_C(0)]),
                                    body=[
                                        ast.For(
                                            target=_N("_a", True),
                                            iter=cap_iter,
                                            body=[
                                                ast.Assign(
                                                    targets=[ast.Subscript(value=_N("_dp"), slice=_N("_a"), ctx=ast.Store())],
                                                    value=_Call("max", ast.Subscript(value=_N("_dp"), slice=_N("_a"), ctx=ast.Load()), _B(ast.Subscript(value=_N("_dp"), slice=_B(_N("_a"), ast.Sub(), _N("_w")), ctx=ast.Load()), ast.Add(), _N("_v"))),
                                                )
                                            ],
                                            orelse=[],
                                        )
                                    ],
                                    orelse=[],
                                )
                            ],
                            orelse=[],
                        ),
                        ast.Return(value=ast.Subscript(value=_N("_dp"), slice=_N(pt), ctx=ast.Load())),
                    ]
                )
        elif "bool" in expected_sorts:
            # BooleanLattice `(or, and, False, True)` over Reverse (0/1 Subset-Sum) & Forward (Unbounded Reachability)
            for reverse_01 in (True, False):
                cap_iter = _Call("range", _N(pt), _B(_N("_c"), ast.Sub(), _C(1)), _C(-1)) if reverse_01 else _Call("range", _N("_c"), _B(_N(pt), ast.Add(), _C(1)))
                candidates.append(
                    [
                        ast.If(test=ast.Compare(left=_N(pt), ops=[ast.Lt()], comparators=[_C(0)]), body=[ast.Return(value=_C(False))], orelse=[]),
                        ast.Assign(targets=[_N("_dp", True)], value=_B(ast.List(elts=[_C(True)], ctx=ast.Load()), ast.Add(), _B(ast.List(elts=[_C(False)], ctx=ast.Load()), ast.Mult(), _N(pt)))),
                        ast.For(
                            target=_N("_c", True),
                            iter=_N(pc),
                            body=[
                                ast.If(
                                    test=ast.Compare(left=_N("_c"), ops=[ast.Gt()], comparators=[_C(0)]),
                                    body=[
                                        ast.For(
                                            target=_N("_a", True),
                                            iter=cap_iter,
                                            body=[
                                                ast.Assign(
                                                    targets=[ast.Subscript(value=_N("_dp"), slice=_N("_a"), ctx=ast.Store())],
                                                    value=ast.BoolOp(
                                                        op=ast.Or(),
                                                        values=[
                                                            ast.Subscript(value=_N("_dp"), slice=_N("_a"), ctx=ast.Load()),
                                                            ast.Subscript(value=_N("_dp"), slice=_B(_N("_a"), ast.Sub(), _N("_c")), ctx=ast.Load()),
                                                        ],
                                                    ),
                                                )
                                            ],
                                            orelse=[],
                                        )
                                    ],
                                    orelse=[],
                                )
                            ],
                            orelse=[],
                        ),
                        ast.Return(value=ast.Subscript(value=_N("_dp"), slice=_N(pt), ctx=ast.Load())),
                    ]
                )
        else:
            # TropicalMinPlus `(min, +, inf, 0)` & CountingRing `(+, *, 0, 1)` x Schedule `{forward, reverse}`
            for reverse_01 in (False, True):
                cap_iter = _Call("range", _N(pt), _B(_N("_c"), ast.Sub(), _C(1)), _C(-1)) if reverse_01 else _Call("range", _N("_c"), _B(_N(pt), ast.Add(), _C(1)))
                # TropicalMinPlus unit-step cost (`min_items` to reach target, `-1` when unreachable)
                candidates.append(
                    [
                        ast.If(test=ast.Compare(left=_N(pt), ops=[ast.LtE()], comparators=[_C(0)]), body=[ast.Return(value=_C(0))], orelse=[]),
                        ast.Assign(targets=[_N("_inf", True)], value=_B(_N(pt), ast.Add(), _C(1))),
                        ast.Assign(targets=[_N("_dp", True)], value=_B(ast.List(elts=[_C(0)], ctx=ast.Load()), ast.Add(), _B(ast.List(elts=[_N("_inf")], ctx=ast.Load()), ast.Mult(), _N(pt)))),
                        ast.For(
                            target=_N("_c", True),
                            iter=_N(pc),
                            body=[
                                ast.If(
                                    test=ast.Compare(left=_N("_c"), ops=[ast.Gt()], comparators=[_C(0)]),
                                    body=[
                                        ast.For(
                                            target=_N("_a", True),
                                            iter=cap_iter,
                                            body=[
                                                ast.Assign(
                                                    targets=[ast.Subscript(value=_N("_dp"), slice=_N("_a"), ctx=ast.Store())],
                                                    value=_Call(
                                                        "min",
                                                        ast.Subscript(value=_N("_dp"), slice=_N("_a"), ctx=ast.Load()),
                                                        _B(ast.Subscript(value=_N("_dp"), slice=_B(_N("_a"), ast.Sub(), _N("_c")), ctx=ast.Load()), ast.Add(), _C(1)),
                                                    ),
                                                )
                                            ],
                                            orelse=[],
                                        )
                                    ],
                                    orelse=[],
                                )
                            ],
                            orelse=[],
                        ),
                        ast.Return(
                            value=ast.IfExp(
                                test=ast.Compare(left=ast.Subscript(value=_N("_dp"), slice=_N(pt), ctx=ast.Load()), ops=[ast.Gt()], comparators=[_N(pt)]),
                                body=_C(-1),
                                orelse=ast.Subscript(value=_N("_dp"), slice=_N(pt), ctx=ast.Load()),
                            )
                        ),
                    ]
                )
                # CountingRing `(+, *, 0, 1)` ways to reach capacity
                candidates.append(
                    [
                        ast.If(test=ast.Compare(left=_N(pt), ops=[ast.Lt()], comparators=[_C(0)]), body=[ast.Return(value=_C(0))], orelse=[]),
                        ast.Assign(targets=[_N("_dp", True)], value=_B(ast.List(elts=[_C(1)], ctx=ast.Load()), ast.Add(), _B(ast.List(elts=[_C(0)], ctx=ast.Load()), ast.Mult(), _N(pt)))),
                        ast.For(
                            target=_N("_c", True),
                            iter=_N(pc),
                            body=[
                                ast.If(
                                    test=ast.Compare(left=_N("_c"), ops=[ast.Gt()], comparators=[_C(0)]),
                                    body=[
                                        ast.For(
                                            target=_N("_a", True),
                                            iter=cap_iter,
                                            body=[
                                                ast.Assign(
                                                    targets=[ast.Subscript(value=_N("_dp"), slice=_N("_a"), ctx=ast.Store())],
                                                    value=_B(
                                                        ast.Subscript(value=_N("_dp"), slice=_N("_a"), ctx=ast.Load()),
                                                        ast.Add(),
                                                        ast.Subscript(value=_N("_dp"), slice=_B(_N("_a"), ast.Sub(), _N("_c")), ctx=ast.Load()),
                                                    ),
                                                )
                                            ],
                                            orelse=[],
                                        )
                                    ],
                                    orelse=[],
                                )
                            ],
                            orelse=[],
                        ),
                        ast.Return(value=ast.Subscript(value=_N("_dp"), slice=_N(pt), ctx=ast.Load())),
                    ]
                )

    # Space C: 2D Alignment Semiring Dynamorphisms `(seq_a, seq_b)` parameterized by `(Semiring, gap_cost, match_reward, sub_cost)`
    if arity == 2 and all(isinstance(row[0], (str, list, tuple)) and isinstance(row[1], (str, list, tuple)) for row in inputs):
        pa, pb = param_names[0], param_names[1]
        # Parameterized 2D Semiring specs: (combine_fn, base_row_is_range, gap_step, match_delta, sub_delta)
        grid_specs = [
            ("max", False, 0, 1, 0),  # TropicalMaxPlus `(max, +, 0)` with match=+1, gap=0
            ("min", True, 1, 0, 1),   # TropicalMinPlus `(min, +, inf)` with gap=1, match=0, sub=1
            ("min", True, 1, 0, 2),   # TropicalMinPlus `(min, +, inf)` with gap=1, match=0, sub=2 (indel metric)
        ]
        for comb_fn, range_init, gap_c, match_d, sub_d in grid_specs:
            init_prev: ast.expr = (
                _Call("list", _Call("range", _B(_Call("len", _N(pb)), ast.Add(), _C(1))))
                if range_init
                else _B(ast.List(elts=[_C(0)], ctx=ast.Load()), ast.Mult(), _B(_Call("len", _N(pb)), ast.Add(), _C(1)))
            )
            row_head: ast.expr = _B(_N("_i"), ast.Add(), _C(1)) if range_init else _C(0)
            eq_cond = ast.Compare(
                left=ast.Subscript(value=_N(pa), slice=_N("_i"), ctx=ast.Load()),
                ops=[ast.Eq()],
                comparators=[ast.Subscript(value=_N(pb), slice=_N("_j"), ctx=ast.Load())],
            )
            diag_prev = ast.Subscript(value=_N("_prev"), slice=_N("_j"), ctx=ast.Load())
            up_prev = ast.Subscript(value=_N("_prev"), slice=_B(_N("_j"), ast.Add(), _C(1)), ctx=ast.Load())
            left_cur = ast.Subscript(value=_N("_cur"), slice=_N("_j"), ctx=ast.Load())
            if comb_fn == "max" and sub_d == 0 and gap_c == 0:
                cell_expr: ast.expr = ast.IfExp(
                    test=eq_cond,
                    body=_B(diag_prev, ast.Add(), _C(match_d)),
                    orelse=_Call("max", up_prev, left_cur),
                )
            else:
                step_diag = ast.IfExp(test=eq_cond, body=_B(diag_prev, ast.Add(), _C(match_d)), orelse=_B(diag_prev, ast.Add(), _C(sub_d)))
                cell_expr = _Call(comb_fn, _B(up_prev, ast.Add(), _C(gap_c)), _B(left_cur, ast.Add(), _C(gap_c)), step_diag)
            candidates.append(
                [
                    ast.Assign(targets=[_N("_prev", True)], value=init_prev),
                    ast.For(
                        target=_N("_i", True),
                        iter=_Call("range", _Call("len", _N(pa))),
                        body=[
                            ast.Assign(
                                targets=[_N("_cur", True)],
                                value=_B(ast.List(elts=[row_head], ctx=ast.Load()), ast.Add(), _B(ast.List(elts=[_C(0)], ctx=ast.Load()), ast.Mult(), _Call("len", _N(pb)))),
                            ),
                            ast.For(
                                target=_N("_j", True),
                                iter=_Call("range", _Call("len", _N(pb))),
                                body=[
                                    ast.Assign(
                                        targets=[ast.Subscript(value=_N("_cur"), slice=_B(_N("_j"), ast.Add(), _C(1)), ctx=ast.Store())],
                                        value=cell_expr,
                                    )
                                ],
                                orelse=[],
                            ),
                            ast.Assign(targets=[_N("_prev", True)], value=_N("_cur")),
                        ],
                        orelse=[],
                    ),
                    ast.Return(value=ast.Subscript(value=_N("_prev"), slice=_Call("len", _N(pb)), ctx=ast.Load())),
                ]
            )
    return candidates


def _build_higher_order_concept_instantiations(
    param_names: Sequence[str],
    inputs: Sequence[tuple[Any, ...]],
    ordered_concepts: Sequence[Any],
    concept_library: Any | None,
) -> list[tuple[list[ast.stmt], float]]:
    """Instantiate invented higher-order concepts (`concept_ho_*`) with synthesized pure `ast.Lambda` combinators."""
    if not ordered_concepts or len(param_names) != 1:
        return []
    p0 = param_names[0]
    if not all(isinstance(row[0], (list, tuple)) for row in inputs):
        return []

    ho_cands: list[tuple[list[ast.stmt], float]] = []
    lam_bodies_arity2: list[ast.expr] = [
        ast.parse("_a + _b", mode="eval").body,
        ast.parse("_a * _b", mode="eval").body,
        ast.parse("_a + _b * _b", mode="eval").body,
        ast.parse("max(_a, _b)", mode="eval").body,
        ast.parse("min(_a, _b)", mode="eval").body,
        ast.parse("max(0, _a + _b)", mode="eval").body,
    ]
    for c_ent in ordered_concepts:
        if not getattr(c_ent, "is_higher_order", False):
            continue
        cp_map = dict(getattr(c_ent, "callable_arity_map", {}) or {})
        p_list = list(c_ent.param_names)
        if len(p_list) != 3 or len(cp_map) != 1:
            continue
        fn_slot = next(iter(cp_map.keys()))
        if cp_map[fn_slot] != 2:
            continue
        prior_bonus = 0.0
        if concept_library is not None and hasattr(concept_library, "levin_description_bits"):
            prior_bonus = max(0.0, 8.0 - float(concept_library.levin_description_bits(c_ent.concept_id)))
        for init_v in (0, 1):
            for lb in lam_bodies_arity2:
                call_args: list[ast.expr] = []
                for idx_p, slot_nm in enumerate(p_list):
                    if slot_nm == fn_slot:
                        call_args.append(
                            ast.Lambda(
                                args=ast.arguments(
                                    posonlyargs=[],
                                    args=[ast.arg(arg="_a"), ast.arg(arg="_b")],
                                    kwonlyargs=[],
                                    kw_defaults=[],
                                    defaults=[],
                                ),
                                body=lb,
                            )
                        )
                    elif idx_p == 0:
                        call_args.append(ast.Name(id=p0, ctx=ast.Load()))
                    else:
                        call_args.append(ast.Constant(value=init_v))
                stmt_ret = [
                    ast.Return(
                        value=ast.Call(
                            func=ast.Name(id=c_ent.concept_id, ctx=ast.Load()),
                            args=call_args,
                            keywords=[],
                        )
                    )
                ]
                ho_cands.append((stmt_ret, prior_bonus))
    return ho_cands


def _synthesize_hors_algorithmic_body(
    *,
    param_names: Sequence[str],
    inputs: Sequence[tuple[Any, ...]],
    target_sig: tuple[Any, ...],
    concept_callables: Mapping[str, Any] | None = None,
    ordered_concepts: Sequence[Any] = (),
    concept_library: Any | None = None,
) -> str | None:
    """Constructive Recursion-Scheme Algebra + Solomonoff-Levin Universal Search (`eval_pure_ast_function`, zero `exec`)."""
    import math as _math
    import time as _time
    from canonical.swe_kernel.concept_library_v1 import (
        build_programmatic_ast_catamorphism_stmts,
        eval_pure_ast_expr,
        eval_pure_ast_function,
    )

    if not inputs or not param_names:
        return None

    arity = len(param_names)
    p0 = param_names[0]
    first_args0 = [row[0] for row in inputs]

    # 1. Empirical AST Catamorphism when arg0 is syntax expression string
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

    # Order probe indices so the richest non-empty / non-zero example falsifies wrong morphisms in 1 step (< 4 us)
    probe_order = sorted(
        range(len(inputs)),
        key=lambda idx: -(len(inputs[idx][0]) if isinstance(inputs[idx][0], (list, tuple, str)) else abs(int(inputs[idx][0])) if isinstance(inputs[idx][0], int) else 1),
    )

    ast_args = ast.arguments(
        posonlyargs=[],
        args=[ast.arg(arg=nm) for nm in param_names],
        kwonlyargs=[],
        kw_defaults=[],
        defaults=[],
    )

    scored_candidates: list[tuple[float, list[ast.stmt]]] = []
    for ho_stmts, prior_bonus in _build_higher_order_concept_instantiations(param_names, inputs, ordered_concepts, concept_library):
        desc_len = float(sum(1 for s in ho_stmts for _ in ast.walk(s))) - prior_bonus
        scored_candidates.append((desc_len, ho_stmts))

    for stmts in _build_product_state_catamorphisms(param_names, inputs, target_sig):
        desc_len = float(sum(1 for s in stmts for _ in ast.walk(s)))
        scored_candidates.append((desc_len, stmts))

    for stmts in _build_semiring_dynamorphisms(param_names, inputs, target_sig):
        desc_len = float(sum(1 for s in stmts for _ in ast.walk(s)))
        scored_candidates.append((desc_len, stmts))

    # Levin Universal Search ordering: prioritize compact description length + concept prior credit
    scored_candidates.sort(key=lambda item: item[0])

    best_winner: tuple[float, str] | None = None
    for desc_len, stmts in scored_candidates:
        if best_winner is not None and desc_len > best_winner[0] + 6.0:
            break
        fdef = ast.FunctionDef(name="_hors_cand", args=ast_args, body=stmts, decorator_list=[], returns=None)
        ast.fix_missing_locations(fdef)
        matched_all = True
        t0_ns = _time.perf_counter_ns()
        for idx_r in probe_order:
            try:
                out = eval_pure_ast_function(fdef, inputs[idx_r], extra_callables=concept_callables, max_steps=25_000)
            except Exception:
                matched_all = False
                break
            if _freeze_val(out) != target_sig[idx_r]:
                matched_all = False
                break
        if matched_all:
            dt_us = max(1.0, (_time.perf_counter_ns() - t0_ns) / 1e3)
            levin_cost = desc_len + _math.log2(1.0 + dt_us)
            mod_out = ast.Module(body=stmts, type_ignores=[])
            ast.fix_missing_locations(mod_out)
            rendered = "\n".join(ast.unparse(s) for s in mod_out.body)
            if best_winner is None or levin_cost < best_winner[0]:
                best_winner = (levin_cost, rendered)
                # Fast exit when already compact
                if desc_len <= 42.0:
                    break

    return best_winner[1] if best_winner is not None else None


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
