"""Fail-closed lossless encoder for the frozen Opus 5.5 interaction schema.

This module solves only representation totality: every member of the pinned stable
and beta interaction-schema sets can be embedded losslessly in Brain-owned IR.
It does not infer actor identity, target semantics, capability, or noninferiority.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = ROOT / "canonical/governance/OPUS55_FROZEN_INTERACTION_SCHEMA_SNAPSHOT_20261005_V1.json"
IR_SCHEMA = "PROJECT_BRAIN_OPUS55_TYPED_INTERACTION_IR_V1"

ACTORS = {
    "OPUS55_POLICY",
    "CLIENT_EXECUTOR",
    "SERVER_EXECUTOR",
    "FALLBACK_POLICY",
    "PLATFORM_WRAPPER",
    "ENVIRONMENT",
    "UNKNOWN",
}

CHANNEL_KEYS = {
    "stable.response_content": ("stable_schema", "response_content_union"),
    "stable.request_content": ("stable_schema", "request_content_union"),
    "stable.tool_definition": ("stable_schema", "tool_union"),
    "stable.stop_reason": ("stable_schema", "stop_reason_union"),
    "stable.request_control": ("stable_schema", "all_request_control_fields"),
    "beta.response_content": ("beta_schema", "response_content_union"),
    "beta.request_content": ("beta_schema", "request_content_union"),
    "beta.tool_definition": ("beta_schema", "tool_union"),
    "beta.stop_reason": ("beta_schema", "stop_reason_union"),
    "beta.request_control": ("beta_schema", "all_request_control_fields"),
}

class EncoderError(ValueError):
    pass

def _snapshot(root: Path = ROOT) -> dict[str, Any]:
    try:
        value = json.loads((root / SNAPSHOT_PATH.relative_to(ROOT)).read_text())
    except Exception as exc:
        raise EncoderError("SNAPSHOT_UNREADABLE") from exc
    if not isinstance(value, dict):
        raise EncoderError("SNAPSHOT_NOT_OBJECT")
    return value

def schema_members(channel: str, root: Path = ROOT) -> tuple[str, ...]:
    if channel not in CHANNEL_KEYS:
        raise EncoderError("UNKNOWN_CHANNEL:" + str(channel))
    section, key = CHANNEL_KEYS[channel]
    values = _snapshot(root).get(section, {}).get(key)
    if not isinstance(values, list) or not values or any(not isinstance(x, str) or not x for x in values):
        raise EncoderError("INVALID_MEMBER_SET:" + channel)
    if len(values) != len(set(values)):
        raise EncoderError("DUPLICATE_MEMBER:" + channel)
    return tuple(values)

def _json_lossless(value: Any) -> Any:
    try:
        encoded = json.dumps(value, allow_nan=False, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return json.loads(encoded)
    except Exception as exc:
        raise EncoderError("NON_JSON_PAYLOAD") from exc

def encode(channel: str, schema_member: str, payload: Any, *, actor: str) -> dict[str, Any]:
    if schema_member not in schema_members(channel):
        raise EncoderError("UNKNOWN_SCHEMA_MEMBER:" + channel + ":" + str(schema_member))
    if actor not in ACTORS:
        raise EncoderError("UNKNOWN_ACTOR:" + str(actor))
    preserved = _json_lossless(payload)
    return {
        "schema": IR_SCHEMA,
        "channel": channel,
        "schema_member": schema_member,
        "actor": actor,
        "payload": preserved,
    }

def decode(ir: dict[str, Any], root: Path = ROOT) -> Any:
    if not isinstance(ir, dict) or ir.get("schema") != IR_SCHEMA:
        raise EncoderError("INVALID_IR")
    channel = ir.get("channel")
    member = ir.get("schema_member")
    actor = ir.get("actor")
    if not isinstance(channel, str) or not isinstance(member, str):
        raise EncoderError("INVALID_IR_IDENTITY")
    if member not in schema_members(channel, root):
        raise EncoderError("IR_MEMBER_NOT_IN_FROZEN_SCHEMA")
    if actor not in ACTORS:
        raise EncoderError("IR_ACTOR_INVALID")
    if "payload" not in ir:
        raise EncoderError("IR_PAYLOAD_MISSING")
    return copy.deepcopy(_json_lossless(ir["payload"]))

def round_trip_equal(channel: str, schema_member: str, payload: Any, *, actor: str) -> bool:
    normalized = _json_lossless(payload)
    return decode(encode(channel, schema_member, payload, actor=actor)) == normalized
