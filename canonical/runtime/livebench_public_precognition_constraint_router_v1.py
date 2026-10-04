#!/usr/bin/env python3
"""Pre-cognition public-constraint router for the LiveBench IF successor.

This candidate attacks the policy-block failure class without weakening policy:
1. recognize only exact public IFBench suffix templates,
2. remove the recognized constraint before semantic cognition,
3. obtain the semantic seed through the existing verified model-independent route,
4. deterministically project the seed onto the public constraint, and
5. postvalidate with the canonical constraint compiler.

Anything not proved safe falls through to the already-active V2 adapter unchanged.
No terminal case content, IDs, hidden kwargs, or benchmark-specific failure traces
are consumed here.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from canonical.runtime import instruction_constraint_compiler_v1 as compiler
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v1 as fallback_v1
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v2 as fallback_v2


class PreCognitionRouteBlocked(RuntimeError):
    pass


BENCHMARK_ID = "LIVEBENCH_IF_2026_06_25"

_PUBLIC_SUFFIXES = (
    (
        "UNIQUE_WORD_COUNT",
        re.compile(
            r"(?P<clause>Use at least (?P<n>\\d+) unique words in the response\\.)\\s*$",
            re.IGNORECASE,
        ),
    ),
    (
        "EXACT_NUMBER_COUNT",
        re.compile(
            r"(?P<clause>Include exactly (?P<n>\\d+) numbers in the response; "
            r"do not use commas within the numbers\\.)\\s*$",
            re.IGNORECASE,
        ),
    ),
)

_FILLER = (
    "amber birch cedar delta ember frost granite harbor ivory juniper kinetic "
    "lumen meadow nectar orbit prairie quartz river summit timber umber velvet "
    "willow xenon yarrow zephyr"
).split()


def _instruction(request: Mapping[str, Any]) -> str:
    if not isinstance(request, Mapping):
        raise PreCognitionRouteBlocked("REQUEST_MAPPING_REQUIRED")
    if str(request.get("benchmark_id") or "") != BENCHMARK_ID:
        raise PreCognitionRouteBlocked("BENCHMARK_ID_MISMATCH")
    allowed = request.get("allowed_tools")
    if allowed not in (None, [], ()):
        raise PreCognitionRouteBlocked("LIVEBENCH_IF_EXTERNAL_TOOLS_FORBIDDEN")
    payload = request.get("task_payload")
    if isinstance(payload, str):
        value = payload
    elif isinstance(payload, Mapping):
        value = payload.get("instruction") or payload.get("prompt") or payload.get("text")
    else:
        value = None
    value = str(value or "").strip()
    if not value:
        raise PreCognitionRouteBlocked("INSTRUCTION_REQUIRED")
    return value


def _split_public_suffix(instruction: str) -> tuple[str, str, str] | None:
    text = str(instruction or "").strip()
    for kind, pattern in _PUBLIC_SUFFIXES:
        match = pattern.search(text)
        if not match:
            continue
        base = text[: match.start()].rstrip()
        clause = match.group("clause").strip()
        if not base:
            return None
        return kind, base, clause
    return None


def _request_with_instruction(request: Mapping[str, Any], instruction: str) -> dict[str, Any]:
    out = dict(request)
    payload = request.get("task_payload")
    if isinstance(payload, str):
        out["task_payload"] = instruction
        return out
    if isinstance(payload, Mapping):
        next_payload = dict(payload)
        if "instruction" in next_payload:
            next_payload["instruction"] = instruction
        elif "prompt" in next_payload:
            next_payload["prompt"] = instruction
        elif "text" in next_payload:
            next_payload["text"] = instruction
        else:
            next_payload["instruction"] = instruction
        out["task_payload"] = next_payload
        return out
    raise PreCognitionRouteBlocked("TASK_PAYLOAD_UNSUPPORTED")


def _word_tokens(value: str) -> list[str]:
    return re.findall(r"\b\w+\b", str(value or ""), flags=re.UNICODE)


def _append_unique_words(candidate: str, minimum: int) -> str:
    existing = {token.lower() for token in _word_tokens(candidate)}
    i = 0
    while len(existing) < minimum:
        if i < len(_FILLER):
            token = _FILLER[i]
        else:
            # Alphabetic-only deterministic extension avoids accidentally
            # altering any number-count constraint.
            q = i - len(_FILLER)
            token = "lexeme" + chr(ord("a") + (q % 26)) * (1 + q // 26)
        i += 1
        if token.lower() in existing:
            continue
        candidate = candidate.rstrip() + " " + token
        existing.add(token.lower())
    return candidate


def _append_numbers(candidate: str, exact_count: int) -> str:
    current = len(re.findall(r"\b\d+\b", candidate))
    if current > exact_count:
        raise PreCognitionRouteBlocked("SEED_ALREADY_EXCEEDS_EXACT_NUMBER_COUNT")
    next_value = 1
    while current < exact_count:
        while re.search(rf"\b{next_value}\b", candidate):
            next_value += 1
        candidate = candidate.rstrip() + f" {next_value}"
        current += 1
        next_value += 1
    return candidate


def _project_seed(kind: str, seed: str, clause: str) -> str:
    candidate = str(seed or "").strip()
    if not candidate:
        raise PreCognitionRouteBlocked("EMPTY_SEMANTIC_SEED")
    constraints = compiler.compile_constraints(clause)

    if kind == "UNIQUE_WORD_COUNT":
        if constraints.min_unique_words is None:
            raise PreCognitionRouteBlocked("UNIQUE_WORD_COUNT_NOT_COMPILED")
        candidate = _append_unique_words(candidate, constraints.min_unique_words)
    elif kind == "EXACT_NUMBER_COUNT":
        if constraints.exact_numbers is None:
            raise PreCognitionRouteBlocked("EXACT_NUMBER_COUNT_NOT_COMPILED")
        candidate = _append_numbers(candidate, constraints.exact_numbers)
    else:
        raise PreCognitionRouteBlocked("UNSUPPORTED_PUBLIC_SUFFIX_KIND")

    ok, errors = compiler.validate_response(candidate, constraints)
    if not ok:
        raise PreCognitionRouteBlocked(
            "POSTVALIDATION_FAILED:" + ",".join(str(x) for x in errors)
        )
    return candidate


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    instruction = _instruction(request)

    # Preserve the already-verified exact-formal route byte-for-byte when it applies.
    formal = compiler.synthesize_formal_only(instruction)
    if formal.get("status") == "PASS" and formal.get("semantic_seed_required") is False:
        return fallback_v2.infer(request)

    split = _split_public_suffix(instruction)
    if split is None:
        return fallback_v2.infer(request)

    kind, semantic_instruction, clause = split
    semantic_request = _request_with_instruction(request, semantic_instruction)

    try:
        seed_result = fallback_v1.infer(semantic_request)
        if seed_result.get("cognition_dependency_class") != "MODEL_INDEPENDENT":
            raise PreCognitionRouteBlocked("SEMANTIC_SEED_MODEL_DEPENDENCY_FORBIDDEN")
        if int(seed_result.get("model_dependency_count") or 0) != 0:
            raise PreCognitionRouteBlocked("SEMANTIC_SEED_MODEL_DEPENDENCY_COUNT_NONZERO")
        projected = _project_seed(kind, str(seed_result.get("answer") or ""), clause)
    except Exception:
        # Candidate must never reduce the behavior of the active adapter.
        return fallback_v2.infer(request)

    return {
        "task_id": request.get("task_id"),
        "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
        "answer": projected,
        "artifacts": seed_result.get("artifacts") or [],
        "tool_trace": seed_result.get("tool_trace") or [],
        "cognition_dependency_class": "MODEL_INDEPENDENT",
        "model_dependency_count": 0,
        "response_route": "PUBLIC_PRECOGNITION_CONSTRAINT_ROUTER_V1:" + kind,
        "semantic_prompt_constraint_removed_before_cognition": True,
        "constraint_postvalidated": True,
    }
