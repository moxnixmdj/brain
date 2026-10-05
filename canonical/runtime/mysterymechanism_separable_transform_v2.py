"""Prospective-selection-safe successor for sparse separable mechanism discovery.

V1 called its final visible experiment "prospective validation" but used that
experiment's error while choosing the transform pair.  With a large transform
grammar and seven observations, that lets the supposed validator participate in
model selection.

V2 repairs the information flow:
  1. remove the reserved validation row completely;
  2. build and deduplicate the transform libraries on fit rows only;
  3. screen all transform pairs using fit-row error only;
  4. choose among the strongest fit-only pairs using leave-one-out prediction
     entirely inside the fit partition;
  5. expose the reserved row exactly once, after structure selection is frozen;
  6. fail closed unless fit, inner-LOO, and prospective errors all satisfy the
     predeclared development gate.

The final row may be used for the final coefficient refit only after the frozen
structure passes the prospective gate.  No private benchmark mechanism, score,
or target is encoded here, and this module grants zero acceptance credit.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from canonical.runtime import mysterymechanism_separable_transform_v1 as v1
from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v1 as sparse

SCHEMA = "PROJECT_BRAIN_MYSTERYMECHANISM_PROSPECTIVE_SELECTION_V2"
MAX_GENERALIZATION_NRMSE = 0.08
_EPS = 1e-12


class ProspectiveSelectionError(ValueError):
    pass


def _scale(values: Sequence[float]) -> float:
    if not values:
        return 1.0
    mean = sum(float(x) for x in values) / len(values)
    spread = math.sqrt(
        sum((float(x) - mean) ** 2 for x in values) / len(values)
    )
    return max(spread, max(abs(float(x)) for x in values) * 1e-9, _EPS)


def _complexity(left: Mapping[str, Any], right: Mapping[str, Any]) -> int:
    return (
        1
        + (1 if left["kind"] == "identity" else 3)
        + (1 if right["kind"] == "identity" else 3)
        + (1 if "boundary" not in str(left["kind"]) else 2)
        + (1 if "boundary" not in str(right["kind"]) else 2)
    )


def _descriptor_pair_key(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> tuple[Any, ...]:
    return (v1._descriptor_key(left), v1._descriptor_key(right))


def _inner_loo_predictions(
    a: Sequence[float],
    b: Sequence[float],
    y: Sequence[float],
) -> list[float] | None:
    if len(y) < 6 or len(a) != len(y) or len(b) != len(y):
        return None
    out: list[float] = []
    for held in range(len(y)):
        keep = [i for i in range(len(y)) if i != held]
        fit = v1._fit_bilinear(
            [float(a[i]) for i in keep],
            [float(b[i]) for i in keep],
            [float(y[i]) for i in keep],
        )
        if fit is None:
            return None
        coeff, _ = fit
        av = float(a[held])
        bv = float(b[held])
        pred = (
            float(coeff[0])
            + float(coeff[1]) * av
            + float(coeff[2]) * bv
            + float(coeff[3]) * av * bv
        )
        if not math.isfinite(pred):
            return None
        out.append(pred)
    return out


def _candidate_summary(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "left": dict(candidate["left"]),
        "right": dict(candidate["right"]),
        "prevalidation_coefficients": [
            float(x) for x in candidate["prevalidation_coefficients"]
        ],
        "fit_nrmse": float(candidate["fit_nrmse"]),
        "inner_loo_nrmse": float(candidate["inner_loo_nrmse"]),
        "selection_score": float(candidate["selection_score"]),
        "complexity": int(candidate["complexity"]),
        "selection_fingerprint": candidate["selection_fingerprint"],
    }


def discover(
    rows: Sequence[Mapping[str, Any]],
    *,
    bounds: Mapping[str, Sequence[Any]],
    target: str = "out",
    validation_index: int = -1,
) -> dict[str, Any]:
    b = sparse._normalize_bounds(bounds)
    if len(b) != 2:
        raise ProspectiveSelectionError("EXACTLY_TWO_INPUTS_REQUIRED")
    target, names, data = sparse._normalize_rows(rows, target, list(b))
    if len(data) < 7:
        raise ProspectiveSelectionError("AT_LEAST_SEVEN_ROWS_REQUIRED")
    if validation_index < 0:
        validation_index = len(data) + validation_index
    if not 0 <= validation_index < len(data):
        raise ProspectiveSelectionError("VALIDATION_INDEX_INVALID")

    fit_indices = [i for i in range(len(data)) if i != validation_index]
    if len(fit_indices) < 6:
        raise ProspectiveSelectionError("SIX_FIT_ROWS_REQUIRED")

    y_all = [float(r[target]) for r in data]
    y_fit = [y_all[i] for i in fit_indices]
    fit_scale = _scale(y_fit)

    n1, n2 = names
    vals1_all = [float(r[n1]) for r in data]
    vals2_all = [float(r[n2]) for r in data]
    vals1_fit = [vals1_all[i] for i in fit_indices]
    vals2_fit = [vals2_all[i] for i in fit_indices]

    # Critical anti-leakage rule: library construction and deduplication see only
    # fit rows.  The validation input and target cannot affect the candidate set.
    l1 = v1._library(n1, vals1_fit, b[n1])
    l2 = v1._library(n2, vals2_fit, b[n2])

    screened: list[tuple[tuple[Any, ...], dict[str, Any], list[float], list[float]]] = []
    considered = 0
    for left in l1:
        a = [float(x) for x in left["values"]]
        for right in l2:
            considered += 1
            bb = [float(x) for x in right["values"]]
            fit = v1._fit_bilinear(a, bb, y_fit)
            if fit is None:
                continue
            coeff, pred_fit = fit
            train_error = float(sparse._nrmse(y_fit, pred_fit))
            complexity = _complexity(left["descriptor"], right["descriptor"])
            key = (
                train_error + 1e-6 * complexity,
                train_error,
                complexity,
                *_descriptor_pair_key(left["descriptor"], right["descriptor"]),
            )
            screened.append(
                (
                    key,
                    {
                        "left": dict(left["descriptor"]),
                        "right": dict(right["descriptor"]),
                        "prevalidation_coefficients": [float(x) for x in coeff],
                        "fit_nrmse": train_error,
                        "complexity": complexity,
                    },
                    a,
                    bb,
                )
            )

    # Exact fit-only branch-and-bound.  The all-fit error plus complexity
    # penalty is a lower bound on this candidate's final selection score because
    # selection uses max(all-fit error, inner-LOO error).  Therefore once the
    # next lower bound exceeds the incumbent score, no unseen pair can win.
    screened.sort(key=lambda row: row[0])
    best: tuple[tuple[Any, ...], dict[str, Any]] | None = None
    inner_evaluated = 0

    for lower_bound, candidate, a, bb in screened:
        if best is not None and float(lower_bound[0]) > float(best[0][0]) + 1e-12:
            break
        loo_pred = _inner_loo_predictions(a, bb, y_fit)
        inner_evaluated += 1
        if loo_pred is None:
            continue
        loo_error = float(sparse._nrmse(y_fit, loo_pred))
        score = max(float(candidate["fit_nrmse"]), loo_error) + 1e-6 * int(
            candidate["complexity"]
        )
        fingerprint = repr(
            _descriptor_pair_key(candidate["left"], candidate["right"])
        )
        candidate = dict(candidate)
        candidate["inner_loo_nrmse"] = loo_error
        candidate["selection_score"] = score
        candidate["selection_fingerprint"] = fingerprint
        key = (
            score,
            max(float(candidate["fit_nrmse"]), loo_error),
            int(candidate["complexity"]),
            *_descriptor_pair_key(candidate["left"], candidate["right"]),
        )
        if best is None or key < best[0]:
            best = (key, candidate)

    if best is None:
        return {
            "schema": SCHEMA,
            "status": "SEPARABLE_GRAMMAR_EXHAUSTED__FAIL_CLOSED",
            "candidate": None,
            "selected_prevalidation": None,
            "validation_observation_used_for_selection": False,
            "transform_pairs_considered": considered,
            "inner_candidates_evaluated": inner_evaluated,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }

    selected = best[1]

    # Only now is the reserved observation exposed to the selected structure.
    av = v1._transform(selected["left"], vals1_all[validation_index])
    bv = v1._transform(selected["right"], vals2_all[validation_index])
    if av is None or bv is None:
        validation_prediction = None
        validation_error = math.inf
    else:
        c = [float(x) for x in selected["prevalidation_coefficients"]]
        validation_prediction = c[0] + c[1] * av + c[2] * bv + c[3] * av * bv
        validation_error = (
            abs(float(validation_prediction) - y_all[validation_index]) / fit_scale
            if math.isfinite(validation_prediction)
            else math.inf
        )

    prospective_pass = (
        float(selected["fit_nrmse"]) <= MAX_GENERALIZATION_NRMSE
        and float(selected["inner_loo_nrmse"]) <= MAX_GENERALIZATION_NRMSE
        and math.isfinite(validation_error)
        and validation_error <= MAX_GENERALIZATION_NRMSE
    )
    selected_summary = _candidate_summary(selected)

    base_result = {
        "schema": SCHEMA,
        "input_variables": list(names),
        "row_count": len(data),
        "fit_row_count": len(fit_indices),
        "validation_index": validation_index,
        "left_library_size": len(l1),
        "right_library_size": len(l2),
        "transform_pairs_considered": considered,
        "inner_candidates_evaluated": inner_evaluated,
        "selection_exact_branch_and_bound": True,
        "selected_prevalidation": selected_summary,
        "prospective_validation_prediction": (
            None if validation_prediction is None else float(validation_prediction)
        ),
        "prospective_validation_actual": y_all[validation_index],
        "prospective_validation_nrmse": float(validation_error),
        "generalization_nrmse_limit": MAX_GENERALIZATION_NRMSE,
        "prospective_validation_pass": prospective_pass,
        "validation_observation_used_for_library": False,
        "validation_observation_used_for_selection": False,
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

    if not prospective_pass:
        return {
            **base_result,
            "status": "PROSPECTIVE_VALIDATION_FAILED__EXPAND_GRAMMAR",
            "candidate": None,
            "expression": None,
        }

    # Passing the predeclared gate authorizes using every visible observation for
    # coefficient estimation while keeping the already-selected structure fixed.
    a_all = [v1._transform(selected["left"], x) for x in vals1_all]
    b_all = [v1._transform(selected["right"], x) for x in vals2_all]
    if any(x is None for x in a_all) or any(x is None for x in b_all):
        raise ProspectiveSelectionError("FINAL_REFIT_DOMAIN_FAILURE")
    refit = v1._fit_bilinear(
        [float(x) for x in a_all],
        [float(x) for x in b_all],
        y_all,
    )
    if refit is None:
        raise ProspectiveSelectionError("FINAL_REFIT_FAILED")
    coeff, pred = refit
    candidate = {
        "left": dict(selected["left"]),
        "right": dict(selected["right"]),
        "coefficients": [float(x) for x in coeff],
        "prevalidation_coefficients": [
            float(x) for x in selected["prevalidation_coefficients"]
        ],
        "fit_nrmse": float(selected["fit_nrmse"]),
        "inner_loo_nrmse": float(selected["inner_loo_nrmse"]),
        "prospective_validation_nrmse": float(validation_error),
        "selection_score": float(selected["selection_score"]),
        "selection_fingerprint": selected["selection_fingerprint"],
        "complexity": int(selected["complexity"]),
        "all_row_nrmse": float(sparse._nrmse(y_all, pred)),
        "prospective_selection_preserved": True,
    }
    return {
        **base_result,
        "status": "PROSPECTIVELY_VALIDATED_SEPARABLE_CANDIDATE__ZERO_ACCEPTANCE_CREDIT",
        "candidate": candidate,
        "expression": v1.serialize(candidate),
    }


def predict(candidate: Mapping[str, Any], point: Mapping[str, Any]) -> float:
    return v1.predict(candidate, point)



def solve(
    rows: Sequence[Mapping[str, Any]],
    *,
    bounds: Mapping[str, Sequence[Any]],
    target: str = "out",
    validation_index: int = -1,
    fit_threshold: float = 0.05,
) -> dict[str, Any]:
    """Prospectively audit first; refine with the final row only after it passes.

    The reserved observation is never allowed to rescue a model that failed to
    predict it prospectively.  Once the pre-final structure passes that audit,
    the observation is no longer wasted: V1 may reuse it as an active
    discriminator to refine the final structure.  This improves capability
    without mislabeling post-observation refinement as independent validation.
    """
    threshold = sparse._finite(fit_threshold, "fit_threshold")
    if threshold <= 0:
        raise ProspectiveSelectionError("FIT_THRESHOLD_INVALID")

    audit = discover(
        rows,
        bounds=bounds,
        target=target,
        validation_index=validation_index,
    )
    audit_candidate = audit.get("candidate")
    if audit_candidate is None:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__PROSPECTIVE_AUDIT_FAILED__NO_REFINEMENT",
            "route": "PROSPECTIVE_AUDIT_THEN_ACTIVE_REFINEMENT",
            "candidate": None,
            "expression": None,
            "fit_threshold": threshold,
            "audit_status": audit["status"],
            "selected_prevalidation": audit.get("selected_prevalidation"),
            "prospective_validation_nrmse": audit.get("prospective_validation_nrmse"),
            "final_row_reused_for_refinement": False,
            "persistent_learned_bytes": 0,
            "external_learned_capability_calls": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }

    audit_conservative = max(
        float(audit_candidate["fit_nrmse"]),
        float(audit_candidate["inner_loo_nrmse"]),
        float(audit_candidate["prospective_validation_nrmse"]),
    )
    if not math.isfinite(audit_conservative) or audit_conservative > threshold:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__PROSPECTIVE_AUDIT_ABOVE_SOLVER_THRESHOLD__NO_REFINEMENT",
            "route": "PROSPECTIVE_AUDIT_THEN_ACTIVE_REFINEMENT",
            "candidate": None,
            "expression": None,
            "fit_threshold": threshold,
            "audit_conservative_nrmse": audit_conservative,
            "selected_prevalidation": audit["selected_prevalidation"],
            "prospective_validation_nrmse": audit["prospective_validation_nrmse"],
            "final_row_reused_for_refinement": False,
            "persistent_learned_bytes": 0,
            "external_learned_capability_calls": 0,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }

    # The information barrier has now done its job.  Reuse the observed final
    # result for capability refinement, but never call the resulting metric an
    # independent validation score.
    refined = v1.discover(
        rows,
        bounds=bounds,
        target=target,
        validation_index=validation_index,
    )
    refined_candidate = refined.get("candidate")
    if refined_candidate is None:
        chosen_candidate = audit_candidate
        chosen_expression = audit["expression"]
        chosen_route = "PROSPECTIVE_AUDIT_CANDIDATE"
        refined_visible_error = math.inf
    else:
        refined_visible_error = max(
            float(refined_candidate.get("fit_nrmse", math.inf)),
            float(refined_candidate.get("reserved_validation_nrmse", math.inf)),
            float(refined_candidate.get("all_row_nrmse", math.inf)),
        )
        if (
            math.isfinite(refined_visible_error)
            and refined_visible_error <= threshold
            and refined_visible_error <= audit_conservative
        ):
            chosen_candidate = refined_candidate
            chosen_expression = refined["expression"]
            chosen_route = "PROSPECTIVE_AUDIT_THEN_ACTIVE_REFINEMENT"
        else:
            chosen_candidate = audit_candidate
            chosen_expression = audit["expression"]
            chosen_route = "PROSPECTIVE_AUDIT_CANDIDATE"

    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_READY__PROSPECTIVE_AUDIT_PASSED__ZERO_PRIVATE_SCORE_CREDIT",
        "route": chosen_route,
        "candidate": chosen_candidate,
        "expression": chosen_expression,
        "audit_conservative_nrmse": audit_conservative,
        "refined_visible_error_nonindependent": (
            None if not math.isfinite(refined_visible_error)
            else float(refined_visible_error)
        ),
        "fit_threshold": threshold,
        "validation_index": audit["validation_index"],
        "audit_passed_before_refinement": True,
        "validation_observation_used_for_audit_selection": False,
        "final_row_reused_for_refinement": chosen_route == "PROSPECTIVE_AUDIT_THEN_ACTIVE_REFINEMENT",
        "final_row_refinement_metric_is_independent_validation": False,
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

def choose_final_experiment(
    rows: Sequence[Mapping[str, Any]],
    *,
    bounds: Mapping[str, Sequence[Any]],
    target: str = "out",
    grid_levels: int = 5,
) -> dict[str, Any]:
    """Choose the final probe before the row that V2 will reserve as holdout."""
    out = sparse.choose_final_experiment(
        rows,
        bounds=bounds,
        target=target,
        grid_levels=grid_levels,
    )
    return {
        **out,
        "prospective_contract": "APPEND_THIS_OBSERVATION_LAST__DO_NOT_USE_ITS_RESULT_BEFORE_V2_STRUCTURE_SELECTION",
        "acceptance_credit_delta": 0,
    }
