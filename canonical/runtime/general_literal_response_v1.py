"""Bounded model-independent literal-response instruction route.

This is deliberately a small grammar, not an open-world instruction follower.
It recognizes only explicit directives whose sole requested effect is emitting
one literal payload. Everything else abstains and falls through to existing
Brain routing.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SCHEMA="PROJECT_BRAIN_GENERAL_LITERAL_RESPONSE_V1"

_PREFIX=r"(?:please\s+)?"
_HEAD=(
    r"(?:(?:reply|respond)(?:\s+with)?|(?:return|output|emit|say))"
    r"\s+exactly\s+"
)
_DOUBLE=r'"(?:\\.|[^"\\])*"'
_SINGLE=r"'[^'\r\n]*'"
_BACKTICK=r"`[^`\r\n]*`"
_TOKEN=r"[^\s"'`]+"
_PATTERN=re.compile(
    r"^\s*"+_PREFIX+_HEAD+
    r"(?P<payload>"+_DOUBLE+r"|"+_SINGLE+r"|"+_BACKTICK+r"|"+_TOKEN+r")\s*$",
    re.IGNORECASE,
)


def _decode_payload(raw: str) -> str | None:
    if not raw:
        return None
    if raw.startswith('"'):
        try:
            value=json.loads(raw)
        except Exception:
            return None
        if not isinstance(value,str) or value=="":
            return None
        return value
    if raw[0] in ("'", "`"):
        if len(raw)<2 or raw[-1]!=raw[0]:
            return None
        value=raw[1:-1]
        return value if value else None
    return raw if raw.strip() else None


def parse_literal_response_instruction(instruction: Any) -> dict[str, Any] | None:
    if not isinstance(instruction,str):
        return None
    match=_PATTERN.fullmatch(instruction)
    if match is None:
        return None
    payload=_decode_payload(match.group("payload"))
    if payload is None:
        return None
    return {
        "schema":SCHEMA,
        "status":"LITERAL_RESPONSE_IDENTIFIED",
        "payload":payload,
        "instruction_sha256":hashlib.sha256(instruction.encode("utf-8")).hexdigest(),
        "payload_sha256":hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "persistent_learned_bytes":0,
        "external_frontier_model_calls":0,
        "external_learned_capability_calls":0,
        "network_calls":0,
        "tool_calls":0,
    }


def run_literal_response_instruction(instruction: Any) -> dict[str, Any] | None:
    parsed=parse_literal_response_instruction(instruction)
    if parsed is None:
        return None
    payload=parsed["payload"]
    return {
        "adapter":"goal",
        "returncode":0,
        "stdout":payload,
        "controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
        "planner_source":None,
        "planner_transport":None,
        "planner_model_last":None,
        "cycles":1,
        "trace":[{
            "cycle":0,
            "plan":{
                "type":"literal_response",
                "instruction_sha256":parsed["instruction_sha256"],
                "payload_sha256":parsed["payload_sha256"],
            },
            "result":{
                "status":"EMITTED_LITERAL_RESPONSE",
                "payload_sha256":parsed["payload_sha256"],
            },
        }],
        "final_summary":payload,
        "literal_response_contract":{
            key:parsed[key] for key in (
                "schema","status","instruction_sha256","payload_sha256",
                "persistent_learned_bytes","external_frontier_model_calls",
                "external_learned_capability_calls","network_calls","tool_calls",
            )
        },
    }
