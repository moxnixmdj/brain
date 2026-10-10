"""Receipt-bound residual-priority ranking for Universal Learning V8.

Contradictions and unexplained decision-relevant residuals should be attacked
before low-value novelty. Ranking is planning metadata only and cannot authorize
an experiment or task execution.
"""
from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_RESIDUAL_PRIORITY_V8"


class ResidualPriorityError(ValueError):
    pass


def _s(x: Any) -> str:
    return " ".join(str(x or "").split())


def _f(x: Any, name: str) -> Fraction:
    if isinstance(x, bool):
        raise ResidualPriorityError(name.upper() + "_INVALID")
    try:
        out = x if isinstance(x, Fraction) else Fraction(str(x))
    except Exception as exc:
        raise ResidualPriorityError(name.upper() + "_INVALID") from exc
    if out < 0:
        raise ResidualPriorityError(name.upper() + "_NEGATIVE")
    return out


def residual_digest(
    *,
    residual_id: str,
    decision_critical: bool,
    residual_mass_ub: Any,
    falsification_value_lcb: Any,
    future_transfer_lcb: Any,
    acquisition_cost_ub: Any,
) -> str:
    rid = _s(residual_id)
    if not rid or not isinstance(decision_critical, bool):
        raise ResidualPriorityError("RESIDUAL_ID_OR_CRITICALITY_INVALID")
    vals = {
        "residual_mass_ub": _f(residual_mass_ub, "residual_mass_ub"),
        "falsification_value_lcb": _f(falsification_value_lcb, "falsification_value_lcb"),
        "future_transfer_lcb": _f(future_transfer_lcb, "future_transfer_lcb"),
        "acquisition_cost_ub": _f(acquisition_cost_ub, "acquisition_cost_ub"),
    }
    body = json.dumps(
        {
            "residual_id": rid,
            "decision_critical": decision_critical,
            **{k: str(v) for k, v in vals.items()},
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return "sha256:" + hashlib.sha256(body).hexdigest()


def _verified(raw: Mapping[str, Any]) -> dict[str, Any]:
    rid = _s(raw.get("residual_id"))
    critical = raw.get("decision_critical")
    if not isinstance(critical, bool):
        raise ResidualPriorityError("DECISION_CRITICAL_REQUIRED")
    vals = {
        "residual_mass_ub": _f(raw.get("residual_mass_ub", 0), "residual_mass_ub"),
        "falsification_value_lcb": _f(raw.get("falsification_value_lcb", 0), "falsification_value_lcb"),
        "future_transfer_lcb": _f(raw.get("future_transfer_lcb", 0), "future_transfer_lcb"),
        "acquisition_cost_ub": _f(raw.get("acquisition_cost_ub", 0), "acquisition_cost_ub"),
    }
    digest = residual_digest(residual_id=rid, decision_critical=critical, **vals)
    r = raw.get("verification_receipt")
    if not isinstance(r, Mapping):
        raise ResidualPriorityError("RESIDUAL_RECEIPT_REQUIRED:" + rid)
    if r.get("independent_verified") is not True or r.get("exact_byte_bound") is not True or r.get("conclusion") != "success":
        raise ResidualPriorityError("RESIDUAL_RECEIPT_INVALID:" + rid)
    if r.get("residual_sha256") != digest or _s(r.get("residual_id")) != rid:
        raise ResidualPriorityError("RESIDUAL_RECEIPT_BINDING_MISMATCH:" + rid)
    rec = _s(r.get("receipt_id"))
    if not rec:
        raise ResidualPriorityError("RESIDUAL_RECEIPT_ID_REQUIRED:" + rid)
    return {"residual_id": rid, "decision_critical": critical, **vals, "residual_sha256": digest, "verification_receipt": rec}


def rank(residuals: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    xs = [_verified(x) for x in residuals]
    if not xs:
        return {"schema": SCHEMA, "status": "NO_VERIFIED_RESIDUALS", "ranked": [], "execution_authority": False}
    if len({x["residual_id"] for x in xs}) != len(xs):
        raise ResidualPriorityError("RESIDUAL_ID_DUPLICATE")

    # Lexicographic, conservative ordering. Decision-critical uncertainty always
    # beats noncritical novelty; inside a class, attack the largest unexplained
    # mass and strongest falsifier before future transfer value and cost.
    xs.sort(
        key=lambda x: (
            0 if x["decision_critical"] else 1,
            -x["residual_mass_ub"],
            -x["falsification_value_lcb"],
            -x["future_transfer_lcb"],
            x["acquisition_cost_ub"],
            x["residual_id"],
        )
    )
    return {
        "schema": SCHEMA,
        "status": "VERIFIED_RESIDUAL_PRIORITY",
        "ranked": [
            {
                "rank": i + 1,
                "residual_id": x["residual_id"],
                "decision_critical": x["decision_critical"],
                "residual_mass_ub": str(x["residual_mass_ub"]),
                "falsification_value_lcb": str(x["falsification_value_lcb"]),
                "future_transfer_lcb": str(x["future_transfer_lcb"]),
                "acquisition_cost_ub": str(x["acquisition_cost_ub"]),
                "verification_receipt": x["verification_receipt"],
            }
            for i, x in enumerate(xs)
        ],
        "ranking_order": [
            "DECISION_CRITICAL_FIRST",
            "RESIDUAL_MASS_UB_DESC",
            "FALSIFICATION_VALUE_LCB_DESC",
            "FUTURE_TRANSFER_LCB_DESC",
            "ACQUISITION_COST_UB_ASC",
            "RESIDUAL_ID_ASC",
        ],
        "planning_only": True,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
