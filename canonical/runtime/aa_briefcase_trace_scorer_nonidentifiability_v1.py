from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_TRACE_SCORER_NONIDENTIFIABILITY_V1"


class CutError(ValueError):
    pass


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def bt_probability(rating: float, anchor_rating: float = 1000.0) -> float:
    z = (float(rating) - float(anchor_rating)) * math.log(10.0) / 400.0
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def crowd_bt_probability(
    rating: float,
    *,
    anchor_rating: float = 1000.0,
    eta: float,
) -> float:
    e = float(eta)
    if not 0.0 <= e <= 1.0:
        raise CutError("ETA_OUT_OF_RANGE")
    p = bt_probability(rating, anchor_rating)
    return e * p + (1.0 - e) * (1.0 - p)


def all_wins_log_likelihood(
    rating: float,
    *,
    anchor_rating: float = 1000.0,
    eta: float,
    comparison_count: int,
) -> float:
    n = int(comparison_count)
    if n < 1:
        raise CutError("COMPARISON_COUNT_INVALID")
    q = crowd_bt_probability(rating, anchor_rating=anchor_rating, eta=eta)
    if q <= 0.0:
        return float("-inf")
    return n * math.log(q)


def public_contract_implies_unique_subject_rating(
    *,
    eta: float,
    comparison_count: int = 1,
) -> dict[str, Any]:
    e = float(eta)
    if not 0.0 <= e <= 1.0:
        raise CutError("ETA_OUT_OF_RANGE")
    n = int(comparison_count)
    if n < 1:
        raise CutError("COMPARISON_COUNT_INVALID")

    if e == 0.5:
        return {
            "schema": SCHEMA,
            "status": "COUNTEREXAMPLE_NONUNIQUE_FLAT_LIKELIHOOD",
            "public_contract_implies_unique_subject_rating": False,
            "reason": (
                "At eta=0.5 the Crowd-BT observed preference is exactly 0.5 "
                "for every finite rating, so every rating has the same likelihood."
            ),
        }

    if e > 0.5:
        return {
            "schema": SCHEMA,
            "status": "COUNTEREXAMPLE_NO_FINITE_MLE_ALL_WINS",
            "public_contract_implies_unique_subject_rating": False,
            "reason": (
                "For an admissible graph containing only subject wins against the "
                "anchor, q(r) is strictly increasing for every finite r and tends "
                "to eta as r->+infinity. The likelihood has a supremum but no "
                "finite maximizer. Extra regularization or fit-state conventions "
                "are therefore load-bearing."
            ),
        }

    return {
        "schema": SCHEMA,
        "status": "COUNTEREXAMPLE_REVERSED_SIGNAL",
        "public_contract_implies_unique_subject_rating": False,
        "reason": (
            "For eta<0.5, increasing latent Bradley-Terry strength decreases the "
            "observed preference probability. Public eta range alone does not "
            "supply the monotone scoring relation needed for the target proof."
        ),
    }


def two_trace_countermodel(public_state: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(public_state, Mapping):
        raise CutError("PUBLIC_STATE_INVALID")

    common = {
        "benchmark": "AA-Briefcase",
        "version": "1.1",
        "public_state": dict(public_state),
        "anchor_model": "GPT-5.5 (medium)",
        "anchor_elo": 1000,
    }
    world_a = {
        **common,
        "hidden_score_bearing_state": {
            "rubric_verdict_vector": [1],
            "analytical_pairwise_verdicts": ["A"],
            "presentation_pairwise_verdicts": ["A"],
        },
    }
    world_b = {
        **common,
        "hidden_score_bearing_state": {
            "rubric_verdict_vector": [0],
            "analytical_pairwise_verdicts": ["B"],
            "presentation_pairwise_verdicts": ["B"],
        },
    }
    digest_a = _sha(world_a)
    digest_b = _sha(world_b)
    return {
        "schema": SCHEMA,
        "status": "PASS_TWO_TRACE_COUNTERMODEL",
        "same_public_state": True,
        "trace_a_sha256": digest_a,
        "trace_b_sha256": digest_b,
        "trace_digests_differ": digest_a != digest_b,
        "public_state_determines_complete_score_trace": False,
        "hard_nonclaim": (
            "The countermodel does not claim either hidden trace is the actual "
            "AA-Briefcase trace; it proves the bound public/internal evidence "
            "does not select one unique trace."
        ),
    }


def evaluate_internal_score_trace_route(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise CutError("PAYLOAD_INVALID")
    public_contract_bound = payload.get("public_contract_bound") is True
    reference_1822_bound = payload.get("reference_1822_bound") is True
    complete_trace_equivalence = payload.get("complete_trace_equivalence_proved") is True
    scorer_unique_or_equivariant = (
        payload.get("scorer_unique_or_equivariant_proved") is True
    )

    missing = []
    if not public_contract_bound:
        missing.append("PUBLIC_CONTRACT")
    if not reference_1822_bound:
        missing.append("FROZEN_REFERENCE_1822")
    if not complete_trace_equivalence:
        missing.append("COMPLETE_REFERENCE_CANDIDATE_TRACE_EQUIVALENCE")
    if not scorer_unique_or_equivariant:
        missing.append("SCORER_IMPLEMENTATION_EQUIVARIANCE_OR_UNIQUE_FIT")

    return {
        "schema": SCHEMA,
        "status": "PASS_ROUTE_PREMISES" if not missing else "OPEN_ROUTE_PREMISES",
        "missing": missing,
        "threshold_1822_proved": not missing,
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }
