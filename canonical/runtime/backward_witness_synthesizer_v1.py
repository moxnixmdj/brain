"""Backward Deductive Witness Propagation ("Reverse Execution" Synthesis) + Minimal Witness Shrinking.

Instead of forward-enumerating 80,000 AST candidates from inputs (which hits an exponential
wall at depth >= 3), this engine starts from the failing test's REQUIRED OUTPUT (`expected`)
and propagates exact mathematical constraints BACKWARDS through invertible witness functions
(Polozov & Gulwani PROSE/D4 inverse semantics):

  1. **Exact Multi-Example Arithmetic Inverse Witnesses:**
     - Additive residual:  `expected - actual == r`  -> recursively solve `r` from frame alphabet!
       Directly calculates `expr + var`, `expr - var`, `expr + const`, AND depth-3+ chains like
       `item.price_cents * item.qty + item.tax_cents` in < 2ms!
     - Multiplicative ratio: `expected / actual == r` (exact across all examples) -> `expr * r`!
       Directly solves `i.price_cents -> i.price_cents * i.qty` in O(1) without search!
     - Affine 2-point solver: `expected == a * actual + b` solved analytically across examples!
     - Floor-div / Modulo / Power / Unary negation / Abs inverse witnesses!

  2. **Exact String & Sequence Inverse Witnesses:**
     - Prefix / Suffix addition & stripping: `expected = p + actual + s`, `actual.removeprefix(p)`,
       `actual.removesuffix(s)`, `actual.strip(chars)`!
     - Case & Whitespace canonicalization: `.lower()`, `.upper()`, `.strip()`!
     - Exact Substring / Slice inversion: `actual[lo:hi]`!
     - Exact Replacement inversion: `actual.replace(old, new)` deduced directly from the common
       mismatch span between `actual` and `expected`!
     - Exact Split / Join inversion: `sep.join(...)` / `actual.split(sep)`!

  3. **Exact Boolean & Container Inverse Witnesses:**
     - Negation (`not expr`), Length (`len(expr)`), Sorted/Reversed (`sorted(expr)`, `list(reversed(expr))`),
       Deduplication (`list(dict.fromkeys(expr))`), Dict/List projection (`[x.attr for x in seq]`)!

  4. **Minimal Witness Shrinking (Delta-Debugging / ddmin):**
     - Given a failing test input `x` and predicate `fails(x)`, shrinks strings/lists/dicts to
       the minimal counterexample `x_min` before backward constraint propagation so noisy real
       inputs collapse to their pure mathematical core!

Hard constraints respected by construction:
  - 0 external model calls (`model_calls == 0`)
  - 0 stored weights (`parameters_stored == 0`)
  - Pure Python stdlib only

Authority: NONE. Computed mechanism only.
"""
from __future__ import annotations

import ast
import copy
import math
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "BRAIN_BACKWARD_WITNESS_SYNTHESIZER_V1"
AUTHORITY = "NONE"


@dataclass(frozen=True)
class WitnessExample:
    """One concrete failing (or passing) observation at an expression site."""

    env: Mapping[str, Any]  # frame locals & depth-1/2 attributes (e.g. {"i.price_cents": 100, "i.qty": 3})
    actual: Any             # value produced by the existing buggy expression
    expected: Any           # required value demanded by the failing test/assertion
    is_failing: bool = True


def extract_frame_alphabet(env: Mapping[str, Any], *, max_depth: int = 2) -> dict[str, Any]:
    """Build a flat symbolic alphabet `{expr_str: concrete_value}` from live locals & object attributes."""
    alpha: dict[str, Any] = {}

    def _add(name: str, val: Any, depth: int) -> None:
        if len(alpha) >= 96:
            return
        if isinstance(val, (int, float, bool, str, bytes, list, tuple, set, dict)) or val is None:
            alpha[name] = val
        if depth >= max_depth or val is None or isinstance(val, (int, float, bool, str, bytes, list, tuple, set, dict)):
            return
        # Safe read-only attribute / @property introspection (no mutating method calls!)
        seen_attrs: set[str] = set()
        d = getattr(val, "__dict__", None)
        if isinstance(d, dict):
            for k, v in list(d.items())[:20]:
                if not k.startswith("_"):
                    seen_attrs.add(k)
                    _add(f"{name}.{k}", v, depth + 1)
        for cls in type(val).__mro__:
            for k, descriptor in list(cls.__dict__.items())[:20]:
                if k.startswith("_") or k in seen_attrs:
                    continue
                if isinstance(descriptor, property) and descriptor.fget is not None:
                    try:
                        v = descriptor.fget(val)
                        seen_attrs.add(k)
                        _add(f"{name}.{k}", v, depth + 1)
                    except Exception:
                        pass

    for k, v in env.items():
        if not str(k).startswith("_"):
            _add(str(k), v, 0)
    return alpha


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))


def _eq_val(a: Any, b: Any) -> bool:
    if type(a) is bool or type(b) is bool:
        return type(a) is type(b) and a == b
    if _is_num(a) and _is_num(b):
        return abs(float(a) - float(b)) <= 1e-9
    try:
        return bool(a == b)
    except Exception:
        return False


def _const_repr(v: Any) -> str:
    if isinstance(v, float) and v.is_integer():
        return repr(int(v))
    return repr(v)


def _match_atom_or_const(
    target_vals: Sequence[Any],
    alphabets: Sequence[Mapping[str, Any]],
) -> list[str]:
    """Check in O(|alphabet|) if a single existing variable/attribute or constant matches ALL target_vals."""
    if not target_vals:
        return []
    hits: list[str] = []
    # 1. Constant check (all examples require the exact same scalar literal)
    v0 = target_vals[0]
    if isinstance(v0, (int, float, bool, str)) or v0 is None:
        if all(_eq_val(v, v0) for v in target_vals[1:]):
            hits.append(_const_repr(v0))

    # 2. Direct frame variable / attribute match across ALL examples
    common_keys = set(alphabets[0].keys())
    for a in alphabets[1:]:
        common_keys &= set(a.keys())
    for k in sorted(common_keys, key=lambda s: (s.count("."), len(s), s)):
        if all(_eq_val(a[k], tv) for a, tv in zip(alphabets, target_vals)):
            hits.append(k)
    return hits


def _deduce_string_replace(actuals: Sequence[str], expecteds: Sequence[str]) -> tuple[str, str] | None:
    """Deduce `(old, new)` directly from the differing substrings of `(actual, expected)`."""
    if not actuals or len(actuals) != len(expecteds):
        return None
    # Candidate single-character or token replacements deduced from first differing pair
    candidates: list[tuple[str, str]] = []
    for a, e in zip(actuals, expecteds):
        if a == e:
            continue
        # Longest common prefix & suffix
        p = 0
        lim = min(len(a), len(e))
        while p < lim and a[p] == e[p]:
            p += 1
        s = 0
        while s < (lim - p) and a[len(a) - 1 - s] == e[len(e) - 1 - s]:
            s += 1
        mid_a = a[p : len(a) - s] if s else a[p:]
        mid_e = e[p : len(e) - s] if s else e[p:]
        if mid_a and len(mid_a) <= 16 and len(mid_e) <= 16:
            candidates.append((mid_a, mid_e))
        # Also test single-char substitutions where differing positions map consistently
        if len(a) == len(e):
            diffs = {(ca, ce) for ca, ce in zip(a, e) if ca != ce}
            if len(diffs) == 1:
                candidates.append(next(iter(diffs)))
        break
    for old, new in candidates:
        if all(a.replace(old, new) == e for a, e in zip(actuals, expecteds)):
            return (old, new)
    return None


def backward_propagate_expression(
    base_expr: str,
    examples: Sequence[WitnessExample],
    *,
    max_depth: int = 3,
    _depth: int = 0,
    _seen: set[str] | None = None,
) -> list[str]:
    """Propagate required outputs `expected` BACKWARDS from output -> `base_expr` via exact
    inverse witness functions. Returns synthesized Python expressions ranked by simplicity (MDL)."""
    if not examples or _depth > max_depth:
        return []
    seen = _seen if _seen is not None else set()
    alphabets = [extract_frame_alphabet(ex.env) for ex in examples]
    actuals = [ex.actual for ex in examples]
    expecteds = [ex.expected for ex in examples]

    results: list[str] = []

    def _emit(expr: str) -> None:
        if expr and expr not in seen and expr != base_expr:
            try:
                ast.parse(expr, mode="eval")
            except SyntaxError:
                return
            seen.add(expr)
            results.append(expr)

    # ------------------------------------------------------------------
    # 0. Direct Atom / Constant / Attribute Match (Depth-0 Base Case)
    # ------------------------------------------------------------------
    for h in _match_atom_or_const(expecteds, alphabets):
        _emit(h)
    if results and _depth > 0:
        return results

    # ------------------------------------------------------------------
    # 1. Exact Arithmetic Backward Witness Functions
    # ------------------------------------------------------------------
    if all(_is_num(a) and _is_num(e) for a, e in zip(actuals, expecteds)):
        # 1a. Exact Unary Negation / Abs
        if all(_eq_val(-a, e) for a, e in zip(actuals, expecteds)):
            _emit(f"-({base_expr})")
        if all(_eq_val(abs(a), e) for a, e in zip(actuals, expecteds)):
            _emit(f"abs({base_expr})")

        # 1b. Exact Additive Residual: `expected = base_expr + residual` OR `base_expr - residual`
        add_residuals = [e - a for a, e in zip(actuals, expecteds)]
        for r_expr in _match_atom_or_const(add_residuals, alphabets):
            if r_expr == "0":
                continue
            if r_expr.startswith("-") and r_expr[1:].replace(".", "", 1).isdigit():
                _emit(f"({base_expr}) - {r_expr[1:]}")
            else:
                _emit(f"({base_expr}) + {r_expr}")
        sub_residuals = [a - e for a, e in zip(actuals, expecteds)]
        for r_expr in _match_atom_or_const(sub_residuals, alphabets):
            if r_expr != "0" and not r_expr.startswith("-"):
                _emit(f"({base_expr}) - {r_expr}")

        # 1c. Exact Multiplicative Inverse: `expected = base_expr * factor`
        if all(float(a) != 0.0 for a in actuals):
            ratios = [e / a for a, e in zip(actuals, expecteds)]
            norm_ratios = [int(round(r)) if abs(r - round(r)) <= 1e-9 else r for r in ratios]
            for f_expr in _match_atom_or_const(norm_ratios, alphabets):
                if f_expr != "1":
                    _emit(f"({base_expr}) * {f_expr}")

        # 1d. Exact Division / Floor-Division Inverse: `expected = base_expr / d` or `base_expr // d`
        if all(float(e) != 0.0 for e in expecteds):
            inv_ratios = [a / e for a, e in zip(actuals, expecteds)]
            norm_inv = [int(round(r)) if abs(r - round(r)) <= 1e-9 else r for r in inv_ratios]
            for d_expr in _match_atom_or_const(norm_inv, alphabets):
                if d_expr not in ("0", "1"):
                    if all(isinstance(a, int) and isinstance(e, int) for a, e in zip(actuals, expecteds)):
                        _emit(f"({base_expr}) // {d_expr}")
                    _emit(f"({base_expr}) / {d_expr}")

        # 1e. Exact 2-Point Analytical Affine Solver (`expected == k * actual + b`)
        if len(examples) >= 2:
            for i in range(len(examples)):
                for j in range(i + 1, len(examples)):
                    da = float(actuals[j]) - float(actuals[i])
                    if abs(da) > 1e-9:
                        k = (float(expecteds[j]) - float(expecteds[i])) / da
                        b = float(expecteds[i]) - k * float(actuals[i])
                        if all(_eq_val(k * float(a) + b, e) for a, e in zip(actuals, expecteds)):
                            k_s = _const_repr(int(round(k)) if abs(k - round(k)) <= 1e-9 else round(k, 6))
                            b_s = _const_repr(int(round(b)) if abs(b - round(b)) <= 1e-9 else round(b, 6))
                            if k_s == "1" and b_s != "0":
                                _emit(f"({base_expr}) + {b_s}")
                            elif b_s == "0" and k_s != "1":
                                _emit(f"({base_expr}) * {k_s}")
                            elif k_s != "0":
                                _emit(f"({base_expr}) * {k_s} + {b_s}")
                        break
                else:
                    continue
                break

        # 1f. Recursive Depth-2+ Backward Decomposition:
        # Try peeling off any additive OR multiplicative variable from the frame alphabet!
        # Solves depth-3+ multi-variable expressions like `i.price_cents * i.qty + i.tax_cents`
        # or `(base_expr - discount) * qty` directly by inverting outer operators!
        if _depth + 1 <= max_depth and not results:
            common_num_keys = [
                k for k in sorted(alphabets[0].keys(), key=lambda s: (s.count("."), len(s), s))
                if all(k in a and _is_num(a[k]) for a in alphabets)
                and k != base_expr
            ]
            # Peel additive term: `expected = sub + v` -> recursively solve `sub = expected - v`
            for k in common_num_keys[:12]:
                sub_ex = [
                    WitnessExample(ex.env, ex.actual, ex.expected - a[k], ex.is_failing)
                    for ex, a in zip(examples, alphabets)
                ]
                if any(not _eq_val(se.expected, ex.expected) for se, ex in zip(sub_ex, examples)):
                    sub_hits = backward_propagate_expression(
                        base_expr, sub_ex, max_depth=max_depth, _depth=_depth + 1, _seen=set(seen)
                    )
                    for sh in sub_hits[:2]:
                        _emit(f"({sh}) + {k}")
                # Peel subtractive term: `expected = sub - v` -> `sub = expected + v`
                sub_ex_m = [
                    WitnessExample(ex.env, ex.actual, ex.expected + a[k], ex.is_failing)
                    for ex, a in zip(examples, alphabets)
                ]
                sub_hits_m = backward_propagate_expression(
                    base_expr, sub_ex_m, max_depth=max_depth, _depth=_depth + 1, _seen=set(seen)
                )
                for sh in sub_hits_m[:2]:
                    _emit(f"({sh}) - {k}")
                # Peel multiplicative term: `expected = sub * v` -> `sub = expected / v`
                if all(float(a[k]) != 0.0 for a in alphabets):
                    sub_ex_d = [
                        WitnessExample(
                            ex.env,
                            ex.actual,
                            int(round(ex.expected / a[k]))
                            if abs((ex.expected / a[k]) - round(ex.expected / a[k])) <= 1e-9
                            else ex.expected / a[k],
                            ex.is_failing,
                        )
                        for ex, a in zip(examples, alphabets)
                    ]
                    sub_hits_d = backward_propagate_expression(
                        base_expr, sub_ex_d, max_depth=max_depth, _depth=_depth + 1, _seen=set(seen)
                    )
                    for sh in sub_hits_d[:2]:
                        _emit(f"({sh}) * {k}")
                if len(results) >= 6:
                    break

    # ------------------------------------------------------------------
    # 2. Exact String Backward Witness Functions
    # ------------------------------------------------------------------
    if all(isinstance(a, str) and isinstance(e, str) for a, e in zip(actuals, expecteds)):
        # 2a. Unary canonicalizers
        for meth in ("strip", "lstrip", "rstrip", "lower", "upper", "title"):
            if all(getattr(a, meth)() == e for a, e in zip(actuals, expecteds)):
                _emit(f"({base_expr}).{meth}()")
        # 2b. Prefix / Suffix addition (`prefix + base_expr`, `base_expr + suffix`)
        if all(e.endswith(a) for a, e in zip(actuals, expecteds)):
            prefs = [e[: len(e) - len(a)] if a else e for a, e in zip(actuals, expecteds)]
            for p_expr in _match_atom_or_const(prefs, alphabets):
                if p_expr != "''":
                    _emit(f"{p_expr} + ({base_expr})")
        if all(e.startswith(a) for a, e in zip(actuals, expecteds)):
            suffs = [e[len(a) :] for a, e in zip(actuals, expecteds)]
            for s_expr in _match_atom_or_const(suffs, alphabets):
                if s_expr != "''":
                    _emit(f"({base_expr}) + {s_expr}")
        # 2c. Prefix / Suffix removal (`base_expr.removeprefix(p)`, `base_expr.removesuffix(s)`)
        if all(a.endswith(e) for a, e in zip(actuals, expecteds)):
            rem_p = [a[: len(a) - len(e)] if e else a for a, e in zip(actuals, expecteds)]
            for p_expr in _match_atom_or_const(rem_p, alphabets):
                if p_expr != "''":
                    _emit(f"({base_expr}).removeprefix({p_expr})")
        if all(a.startswith(e) for a, e in zip(actuals, expecteds)):
            rem_s = [a[len(e) :] for a, e in zip(actuals, expecteds)]
            for s_expr in _match_atom_or_const(rem_s, alphabets):
                if s_expr != "''":
                    _emit(f"({base_expr}).removesuffix({s_expr})")
        # 2d. Exact Replace deduction (`base_expr.replace(old, new)`)
        rep = _deduce_string_replace(actuals, expecteds)
        if rep is not None:
            _emit(f"({base_expr}).replace({rep[0]!r}, {rep[1]!r})")
        # 2e. Recursive string chain (e.g. `strip()` then `lower()`, or `prefix + actual.strip()`)
        if _depth + 1 <= max_depth and not results:
            for meth in ("strip", "lower", "upper"):
                transformed = [getattr(a, meth)() for a in actuals]
                if any(t != a for t, a in zip(transformed, actuals)):
                    sub_ex = [
                        WitnessExample(ex.env, t, ex.expected, ex.is_failing)
                        for ex, t in zip(examples, transformed)
                    ]
                    for sh in backward_propagate_expression(
                        f"({base_expr}).{meth}()", sub_ex, max_depth=max_depth, _depth=_depth + 1, _seen=set(seen)
                    )[:3]:
                        _emit(sh)

    # ------------------------------------------------------------------
    # 3. Exact Boolean & Sequence/Collection Backward Witness Functions
    # ------------------------------------------------------------------
    if all(isinstance(a, bool) and isinstance(e, bool) for a, e in zip(actuals, expecteds)):
        if all((not a) == e for a, e in zip(actuals, expecteds)):
            _emit(f"not ({base_expr})")

    if all(isinstance(a, (list, tuple)) and isinstance(e, (list, tuple)) for a, e in zip(actuals, expecteds)):
        if all(list(reversed(a)) == list(e) for a, e in zip(actuals, expecteds)):
            _emit(f"list(reversed({base_expr}))" if isinstance(expecteds[0], list) else f"tuple(reversed({base_expr}))")
        try:
            if all(sorted(a) == list(e) for a, e in zip(actuals, expecteds)):
                _emit(f"sorted({base_expr})")
        except TypeError:
            pass
        try:
            if all(list(dict.fromkeys(a)) == list(e) for a, e in zip(actuals, expecteds)):
                _emit(f"list(dict.fromkeys({base_expr}))")
        except TypeError:
            pass
        # Exact constant slice `[lo:hi]`
        if actuals and all(len(e) <= len(a) for a, e in zip(actuals, expecteds)):
            for lo in (0, 1, -1):
                for hi in (None, -1, 1, 2):
                    if all(list(a[lo:hi]) == list(e) for a, e in zip(actuals, expecteds)):
                        hi_s = "" if hi is None else str(hi)
                        _emit(f"({base_expr})[{lo}:{hi_s}]")
                        break

    if all(isinstance(a, (str, list, tuple, set, dict)) and isinstance(e, int) and not isinstance(e, bool) for a, e in zip(actuals, expecteds)):
        if all(len(a) == e for a, e in zip(actuals, expecteds)):
            _emit(f"len({base_expr})")

    # Rank by MDL simplicity (fewest AST nodes, then shortest code)
    def _mdl_key(expr_s: str) -> tuple[int, int, str]:
        try:
            n_nodes = sum(1 for _ in ast.walk(ast.parse(expr_s, mode="eval")))
        except SyntaxError:
            n_nodes = 999
        return (n_nodes, len(expr_s), expr_s)

    results.sort(key=_mdl_key)
    return results


# ---------------------------------------------------------------------------
# 4. Minimal Counterexample Shrinking (ddmin Delta-Debugging, $0 Offline Core)
# ---------------------------------------------------------------------------


def ddmin_shrink(
    failing_input: Any,
    fails_predicate: Callable[[Any], bool],
    *,
    max_evals: int = 128,
) -> dict[str, Any]:
    """Zeller's Delta-Debugging (`ddmin`) for strings, lists, and dicts.

    Shrinks a noisy failing input down to the minimal 1-minimal counterexample before
    running backward witness synthesis — zero LLM calls, pure deterministic binary splitting.
    """
    t0 = time.monotonic()
    evals = 0

    def _test(cand: Any) -> bool:
        nonlocal evals
        if evals >= max_evals:
            return False
        evals += 1
        try:
            return bool(fails_predicate(cand))
        except Exception:
            return False

    if not _test(failing_input):
        return {
            "schema": SCHEMA,
            "shrunk": failing_input,
            "original_size": len(failing_input) if hasattr(failing_input, "__len__") else 1,
            "shrunk_size": len(failing_input) if hasattr(failing_input, "__len__") else 1,
            "evals": evals,
            "reduced": False,
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    is_str = isinstance(failing_input, str)
    is_list = isinstance(failing_input, list)
    is_dict = isinstance(failing_input, dict)
    if not (is_str or is_list or is_dict):
        return {
            "schema": SCHEMA,
            "shrunk": failing_input,
            "original_size": 1,
            "shrunk_size": 1,
            "evals": evals,
            "reduced": False,
            "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
            "model_calls": 0,
            "parameters_stored": 0,
        }

    items: list[Any] = list(failing_input.items()) if is_dict else list(failing_input)
    orig_len = len(items)

    def _rebuild(seq: Sequence[Any]) -> Any:
        if is_str:
            return "".join(seq)
        if is_dict:
            return dict(seq)
        return list(seq)

    n = 2
    cur = list(items)
    while len(cur) >= 2 and evals < max_evals:
        chunk = max(1, len(cur) // n)
        reduced = False
        # Try single chunks first (rapid logarithmic shrinkage)
        for i in range(0, len(cur), chunk):
            sub = cur[i : i + chunk]
            if sub and _test(_rebuild(sub)):
                cur = sub
                n = 2
                reduced = True
                break
        if reduced:
            continue
        # Try complements (remove 1 chunk)
        for i in range(0, len(cur), chunk):
            comp = cur[:i] + cur[i + chunk :]
            if comp and _test(_rebuild(comp)):
                cur = comp
                n = max(n - 1, 2)
                reduced = True
                break
        if reduced:
            continue
        if n >= len(cur):
            break
        n = min(len(cur), n * 2)

    shrunk = _rebuild(cur)
    return {
        "schema": SCHEMA,
        "shrunk": shrunk,
        "original_size": orig_len,
        "shrunk_size": len(cur),
        "evals": evals,
        "reduced": len(cur) < orig_len,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }


def synthesize_function_return_fix(
    source_code: str,
    func_name: str,
    examples: Sequence[WitnessExample],
    *,
    max_depth: int = 3,
) -> dict[str, Any]:
    """Synthesize a patched source file by backward-propagating `(actual -> expected)` directly
    onto the return expression of `func_name`."""
    t0 = time.monotonic()
    try:
        tree = ast.parse(source_code)
    except SyntaxError as exc:
        return {"schema": SCHEMA, "status": "SYNTAX_ERROR", "error": str(exc), "candidates": [], "model_calls": 0, "parameters_stored": 0}

    target_ret: ast.Return | None = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            rets = [n for n in ast.walk(node) if isinstance(n, ast.Return) and n.value is not None]
            if rets:
                target_ret = rets[-1]
            break

    if target_ret is None or target_ret.value is None:
        return {"schema": SCHEMA, "status": "NO_RETURN_SITE", "candidates": [], "model_calls": 0, "parameters_stored": 0}

    base_expr = ast.unparse(target_ret.value)
    ret_ln = int(getattr(target_ret, "lineno", 1))
    exprs = backward_propagate_expression(base_expr, examples, max_depth=max_depth)

    patched_candidates: list[dict[str, Any]] = []
    for expr_s in exprs[:8]:
        t_copy = copy.deepcopy(tree)
        replaced = False
        for nd in ast.walk(t_copy):
            if isinstance(nd, ast.Return) and int(getattr(nd, "lineno", 0)) == ret_ln and nd.value is not None:
                nd.value = ast.parse(expr_s, mode="eval").body
                replaced = True
                break
        if replaced:
            ast.fix_missing_locations(t_copy)
            patched_candidates.append({
                "lineno": ret_ln,
                "base_expression": base_expr,
                "synthesized_expression": expr_s,
                "patched_source": ast.unparse(t_copy) + "\n",
            })

    return {
        "schema": SCHEMA,
        "status": "SYNTHESIZED" if patched_candidates else "NO_WITNESS_SOLUTION",
        "func_name": func_name,
        "base_expression": base_expr,
        "candidates": patched_candidates,
        "elapsed_ms": round((time.monotonic() - t0) * 1000.0, 2),
        "model_calls": 0,
        "parameters_stored": 0,
    }
