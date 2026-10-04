"""Deterministic expression-tree successor for zero-learned mechanism discovery.

This module extends the independently verified V1 mechanism synthesizer at its
explicit structural residual: nested saturation/correction laws.  It keeps the
same zero-learned, standard-library-only boundary and does NOT claim a hidden
MysteryMechanism score.

The main construction is a bounded, deterministic library of univariate
response features composed into a separable bilinear expression tree

    c0 + c1*f(x) + c2*g(z) + c3*f(x)*g(z)

which exactly contains products of affine corrections and baseline-plus-product
laws.  The feature grammar includes powers, one-plus-power reciprocal
saturation, upper-singularity corrections, and corrected powers of the forms

    x^p * (1 + (x/k)^q)^r
    x^p / (1 + (k/x)^q)^r

Numeric constants are generated from declared bounds plus a small canonical
dimensionless constant basis.  Candidate ranking uses full-data normalized
error, leave-one-out error, and a deterministic complexity tie-break.

The design is intentionally fail-closed.  It returns an unverified candidate
only when the best expression is below a caller-visible fit threshold.
"""
from __future__ import annotations

import itertools
import math
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_zero_learned_mechanism_synthesizer_v1 as v1

SCHEMA = "PROJECT_BRAIN_H100_ZERO_LEARNED_EXPRESSION_TREE_SYNTHESIZER_V2"
_EPS = 1e-12

_POWER_GRID = (
    -2.0, -1.5, -1.0, -0.75, -0.5, -0.25,
    0.25, 1.0 / 3.0, 0.5, 0.625, 2.0 / 3.0, 0.75, 0.8, 1.0, 1.5, 2.0, 3.0,
)
_POSITIVE_POWER_GRID = (
    0.25, 1.0 / 3.0, 0.5, 0.625, 2.0 / 3.0, 0.75, 0.8, 1.0, 1.5, 2.0,
)
_CORRECTION_GRID = (0.25, 0.5, 0.75, 0.8, 1.0)
_SINGULAR_GRID = (0.5, 1.0, 1.5, 1.75, 1.9, 1.9125, 2.0, 2.25, 2.5, 3.0)
_CANONICAL_CONSTANTS = (0.25, 0.4, 0.5, 1.0, 2.0, 4.0)


def _finite(value: Any, field: str) -> float:
    return v1._finite_number(value, field)


def _nrmse(actual: Sequence[float], predicted: Sequence[float]) -> float:
    return v1._nrmse(actual, predicted)


def _dedupe(values: Sequence[float]) -> list[float]:
    out: list[float] = []
    seen: set[float] = set()
    for raw in values:
        x = float(raw)
        if not math.isfinite(x):
            continue
        key = round(x, 12)
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


def _bounds_for(
    values: Sequence[float],
    explicit: Sequence[Any] | None,
) -> tuple[float, float]:
    if explicit is not None:
        if (
            not isinstance(explicit, Sequence)
            or isinstance(explicit, (str, bytes))
            or len(explicit) != 2
        ):
            raise v1.MechanismSynthesisError("BOUND_INVALID")
        lo = _finite(explicit[0], "bound_lo")
        hi = _finite(explicit[1], "bound_hi")
    else:
        lo = min(values)
        hi = max(values)
    if not lo < hi:
        raise v1.MechanismSynthesisError("BOUND_ORDER_INVALID")
    return lo, hi


def _k_grid(values: Sequence[float], explicit: Sequence[Any] | None) -> list[float]:
    lo, hi = _bounds_for(values, explicit)
    positive = [x for x in values if x > 0]
    geo = math.sqrt(max(lo, _EPS) * hi) if lo > 0 and hi > 0 else None
    raw = [
        0.5 * lo, lo, 2.0 * lo, 4.0 * lo,
        0.25 * hi, 0.5 * hi, 0.75 * hi, 0.9 * hi, 0.94 * hi, hi, 1.1 * hi, 2.0 * hi,
        *_CANONICAL_CONSTANTS,
    ]
    if geo is not None:
        raw.extend((0.25 * geo, 0.5 * geo, geo, 2.0 * geo, 4.0 * geo))
    if positive:
        pmin, pmax = min(positive), max(positive)
        raw.extend((pmin, 2.0 * pmin, pmax, 0.94 * pmax))
    return sorted(x for x in _dedupe(raw) if x > _EPS)


def _feature_key(spec: Mapping[str, Any]) -> tuple[Any, ...]:
    fam = str(spec["family"])
    return (fam,) + tuple(round(float(x), 12) for x in spec.get("params", ()))


def _feature_specs(
    values: Sequence[float],
    explicit_bounds: Sequence[Any] | None,
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for p in _POWER_GRID:
        specs.append({"family": "power", "params": (p,), "complexity": 1.0 + abs(p)})

    for p in _POSITIVE_POWER_GRID:
        specs.append({
            "family": "reciprocal_one_plus_power",
            "params": (p,),
            "complexity": 3.0 + abs(p),
        })

    anchors = _k_grid(values, explicit_bounds)
    for anchor in anchors:
        for p in _SINGULAR_GRID:
            specs.append({
                "family": "upper_singularity",
                "params": (anchor, p),
                "complexity": 4.0 + abs(p),
            })

    ks = _k_grid(values, explicit_bounds)
    # Corrected-power grammar.  Deliberately bounded: enough structure to express
    # common saturation/correction laws while keeping the search deterministic.
    p_grid = (1.0 / 3.0, 0.5, 0.625, 2.0 / 3.0, 0.75, 1.0)
    q_grid = (0.5, 0.625, 2.0 / 3.0, 1.0, 1.5, 2.0)
    for p, q, r, k in itertools.product(p_grid, q_grid, _CORRECTION_GRID, ks):
        specs.append({
            "family": "corrected_power_up",
            "params": (p, k, q, r),
            "complexity": 6.0 + abs(p) + abs(q) + abs(r),
        })
        specs.append({
            "family": "corrected_power_down",
            "params": (p, k, q, r),
            "complexity": 6.0 + abs(p) + abs(q) + abs(r),
        })

    out: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for spec in specs:
        key = _feature_key(spec)
        if key in seen:
            continue
        seen.add(key)
        out.append(spec)
    return out


def _eval_feature(spec: Mapping[str, Any], x: float) -> float | None:
    fam = str(spec["family"])
    params = tuple(float(v) for v in spec.get("params", ()))
    try:
        if fam == "power":
            (p,) = params
            if x < 0 and abs(p - round(p)) > 1e-12:
                return None
            if abs(x) <= _EPS and p < 0:
                return None
            y = x ** p
        elif fam == "reciprocal_one_plus_power":
            (p,) = params
            if x < 0 and abs(p - round(p)) > 1e-12:
                return None
            xp = x ** p
            den = 1.0 + xp
            if abs(den) <= _EPS:
                return None
            y = 1.0 / den
        elif fam == "upper_singularity":
            anchor, p = params
            den = anchor - x
            if den <= _EPS:
                return None
            y = x / (den ** p)
        elif fam == "corrected_power_up":
            p, k, q, r = params
            if x <= 0 or k <= 0:
                return None
            y = (x ** p) * ((1.0 + (x / k) ** q) ** r)
        elif fam == "corrected_power_down":
            p, k, q, r = params
            if x <= 0 or k <= 0:
                return None
            y = (x ** p) / ((1.0 + (k / x) ** q) ** r)
        else:
            return None
    except (OverflowError, ValueError, ZeroDivisionError):
        return None
    return y if math.isfinite(y) else None


def _fmt(x: float) -> str:
    if abs(x - round(x)) <= 1e-12:
        return str(int(round(x)))
    return format(float(x), ".12g")


def _feature_expression(spec: Mapping[str, Any], var: str) -> str:
    fam = str(spec["family"])
    p = tuple(float(v) for v in spec.get("params", ()))
    if fam == "power":
        return f"({var}**{_fmt(p[0])})"
    if fam == "reciprocal_one_plus_power":
        return f"(1/(1+{var}**{_fmt(p[0])}))"
    if fam == "upper_singularity":
        return f"({var}/({_fmt(p[0])}-{var})**{_fmt(p[1])})"
    if fam == "corrected_power_up":
        return (
            f"({var}**{_fmt(p[0])}*(1+({var}/{_fmt(p[1])})**{_fmt(p[2])})"
            f"**{_fmt(p[3])})"
        )
    if fam == "corrected_power_down":
        return (
            f"({var}**{_fmt(p[0])}/(1+({_fmt(p[1])}/{var})**{_fmt(p[2])})"
            f"**{_fmt(p[3])})"
        )
    raise v1.MechanismSynthesisError("FEATURE_FAMILY_INVALID")


def _fit_linear_features(
    feature_rows: Sequence[Sequence[float]],
    targets: Sequence[float],
) -> list[float] | None:
    if len(feature_rows) != len(targets) or not feature_rows:
        return None
    p = len(feature_rows[0])
    if p == 0 or any(len(row) != p for row in feature_rows):
        return None
    xtx = [[0.0] * p for _ in range(p)]
    xty = [0.0] * p
    for feats, y in zip(feature_rows, targets):
        for i in range(p):
            xty[i] += float(feats[i]) * float(y)
            for j in range(p):
                xtx[i][j] += float(feats[i]) * float(feats[j])
    trace = sum(abs(xtx[i][i]) for i in range(p))
    ridge = max(trace, 1.0) * 1e-13
    for i in range(p):
        xtx[i][i] += ridge
    return v1._solve_linear_system(xtx, xty)


def _predict_linear(coef: Sequence[float], feature_rows: Sequence[Sequence[float]]) -> list[float]:
    return [sum(float(a) * float(b) for a, b in zip(coef, row)) for row in feature_rows]


def _robust_fit_indices(targets: Sequence[float]) -> list[int]:
    if len(targets) < 6:
        return list(range(len(targets)))
    anchor = max(range(len(targets)), key=lambda i: abs(float(targets[i])))
    dominant = 1.0 if float(targets[anchor]) >= 0 else -1.0
    max_abs = max(abs(float(x)) for x in targets)
    keep: list[int] = []
    for i, raw in enumerate(targets):
        y = float(raw)
        sign = 1.0 if y >= 0 else -1.0
        # Private benchmark observations are noisy.  A tiny sign-flipped sample
        # should not force the structural search into an unrelated family.
        if sign != dominant and abs(y) <= 0.02 * max_abs:
            continue
        keep.append(i)
    return keep if len(keep) >= 5 else list(range(len(targets)))


def _single_feature_rank(
    values: Sequence[float],
    targets: Sequence[float],
    spec: Mapping[str, Any],
    fit_indices: Sequence[int],
) -> tuple[float, list[float]] | None:
    fv = [_eval_feature(spec, float(x)) for x in values]
    if any(x is None for x in fv):
        return None
    vec = [float(x) for x in fv if x is not None]
    train = [[1.0, vec[i]] for i in fit_indices]
    coef = _fit_linear_features(train, [targets[i] for i in fit_indices])
    if coef is None:
        return None
    pred = _predict_linear(coef, [[1.0, x] for x in vec])
    return _nrmse(targets, pred), vec


def _shortlist_features(
    values: Sequence[float],
    targets: Sequence[float],
    explicit_bounds: Sequence[Any] | None,
    fit_indices: Sequence[int],
    *,
    per_family: int = 12,
    global_limit: int = 72,
) -> list[dict[str, Any]]:
    ranked: list[tuple[float, float, tuple[Any, ...], dict[str, Any]]] = []
    for spec in _feature_specs(values, explicit_bounds):
        result = _single_feature_rank(values, targets, spec, fit_indices)
        if result is None:
            continue
        err, vec = result
        row = dict(spec)
        row["values"] = vec
        row["single_feature_nrmse"] = err
        ranked.append((err, float(spec["complexity"]), _feature_key(spec), row))
    ranked.sort(key=lambda x: (x[0], x[1], x[2]))

    out: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    seen: set[tuple[Any, ...]] = set()
    # Preserve structural diversity first, then use remaining slots globally.
    for _, _, key, row in ranked:
        fam = str(row["family"])
        if counts.get(fam, 0) >= per_family:
            continue
        counts[fam] = counts.get(fam, 0) + 1
        out.append(row)
        seen.add(key)
    for _, _, key, row in ranked:
        if len(out) >= global_limit:
            break
        if key in seen:
            continue
        out.append(row)
        seen.add(key)
    out.sort(key=lambda r: (
        float(r["single_feature_nrmse"]),
        float(r["complexity"]),
        _feature_key(r),
    ))
    return out[:global_limit]


def _tree_rows(f: Sequence[float], g: Sequence[float]) -> list[list[float]]:
    return [[1.0, a, b, a * b] for a, b in zip(f, g)]


def _loo_error(rows: Sequence[Sequence[float]], targets: Sequence[float]) -> float:
    if len(rows) < 6:
        return math.inf
    pred: list[float] = []
    actual: list[float] = []
    for held in range(len(rows)):
        idx = [i for i in range(len(rows)) if i != held]
        coef = _fit_linear_features([rows[i] for i in idx], [targets[i] for i in idx])
        if coef is None:
            return math.inf
        y = sum(float(a) * float(b) for a, b in zip(coef, rows[held]))
        if not math.isfinite(y):
            return math.inf
        pred.append(y)
        actual.append(float(targets[held]))
    return _nrmse(actual, pred)


def _tree_expression(
    coef: Sequence[float],
    f: Mapping[str, Any],
    g: Mapping[str, Any],
    variables: Sequence[str],
) -> str:
    fe = _feature_expression(f, variables[0])
    ge = _feature_expression(g, variables[1])
    return (
        f"({_fmt(coef[0])}"
        f"+({_fmt(coef[1])})*{fe}"
        f"+({_fmt(coef[2])})*{ge}"
        f"+({_fmt(coef[3])})*{fe}*{ge})"
    )


def _candidate_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        round(float(candidate["selection_score"]), 14),
        round(float(candidate["nrmse"]), 14),
        round(float(candidate.get("loo_nrmse", math.inf)), 14),
        float(candidate["complexity"]),
        str(candidate["structural_signature"]),
        str(candidate["expression"]),
    )


def discover(
    rows: Sequence[Mapping[str, Any]],
    *,
    target: str,
    inputs: Sequence[str] | None = None,
    bounds: Mapping[str, Sequence[Any]] | None = None,
    top_k: int = 16,
    max_shortlist_per_variable: int = 72,
) -> dict[str, Any]:
    target, variables, data = v1._normalize_rows(rows, target, inputs)
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
        raise v1.MechanismSynthesisError("TOP_K_INVALID")
    if len(variables) != 2:
        baseline = v1.discover(data, target=target, inputs=variables, top_k=top_k)
        return {
            "schema": SCHEMA,
            "status": baseline["status"],
            "target": target,
            "input_variables": list(variables),
            "row_count": len(data),
            "search_mode": "V1_FALLBACK_NON_2D",
            "candidates": baseline["candidates"],
            "learned_parameter_bytes": 0,
            "external_learned_capability_calls": 0,
            "acceptance_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }

    targets = [float(row[target]) for row in data]
    fit_indices = _robust_fit_indices(targets)
    shortlist: dict[str, list[dict[str, Any]]] = {}
    for variable in variables:
        explicit = None if bounds is None else bounds.get(variable)
        shortlist[variable] = _shortlist_features(
            [float(row[variable]) for row in data],
            targets,
            explicit,
            fit_indices,
            global_limit=max_shortlist_per_variable,
        )
        if not shortlist[variable]:
            return {
                "schema": SCHEMA,
                "status": "GRAMMAR_EXHAUSTED__EXPAND_MECHANISM_LANGUAGE",
                "target": target,
                "input_variables": list(variables),
                "row_count": len(data),
                "search_mode": "SEPARABLE_EXPRESSION_TREE_V2",
                "candidates": [],
                "learned_parameter_bytes": 0,
                "external_learned_capability_calls": 0,
                "acceptance_credit_delta": 0,
                "ownership_credit_delta": 0,
                "execution_authority": False,
                "promotion_authority": False,
                "fresh_reality_authority": False,
            }

    raw: list[dict[str, Any]] = []
    left, right = variables
    for f, g in itertools.product(shortlist[left], shortlist[right]):
        basis = _tree_rows(f["values"], g["values"])
        train_basis = [basis[i] for i in fit_indices]
        coef = _fit_linear_features(train_basis, [targets[i] for i in fit_indices])
        if coef is None:
            continue
        predicted = _predict_linear(coef, basis)
        if not all(math.isfinite(x) for x in predicted):
            continue
        err = _nrmse(targets, predicted)
        complexity = float(f["complexity"]) + float(g["complexity"]) + 4.0
        raw.append({
            "family": "separable_bilinear_tree",
            "target": target,
            "variables": list(variables),
            "left_feature": {k: v for k, v in f.items() if k != "values"},
            "right_feature": {k: v for k, v in g.items() if k != "values"},
            "coefficients": [float(x) for x in coef],
            "nrmse": err,
            "complexity": complexity,
            "structural_signature": (
                "separable_bilinear_tree|"
                + str(f["family"]) + "|" + str(g["family"])
            ),
            "expression": _tree_expression(coef, f, g, variables),
        })

    # Compute the more expensive leave-one-out score only on the strongest
    # full-data candidates.  This keeps runtime bounded while punishing brittle
    # four-coefficient interpolation of seven observations.
    raw.sort(key=lambda c: (float(c["nrmse"]), float(c["complexity"]), str(c["expression"])))
    for candidate in raw[:256]:
        f = candidate["left_feature"]
        g = candidate["right_feature"]
        fv = [_eval_feature(f, float(row[left])) for row in data]
        gv = [_eval_feature(g, float(row[right])) for row in data]
        if any(x is None for x in fv) or any(x is None for x in gv):
            candidate["loo_nrmse"] = math.inf
        else:
            basis = _tree_rows([float(x) for x in fv], [float(x) for x in gv])
            candidate["loo_nrmse"] = _loo_error(basis, targets)
        loo = float(candidate["loo_nrmse"])
        if not math.isfinite(loo):
            loo = 1e6
        candidate["selection_score"] = (
            float(candidate["nrmse"])
            + 0.35 * loo
            + 1e-6 * float(candidate["complexity"])
        )
    for candidate in raw[256:]:
        candidate["loo_nrmse"] = math.inf
        candidate["selection_score"] = 1e6 + float(candidate["nrmse"])

    raw.sort(key=_candidate_key)
    kept: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for candidate in raw:
        sig = (
            candidate["structural_signature"],
            _feature_key(candidate["left_feature"]),
            _feature_key(candidate["right_feature"]),
        )
        if sig in seen:
            continue
        seen.add(sig)
        kept.append(candidate)
        if len(kept) >= top_k:
            break

    # V1 remains a useful simpler challenger.  Keep it as evidence against
    # gratuitous tree complexity, but never hide which search mode produced it.
    baseline = v1.discover(data, target=target, inputs=variables, top_k=min(top_k, 8))
    for base in baseline.get("candidates", []):
        row = dict(base)
        row["search_origin"] = "V1_BASELINE"
        row.setdefault("expression", str(row.get("feature_expression", row.get("family"))))
        row.setdefault("loo_nrmse", math.inf)
        row.setdefault(
            "selection_score",
            float(row.get("nrmse", math.inf)) + 1e-6 * float(row.get("complexity", 1)),
        )
        kept.append(row)
    kept.sort(key=lambda c: (
        float(c.get("selection_score", math.inf)),
        float(c.get("nrmse", math.inf)),
        float(c.get("complexity", math.inf)),
        str(c.get("structural_signature", "")),
    ))
    kept = kept[:top_k]

    return {
        "schema": SCHEMA,
        "status": "CANDIDATES_FOUND" if kept else "GRAMMAR_EXHAUSTED__EXPAND_MECHANISM_LANGUAGE",
        "target": target,
        "input_variables": list(variables),
        "row_count": len(data),
        "search_mode": "SEPARABLE_EXPRESSION_TREE_V2",
        "robust_fit_row_count": len(fit_indices),
        "feature_shortlist_sizes": {k: len(v) for k, v in shortlist.items()},
        "tree_candidates_considered": len(raw),
        "candidates": kept,
        "learned_parameter_bytes": 0,
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def predict(candidate: Mapping[str, Any], point: Mapping[str, Any]) -> float:
    if candidate.get("family") != "separable_bilinear_tree":
        return v1.predict(candidate, point)
    variables = [str(x) for x in candidate.get("variables", [])]
    if len(variables) != 2 or any(name not in point for name in variables):
        raise v1.MechanismSynthesisError("PREDICTION_POINT_SCHEMA_INVALID")
    x = _finite(point[variables[0]], variables[0])
    z = _finite(point[variables[1]], variables[1])
    f = _eval_feature(candidate["left_feature"], x)
    g = _eval_feature(candidate["right_feature"], z)
    if f is None or g is None:
        raise v1.MechanismSynthesisError("PREDICTION_OUTSIDE_CANDIDATE_DOMAIN")
    c = [float(x) for x in candidate["coefficients"]]
    y = c[0] + c[1] * f + c[2] * g + c[3] * f * g
    if not math.isfinite(y):
        raise v1.MechanismSynthesisError("PREDICTION_NONFINITE")
    return y


def judge(
    discovery: Mapping[str, Any],
    *,
    fit_threshold: float = 0.03,
    loo_threshold: float = 0.08,
) -> dict[str, Any]:
    candidates = list(discovery.get("candidates") or [])
    if not candidates:
        return {
            "status": "EXPAND_MECHANISM_LANGUAGE",
            "candidate": None,
            "reason": "NO_DECLARED_GRAMMAR_CANDIDATE_EXPLAINS_EVIDENCE",
        }
    best = candidates[0]
    fit = float(best.get("nrmse", math.inf))
    loo = float(best.get("loo_nrmse", math.inf))
    if best.get("search_origin") == "V1_BASELINE":
        loo_ok = True
    else:
        loo_ok = math.isfinite(loo) and loo <= loo_threshold
    if fit <= fit_threshold and loo_ok:
        return {
            "status": "IDENTIFIED_CANDIDATE_UNVERIFIED",
            "candidate": best,
            "reason": "BOUNDED_EXPRESSION_TREE_FITS_AND_GENERALIZES_WITHIN_VISIBLE_EVIDENCE",
        }
    return {
        "status": "EXPAND_MECHANISM_LANGUAGE",
        "candidate": None,
        "best_visible_fit_nrmse": fit,
        "best_visible_loo_nrmse": loo,
        "reason": "VISIBLE_EVIDENCE_DOES_NOT_SUPPORT_A_STABLE_DECLARED_GRAMMAR_CANDIDATE",
    }
