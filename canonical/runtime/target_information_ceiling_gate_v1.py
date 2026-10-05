"""Fail-closed target-information elimination gate for objective-top receipts.

This gate issues routing certificates only. It never grants acceptance, capability,
family, ownership, execution, promotion, or fresh-reality authority.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from typing import Any

SCHEMA = "PROJECT_BRAIN_TARGET_INFORMATION_CEILING_GATE_V1"
CERT_SCHEMA = "PROJECT_BRAIN_TARGET_INFORMATION_CEILING_CERTIFICATE_V1"
_SHA = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")


class CeilingGateError(ValueError):
    pass


def _tok(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CeilingGateError(label + "_INVALID")
    return value.strip()


def _sha(value: Any, label: str) -> str:
    text = _tok(value, label).lower()
    if _SHA.fullmatch(text) is None:
        raise CeilingGateError(label + "_INVALID")
    return text


def _decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool):
        raise CeilingGateError(label + "_INVALID")
    try:
        out = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise CeilingGateError(label + "_INVALID") from None
    if not out.is_finite():
        raise CeilingGateError(label + "_NONFINITE")
    return out


def _receipt(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CeilingGateError(label + "_INVALID")
    required_true = (
        "scope_complete",
        "acceptance_preorder_monotone",
        "metric_bounds_objective",
        "independent_or_objective",
    )
    for key in required_true:
        if value.get(key) is not True:
            raise CeilingGateError(label + "_" + key.upper() + "_NOT_TRUE")
    return {
        "path": _tok(value.get("path"), label + "_PATH"),
        "git_blob_sha": _sha(value.get("git_blob_sha"), label + "_GIT_BLOB_SHA"),
        **{key: True for key in required_true},
    }


def _normalize_coordinate(raw: Any, index: int) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise CeilingGateError(f"COORDINATE_{index}_INVALID")
    direction = _tok(raw.get("direction"), f"COORDINATE_{index}_DIRECTION").lower()
    if direction not in {"benefit", "loss"}:
        raise CeilingGateError(f"COORDINATE_{index}_DIRECTION_UNSUPPORTED")
    lower = _decimal(raw.get("lower_bound"), f"COORDINATE_{index}_LOWER_BOUND")
    upper = _decimal(raw.get("upper_bound"), f"COORDINATE_{index}_UPPER_BOUND")
    value = _decimal(raw.get("brain_value"), f"COORDINATE_{index}_BRAIN_VALUE")
    if lower > upper:
        raise CeilingGateError(f"COORDINATE_{index}_INVERTED_BOUNDS")
    if not (lower <= value <= upper):
        raise CeilingGateError(f"COORDINATE_{index}_VALUE_OUT_OF_BOUNDS")
    target_extreme = upper if direction == "benefit" else lower
    return {
        "name": _tok(raw.get("name"), f"COORDINATE_{index}_NAME"),
        "direction": direction,
        "lower_bound": str(lower),
        "upper_bound": str(upper),
        "brain_value": str(value),
        "required_extreme": str(target_extreme),
        "at_objective_top": value == target_extreme,
    }


def _canonical_sha256(value: Any) -> str:
    data = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def verify_ceiling_certificate(cert: Mapping[str, Any]) -> dict[str, Any]:
    """Return a routing certificate that target output is unnecessary, or fail closed."""
    try:
        if not isinstance(cert, Mapping):
            raise CeilingGateError("CERT_NOT_OBJECT")
        if cert.get("schema") != CERT_SCHEMA:
            raise CeilingGateError("CERT_SCHEMA_MISMATCH")

        predicate_id = _tok(cert.get("predicate_id"), "PREDICATE_ID")
        parent_cut_sha = _sha(
            cert.get("parent_target_information_cut_sha"),
            "PARENT_CUT_SHA",
        )
        scope_id = _tok(cert.get("scope_id"), "SCOPE_ID")
        semantics = _receipt(cert.get("semantic_receipt"), "SEMANTIC_RECEIPT")
        coords_raw = cert.get("coordinates")
        if (
            not isinstance(coords_raw, Sequence)
            or isinstance(coords_raw, (str, bytes))
            or not coords_raw
        ):
            raise CeilingGateError("COORDINATES_INVALID")
        coords = [_normalize_coordinate(row, i) for i, row in enumerate(coords_raw)]
        names = [row["name"] for row in coords]
        if len(names) != len(set(names)):
            raise CeilingGateError("COORDINATE_NAME_DUPLICATE")

        if not all(row["at_objective_top"] for row in coords):
            return {
                "schema": SCHEMA,
                "status": "OPEN__TARGET_INFORMATION_NOT_ELIMINATED",
                "predicate_id": predicate_id,
                "scope_id": scope_id,
                "reason": "BRAIN_NOT_AT_COMPONENTWISE_OBJECTIVE_TOP",
                "coordinates": coords,
                "acceptance_credit_delta": 0,
                "fresh_reality_authority": False,
            }

        normalized = {
            "schema": CERT_SCHEMA,
            "predicate_id": predicate_id,
            "parent_target_information_cut_sha": parent_cut_sha,
            "scope_id": scope_id,
            "semantic_receipt": semantics,
            "coordinates": coords,
        }
        cert_sha = _canonical_sha256(normalized)
        return {
            "schema": SCHEMA,
            "status": "PASS__TARGET_OUTPUT_NOT_REQUIRED_FOR_THIS_PREDICATE_SCOPE",
            "predicate_id": predicate_id,
            "scope_id": scope_id,
            "certificate_sha256": cert_sha,
            "reason": "COMPONENTWISE_OBJECTIVE_TOP_DOMINATES_EVERY_ADMISSIBLE_TARGET_VALUE_UNDER_BOUND_MONOTONE_SEMANTICS",
            "coordinates": coords,
            "target_output_required": False,
            "predicate_closed": False,
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
            "fresh_reality_authority": False,
        }
