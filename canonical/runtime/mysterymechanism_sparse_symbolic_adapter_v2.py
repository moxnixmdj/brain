"""Sparse, benchmark-shaped symbolic discovery adapter for MysteryMechanism V2.

This is a zero-learned-byte candidate route. It is designed around the public
MysteryMechanism contract: two passive observations plus at most 2d+1 bounded
experiments. It does not contain or access private mechanisms and grants no
benchmark, family, capability, ownership, or terminal credit.

The key repair over the older expression-tree route is sparse-data model
selection: structures are ranked by leave-one-out prediction error, allowing
5-7 observation problems without pretending an underdetermined exact fit is a
proof. Existing continuous power/linear/monomial synthesis remains the first
route; this module adds a compact expression grammar and a bound-constrained
final discriminator.
"""
from __future__ import annotations

import itertools
import math
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_zero_learned_mechanism_synthesizer_v1 as base

SCHEMA = "PROJECT_BRAIN_MYSTERYMECHANISM_SPARSE_SYMBOLIC_ADAPTER_V2"
_EPS = 1e-12
_UNARY = (
    "neg", "abs", "square", "sqrt_abs", "pow_abs_1_3", "pow_abs_2_3",
    "pow_abs_1_4", "pow_abs_5_8", "pow_abs_4_5", "log1p_abs", "sat",
    "reciprocal", "exp", "sin", "cos",
)
_BINARY = ("add", "sub", "mul", "stable_div", "safe_div")
_COMMUTATIVE = {"add", "mul"}


class SparseSymbolicError(ValueError):
    pass


def _finite(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise SparseSymbolicError(field.upper() + "_INVALID")
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise SparseSymbolicError(field.upper() + "_INVALID") from exc
    if not math.isfinite(x):
        raise SparseSymbolicError(field.upper() + "_NONFINITE")
    return x


def _normalize_bounds(bounds: Mapping[str, Sequence[Any]]) -> dict[str, tuple[float, float]]:
    if not isinstance(bounds, Mapping) or not bounds:
        raise SparseSymbolicError("BOUNDS_REQUIRED")
    out: dict[str, tuple[float, float]] = {}
    for raw_name, raw_pair in bounds.items():
        name = str(raw_name).strip()
        if not name or not isinstance(raw_pair, Sequence) or isinstance(raw_pair, (str, bytes)) or len(raw_pair) != 2:
            raise SparseSymbolicError("BOUND_INVALID")
        lo = _finite(raw_pair[0], name + "_lo")
        hi = _finite(raw_pair[1], name + "_hi")
        if not lo < hi:
            raise SparseSymbolicError("BOUND_ORDER_INVALID:" + name)
        out[name] = (lo, hi)
    return dict(sorted(out.items()))


def _center(lo: float, hi: float) -> float:
    return math.sqrt(lo * hi) if lo > 0 and hi > 0 else (lo + hi) / 2.0


def plan_experiments(bounds: Mapping[str, Sequence[Any]]) -> dict[str, Any]:
    """Return 2d initial axis/corner probes with the final 1 experiment reserved."""
    b = _normalize_bounds(bounds)
    names = list(b)
    d = len(names)
    center = {name: _center(*b[name]) for name in names}
    initial: list[dict[str, float]] = []
    if d == 1:
        name = names[0]
        initial = [{name: b[name][0]}, {name: b[name][1]}]
    elif d == 2:
        a, z = names
        alo, ahi = b[a]
        zlo, zhi = b[z]
        initial = [
            {a: alo, z: zlo}, {a: ahi, z: zlo},
            {a: alo, z: zhi}, {a: ahi, z: zhi},
        ]
    else:
        for name in names:
            lo, hi = b[name]
            low = dict(center)
            high = dict(center)
            low[name] = lo
            high[name] = hi
            initial.extend([low, high])
    assert len(initial) == 2 * d
    return {
        "schema": SCHEMA,
        "status": "SPARSE_ACTIVE_PLAN_READY",
        "dimension": d,
        "active_budget": 2 * d + 1,
        "initial_experiments": initial,
        "reserved_final_experiment": center,
        "initial_experiment_count": len(initial),
        "reserved_count": 1,
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
    }


def _normalize_rows(rows: Sequence[Mapping[str, Any]], target: str, inputs: Sequence[str] | None):
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or len(rows) < 5:
        raise SparseSymbolicError("AT_LEAST_FIVE_ROWS_REQUIRED")
    target = str(target or "").strip()
    if not target:
        raise SparseSymbolicError("TARGET_REQUIRED")
    first = rows[0]
    if not isinstance(first, Mapping) or target not in first:
        raise SparseSymbolicError("TARGET_MISSING")
    if inputs is None:
        names = sorted(str(k) for k in first if str(k) != target)
    else:
        names = [str(x).strip() for x in inputs if str(x).strip()]
    if not names or len(names) != len(set(names)) or target in names or len(names) > 5:
        raise SparseSymbolicError("INPUTS_INVALID_OR_TOO_MANY")
    out = []
    for i, raw in enumerate(rows):
        if not isinstance(raw, Mapping) or target not in raw or any(name not in raw for name in names):
            raise SparseSymbolicError("ROW_SCHEMA_MISMATCH:" + str(i))
        row = {name: _finite(raw[name], name) for name in names}
        row[target] = _finite(raw[target], target)
        out.append(row)
    return target, tuple(names), out


def _nrmse(actual: Sequence[float], predicted: Sequence[float]) -> float:
    if len(actual) != len(predicted) or len(actual) < 2:
        return math.inf
    mean = sum(actual) / len(actual)
    spread = math.sqrt(sum((x - mean) ** 2 for x in actual) / len(actual))
    scale = max(spread, max(abs(x) for x in actual) * 1e-9, _EPS)
    return math.sqrt(sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual)) / scale


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    n = len(vector)
    if n == 0 or len(matrix) != n or any(len(row) != n for row in matrix):
        return None
    a = [list(map(float, row)) + [float(vector[i])] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) <= 1e-10:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        div = a[col][col]
        a[col] = [x / div for x in a[col]]
        for r in range(n):
            if r == col:
                continue
            factor = a[r][col]
            if abs(factor) <= _EPS:
                continue
            a[r] = [x - factor * y for x, y in zip(a[r], a[col])]
    out = [a[i][-1] for i in range(n)]
    return out if all(math.isfinite(x) for x in out) else None


def _fit(feature_columns: Sequence[Sequence[float]], targets: Sequence[float]) -> list[float] | None:
    p = len(feature_columns) + 1
    if len(targets) < p + 1 or any(len(col) != len(targets) for col in feature_columns):
        return None
    xtx = [[0.0] * p for _ in range(p)]
    xty = [0.0] * p
    for r, y in enumerate(targets):
        x = [1.0] + [float(col[r]) for col in feature_columns]
        for i in range(p):
            xty[i] += x[i] * float(y)
            for j in range(p):
                xtx[i][j] += x[i] * x[j]
    for i in range(p):
        xtx[i][i] += 1e-12
    return _solve(xtx, xty)


def _unary(op: str, x: float) -> float | None:
    try:
        if op == "neg":
            y = -x
        elif op == "abs":
            y = abs(x)
        elif op == "square":
            y = x * x
        elif op == "sqrt_abs":
            y = math.sqrt(abs(x))
        elif op == "pow_abs_1_3":
            y = abs(x) ** (1.0 / 3.0)
        elif op == "pow_abs_2_3":
            y = abs(x) ** (2.0 / 3.0)
        elif op == "pow_abs_1_4":
            y = abs(x) ** 0.25
        elif op == "pow_abs_5_8":
            y = abs(x) ** 0.625
        elif op == "pow_abs_4_5":
            y = abs(x) ** 0.8
        elif op == "log1p_abs":
            y = math.log1p(abs(x))
        elif op == "sat":
            y = x / (1.0 + abs(x))
        elif op == "reciprocal":
            if abs(x) <= _EPS:
                return None
            y = 1.0 / x
        elif op == "exp":
            if x > 700.0:
                return None
            y = math.exp(x)
        elif op == "sin":
            y = math.sin(x)
        elif op == "cos":
            y = math.cos(x)
        else:
            return None
    except (OverflowError, ValueError, ZeroDivisionError):
        return None
    return y if math.isfinite(y) else None


def _binary(op: str, left: float, right: float) -> float | None:
    try:
        if op == "add":
            y = left + right
        elif op == "sub":
            y = left - right
        elif op == "mul":
            y = left * right
        elif op == "stable_div":
            y = left / (1.0 + abs(right))
        elif op == "safe_div":
            if abs(right) <= _EPS:
                return None
            y = left / right
        else:
            return None
    except (OverflowError, ValueError, ZeroDivisionError):
        return None
    return y if math.isfinite(y) else None


def _eval(tree: Mapping[str, Any], row: Mapping[str, float]) -> float:
    op = str(tree.get("op") or "")
    if op == "one":
        return 1.0
    if op == "var":
        name = str(tree.get("name") or "")
        if name not in row:
            raise SparseSymbolicError("TREE_VARIABLE_MISSING:" + name)
        return float(row[name])
    if op in _UNARY:
        v = _unary(op, _eval(tree.get("arg") or {}, row))
        if v is None:
            raise SparseSymbolicError("TREE_UNARY_NONFINITE:" + op)
        return v
    if op in _BINARY:
        v = _binary(op, _eval(tree.get("left") or {}, row), _eval(tree.get("right") or {}, row))
        if v is None:
            raise SparseSymbolicError("TREE_BINARY_NONFINITE:" + op)
        return v
    raise SparseSymbolicError("TREE_OPERATOR_INVALID")


def _sig(tree: Mapping[str, Any], names: Sequence[str]) -> str:
    op = str(tree.get("op") or "")
    if op == "one":
        return "1"
    if op == "var":
        name = str(tree.get("name") or "")
        if name not in names:
            raise SparseSymbolicError("TREE_VARIABLE_UNKNOWN:" + name)
        return "v" + str(names.index(name))
    if op in _UNARY:
        return op + "(" + _sig(tree["arg"], names) + ")"
    if op in _BINARY:
        a, b = _sig(tree["left"], names), _sig(tree["right"], names)
        if op in _COMMUTATIVE and b < a:
            a, b = b, a
        return op + "(" + a + "," + b + ")"
    raise SparseSymbolicError("TREE_OPERATOR_INVALID")


def _complexity(tree: Mapping[str, Any]) -> int:
    op = str(tree.get("op") or "")
    if op in {"one", "var"}:
        return 1
    if op in _UNARY:
        return 1 + _complexity(tree["arg"])
    if op in _BINARY:
        return 1 + _complexity(tree["left"]) + _complexity(tree["right"])
    raise SparseSymbolicError("TREE_OPERATOR_INVALID")


def _feature(tree: Mapping[str, Any], rows: Sequence[Mapping[str, float]]) -> list[float] | None:
    try:
        vals = [_eval(tree, row) for row in rows]
    except SparseSymbolicError:
        return None
    return vals if all(math.isfinite(x) for x in vals) else None


def _loo_score(columns: Sequence[Sequence[float]], y: Sequence[float]) -> float:
    preds, gold = [], []
    n = len(y)
    for hold in range(n):
        train_cols = [[col[i] for i in range(n) if i != hold] for col in columns]
        train_y = [y[i] for i in range(n) if i != hold]
        coeff = _fit(train_cols, train_y)
        if coeff is None:
            return math.inf
        pred = coeff[0] + sum(coeff[j + 1] * columns[j][hold] for j in range(len(columns)))
        if not math.isfinite(pred):
            return math.inf
        preds.append(pred)
        gold.append(y[hold])
    return _nrmse(gold, preds)


def sparse_discover(
    rows: Sequence[Mapping[str, Any]],
    *,
    target: str,
    inputs: Sequence[str] | None = None,
    max_depth: int = 2,
    beam_width: int = 24,
    pair_pool: int = 18,
) -> dict[str, Any]:
    target, names, data = _normalize_rows(rows, target, inputs)
    if not isinstance(max_depth, int) or not 1 <= max_depth <= 3:
        raise SparseSymbolicError("MAX_DEPTH_INVALID")
    if not isinstance(beam_width, int) or not 4 <= beam_width <= 48:
        raise SparseSymbolicError("BEAM_WIDTH_INVALID")
    if not isinstance(pair_pool, int) or not 4 <= pair_pool <= 32:
        raise SparseSymbolicError("PAIR_POOL_INVALID")
    y = [float(row[target]) for row in data]
    features: list[dict[str, Any]] = []
    seen: set[tuple[float, ...]] = set()

    def admit(tree: Mapping[str, Any]):
        vals = _feature(tree, data)
        if vals is None:
            return None
        scale = max(1.0, max(abs(v) for v in vals))
        key = tuple(round(v / scale, 10) for v in vals)
        if key in seen:
            return None
        seen.add(key)
        loo = _loo_score([vals], y)
        coeff = _fit([vals], y)
        if coeff is None or not math.isfinite(loo):
            return None
        pred = [coeff[0] + coeff[1] * v for v in vals]
        rec = {
            "tree": tree, "values": vals, "signature": _sig(tree, names),
            "complexity": _complexity(tree), "loo_nrmse": loo,
            "all_nrmse": _nrmse(y, pred), "coefficients": coeff,
        }
        features.append(rec)
        return rec

    beam = []
    for name in names:
        rec = admit({"op": "var", "name": name})
        if rec:
            beam.append(rec)
    admit({"op": "one"})
    beam.sort(key=lambda r: (r["loo_nrmse"], r["complexity"], r["signature"]))

    for _ in range(max_depth):
        global_best = sorted(features, key=lambda r: (r["loo_nrmse"], r["complexity"], r["signature"]))[:beam_width]
        pool, sigs = [], set()
        for rec in beam + global_best:
            if rec["signature"] in sigs:
                continue
            sigs.add(rec["signature"])
            pool.append(rec)
            if len(pool) >= 12:
                break
        proposed = []
        for rec in beam:
            for op in _UNARY:
                proposed.append({"op": op, "arg": rec["tree"]})
        for i, left in enumerate(pool):
            for j, right in enumerate(pool):
                for op in _BINARY:
                    if op in _COMMUTATIVE and j < i:
                        continue
                    proposed.append({"op": op, "left": left["tree"], "right": right["tree"]})
        new = []
        for tree in proposed:
            rec = admit(tree)
            if rec:
                new.append(rec)
        new.sort(key=lambda r: (r["loo_nrmse"], r["complexity"], r["signature"]))
        beam = new[:beam_width]
        if not beam:
            break

    ordered = sorted(features, key=lambda r: (r["loo_nrmse"], r["all_nrmse"], r["complexity"], r["signature"]))
    combos = []
    pool = ordered[:pair_pool]
    for i, left in enumerate(pool):
        for right in pool[i + 1:]:
            loo = _loo_score([left["values"], right["values"]], y)
            coeff = _fit([left["values"], right["values"]], y)
            if coeff is None or not math.isfinite(loo):
                continue
            pred = [coeff[0] + coeff[1] * left["values"][k] + coeff[2] * right["values"][k] for k in range(len(y))]
            combos.append({
                "features": [left["tree"], right["tree"]],
                "feature_signatures": [left["signature"], right["signature"]],
                "coefficients": coeff,
                "loo_nrmse": loo,
                "all_nrmse": _nrmse(y, pred),
                "complexity": left["complexity"] + right["complexity"] + 2,
            })
    singles = [{
        "features": [rec["tree"]], "feature_signatures": [rec["signature"]],
        "coefficients": rec["coefficients"], "loo_nrmse": rec["loo_nrmse"],
        "all_nrmse": rec["all_nrmse"], "complexity": rec["complexity"] + 1,
    } for rec in ordered[:max(pair_pool, 8)]]
    candidates = singles + combos
    candidates.sort(key=lambda c: (
        max(float(c["loo_nrmse"]), float(c["all_nrmse"])),
        int(c["complexity"]), tuple(c["feature_signatures"])
    ))
    return {
        "schema": SCHEMA,
        "status": "SPARSE_CANDIDATES_FOUND" if candidates else "SPARSE_GRAMMAR_EXHAUSTED",
        "row_count": len(data),
        "input_variables": list(names),
        "candidate_count": len(candidates),
        "best_candidate": candidates[0] if candidates else None,
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
        "dynamic_code_execution": False,
        "random_search": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def _tree_expr(tree: Mapping[str, Any]) -> str:
    op = str(tree.get("op") or "")
    if op == "one":
        return "1.0"
    if op == "var":
        return str(tree["name"])
    a = _tree_expr(tree.get("arg") or {}) if op in _UNARY else None
    if op == "neg":
        return f"(-({a}))"
    if op == "abs":
        return f"abs({a})"
    if op == "square":
        return f"(({a})**2)"
    powers = {
        "sqrt_abs": "0.5", "pow_abs_1_3": "(1/3)", "pow_abs_2_3": "(2/3)",
        "pow_abs_1_4": "0.25", "pow_abs_5_8": "0.625", "pow_abs_4_5": "0.8",
    }
    if op in powers:
        return f"(abs({a})**{powers[op]})"
    if op == "log1p_abs":
        return f"log1p(abs({a}))"
    if op == "sat":
        return f"(({a})/(1+abs({a})))"
    if op == "reciprocal":
        return f"(1.0/({a}))"
    if op == "exp":
        return f"exp({a})"
    if op == "sin":
        return f"sin({a})"
    if op == "cos":
        return f"cos({a})"
    if op in _BINARY:
        left, right = _tree_expr(tree["left"]), _tree_expr(tree["right"])
        if op == "add":
            return f"(({left})+({right}))"
        if op == "sub":
            return f"(({left})-({right}))"
        if op == "mul":
            return f"(({left})*({right}))"
        if op == "stable_div":
            return f"(({left})/(1+abs({right})))"
        if op == "safe_div":
            return f"(({left})/({right}))"
    raise SparseSymbolicError("TREE_SERIALIZATION_INVALID")


def _sparse_predict(candidate: Mapping[str, Any], point: Mapping[str, Any]) -> float:
    coeff = [float(x) for x in candidate["coefficients"]]
    value = coeff[0]
    for c, tree in zip(coeff[1:], candidate["features"]):
        value += c * _eval(tree, {str(k): _finite(v, str(k)) for k, v in point.items()})
    if not math.isfinite(value):
        raise SparseSymbolicError("SPARSE_PREDICTION_NONFINITE")
    return value


def _base_expr(candidate: Mapping[str, Any]) -> str | None:
    variables = [str(x) for x in candidate.get("variables", [])]
    family = candidate.get("family")
    if family == "linear":
        terms = [repr(float(candidate["intercept"]))]
        terms.extend(f"({repr(float(c))})*{v}" for c, v in zip(candidate["coefficients"], variables))
        return "+".join(terms)
    if family == "log_power":
        expr = repr(float(candidate["scale"]))
        for exponent, var in zip(candidate["exponents"], variables):
            expr += f"*({var}**({repr(float(exponent))}))"
        return expr
    if family == "monomial" and candidate.get("target_transform") == "identity":
        expr = repr(float(candidate["intercept"])) + "+(" + repr(float(candidate["scale"])) + ")"
        for exponent, var in zip(candidate["exponents"], variables):
            if float(exponent) != 0.0:
                expr += f"*({var}**({repr(float(exponent))}))"
        return expr
    return None


def _sparse_expr(candidate: Mapping[str, Any]) -> str:
    coeff = [float(x) for x in candidate["coefficients"]]
    parts = [repr(coeff[0])]
    for c, tree in zip(coeff[1:], candidate["features"]):
        parts.append(f"({repr(c)})*({_tree_expr(tree)})")
    return "+".join(parts)


def solve(rows: Sequence[Mapping[str, Any]], *, bounds: Mapping[str, Sequence[Any]], target: str = "out", fit_threshold: float = 0.05) -> dict[str, Any]:
    b = _normalize_bounds(bounds)
    fit_threshold = _finite(fit_threshold, "fit_threshold")
    if fit_threshold <= 0:
        raise SparseSymbolicError("FIT_THRESHOLD_INVALID")
    options = []

    try:
        bd = base.discover(rows, target=target, inputs=list(b))
        if bd.get("candidates"):
            bc = bd["candidates"][0]
            expr = _base_expr(bc)
            if expr is not None:
                err = max(float(bc.get("nrmse", math.inf)), float(bc.get("validation_nrmse", bc.get("nrmse", math.inf))))
                options.append(("BASE_ZERO_LEARNED", err, int(bc.get("complexity", 999)), bc, expr))
    except (base.MechanismSynthesisError, ValueError, OverflowError):
        pass

    try:
        sd = sparse_discover(rows, target=target, inputs=list(b))
        sc = sd.get("best_candidate")
        if sc is not None:
            err = max(float(sc["loo_nrmse"]), float(sc["all_nrmse"]))
            options.append(("SPARSE_LOO_EXPRESSION", err, int(sc["complexity"]), sc, _sparse_expr(sc)))
    except SparseSymbolicError:
        pass

    options.sort(key=lambda x: (x[1], x[2], x[0]))
    if not options or options[0][1] > fit_threshold:
        return {
            "schema": SCHEMA, "status": "FAIL_CLOSED__EXPAND_MECHANISM_LANGUAGE",
            "candidate": None, "expression": None,
            "best_conservative_nrmse": options[0][1] if options else None,
            "fit_threshold": fit_threshold,
            "persistent_learned_bytes": 0, "external_learned_capability_calls": 0,
            "acceptance_credit_delta": 0, "family_credit_delta": 0,
        }
    route, error, complexity, candidate, expression = options[0]
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_READY__UNVERIFIED_ON_PRIVATE_STRUCTURAL_PROBES",
        "route": route,
        "candidate": candidate,
        "expression": expression,
        "conservative_nrmse": error,
        "complexity": complexity,
        "fit_threshold": fit_threshold,
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
        "dynamic_code_execution": False,
        "random_search": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "private_score_claimed": False,
    }


def choose_final_experiment(
    rows: Sequence[Mapping[str, Any]],
    *,
    bounds: Mapping[str, Sequence[Any]],
    target: str = "out",
    grid_levels: int = 5,
) -> dict[str, Any]:
    """Choose the reserved last experiment by model disagreement, always in bounds."""
    b = _normalize_bounds(bounds)
    default = {name: _center(lo, hi) for name, (lo, hi) in b.items()}
    if len(rows) < 5:
        return {"status": "RESERVED_CENTER", "point": default, "reason": "INSUFFICIENT_ROWS_FOR_DISAGREEMENT"}
    try:
        discovery = base.discover(rows, target=target, inputs=list(b), top_k=8)
        candidates = discovery.get("candidates") or []
    except (base.MechanismSynthesisError, ValueError, OverflowError):
        candidates = []
    if len(candidates) < 2:
        return {"status": "RESERVED_CENTER", "point": default, "reason": "FEWER_THAN_TWO_BASE_CANDIDATES"}

    axes = []
    for name, (lo, hi) in b.items():
        if lo > 0 and hi > 0:
            ratio = hi / lo
            vals = [lo * (ratio ** (i / (grid_levels - 1))) for i in range(grid_levels)]
        else:
            vals = [lo + (hi - lo) * i / (grid_levels - 1) for i in range(grid_levels)]
        axes.append(vals)
    best = None
    for values in itertools.product(*axes):
        point = dict(zip(b, values))
        preds = []
        for cand in candidates:
            try:
                preds.append(base.predict(cand, point))
            except base.MechanismSynthesisError:
                pass
        if len(preds) < 2:
            continue
        mean = sum(preds) / len(preds)
        spread = math.sqrt(sum((x - mean) ** 2 for x in preds) / len(preds))
        score = spread / max(1.0, abs(mean), max(abs(x) for x in preds))
        key = (score, tuple(values))
        if best is None or key > best[0]:
            best = (key, point)
    if best is None or best[0][0] <= 1e-12:
        return {"status": "RESERVED_CENTER", "point": default, "reason": "NO_USEFUL_DISAGREEMENT"}
    return {
        "status": "BOUND_CONSTRAINED_DISCRIMINATOR",
        "point": best[1],
        "normalized_disagreement": best[0][0],
        "candidate_count": len(candidates),
        "all_coordinates_within_declared_bounds": True,
    }
