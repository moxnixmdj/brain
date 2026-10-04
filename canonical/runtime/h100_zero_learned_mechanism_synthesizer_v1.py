"""Deterministic zero-learned-byte mechanism synthesizer for H100 Gate 1.

Purpose:
- generate simple mathematical mechanism candidates from structured numeric evidence;
- canonicalize candidate structure independently of surface variable names;
- choose informative next probes from disagreement among surviving candidates;
- fail closed when the grammar cannot explain the observations.

This is a mechanism candidate generator, not an acceptance result. It contains
no learned parameters and grants no execution, promotion, or capability credit.
"""
from __future__ import annotations

import itertools
import math
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_H100_ZERO_LEARNED_MECHANISM_SYNTHESIZER_V1"

class MechanismSynthesisError(ValueError):
    pass

_EPS = 1e-12
_EXPONENTS = (-3, -2, -1, -0.5, 0, 0.5, 1, 2, 3)


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise MechanismSynthesisError(field.upper() + "_INVALID")
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise MechanismSynthesisError(field.upper() + "_INVALID") from exc
    if not math.isfinite(x):
        raise MechanismSynthesisError(field.upper() + "_NONFINITE")
    return x


def _normalize_rows(rows: Sequence[Mapping[str, Any]], target: str, inputs: Sequence[str] | None):
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or len(rows) < 5:
        raise MechanismSynthesisError("AT_LEAST_FIVE_ROWS_REQUIRED")
    target = str(target or "").strip()
    if not target:
        raise MechanismSynthesisError("TARGET_REQUIRED")
    first = rows[0]
    if not isinstance(first, Mapping) or target not in first:
        raise MechanismSynthesisError("TARGET_MISSING")
    if inputs is None:
        names = sorted(str(k) for k in first.keys() if str(k) != target)
    else:
        names = [str(x).strip() for x in inputs if str(x).strip()]
    if not names or len(names) != len(set(names)) or target in names:
        raise MechanismSynthesisError("INPUTS_INVALID")
    out = []
    for i, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise MechanismSynthesisError(f"ROW_NOT_MAPPING:{i}")
        if target not in raw or any(name not in raw for name in names):
            raise MechanismSynthesisError(f"ROW_SCHEMA_MISMATCH:{i}")
        row = {name: _finite_number(raw[name], name) for name in names}
        row[target] = _finite_number(raw[target], target)
        out.append(row)
    return target, tuple(names), out


def _pow(x: float, exponent: float) -> float | None:
    if exponent < 0 and abs(x) <= _EPS:
        return None
    if abs(exponent - round(exponent)) > _EPS and x < 0:
        return None
    try:
        y = x ** exponent
    except (OverflowError, ZeroDivisionError, ValueError):
        return None
    return y if math.isfinite(y) else None


def _monomial_value(row: Mapping[str, float], variables: Sequence[str], exponents: Sequence[float]) -> float | None:
    value = 1.0
    for name, exponent in zip(variables, exponents):
        if exponent == 0:
            continue
        term = _pow(float(row[name]), float(exponent))
        if term is None:
            return None
        value *= term
        if not math.isfinite(value):
            return None
    return value


def _target_transform(kind: str, y: float) -> float | None:
    if kind == "identity":
        return y
    if kind == "log_abs":
        if abs(y) <= _EPS:
            return None
        return math.log(abs(y))
    if kind == "reciprocal":
        if abs(y) <= _EPS:
            return None
        return 1.0 / y
    raise MechanismSynthesisError("TARGET_TRANSFORM_INVALID")


def _target_inverse(kind: str, value: float, sign: float = 1.0) -> float | None:
    try:
        if kind == "identity":
            out = value
        elif kind == "log_abs":
            out = sign * math.exp(value)
        elif kind == "reciprocal":
            if abs(value) <= _EPS:
                return None
            out = 1.0 / value
        else:
            return None
    except (OverflowError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _fit_affine(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float] | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    var = sum((x - mx) ** 2 for x in xs)
    if var <= _EPS:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    scale = cov / var
    intercept = my - scale * mx
    if not (math.isfinite(scale) and math.isfinite(intercept)):
        return None
    return scale, intercept


def _rmse(actual: Sequence[float], predicted: Sequence[float]) -> float:
    if len(actual) != len(predicted) or not actual:
        return math.inf
    return math.sqrt(sum((a - p) ** 2 for a, p in zip(actual, predicted)) / len(actual))


def _nrmse(actual: Sequence[float], predicted: Sequence[float]) -> float:
    if len(actual) < 2:
        return math.inf
    mean = sum(actual) / len(actual)
    spread = math.sqrt(sum((x - mean) ** 2 for x in actual) / len(actual))
    scale = max(spread, max(abs(x) for x in actual) * 1e-9, _EPS)
    return _rmse(actual, predicted) / scale


def _fmt_exp(exponent: float) -> str:
    return str(int(exponent)) if abs(exponent - round(exponent)) <= _EPS else str(exponent)


def _expression(exponents: Sequence[float], variables: Sequence[str]) -> str:
    terms = []
    for name, exponent in zip(variables, exponents):
        if exponent == 0:
            continue
        terms.append(name if exponent == 1 else f"{name}^{_fmt_exp(float(exponent))}")
    return " * ".join(terms) if terms else "1"


def _signature(target_transform: str, exponents: Sequence[float]) -> str:
    active = sorted(float(e) for e in exponents if abs(float(e)) > _EPS)
    return f"{target_transform}|monomial|" + ",".join(_fmt_exp(e) for e in active)


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
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


def _fit_linear_basis(rows: Sequence[Mapping[str, float]], target: str, variables: Sequence[str]):
    p = len(variables) + 1
    if len(rows) < p + 1:
        return None
    xtx = [[0.0] * p for _ in range(p)]
    xty = [0.0] * p
    for row in rows:
        feats = [1.0] + [float(row[v]) for v in variables]
        y = float(row[target])
        for i in range(p):
            xty[i] += feats[i] * y
            for j in range(p):
                xtx[i][j] += feats[i] * feats[j]
    for i in range(p):
        xtx[i][i] += 1e-12
    sol = _solve_linear_system(xtx, xty)
    if sol is None:
        return None
    return sol[0], sol[1:]


def _fit_log_power(rows: Sequence[Mapping[str, float]], target: str, variables: Sequence[str]):
    """Fit y = scale * product(x_i ** p_i) with robust near-zero sign-noise handling."""
    if len(rows) < len(variables) + 2:
        return None
    if any(float(row[v]) <= 0 for row in rows for v in variables):
        return None
    nonzero = [row for row in rows if abs(float(row[target])) > _EPS]
    if len(nonzero) < len(variables) + 2:
        return None
    anchor = max(nonzero, key=lambda row: abs(float(row[target])))
    dominant_sign = 1.0 if float(anchor[target]) > 0 else -1.0
    max_abs = abs(float(anchor[target]))
    usable = []
    for row in nonzero:
        y = float(row[target])
        sign = 1.0 if y > 0 else -1.0
        if sign != dominant_sign:
            if abs(y) <= 0.02 * max_abs:
                continue
            return None
        usable.append(row)
    if len(usable) < len(variables) + 2:
        return None
    p = len(variables) + 1
    xtx = [[0.0] * p for _ in range(p)]
    xty = [0.0] * p
    for row in usable:
        feats = [1.0] + [math.log(float(row[v])) for v in variables]
        y = math.log(abs(float(row[target])))
        for i in range(p):
            xty[i] += feats[i] * y
            for j in range(p):
                xtx[i][j] += feats[i] * feats[j]
    for i in range(p):
        xtx[i][i] += 1e-12
    sol = _solve_linear_system(xtx, xty)
    if sol is None:
        return None
    log_scale, *exponents = sol
    try:
        scale = dominant_sign * math.exp(log_scale)
    except OverflowError:
        return None
    if not math.isfinite(scale) or not all(math.isfinite(x) for x in exponents):
        return None
    return scale, exponents


def _candidate_predictions(candidate: Mapping[str, Any], rows: Sequence[Mapping[str, float]], target: str):
    preds = []
    variables = candidate["variables"]
    if candidate.get("family") == "linear":
        coeffs = [float(x) for x in candidate["coefficients"]]
        for row in rows:
            y = float(candidate["intercept"]) + sum(c * float(row[v]) for c, v in zip(coeffs, variables))
            if not math.isfinite(y):
                return None
            preds.append(y)
        return preds

    if candidate.get("family") == "log_power":
        exponents = [float(x) for x in candidate["exponents"]]
        for row in rows:
            value = float(candidate["scale"])
            for exponent, variable in zip(exponents, variables):
                term = _pow(float(row[variable]), exponent)
                if term is None:
                    return None
                value *= term
            if not math.isfinite(value):
                return None
            preds.append(value)
        return preds

    sign = float(candidate.get("target_sign", 1.0))
    exponents = candidate["exponents"]
    for row in rows:
        f = _monomial_value(row, variables, exponents)
        if f is None:
            return None
        transformed = float(candidate["intercept"]) + float(candidate["scale"]) * f
        y = _target_inverse(str(candidate["target_transform"]), transformed, sign=sign)
        if y is None:
            return None
        preds.append(y)
    return preds


def discover(
    rows: Sequence[Mapping[str, Any]],
    *,
    target: str,
    inputs: Sequence[str] | None = None,
    max_active_variables: int = 3,
    top_k: int = 16,
) -> dict[str, Any]:
    target, variables, data = _normalize_rows(rows, target, inputs)
    if not isinstance(max_active_variables, int) or isinstance(max_active_variables, bool) or max_active_variables < 1:
        raise MechanismSynthesisError("MAX_ACTIVE_VARIABLES_INVALID")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise MechanismSynthesisError("TOP_K_INVALID")

    train = [row for i, row in enumerate(data) if i % 4 != 3]
    valid = [row for i, row in enumerate(data) if i % 4 == 3]
    if len(valid) < 1:
        valid = data[-1:]
        train = data[:-1]

    candidates = []
    grammar_count = 0
    for exponents in itertools.product(_EXPONENTS, repeat=len(variables)):
        active = sum(1 for e in exponents if e != 0)
        if active == 0 or active > max_active_variables:
            continue
        complexity = sum(abs(float(e)) for e in exponents) + active
        if complexity > 9:
            continue
        grammar_count += 1
        x_train = []
        valid_train_rows = []
        for row in train:
            value = _monomial_value(row, variables, exponents)
            if value is None:
                continue
            x_train.append(value)
            valid_train_rows.append(row)
        if len(x_train) < max(4, len(train) - 1):
            continue

        for target_transform in ("identity", "log_abs", "reciprocal"):
            y_train = []
            x2 = []
            signs = []
            for x, row in zip(x_train, valid_train_rows):
                y = _target_transform(target_transform, row[target])
                if y is None:
                    continue
                x2.append(x)
                y_train.append(y)
                signs.append(1.0 if row[target] >= 0 else -1.0)
            if len(x2) < max(4, len(train) - 1):
                continue
            target_sign = 1.0
            if target_transform == "log_abs":
                if len(set(signs)) != 1:
                    continue
                target_sign = signs[0]
            fit = _fit_affine(x2, y_train)
            if fit is None:
                continue
            scale, intercept = fit
            cand = {
                "family": "monomial",
                "target": target,
                "variables": list(variables),
                "exponents": list(exponents),
                "feature_expression": _expression(exponents, variables),
                "target_transform": target_transform,
                "target_sign": target_sign,
                "scale": scale,
                "intercept": intercept,
                "structural_signature": _signature(target_transform, exponents),
                "complexity": complexity + (0 if target_transform == "identity" else 2),
            }
            pred_all = _candidate_predictions(cand, data, target)
            pred_valid = _candidate_predictions(cand, valid, target)
            if pred_all is None or pred_valid is None:
                continue
            actual_all = [row[target] for row in data]
            actual_valid = [row[target] for row in valid]
            all_err = _nrmse(actual_all, pred_all)
            val_err = _nrmse(actual_valid, pred_valid) if len(valid) >= 2 else all_err
            score = val_err + 0.25 * all_err + 1e-5 * cand["complexity"]
            cand["nrmse"] = all_err
            cand["validation_nrmse"] = val_err
            cand["selection_score"] = score
            candidates.append(cand)

    log_power_fit = _fit_log_power(train, target, variables)
    if log_power_fit is not None:
        scale, exponents = log_power_fit
        cand = {
            "family": "log_power",
            "target": target,
            "variables": list(variables),
            "exponents": list(exponents),
            "scale": scale,
            "intercept": 0.0,
            "structural_signature": f"log_power|{len(variables)}",
            "complexity": len(variables) + 2,
        }
        pred_all = _candidate_predictions(cand, data, target)
        pred_valid = _candidate_predictions(cand, valid, target)
        if pred_all is not None and pred_valid is not None:
            actual_all = [row[target] for row in data]
            actual_valid = [row[target] for row in valid]
            all_err = _nrmse(actual_all, pred_all)
            val_err = _nrmse(actual_valid, pred_valid) if len(valid) >= 2 else all_err
            cand["nrmse"] = all_err
            cand["validation_nrmse"] = val_err
            cand["selection_score"] = val_err + 0.25 * all_err + 1e-5 * cand["complexity"]
            candidates.append(cand)

    linear_fit = _fit_linear_basis(train, target, variables)
    if linear_fit is not None:
        intercept, coefficients = linear_fit
        cand = {
            "family": "linear",
            "target": target,
            "variables": list(variables),
            "coefficients": list(coefficients),
            "intercept": intercept,
            "structural_signature": f"identity|linear|{len(variables)}",
            "complexity": len(variables) + 1,
        }
        pred_all = _candidate_predictions(cand, data, target)
        pred_valid = _candidate_predictions(cand, valid, target)
        if pred_all is not None and pred_valid is not None:
            actual_all = [row[target] for row in data]
            actual_valid = [row[target] for row in valid]
            all_err = _nrmse(actual_all, pred_all)
            val_err = _nrmse(actual_valid, pred_valid) if len(valid) >= 2 else all_err
            cand["nrmse"] = all_err
            cand["validation_nrmse"] = val_err
            cand["selection_score"] = val_err + 0.25 * all_err + 1e-5 * cand["complexity"]
            candidates.append(cand)

    candidates.sort(
        key=lambda c: (
            float(c["selection_score"]),
            float(c["nrmse"]),
            int(c["complexity"]),
            str(c["structural_signature"]),
            str(c.get("feature_expression", "linear")),
        )
    )
    kept = []
    seen = set()
    for cand in candidates:
        if cand.get("family") == "linear":
            params = tuple(round(float(x), 10) for x in cand["coefficients"])
        elif cand.get("family") == "log_power":
            params = tuple(round(float(x), 8) for x in cand["exponents"]) + (round(float(cand["scale"]), 10),)
        else:
            params = (round(float(cand["scale"]), 10),)
        key = (
            cand["structural_signature"],
            params,
            round(float(cand["intercept"]), 10),
        )
        if key in seen:
            continue
        seen.add(key)
        kept.append(cand)
        if len(kept) >= top_k:
            break

    status = "CANDIDATES_FOUND" if kept else "GRAMMAR_EXHAUSTED__EXPAND_MECHANISM_LANGUAGE"
    return {
        "schema": SCHEMA,
        "status": status,
        "target": target,
        "input_variables": list(variables),
        "row_count": len(data),
        "grammar_candidates_considered": grammar_count,
        "candidates": kept,
        "learned_parameter_bytes": 0,
        "external_learned_capability_calls": 0,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def predict(candidate: Mapping[str, Any], point: Mapping[str, Any]) -> float:
    variables = [str(x) for x in candidate.get("variables", [])]
    if any(name not in point for name in variables):
        raise MechanismSynthesisError("PREDICTION_POINT_MISSING_VARIABLE")
    row = {name: _finite_number(point[name], name) for name in variables}
    if candidate.get("family") == "linear":
        coeffs = [float(x) for x in candidate["coefficients"]]
        y = float(candidate["intercept"]) + sum(c * row[v] for c, v in zip(coeffs, variables))
        if not math.isfinite(y):
            raise MechanismSynthesisError("PREDICTION_NONFINITE")
        return y
    if candidate.get("family") == "log_power":
        y = float(candidate["scale"])
        for exponent, variable in zip(candidate["exponents"], variables):
            term = _pow(row[variable], float(exponent))
            if term is None:
                raise MechanismSynthesisError("PREDICTION_OUTSIDE_CANDIDATE_DOMAIN")
            y *= term
        if not math.isfinite(y):
            raise MechanismSynthesisError("PREDICTION_NONFINITE")
        return y
    f = _monomial_value(row, variables, candidate["exponents"])
    if f is None:
        raise MechanismSynthesisError("PREDICTION_OUTSIDE_CANDIDATE_DOMAIN")
    transformed = float(candidate["intercept"]) + float(candidate["scale"]) * f
    y = _target_inverse(str(candidate["target_transform"]), transformed, sign=float(candidate.get("target_sign", 1.0)))
    if y is None:
        raise MechanismSynthesisError("PREDICTION_NONFINITE")
    return y


def structural_match(a: Mapping[str, Any], b: Mapping[str, Any], *, exponent_tolerance: float = 0.05) -> dict[str, Any]:
    sa = str(a.get("structural_signature") or "")
    sb = str(b.get("structural_signature") or "")
    match = bool(sa) and sa == sb
    exponent_distance = None
    if a.get("family") == "log_power" and b.get("family") == "log_power":
        ea = sorted(float(x) for x in a.get("exponents", []))
        eb = sorted(float(x) for x in b.get("exponents", []))
        if len(ea) == len(eb) and ea:
            exponent_distance = max(abs(x-y) for x,y in zip(ea,eb))
            match = exponent_distance <= float(exponent_tolerance)
        else:
            match = False
    return {
        "match": match,
        "source_signature": sa,
        "target_signature": sb,
        "surface_variable_names_ignored": True,
        "max_sorted_exponent_distance": exponent_distance,
    }


def design_initial_probes(bounds: Mapping[str, Sequence[Any]], *, budget: int | None = None) -> dict[str, Any]:
    """Deterministic 2d+1 bounded experiment design.

    d=2 uses four corners plus a geometric/arithmetic center.
    d>2 uses center plus low/high axis probes around the center.
    """
    if not isinstance(bounds, Mapping) or not bounds:
        raise MechanismSynthesisError("BOUNDS_REQUIRED")
    normalized = {}
    for raw_name, raw_pair in bounds.items():
        name = str(raw_name).strip()
        if not name or not isinstance(raw_pair, Sequence) or isinstance(raw_pair, (str, bytes)) or len(raw_pair) != 2:
            raise MechanismSynthesisError("BOUND_INVALID")
        lo = _finite_number(raw_pair[0], name+"_lo")
        hi = _finite_number(raw_pair[1], name+"_hi")
        if not lo < hi:
            raise MechanismSynthesisError("BOUND_ORDER_INVALID:"+name)
        normalized[name] = (lo,hi)
    names = sorted(normalized)
    d = len(names)
    default_budget = 2*d + 1
    if budget is None:
        budget = default_budget
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 1:
        raise MechanismSynthesisError("BUDGET_INVALID")
    budget = min(budget, default_budget)

    center = {}
    for name,(lo,hi) in normalized.items():
        center[name] = math.sqrt(lo*hi) if lo > 0 and hi > 0 else (lo+hi)/2.0

    points = []
    if d == 1:
        name = names[0]
        lo,hi = normalized[name]
        points = [{name:lo},{name:hi},{name:center[name]}]
    elif d == 2:
        a,b = names
        alo,ahi=normalized[a]; blo,bhi=normalized[b]
        points=[
            {a:alo,b:blo},
            {a:ahi,b:blo},
            {a:alo,b:bhi},
            {a:ahi,b:bhi},
            dict(center),
        ]
    else:
        points=[dict(center)]
        for name in names:
            lo,hi=normalized[name]
            p1=dict(center); p1[name]=lo
            p2=dict(center); p2[name]=hi
            points.extend([p1,p2])
    return {
        "status":"PROBE_DESIGN_READY",
        "dimension":d,
        "budget":budget,
        "default_budget_2d_plus_1":default_budget,
        "points":points[:budget],
        "learned_parameter_bytes":0,
        "external_learned_capability_calls":0,
    }

def _probe_values(observed: Sequence[float]) -> list[float]:
    lo, hi = min(observed), max(observed)
    mid = (lo + hi) / 2.0
    values = {lo, mid, hi}
    if abs(lo) > _EPS and abs(hi) > _EPS and lo * hi > 0:
        values.add(math.copysign(math.sqrt(abs(lo * hi)), lo))
    span = hi - lo
    if span > _EPS:
        values.add(lo - 0.25 * span)
        values.add(hi + 0.25 * span)
    return sorted(x for x in values if math.isfinite(x))


def propose_discriminator(
    candidates: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
    *,
    max_points: int = 4096,
) -> dict[str, Any]:
    if len(candidates) < 2:
        return {"status": "NO_DISCRIMINATOR_NEEDED", "point": None, "disagreement": 0.0}
    variables = tuple(str(x) for x in candidates[0].get("variables", []))
    if not variables or any(tuple(str(x) for x in c.get("variables", [])) != variables for c in candidates):
        raise MechanismSynthesisError("CANDIDATE_VARIABLE_SCHEMA_MISMATCH")
    observed = {name: [] for name in variables}
    for raw in rows:
        for name in variables:
            observed[name].append(_finite_number(raw[name], name))
    axes = [_probe_values(observed[name]) for name in variables]
    best = None
    count = 0
    for vals in itertools.product(*axes):
        count += 1
        if count > max_points:
            break
        point = dict(zip(variables, vals))
        preds = []
        for cand in candidates:
            try:
                preds.append(predict(cand, point))
            except MechanismSynthesisError:
                pass
        if len(preds) < 2:
            continue
        center = sum(preds) / len(preds)
        spread = math.sqrt(sum((p - center) ** 2 for p in preds) / len(preds))
        scale = max(abs(center), max(abs(p) for p in preds), 1.0)
        disagreement = spread / scale
        key = (disagreement, tuple(vals))
        if best is None or key > best[0]:
            best = (key, point, preds)
    if best is None or best[0][0] <= 1e-12:
        return {"status": "NO_USEFUL_DISCRIMINATOR_IN_BOUNDED_GRID", "point": None, "disagreement": 0.0}
    return {
        "status": "DISCRIMINATOR_FOUND",
        "point": best[1],
        "disagreement": best[0][0],
        "candidate_predictions": best[2],
        "points_considered": min(count, max_points),
    }


def judge(
    discovery: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    *,
    fit_threshold: float = 0.03,
    ambiguity_factor: float = 1.5,
) -> dict[str, Any]:
    candidates = list(discovery.get("candidates") or [])
    if not candidates:
        return {
            "status": "EXPAND_MECHANISM_LANGUAGE",
            "candidate": None,
            "next_probe": None,
            "reason": "NO_DECLARED_GRAMMAR_CANDIDATE_EXPLAINS_EVIDENCE",
        }
    good = [c for c in candidates if float(c["nrmse"]) <= fit_threshold]
    if not good:
        return {
            "status": "EXPAND_MECHANISM_LANGUAGE",
            "candidate": None,
            "next_probe": None,
            "reason": "BEST_CANDIDATE_ABOVE_FIT_THRESHOLD",
        }
    best = good[0]
    alternatives = [
        c for c in good[1:]
        if str(c["structural_signature"]) != str(best["structural_signature"])
        and float(c["selection_score"]) <= max(float(best["selection_score"]) * ambiguity_factor, float(best["selection_score"]) + 1e-4)
    ]
    if alternatives:
        probe = propose_discriminator([best] + alternatives[:7], rows)
        return {
            "status": "REQUEST_DISCRIMINATOR",
            "candidate": best,
            "alternatives": alternatives,
            "next_probe": probe,
            "reason": "MULTIPLE_STRUCTURALLY_DISTINCT_LOW_ERROR_CANDIDATES",
        }
    return {
        "status": "IDENTIFIED_CANDIDATE_UNVERIFIED",
        "candidate": best,
        "alternatives": [],
        "next_probe": None,
        "reason": "ONE_STRUCTURAL_CLASS_DOMINATES_WITHIN_FROZEN_GRAMMAR",
    }
