from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Mapping
from urllib.parse import urlparse

SCHEMA = "PROJECT_BRAIN_FINANCE_INDEX_DIRECT_RESULT_BRIDGE_V1"
SUBJECT_SCHEMA = "PROJECT_BRAIN_FINANCE_INDEX_EVALUATION_SUBJECT_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_FINANCE_INDEX_DIRECT_RESULT_V1"
AUTHORITY_SCHEMA = "PROJECT_BRAIN_EXTERNAL_RESULT_AUTHORITY_RECEIPT_V1"

EXPECTED_BENCHMARK = "Artificial Analysis Finance & Accounting Index"
EXPECTED_BENCHMARK_VERSION = "1.1"
EXPECTED_EVALUATOR = "Artificial Analysis"
EXPECTED_UNIT = "index_points"
EXPECTED_SCORE_SCALE = "RAW_CAPABILITY_INDEX_POINTS"
THRESHOLD = 61.0

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class FinanceIndexResultBridgeError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _valid_sha40(value: Any) -> bool:
    return bool(_SHA40.fullmatch(str(value or "")))


def _valid_sha256(value: Any) -> bool:
    return bool(_SHA256.fullmatch(str(value or "")))


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FinanceIndexResultBridgeError(label + "_INVALID")
    out = float(value)
    if not math.isfinite(out):
        raise FinanceIndexResultBridgeError(label + "_INVALID")
    return out


def subject_digest(subject: Mapping[str, Any]) -> str:
    required = {
        "schema",
        "repository",
        "git_commit_sha",
        "execution_profile_git_blob_sha",
        "configuration_git_blob_sha",
        "execution_bundle_sha256",
    }
    if not isinstance(subject, Mapping) or set(subject) != required:
        raise FinanceIndexResultBridgeError("SUBJECT_FIELDS_INVALID")
    if subject.get("schema") != SUBJECT_SCHEMA:
        raise FinanceIndexResultBridgeError("SUBJECT_SCHEMA_MISMATCH")
    if subject.get("repository") != "moxnixmdj/brain":
        raise FinanceIndexResultBridgeError("SUBJECT_REPOSITORY_MISMATCH")
    if not _valid_sha40(subject.get("git_commit_sha")):
        raise FinanceIndexResultBridgeError("SUBJECT_COMMIT_INVALID")
    if not _valid_sha40(subject.get("execution_profile_git_blob_sha")):
        raise FinanceIndexResultBridgeError("SUBJECT_EXECUTION_PROFILE_BLOB_INVALID")
    if not _valid_sha40(subject.get("configuration_git_blob_sha")):
        raise FinanceIndexResultBridgeError("SUBJECT_CONFIGURATION_BLOB_INVALID")
    if not _valid_sha256(subject.get("execution_bundle_sha256")):
        raise FinanceIndexResultBridgeError("SUBJECT_EXECUTION_BUNDLE_INVALID")
    return _sha(subject)


def authority_statement_sha256(
    *,
    subject_sha256: str,
    brain_score: float,
    evidence_sha256: str,
    result_source_kind: str,
    result_source_uri: str,
) -> str:
    return _sha({
        "claim": "FINANCE_ACCOUNTING_INDEX_DIRECT_RAW_RESULT_AUTHENTICATED",
        "benchmark": EXPECTED_BENCHMARK,
        "benchmark_version": EXPECTED_BENCHMARK_VERSION,
        "evaluator": EXPECTED_EVALUATOR,
        "unit": EXPECTED_UNIT,
        "score_scale": EXPECTED_SCORE_SCALE,
        "threshold": THRESHOLD,
        "subject_sha256": subject_sha256,
        "brain_score": brain_score,
        "evidence_sha256": evidence_sha256,
        "result_source_kind": result_source_kind,
        "result_source_uri": result_source_uri,
    })


def _authority_ok(
    authority: Mapping[str, Any],
    *,
    statement_sha256: str,
    evidence_sha256: str,
    result_source_kind: str,
) -> bool:
    required = {
        "schema",
        "verified",
        "source_kind",
        "verifier_id",
        "statement_sha256",
        "evidence_sha256",
        "verification_authority_mutated",
        "auth_method",
        "auth_artifact_sha256",
        "receipt_sha256",
    }
    if not isinstance(authority, Mapping) or set(authority) != required:
        return False
    if authority.get("schema") != AUTHORITY_SCHEMA:
        return False
    if authority.get("verified") is not True:
        return False
    if authority.get("source_kind") != result_source_kind:
        return False
    if result_source_kind not in {"OWNER_EVALUATOR", "INDEPENDENT_VERIFIER"}:
        return False
    verifier_id = str(authority.get("verifier_id") or "").strip()
    if not verifier_id or verifier_id.upper() in {"BRAIN", "SELF", "SUBJECT"}:
        return False
    if authority.get("verification_authority_mutated") is not False:
        return False
    if authority.get("statement_sha256") != statement_sha256:
        return False
    if authority.get("evidence_sha256") != evidence_sha256:
        return False
    if authority.get("auth_method") not in {
        "OWNER_PUBLISHED_RESULT",
        "VERIFIED_DIGITAL_SIGNATURE",
        "INDEPENDENT_REPLAY",
    }:
        return False
    if not _valid_sha256(authority.get("auth_artifact_sha256")):
        return False
    if not _valid_sha256(authority.get("receipt_sha256")):
        return False
    payload = {str(k): v for k, v in authority.items() if k != "receipt_sha256"}
    return authority["receipt_sha256"] == _sha(payload)


def compile_direct_result(
    subject: Mapping[str, Any],
    result: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    subject_sha256 = subject_digest(subject)

    required_result = {
        "schema",
        "status",
        "benchmark",
        "benchmark_version",
        "evaluator",
        "unit",
        "score_scale",
        "score_rounding_applied",
        "brain_score",
        "threshold",
        "subject_sha256",
        "evidence_sha256",
        "result_source_kind",
        "result_source_uri",
    }
    if not isinstance(result, Mapping) or set(result) != required_result:
        raise FinanceIndexResultBridgeError("RESULT_FIELDS_INVALID")
    if result.get("schema") != RESULT_SCHEMA:
        raise FinanceIndexResultBridgeError("RESULT_SCHEMA_MISMATCH")
    if result.get("status") != "VERIFIED_COMPARABLE_BRAIN_SCORE":
        raise FinanceIndexResultBridgeError("RESULT_NOT_VERIFIED_COMPARABLE")
    expected = {
        "benchmark": EXPECTED_BENCHMARK,
        "benchmark_version": EXPECTED_BENCHMARK_VERSION,
        "evaluator": EXPECTED_EVALUATOR,
        "unit": EXPECTED_UNIT,
        "score_scale": EXPECTED_SCORE_SCALE,
    }
    for key, value in expected.items():
        if result.get(key) != value:
            raise FinanceIndexResultBridgeError("RESULT_TUPLE_MISMATCH:" + key)
    if result.get("score_rounding_applied") is not False:
        raise FinanceIndexResultBridgeError("ROUNDED_OR_DISPLAY_SCORE_FORBIDDEN")
    if result.get("subject_sha256") != subject_sha256:
        raise FinanceIndexResultBridgeError("RESULT_SUBJECT_MISMATCH")
    threshold = _finite_number(result.get("threshold"), "RESULT_THRESHOLD")
    if threshold != THRESHOLD:
        raise FinanceIndexResultBridgeError("RESULT_THRESHOLD_MISMATCH")
    score = _finite_number(result.get("brain_score"), "RESULT_SCORE")
    if not (0.0 <= score <= 100.0):
        raise FinanceIndexResultBridgeError("RESULT_SCORE_OUT_OF_RANGE")

    evidence_sha256 = str(result.get("evidence_sha256") or "")
    if not _valid_sha256(evidence_sha256):
        raise FinanceIndexResultBridgeError("RESULT_EVIDENCE_DIGEST_INVALID")
    source_kind = str(result.get("result_source_kind") or "")
    if source_kind not in {"OWNER_EVALUATOR", "INDEPENDENT_VERIFIER"}:
        raise FinanceIndexResultBridgeError("RESULT_SOURCE_KIND_INVALID")
    source_uri = str(result.get("result_source_uri") or "")
    parsed = urlparse(source_uri)
    if parsed.scheme != "https" or not parsed.netloc:
        raise FinanceIndexResultBridgeError("RESULT_SOURCE_URI_INVALID")
    if source_kind == "OWNER_EVALUATOR" and parsed.hostname not in {
        "artificialanalysis.ai",
        "www.artificialanalysis.ai",
    }:
        raise FinanceIndexResultBridgeError("OWNER_RESULT_SOURCE_NOT_ARTIFICIAL_ANALYSIS")

    statement_sha256 = authority_statement_sha256(
        subject_sha256=subject_sha256,
        brain_score=score,
        evidence_sha256=evidence_sha256,
        result_source_kind=source_kind,
        result_source_uri=source_uri,
    )
    if not _authority_ok(
        authority,
        statement_sha256=statement_sha256,
        evidence_sha256=evidence_sha256,
        result_source_kind=source_kind,
    ):
        raise FinanceIndexResultBridgeError("RESULT_AUTHORITY_RECEIPT_INVALID")

    sufficient = score >= THRESHOLD
    material = {
        "schema": SCHEMA,
        "status": (
            "VERIFIED_DIRECT_RAW_SCORE_AT_OR_ABOVE_THRESHOLD"
            if sufficient
            else "VERIFIED_DIRECT_RAW_SCORE_BELOW_THRESHOLD"
        ),
        "benchmark": EXPECTED_BENCHMARK,
        "benchmark_version": EXPECTED_BENCHMARK_VERSION,
        "evaluator": EXPECTED_EVALUATOR,
        "brain_score": score,
        "threshold": THRESHOLD,
        "unit": EXPECTED_UNIT,
        "score_scale": EXPECTED_SCORE_SCALE,
        "subject_sha256": subject_sha256,
        "result_evidence_sha256": evidence_sha256,
        "authority_receipt_sha256": authority["receipt_sha256"],
        "mathematically_sufficient": sufficient,
        "acceptance_credit_delta": 0,
        "promotion_authority": False,
        "terminal_authority": False,
    }
    return {**material, "bridge_verdict_sha256": _sha(material)}
