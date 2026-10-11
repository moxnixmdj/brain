"""Fail-closed GDPval-AA v2.1 matched-score receipt gate.

This gate does not create benchmark evidence. It validates one of two admissible
evidence shapes:
1) a Brain score measured under the frozen historical 1846 epoch/harness, or
2) a stronger same-fit Brain >= Claude Opus 5.5 comparator certificate where
   the comparator in that exact fit is itself >= 1846.

Passing this gate means the row is mechanically proof-ready. Promotion remains
a separate canonical action.
"""
from __future__ import annotations

import math
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_GDPVAL_MATCHED_EPOCH_RECEIPT_GATE_V1"
PREDICATE_ID = "PROWORK_GDPVAL_GE_1846"
BENCHMARK_ID = "GDPVAL-AA v2.1"
OWNER_ID = "ARTIFICIAL_ANALYSIS"
TARGET_MODEL_ID = "CLAUDE_OPUS_5_5_MAX_DEFAULT_FALLBACK"
TASK_COUNT = 220
FROZEN_BAR = 1846.0
_SHA = re.compile(r"^[0-9a-f]{64}$")
ROUTES = {"MATCHED_HISTORICAL_FIXED_BAR", "SAME_FIT_OPUS55_NONINFERIORITY"}


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "OPEN__GDPVAL_MATCHED_RECEIPT_NOT_PROVED",
        "reason": reason,
        "predicate_id": PREDICATE_ID,
        "row_acceptance_ready": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
        **extra,
    }


def _sha(value: Any) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _score(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    x = float(value)
    return x if math.isfinite(x) else None


def _common(receipt: Mapping[str, Any]) -> dict[str, Any] | None:
    if receipt.get("predicate_id") != PREDICATE_ID:
        return _fail("PREDICATE_ID_MISMATCH")
    if receipt.get("benchmark_id") != BENCHMARK_ID:
        return _fail("BENCHMARK_ID_MISMATCH")
    if receipt.get("score_owner") != OWNER_ID:
        return _fail("SCORE_OWNER_NOT_ARTIFICIAL_ANALYSIS")
    if receipt.get("task_count") != TASK_COUNT:
        return _fail("TASK_COUNT_NOT_220", observed=receipt.get("task_count"))
    if receipt.get("frozen_before_brain_scoring") is not True:
        return _fail("PREDECLARATION_NOT_PROVED")
    if receipt.get("harness_valid") is not True:
        return _fail("HARNESS_VALIDITY_NOT_PROVED")
    if receipt.get("scoring_protocol_valid") is not True:
        return _fail("SCORING_PROTOCOL_VALIDITY_NOT_PROVED")
    if receipt.get("same_task_population") is not True:
        return _fail("TASK_POPULATION_COMPARABILITY_NOT_PROVED")

    required_hashes = (
        "brain_subject_sha256",
        "task_population_sha256",
        "harness_manifest_sha256",
        "submission_manifest_sha256",
        "score_receipt_sha256",
        "independent_verification_sha256",
    )
    for field in required_hashes:
        if not _sha(receipt.get(field)):
            return _fail("CONTENT_ADDRESS_MISSING_OR_INVALID", field=field)
    return None


def verify(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        return _fail("RECEIPT_MAPPING_REQUIRED")

    common_failure = _common(receipt)
    if common_failure is not None:
        return common_failure

    route = receipt.get("route")
    if route not in ROUTES:
        return _fail("ROUTE_UNRECOGNIZED", route=route)

    brain_score = _score(receipt.get("brain_score"))
    if brain_score is None:
        return _fail("BRAIN_SCORE_INVALID")

    if route == "MATCHED_HISTORICAL_FIXED_BAR":
        if receipt.get("historical_bar") != FROZEN_BAR:
            return _fail("HISTORICAL_BAR_MISMATCH", observed=receipt.get("historical_bar"))
        brain_epoch = receipt.get("brain_epoch_id")
        target_epoch = receipt.get("target_epoch_id")
        if not isinstance(brain_epoch, str) or not brain_epoch or brain_epoch != target_epoch:
            return _fail("HISTORICAL_EPOCH_NOT_MATCHED")
        if receipt.get("same_harness_as_target_epoch") is not True:
            return _fail("HISTORICAL_HARNESS_NOT_MATCHED")
        for field in ("target_comparator_receipt_sha256", "epoch_equivalence_receipt_sha256"):
            if not _sha(receipt.get(field)):
                return _fail("HISTORICAL_MATCH_EVIDENCE_MISSING", field=field)
        if brain_score < FROZEN_BAR:
            return _fail(
                "BRAIN_SCORE_BELOW_FROZEN_BAR",
                brain_score=brain_score,
                required=FROZEN_BAR,
            )
        theorem = "MATCHED_HISTORICAL_BRAIN_SCORE_GE_FROZEN_1846_BAR"

    else:
        if receipt.get("comparator_model_id") != TARGET_MODEL_ID:
            return _fail("COMPARATOR_MODEL_ID_MISMATCH")
        if receipt.get("same_fit") is not True:
            return _fail("BRAIN_AND_OPUS_NOT_IN_SAME_FIT")
        if receipt.get("same_harness_as_comparator") is not True:
            return _fail("BRAIN_AND_OPUS_HARNESS_NOT_MATCHED")
        brain_fit = receipt.get("brain_fit_id")
        comparator_fit = receipt.get("comparator_fit_id")
        if not isinstance(brain_fit, str) or not brain_fit or brain_fit != comparator_fit:
            return _fail("FIT_ID_MISMATCH")
        comparator_score = _score(receipt.get("comparator_score"))
        if comparator_score is None:
            return _fail("COMPARATOR_SCORE_INVALID")
        if not _sha(receipt.get("comparator_score_receipt_sha256")):
            return _fail("COMPARATOR_SCORE_RECEIPT_MISSING")
        if comparator_score < FROZEN_BAR:
            return _fail(
                "SAME_FIT_COMPARATOR_DOES_NOT_DOMINATE_FROZEN_BAR",
                comparator_score=comparator_score,
                frozen_bar=FROZEN_BAR,
            )
        if brain_score < comparator_score:
            return _fail(
                "BRAIN_INFERIOR_TO_OPUS_IN_SAME_FIT",
                brain_score=brain_score,
                comparator_score=comparator_score,
            )
        theorem = (
            "SAME_FIT_BRAIN_GE_OPUS55_AND_SAME_FIT_OPUS55_GE_1846__"
            "THEREFORE_BRAIN_GE_1846_ON_THAT_V2_1_SCALE"
        )

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__GDPVAL_MATCHED_RECEIPT_ROW_PROOF_READY",
        "predicate_id": PREDICATE_ID,
        "route": route,
        "brain_score": brain_score,
        "frozen_bar": FROZEN_BAR,
        "theorem": theorem,
        "row_acceptance_ready": True,
        "acceptance_authority": False,
        "promotion_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
        "boundary": (
            "THIS_GATE_VALIDATES_AUTHENTICATED_MEASUREMENT_RECEIPTS_ONLY__"
            "IT_NEVER_MINTS_A_SCORE_OR_EPOCH_EQUIVALENCE_FROM INTERNAL CLAIMS"
        ),
    }


def run(args=None, root=None):
    return verify(args or {})
