#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import livebench_public_grammar_compiler_v2 as compiler_v2
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v2 as fallback_v2


class Root2InferenceBlocked(RuntimeError):
    pass


BENCHMARK_ID = "LIVEBENCH_IF_2026_06_25"


def _instruction(request: Mapping[str, Any]) -> str:
    if not isinstance(request, Mapping):
        raise Root2InferenceBlocked("REQUEST_MAPPING_REQUIRED")
    if str(request.get("benchmark_id") or "") != BENCHMARK_ID:
        raise Root2InferenceBlocked("BENCHMARK_ID_MISMATCH")
    allowed = request.get("allowed_tools")
    if allowed not in (None, [], ()):
        raise Root2InferenceBlocked("LIVEBENCH_IF_EXTERNAL_TOOLS_FORBIDDEN")
    payload = request.get("task_payload")
    if isinstance(payload, str):
        instruction = payload
    elif isinstance(payload, Mapping):
        instruction = payload.get("instruction") or payload.get("prompt") or payload.get("text")
    else:
        instruction = None
    instruction = str(instruction or "").strip()
    if not instruction:
        raise Root2InferenceBlocked("INSTRUCTION_REQUIRED")
    return instruction


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    instruction = _instruction(request)
    try:
        compiled = compiler_v2.synthesize_public_structural_only(instruction)
    except Exception:
        return fallback_v2.infer(request)

    if compiled.get("status") == "PASS" and compiled.get("semantic_seed_required") is False:
        answer = str(compiled.get("response") or "")
        if not answer:
            return fallback_v2.infer(request)
        return {
            "task_id": request.get("task_id"),
            "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
            "answer": answer,
            "artifacts": [],
            "tool_trace": [],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
            "response_route": compiled.get("response_route") or "PINNED_PUBLIC_CHECKER_WITNESS_V2",
            "matched_public_rules": compiled.get("matched_public_rules") or [],
        }

    # Every unproved or unsatisfied public-grammar combination falls through to the
    # previously verified V2 route unchanged. No hidden ids/kwargs, no terminal case
    # content, no policy weakening.
    return fallback_v2.infer(request)
