"""Constructive Brain cutpoint state for acceptance-quotient simulation.

The cutpoint conservatively embeds the entire verified composition capsule.
This intentionally sacrifices some state compression to make cross-role
state/evidence retention mechanical once a separate scope-complete channel
no-bypass receipt exists.

This module verifies certificate shape and capsule integrity only. It does not
prove the external no-bypass receipt, acceptance completeness, macrostep
realizability, or terminal noninferiority.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from typing import Any

from canonical.runtime.composition_state_capsule_v2 import verify_capsule

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_CUTPOINT_CAPSULE_QUOTIENT_V1"


class CutpointError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CutpointError("NON_CANONICALIZABLE_VALUE") from exc


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CutpointError(label + "_INVALID")
    return value.strip()


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CutpointError(label + "_INVALID")
    out = copy.deepcopy(dict(value))
    _canon(out)
    return out


def _channel_receipt(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CutpointError("CHANNEL_RECEIPT_INVALID")
    required_true = (
        "scope_complete",
        "cross_role_state_edges_capsule_dominated",
        "acceptance_relevant_evidence_edges_capsule_dominated",
        "unknown_dynamic_edges_fail_closed",
        "exact_runtime_identity_bound",
        "independent_or_objective",
    )
    out = {
        "path": _token(value.get("path"), "CHANNEL_RECEIPT_PATH"),
        "git_blob_sha": _token(value.get("git_blob_sha"), "CHANNEL_RECEIPT_SHA"),
    }
    for field in required_true:
        if value.get(field) is not True:
            raise CutpointError("CHANNEL_RECEIPT_" + field.upper() + "_NOT_TRUE")
        out[field] = True
    return out


def compile_brain_cutpoint(
    *,
    capsule: Mapping[str, Any],
    acceptance_facts: Mapping[str, Any],
    scope_authority_facts: Mapping[str, Any],
    terminal_facts: Mapping[str, Any],
    channel_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile a conservative Brain quotient/precondition cutpoint."""
    capsule_verdict = verify_capsule(capsule)
    if capsule_verdict.get("status") != "PASS":
        raise CutpointError(
            "CAPSULE_NOT_VERIFIED:" + str(capsule_verdict.get("reason", "UNKNOWN"))
        )

    receipt = _channel_receipt(channel_receipt)
    quotient = {
        "acceptance_facts": _object(acceptance_facts, "ACCEPTANCE_FACTS"),
        "scope_authority_facts": _object(
            scope_authority_facts, "SCOPE_AUTHORITY_FACTS"
        ),
        "terminal_facts": _object(terminal_facts, "TERMINAL_FACTS"),
        # Full value, not only head_hash. This avoids relying on hash
        # injectivity for the semantic retention argument.
        "composition_capsule_v2": copy.deepcopy(dict(capsule)),
        "channel_receipt_binding": receipt,
    }
    canonical = _canon(quotient)
    return {
        "schema": SCHEMA,
        "status": "PASS__CONSERVATIVE_CUTPOINT_CONSTRUCTED",
        "quotient": quotient,
        "quotient_sha256": hashlib.sha256(canonical).hexdigest(),
        "full_capsule_retained": True,
        "cross_role_hidden_debt_premise_shape_satisfied": True,
        "proof_boundary": (
            "CONDITIONAL_ON_EXTERNAL_SCOPE_COMPLETE_NO_BYPASS_RECEIPT; "
            "NO_ACCEPTANCE_COMPLETENESS_OR_MACROSTEP_REALIZABILITY_CREDIT"
        ),
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
    }


def verify_cutpoint(value: Mapping[str, Any]) -> dict[str, Any]:
    """Fail-closed structural verification of a compiled cutpoint."""
    try:
        if not isinstance(value, Mapping):
            raise CutpointError("CUTPOINT_NOT_OBJECT")
        if value.get("schema") != SCHEMA:
            raise CutpointError("SCHEMA_MISMATCH")
        if value.get("status") != "PASS__CONSERVATIVE_CUTPOINT_CONSTRUCTED":
            raise CutpointError("STATUS_NOT_PASS")

        quotient = value.get("quotient")
        if not isinstance(quotient, Mapping):
            raise CutpointError("QUOTIENT_INVALID")

        expected_fields = {
            "acceptance_facts",
            "scope_authority_facts",
            "terminal_facts",
            "composition_capsule_v2",
            "channel_receipt_binding",
        }
        if set(quotient.keys()) != expected_fields:
            raise CutpointError("QUOTIENT_FIELDS_INVALID")

        _object(quotient["acceptance_facts"], "ACCEPTANCE_FACTS")
        _object(quotient["scope_authority_facts"], "SCOPE_AUTHORITY_FACTS")
        _object(quotient["terminal_facts"], "TERMINAL_FACTS")
        _channel_receipt(quotient["channel_receipt_binding"])

        capsule_verdict = verify_capsule(quotient["composition_capsule_v2"])
        if capsule_verdict.get("status") != "PASS":
            raise CutpointError(
                "CAPSULE_NOT_VERIFIED:" + str(capsule_verdict.get("reason", "UNKNOWN"))
            )

        expected = hashlib.sha256(_canon(dict(quotient))).hexdigest()
        if value.get("quotient_sha256") != expected:
            raise CutpointError("QUOTIENT_DIGEST_MISMATCH")
        if value.get("full_capsule_retained") is not True:
            raise CutpointError("FULL_CAPSULE_RETENTION_NOT_TRUE")
        if value.get("cross_role_hidden_debt_premise_shape_satisfied") is not True:
            raise CutpointError("HIDDEN_DEBT_SHAPE_NOT_TRUE")

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "quotient_sha256": expected,
            "full_capsule_retained": True,
            "external_no_bypass_receipt_still_load_bearing": True,
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }
