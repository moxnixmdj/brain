"""Generic separable 2D transform discovery for sparse active-science tasks.

The learner stores no task formulas. It searches generic univariate transform
families and fits the bilinear interaction surface

    y = b0 + b1*f(x1) + b2*g(x2) + b3*f(x1)*g(x2)

Selection is exact leave-one-out NRMSE, then all-row NRMSE, then complexity.
The search remains practical because in-sample ridge error is a lower bound on
leave-one-out error; candidates are ordered by that lower bound and the scan
stops only when no unseen pair can beat the current best LOO score.

This is a candidate generator only. Public-development success is not a private
benchmark score and carries zero acceptance/family/ownership credit.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v1 as sparse

SCHEMA = "PROJECT_BRAIN_MYSTERYMECHANISM_SEPARABLE_TRANSFORM_V1"
_RATIONAL = (0.25, 1 / 3, 0.5, 0.625, 2 / 3, 0.8, 1.0, 1.5, 2.0)
_BOUNDARY_P = tuple(round(0.5 + 0.1 * i, 10) for i in range(26))
_EPS = 1e-12


class SeparableTransformError(ValueError):
    pass


def _descriptor_key(d: Mapping[str, Any]) -> tuple:
    return (
        str(d["kind"]),
        str(d.get("variable", "")),
        round(float(d.get("power", 0)), 10),
        round(float(d.get("anchor", 0)), 10),
    )


def _descriptor_complexity(d: Mapping[str, Any]) -> int:
    return {
        "identity": 1,
        "power": 2,
        "inv1p": 3,
        "satp": 4,
        "boundary_distance": 4,
        "boundary_ratio": 5,
    }.get(str(d["kind"]), 99)


def _transform(d: Mapping[str, Any], x: float) -> float | None:
    kind = str(d["kind"])
    p = float(d.get("power", 1.0))
    ax = abs(float(x))
    try:
        if kind == "identity":
            y = float(x)
        elif kind == "power":
            y = ax ** p
        elif kind == "inv1p":
            y = 1.0 / (1.0 + ax ** p)
        elif kind == "satp":
            u = ax ** p
            y = u / (1.0 + u)
        elif kind == "boundary_distance":
            y = abs(float(d["anchor"]) - float(x)) ** p
        elif kind == "boundary_ratio":
            distance = abs(float(d["anchor"]) - float(x))
            if distance <= _EPS:
                return None
            y = float(x) / (distance ** p)
        else:
            return None
    except (OverflowError, ValueError, ZeroDivisionError):
        return None
    return y if math.isfinite(y) else None


def _expr(d: Mapping[str, Any]) -> str:
    v = str(d["variable"])
    kind = str(d["kind"])
    p = repr(float(d.get("power", 1.0)))
    if kind == "identity":
        return v
    if kind == "power":
        return f"(abs({v})**({p}))"
    if kind == "inv1p":
        return f"(1/(1+abs({v})**({p})))"
    if kind == "satp":
        return f"((abs({v})**({p}))/(1+abs({v})**({p})))"
    anchor = repr(float(d["anchor"]))
    distance = f"abs(({anchor})-{v})"
    if kind == "boundary_distance":
        return f"(({distance})**({p}))"
    if kind == "boundary_ratio":
        return f"({v}/(({distance})**({p})))"
    raise SeparableTransformError("DESCRIPTOR_INVALID")


def _library(
    variable: str,
    values: Sequence[float],
    bound: tuple[float, float],
) -> list[dict[str, Any]]:
    lo, hi = bound
    span = hi - lo
    descs = [{"kind": "identity", "variable": variable}]
    for p in _RATIONAL:
        for kind in ("power", "inv1p", "satp"):
            descs.append({"kind": kind, "variable": variable, "power": p})

    anchors = {-2.0, -1.0, 0.0, 1.0, 2.0, lo - span, hi + span}
    for anchor in sorted(anchors):
        for p in _BOUNDARY_P:
            # Direct boundary distance is safe even when the anchor lies inside
            # the interval and is required by the frozen capability grammar.
            descs.append({
                "kind": "boundary_distance",
                "variable": variable,
                "power": p,
                "anchor": anchor,
            })
            # Ratio forms may be singular, so their anchor must be provably
            # outside every admissible point.
            if anchor < lo or anchor > hi:
                descs.append({
                    "kind": "boundary_ratio",
                    "variable": variable,
                    "power": p,
                    "anchor": anchor,
                })

    out = []
    seen = set()
    for d in descs:
        vec = [_transform(d, x) for x in values]
        if any(v is None or not math.isfinite(v) for v in vec):
            continue
        scale = max(1.0, max(abs(float(v)) for v in vec))
        key = tuple(round(float(v) / scale, 10) for v in vec)
        if key in seen:
            continue
        seen.add(key)
        out.append({"descriptor": d, "values": [float(v) for v in vec]})
    out.sort(key=lambda r: _descriptor_key(r["descriptor"]))
    return out


def _fit_bilinear(a: Sequence[float], b: Sequence[float], y: Sequence[float]):
    interaction = [x * z for x, z in zip(a, b)]
    coeff = sparse._fit([a, b, interaction], y)
    if coeff is None:
        return None
    pred = [
        coeff[0] + coeff[1] * a[i] + coeff[2] * b[i] + coeff[3] * interaction[i]
        for i in range(len(y))
    ]
    return coeff, pred


def _loo_nrmse(a: Sequence[float], b: Sequence[float], y: Sequence[float]) -> float:
    pred = []
    n = len(y)
    for hold in range(n):
        keep = [i for i in range(n) if i != hold]
        fit = _fit_bilinear(
            [a[i] for i in keep],
            [b[i] for i in keep],
            [y[i] for i in keep],
        )
        if fit is None:
            return math.inf
        coeff, _ = fit
        value = coeff[0] + coeff[1] * a[hold] + coeff[2] * b[hold] + coeff[3] * a[hold] * b[hold]
        if not math.isfinite(value):
            return math.inf
        pred.append(value)
    return sparse._nrmse(y, pred)


def discover(
    rows: Sequence[Mapping[str, Any]],
    *,
    bounds: Mapping[str, Sequence[Any]],
    target: str = "out",
) -> dict[str, Any]:
    b = sparse._normalize_bounds(bounds)
    if len(b) != 2:
        raise SeparableTransformError("EXACTLY_TWO_INPUTS_REQUIRED")
    target, names, data = sparse._normalize_rows(rows, target, list(b))
    if len(data) < 7:
        raise SeparableTransformError("AT_LEAST_SEVEN_ROWS_REQUIRED")

    y = [float(r[target]) for r in data]
    n1, n2 = names
    vals1 = [float(r[n1]) for r in data]
    vals2 = [float(r[n2]) for r in data]
    l1 = _library(n1, vals1, b[n1])
    l2 = _library(n2, vals2, b[n2])

    # Pass 1: compute the all-row ridge fit for the complete grammar. For a
    # linear ridge smoother, PRESS residual_i = residual_i/(1-h_ii) with
    # 0 <= h_ii < 1, so all-row NRMSE is a valid lower bound on LOO NRMSE.
    lower_bound_order = []
    considered = 0
    for left in l1:
        for right in l2:
            considered += 1
            fit = _fit_bilinear(left["values"], right["values"], y)
            if fit is None:
                continue
            coeff, pred = fit
            all_error = sparse._nrmse(y, pred)
            if not math.isfinite(all_error):
                continue
            complexity = 4 + _descriptor_complexity(left["descriptor"]) + _descriptor_complexity(right["descriptor"])
            lower_bound_order.append((
                float(all_error),
                int(complexity),
                _descriptor_key(left["descriptor"]),
                _descriptor_key(right["descriptor"]),
                left,
                right,
                [float(x) for x in coeff],
            ))
    lower_bound_order.sort(key=lambda item: item[:4])

    # Pass 2: exact branch-and-bound over LOO. Once the next all-row lower
    # bound exceeds the best LOO score, every remaining pair is provably worse.
    best = None
    loo_pairs_evaluated = 0
    for all_error, complexity, lkey, rkey, left, right, coeff in lower_bound_order:
        if best is not None and all_error > best[0][0] + 1e-12:
            break
        loo = _loo_nrmse(left["values"], right["values"], y)
        loo_pairs_evaluated += 1
        if not math.isfinite(loo):
            continue
        key = (float(loo), float(all_error), complexity, lkey, rkey)
        if best is None or key < best[0]:
            best = (key, {
                "left": left["descriptor"],
                "right": right["descriptor"],
                "coefficients": coeff,
                "loo_nrmse": float(loo),
                "all_row_nrmse": float(all_error),
                "complexity": complexity,
            })

    if best is None:
        return {
            "schema": SCHEMA,
            "status": "SEPARABLE_GRAMMAR_EXHAUSTED",
            "candidate": None,
            "transform_pairs_considered": considered,
            "loo_pairs_evaluated": loo_pairs_evaluated,
            "selection_rule": "LOO_NRMSE_THEN_ALL_ROW_NRMSE_THEN_COMPLEXITY",
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "persistent_learned_bytes": 0,
            "external_learned_capability_calls": 0,
        }

    candidate = best[1]
    expression = serialize(candidate)
    return {
        "schema": SCHEMA,
        "status": "SEPARABLE_CANDIDATE_FOUND__PUBLIC_OR_SYNTHETIC_ONLY",
        "input_variables": list(names),
        "row_count": len(data),
        "left_library_size": len(l1),
        "right_library_size": len(l2),
        "transform_pairs_considered": considered,
        "loo_pairs_evaluated": loo_pairs_evaluated,
        "selection_rule": "LOO_NRMSE_THEN_ALL_ROW_NRMSE_THEN_COMPLEXITY",
        "selection_exact_branch_and_bound": True,
        "candidate": candidate,
        "expression": expression,
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
        "dynamic_code_execution": False,
        "random_search": False,
        "private_score_claimed": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def predict(candidate: Mapping[str, Any], point: Mapping[str, Any]) -> float:
    left, right = candidate["left"], candidate["right"]
    x = sparse._finite(point[str(left["variable"])], str(left["variable"]))
    z = sparse._finite(point[str(right["variable"])], str(right["variable"]))
    a = _transform(left, x)
    b = _transform(right, z)
    if a is None or b is None:
        raise SeparableTransformError("POINT_OUTSIDE_CANDIDATE_DOMAIN")
    c = [float(v) for v in candidate["coefficients"]]
    y = c[0] + c[1] * a + c[2] * b + c[3] * a * b
    if not math.isfinite(y):
        raise SeparableTransformError("PREDICTION_NONFINITE")
    return y


def serialize(candidate: Mapping[str, Any]) -> str:
    c = [float(v) for v in candidate["coefficients"]]
    a = _expr(candidate["left"])
    b = _expr(candidate["right"])
    return (
        repr(c[0])
        + "+(" + repr(c[1]) + ")*(" + a + ")"
        + "+(" + repr(c[2]) + ")*(" + b + ")"
        + "+(" + repr(c[3]) + ")*(" + a + ")*(" + b + ")"
    )
