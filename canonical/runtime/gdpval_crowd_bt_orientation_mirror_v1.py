"""Exact Crowd-BT orientation mirror theorem over rational true-preference probabilities.

For direct head-to-head comparisons, if p is the latent Brain-over-Target
preference probability and eta is annotator quality, Crowd-BT observes

    q = eta*p + (1-eta)*(1-p).

The mirror world p' = 1-p, eta' = 1-eta gives exactly the same q.
Therefore direct comparison observations alone cannot identify which side of
1/2 the latent preference probability lies on while eta orientation is free.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping


class OrientationMirrorError(ValueError):
    pass


def _f(value: Any, label: str) -> Fraction:
    if isinstance(value, bool):
        raise OrientationMirrorError(f"{label}_BOOL_FORBIDDEN")
    try:
        out = Fraction(str(value))
    except Exception as exc:
        raise OrientationMirrorError(f"{label}_INVALID") from exc
    if out < 0 or out > 1:
        raise OrientationMirrorError(f"{label}_OUTSIDE_UNIT_INTERVAL")
    return out


def crowd_probability(true_brain_preference: Fraction, eta: Fraction) -> Fraction:
    return eta * true_brain_preference + (1 - eta) * (1 - true_brain_preference)


def mirror_world(true_brain_preference: Any, eta: Any) -> dict[str, str | bool]:
    p = _f(true_brain_preference, "TRUE_PREFERENCE")
    e = _f(eta, "ETA")
    q = crowd_probability(p, e)
    pm = 1 - p
    em = 1 - e
    qm = crowd_probability(pm, em)
    return {
        "original_true_preference": str(p),
        "original_eta": str(e),
        "original_observed_probability": str(q),
        "mirror_true_preference": str(pm),
        "mirror_eta": str(em),
        "mirror_observed_probability": str(qm),
        "observationally_identical": q == qm,
        "latent_direction_reversed": (p > Fraction(1, 2) and pm < Fraction(1, 2))
        or (p < Fraction(1, 2) and pm > Fraction(1, 2)),
    }


def certify(task: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(task, Mapping):
        raise OrientationMirrorError("TASK_INVALID")
    rows = task.get("judges")
    if not isinstance(rows, list) or not rows:
        raise OrientationMirrorError("JUDGES_REQUIRED")

    witnesses = []
    for idx, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise OrientationMirrorError(f"JUDGE_{idx}_INVALID")
        witnesses.append(mirror_world(row.get("true_preference"), row.get("eta")))

    identity = all(bool(w["observationally_identical"]) for w in witnesses)
    return {
        "schema": "PROJECT_BRAIN_DIRECT_CROWD_BT_ORIENTATION_NONIDENTIFIABILITY_V1",
        "status": "PASS__EXACT_MIRROR_IDENTITY" if identity else "FAIL",
        "witnesses": witnesses,
        "theorem": (
            "P_CROWD(p,eta)=P_CROWD(1-p,1-eta); THEREFORE WHEN ETA ORIENTATION "
            "IS UNCONSTRAINED, DIRECT HEAD_TO_HEAD OBSERVATIONS ALONE DO NOT "
            "IDENTIFY THE SIGN OF LATENT BRAIN_MINUS_TARGET STRENGTH."
        ),
        "required_escape": (
            "BIND_AN_ORIENTATION_OR_CALIBRATION_CONSTRAINT_THAT_EXCLUDES_THE_MIRROR_CLASS, "
            "OR_USE_A_SOUND_STRONGER_RELATION_CERTIFICATE_NOT_DEPENDENT_ON_CROWD_BT_SIGN_IDENTIFICATION."
        ),
        "terminal_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
