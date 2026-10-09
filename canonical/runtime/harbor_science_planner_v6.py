"""Pinned local general-cognition proposal transport for Brain's Harbor science controller.

This module talks only to the loopback llama.cpp OpenAI-compatible endpoint that
is started from independently pinned Qwen model bytes by the execution carrier.
The model may propose bounded research requirements/actions, but Brain retains
command admissibility, action selection, independent verification, state update,
and finish authority.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
import urllib.error
import urllib.request
from typing import Any

from canonical.runtime.harbor_command_policy import MAX_COMMAND_CHARS

ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
TOKEN_COUNT_ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions/input_tokens"
MODEL = "brain-qwen3.5-9b"
TOOL_NAME = "submit_science_proposal"
MAX_RESPONSE_BYTES = 100_000
MAX_TOOL_COMPLETION_TOKENS = 4096
SERVER_CONTEXT_TOKENS = 16384
MAX_CANDIDATES_PER_PROPOSAL = 4
MAX_REQUIREMENT_ID_CHARS = 8
MAX_ACTION_ID_CHARS = 32
REQUIREMENT_ID_PATTERN = "^[A-Za-z0-9_-]{1,8}$"
ACTION_ID_PATTERN = "^[A-Za-z0-9_-]{1,32}$"
MIN_TIMEOUT_S = 300
MAX_TIMEOUT_S = 900
TOKEN_COUNT_TIMEOUT_S = 60
PREFILL_TOKENS_PER_SECOND_FLOOR = 15
GENERATION_AND_TRANSPORT_MARGIN_S = 180
LONG_CONTEXT_THRESHOLD_TOKENS = 8192
LONG_CONTEXT_PREFILL_TOKENS_PER_SECOND_FLOOR = 8
LONG_CONTEXT_GENERATION_AND_TRANSPORT_MARGIN_S = 240
LONG_CONTEXT_MAX_TIMEOUT_S = 1800
MAX_TRANSPORT_ATTEMPTS = 3
TRANSPORT_RETRY_BACKOFF_S = 0.25
MAX_EVIDENCE_REQUESTS = 4
EVIDENCE_ID_PATTERN = "^[0-9a-f]{64}$"
MAX_EVIDENCE_CHUNK_INDEX = 4095


def effective_timeout_s(input_tokens: int, requested_timeout_s: int) -> int:
    if (
        not isinstance(input_tokens, int)
        or isinstance(input_tokens, bool)
        or input_tokens < 1
    ):
        raise SciencePlannerError("SCIENCE_PLANNER_INPUT_TOKEN_COUNT_INVALID")
    if (
        not isinstance(requested_timeout_s, int)
        or isinstance(requested_timeout_s, bool)
        or not 1 <= requested_timeout_s <= MAX_TIMEOUT_S
    ):
        raise SciencePlannerError("SCIENCE_PLANNER_TIMEOUT_INVALID")
    if input_tokens > LONG_CONTEXT_THRESHOLD_TOKENS:
        prefill_floor = LONG_CONTEXT_PREFILL_TOKENS_PER_SECOND_FLOOR
        margin_s = LONG_CONTEXT_GENERATION_AND_TRANSPORT_MARGIN_S
        effective_cap_s = LONG_CONTEXT_MAX_TIMEOUT_S
    else:
        prefill_floor = PREFILL_TOKENS_PER_SECOND_FLOOR
        margin_s = GENERATION_AND_TRANSPORT_MARGIN_S
        effective_cap_s = MAX_TIMEOUT_S
    prompt_floor = math.ceil(input_tokens / prefill_floor)
    required = prompt_floor + margin_s
    return min(effective_cap_s, max(MIN_TIMEOUT_S, requested_timeout_s, required))

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
                    "items": {"type": "string", "minLength": 1, "maxLength": MAX_REQUIREMENT_ID_CHARS, "pattern": REQUIREMENT_ID_PATTERN},
                    "description": (
                        "Stable short material requirement IDs. Repeat the exact same "
                        "frozen list on later cycles."
                    ),
                },
                "candidates": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": MAX_CANDIDATES_PER_PROPOSAL,
                    "items": {
                        "type": "object",
                        "properties": {
                            "action_id": {"type": "string", "minLength": 1, "maxLength": MAX_ACTION_ID_CHARS, "pattern": ACTION_ID_PATTERN},
                            "covers": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": 16,
                                "items": {"type": "string", "minLength": 1, "maxLength": MAX_REQUIREMENT_ID_CHARS, "pattern": REQUIREMENT_ID_PATTERN},
                            },
                            # Do not encode MAX_COMMAND_CHARS as JSON-schema maxLength here.
                            # llama.cpp compiles tool schemas into grammars and rejects very
                            # large repetition bounds before generation. Brain enforces the
                            # exact bound immediately after decoding instead.
                            "depends_on": {
                                "type": "array",
                                "maxItems": MAX_CANDIDATES_PER_PROPOSAL,
                                "items": {"type": "string", "minLength": 1, "maxLength": MAX_ACTION_ID_CHARS, "pattern": ACTION_ID_PATTERN},
                            },
                            "timeout_sec": {"type": "integer", "minimum": 1, "maximum": 3600},
                            "verify_timeout_sec": {"type": "integer", "minimum": 1, "maximum": 3600},
                            "executor": {"type": "string", "enum": ["shell", "python"]},
                            "command": {"type": "string"},
                            "verify_executor": {"type": "string", "enum": ["shell", "python"]},
                            "verify_command": {"type": "string"},
                            "schema_requirements": {
                                "type": "array",
                                "maxItems": 16,
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "path": {"type": "string"},
                                        "format": {"type": "string", "enum": ["json", "npz"]},
                                        "keys": {"type": "array", "minItems": 1, "maxItems": 32, "items": {"type": "string"}}
                                    },
                                    "required": ["path", "format", "keys"],
                                    "additionalProperties": False
                                }
                            },
                            "deliverables": {
                                "type": "array",
                                "maxItems": 16,
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "path": {"type": "string"},
                                        "format": {"type": "string", "enum": ["file", "json", "python", "npz", "npy", "csv"]}
                                    },
                                    "required": ["path", "format"],
                                    "additionalProperties": False
                                }
                            },
                        },
                        "required": ["action_id", "covers", "executor", "command", "verify_executor", "verify_command"],
                        "additionalProperties": False,
                    },
                    "description": (
                        "One to four local-environment action candidates. Use depends_on for "
                        "true sequencing; overlapping candidates may be alternatives. Brain "
                        "independently verifies each action before promoting coverage."
                    ),
                },
                "evidence_requests": {
                    "type": "array",
                    "maxItems": MAX_EVIDENCE_REQUESTS,
                    "items": {
                        "type": "object",
                        "properties": {
                            "evidence_id": {
                                "type": "string",
                                "minLength": 64,
                                "maxLength": 64,
                                "pattern": EVIDENCE_ID_PATTERN,
                            },
                            "chunk_index": {
                                "type": "integer",
                                "minimum": 0,
                                "maximum": MAX_EVIDENCE_CHUNK_INDEX,
                            },
                        },
                        "required": ["evidence_id", "chunk_index"],
                        "additionalProperties": False,
                    },
                    "description": (
                        "Request exact omitted evidence chunks listed in the "
                        "BRAIN_EVIDENCE_DIRECTORY. Evidence retrieval is cognition-only; "
                        "it grants no execution or finish authority."
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


def _seedless_request_payload(prompt: str) -> dict[str, Any]:
    return {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an optional proposal source inside Project Brain. "
                    "Use the provided submit_science_proposal tool exactly once. "
                    "Return one to four terse candidate actions per proposal. Use short requirement IDs, "
                    "declare depends_on when an action requires a prior proposed action, and request only the "
                    "smallest sufficient timeout_sec / verify_timeout_sec when defaults may be insufficient. "
                    "Every candidate must explicitly type executor and verify_executor as shell or python. "
                    "For Python, declare every literal external mapping key in schema_requirements; Brain probes those keys before effect. "
                    "Declare exact deliverable path/format postconditions for artifacts the action claims to create. "
                    f"Keep command and verify_command under {MAX_COMMAND_CHARS} characters each, and use no explanatory prose. "
                    "If a BRAIN_EVIDENCE_DIRECTORY is present and omitted exact evidence is needed, "
                    "request it with evidence_requests instead of guessing. "
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
    }


def _payload_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _request_payload(prompt: str) -> dict[str, Any]:
    """Compatibility helper returning the seedless semantic request."""
    return _seedless_request_payload(prompt)


def build_request_payload(
    prompt: str,
    *,
    logical_attempt_id: str,
    cycle: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    prompt = str(prompt or "")
    if not prompt.strip():
        raise SciencePlannerError("SCIENCE_PLANNER_PROMPT_REQUIRED")
    if not isinstance(logical_attempt_id, str) or len(logical_attempt_id) != 64:
        raise SciencePlannerError("SCIENCE_PLANNER_LOGICAL_ATTEMPT_ID_INVALID")
    try:
        int(logical_attempt_id, 16)
    except Exception as exc:
        raise SciencePlannerError("SCIENCE_PLANNER_LOGICAL_ATTEMPT_ID_INVALID") from exc
    if not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 0:
        raise SciencePlannerError("SCIENCE_PLANNER_CYCLE_INVALID")

    seedless = _seedless_request_payload(prompt)
    identity_material = json.dumps(
        {
            "logical_attempt_id": logical_attempt_id,
            "cycle": cycle,
            "seedless_payload_sha256": hashlib.sha256(_payload_bytes(seedless)).hexdigest(),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    request_identity_sha256 = hashlib.sha256(identity_material).hexdigest()
    seed = int(request_identity_sha256[:8], 16) & 0x7fffffff
    payload = dict(seedless)
    payload["seed"] = seed
    return payload, {
        "logical_attempt_id": logical_attempt_id,
        "cycle": cycle,
        "seed": seed,
        "request_identity_sha256": request_identity_sha256,
        "seedless_payload_sha256": hashlib.sha256(_payload_bytes(seedless)).hexdigest(),
    }

def count_input_tokens(payload: dict[str, Any]) -> int:
    body = _payload_bytes(payload)
    req = urllib.request.Request(
        TOKEN_COUNT_ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TOKEN_COUNT_TIMEOUT_S) as response:
            status = int(getattr(response, "status", 200))
            if status != 200:
                raise SciencePlannerError(
                    f"SCIENCE_PLANNER_TOKEN_COUNT_HTTP_STATUS:{status}"
                )
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise SciencePlannerError("SCIENCE_PLANNER_TOKEN_COUNT_RESPONSE_TOO_LARGE")
        try:
            data = json.loads(raw.decode("utf-8", "replace"))
        except Exception as exc:
            raise SciencePlannerError(
                "SCIENCE_PLANNER_TOKEN_COUNT_RESPONSE_JSON_INVALID"
            ) from exc
        value = data.get("input_tokens") if isinstance(data, dict) else None
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < 1
        ):
            raise SciencePlannerError("SCIENCE_PLANNER_INPUT_TOKEN_COUNT_INVALID")
        return value
    except SciencePlannerError:
        raise
    except Exception as exc:
        raise SciencePlannerError(
            "SCIENCE_PLANNER_TOKEN_COUNT_ROUTE_FAILED:"
            + type(exc).__name__
            + ":"
            + str(exc)
        ) from exc


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


def _plan_once(
    prompt: str,
    *,
    logical_attempt_id: str,
    cycle: int,
    timeout_s: int = 180,
) -> dict[str, Any]:
    prompt = str(prompt or "")
    if not prompt.strip():
        raise SciencePlannerError("SCIENCE_PLANNER_PROMPT_REQUIRED")
    payload, request_meta = build_request_payload(
        prompt,
        logical_attempt_id=logical_attempt_id,
        cycle=cycle,
    )
    input_tokens = count_input_tokens(payload)
    required_context_tokens = input_tokens + MAX_TOOL_COMPLETION_TOKENS
    if required_context_tokens > SERVER_CONTEXT_TOKENS:
        raise SciencePlannerError(
            f"SCIENCE_PLANNER_CONTEXT_ENVELOPE_EXCEEDED:"
            f"{input_tokens}+{MAX_TOOL_COMPLETION_TOKENS}>{SERVER_CONTEXT_TOKENS}"
        )
    timeout_s = effective_timeout_s(input_tokens, timeout_s)
    payload_sha256 = hashlib.sha256(_payload_bytes(payload)).hexdigest()

    body = _payload_bytes(payload)
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
            if not isinstance(candidates, list) or len(candidates) > MAX_CANDIDATES_PER_PROPOSAL:
                raise SciencePlannerError("SCIENCE_PLANNER_CANDIDATES_BOUND_INVALID")
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    raise SciencePlannerError("SCIENCE_PLANNER_CANDIDATE_OBJECT_REQUIRED")
                for field in ("executor", "verify_executor"):
                    value = candidate.get(field)
                    if value not in ("shell", "python"):
                        raise SciencePlannerError(f"SCIENCE_PLANNER_{field.upper()}_INVALID")
                for field in ("command", "verify_command"):
                    value = candidate.get(field)
                    if not isinstance(value, str) or not value:
                        raise SciencePlannerError(f"SCIENCE_PLANNER_{field.upper()}_REQUIRED")
                    if len(value) > MAX_COMMAND_CHARS:
                        raise SciencePlannerError(f"SCIENCE_PLANNER_{field.upper()}_TOO_LONG")
                for field in ("schema_requirements", "deliverables"):
                    value = candidate.get(field)
                    if value is not None and not isinstance(value, list):
                        raise SciencePlannerError(f"SCIENCE_PLANNER_{field.upper()}_INVALID")
        evidence_requests = proposal.get("evidence_requests")
        if evidence_requests is not None:
            if not isinstance(evidence_requests, list) or len(evidence_requests) > MAX_EVIDENCE_REQUESTS:
                raise SciencePlannerError("SCIENCE_PLANNER_EVIDENCE_REQUESTS_INVALID")
            seen_requests: set[tuple[str, int]] = set()
            for row in evidence_requests:
                if not isinstance(row, dict):
                    raise SciencePlannerError("SCIENCE_PLANNER_EVIDENCE_REQUEST_OBJECT_REQUIRED")
                evidence_id = row.get("evidence_id")
                chunk_index = row.get("chunk_index")
                if (
                    not isinstance(evidence_id, str)
                    or len(evidence_id) != 64
                    or any(c not in "0123456789abcdef" for c in evidence_id)
                ):
                    raise SciencePlannerError("SCIENCE_PLANNER_EVIDENCE_ID_INVALID")
                if (
                    not isinstance(chunk_index, int)
                    or isinstance(chunk_index, bool)
                    or not 0 <= chunk_index <= MAX_EVIDENCE_CHUNK_INDEX
                ):
                    raise SciencePlannerError("SCIENCE_PLANNER_EVIDENCE_CHUNK_INDEX_INVALID")
                key = (evidence_id, chunk_index)
                if key in seen_requests:
                    raise SciencePlannerError("SCIENCE_PLANNER_EVIDENCE_REQUEST_DUPLICATE")
                seen_requests.add(key)
        # Keep the controller boundary unchanged: it consumes untrusted JSON text.
        text = json.dumps(proposal, sort_keys=True, separators=(",", ":"))
        extract_json_object(text)
        return {
            "text": text,
            "model": str(data.get("model") or MODEL),
            "duration_s": round(time.monotonic() - started, 3),
            "input_tokens": input_tokens,
            "required_context_tokens": required_context_tokens,
            "context_headroom_tokens": SERVER_CONTEXT_TOKENS - required_context_tokens,
            "seed": request_meta["seed"],
            "request_identity_sha256": request_meta["request_identity_sha256"],
            "seedless_payload_sha256": request_meta["seedless_payload_sha256"],
            "payload_sha256": payload_sha256,
            "effective_timeout_s": timeout_s,
            "errors": [],
            "transport": "PINNED_LOCAL_QWEN_LLAMA_CPP_TOOL_CALL_V6__SEEDED__EXACT_WIRE_TOKEN_COUNT__PRODUCTION_CONTEXT_GUARD__LOSSLESS_EVIDENCE_REQUESTS__TYPED_ACTIONS",
            "endpoint": ENDPOINT,
            "token_count_endpoint": TOKEN_COUNT_ENDPOINT,
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


def _retryable_transport_failure(exc: BaseException) -> bool:
    """True only for transient transport loss, never deterministic request bugs."""
    if not isinstance(exc, SciencePlannerError):
        return False
    msg = str(exc)
    retryable_status = {408, 425, 429, 500, 502, 503, 504}
    for code in retryable_status:
        if msg == f"SCIENCE_PLANNER_HTTP_STATUS:{code}":
            return True

    if not (
        msg.startswith("SCIENCE_PLANNER_TOKEN_COUNT_ROUTE_FAILED:")
        or msg.startswith("SCIENCE_PLANNER_LOCAL_ROUTE_FAILED:")
    ):
        return False

    cause = exc.__cause__
    if isinstance(cause, urllib.error.HTTPError):
        return int(cause.code) in retryable_status
    if isinstance(cause, (urllib.error.URLError, TimeoutError, ConnectionError)):
        return True
    # urlopen/socket failures can surface as OSError subclasses. They are safe to
    # replay because this route is loopback-only and planner inference has no
    # environment side effects.
    return isinstance(cause, OSError)


def plan(
    prompt: str,
    *,
    logical_attempt_id: str,
    cycle: int,
    timeout_s: int = 180,
) -> dict[str, Any]:
    """Retry only the exact same side-effect-free planner request on transport loss.

    Logical/model/schema/context failures are never retried. The retry identity is
    derived before the first attempt and every successful receipt must bind back to
    those exact bytes.
    """
    expected_payload, expected_meta = build_request_payload(
        prompt,
        logical_attempt_id=logical_attempt_id,
        cycle=cycle,
    )
    expected_payload_sha256 = hashlib.sha256(_payload_bytes(expected_payload)).hexdigest()

    last: SciencePlannerError | None = None
    for attempt in range(1, MAX_TRANSPORT_ATTEMPTS + 1):
        try:
            out = _plan_once(
                prompt,
                logical_attempt_id=logical_attempt_id,
                cycle=cycle,
                timeout_s=timeout_s,
            )
            if out.get("request_identity_sha256") != expected_meta["request_identity_sha256"]:
                raise SciencePlannerError("SCIENCE_PLANNER_RETRY_IDENTITY_DRIFT")
            if out.get("payload_sha256") != expected_payload_sha256:
                raise SciencePlannerError("SCIENCE_PLANNER_RETRY_PAYLOAD_DRIFT")
            out = dict(out)
            out["transport_attempts"] = attempt
            out["transport_retries"] = attempt - 1
            out["transport_retry_policy"] = (
                "EXACT_REQUEST_ONLY__TRANSPORT_FAILURE_ONLY__"
                "NO_SEMANTIC_OR_SCHEMA_RETRY"
            )
            return out
        except SciencePlannerError as exc:
            if not _retryable_transport_failure(exc):
                raise
            last = exc
            if attempt >= MAX_TRANSPORT_ATTEMPTS:
                raise
            time.sleep(TRANSPORT_RETRY_BACKOFF_S * attempt)
    assert last is not None
    raise last
