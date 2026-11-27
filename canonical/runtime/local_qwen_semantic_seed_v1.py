#!/usr/bin/env python3
"""Pinned local semantic-seed generation for Project Brain.

This adapter exposes the already content-addressed local Qwen carrier as an
untrusted semantic text producer. It has no execution, acceptance, or finish
authority. The only network address it may contact is the loopback llama.cpp
endpoint started from the separately pinned model and runtime bytes.
"""
from __future__ import annotations

import json
import time
import urllib.request
from typing import Any

SCHEMA = "PROJECT_BRAIN_LOCAL_QWEN_SEMANTIC_SEED_V1"
ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
MODEL = "brain-qwen3.5-9b"
MAX_RESPONSE_BYTES = 200_000
DEFAULT_MAX_TOKENS = 1536


class SemanticSeedError(RuntimeError):
    pass


def _extract_content(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise SemanticSeedError("SEMANTIC_SEED_ONE_CHOICE_REQUIRED")
    message = (choices[0] or {}).get("message")
    if not isinstance(message, dict):
        raise SemanticSeedError("SEMANTIC_SEED_MESSAGE_REQUIRED")
    if message.get("tool_calls"):
        raise SemanticSeedError("SEMANTIC_SEED_UNEXPECTED_TOOL_CALL")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise SemanticSeedError("SEMANTIC_SEED_NONEMPTY_CONTENT_REQUIRED")
    return content.strip()


def generate(prompt: str, *, timeout_s: int = 180, max_tokens: int = DEFAULT_MAX_TOKENS) -> dict[str, Any]:
    prompt = str(prompt or "")
    if not prompt.strip():
        raise SemanticSeedError("SEMANTIC_SEED_PROMPT_REQUIRED")
    if (
        not isinstance(timeout_s, int)
        or isinstance(timeout_s, bool)
        or not 1 <= timeout_s <= 300
    ):
        raise SemanticSeedError("SEMANTIC_SEED_TIMEOUT_INVALID")
    if (
        not isinstance(max_tokens, int)
        or isinstance(max_tokens, bool)
        or not 64 <= max_tokens <= 4096
    ):
        raise SemanticSeedError("SEMANTIC_SEED_MAX_TOKENS_INVALID")

    body = json.dumps(
        {
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the local semantic text producer inside Project Brain. "
                        "Answer the visible user request faithfully and directly. Preserve "
                        "the requested meaning, facts, entities, and task intent. For "
                        "paraphrase, simplify, summarize, or story-generation requests, "
                        "perform that semantic task rather than discussing how to do it. "
                        "Return only the final answer. Do not claim execution, verification, "
                        "acceptance, or finish authority."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
            "stream": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")

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
                raise SemanticSeedError(f"SEMANTIC_SEED_HTTP_STATUS:{status}")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise SemanticSeedError("SEMANTIC_SEED_RESPONSE_TOO_LARGE")
        try:
            data = json.loads(raw.decode("utf-8", "replace"))
        except Exception as exc:
            raise SemanticSeedError("SEMANTIC_SEED_RESPONSE_JSON_INVALID") from exc
        if not isinstance(data, dict):
            raise SemanticSeedError("SEMANTIC_SEED_RESPONSE_OBJECT_REQUIRED")
        content = _extract_content(data)
        return {
            "schema": SCHEMA,
            "status": "PASS",
            "response": content,
            "model": str(data.get("model") or MODEL),
            "endpoint": ENDPOINT,
            "transport": "PINNED_LOCAL_QWEN_LLAMA_CPP_CHAT_COMPLETION",
            "duration_s": round(time.monotonic() - started, 3),
            "network_scope": "LOOPBACK_ONLY",
            "remote_generation_dependencies": 0,
            "api_key_dependencies": 0,
            "incremental_spend_usd": 0,
            "authority": {
                "execution": False,
                "verification": False,
                "acceptance": False,
                "finish": False,
            },
        }
    except SemanticSeedError:
        raise
    except Exception as exc:
        raise SemanticSeedError(
            "SEMANTIC_SEED_LOCAL_ROUTE_FAILED:"
            + type(exc).__name__
            + ":"
            + str(exc)
        ) from exc
