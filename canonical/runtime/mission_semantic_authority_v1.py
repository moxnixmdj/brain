from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SEMANTIC_FIELDS = (
    "real_objective",
    "optimization_objective",
    "compounding_requirement",
    "knowledge_policy",
    "opus_5_5_role",
    "benchmark_role",
    "checkpoint_rule",
    "correctness_rule",
    "spend_rule",
    "mission_terminality",
    "option_preservation_requirement",
    "future_technology_compatibility",
)
SOURCE_PATH = "canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"


def semantic_projection(source: Mapping[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for field in SEMANTIC_FIELDS:
        value = source.get(field)
        if not isinstance(value, str) or not value:
            raise ValueError("MISSION_SEMANTIC_FIELD_INVALID:" + field)
        out[field] = value
    return out


def semantic_sha256(source: Mapping[str, Any]) -> str:
    raw = json.dumps(
        semantic_projection(source),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate(
    pointer: Mapping[str, Any],
    source: Mapping[str, Any],
    *,
    source_git_blob_sha: str,
    expected_source_git_blob_sha: str,
    expected_semantics_sha256: str,
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        digest = semantic_sha256(source)
    except Exception as exc:
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_credit_delta": 0,
        }

    if source_git_blob_sha != expected_source_git_blob_sha:
        errors.append("MISSION_SOURCE_BLOB_DRIFT")
    if digest != expected_semantics_sha256:
        errors.append("MISSION_SEMANTICS_DRIFT")

    auth = pointer.get("authoritative_source") if isinstance(pointer, Mapping) else None
    if not isinstance(auth, Mapping) or auth.get("path") != SOURCE_PATH:
        errors.append("MISSION_POINTER_SOURCE_PATH_DRIFT")
    if pointer.get("real_objective") != source.get("real_objective"):
        errors.append("MISSION_POINTER_OBJECTIVE_DRIFT")
    if pointer.get("opus_5_5_role") != source.get("opus_5_5_role"):
        errors.append("MISSION_POINTER_CHECKPOINT_ROLE_DRIFT")

    return {
        "pass": not errors,
        "status": "PASS__MISSION_SEMANTICS_CURRENT" if not errors else "FAIL_CLOSED",
        "errors": errors,
        "mission_semantics_sha256": digest,
        "pointer_blob_is_semantic_authority": False,
        "terminal_credit_delta": 0,
    }
