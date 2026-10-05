"""Generic lossless protocol-value IR for the schema-closed trace route.

This module proves a narrow representation property only: supported finite
protocol values can be encoded into a tagged Brain-owned IR and reconstructed
exactly. It does not decide Sigma_T schema membership and does not grant
behavioral refinement, acceptance, capability, ownership, or execution credit.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_PROTOCOL_IR_LOSSLESS_ENCODER_V1"


class ProtocolIRError(ValueError):
    pass


def _exact_keys(value: Mapping[str, Any], required: set[str]) -> None:
    if set(value.keys()) != required:
        raise ProtocolIRError(
            "IR_KEYS_INVALID:expected="
            + ",".join(sorted(required))
            + ":actual="
            + ",".join(sorted(str(k) for k in value.keys()))
        )


def encode(value: Any) -> dict[str, Any]:
    """Encode a supported finite JSON-like protocol value losslessly."""
    if value is None:
        return {"k": "null"}

    # bool must precede int because bool subclasses int in Python.
    if isinstance(value, bool):
        return {"k": "bool", "v": value}

    if isinstance(value, int):
        return {"k": "int", "v": str(value)}

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ProtocolIRError("NONFINITE_FLOAT_UNSUPPORTED")
        return {"k": "float", "v": value.hex()}

    if isinstance(value, str):
        return {"k": "str", "v": value}

    if isinstance(value, list):
        return {"k": "list", "v": [encode(item) for item in value]}

    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise ProtocolIRError("NONSTRING_RECORD_KEY")
        return {
            "k": "obj",
            "v": [[key, encode(item)] for key, item in value.items()],
        }

    raise ProtocolIRError("UNSUPPORTED_VALUE_TYPE:" + type(value).__name__)


def decode(ir: Any) -> Any:
    """Decode a tagged IR value, rejecting malformed or ambiguous encodings."""
    if not isinstance(ir, Mapping):
        raise ProtocolIRError("IR_NOT_OBJECT")

    kind = ir.get("k")
    if kind == "null":
        _exact_keys(ir, {"k"})
        return None

    if kind == "bool":
        _exact_keys(ir, {"k", "v"})
        if not isinstance(ir["v"], bool):
            raise ProtocolIRError("IR_BOOL_INVALID")
        return ir["v"]

    if kind == "int":
        _exact_keys(ir, {"k", "v"})
        raw = ir["v"]
        if not isinstance(raw, str) or not raw:
            raise ProtocolIRError("IR_INT_INVALID")
        try:
            parsed = int(raw, 10)
        except Exception as exc:
            raise ProtocolIRError("IR_INT_INVALID") from exc
        # Canonical decimal text prevents multiple encodings of one integer.
        if str(parsed) != raw:
            raise ProtocolIRError("IR_INT_NONCANONICAL")
        return parsed

    if kind == "float":
        _exact_keys(ir, {"k", "v"})
        raw = ir["v"]
        if not isinstance(raw, str) or not raw:
            raise ProtocolIRError("IR_FLOAT_INVALID")
        try:
            parsed = float.fromhex(raw)
        except Exception as exc:
            raise ProtocolIRError("IR_FLOAT_INVALID") from exc
        if not math.isfinite(parsed):
            raise ProtocolIRError("IR_FLOAT_NONFINITE")
        if parsed.hex() != raw:
            raise ProtocolIRError("IR_FLOAT_NONCANONICAL")
        return parsed

    if kind == "str":
        _exact_keys(ir, {"k", "v"})
        if not isinstance(ir["v"], str):
            raise ProtocolIRError("IR_STRING_INVALID")
        return ir["v"]

    if kind == "list":
        _exact_keys(ir, {"k", "v"})
        raw = ir["v"]
        if not isinstance(raw, list):
            raise ProtocolIRError("IR_LIST_INVALID")
        return [decode(item) for item in raw]

    if kind == "obj":
        _exact_keys(ir, {"k", "v"})
        raw = ir["v"]
        if not isinstance(raw, list):
            raise ProtocolIRError("IR_OBJECT_INVALID")
        out: dict[str, Any] = {}
        for entry in raw:
            if (
                not isinstance(entry, list)
                or len(entry) != 2
                or not isinstance(entry[0], str)
            ):
                raise ProtocolIRError("IR_OBJECT_ENTRY_INVALID")
            key = entry[0]
            if key in out:
                raise ProtocolIRError("IR_OBJECT_DUPLICATE_KEY:" + key)
            out[key] = decode(entry[1])
        return out

    raise ProtocolIRError("IR_KIND_UNKNOWN:" + repr(kind))


def certify_roundtrip(value: Any) -> dict[str, Any]:
    """Return a zero-credit left-inverse representation verdict."""
    try:
        ir = encode(value)
        recovered = decode(ir)
        # Python equality does not distinguish the sign of zero, so compare the
        # encoded canonical form after decoding as well.
        left_inverse = recovered == value and encode(recovered) == ir
        if not left_inverse:
            raise ProtocolIRError("LEFT_INVERSE_MISMATCH")
        return {
            "schema": SCHEMA,
            "status": "PASS__LEFT_INVERTIBLE_REPRESENTATION",
            "left_inverse_proved_for_supplied_value": True,
            "ir": ir,
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__REPRESENTATION_NOT_PROVED",
            "left_inverse_proved_for_supplied_value": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "fresh_reality_authority": False,
        }
