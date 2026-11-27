"""MysteryMechanism adaptive planner V4: structural finalization repair.

V4 preserves V3 experiment selection but tightens finalization.  In particular,
an unconstrained bilinear surface is never sufficient evidence for a mechanism.
The finalizer admits only:
  * a stable log-power candidate from the existing V2 route; or
  * a rank-one multiplicative two-factor structure whose fixed transforms remain
    predictive under leave-one-out refits.

Everything else fails closed.  Public-development success is not benchmark
credit and this module never accesses private tasks or credentials.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from canonical.runtime import mysterymechanism_adaptive_planner_v3 as v3
from canonical.runtime import mysterymechanism_separable_transform_v1 as sep
from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v2 as sparse

SCHEMA = "PROJECT_BRAIN_MYSTERYMECHANISM_ADAPTIVE_PLANNER_V4"
_EPS = 1e-12

next_experiment = v3.next_experiment
adaptive_probe = v3.adaptive_probe
maximin_probe = v3.maximin_probe
choose_from_predictors = v3.choose_from_predictors


def _complexity(d: Mapping[str, Any]) -> int:
    kind = str(d.get("kind") or "")
    if kind == "identity":
        return 1
    if kind == "power":
        return 2
    if kind in {"inv1p", "satp"}:
        return 3
    return 4


def _fit_product(
    left: Sequence[float],
    right: Sequence[float],
    target: Sequence[float],
    *,
    refine: bool = True,
) -> dict[str, Any] | None:
    fit = sep._fit_bilinear(left, right, target)
    if fit is None:
        return None
    coeff, _ = fit
    b0, b1, b2, b3 = [float(x) for x in coeff]
    norm = math.sqrt(sum(x * x for x in coeff))
    if norm <= _EPS or abs(b0) <= 1e-10 * norm:
        return None

    determinant_residual = abs(b0 * b3 - b1 * b2) / max(norm * norm, _EPS)
    params = [b0, b1 / b0, b2 / b0]

    def predict(p: Sequence[float]) -> list[float] | None:
        mu, a, c = [float(x) for x in p]
        try:
            out = [
                mu * (1.0 + a * float(x)) * (1.0 + c * float(z))
                for x, z in zip(left, right)
            ]
        except (OverflowError, ValueError):
            return None
        return out if all(math.isfinite(x) for x in out) else None

    def sse(p: Sequence[float]) -> float:
        pred = predict(p)
        if pred is None:
            return math.inf
        return sum((float(y) - q) ** 2 for y, q in zip(target, pred))

    # Deterministic Gauss-Newton with line search.  The unconstrained
    # bilinear fit supplies the initial factorization, then the constrained
    # three-parameter family is optimized directly rather than projected once.
    best = list(params)
    best_sse = sse(best)
    iterations = 40 if refine else 0
    for _ in range(iterations):
        mu, a, c = best
        pred = predict(best)
        if pred is None:
            return None
        jtj = [[0.0] * 3 for _ in range(3)]
        jtr = [0.0] * 3
        for x, z, y, q in zip(left, right, target, pred):
            fx, gz = float(x), float(z)
            jac = [
                (1.0 + a * fx) * (1.0 + c * gz),
                mu * fx * (1.0 + c * gz),
                mu * gz * (1.0 + a * fx),
            ]
            residual = float(y) - q
            for i in range(3):
                jtr[i] += jac[i] * residual
                for k in range(3):
                    jtj[i][k] += jac[i] * jac[k]
        ridge = max(1.0, max(abs(v) for row in jtj for v in row)) * 1e-12
        for i in range(3):
            jtj[i][i] += ridge
        delta = sparse._solve(jtj, jtr)
        if delta is None:
            break
        accepted = False
        step = 1.0
        for _ in range(12):
            trial = [best[i] + step * float(delta[i]) for i in range(3)]
            trial_sse = sse(trial)
            if trial_sse + 1e-18 < best_sse:
                best, best_sse = trial, trial_sse
                accepted = True
                break
            step *= 0.5
        if not accepted:
            break
        if max(abs(step * float(x)) for x in delta) <= 1e-10 * max(
            1.0, max(abs(x) for x in best)
        ):
            break

    mu, a, c = best
    pred = predict(best)
    if pred is None:
        return None
    return {
        "mu": mu,
        "a": a,
        "c": c,
        "predictions": pred,
        "nrmse": sparse._nrmse(target, pred),
        "determinant_residual": determinant_residual,
    }


def _fixed_structure_loo(
    rows: Sequence[Mapping[str, Any]],
    *,
    names: tuple[str, str],
    target: str,
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> float:
    gold: list[float] = []
    pred: list[float] = []
    for hold in range(len(rows)):
        train_left, train_right, train_y = [], [], []
        for i, row in enumerate(rows):
            if i == hold:
                continue
            lv = sep._transform(left, float(row[names[0]]))
            rv = sep._transform(right, float(row[names[1]]))
            if lv is None or rv is None:
                return math.inf
            train_left.append(lv)
            train_right.append(rv)
            train_y.append(float(row[target]))
        fit = _fit_product(train_left, train_right, train_y)
        if fit is None:
            return math.inf
        lv = sep._transform(left, float(rows[hold][names[0]]))
        rv = sep._transform(right, float(rows[hold][names[1]]))
        if lv is None or rv is None:
            return math.inf
        yhat = fit["mu"] * (1.0 + fit["a"] * lv) * (1.0 + fit["c"] * rv)
        if not math.isfinite(yhat):
            return math.inf
        pred.append(yhat)
        gold.append(float(rows[hold][target]))
    return sparse._nrmse(gold, pred)


def structured_product_discover(
    rows: Sequence[Mapping[str, Any]],
    *,
    bounds: Mapping[str, Sequence[Any]],
    target: str = "out",
) -> dict[str, Any]:
    b = sparse._normalize_bounds(bounds)
    if len(b) != 2:
        return {"status": "NOT_APPLICABLE__TWO_INPUTS_REQUIRED", "candidate": None}
    target, names_raw, data = sparse._normalize_rows(rows, target, list(b))
    names = (names_raw[0], names_raw[1])
    if len(data) < 7:
        return {"status": "INSUFFICIENT_EVIDENCE", "candidate": None}

    values = [[float(row[name]) for row in data] for name in names]
    libs = [
        sep._library(names[i], values[i], b[names[i]])
        for i in range(2)
    ]
    y = [float(row[target]) for row in data]
    shortlist: list[tuple[Any, ...]] = []

    # First stage is deliberately cheap: rank by constrained all-row fit and
    # rank-one residual.  LOO is then computed only for the strongest finite
    # candidates, avoiding a sevenfold full-library explosion.
    for left_rec in libs[0]:
        for right_rec in libs[1]:
            fit = _fit_product(
                left_rec["values"], right_rec["values"], y, refine=False
            )
            if fit is None or not math.isfinite(fit["nrmse"]):
                continue
            key = (
                float(fit["nrmse"]),
                float(fit["determinant_residual"]),
                _complexity(left_rec["descriptor"]) + _complexity(right_rec["descriptor"]),
                sep._descriptor_key(left_rec["descriptor"]),
                sep._descriptor_key(right_rec["descriptor"]),
            )
            shortlist.append((key, left_rec["descriptor"], right_rec["descriptor"], fit))

    if not shortlist:
        return {"status": "NO_STRUCTURED_PRODUCT_CANDIDATE", "candidate": None}
    shortlist.sort(key=lambda item: item[0])

    evaluated = []
    for key, left, right, _screen_fit in shortlist[:32]:
        left_values = [sep._transform(left, float(row[names[0]])) for row in data]
        right_values = [sep._transform(right, float(row[names[1]])) for row in data]
        if any(x is None for x in left_values) or any(x is None for x in right_values):
            continue
        fit = _fit_product(left_values, right_values, y, refine=True)
        if fit is None:
            continue
        loo = _fixed_structure_loo(
            data, names=names, target=target, left=left, right=right
        )
        if not math.isfinite(loo):
            continue
        evaluated.append((loo, key, left, right, fit))
    if not evaluated:
        return {"status": "NO_STABLE_STRUCTURED_PRODUCT_CANDIDATE", "candidate": None}

    evaluated.sort(
        key=lambda item: (
            item[0],
            item[1][0],
            item[1][1],
            item[1][2],
            item[1][3],
            item[1][4],
        )
    )
    loo, _, left, right, fit = evaluated[0]

    # Identifiability gate: near-best structures must agree off the observed
    # points.  Otherwise the evidence supports several incompatible laws and
    # selecting the numerically best interpolation would be false confidence.
    plausible = [
        item for item in evaluated
        if item[0] <= max(loo * 2.0, loo + 0.01)
        and float(item[4]["nrmse"]) <= max(float(fit["nrmse"]) * 3.0, float(fit["nrmse"]) + 0.01)
    ][:12]
    mean_y = sum(y) / len(y)
    y_scale = max(
        math.sqrt(sum((q - mean_y) ** 2 for q in y) / len(y)),
        max(abs(q) for q in y) * 1e-9,
        _EPS,
    )
    worst_disagreement = 0.0
    for _, point in v3._candidate_points(b, grid_levels=5, max_points=625):
        preds = []
        for _, _, pleft, pright, pfit in plausible:
            lv = sep._transform(pleft, float(point[names[0]]))
            rv = sep._transform(pright, float(point[names[1]]))
            if lv is None or rv is None:
                continue
            pred = pfit["mu"] * (1.0 + pfit["a"] * lv) * (1.0 + pfit["c"] * rv)
            if math.isfinite(pred):
                preds.append(pred)
        if len(preds) >= 2:
            worst_disagreement = max(
                worst_disagreement, (max(preds) - min(preds)) / y_scale
            )

    left_expr = sep._expr(left)
    right_expr = sep._expr(right)
    expression = (
        f"({fit['mu']!r})*(1+({fit['a']!r})*({left_expr}))"
        f"*(1+({fit['c']!r})*({right_expr}))"
    )
    candidate = {
        "family": "structured_multiplicative_two_factor",
        "variables": list(names),
        "left": dict(left),
        "right": dict(right),
        "mu": fit["mu"],
        "a": fit["a"],
        "c": fit["c"],
        "nrmse": fit["nrmse"],
        "fixed_structure_loo_nrmse": loo,
        "rank_one_determinant_residual": fit["determinant_residual"],
        "plausible_structure_count": len(plausible),
        "max_plausible_prediction_disagreement_nrmse": worst_disagreement,
        "expression": expression,
    }
    return {
        "schema": SCHEMA,
        "status": "STRUCTURED_PRODUCT_CANDIDATE",
        "candidate": candidate,
        "candidates_screened": len(shortlist),
        "loo_candidates_evaluated": len(evaluated),
        "private_task_data_used": False,
        "acceptance_credit_delta": 0,
    }


def _zero_credit(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "private_score_claimed": False,
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        **extra,
    }


def finalize(
    rows: Sequence[Mapping[str, Any]],
    *,
    bounds: Mapping[str, Sequence[Any]],
    target: str = "out",
    fit_threshold: float = 0.05,
) -> dict[str, Any]:
    old = v3.finalize(rows, bounds=bounds, target=target, fit_threshold=fit_threshold)

    # Preserve the already-strong continuous power-law route, but do not
    # inherit V3's generic "candidate ready" status for arbitrary sparse or
    # unconstrained separable fits.
    old_candidate = old.get("candidate")
    if (
        old.get("status") == "CANDIDATE_READY__UNVERIFIED_ON_PRIVATE_STRUCTURAL_PROBES"
        and old.get("route") == "V2_BASE_OR_SPARSE"
        and isinstance(old_candidate, Mapping)
        and old_candidate.get("family") == "log_power"
        and float(old.get("conservative_nrmse", math.inf)) <= min(float(fit_threshold), 0.01)
    ):
        return _zero_credit(
            "CANDIDATE_READY__STRUCTURALLY_CONSTRAINED__PRIVATE_UNVERIFIED",
            route="LOG_POWER",
            candidate=old_candidate,
            expression=old.get("expression"),
            conservative_nrmse=float(old["conservative_nrmse"]),
            fit_threshold=float(fit_threshold),
            old_v3_status=old.get("status"),
        )

    product = structured_product_discover(rows, bounds=bounds, target=target)
    cand = product.get("candidate")
    if isinstance(cand, Mapping):
        fit_error = float(cand.get("nrmse", math.inf))
        loo_error = float(cand.get("fixed_structure_loo_nrmse", math.inf))
        det_error = float(cand.get("rank_one_determinant_residual", math.inf))
        disagreement = float(
            cand.get("max_plausible_prediction_disagreement_nrmse", math.inf)
        )
        if (
            fit_error <= 0.02
            and loo_error <= 0.02
            and det_error <= 0.05
            and disagreement <= 0.01
        ):
            return _zero_credit(
                "CANDIDATE_READY__STRUCTURALLY_CONSTRAINED__PRIVATE_UNVERIFIED",
                route="STRUCTURED_MULTIPLICATIVE_TWO_FACTOR",
                candidate=dict(cand),
                expression=cand.get("expression"),
                conservative_nrmse=max(fit_error, loo_error),
                fit_threshold=float(fit_threshold),
                structural_checks={
                    "all_row_nrmse": fit_error,
                    "fixed_structure_loo_nrmse": loo_error,
                    "rank_one_determinant_residual": det_error,
                    "max_plausible_prediction_disagreement_nrmse": disagreement,
                },
                old_v3_status=old.get("status"),
            )

    return _zero_credit(
        "FAIL_CLOSED__STRUCTURAL_IDENTIFIABILITY_NOT_PROVED",
        route=None,
        candidate=None,
        expression=None,
        fit_threshold=float(fit_threshold),
        old_v3_status=old.get("status"),
        old_v3_route=old.get("route"),
        old_v3_candidate_quarantined=bool(old.get("candidate")),
        structured_product_status=product.get("status"),
        structured_product_candidate=product.get("candidate"),
    )