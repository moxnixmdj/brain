from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping
import re

INPUT_SCHEMA = "PROJECT_BRAIN_BLIND_THRESHOLD_RECEIPT_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_BLIND_THRESHOLD_RECEIPT_OUTPUT_V1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")

SUPPORTED_METRIC_KINDS = {
    "ADDITIVE_THRESHOLD",
    "GATED_WEIGHTED_THRESHOLD",
    "RELATIVE_RATING_THRESHOLD",
}
SUPPORTED_RECEIPT_CLASSES = {
    "OWNER_PLATFORM_THRESHOLD_RECEIPT",
    "OWNER_SIGNED_THRESHOLD_RECEIPT",
    "OWNER_BLIND_SCORE_THRESHOLD_RECEIPT",
}

class BlindThresholdReceiptError(ValueError):
    pass

def _mapping(v: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(v, Mapping):
        raise BlindThresholdReceiptError(field + "_MAPPING_REQUIRED")
    return v

def _text(v: Any, field: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise BlindThresholdReceiptError(field + "_TEXT_REQUIRED")
    return v.strip()

def _hex40(v: Any, field: str) -> str:
    s = _text(v, field).lower()
    if not HEX40.fullmatch(s):
        raise BlindThresholdReceiptError(field + "_HEX40_REQUIRED")
    return s

def _decimal(v: Any, field: str) -> Decimal:
    if isinstance(v, bool):
        raise BlindThresholdReceiptError(field + "_DECIMAL_REQUIRED")
    try:
        x = Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise BlindThresholdReceiptError(field + "_DECIMAL_REQUIRED") from exc
    if not x.is_finite():
        raise BlindThresholdReceiptError(field + "_FINITE_REQUIRED")
    return x

def _receipt_ref(v: Any, field: str) -> dict[str, str]:
    m = _mapping(v, field)
    return {
        "path": _text(m.get("path"), field + "_PATH"),
        "git_blob_sha": _hex40(m.get("git_blob_sha"), field + "_GIT_BLOB_SHA"),
    }

def _identity(v: Any, field: str) -> dict[str, str]:
    m = _mapping(v, field)
    return {
        "commit_sha": _hex40(m.get("commit_sha"), field + "_COMMIT_SHA"),
        "tree_sha": _hex40(m.get("tree_sha"), field + "_TREE_SHA"),
    }

def compile_blind_threshold_receipt(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping):
            raise BlindThresholdReceiptError("DOCUMENT_MAPPING_REQUIRED")
        if doc.get("schema") != INPUT_SCHEMA:
            raise BlindThresholdReceiptError("SCHEMA_MISMATCH")

        target = _mapping(doc.get("frozen_target"), "FROZEN_TARGET")
        receipt = _mapping(doc.get("blind_receipt"), "BLIND_RECEIPT")

        predicate_id = _text(target.get("predicate_id"), "TARGET_PREDICATE_ID")
        benchmark_id = _text(target.get("benchmark_id"), "TARGET_BENCHMARK_ID")
        metric_kind = _text(target.get("metric_kind"), "TARGET_METRIC_KIND")
        if metric_kind not in SUPPORTED_METRIC_KINDS:
            raise BlindThresholdReceiptError("TARGET_METRIC_KIND_UNSUPPORTED")
        if target.get("operator") != "GE":
            raise BlindThresholdReceiptError("ONLY_GE_THRESHOLDS_SUPPORTED")
        threshold = _decimal(target.get("threshold"), "TARGET_THRESHOLD")
        unit = _text(target.get("unit"), "TARGET_UNIT")
        candidate = _identity(target.get("candidate_identity"), "TARGET_CANDIDATE_IDENTITY")
        harness = _receipt_ref(target.get("harness_receipt"), "TARGET_HARNESS_RECEIPT")

        if receipt.get("receipt_class") not in SUPPORTED_RECEIPT_CLASSES:
            raise BlindThresholdReceiptError("RECEIPT_CLASS_UNSUPPORTED")
        if _text(receipt.get("predicate_id"), "RECEIPT_PREDICATE_ID") != predicate_id:
            raise BlindThresholdReceiptError("PREDICATE_ID_DRIFT")
        if _text(receipt.get("benchmark_id"), "RECEIPT_BENCHMARK_ID") != benchmark_id:
            raise BlindThresholdReceiptError("BENCHMARK_ID_DRIFT")
        if receipt.get("operator") != "GE":
            raise BlindThresholdReceiptError("RECEIPT_OPERATOR_DRIFT")
        if _decimal(receipt.get("threshold"), "RECEIPT_THRESHOLD") != threshold:
            raise BlindThresholdReceiptError("THRESHOLD_DRIFT")
        if _text(receipt.get("unit"), "RECEIPT_UNIT") != unit:
            raise BlindThresholdReceiptError("UNIT_DRIFT")
        if _identity(receipt.get("candidate_identity"), "RECEIPT_CANDIDATE_IDENTITY") != candidate:
            raise BlindThresholdReceiptError("CANDIDATE_IDENTITY_DRIFT")
        if _receipt_ref(receipt.get("harness_receipt"), "RECEIPT_HARNESS_RECEIPT") != harness:
            raise BlindThresholdReceiptError("HARNESS_IDENTITY_DRIFT")

        source = _receipt_ref(receipt.get("source_artifact"), "SOURCE_ARTIFACT")
        independent = _receipt_ref(
            receipt.get("source_verification_receipt"), "SOURCE_VERIFICATION_RECEIPT"
        )
        issuer = _text(receipt.get("issuer"), "ISSUER")
        run_id = _text(receipt.get("evaluation_run_id"), "EVALUATION_RUN_ID")

        required_true = [
            "source_authenticity_verified",
            "exact_frozen_protocol_verified",
            "candidate_identity_verified",
            "harness_identity_verified",
            "threshold_identity_verified",
            "independent_or_objective",
        ]
        for key in required_true:
            if receipt.get(key) is not True:
                raise BlindThresholdReceiptError(key.upper() + "_TRUE_REQUIRED")

        semantics = _text(receipt.get("metric_semantics"), "METRIC_SEMANTICS")
        if metric_kind == "RELATIVE_RATING_THRESHOLD":
            if semantics != "OFFICIAL_RELATIVE_RATING_THRESHOLD_VERDICT":
                raise BlindThresholdReceiptError(
                    "RELATIVE_RATING_REQUIRES_OFFICIAL_RELATIVE_THRESHOLD_VERDICT"
                )
        elif semantics != "OFFICIAL_FIXED_BAR_THRESHOLD_VERDICT":
            raise BlindThresholdReceiptError("FIXED_BAR_REQUIRES_OFFICIAL_THRESHOLD_VERDICT")

        verdict = _text(receipt.get("verdict"), "VERDICT")
        if verdict not in {"PASS", "FAIL"}:
            raise BlindThresholdReceiptError("VERDICT_INVALID")

        disclosed = receipt.get("exact_score_disclosed")
        if not isinstance(disclosed, bool):
            raise BlindThresholdReceiptError("EXACT_SCORE_DISCLOSED_BOOLEAN_REQUIRED")
        exact_score = None
        if disclosed:
            exact_score = _decimal(receipt.get("exact_score"), "EXACT_SCORE")
            derived = "PASS" if exact_score >= threshold else "FAIL"
            if derived != verdict:
                raise BlindThresholdReceiptError("DISCLOSED_SCORE_VERDICT_INCONSISTENT")
        elif "exact_score" in receipt and receipt.get("exact_score") is not None:
            raise BlindThresholdReceiptError("UNDISCLOSED_EXACT_SCORE_PRESENT")

        return {
            "schema": OUTPUT_SCHEMA,
            "status": "PASS__BLIND_THRESHOLD_CERTIFICATE_STRUCTURALLY_ELIGIBLE__ZERO_CREDIT",
            "predicate_id": predicate_id,
            "benchmark_id": benchmark_id,
            "metric_kind": metric_kind,
            "operator": "GE",
            "threshold": str(threshold),
            "unit": unit,
            "verdict": verdict,
            "certificate_effect": (
                "PASS_CERTIFICATE_ELIGIBLE_FOR_SEPARATE_ACCEPTANCE_REDUCTION"
                if verdict == "PASS"
                else "FAIL_CERTIFICATE_ELIGIBLE_FOR_SEPARATE_ACCEPTANCE_REDUCTION"
            ),
            "exact_score_required": False,
            "exact_score_disclosed": disclosed,
            "exact_score": str(exact_score) if exact_score is not None else None,
            "candidate_identity": candidate,
            "harness_receipt": harness,
            "source_artifact": source,
            "source_verification_receipt": independent,
            "issuer": issuer,
            "evaluation_run_id": run_id,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "fresh_reality_authority": False,
            "promotion_authority": False,
        }
    except BlindThresholdReceiptError as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "fresh_reality_authority": False,
            "promotion_authority": False,
        }
