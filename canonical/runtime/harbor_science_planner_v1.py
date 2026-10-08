"""Pinned local general-cognition proposal transport for Brain's Harbor science controller.

This module talks only to the loopback llama.cpp OpenAI-compatible endpoint that
is started from independently pinned Qwen model bytes by the execution carrier.
The model may propose bounded research requirements/actions, but Brain retains
command admissibility, action selection, independent verification, state update,
and finish authority.
"""
from __future__ import annotations

import json
import math
import time
import urllib.request
from typing import Any

from canonical.runtime.harbor_command_policy import MAX_COMMAND_CHARS

ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "brain-qwen3.5-9b"
TOOL_NAME = "submit_science_proposal"
MAX_RESPONSE_BYTES = 100_000
MAX_TOOL_COMPLETION_TOKENS = 4096
MIN_TIMEOUT_S = 300
MAX_TIMEOUT_S = 900
REQUEST_BYTES_PER_TOKEN_ESTIMATE = 2
PREFILL_TOKENS_PER_SECOND_FLOOR = 10
GENERATION_AND_TRANSPORT_MARGIN_S = 180


def effective_timeout_s(request_body: bytes, requested_timeout_s: int) -> int:
    if (
        not isinstance(requested_timeout_s, int)
        or isinstance(requested_timeout_s, bool)
        or not 1 <= requested_timeout_s <= MAX_TIMEOUT_S
    ):
        raise SciencePlannerError("SCIENCE_PLANNER_TIMEOUT_INVALID")
    if not isinstance(request_body, (bytes, bytearray)) or not request_body:
        raise SciencePlannerError("SCIENCE_PLANNER_REQUEST_BODY_REQUIRED")
    estimated_request_tokens = max(
        1, math.ceil(len(request_body) / REQUEST_BYTES_PER_TOKEN_ESTIMATE)
    )
    prefill_floor = math.ceil(
        estimated_request_tokens / PREFILL_TOKENS_PER_SECOND_FLOOR
    )
    required = prefill_floor + GENERATION_AND_TRANSPORT_MARGIN_S
    return min(MAX_TIMEOUT_S, max(MIN_TIMEOUT_S, requested_timeout_s, required))

TOOL = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": (
            "Submit one bounded science-work proposal to Project Brain. "
            "Brain independently validates every command and verification result."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "material_requirements": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 16,
                    "items": {"type": "string", "minLength": 1, "maxLength": 64},
                    "description": (
                        "Stable short material requirement IDs. Repeat the exact same "
                        "frozen list on later cycles."
                    ),
                },
                "candidates": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "action_id": {"type": "string", "minLength": 1, "maxLength": 64},
                            "covers": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 16,
                                "items": {"type": "string", "minLength": 1, "maxLength": 64},
                            },
                            # Do not encode MAX_COMMAND_CHARS as JSON-schema maxLength here.
                            # llama.cpp compiles tool schemas into grammars and rejects very
                            # large repetition bounds before generation. Brain enforces the
                            # exact bound immediately after decoding instead.
                            "command": {"type": "string"},
                            "verify_command": {"type": "string"},
                        },
                        "required": ["action_id", "covers", "command", "verify_command"],
                        "additionalProperties": False,
                    },
                    "description": (
                        "One to eight local-environment action candidates. Omit only "
                        "when all frozen requirements are already resolved."
                    ),
                },
                "finish_summary": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 512,
                    "description": (
                        "Optional descriptive summary. It never grants finish authority."
                    ),
                },
            },
            "required": ["material_requirements"],
            "additionalProperties": False,
        },
    },
}


class SciencePlannerError(RuntimeError):
    pass


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
            obj = json.loads(raw[a:b + 1])
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


def _decode_tool_arguments(data: dict[str, Any]) -> dict[str, Any]:
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise SciencePlannerError("SCIENCE_PLANNER_ONE_CHOICE_REQUIRED")
    choice = choices[0] or {}
    if not isinstance(choice, dict):
        raise SciencePlannerError("SCIENCE_PLANNER_CHOICE_REQUIRED")
    if choice.get("finish_reason") == "length":
        raise SciencePlannerError("SCIENCE_PLANNER_OUTPUT_TRUNCATED")
    message = choice.get("message")
    if not isinstance(message, dict):
        raise SciencePlannerError("SCIENCE_PLANNER_MESSAGE_REQUIRED")
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or not calls:
        raise SciencePlannerError("SCIENCE_PLANNER_TOOL_CALL_REQUIRED")
    matched: list[dict[str, Any]] = []
    for call in calls:
        fn = (call or {}).get("function") if isinstance(call, dict) else None
        if not isinstance(fn, dict) or fn.get("name") != TOOL_NAME:
            continue
        args = fn.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception as exc:
                raise SciencePlannerError("SCIENCE_PLANNER_TOOL_ARGUMENTS_JSON_INVALID") from exc
        if not isinstance(args, dict):
            raise SciencePlannerError("SCIENCE_PLANNER_TOOL_ARGUMENTS_OBJECT_REQUIRED")
        matched.append(args)
    if len(matched) != 1:
        raise SciencePlannerError("SCIENCE_PLANNER_EXACTLY_ONE_PROPOSAL_TOOL_CALL_REQUIRED")
    return matched[0]


def plan(prompt: str, *, timeout_s: int = 180) -> dict[str, Any]:
    prompt = str(prompt or "")
    if not prompt.strip():
        raise SciencePlannerError("SCIENCE_PLANNER_PROMPT_REQUIRED")
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an optional proposal source inside Project Brain. "
                    "Use the provided submit_science_proposal tool exactly once. "
                    "Return exactly one terse candidate action per proposal. Use short requirement IDs, "
                    f"keep command and verify_command under {MAX_COMMAND_CHARS} characters each, and use no explanatory prose. "
                    "Never claim execution or finish authority."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "tools": [TOOL],
        "tool_choice": "required",
        "parallel_tool_calls": False,
        "temperature": 0,
        "max_tokens": MAX_TOOL_COMPLETION_TOKENS,
        "stream": False,
    }).encode("utf-8")
    timeout_s = effective_timeout_s(body, timeout_s)
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as response:
            status = int(getattr(response, "status", 200))
            if status != 200:
                raise SciencePlannerError(f"SCIENCE_PLANNER_HTTP_STATUS:{status}")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise SciencePlannerError("SCIENCE_PLANNER_RESPONSE_TOO_LARGE")
        try:
            data = json.loads(raw.decode("utf-8", "replace"))
        except Exception as exc:
            raise SciencePlannerError("SCIENCE_PLANNER_RESPONSE_JSON_INVALID") from exc
        if not isinstance(data, dict):
            raise SciencePlannerError("SCIENCE_PLANNER_RESPONSE_OBJECT_REQUIRED")
        proposal = _decode_tool_arguments(data)
        candidates = proposal.get("candidates")
        if candidates is not None:
            if not isinstance(candidates, list) or len(candidates) > 1:
                raise SciencePlannerError("SCIENCE_PLANNER_CANDIDATES_BOUND_INVALID")
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    raise SciencePlannerError("SCIENCE_PLANNER_CANDIDATE_OBJECT_REQUIRED")
                for field in ("command", "verify_command"):
                    value = candidate.get(field)
                    if not isinstance(value, str) or not value:
                        raise SciencePlannerError(f"SCIENCE_PLANNER_{field.upper()}_REQUIRED")
                    if len(value) > MAX_COMMAND_CHARS:
                        raise SciencePlannerError(f"SCIENCE_PLANNER_{field.upper()}_TOO_LONG")
        # Keep the controller boundary unchanged: it consumes untrusted JSON text.
        text = json.dumps(proposal, sort_keys=True, separators=(",", ":"))
        extract_json_object(text)
        return {
            "text": text,
            "model": str(data.get("model") or MODEL),
            "duration_s": round(time.monotonic() - started, 3),
            "errors": [],
            "transport": "PINNED_LOCAL_QWEN_LLAMA_CPP_TOOL_CALL",
            "endpoint": ENDPOINT,
        }
    except SciencePlannerError:
        raise
    except Exception as exc:
        raise SciencePlannerError(
            "SCIENCE_PLANNER_LOCAL_ROUTE_FAILED:"
            + type(exc).__name__
            + ":"
            + str(exc)
        ) from exc
