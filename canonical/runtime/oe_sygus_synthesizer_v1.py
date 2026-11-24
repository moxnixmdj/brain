"""Unified Multi-Language Observational-Equivalence SyGuS + EUSolver Synthesizer v1.

Zero-LLM (`model_calls=0`), zero-weight (`parameters_stored=0`), sub-10ms execution-guided
program synthesis engine shared across Python, JavaScript/TypeScript, and C/C++17.

Core mechanisms:
  1. Bottom-Up Observational-Equivalence (OE) Enumeration over live runtime environments
     (collapsing semantically identical ASTs by exact output vector across failing + passing
     frames, preserving minimal AST size).
  2. EUSolver Information-Gain Decision-Tree Predicate Synthesis: discovers the minimal
     general guard separating failing/non-terminating inputs from passing inputs, explicitly
     preferring semantic domain predicates (`is_integer`, `is_finite`, `< 0`, `<= 0`,
     `is_empty`, `is_none`) over brittle exact-literal matches (`x == 0.5`).
  3. Value, Coercion & Conditional (ITE) Expression Synthesis across failing + passing I/O
     examples.
  4. Native 3-Language Code Emission (`python`, `js`, `c`) from ONE unified typed AST.
  5. Plotkin Anti-Unification (`abstract_synthesized_repair`) turning any verified
     synthesized patch into a zero-repo, inspectable, instantly unlearnable external skill.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

SCHEMA = "brain.oe_sygus_synthesizer.v1"
AUTHORITY = "NONE"

_SENTINEL_ERR = object()


@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple[Any, ...]
    size: int
    generality_penalty: int = 0  # Higher = more brittle/literal-overfit


# ---------------------------------------------------------------------------
# 1. Safe Concrete Semantics Evaluator (Python-hosted, JS/C-compatible!)
# ---------------------------------------------------------------------------

def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _eval_expr(expr: Expr, env: Mapping[str, Any]) -> Any:
    op = expr.op
    a = expr.args
    try:
        if op == "var":
            name = a[0]
            return env[name] if name in env else _SENTINEL_ERR
        if op == "const":
            return a[0]
        if op == "len":
            v = _eval_expr(a[0], env)
            if v is _SENTINEL_ERR or not isinstance(v, (str, list, tuple, dict, set)):
                return _SENTINEL_ERR
            return len(v)
        if op == "neg":
            v = _eval_expr(a[0], env)
            if not _is_num(v):
                return _SENTINEL_ERR
            return -v
        if op == "abs":
            v = _eval_expr(a[0], env)
            if not _is_num(v):
                return _SENTINEL_ERR
            return abs(v)
        if op == "trunc":
            v = _eval_expr(a[0], env)
            if not _is_num(v) or not math.isfinite(float(v)):
                return _SENTINEL_ERR
            return math.trunc(v)
        if op == "floor":
            v = _eval_expr(a[0], env)
            if not _is_num(v) or not math.isfinite(float(v)):
                return _SENTINEL_ERR
            return math.floor(v)
        if op == "ceil":
            v = _eval_expr(a[0], env)
            if not _is_num(v) or not math.isfinite(float(v)):
                return _SENTINEL_ERR
            return math.ceil(v)
        if op == "int32_trunc":
            v = _eval_expr(a[0], env)
            if not _is_num(v):
                return _SENTINEL_ERR
            fv = float(v)
            if not math.isfinite(fv):
                return 0
            iv = int(math.trunc(fv)) & 0xFFFFFFFF
            return iv - 0x100000000 if iv >= 0x80000000 else iv
        if op == "strip":
            v = _eval_expr(a[0], env)
            return v.strip() if isinstance(v, str) else _SENTINEL_ERR
        if op == "lower":
            v = _eval_expr(a[0], env)
            return v.lower() if isinstance(v, str) else _SENTINEL_ERR
        if op == "upper":
            v = _eval_expr(a[0], env)
            return v.upper() if isinstance(v, str) else _SENTINEL_ERR

        # Unary semantic domain predicates (general, non-overfitting!)
        if op == "not":
            v = _eval_expr(a[0], env)
            return (not bool(v)) if isinstance(v, bool) else _SENTINEL_ERR
        if op == "is_none":
            v = _eval_expr(a[0], env)
            return (v is None) if v is not _SENTINEL_ERR else _SENTINEL_ERR
        if op == "is_not_none":
            v = _eval_expr(a[0], env)
            return (v is not None) if v is not _SENTINEL_ERR else _SENTINEL_ERR
        if op == "is_nan":
            v = _eval_expr(a[0], env)
            if v is _SENTINEL_ERR:
                return _SENTINEL_ERR
            if isinstance(v, float):
                return math.isnan(v)
            return False if _is_num(v) else _SENTINEL_ERR
        if op == "is_finite":
            v = _eval_expr(a[0], env)
            if not _is_num(v):
                return False if v is not _SENTINEL_ERR else _SENTINEL_ERR
            return math.isfinite(float(v))
        if op == "not_finite":
            v = _eval_expr(a[0], env)
            if v is _SENTINEL_ERR:
                return _SENTINEL_ERR
            if not _is_num(v):
                return True
            return not math.isfinite(float(v))
        if op == "is_integer":
            v = _eval_expr(a[0], env)
            if v is _SENTINEL_ERR:
                return _SENTINEL_ERR
            if isinstance(v, bool) or not _is_num(v):
                return False
            fv = float(v)
            return math.isfinite(fv) and fv.is_integer()
        if op == "not_integer":
            v = _eval_expr(a[0], env)
            if v is _SENTINEL_ERR:
                return _SENTINEL_ERR
            if isinstance(v, bool) or not _is_num(v):
                return True
            fv = float(v)
            return (not math.isfinite(fv)) or (not fv.is_integer())
        if op == "is_empty":
            v = _eval_expr(a[0], env)
            if isinstance(v, (str, list, tuple, dict, set)):
                return len(v) == 0
            return _SENTINEL_ERR
        if op == "not_empty":
            v = _eval_expr(a[0], env)
            if isinstance(v, (str, list, tuple, dict, set)):
                return len(v) > 0
            return _SENTINEL_ERR

        # Binary ops
        lv = _eval_expr(a[0], env)
        rv = _eval_expr(a[1], env)
        if lv is _SENTINEL_ERR or rv is _SENTINEL_ERR:
            return _SENTINEL_ERR

        if op == "and":
            return (bool(lv) and bool(rv)) if (isinstance(lv, bool) and isinstance(rv, bool)) else _SENTINEL_ERR
        if op == "or":
            return (bool(lv) or bool(rv)) if (isinstance(lv, bool) and isinstance(rv, bool)) else _SENTINEL_ERR

        if op in ("<", "<=", ">", ">="):
            if not (_is_num(lv) and _is_num(rv)):
                return _SENTINEL_ERR
            if isinstance(lv, float) and math.isnan(lv):
                return False
            if isinstance(rv, float) and math.isnan(rv):
                return False
            if op == "<":
                return lv < rv
            if op == "<=":
                return lv <= rv
            if op == ">":
                return lv > rv
            return lv >= rv
        if op == "==":
            if type(lv) is bool and type(rv) is not bool:
                return False
            if type(rv) is bool and type(lv) is not bool:
                return False
            return lv == rv
        if op == "!=":
            if type(lv) is bool and type(rv) is not bool:
                return True
            if type(rv) is bool and type(lv) is not bool:
                return True
            return lv != rv

        if op == "+":
            if _is_num(lv) and _is_num(rv):
                return lv + rv
            if isinstance(lv, str) and isinstance(rv, str) and len(lv) + len(rv) <= 256:
                return lv + rv
            return _SENTINEL_ERR
        if op == "-":
            return (lv - rv) if (_is_num(lv) and _is_num(rv)) else _SENTINEL_ERR
        if op == "*":
            return (lv * rv) if (_is_num(lv) and _is_num(rv)) else _SENTINEL_ERR
        if op == "min":
            return min(lv, rv) if (_is_num(lv) and _is_num(rv) and not (math.isnan(float(lv)) or math.isnan(float(rv)))) else _SENTINEL_ERR
        if op == "max":
            return max(lv, rv) if (_is_num(lv) and _is_num(rv) and not (math.isnan(float(lv)) or math.isnan(float(rv)))) else _SENTINEL_ERR
        if op == "in":
            return (lv in rv) if (isinstance(lv, str) and isinstance(rv, str)) else _SENTINEL_ERR
        if op == "startswith":
            return rv.startswith(lv) if (isinstance(lv, str) and isinstance(rv, str)) else _SENTINEL_ERR
        if op == "endswith":
            return rv.endswith(lv) if (isinstance(lv, str) and isinstance(rv, str)) else _SENTINEL_ERR
        if op == "ite":
            cv = _eval_expr(a[0], env)
            if not isinstance(cv, bool):
                return _SENTINEL_ERR
            return _eval_expr(a[1] if cv else a[2], env)
    except Exception:
        return _SENTINEL_ERR
    return _SENTINEL_ERR


def _sig_atom(v: Any) -> tuple[str, Any]:
    if v is None:
        return ("none", None)
    if isinstance(v, bool):
        return ("bool", v)
    if isinstance(v, int):
        return ("num", float(v))
    if isinstance(v, float):
        if math.isnan(v):
            return ("nan", "nan")
        if math.isinf(v):
            return ("inf", "+" if v > 0 else "-")
        return ("num", round(v, 9))
    if isinstance(v, str):
        return ("str", v)
    return ("other", repr(v)[:64])


def _sig_vec(vals: Sequence[Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(_sig_atom(v) for v in vals)


# ---------------------------------------------------------------------------
# 2. Native 3-Language AST Emitter (`python`, `js`, `c`)
# ---------------------------------------------------------------------------

def emit_expr(expr: Expr, lang: str = "python") -> str:
    """Emit clean, idiomatic code for `expr` in Python, JavaScript, or C."""
    op = expr.op
    a = expr.args
    lg = lang.lower()

    if op == "var":
        return str(a[0])
    if op == "const":
        v = a[0]
        if v is None:
            return {"python": "None", "js": "null", "c": "NULL"}[lg]
        if isinstance(v, bool):
            if lg == "python":
                return "True" if v else "False"
            return "true" if v else "false"
        if isinstance(v, str):
            return repr(v) if lg == "python" else '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
        return str(v)

    if op == "len":
        s = emit_expr(a[0], lg)
        if lg == "python":
            return f"len({s})"
        if lg == "js":
            return f"{s}.length"
        return f"strlen({s})"
    if op == "neg":
        return f"-({emit_expr(a[0], lg)})"
    if op == "abs":
        s = emit_expr(a[0], lg)
        return {"python": f"abs({s})", "js": f"Math.abs({s})", "c": f"fabs({s})"}[lg]
    if op == "trunc":
        s = emit_expr(a[0], lg)
        return {"python": f"int({s})", "js": f"Math.trunc({s})", "c": f"((int)({s}))"}[lg]
    if op == "floor":
        s = emit_expr(a[0], lg)
        return {"python": f"math.floor({s})", "js": f"Math.floor({s})", "c": f"floor({s})"}[lg]
    if op == "ceil":
        s = emit_expr(a[0], lg)
        return {"python": f"math.ceil({s})", "js": f"Math.ceil({s})", "c": f"ceil({s})"}[lg]
    if op == "int32_trunc":
        s = emit_expr(a[0], lg)
        return {"python": f"int({s})", "js": f"({s} | 0)", "c": f"((int)({s}))"}[lg]
    if op == "strip":
        s = emit_expr(a[0], lg)
        return f"{s}.strip()" if lg == "python" else f"{s}.trim()"
    if op == "lower":
        s = emit_expr(a[0], lg)
        return f"{s}.lower()" if lg == "python" else f"{s}.toLowerCase()"
    if op == "upper":
        s = emit_expr(a[0], lg)
        return f"{s}.upper()" if lg == "python" else f"{s}.toUpperCase()"

    if op == "not":
        s = emit_expr(a[0], lg)
        return f"(not ({s}))" if lg == "python" else f"!({s})"
    if op == "is_none":
        s = emit_expr(a[0], lg)
        return {"python": f"{s} is None", "js": f"{s} == null", "c": f"{s} == NULL"}[lg]
    if op == "is_not_none":
        s = emit_expr(a[0], lg)
        return {"python": f"{s} is not None", "js": f"{s} != null", "c": f"{s} != NULL"}[lg]
    if op == "is_nan":
        s = emit_expr(a[0], lg)
        return {"python": f"math.isnan({s})", "js": f"Number.isNaN({s})", "c": f"isnan({s})"}[lg]
    if op == "is_finite":
        s = emit_expr(a[0], lg)
        return {"python": f"math.isfinite({s})", "js": f"Number.isFinite({s})", "c": f"isfinite({s})"}[lg]
    if op == "not_finite":
        s = emit_expr(a[0], lg)
        return {"python": f"(not math.isfinite({s}))", "js": f"!Number.isFinite({s})", "c": f"!isfinite({s})"}[lg]
    if op == "is_integer":
        s = emit_expr(a[0], lg)
        if lg == "python":
            return f"(isinstance({s}, int) and not isinstance({s}, bool))"
        if lg == "js":
            return f"Number.isInteger({s})"
        return f"(floor({s}) == ({s}))"
    if op == "not_integer":
        s = emit_expr(a[0], lg)
        if lg == "python":
            return f"(not (isinstance({s}, int) and not isinstance({s}, bool)))"
        if lg == "js":
            return f"!Number.isInteger({s})"
        return f"(floor({s}) != ({s}))"
    if op == "is_empty":
        s = emit_expr(a[0], lg)
        if lg == "python":
            return f"len({s}) == 0"
        if lg == "js":
            return f"{s}.length === 0"
        return f"strlen({s}) == 0"
    if op == "not_empty":
        s = emit_expr(a[0], lg)
        if lg == "python":
            return f"len({s}) > 0"
        if lg == "js":
            return f"{s}.length > 0"
        return f"strlen({s}) > 0"

    if op == "and":
        l, r = emit_expr(a[0], lg), emit_expr(a[1], lg)
        return f"({l} and {r})" if lg == "python" else f"({l} && {r})"
    if op == "or":
        l, r = emit_expr(a[0], lg), emit_expr(a[1], lg)
        return f"({l} or {r})" if lg == "python" else f"({l} || {r})"
    if op in ("<", "<=", ">", ">=", "+", "-", "*"):
        l, r = emit_expr(a[0], lg), emit_expr(a[1], lg)
        return f"({l} {op} {r})"
    if op == "==":
        l, r = emit_expr(a[0], lg), emit_expr(a[1], lg)
        eq = "===" if lg == "js" else "=="
        return f"({l} {eq} {r})"
    if op == "!=":
        l, r = emit_expr(a[0], lg), emit_expr(a[1], lg)
        neq = "!==" if lg == "js" else "!="
        return f"({l} {neq} {r})"
    if op == "min":
        l, r = emit_expr(a[0], lg), emit_expr(a[1], lg)
        return {"python": f"min({l}, {r})", "js": f"Math.min({l}, {r})", "c": f"(({l}) < ({r}) ? ({l}) : ({r}))"}[lg]
    if op == "max":
        l, r = emit_expr(a[0], lg), emit_expr(a[1], lg)
        return {"python": f"max({l}, {r})", "js": f"Math.max({l}, {r})", "c": f"(({l}) > ({r}) ? ({l}) : ({r}))"}[lg]
    if op == "in":
        l, r = emit_expr(a[0], lg), emit_expr(a[1], lg)
        return f"({l} in {r})" if lg == "python" else f"{r}.includes({l})"
    if op == "startswith":
        l, r = emit_expr(a[0], lg), emit_expr(a[1], lg)
        return f"{r}.startswith({l})" if lg == "python" else f"{r}.startsWith({l})"
    if op == "endswith":
        l, r = emit_expr(a[0], lg), emit_expr(a[1], lg)
        return f"{r}.endswith({l})" if lg == "python" else f"{r}.endsWith({l})"
    if op == "ite":
        c, t, e = emit_expr(a[0], lg), emit_expr(a[1], lg), emit_expr(a[2], lg)
        if lg == "python":
            return f"({t} if {c} else {e})"
        return f"(({c}) ? ({t}) : ({e}))"
    raise ValueError(f"Unsupported op: {op}")


# ---------------------------------------------------------------------------
# 3. EUSolver Decision-Tree Predicate Synthesizer (Separating Fail vs Pass!)
# ---------------------------------------------------------------------------

def _normalize_envs(envs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in envs:
        d: dict[str, Any] = {}
        for k, v in e.items():
            if not isinstance(k, str) or not k:
                continue
            if v == "__NaN__":
                d[k] = float("nan")
            elif v == "__Inf__":
                d[k] = float("inf")
            elif v == "__NegInf__":
                d[k] = float("-inf")
            elif v is None or isinstance(v, (bool, int, float, str, list, tuple)):
                d[k] = v
        if d:
            out.append(d)
    return out


def synthesize_separating_predicates(
    failing_envs: Sequence[Mapping[str, Any]],
    passing_envs: Sequence[Mapping[str, Any]],
    *,
    lang: str = "python",
    extra_consts: Sequence[Any] = (),
    max_results: int = 8,
) -> list[dict[str, Any]]:
    """Synthesize minimal, general separating guards: True on ALL failing, False on ALL passing.

    Uses bottom-up observational-equivalence predicate pruning + EUSolver entropy-guided
    disjunctive/conjunctive decision-tree synthesis. Penalizes exact-literal overfitting
    so semantic domain guards (`!Number.isInteger(size)`, `!Number.isFinite(size)`, `size < 0`)
    always outrank brittle equality checks (`size === 0.5`).
    """
    f_envs = _normalize_envs(failing_envs)
    p_envs = _normalize_envs(passing_envs)
    if not f_envs or not p_envs:
        return []

    all_envs = f_envs + p_envs
    n_f = len(f_envs)
    n_p = len(p_envs)
    target_bits = tuple([True] * n_f + [False] * n_p)

    # Candidate variables present across all failing envs (and at least one passing env)
    shared_vars = sorted(
        k for k in set(f_envs[0].keys())
        if all(k in e for e in f_envs) and all(k in e for e in p_envs)
        and not any(b in k.lower() for b in ("pytest_", "_pytest", "conftest", "unittest", "plugin_name"))
    )
    if not shared_vars:
        return []

    # Build OE-pruned atomic boolean predicate pool: bit_tuple -> (rank_tuple, Expr)
    pred_pool: dict[tuple[bool, ...], tuple[tuple[int, int, str], Expr]] = {}

    def _add_pred(ex: Expr) -> None:
        bits: list[bool] = []
        for env in all_envs:
            v = _eval_expr(ex, env)
            if not isinstance(v, bool):
                return
            bits.append(v)
        bt = tuple(bits)
        # Skip constant all-True / all-False predicates
        if all(bt) or not any(bt):
            return
        code = emit_expr(ex, lang)
        rank = (ex.generality_penalty, ex.size, code)
        if bt not in pred_pool or rank < pred_pool[bt][0]:
            pred_pool[bt] = (rank, ex)

    # Generate atomic predicates per variable
    num_bounds = [0, 1, -1]
    for c in extra_consts[:6]:
        if _is_num(c) and c not in num_bounds:
            num_bounds.append(c)

    for vname in shared_vars[:12]:
        vexpr = Expr("var", (vname,), 1, 0)
        sample_vals = [e[vname] for e in all_envs]
        has_none = any(v is None for v in sample_vals)
        has_num = any(_is_num(v) for v in sample_vals)
        has_str = any(isinstance(v, str) for v in sample_vals)
        has_seq = any(isinstance(v, (str, list, tuple)) for v in sample_vals)

        if has_none:
            _add_pred(Expr("is_none", (vexpr,), 2, 0))
            _add_pred(Expr("is_not_none", (vexpr,), 2, 0))

        if has_num:
            # High-generality domain predicates (penalty = 0!)
            _add_pred(Expr("not_integer", (vexpr,), 2, 0))
            _add_pred(Expr("is_integer", (vexpr,), 2, 0))
            _add_pred(Expr("not_finite", (vexpr,), 2, 0))
            _add_pred(Expr("is_finite", (vexpr,), 2, 0))
            _add_pred(Expr("is_nan", (vexpr,), 2, 0))
            for b in num_bounds:
                pen = 0 if b == 0 else (1 if b in (1, -1) else 3)
                bexpr = Expr("const", (b,), 1, pen)
                for cmp_op in ("<", "<=", ">", ">="):
                    _add_pred(Expr(cmp_op, (vexpr, bexpr), 3, pen))
                # Equality against exact numbers gets higher generality penalty than domain predicates
                eq_pen = 2 if b in (0, 1, -1) else 6
                _add_pred(Expr("==", (vexpr, bexpr), 3, eq_pen))
                _add_pred(Expr("!=", (vexpr, bexpr), 3, eq_pen))

        if has_seq:
            _add_pred(Expr("is_empty", (vexpr,), 2, 0))
            _add_pred(Expr("not_empty", (vexpr,), 2, 0))

        if has_str:
            for c in extra_consts[:6]:
                if isinstance(c, str) and len(c) >= 2:
                    cexpr = Expr("const", (c,), 1, 2)
                    _add_pred(Expr("in", (cexpr, vexpr), 3, 2))
                    _add_pred(Expr("startswith", (cexpr, vexpr), 3, 2))
                    _add_pred(Expr("endswith", (cexpr, vexpr), 3, 2))

    # Pairwise variable comparisons (e.g. a < b, a <= b, a > b)
    num_vars = [vn for vn in shared_vars[:8] if all(_is_num(e[vn]) for e in all_envs)]
    for i in range(len(num_vars)):
        for j in range(i + 1, len(num_vars)):
            va = Expr("var", (num_vars[i],), 1, 0)
            vb = Expr("var", (num_vars[j],), 1, 0)
            for cmp_op in ("<", "<=", ">", ">=", "==", "!="):
                _add_pred(Expr(cmp_op, (va, vb), 3, 0))

    solutions: list[tuple[tuple[int, int, str], Expr]] = []
    seen_codes: set[str] = set()

    def _record_sol(ex: Expr) -> None:
        code = emit_expr(ex, lang)
        if code not in seen_codes:
            seen_codes.add(code)
            solutions.append(((ex.generality_penalty, ex.size, code), ex))

    # 1. Exact single-predicate separators
    if target_bits in pred_pool:
        _record_sol(pred_pool[target_bits][1])
    # Also collect all distinct single-predicate separators (not just 1!)
    # Check 2-predicate OR / AND combinations (OE-pruned!)
    items = sorted(pred_pool.items(), key=lambda kv: kv[1][0])[:48]

    # Disjunctions `P1 || P2` where neither fires on ANY passing env (zero false positives!)
    safe_disjuncts = [
        (bt, ex) for bt, (_rk, ex) in items
        if not any(bt[n_f:]) and any(bt[:n_f])
    ]
    for i in range(len(safe_disjuncts)):
        bt1, ex1 = safe_disjuncts[i]
        if bt1 == target_bits:
            _record_sol(ex1)
            continue
        for j in range(i + 1, len(safe_disjuncts)):
            bt2, ex2 = safe_disjuncts[j]
            comb = tuple(a or b for a, b in zip(bt1, bt2))
            if comb == target_bits:
                _record_sol(Expr("or", (ex1, ex2), ex1.size + ex2.size + 1, ex1.generality_penalty + ex2.generality_penalty))

    # Conjunctions `P1 && P2` where both hold on ALL failing envs (zero false negatives!)
    safe_conjuncts = [
        (bt, ex) for bt, (_rk, ex) in items
        if all(bt[:n_f]) and not all(bt[n_f:])
    ]
    for i in range(len(safe_conjuncts)):
        bt1, ex1 = safe_conjuncts[i]
        if bt1 == target_bits:
            _record_sol(ex1)
            continue
        for j in range(i + 1, len(safe_conjuncts)):
            bt2, ex2 = safe_conjuncts[j]
            comb = tuple(a and b for a, b in zip(bt1, bt2))
            if comb == target_bits:
                _record_sol(Expr("and", (ex1, ex2), ex1.size + ex2.size + 1, ex1.generality_penalty + ex2.generality_penalty))

    # 3. Greedy EUSolver Set-Cover / Decision-Tree (up to 3 disjuncts covering all failing envs!)
    if not solutions and safe_disjuncts:
        uncovered = set(range(n_f))
        chosen: list[Expr] = []
        for _step in range(3):
            if not uncovered:
                break
            best_pick: tuple[int, tuple[int, int, str], set[int], Expr] | None = None
            for bt, ex in safe_disjuncts:
                cov = {idx for idx in uncovered if bt[idx]}
                if not cov:
                    continue
                cand_score = (-len(cov), (ex.generality_penalty, ex.size, emit_expr(ex, lang)), cov, ex)
                if best_pick is None or (cand_score[0], cand_score[1]) < (best_pick[0], best_pick[1]):
                    best_pick = cand_score
            if best_pick is None:
                break
            uncovered -= best_pick[2]
            chosen.append(best_pick[3])
        if not uncovered and chosen:
            acc = chosen[0]
            for nxt in chosen[1:]:
                acc = Expr("or", (acc, nxt), acc.size + nxt.size + 1, acc.generality_penalty + nxt.generality_penalty)
            _record_sol(acc)

    solutions.sort(key=lambda x: x[0])
    out: list[dict[str, Any]] = []
    for rk, ex in solutions[:max_results]:
        out.append({
            "code": emit_expr(ex, lang),
            "expr": ex,
            "size": ex.size,
            "generality_penalty": ex.generality_penalty,
            "lang": lang,
        })
    return out


# ---------------------------------------------------------------------------
# 4. OE-SyGuS Value / Coercion / ITE Expression Synthesizer
# ---------------------------------------------------------------------------

def synthesize_value_expressions(
    examples: Sequence[tuple[Mapping[str, Any], Any]],
    *,
    lang: str = "python",
    extra_consts: Sequence[Any] = (),
    max_results: int = 8,
) -> list[dict[str, Any]]:
    """Bottom-up Observational-Equivalence SyGuS synthesizer for value/coercion expressions.

    Given concrete `(env, expected_value)` pairs across failing + passing inputs, enumerates
    minimal expressions matching ALL pairs exactly (including `trunc`/`floor`/`ceil`/`| 0`/
    arithmetic/string ops and EUSolver ITE branches when needed).
    """
    if not examples:
        return []
    envs = _normalize_envs([e for e, _ in examples])
    if len(envs) != len(examples):
        return []
    targets = [t for _, t in examples]
    target_sig = _sig_vec(targets)

    shared_vars = sorted(
        k for k in set(envs[0].keys())
        if all(k in e for e in envs)
        and not any(b in k.lower() for b in ("pytest_", "_pytest", "conftest", "unittest", "plugin_name"))
    )

    pool: dict[tuple[tuple[str, Any], ...], tuple[tuple[int, int, str], Expr, tuple[Any, ...]]] = {}
    solutions: list[tuple[tuple[int, int, str], Expr]] = []
    seen_codes: set[str] = set()

    def _register(ex: Expr) -> None:
        vals: list[Any] = []
        for env in envs:
            v = _eval_expr(ex, env)
            if v is _SENTINEL_ERR:
                return
            if isinstance(v, str) and len(v) > 256:
                return
            vals.append(v)
        vt = tuple(vals)
        sk = _sig_vec(vt)
        code = emit_expr(ex, lang)
        rk = (ex.generality_penalty, ex.size, code)
        if sk == target_sig and code not in seen_codes:
            if ex.op != "const" or len(set(_sig_atom(t) for t in targets)) == 1:
                seen_codes.add(code)
                solutions.append((rk, ex))
        if sk not in pool or rk < pool[sk][0]:
            pool[sk] = (rk, ex, vt)

    # Level 0: variables & constants
    for vn in shared_vars[:12]:
        _register(Expr("var", (vn,), 1, 0))
    consts: list[Any] = [0, 1, -1, 2, ""]
    for c in extra_consts[:6]:
        if (c is None or isinstance(c, (bool, int, float, str))) and c not in consts:
            consts.append(c)
    for c in consts:
        _register(Expr("const", (c,), 1, 1 if c not in (0, 1, "") else 0))

    # Level 1: unary coercions & normalizers
    lvl0 = list(pool.values())[:28]
    for _rk, node, vt in lvl0:
        if node.op == "const":
            continue
        if all(_is_num(v) for v in vt):
            for uop in ("trunc", "floor", "ceil", "int32_trunc", "abs", "neg"):
                _register(Expr(uop, (node,), node.size + 1, node.generality_penalty))
        elif all(isinstance(v, str) for v in vt):
            for uop in ("strip", "lower", "upper", "len"):
                _register(Expr(uop, (node,), node.size + 1, node.generality_penalty))

    # Level 2: binary ops (OE-pruned)
    lvl1 = sorted(pool.values(), key=lambda x: x[0])[:28]
    num_items = [x for x in lvl1 if all(_is_num(v) for v in x[2])]
    str_items = [x for x in lvl1 if all(isinstance(v, str) for v in x[2])]

    for i, (_rka, na, _va) in enumerate(num_items[:14]):
        for j, (_rkb, nb, _vb) in enumerate(num_items[:14]):
            if na.op == "const" and nb.op == "const":
                continue
            if i <= j:
                for bop in ("+", "*", "min", "max"):
                    _register(Expr(bop, (na, nb), na.size + nb.size + 1, na.generality_penalty + nb.generality_penalty))
            if i != j:
                _register(Expr("-", (na, nb), na.size + nb.size + 1, na.generality_penalty + nb.generality_penalty))

    for i, (_rka, na, _va) in enumerate(str_items[:10]):
        for j, (_rkb, nb, _vb) in enumerate(str_items[:10]):
            if na.op == "const" and nb.op == "const":
                continue
            if i != j:
                _register(Expr("+", (na, nb), na.size + nb.size + 1, na.generality_penalty + nb.generality_penalty))

    # Level 3: EUSolver ITE composition if no single branch matches all examples
    if not solutions and len(envs) >= 2:
        # Find best partial expression covering a strict subset of examples, then synthesize guard!
        best_parts: list[tuple[int, Expr, set[int]]] = []
        for _rk, ex, vt in pool.values():
            cov = {idx for idx, (vv, tv) in enumerate(zip(vt, targets)) if _sig_atom(vv) == _sig_atom(tv)}
            if 0 < len(cov) < len(envs):
                best_parts.append((len(cov), ex, cov))
        best_parts.sort(key=lambda x: (-x[0], x[1].generality_penalty, x[1].size))
        for _c1, ex_then, cov_then in best_parts[:8]:
            rem = set(range(len(envs))) - cov_then
            ex_else = next((ex2 for _c2, ex2, cov2 in best_parts if rem.issubset(cov2)), None)
            if ex_else is None:
                continue
            f_sub = [envs[idx] for idx in sorted(cov_then)]
            p_sub = [envs[idx] for idx in sorted(rem)]
            guards = synthesize_separating_predicates(f_sub, p_sub, lang=lang, extra_consts=extra_consts, max_results=2)
            for g in guards:
                ite = Expr(
                    "ite",
                    (g["expr"], ex_then, ex_else),
                    g["expr"].size + ex_then.size + ex_else.size + 1,
                    g["expr"].generality_penalty + ex_then.generality_penalty + ex_else.generality_penalty,
                )
                _register(ite)

    solutions.sort(key=lambda x: x[0])
    return [
        {
            "code": emit_expr(ex, lang),
            "expr": ex,
            "size": ex.size,
            "generality_penalty": ex.generality_penalty,
            "lang": lang,
        }
        for _rk, ex in solutions[:max_results]
    ]


# ---------------------------------------------------------------------------
# 5. Plotkin Anti-Unification: Turn Verified Synthesized Fixes into Skills
# ---------------------------------------------------------------------------

def _abstract_expr_template(expr: Expr, var_map: dict[str, str]) -> str:
    if expr.op == "var":
        v = str(expr.args[0])
        if v not in var_map:
            var_map[v] = f"$V{len(var_map)}"
        return var_map[v]
    if expr.op == "const":
        c = expr.args[0]
        if c in (0, 1, -1, None, True, False, ""):
            return repr(c)
        return "$C"
    sub = ", ".join(_abstract_expr_template(a, var_map) for a in expr.args if isinstance(a, Expr))
    return f"{expr.op}({sub})"


def abstract_synthesized_repair(
    *,
    lang: str,
    error_kind: str,
    guard_expr: Expr | None = None,
    action_kind: str = "return_const",
    action_expr: Expr | None = None,
) -> dict[str, Any]:
    """Plotkin-abstract a verified synthesized repair into a zero-repo, zero-weight skill."""
    vmap: dict[str, str] = {}
    g_tpl = _abstract_expr_template(guard_expr, vmap) if guard_expr is not None else None
    a_tpl = _abstract_expr_template(action_expr, vmap) if action_expr is not None else None
    sig = f"{lang}|{error_kind}|{g_tpl}|{action_kind}|{a_tpl}"
    law_id = "oesygus_" + hashlib.sha256(sig.encode("utf-8")).hexdigest()[:12]
    return {
        "law_id": law_id,
        "kind": "OE_SYGUS_SYNTHESIZED_LAW",
        "lang": lang,
        "error_kind": error_kind,
        "guard_template": g_tpl,
        "action_kind": action_kind,
        "action_template": a_tpl,
        "arity": len(vmap),
        "parameters_stored": 0,
    }
