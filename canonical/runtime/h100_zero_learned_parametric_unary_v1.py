"""Deterministic zero-learned parametric unary basis synthesis for H100.

Adds three general single-variable primitive families that are absent from the
current bounded expression-tree grammar:
- affine trend + sinusoid with fitted frequency and phase,
- exponential in absolute input with fitted scale/rate,
- affine threshold step with fitted boundary.

All parameters are inferred from task observations at runtime. There is no
persistent learned state, no random search, no model/provider call, and no
dynamic code execution. This is a candidate generator only.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_H100_ZERO_LEARNED_PARAMETRIC_UNARY_V1"
_EPS = 1e-12


class ParametricUnaryError(ValueError):
    pass


def _finite(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ParametricUnaryError(field.upper() + "_INVALID")
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise ParametricUnaryError(field.upper() + "_INVALID") from exc
    if not math.isfinite(out):
        raise ParametricUnaryError(field.upper() + "_NONFINITE")
    return out


def _normalize(rows: Sequence[Mapping[str, Any]], target: str, input_name: str | None):
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or len(rows) < 8:
        raise ParametricUnaryError("AT_LEAST_EIGHT_ROWS_REQUIRED")
    target = str(target or "").strip()
    if not target:
        raise ParametricUnaryError("TARGET_REQUIRED")
    first = rows[0]
    if not isinstance(first, Mapping) or target not in first:
        raise ParametricUnaryError("TARGET_MISSING")
    if input_name is None:
        names = [str(k) for k in first if str(k) != target]
        if len(names) != 1:
            raise ParametricUnaryError("EXACTLY_ONE_INPUT_REQUIRED")
        input_name = names[0]
    input_name = str(input_name).strip()
    if not input_name or input_name == target:
        raise ParametricUnaryError("INPUT_INVALID")
    out = []
    for i, raw in enumerate(rows):
        if not isinstance(raw, Mapping) or input_name not in raw or target not in raw:
            raise ParametricUnaryError(f"ROW_SCHEMA_MISMATCH:{i}")
        out.append({input_name: _finite(raw[input_name], input_name), target: _finite(raw[target], target)})
    return target, input_name, out


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    n = len(vector)
    if n == 0 or len(matrix) != n or any(len(row) != n for row in matrix):
        return None
    a = [list(map(float, row)) + [float(vector[i])] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) <= 1e-11:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        div = a[col][col]
        a[col] = [v / div for v in a[col]]
        for r in range(n):
            if r == col:
                continue
            factor = a[r][col]
            if abs(factor) <= _EPS:
                continue
            a[r] = [x - factor * y for x, y in zip(a[r], a[col])]
    result = [a[i][-1] for i in range(n)]
    return result if all(math.isfinite(x) for x in result) else None


def _least_squares(columns: Sequence[Sequence[float]], y: Sequence[float]) -> list[float] | None:
    if not y or any(len(col) != len(y) for col in columns):
        return None
    p = len(columns)
    xtx = [[0.0] * p for _ in range(p)]
    xty = [0.0] * p
    for row_i, target in enumerate(y):
        vals = [float(col[row_i]) for col in columns]
        for i in range(p):
            xty[i] += vals[i] * float(target)
            for j in range(p):
                xtx[i][j] += vals[i] * vals[j]
    for i in range(p):
        xtx[i][i] += 1e-13
    return _solve(xtx, xty)


def _nrmse(actual: Sequence[float], pred: Sequence[float]) -> float:
    if len(actual) != len(pred) or len(actual) < 2:
        return math.inf
    mean = sum(actual) / len(actual)
    spread = math.sqrt(sum((v - mean) ** 2 for v in actual) / len(actual))
    scale = max(spread, max(abs(v) for v in actual) * 1e-9, _EPS)
    rmse = math.sqrt(sum((a-b) ** 2 for a,b in zip(actual, pred)) / len(actual))
    return rmse / scale


def _fit_sinusoid(xs: Sequence[float], ys: Sequence[float], omega: float):
    sin_col = [math.sin(omega*x) for x in xs]
    cos_col = [math.cos(omega*x) for x in xs]
    coeff = _least_squares([[1.0]*len(xs), list(xs), sin_col, cos_col], ys)
    if coeff is None:
        return None
    pred = [coeff[0] + coeff[1]*x + coeff[2]*math.sin(omega*x) + coeff[3]*math.cos(omega*x) for x in xs]
    return coeff, _nrmse(ys, pred)


def _sinusoid_candidate(xs: Sequence[float], ys: Sequence[float]):
    lo, hi, step = 0.05, 8.0, 0.005
    best = None
    count = int(round((hi-lo)/step)) + 1
    for i in range(count):
        omega = lo + i*step
        fit = _fit_sinusoid(xs, ys, omega)
        if fit is None:
            continue
        coeff, err = fit
        row = (err, omega, coeff)
        if best is None or row[:2] < best[:2]:
            best = row
    if best is None:
        return None

    center = best[1]
    left = max(lo, center-step)
    right = min(hi, center+step)
    phi = (1.0 + math.sqrt(5.0)) / 2.0
    c = right - (right-left)/phi
    d = left + (right-left)/phi
    fc = _fit_sinusoid(xs, ys, c)
    fd = _fit_sinusoid(xs, ys, d)
    for _ in range(90):
        ec = math.inf if fc is None else fc[1]
        ed = math.inf if fd is None else fd[1]
        if ec <= ed:
            right, d, fd = d, c, fc
            c = right - (right-left)/phi
            fc = _fit_sinusoid(xs, ys, c)
        else:
            left, c, fc = c, d, fd
            d = left + (right-left)/phi
            fd = _fit_sinusoid(xs, ys, d)
    omega = (left+right)/2.0
    fit = _fit_sinusoid(xs, ys, omega)
    if fit is None:
        return None
    coeff, err = fit
    amp = math.hypot(coeff[2], coeff[3])
    return {
        "family":"linear_trend_sinusoid",
        "omega":omega,
        "intercept":coeff[0],
        "linear":coeff[1],
        "sin_coefficient":coeff[2],
        "cos_coefficient":coeff[3],
        "amplitude":amp,
        "nrmse":err,
        "complexity":7,
    }


def _exponential_abs_candidate(xs: Sequence[float], ys: Sequence[float]):
    if any(y <= 0 for y in ys):
        return None
    logs = [math.log(y) for y in ys]
    coeff = _least_squares([[1.0]*len(xs), [abs(x) for x in xs]], logs)
    if coeff is None:
        return None
    try:
        scale = math.exp(coeff[0])
    except OverflowError:
        return None
    rate = coeff[1]
    pred = []
    try:
        for x in xs:
            pred.append(scale * math.exp(rate * abs(x)))
    except OverflowError:
        return None
    if not all(math.isfinite(v) for v in pred):
        return None
    return {
        "family":"exp_abs",
        "scale":scale,
        "rate":rate,
        "nrmse":_nrmse(ys,pred),
        "complexity":3,
    }


def _step_candidate(xs: Sequence[float], ys: Sequence[float]):
    unique = sorted(set(xs))
    if len(unique) < 2:
        return None
    candidates = []
    # Observed-value thresholds are preferred because they encode an identifiable
    # boundary convention x>=threshold without inventing an unseen midpoint.
    thresholds = [(x,0) for x in unique]
    thresholds += [((a+b)/2.0,1) for a,b in zip(unique,unique[1:])]
    for threshold, source_rank in thresholds:
        feature = [1.0 if x >= threshold else -1.0 for x in xs]
        coeff = _least_squares([[1.0]*len(xs), feature], ys)
        if coeff is None:
            continue
        pred = [coeff[0] + coeff[1]*f for f in feature]
        err = _nrmse(ys,pred)
        candidates.append((err,source_rank,abs(threshold),threshold,coeff))
    if not candidates:
        return None
    err,source_rank,_,threshold,coeff = min(candidates)
    return {
        "family":"threshold_step",
        "threshold":threshold,
        "threshold_source":"observed" if source_rank == 0 else "midpoint",
        "intercept":coeff[0],
        "amplitude":coeff[1],
        "nrmse":err,
        "complexity":4,
    }


def predict(candidate: Mapping[str, Any], point: Mapping[str, Any]) -> float:
    name = str(candidate.get("input_name") or "")
    if name not in point:
        raise ParametricUnaryError("PREDICTION_INPUT_MISSING")
    x = _finite(point[name], name)
    family = candidate.get("family")
    if family == "linear_trend_sinusoid":
        y = (
            float(candidate["intercept"])
            + float(candidate["linear"])*x
            + float(candidate["sin_coefficient"])*math.sin(float(candidate["omega"])*x)
            + float(candidate["cos_coefficient"])*math.cos(float(candidate["omega"])*x)
        )
    elif family == "exp_abs":
        try:
            y = float(candidate["scale"]) * math.exp(float(candidate["rate"])*abs(x))
        except OverflowError as exc:
            raise ParametricUnaryError("PREDICTION_OVERFLOW") from exc
    elif family == "threshold_step":
        f = 1.0 if x >= float(candidate["threshold"]) else -1.0
        y = float(candidate["intercept"]) + float(candidate["amplitude"])*f
    else:
        raise ParametricUnaryError("CANDIDATE_FAMILY_INVALID")
    if not math.isfinite(y):
        raise ParametricUnaryError("PREDICTION_NONFINITE")
    return y


def discover(rows: Sequence[Mapping[str, Any]], *, target: str, input_name: str | None = None, exact_nrmse: float = 1e-8):
    target, input_name, data = _normalize(rows, target, input_name)
    exact_nrmse = _finite(exact_nrmse, "exact_nrmse")
    if exact_nrmse <= 0 or exact_nrmse > 1e-3:
        raise ParametricUnaryError("EXACT_NRMSE_INVALID")
    xs = [row[input_name] for row in data]
    ys = [row[target] for row in data]
    raw = [
        _exponential_abs_candidate(xs,ys),
        _step_candidate(xs,ys),
        _sinusoid_candidate(xs,ys),
    ]
    candidates = []
    for c in raw:
        if c is None:
            continue
        c = dict(c)
        c["input_name"] = input_name
        candidates.append(c)
    candidates.sort(key=lambda c:(float(c["nrmse"]),int(c["complexity"]),str(c["family"])))
    exact = [c for c in candidates if float(c["nrmse"]) <= exact_nrmse]
    return {
        "schema":SCHEMA,
        "status":"EXACT_CANDIDATE_FOUND" if exact else "PARAMETRIC_FAMILIES_NOT_EXACT",
        "target":target,
        "input_name":input_name,
        "row_count":len(data),
        "exact_nrmse_threshold":exact_nrmse,
        "best_candidate": exact[0] if exact else (candidates[0] if candidates else None),
        "candidate_count":len(candidates),
        "persistent_learned_bytes":0,
        "external_frontier_model_calls":0,
        "external_learned_capability_calls":0,
        "random_search":False,
        "dynamic_code_execution":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }
