"""Fail-closed structural verifier for opaque-state observational quotienting.

This module proves only alpha-equivalence of traces after opaque carrier bytes/IDs
are quotiented while preserving carrier kind, actor, identity, order and emit/echo linkage.
It does not prove that a carrier is semantically opaque or that any Brain route
implements the resulting abstract transition relation.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_OPUS55_OPAQUE_STATE_OBSERVATIONAL_QUOTIENT_V1"

SEMANTIC_TYPES = {
    "TEXT",
    "VISIBLE_THINKING_SUMMARY",
    "TOOL_USE",
    "TOOL_RESULT",
    "STOP",
    "CONTROL",
}
OPAQUE_TYPES = {"OPAQUE_STATE_EMIT", "OPAQUE_STATE_ECHO"}


class QuotientError(ValueError):
    pass


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise QuotientError(label + "_INVALID")
    return value


def _events(trace: Any) -> list[Mapping[str, Any]]:
    if not isinstance(trace, Sequence) or isinstance(trace, (str, bytes, bytearray)):
        raise QuotientError("TRACE_INVALID")
    out: list[Mapping[str, Any]] = []
    for i, event in enumerate(trace):
        if not isinstance(event, Mapping):
            raise QuotientError(f"EVENT_{i}_NOT_OBJECT")
        out.append(event)
    return out


def project_trace(trace: Any) -> list[dict[str, Any]]:
    """Project a raw trace to its capability-relevant observational quotient.

    Opaque state carriers are alpha-renamed by first emission while preserving:
    carrier kind, actor, emit/echo operation, equality/inequality, and use order.
    Unknown event types and echo-before-emit fail closed.
    """
    carrier_map: dict[tuple[str, str, str], str] = {}
    projected: list[dict[str, Any]] = []

    for i, event in enumerate(_events(trace)):
        typ = _token(event.get("type"), f"EVENT_{i}_TYPE")
        actor = _token(event.get("actor"), f"EVENT_{i}_ACTOR")

        if typ in SEMANTIC_TYPES:
            if "payload" not in event:
                raise QuotientError(f"EVENT_{i}_SEMANTIC_PAYLOAD_MISSING")
            projected.append({
                "type": typ,
                "actor": actor,
                "payload": event["payload"],
            })
            continue

        if typ not in OPAQUE_TYPES:
            raise QuotientError(f"EVENT_{i}_UNKNOWN_TYPE:{typ}")

        kind = _token(event.get("carrier_kind"), f"EVENT_{i}_CARRIER_KIND")
        raw_id = _token(event.get("carrier_id"), f"EVENT_{i}_CARRIER_ID")
        key = (actor, kind, raw_id)

        if typ == "OPAQUE_STATE_EMIT":
            if key in carrier_map:
                raise QuotientError(f"EVENT_{i}_DUPLICATE_CARRIER_EMIT")
            carrier_map[key] = f"carrier_{len(carrier_map)}"
        else:
            if key not in carrier_map:
                raise QuotientError(f"EVENT_{i}_ECHO_BEFORE_EMIT")

        projected.append({
            "type": typ,
            "actor": actor,
            "carrier_kind": kind,
            "carrier": carrier_map[key],
        })

    return projected


def verify_observational_equivalence(left: Any, right: Any) -> dict[str, Any]:
    try:
        lp = project_trace(left)
        rp = project_trace(right)
        if lp != rp:
            return {
                "schema": SCHEMA,
                "status": "NOT_EQUIVALENT",
                "left_projection": lp,
                "right_projection": rp,
                "capability_credit_delta": 0,
            }
        return {
            "schema": SCHEMA,
            "status": "EQUIVALENT",
            "projection": lp,
            "opaque_bytes_or_ids_required_to_match": False,
            "opaque_identity_order_linkage_preserved": True,
            "capability_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc),
            "capability_credit_delta": 0,
        }
