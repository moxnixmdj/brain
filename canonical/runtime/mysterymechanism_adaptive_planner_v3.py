"""Adaptive experiment planner for MysteryMechanism V3.

Zero-learned-byte, private-task-blind route. It preserves the public 2d+1 active
experiment budget while replacing the static "four corners then one center"
pattern with: space-filling seed probes until five total observations exist,
then bounded candidate-disagreement probes after every new observation.

No private benchmark task, target function, score, threshold, or credential is
embedded or accessed. No acceptance/capability/terminal credit is granted.
"""
from __future__ import annotations

import itertools
import math
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import h100_zero_learned_mechanism_synthesizer_v1 as base
from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v2 as sparse
from canonical.runtime import mysterymechanism_separable_transform_v1 as separable

SCHEMA = "PROJECT_BRAIN_MYSTERYMECHANISM_ADAPTIVE_PLANNER_V3"
_EPS = 1e-12


class AdaptivePlannerError(ValueError):
    pass


def _finite(v: Any, name: str) -> float:
    if isinstance(v, bool):
        raise AdaptivePlannerError(name.upper() + "_INVALID")
    try:
        x = float(v)
    except (TypeError, ValueError) as exc:
        raise AdaptivePlannerError(name.upper() + "_INVALID") from exc
    if not math.isfinite(x):
        raise AdaptivePlannerError(name.upper() + "_NONFINITE")
    return x


def _bounds(bounds: Mapping[str, Sequence[Any]]) -> dict[str, tuple[float, float]]:
    if not isinstance(bounds, Mapping) or not bounds:
        raise AdaptivePlannerError("BOUNDS_REQUIRED")
    out = {}
    for raw_name, pair in bounds.items():
        name = str(raw_name).strip()
        if not name or not isinstance(pair, Sequence) or isinstance(pair, (str, bytes)) or len(pair) != 2:
            raise AdaptivePlannerError("BOUND_INVALID")
        lo, hi = _finite(pair[0], name + "_lo"), _finite(pair[1], name + "_hi")
        if not lo < hi:
            raise AdaptivePlannerError("BOUND_ORDER_INVALID:" + name)
        out[name] = (lo, hi)
    if len(out) > 5:
        raise AdaptivePlannerError("TOO_MANY_INPUTS")
    return dict(sorted(out.items()))


def _axes(
    bounds: Mapping[str, Sequence[Any]],
    *,
    grid_levels: int = 7,
    max_points: int = 4096,
) -> tuple[dict[str, tuple[float, float]], list[list[float]]]:
    b = _bounds(bounds)
    d = len(b)
    if not isinstance(grid_levels, int) or grid_levels < 3:
        raise AdaptivePlannerError("GRID_LEVELS_INVALID")
    if not isinstance(max_points, int) or max_points < 3 ** d:
        raise AdaptivePlannerError("MAX_POINTS_TOO_SMALL")
    levels = max(3, min(grid_levels, int(max_points ** (1.0 / d))))
    while levels ** d > max_points and levels > 3:
        levels -= 1
    axes = []
    for lo, hi in b.values():
        if lo > 0 and hi > 0:
            ratio = hi / lo
            vals = [lo * ratio ** (i / (levels - 1)) for i in range(levels)]
        else:
            vals = [lo + (hi - lo) * i / (levels - 1) for i in range(levels)]
        axes.append(vals)
    return b, axes


def _candidate_points(
    bounds: Mapping[str, Sequence[Any]],
    *,
    grid_levels: int = 7,
    max_points: int = 4096,
):
    b, axes = _axes(bounds, grid_levels=grid_levels, max_points=max_points)
    for vals in itertools.product(*axes):
        yield b, dict(zip(b, vals))


def _point_from_row(row: Mapping[str, Any], b: Mapping[str, tuple[float, float]]) -> dict[str, float]:
    if not isinstance(row, Mapping):
        raise AdaptivePlannerError("ROW_INVALID")
    point = {}
    for name, (lo, hi) in b.items():
        if name not in row:
            raise AdaptivePlannerError("ROW_INPUT_MISSING:" + name)
        x = _finite(row[name], name)
        if x < lo - _EPS or x > hi + _EPS:
            raise AdaptivePlannerError("ROW_OUTSIDE_DECLARED_BOUNDS:" + name)
        point[name] = x
    return point


def _distance(
    point: Mapping[str, float],
    other: Mapping[str, float],
    b: Mapping[str, tuple[float, float]],
) -> float:
    return math.sqrt(
        sum(((point[name] - other[name]) / (hi - lo)) ** 2 for name, (lo, hi) in b.items())
        / len(b)
    )


def maximin_probe(
    rows: Sequence[Mapping[str, Any]],
    *,
    bounds: Mapping[str, Sequence[Any]],
    grid_levels: int = 7,
    max_points: int = 4096,
) -> dict[str, Any]:
    """Strictly bounded deterministic space-filling fallback/seed probe."""
    b = _bounds(bounds)
    observed = [_point_from_row(row, b) for row in rows]
    best = None
    considered = 0
    for _, point in _candidate_points(b, grid_levels=grid_levels, max_points=max_points):
        considered += 1
        novelty = min((_distance(point, row, b) for row in observed), default=1.0)
        key = (novelty, tuple(point[name] for name in b))
        if best is None or key > best[0]:
            best = (key, point)
    if best is None:
        raise AdaptivePlannerError("NO_BOUNDED_PROBE")
    return {
        "schema": SCHEMA,
        "status": "SPACE_FILLING_MAXIMIN",
        "point": best[1],
        "novelty": best[0][0],
        "points_considered": considered,
        "all_coordinates_within_declared_bounds": True,
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
    }


def choose_from_predictors(
    rows: Sequence[Mapping[str, Any]],
    *,
    bounds: Mapping[str, Sequence[Any]],
    predictors: Sequence[Callable[[Mapping[str, float]], float]],
    grid_levels: int = 7,
    max_points: int = 4096,
) -> dict[str, Any]:
    """Select a bounded point that maximizes plausible-model disagreement.

    This core is intentionally generic so it can be independently tested
    without private benchmark material or any particular symbolic grammar.
    """
    b = _bounds(bounds)
    observed = [_point_from_row(row, b) for row in rows]
    if len(predictors) < 2:
        return maximin_probe(rows, bounds=b, grid_levels=grid_levels, max_points=max_points)

    best = None
    considered = 0
    for _, point in _candidate_points(b, grid_levels=grid_levels, max_points=max_points):
        considered += 1
        novelty = min((_distance(point, row, b) for row in observed), default=1.0)
        if novelty <= 1e-12:
            continue
        preds = []
        for predictor in predictors:
            try:
                y = float(predictor(point))
            except Exception:
                continue
            if math.isfinite(y):
                preds.append(y)
        if len(preds) < 2:
            continue
        preds.sort()
        median = preds[len(preds) // 2]
        spread = preds[-1] - preds[0]
        scale = max(1.0, abs(median), max(abs(x) for x in preds))
        disagreement = spread / scale
        # Avoid selecting a near-duplicate solely because one extrapolating
        # model explodes there. Novelty is bounded in [0,1] for this factor.
        score = disagreement * (0.35 + 0.65 * min(1.0, 2.0 * novelty))
        key = (score, disagreement, novelty, tuple(point[name] for name in b))
        if best is None or key > best[0]:
            best = (key, point, preds)
    if best is None or best[0][1] <= 1e-12:
        return maximin_probe(rows, bounds=b, grid_levels=grid_levels, max_points=max_points)
    return {
        "schema": SCHEMA,
        "status": "ADAPTIVE_CANDIDATE_DISAGREEMENT",
        "point": best[1],
        "score": best[0][0],
        "normalized_disagreement": best[0][1],
        "novelty": best[0][2],
        "candidate_predictions": best[2],
        "candidate_count": len(predictors),
        "points_considered": considered,
        "all_coordinates_within_declared_bounds": True,
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
    }


def _ensemble(
    rows: Sequence[Mapping[str, Any]],
    *,
    bounds: Mapping[str, Sequence[Any]],
    target: str,
) -> list[dict[str, Any]]:
    """Build a diverse, error-ranked candidate set from existing Brain routes."""
    b = _bounds(bounds)
    members = []

    try:
        discovery = base.discover(rows, target=target, inputs=list(b), top_k=12)
        for cand in discovery.get("candidates") or []:
            err = max(
                float(cand.get("nrmse", math.inf)),
                float(cand.get("validation_nrmse", cand.get("nrmse", math.inf))),
            )
            if math.isfinite(err):
                members.append({
                    "kind": "base",
                    "candidate": cand,
                    "error": err,
                    "id": "base:" + str(cand.get("structural_signature") or cand.get("family")),
                })
    except (base.MechanismSynthesisError, ValueError, OverflowError):
        pass

    # Multiple grammar depths intentionally create competing sparse hypotheses
    # rather than reducing the sparse route to one premature winner.
    for depth, beam, pool in ((1, 20, 12), (2, 28, 16)):
        try:
            discovery = sparse.sparse_discover(
                rows,
                target=target,
                inputs=list(b),
                max_depth=depth,
                beam_width=beam,
                pair_pool=pool,
            )
            cand = discovery.get("best_candidate")
            if cand is None:
                continue
            err = max(float(cand["loo_nrmse"]), float(cand["all_nrmse"]))
            if math.isfinite(err):
                members.append({
                    "kind": "sparse",
                    "candidate": cand,
                    "error": err,
                    "id": "sparse:d" + str(depth) + ":" + "|".join(cand.get("feature_signatures") or []),
                })
        except (sparse.SparseSymbolicError, ValueError, OverflowError):
            pass

    members.sort(key=lambda m: (m["error"], m["id"]))
    if not members:
        return []

    # Keep only candidates that remain remotely plausible on observed evidence.
    best_error = float(members[0]["error"])
    limit = max(0.08, best_error * 4.0 + 1e-4)
    plausible = [m for m in members if float(m["error"]) <= limit]
    if len(plausible) < 2:
        plausible = members[: min(2, len(members))]

    # Prediction-equivalent candidates do not buy information.
    unique = []
    signatures = set()
    points = [{name: float(row[name]) for name in b} for row in rows]
    for member in plausible:
        values = []
        valid = True
        for point in points:
            try:
                values.append(_predict_member(member, point))
            except Exception:
                valid = False
                break
        if not valid:
            continue
        scale = max(1.0, max(abs(v) for v in values))
        sig = tuple(round(v / scale, 8) for v in values)
        if sig in signatures:
            continue
        signatures.add(sig)
        unique.append(member)
        if len(unique) >= 16:
            break
    return unique


def _predict_member(member: Mapping[str, Any], point: Mapping[str, float]) -> float:
    kind = str(member.get("kind") or "")
    if kind == "base":
        return float(base.predict(member["candidate"], point))
    if kind == "sparse":
        return float(sparse._sparse_predict(member["candidate"], point))
    raise AdaptivePlannerError("CANDIDATE_KIND_INVALID")


def adaptive_probe(
    rows: Sequence[Mapping[str, Any]],
    *,
    bounds: Mapping[str, Sequence[Any]],
    target: str = "out",
    grid_levels: int = 7,
    max_points: int = 4096,
) -> dict[str, Any]:
    """Recompute candidate set and choose the next bounded discriminator."""
    members = _ensemble(rows, bounds=bounds, target=target)
    predictors = [
        (lambda point, member=member: _predict_member(member, point))
        for member in members
    ]
    out = choose_from_predictors(
        rows,
        bounds=bounds,
        predictors=predictors,
        grid_levels=grid_levels,
        max_points=max_points,
    )
    out["ensemble_routes"] = [member["kind"] for member in members]
    out["ensemble_ids"] = [member["id"] for member in members]
    out["ensemble_fit_errors"] = [member["error"] for member in members]
    return out


def next_experiment(
    rows: Sequence[Mapping[str, Any]],
    *,
    bounds: Mapping[str, Sequence[Any]],
    active_experiments_used: int,
    target: str = "out",
    grid_levels: int = 7,
    max_points: int = 4096,
) -> dict[str, Any]:
    """Return exactly one next experiment under the public 2d+1 budget."""
    b = _bounds(bounds)
    d = len(b)
    budget = 2 * d + 1
    if not isinstance(active_experiments_used, int) or isinstance(active_experiments_used, bool):
        raise AdaptivePlannerError("ACTIVE_EXPERIMENTS_USED_INVALID")
    if not 0 <= active_experiments_used <= budget:
        raise AdaptivePlannerError("ACTIVE_EXPERIMENTS_USED_OUT_OF_RANGE")
    if active_experiments_used >= budget:
        return {
            "schema": SCHEMA,
            "status": "ACTIVE_BUDGET_EXHAUSTED",
            "point": None,
            "active_budget": budget,
            "active_experiments_used": active_experiments_used,
            "remaining_active_experiments": 0,
            "acceptance_credit_delta": 0,
        }

    # Five total observations are the first point at which the frozen sparse
    # route can perform leave-one-out model selection. Until then, maximize
    # geometric information without inventing a mechanism.
    if len(rows) < 5:
        out = maximin_probe(
            rows,
            bounds=b,
            grid_levels=grid_levels,
            max_points=max_points,
        )
        out["reason"] = "SEED_UNTIL_FIVE_TOTAL_OBSERVATIONS"
    else:
        out = adaptive_probe(
            rows,
            bounds=b,
            target=target,
            grid_levels=grid_levels,
            max_points=max_points,
        )
        if out["status"] == "SPACE_FILLING_MAXIMIN":
            out["reason"] = "NO_TWO_PLAUSIBLE_PREDICTIVELY_DISTINCT_MODELS"
        else:
            out["reason"] = "DISCRIMINATE_CURRENT_PLAUSIBLE_MECHANISMS"

    out.update({
        "active_budget": budget,
        "active_experiments_used": active_experiments_used,
        "remaining_active_experiments_after_this": budget - active_experiments_used - 1,
        "replan_required_after_observation": True,
        "private_task_data_used": False,
        "private_score_claimed": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    })
    return out


def finalize(
    rows: Sequence[Mapping[str, Any]],
    *,
    bounds: Mapping[str, Sequence[Any]],
    target: str = "out",
    fit_threshold: float = 0.05,
) -> dict[str, Any]:
    """Race existing final solvers and return the strongest observed-data route."""
    b = _bounds(bounds)
    options = []

    try:
        out = sparse.solve(rows, bounds=b, target=target, fit_threshold=fit_threshold)
        if out.get("candidate") is not None and out.get("expression"):
            options.append({
                "route": "V2_BASE_OR_SPARSE",
                "error": float(out["conservative_nrmse"]),
                "expression": out["expression"],
                "candidate": out["candidate"],
            })
    except Exception:
        pass

    if len(b) == 2 and len(rows) >= 7:
        try:
            out = separable.discover(rows, bounds=b, target=target, validation_index=-1)
            cand = out.get("candidate")
            if cand is not None and out.get("expression"):
                error = max(
                    float(cand.get("fit_nrmse", math.inf)),
                    float(cand.get("reserved_validation_nrmse", math.inf)),
                )
                if math.isfinite(error):
                    options.append({
                        "route": "SEPARABLE_TRANSFORM",
                        "error": error,
                        "expression": out["expression"],
                        "candidate": cand,
                    })
        except Exception:
            pass

    options.sort(key=lambda x: (x["error"], x["route"]))
    if not options or options[0]["error"] > fit_threshold:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__MECHANISM_LANGUAGE_OR_EVIDENCE_INSUFFICIENT",
            "candidate": None,
            "expression": None,
            "best_conservative_nrmse": options[0]["error"] if options else None,
            "fit_threshold": float(fit_threshold),
            "private_score_claimed": False,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    best = options[0]
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_READY__UNVERIFIED_ON_PRIVATE_STRUCTURAL_PROBES",
        "route": best["route"],
        "candidate": best["candidate"],
        "expression": best["expression"],
        "conservative_nrmse": best["error"],
        "fit_threshold": float(fit_threshold),
        "private_score_claimed": False,
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
        "random_search": False,
        "dynamic_code_execution": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
