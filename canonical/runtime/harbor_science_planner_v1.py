"""Dedicated general-cognition proposal transport for Brain's Harbor science controller.

This module is intentionally narrow: it sends the already-authorized task instruction/control
prompt to one frozen zero-incremental-spend proposal endpoint and returns untrusted JSON text.
It performs no search, retrieval, environment action, acceptance decision, or finish decision.
Those remain Brain-controller authority.
"""
from __future__ import annotations

import json
import time
import urllib.request
from typing import Any

ENDPOINT = "https://text.pollinations.ai/"
MODEL_ALIASES = ("openai-fast", "openai", "mistral")
MAX_RESPONSE_BYTES = 30_000


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


def plan(prompt: str, *, timeout_s: int = 20) -> dict[str, Any]:
    prompt = str(prompt or "")
    if not prompt.strip():
        raise SciencePlannerError("SCIENCE_PLANNER_PROMPT_REQUIRED")
    if not isinstance(timeout_s, int) or isinstance(timeout_s, bool) or not 1 <= timeout_s <= 60:
        raise SciencePlannerError("SCIENCE_PLANNER_TIMEOUT_INVALID")

    errors: list[dict[str, Any]] = []
    for model in MODEL_ALIASES:
        body = json.dumps({
            "messages": [{"role": "user", "content": prompt}],
            "model": model,
            "jsonMode": True,
        }).encode("utf-8")
        req = urllib.request.Request(
            ENDPOINT,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "ProjectBrain/1.0"},
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
            text = raw.decode("utf-8", "replace")
            # Validate object shape at the transport boundary, but keep the object untrusted.
            extract_json_object(text)
            return {
                "text": text,
                "model": model,
                "duration_s": round(time.monotonic() - started, 3),
                "errors": errors,
                "transport": "FROZEN_GENERAL_COGNITION_PROPOSAL_ENDPOINT",
                "endpoint": ENDPOINT,
            }
        except Exception as exc:
            errors.append({
                "model": model,
                "error": type(exc).__name__ + ":" + str(exc),
                "duration_s": round(time.monotonic() - started, 3),
            })
    raise SciencePlannerError(
        "SCIENCE_PLANNER_ALL_ROUTES_FAILED:" + json.dumps(errors, sort_keys=True)[:1800]
    )
