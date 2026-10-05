"""V2 separable 2-D discovery for sparse MysteryMechanism-style tasks.

V1 established the representational envelope but public falsification showed
that choosing the minimum leave-one-out error across roughly 1e5 transform
pairs is selection-biased with only seven observations.

V2 preserves the same bilinear hypothesis envelope while:
1. quotienting each univariate transform library by affine equivalence on the
   observed rows, because f and a+b*f (b != 0) generate the same bilinear
   function class after coefficient reparameterization; and
2. selecting by exact delete-two NRMSE, then LOO, all-row NRMSE, complexity,
   and deterministic descriptor order.

The full transform cross-product is still searched exactly. All-row ridge
NRMSE is used only as a branch-and-bound lower bound; no candidate is pruned
unless it provably cannot beat the incumbent delete-two score.

This is a public/synthetic development candidate only. It grants zero private
benchmark, family, capability, ownership, or terminal credit.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from canonical.runtime import mysterymechanism_separable_transform_v1 as v1
from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v1 as sparse

SCHEMA = "PROJECT_BRAIN_MYSTERYMECHANISM_SEPARABLE_TRANSFORM_V2"
_EPS = 1e-12


class SeparableTransformV2Error(ValueError):
    pass


def _affine_behavior_key(values: Sequence[float]) -> tuple[float, ...] | None:
    """Canonicalize a sampled transform modulo nonzero affine reparameterization."""
    if not values:
        return None
    vals = [float(x) for x in values]
    if not all(math.isfinite(x) for x in vals):
        return None
    mean = sum(vals) / len(vals)
    centered = [x - mean for x in vals]
    rms = math.sqrt(sum(x * x for x in centered) / len(centered))
    scale = max(1.0, max(abs(x) for x in vals))
    if rms <= 1e-12 * scale:
        # Constant univariate features add no function class beyond the intercept.
        return None
    normalized = [x / rms for x in centered]
    for x in normalized:
        if abs(x) > 1e-10:
            if x < 0:
                normalized = [-z for z in normalized]
            break
    return tuple(round(x, 10) for x in normalized)


def _descriptor_records(
    variable: str,
    values: Sequence[float],
    bound: tuple[float, float],
) -> list[dict[str, Any]]:
    lo, hi = bound
    span = hi - lo
    descs: list[dict[str, Any]] = [{"kind": "identity", "variable": variable}]
    for p in v1._RATIONAL:
        for kind in ("power", "inv1p", "satp"):
            descs.append({"kind": kind, "variable": variable, "power": p})

    anchors = {-2.0, -1.0, 0.0, 1.0, 2.0, lo - span, hi + span}
    for anchor in sorted(anchors):
        for p in v1._BOUNDARY_P:
            descs.append({
                "kind": "boundary_distance",
                "variable": variable,
                "power": p,
                "anchor": anchor,
            })
            if anchor < lo or anchor > hi:
                descs.append({
                    "kind": "boundary_ratio",
                    "variable": variable,
                    "power": p,
                    "anchor": anchor,
                })

    records = []
    for d in descs:
        vec = [v1._transform(d, x) for x in values]
        if any(x is None or not math.isfinite(float(x)) for x in vec):
            continue
        records.append({
            "descriptor": d,
            "values": [float(x) for x in vec],
            "complexity": v1._descriptor_complexity(d),
        })
    records.sort(
        key=lambda r: (r["complexity"], v1._descriptor_key(r["descriptor"]))
    )
    return records


def _library(
    variable: str,
    values: Sequence[float],
    bound: tuple[float, float],
) -> list[dict[str, Any]]:
    # Lowest-complexity representative wins each exact sampled affine class.
    out: list[dict[str, Any]] = []
    seen: set[tuple[float, ...]] = set()
    for rec in _descriptor_records(variable, values, bound):
        key = _affine_behavior_key(rec["values"])
        if key is None or key in seen:
            continue
        seen.add(key)
        out.append({
            "descriptor": rec["descriptor"],
            "values": rec["values"],
        })
    out.sort(key=lambda r: v1._descriptor_key(r["descriptor"]))
    return out


def _delete_two_nrmse(
    a: Sequence[float],
    b: Sequence[float],
    y: Sequence[float],
) -> float:
    n = len(y)
    if n < 7 or len(a) != n or len(b) != n:
        return math.inf
    predicted: list[float] = []
    actual: list[float] = []
    for first in range(n):
        for second in range(first + 1, n):
            keep = [i for i in range(n) if i not in (first, second)]
            fit = v1._fit_bilinear(
                [a[i] for i in keep],
                [b[i] for i in keep],
                [y[i] for i in keep],
            )
            if fit is None:
                return math.inf
            coeff, _ = fit
            for hold in (first, second):
                value = (
                    coeff[0]
                    + coeff[1] * a[hold]
                    + coeff[2] * b[hold]
                    + coeff[3] * a[hold] * b[hold]
                )
                if not math.isfinite(value):
                    return math.inf
                predicted.append(value)
                actual.append(float(y[hold]))
    return sparse._nrmse(actual, predicted)


def discover(
    rows: Sequence[Mapping[str, Any]],
    *,
    bounds: Mapping[str, Sequence[Any]],
    target: str = "out",
) -> dict[str, Any]:
    b = sparse._normalize_bounds(bounds)
    if len(b) != 2:
        raise SeparableTransformV2Error("EXACTLY_TWO_INPUTS_REQUIRED")
    target, names, data = sparse._normalize_rows(rows, target, list(b))
    if len(data) < 7:
        raise SeparableTransformV2Error("AT_LEAST_SEVEN_ROWS_REQUIRED")

    y = [float(row[target]) for row in data]
    n1, n2 = names
    vals1 = [float(row[n1]) for row in data]
    vals2 = [float(row[n2]) for row in data]
    l1 = _library(n1, vals1, b[n1])
    l2 = _library(n2, vals2, b[n2])

    ordered: list[tuple[Any, ...]] = []
    considered = 0
    for left in l1:
        for right in l2:
            considered += 1
            fit = v1._fit_bilinear(left["values"], right["values"], y)
            if fit is None:
                continue
            coeff, pred = fit
            all_error = sparse._nrmse(y, pred)
            if not math.isfinite(all_error):
                continue
            complexity = (
                4
                + v1._descriptor_complexity(left["descriptor"])
                + v1._descriptor_complexity(right["descriptor"])
            )
            ordered.append((
                float(all_error),
                int(complexity),
                v1._descriptor_key(left["descriptor"]),
                v1._descriptor_key(right["descriptor"]),
                left,
                right,
                [float(x) for x in coeff],
            ))
    ordered.sort(key=lambda item: item[:4])

    best = None
    delete_two_pairs_evaluated = 0
    loo_pairs_evaluated = 0

    # Exact branch-and-bound. Across all delete-two folds every observation is
    # held out equally often, so the NRMSE denominator is the same as all-row
    # NRMSE. For a linear ridge smoother the multi-delete residual vector is
    # (I-H_SS)^-1 times the in-sample residual vector on S. H_SS is PSD with
    # eigenvalues in [0,1), hence each fold's residual norm cannot decrease.
    for all_error, complexity, lkey, rkey, left, right, coeff in ordered:
        if best is not None and all_error > best[0][0] + 1e-12:
            break
        delete_two = _delete_two_nrmse(left["values"], right["values"], y)
        delete_two_pairs_evaluated += 1
        if not math.isfinite(delete_two):
            continue
        loo = v1._loo_nrmse(left["values"], right["values"], y)
        loo_pairs_evaluated += 1
        if not math.isfinite(loo):
            continue
        key = (
            float(delete_two),
            float(loo),
            float(all_error),
            int(complexity),
            lkey,
            rkey,
        )
        if best is None or key < best[0]:
            best = (key, {
                "left": left["descriptor"],
                "right": right["descriptor"],
                "coefficients": coeff,
                "delete_two_nrmse": float(delete_two),
                "loo_nrmse": float(loo),
                "all_row_nrmse": float(all_error),
                "complexity": int(complexity),
            })

    common = {
        "schema": SCHEMA,
        "input_variables": list(names),
        "row_count": len(data),
        "left_library_size": len(l1),
        "right_library_size": len(l2),
        "transform_pairs_considered": considered,
        "delete_two_pairs_evaluated": delete_two_pairs_evaluated,
        "loo_pairs_evaluated": loo_pairs_evaluated,
        "affine_equivalence_quotient": True,
        "selection_rule": (
            "DELETE_TWO_NRMSE_THEN_LOO_NRMSE_THEN_ALL_ROW_NRMSE_"
            "THEN_COMPLEXITY_THEN_DESCRIPTOR_KEY"
        ),
        "selection_exact_branch_and_bound": True,
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
    if best is None:
        return {
            **common,
            "status": "SEPARABLE_V2_GRAMMAR_EXHAUSTED",
            "candidate": None,
            "expression": None,
        }

    candidate = best[1]
    return {
        **common,
        "status": "SEPARABLE_V2_CANDIDATE_FOUND__PUBLIC_OR_SYNTHETIC_ONLY",
        "candidate": candidate,
        "expression": v1.serialize(candidate),
    }


def predict(candidate: Mapping[str, Any], point: Mapping[str, Any]) -> float:
    return v1.predict(candidate, point)


def serialize(candidate: Mapping[str, Any]) -> str:
    return v1.serialize(candidate)
