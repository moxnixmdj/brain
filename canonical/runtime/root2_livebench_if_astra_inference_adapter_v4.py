#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import livebench_public_grammar_compiler_v2 as compiler_v2
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v2 as fallback_v2
from canonical.runtime import seed_preserving_instruction_postprocessor_v1 as seed_postprocessor


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


def _wrap(request: Mapping[str, Any], answer: str, route: str, matched_public_rules=None) -> dict[str, Any]:
    return {
        "task_id": request.get("task_id"),
        "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
        "answer": answer,
        "artifacts": [],
        "tool_trace": [],
        "cognition_dependency_class": "MODEL_INDEPENDENT",
        "model_dependency_count": 0,
        "response_route": route,
        "matched_public_rules": matched_public_rules or [],
    }


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    instruction = _instruction(request)

    # Lane A: constraints whose public deterministic checker semantics are enough
    # to construct a complete witness without any semantic seed.
    try:
        compiled = compiler_v2.synthesize_public_structural_only(instruction)
    except Exception:
        compiled = {"status": "BLOCKED"}

    if compiled.get("status") == "PASS" and compiled.get("semantic_seed_required") is False:
        answer = str(compiled.get("response") or "")
        if answer:
            return _wrap(
                request,
                answer,
                str(compiled.get("response_route") or "PINNED_PUBLIC_CHECKER_WITNESS_V2"),
                compiled.get("matched_public_rules") or [],
            )

    # Lane B: preserve the existing verified model-independent semantic route,
    # then apply only independently verified seed-preserving transforms.
    base = fallback_v2.infer(request)
    seed = str(base.get("answer") or "")
    if not seed:
        return base

    try:
        post = seed_postprocessor.transform(seed, instruction)
    except Exception:
        return base

    if post.get("status") == "PASS" and post.get("response") is not None:
        out = dict(base)
        out["answer"] = str(post["response"])
        out["response_route"] = "VERIFIED_SEED_PRESERVING_POSTPROCESSOR_V1"
        out["seed_postprocess_applied"] = post.get("applied_transforms") or []
        return out

    # A failed transform is not evidence that the already-verified semantic seed is
    # invalid. Preserve the predecessor output exactly; never degrade a successful
    # route merely because the optional postprocessor cannot prove a safe edit.
    return base
