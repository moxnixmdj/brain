"""Executable binding gate for field-scoped zero-reality verification reuse.

Semantic currentness alone is insufficient. Reuse is admitted only when:
1. the frozen pure-field capsule remains semantically current;
2. an exact pure+sealed execution binds the same consumer, projection, and result;
3. an independent prior result-verification receipt binds that same capsule; and
4. no dynamic or external semantic dependency remains open.

The granted authority is deliberately narrow: reuse of the prior zero-reality
verification result. This module grants no execution, promotion, fresh-reality,
acceptance, capability, ownership, or terminal authority.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_FIELD_SCOPED_ZERO_REALITY_REUSE_GATE_V1"
CAPSULE_SCHEMA = "PROJECT_BRAIN_PURE_FIELD_PROJECTION_CAPSULE_V1"
CAPSULE_STATUS = "PASS__PURE_FIELD_PROJECTION_SEMANTIC_CAPSULE"
CURRENTNESS_SCHEMA = "PROJECT_BRAIN_PURE_FIELD_PROJECTION_CURRENTNESS_V1"
CURRENTNESS_STATUS = "PASS__PURE_FIELD_PROJECTION_SEMANTIC_IDENTITY_CURRENT"
SEALED_SCHEMA = "PROJECT_BRAIN_PURE_SEALED_PROJECTION_CONSUMER_V1"
SEALED_STATUS = "PASS__PURE_AND_SEALED_FIELD_PROJECTION_CONSUMER"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "zero_reality_verification_reuse_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        **extra,
    }


def verify_reuse(
    *,
    frozen_capsule: Mapping[str, Any],
    currentness_receipt: Mapping[str, Any],
    pure_sealed_execution_receipt: Mapping[str, Any],
    independent_result_verification: Mapping[str, Any],
) -> dict[str, Any]:
    try:
        if (
            not isinstance(frozen_capsule, Mapping)
            or frozen_capsule.get("schema") != CAPSULE_SCHEMA
            or frozen_capsule.get("pass") is not True
            or frozen_capsule.get("status") != CAPSULE_STATUS
        ):
            return _fail("FROZEN_CAPSULE_INVALID")

        semantic_identity = frozen_capsule.get("semantic_identity_sha256")
        consumer_source_sha = frozen_capsule.get("consumer_source_sha256")
        projection_bundle_sha = frozen_capsule.get("projection_bundle_sha256")
        consumer_result_sha = frozen_capsule.get("consumer_result_sha256")
        consumer_result = frozen_capsule.get("consumer_result")
        for label, digest in (
            ("SEMANTIC_IDENTITY", semantic_identity),
            ("CONSUMER_SOURCE", consumer_source_sha),
            ("PROJECTION_BUNDLE", projection_bundle_sha),
            ("CONSUMER_RESULT", consumer_result_sha),
        ):
            if not _valid_sha256(digest):
                return _fail("FROZEN_" + label + "_SHA256_INVALID")
        if not isinstance(consumer_result, Mapping):
            return _fail("FROZEN_CONSUMER_RESULT_INVALID")
        if _sha256(dict(consumer_result)) != consumer_result_sha:
            return _fail("FROZEN_CONSUMER_RESULT_DIGEST_MISMATCH")

        if (
            not isinstance(currentness_receipt, Mapping)
            or currentness_receipt.get("schema") != CURRENTNESS_SCHEMA
            or currentness_receipt.get("pass") is not True
            or currentness_receipt.get("status") != CURRENTNESS_STATUS
            or currentness_receipt.get("semantic_identity_current") is not True
        ):
            return _fail("CURRENTNESS_RECEIPT_INVALID")
        if (
            currentness_receipt.get("frozen_semantic_identity_sha256")
            != semantic_identity
            or currentness_receipt.get("current_semantic_identity_sha256")
            != semantic_identity
            or currentness_receipt.get("pure_consumer_source_unchanged") is not True
        ):
            return _fail("CURRENTNESS_CAPSULE_BINDING_MISMATCH")

        sealed = pure_sealed_execution_receipt
        if (
            not isinstance(sealed, Mapping)
            or sealed.get("schema") != SEALED_SCHEMA
            or sealed.get("pass") is not True
            or sealed.get("status") != SEALED_STATUS
        ):
            return _fail("PURE_SEALED_EXECUTION_RECEIPT_INVALID")
        if sealed.get("consumer_source_sha256") != consumer_source_sha:
            return _fail("SEALED_CONSUMER_SOURCE_BINDING_MISMATCH")
        if sealed.get("projection_bundle_sha256") != projection_bundle_sha:
            return _fail("SEALED_PROJECTION_BINDING_MISMATCH")
        sealed_result = sealed.get("consumer_result")
        if not isinstance(sealed_result, Mapping):
            return _fail("SEALED_CONSUMER_RESULT_INVALID")
        if _sha256(dict(sealed_result)) != consumer_result_sha:
            return _fail("SEALED_CONSUMER_RESULT_BINDING_MISMATCH")
        if sealed.get("helper_files_allowed") is not False:
            return _fail("SEALED_HELPER_FILE_EXCLUSION_UNPROVED")
        if sealed.get("undeclared_host_repository_reads_available") is not False:
            return _fail("SEALED_UNDECLARED_READ_EXCLUSION_UNPROVED")

        independent = independent_result_verification
        if not isinstance(independent, Mapping):
            return _fail("INDEPENDENT_RESULT_VERIFICATION_MISSING")
        if (
            independent.get("pass") is not True
            or independent.get("independently_verified") is not True
            or not _valid_sha256(independent.get("sha256"))
        ):
            return _fail("INDEPENDENT_RESULT_VERIFICATION_INVALID")
        if independent.get("semantic_identity_sha256") != semantic_identity:
            return _fail("INDEPENDENT_SEMANTIC_IDENTITY_BINDING_MISMATCH")
        if independent.get("consumer_result_sha256") != consumer_result_sha:
            return _fail("INDEPENDENT_RESULT_DIGEST_BINDING_MISMATCH")
        if independent.get("external_unbound_dependencies") != []:
            return _fail("INDEPENDENT_EXTERNAL_DEPENDENCIES_OPEN")
        if independent.get("dynamic_or_implicit_dependencies") != []:
            return _fail("INDEPENDENT_DYNAMIC_DEPENDENCIES_OPEN")

        sealed_receipt_sha = _sha256(dict(sealed))
        core = {
            "semantic_identity_sha256": semantic_identity,
            "consumer_source_sha256": consumer_source_sha,
            "projection_bundle_sha256": projection_bundle_sha,
            "consumer_result_sha256": consumer_result_sha,
            "independent_result_verification_sha256": independent["sha256"],
            "pure_sealed_execution_receipt_sha256": sealed_receipt_sha,
        }
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": (
                "PASS__FIELD_SCOPED_ZERO_REALITY_VERIFICATION_REUSE_BOUND__"
                "LIVE_SCHEDULER_RECHECK_STILL_REQUIRED"
            ),
            "reason": None,
            **core,
            "reuse_receipt_sha256": _sha256(core),
            "zero_reality_verification_reuse_authority": True,
            "scheduler_replan_required": bool(
                currentness_receipt.get("scheduler_replan_required_on_global_epoch_drift")
            ),
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "terminal_credit_delta": 0,
            "rule": (
                "REUSE_REQUIRES_CURRENT_SEMANTIC_IDENTITY_PLUS_EXACT_PURE_SEALED_"
                "RESULT_BINDING_PLUS_PRIOR_INDEPENDENT_RESULT_VERIFICATION__"
                "CONSEQUENTIAL_ACTIONS_REQUIRE_SEPARATE_LIVE_AUTHORITY"
            ),
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
