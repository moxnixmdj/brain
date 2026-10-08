"""Two-anchor identification for the public Crowd-BT observation law.

This runtime proves a conditional identification theorem. It does not claim that any
particular GDPval reference corpus or AA score is currently bound.

Crowd-BT for one judge:
  q_r = eta * sigma(s-r) + (1-eta) * (1-sigma(s-r))
where sigma uses Elo scale 400.

Writing
  z_r = 2*q_r - 1
  a   = 2*eta - 1
gives
  z_r = a * tanh(ln(10)*(s-r)/800).

For two distinct fixed reference ratings r1 != r2, if the judge is informative
(a != 0), the ratio rho=z1/z2 cancels a. Setting
  u=10^(s/400), A=10^(r1/400), B=10^(r2/400)
yields
  rho = ((u-A)(u+B))/((u+A)(u-B)).
Thus u is the unique positive root of
  (rho-1)u^2 + (A-B)(rho+1)u - (rho-1)AB = 0.
The two algebraic roots have product -AB < 0, so exactly one is positive.

Special cases:
  z1=0,z2!=0 -> s=r1
  z2=0,z1!=0 -> s=r2
  z1=z2=0 -> judge is exactly uninformative (eta=1/2), so s is unidentified.

The theorem tolerates eta below 1/2. Orientation is learned rather than assumed.
"""
from __future__ import annotations

import math
from typing import Any, Mapping


ELO_SCALE = 400.0
LN10 = math.log(10.0)
TOL = 1e-10


class TwoAnchorIdentificationError(ValueError):
    pass


def _real(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TwoAnchorIdentificationError(f"{label}_MUST_BE_REAL")
    value = float(value)
    if not math.isfinite(value):
        raise TwoAnchorIdentificationError(f"{label}_MUST_BE_FINITE")
    return value


def bt_probability(score: float, ref: float) -> float:
    x = (score - ref) * LN10 / ELO_SCALE
    if x >= 0:
        e = math.exp(-x)
        return 1.0 / (1.0 + e)
    e = math.exp(x)
    return e / (1.0 + e)


def crowd_bt_probability(score: float, ref: float, eta: float) -> float:
    p = bt_probability(score, ref)
    return eta * p + (1.0 - eta) * (1.0 - p)


def identify(task: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(task, Mapping):
        raise TwoAnchorIdentificationError("TASK_INVALID")

    r1 = _real(task.get("anchor1_rating"), "ANCHOR1_RATING")
    r2 = _real(task.get("anchor2_rating"), "ANCHOR2_RATING")
    q1 = _real(task.get("preference_probability_vs_anchor1"), "Q1")
    q2 = _real(task.get("preference_probability_vs_anchor2"), "Q2")

    if abs(r1 - r2) <= TOL:
        raise TwoAnchorIdentificationError("ANCHORS_MUST_HAVE_DISTINCT_RATINGS")
    if not (0.0 <= q1 <= 1.0 and 0.0 <= q2 <= 1.0):
        raise TwoAnchorIdentificationError("PREFERENCE_PROBABILITIES_MUST_BE_IN_UNIT_INTERVAL")

    z1 = 2.0 * q1 - 1.0
    z2 = 2.0 * q2 - 1.0

    if abs(z1) <= TOL and abs(z2) <= TOL:
        return {
            "schema": "PROJECT_BRAIN_GDPVAL_CROWDBT_TWO_ANCHOR_IDENTIFICATION_RESULT_V1",
            "status": "UNKNOWN__JUDGE_EXACTLY_UNINFORMATIVE_OR_INPUT_PRECISION_INSUFFICIENT",
            "identified_rating": None,
            "identified_eta": None,
            "terminal_authority": False,
            "promotion_authority": False,
            "terminal_credit_delta": 0,
        }

    if abs(z1) <= TOL:
        score = r1
    elif abs(z2) <= TOL:
        score = r2
    else:
        rho = z1 / z2
        if abs(rho - 1.0) <= TOL:
            raise TwoAnchorIdentificationError("NO_FINITE_INFORMATIVE_CROWDBT_SOLUTION_FOR_RHO_ONE")

        A = 10.0 ** (r1 / ELO_SCALE)
        B = 10.0 ** (r2 / ELO_SCALE)
        qa = rho - 1.0
        qb = (A - B) * (rho + 1.0)
        qc = -(rho - 1.0) * A * B

        disc = qb * qb - 4.0 * qa * qc
        if disc <= 0.0:
            raise TwoAnchorIdentificationError("POSITIVE_ROOT_DISCRIMINANT_REQUIRED")
        root_disc = math.sqrt(disc)
        roots = [(-qb + root_disc) / (2.0 * qa), (-qb - root_disc) / (2.0 * qa)]
        positives = [u for u in roots if u > 0.0 and math.isfinite(u)]
        if len(positives) != 1:
            raise TwoAnchorIdentificationError("UNIQUE_POSITIVE_ROOT_NOT_FOUND")
        u = positives[0]
        score = ELO_SCALE * math.log10(u)

    # Recover eta from whichever anchor is not at equality.
    c = LN10 / (2.0 * ELO_SCALE)
    t1 = math.tanh(c * (score - r1))
    t2 = math.tanh(c * (score - r2))
    if abs(t1) > TOL:
        orientation = z1 / t1
    elif abs(t2) > TOL:
        orientation = z2 / t2
    else:
        raise TwoAnchorIdentificationError("INFORMATIVE_ANCHOR_DENOMINATOR_MISSING")
    eta = (1.0 + orientation) / 2.0

    if eta < -TOL or eta > 1.0 + TOL:
        raise TwoAnchorIdentificationError("OBSERVATIONS_INCOMPATIBLE_WITH_CROWDBT_ETA_UNIT_INTERVAL")
    eta = min(1.0, max(0.0, eta))

    q1_check = crowd_bt_probability(score, r1, eta)
    q2_check = crowd_bt_probability(score, r2, eta)
    residual = max(abs(q1_check - q1), abs(q2_check - q2))
    if residual > 1e-7:
        raise TwoAnchorIdentificationError(f"RECONSTRUCTION_RESIDUAL_TOO_LARGE:{residual}")

    return {
        "schema": "PROJECT_BRAIN_GDPVAL_CROWDBT_TWO_ANCHOR_IDENTIFICATION_RESULT_V1",
        "status": "PASS__UNIQUE_CROWDBT_SCORE_AND_JUDGE_ORIENTATION_IDENTIFIED",
        "identified_rating": score,
        "identified_eta": eta,
        "judge_orientation": "NONADVERSARIAL" if eta > 0.5 else "ADVERSARIAL" if eta < 0.5 else "UNINFORMATIVE",
        "reconstruction_max_abs_error": residual,
        "theorem": [
            "TWO_DISTINCT_FIXED_ANCHORS_CANCEL_UNKNOWN_JUDGE_QUALITY",
            "RESULTING_QUADRATIC_HAS_ROOT_PRODUCT_MINUS_A_TIMES_B",
            "EXACTLY_ONE_ROOT_IS_POSITIVE",
            "ETA_BELOW_ONE_HALF_IS_ALLOWED",
        ],
        "semantic_premise_verified_by_this_runtime": False,
        "finite_sample_uncertainty_handled": False,
        "terminal_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
