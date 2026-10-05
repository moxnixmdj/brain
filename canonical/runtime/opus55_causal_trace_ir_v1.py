from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from canonical.runtime.opus55_lossless_json_ir_v1 import (
    JsonValueCapsuleError,
    make_capsule,
    verify_and_decode_capsule,
)


TRACE_SCHEMA = "PROJECT_BRAIN_OPUS55_CAUSAL_TRACE_IR_V1"

ALLOWED_ACTORS = {
    "USER_OR_ENVIRONMENT",
    "OPUS55_POLICY",
    "EXTERNAL_EXECUTOR",
    "ANTHROPIC_WRAPPER_OR_CLASSIFIER",
    "FALLBACK_MODEL",
}

ALLOWED_CHANNELS = {
    "R0_EXTERNAL_OBSERVATION_OR_CONFIGURATION_IN",
    "R1_MODEL_VISIBLE_SEMANTIC_OUTPUT",
    "R2_MODEL_ACTION_OR_TOOL_INTENT",
    "R3_MODEL_OPAQUE_CONTINUATION_STATE",
    "R4_PROTOCOL_OR_TURN_CONTROL_SIGNAL",
}


class TraceIRError(ValueError):
    pass


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _event_hash(unsigned_event: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(unsigned_event)).hexdigest()


def new_trace(*, target: str = "CLAUDE_OPUS_5_5") -> dict[str, Any]:
    if not target:
        raise TraceIRError("EMPTY_TARGET")
    return {
        "schema": TRACE_SCHEMA,
        "target": target,
        "events": [],
        "head_sha256": None,
    }


def _verify_ref_list(
    refs: Iterable[str],
    *,
    prior_hashes: set[str],
    field: str,
) -> list[str]:
    normalized = list(refs)
    if len(normalized) != len(set(normalized)):
        raise TraceIRError(f"DUPLICATE_REFERENCE {field}")
    for ref in normalized:
        if ref not in prior_hashes:
            raise TraceIRError(f"UNKNOWN_OR_FORWARD_REFERENCE {field} {ref}")
    return normalized


def append_event(
    trace: dict[str, Any],
    value: Any,
    *,
    schema_path: str,
    actor: str,
    channel: str,
    actor_model_id: str | None = None,
    causal_parent_hashes: Iterable[str] | None = None,
    state_ref_hashes: Iterable[str] = (),
    raw_wire_bytes: bytes | None = None,
) -> str:
    verify_trace(trace)

    if actor not in ALLOWED_ACTORS:
        raise TraceIRError(f"UNKNOWN_ACTOR {actor}")
    if channel not in ALLOWED_CHANNELS:
        raise TraceIRError(f"UNKNOWN_CAUSAL_CHANNEL {channel}")
    if actor == "FALLBACK_MODEL" and not actor_model_id:
        raise TraceIRError("FALLBACK_MODEL_REQUIRES_MODEL_ID")

    events = trace["events"]
    prior_hashes = {event["event_sha256"] for event in events}
    ledger_parent = events[-1]["event_sha256"] if events else None

    if causal_parent_hashes is None:
        causal_parents = [ledger_parent] if ledger_parent is not None else []
    else:
        causal_parents = _verify_ref_list(
            causal_parent_hashes,
            prior_hashes=prior_hashes,
            field="causal_parent_hashes",
        )

    state_refs = _verify_ref_list(
        state_ref_hashes,
        prior_hashes=prior_hashes,
        field="state_ref_hashes",
    )

    capsule = make_capsule(
        value,
        schema_path=schema_path,
        actor=actor,
        channel=channel,
        raw_wire_bytes=raw_wire_bytes,
    )

    unsigned_event: dict[str, Any] = {
        "ordinal": len(events),
        "ledger_parent_sha256": ledger_parent,
        "causal_parent_hashes": causal_parents,
        "state_ref_hashes": state_refs,
        "actor_model_id": actor_model_id,
        "capsule": capsule,
    }
    event_sha = _event_hash(unsigned_event)
    event = dict(unsigned_event)
    event["event_sha256"] = event_sha

    events.append(event)
    trace["head_sha256"] = event_sha
    return event_sha


def verify_trace(trace: dict[str, Any]) -> None:
    if trace.get("schema") != TRACE_SCHEMA:
        raise TraceIRError("WRONG_TRACE_SCHEMA")
    if not isinstance(trace.get("target"), str) or not trace["target"]:
        raise TraceIRError("INVALID_TARGET")
    events = trace.get("events")
    if not isinstance(events, list):
        raise TraceIRError("EVENTS_NOT_LIST")

    prior_hashes: set[str] = set()
    previous_hash: str | None = None

    for expected_ordinal, event in enumerate(events):
        if not isinstance(event, dict):
            raise TraceIRError(f"EVENT_NOT_OBJECT {expected_ordinal}")

        claimed_hash = event.get("event_sha256")
        if not isinstance(claimed_hash, str):
            raise TraceIRError(f"MISSING_EVENT_HASH {expected_ordinal}")

        unsigned = dict(event)
        unsigned.pop("event_sha256", None)
        actual_hash = _event_hash(unsigned)
        if actual_hash != claimed_hash:
            raise TraceIRError(
                f"EVENT_HASH_MISMATCH {expected_ordinal} {actual_hash} != {claimed_hash}"
            )

        if event.get("ordinal") != expected_ordinal:
            raise TraceIRError(f"ORDINAL_MISMATCH {expected_ordinal}")

        if event.get("ledger_parent_sha256") != previous_hash:
            raise TraceIRError(f"LEDGER_PARENT_MISMATCH {expected_ordinal}")

        actor = event.get("capsule", {}).get("actor")
        channel = event.get("capsule", {}).get("channel")
        if actor not in ALLOWED_ACTORS:
            raise TraceIRError(f"UNKNOWN_ACTOR {actor}")
        if channel not in ALLOWED_CHANNELS:
            raise TraceIRError(f"UNKNOWN_CAUSAL_CHANNEL {channel}")
        if actor == "FALLBACK_MODEL" and not event.get("actor_model_id"):
            raise TraceIRError("FALLBACK_MODEL_REQUIRES_MODEL_ID")

        _verify_ref_list(
            event.get("causal_parent_hashes", []),
            prior_hashes=prior_hashes,
            field="causal_parent_hashes",
        )
        _verify_ref_list(
            event.get("state_ref_hashes", []),
            prior_hashes=prior_hashes,
            field="state_ref_hashes",
        )

        try:
            verify_and_decode_capsule(event["capsule"])
        except (JsonValueCapsuleError, KeyError, TypeError) as exc:
            raise TraceIRError(
                f"INVALID_VALUE_CAPSULE {expected_ordinal}: {exc}"
            ) from exc

        prior_hashes.add(claimed_hash)
        previous_hash = claimed_hash

    if trace.get("head_sha256") != previous_hash:
        raise TraceIRError("HEAD_MISMATCH")


def trace_event_index(trace: dict[str, Any]) -> dict[str, dict[str, Any]]:
    verify_trace(trace)
    return {event["event_sha256"]: event for event in trace["events"]}
