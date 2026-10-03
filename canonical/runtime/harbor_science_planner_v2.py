"""Pinned local structured proposal transport for Brain's Harbor science controller.

The cognition substrate is proposal-only. This transport accepts exactly one forced
OpenAI-compatible tool call from a pinned local model endpoint. It has no external
network fallback and no execution, verification, state-transition, or finish authority.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
DEFAULT_MODEL = "brain-qwen3.5-9b"
TOOL_NAME = "submit_science_proposal"
MAX_RESPONSE_BYTES = 128_000


class SciencePlannerError(RuntimeError):
    pass


def _endpoint() -> str:
    raw = os.environ.get("PROJECT_BRAIN_SCIENCE_LOCAL_ENDPOINT", DEFAULT_ENDPOINT).strip()
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme != "http":
        raise SciencePlannerError("SCIENCE_LOCAL_ENDPOINT_SCHEME_INVALID")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SciencePlannerError("SCIENCE_LOCAL_ENDPOINT_NOT_LOOPBACK")
    if parsed.path.rstrip("/") != "/v1/chat/completions":
        raise SciencePlannerError("SCIENCE_LOCAL_ENDPOINT_PATH_INVALID")
    if parsed.params or parsed.query or parsed.fragment:
        raise SciencePlannerError("SCIENCE_LOCAL_ENDPOINT_EXTRAS_INVALID")
    return raw


def _model() -> str:
    model = os.environ.get("PROJECT_BRAIN_SCIENCE_LOCAL_MODEL", DEFAULT_MODEL).strip()
    if not model:
        raise SciencePlannerError("SCIENCE_LOCAL_MODEL_REQUIRED")
    return model


def extract_json_object(text: Any) -> dict[str, Any]:
    raw = str(text or "").strip()
    try:
        obj = json.loads(raw)
    except Exception:
        a = raw.find("{")
        b = raw.rfind("}")
        if a < 0 or b < a:
            raise SciencePlannerError("SCIENCE_PLANNER_NO_JSON")
        try:
            obj = json.loads(raw[a:b+1])
        except Exception as exc:
            raise SciencePlannerError("SCIENCE_PLANNER_JSON_INVALID") from exc
    if not isinstance(obj, dict):
        raise SciencePlannerError("SCIENCE_PLANNER_OBJECT_REQUIRED")
    return obj


def normalize_proposal_object(obj: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise SciencePlannerError("SCIENCE_PLANNER_OBJECT_REQUIRED")
    out = dict(obj)
    if "safe_candidates" in out:
        if "candidates" in out:
            raise SciencePlannerError("SCIENCE_PLANNER_CANDIDATE_ALIAS_AMBIGUOUS")
        out["candidates"] = out.pop("safe_candidates")
    return out


def _proposal_tool() -> dict[str, Any]:
    candidate = {
        "type": "object",
        "properties": {
            "action_id": {"type": "string", "minLength": 1},
            "covers": {
                "type": "array",
                "minItems": 1,
                "maxItems": 16,
                "items": {"type": "string", "minLength": 1},
            },
            "command": {"type": "string", "minLength": 1},
            "verify_command": {"type": "string", "minLength": 1},
        },
        "required": ["action_id", "covers", "command", "verify_command"],
        "additionalProperties": False,
    }
    return {
        "type": "function",
        "function": {
            "name": TOOL_NAME,
            "description": (
                "Submit one bounded science action proposal. Project Brain validates, "
                "selects, executes, verifies, updates state, and decides completion."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "material_requirements": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 16,
                        "items": {"type": "string", "minLength": 1},
                    },
                    "candidates": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 8,
                        "items": candidate,
                    },
                    "finish_summary": {"type": "string", "minLength": 1},
                },
                "required": ["candidates"],
                "additionalProperties": False,
            },
        },
    }


def _extract_forced_tool_arguments(data: dict[str, Any], expected_model: str) -> dict[str, Any]:
    if str(data.get("model") or "") != expected_model:
        raise SciencePlannerError("SCIENCE_LOCAL_MODEL_IDENTITY_MISMATCH")
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise SciencePlannerError("SCIENCE_LOCAL_CHOICE_COUNT_INVALID")
    message = (choices[0] or {}).get("message") or {}
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or len(calls) != 1:
        raise SciencePlannerError("SCIENCE_LOCAL_TOOL_CALL_COUNT_INVALID")
    fn = (calls[0] or {}).get("function") or {}
    if fn.get("name") != TOOL_NAME:
        raise SciencePlannerError("SCIENCE_LOCAL_TOOL_NAME_INVALID")
    args = fn.get("arguments")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception as exc:
            raise SciencePlannerError("SCIENCE_LOCAL_TOOL_ARGUMENTS_JSON_INVALID") from exc
    if not isinstance(args, dict):
        raise SciencePlannerError("SCIENCE_LOCAL_TOOL_ARGUMENTS_OBJECT_REQUIRED")
    return normalize_proposal_object(args)


def plan(prompt: str, *, timeout_s: int = 180) -> dict[str, Any]:
    prompt = str(prompt or "")
    if not prompt.strip():
        raise SciencePlannerError("SCIENCE_PLANNER_PROMPT_REQUIRED")
    if not isinstance(timeout_s, int) or isinstance(timeout_s, bool) or not 1 <= timeout_s <= 300:
        raise SciencePlannerError("SCIENCE_PLANNER_TIMEOUT_INVALID")

    endpoint = _endpoint()
    model = _model()
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a proposal-only cognition substrate inside Project Brain. "
                    "You MUST call submit_science_proposal exactly once. Do not answer normally. "
                    "Project Brain alone owns execution, verification, state transitions, and finish authority."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "tools": [_proposal_tool()],
        "tool_choice": "required",
        "parallel_tool_calls": False,
        "temperature": 0,
        "max_tokens": 2048,
        "stream": False,
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as response:
            status = int(getattr(response, "status", 200))
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except Exception as exc:
        raise SciencePlannerError(
            "SCIENCE_LOCAL_PLANNER_UNAVAILABLE:" + type(exc).__name__ + ":" + str(exc)
        ) from exc
    if status != 200:
        raise SciencePlannerError(f"SCIENCE_LOCAL_PLANNER_HTTP_STATUS:{status}")
    if len(raw) > MAX_RESPONSE_BYTES:
        raise SciencePlannerError("SCIENCE_LOCAL_PLANNER_RESPONSE_TOO_LARGE")
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except Exception as exc:
        raise SciencePlannerError("SCIENCE_LOCAL_PLANNER_RESPONSE_JSON_INVALID") from exc
    if not isinstance(data, dict):
        raise SciencePlannerError("SCIENCE_LOCAL_PLANNER_RESPONSE_OBJECT_REQUIRED")

    proposal = _extract_forced_tool_arguments(data, model)
    return {
        "text": json.dumps(proposal, sort_keys=True),
        "proposal": proposal,
        "model": model,
        "duration_s": round(time.monotonic() - started, 3),
        "transport": "PINNED_LOCAL_OPENAI_TOOL_CALL",
        "endpoint": endpoint,
        "tool_name": TOOL_NAME,
        "external_network_fallback": False,
    }
