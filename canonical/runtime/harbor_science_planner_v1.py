"""Dedicated general-cognition proposal transport for Brain's Harbor science controller.

This module is intentionally narrow: it sends the already-authorized task instruction/control
prompt to one frozen zero-incremental-spend proposal endpoint and returns untrusted JSON text.
It performs no search, retrieval, environment action, acceptance decision, or finish decision.
Those remain Brain-controller authority.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any

ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "brain-qwen3.5-9b"
BACKEND = "LOCAL_LLAMA_SERVER"
MAX_RESPONSE_BYTES = 60_000
MAX_COMPLETION_TOKENS = 1400


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
            obj = json.loads(raw[a:b+1])
        except Exception as exc:
            raise SciencePlannerError("SCIENCE_PLANNER_JSON_INVALID") from exc
    if not isinstance(obj, dict):
        raise SciencePlannerError("SCIENCE_PLANNER_OBJECT_REQUIRED")
    return obj


def normalize_proposal_object(obj: dict[str, Any]) -> dict[str, Any]:
    """Normalize exactly one independently observed harmless schema alias.

    Some proposal endpoints label the candidate list safe_candidates even
    when instructed to emit candidates. Both at once is ambiguous and
    therefore rejected. No other keys are guessed or renamed.
    """
    if not isinstance(obj, dict):
        raise SciencePlannerError("SCIENCE_PLANNER_OBJECT_REQUIRED")
    out = dict(obj)
    if "safe_candidates" in out:
        if "candidates" in out:
            raise SciencePlannerError("SCIENCE_PLANNER_CANDIDATE_ALIAS_AMBIGUOUS")
        out["candidates"] = out.pop("safe_candidates")
    return out

def plan(prompt: str, *, timeout_s: int = 180) -> dict[str, Any]:
    """Return one untrusted JSON proposal from the pinned local Qwen endpoint.

    Terminal Science has no hosted fallback.  If the local endpoint or exact
    model identity is unavailable, fail closed before any environment action.
    """
    prompt = str(prompt or "")
    if not prompt.strip():
        raise SciencePlannerError("SCIENCE_PLANNER_PROMPT_REQUIRED")
    if not isinstance(timeout_s, int) or isinstance(timeout_s, bool) or not 1 <= timeout_s <= 300:
        raise SciencePlannerError("SCIENCE_PLANNER_TIMEOUT_INVALID")

    configured = os.environ.get("PROJECT_BRAIN_SCIENCE_PLANNER_ENDPOINT", ENDPOINT).strip()
    if configured != ENDPOINT:
        raise SciencePlannerError("SCIENCE_PLANNER_ENDPOINT_IDENTITY_MISMATCH")

    body = json.dumps({
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return exactly one JSON object and no prose. "
                    "You are only an untrusted proposal source; Project Brain owns "
                    "action selection, execution, verification, and finish authority."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": MAX_COMPLETION_TOKENS,
        "stream": False,
    }).encode("utf-8")
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
        envelope = json.loads(raw.decode("utf-8", "replace"))
        if not isinstance(envelope, dict):
            raise SciencePlannerError("SCIENCE_PLANNER_ENVELOPE_INVALID")
        reported_model = str(envelope.get("model") or "")
        if reported_model != MODEL:
            raise SciencePlannerError("SCIENCE_PLANNER_MODEL_IDENTITY_MISMATCH")
        choices = envelope.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise SciencePlannerError("SCIENCE_PLANNER_CHOICES_INVALID")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise SciencePlannerError("SCIENCE_PLANNER_MESSAGE_INVALID")
        text = message.get("content")
        if not isinstance(text, str) or not text.strip():
            raise SciencePlannerError("SCIENCE_PLANNER_CONTENT_EMPTY")
        extract_json_object(text)
        return {
            "text": text,
            "model": reported_model,
            "duration_s": round(time.monotonic() - started, 3),
            "errors": [],
            "transport": "PINNED_LOCAL_OPENAI_CHAT_COMPLETIONS",
            "endpoint": ENDPOINT,
            "backend": BACKEND,
        }
    except SciencePlannerError:
        raise
    except Exception as exc:
        raise SciencePlannerError(
            "SCIENCE_LOCAL_PLANNER_FAILED:" + type(exc).__name__ + ":" + str(exc)
        ) from exc
