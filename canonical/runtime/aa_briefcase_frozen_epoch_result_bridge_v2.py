from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping
from urllib.parse import urlparse

from canonical.runtime.aa_briefcase_dual_predicate_result_bridge_v1 import (
    EXPECTED,
    FROZEN_RATING_EPOCH,
    PREDICATES,
    THRESHOLD,
    BridgeError,
    compile_bridge as compile_v1_bridge,
)

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_FROZEN_EPOCH_RESULT_BRIDGE_V2"
SUBJECT_SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_FROZEN_EVALUATION_SUBJECT_V1"
AUTHORITY_SCHEMA = "PROJECT_BRAIN_EXTERNAL_RESULT_AUTHORITY_RECEIPT_V1"
RESULT_SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_FROZEN_EPOCH_RESULT_V2"

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


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
        raise BridgeError(label + "_INVALID")
    out = float(value)
    if out != out or out in (float("inf"), float("-inf")):
        raise BridgeError(label + "_INVALID")
    return out


def _subject_digest(subject: Mapping[str, Any]) -> str:
    required = {
        "schema",
        "repository",
        "git_commit_sha",
        "execution_profile_git_blob_sha",
        "configuration_git_blob_sha",
        "execution_bundle_sha256",
    }
    if not isinstance(subject, Mapping) or set(subject) != required:
        raise BridgeError("SUBJECT_FIELDS_INVALID")
    if subject.get("schema") != SUBJECT_SCHEMA:
        raise BridgeError("SUBJECT_SCHEMA_MISMATCH")
    if subject.get("repository") != "moxnixmdj/brain":
        raise BridgeError("SUBJECT_REPOSITORY_MISMATCH")
    if not _valid_sha40(subject.get("git_commit_sha")):
        raise BridgeError("SUBJECT_COMMIT_INVALID")
    if not _valid_sha40(subject.get("execution_profile_git_blob_sha")):
        raise BridgeError("SUBJECT_EXECUTION_PROFILE_BLOB_INVALID")
    if not _valid_sha40(subject.get("configuration_git_blob_sha")):
        raise BridgeError("SUBJECT_CONFIGURATION_BLOB_INVALID")
    if not _valid_sha256(subject.get("execution_bundle_sha256")):
        raise BridgeError("SUBJECT_EXECUTION_BUNDLE_INVALID")
    return _sha(subject)


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
    if not verifier_id or verifier_id in {"BRAIN", "SELF", "SUBJECT"}:
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


def compile_hardened_bridge(
    registry: Mapping[str, Any],
    target_bindings: Mapping[str, Any],
    root2: Mapping[str, Any],
    subject: Mapping[str, Any],
    result: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    subject_sha256 = _subject_digest(subject)

    required_result = {
        "schema",
        "status",
        "benchmark",
        "benchmark_version",
        "evaluator",
        "harness",
        "fallback_policy",
        "unit",
        "brain_score",
        "subject_sha256",
        "rating_epoch",
        "rating_epoch_verified",
        "opus55_reference_score",
        "evidence_sha256",
        "result_source_kind",
        "result_source_uri",
    }
    if not isinstance(result, Mapping) or set(result) != required_result:
        raise BridgeError("RESULT_FIELDS_INVALID")
    if result.get("schema") != RESULT_SCHEMA:
        raise BridgeError("RESULT_SCHEMA_MISMATCH")
    if result.get("status") != "VERIFIED_COMPARABLE_BRAIN_SCORE":
        raise BridgeError("RESULT_NOT_VERIFIED_COMPARABLE")
    for key in ("benchmark", "benchmark_version", "evaluator", "harness", "fallback_policy", "unit"):
        if result.get(key) != EXPECTED[key]:
            raise BridgeError("RESULT_TUPLE_MISMATCH:" + key)
    if result.get("subject_sha256") != subject_sha256:
        raise BridgeError("RESULT_SUBJECT_MISMATCH")
    if result.get("rating_epoch") != FROZEN_RATING_EPOCH:
        raise BridgeError("RESULT_RATING_EPOCH_MISMATCH")
    if result.get("rating_epoch_verified") is not True:
        raise BridgeError("RESULT_RATING_EPOCH_NOT_VERIFIED")
    if _finite_number(result.get("opus55_reference_score"), "RESULT_REFERENCE") != THRESHOLD:
        raise BridgeError("RESULT_OPUS55_REFERENCE_SCORE_MISMATCH")
    score = _finite_number(result.get("brain_score"), "RESULT_SCORE")

    evidence_sha256 = str(result.get("evidence_sha256") or "")
    if not _valid_sha256(evidence_sha256):
        raise BridgeError("RESULT_EVIDENCE_DIGEST_INVALID")
    source_kind = str(result.get("result_source_kind") or "")
    if source_kind not in {"OWNER_EVALUATOR", "INDEPENDENT_VERIFIER"}:
        raise BridgeError("RESULT_SOURCE_KIND_INVALID")
    source_uri = str(result.get("result_source_uri") or "")
    parsed = urlparse(source_uri)
    if parsed.scheme != "https" or not parsed.netloc:
        raise BridgeError("RESULT_SOURCE_URI_INVALID")
    if source_kind == "OWNER_EVALUATOR" and parsed.hostname not in {
        "artificialanalysis.ai",
        "www.artificialanalysis.ai",
    }:
        raise BridgeError("OWNER_RESULT_SOURCE_NOT_ARTIFICIAL_ANALYSIS")

    statement_sha256 = _sha({
        "claim": "AA_BRIEFCASE_FROZEN_EPOCH_RESULT_AUTHENTICATED",
        "benchmark": EXPECTED["benchmark"],
        "benchmark_version": EXPECTED["benchmark_version"],
        "evaluator": EXPECTED["evaluator"],
        "harness": EXPECTED["harness"],
        "fallback_policy": EXPECTED["fallback_policy"],
        "unit": EXPECTED["unit"],
        "rating_epoch": FROZEN_RATING_EPOCH,
        "subject_sha256": subject_sha256,
        "brain_score": score,
        "opus55_reference_score": THRESHOLD,
        "evidence_sha256": evidence_sha256,
        "result_source_kind": source_kind,
        "result_source_uri": source_uri,
    })
    if not _authority_ok(
        authority,
        statement_sha256=statement_sha256,
        evidence_sha256=evidence_sha256,
        result_source_kind=source_kind,
    ):
        raise BridgeError("RESULT_AUTHORITY_RECEIPT_INVALID")

    legacy_result = {
        "schema": "PROJECT_BRAIN_AA_BRIEFCASE_RESULT_V1",
        "status": "VERIFIED_COMPARABLE_BRAIN_SCORE",
        "independent_or_owner_verified": True,
        "benchmark": result["benchmark"],
        "benchmark_version": result["benchmark_version"],
        "evaluator": result["evaluator"],
        "harness": result["harness"],
        "fallback_policy": result["fallback_policy"],
        "unit": result["unit"],
        "brain_score": score,
        "subject_sha256": subject_sha256,
        "rating_epoch": result["rating_epoch"],
        "rating_epoch_verified": result["rating_epoch_verified"],
        "opus55_reference_score": result["opus55_reference_score"],
    }
    legacy = compile_v1_bridge(registry, target_bindings, root2, legacy_result)

    material = {
        "schema": SCHEMA,
        "status": legacy["status"],
        "shared_surface": legacy["shared_surface"],
        "brain_score": legacy["brain_score"],
        "threshold": legacy["threshold"],
        "unit": legacy["unit"],
        "rating_epoch": legacy["rating_epoch"],
        "opus55_reference_score": legacy["opus55_reference_score"],
        "subject_sha256": subject_sha256,
        "result_evidence_sha256": evidence_sha256,
        "authority_receipt_sha256": authority["receipt_sha256"],
        "authority_auth_artifact_sha256": authority["auth_artifact_sha256"],
        "predicate_results": legacy["predicate_results"],
        "single_result_reused_across_predicates": True,
        "legacy_v1_semantics_reused": True,
        "acceptance_credit_delta": 0,
        "promotion_authority": False,
        "terminal_authority": False,
    }
    return {**material, "bridge_verdict_sha256": _sha(material)}
