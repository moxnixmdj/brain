#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import root2_livebench_if_astra_inference_adapter_v2 as base_v2
from canonical.runtime import seed_preserving_instruction_postprocessor_v1 as postprocessor


class Root2InferenceBlocked(RuntimeError):
    pass


BENCHMARK_ID = base_v2.BENCHMARK_ID


def _instruction(request: Mapping[str, Any]) -> str:
    try:
        return base_v2._instruction(request)
    except Exception as exc:
        raise Root2InferenceBlocked(type(exc).__name__ + ":" + str(exc)) from exc


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    """Compose the verified V2 inference route with verified seed-preserving constraints.

    The V2 adapter remains the semantic producer and formal-only fast path. This
    successor never acquires post-prompt capabilities, never uses external tools,
    and never invents or deletes semantic content merely to satisfy a structural
    constraint. When a structural constraint cannot be satisfied by the verified
    postprocessor, inference fails closed instead of knowingly emitting a response
    that violates the compiled instruction contract.
    """
    instruction = _instruction(request)

    try:
        base = base_v2.infer(request)
    except Exception as exc:
        raise Root2InferenceBlocked(type(exc).__name__ + ":" + str(exc)) from exc

    if not isinstance(base, dict):
        raise Root2InferenceBlocked("BASE_RESULT_OBJECT_REQUIRED")
    if base.get("cognition_dependency_class") != "MODEL_INDEPENDENT":
        raise Root2InferenceBlocked("MODEL_DEPENDENCY_FORBIDDEN")
    try:
        model_dependency_count = int(base.get("model_dependency_count"))
    except Exception as exc:
        raise Root2InferenceBlocked("MODEL_DEPENDENCY_COUNT_INVALID") from exc
    if model_dependency_count != 0:
        raise Root2InferenceBlocked("MODEL_DEPENDENCY_FORBIDDEN")

    answer = base.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise Root2InferenceBlocked("SEMANTIC_SEED_REQUIRED")

    transformed = postprocessor.transform(answer, instruction)
    if transformed.get("status") != "PASS":
        errors = transformed.get("validation_errors") or []
        error = str(transformed.get("error") or "POSTPROCESS_FAIL_CLOSED")
        suffix = ":" + ",".join(str(x) for x in errors) if errors else ""
        raise Root2InferenceBlocked(error + suffix)

    final_answer = transformed.get("response")
    if not isinstance(final_answer, str) or not final_answer:
        raise Root2InferenceBlocked("POSTPROCESS_EMPTY_RESPONSE")

    out = dict(base)
    out["answer"] = final_answer
    out["response_route"] = "V2_THEN_SEED_PRESERVING_INSTRUCTION_POSTPROCESSOR_V1"
    out["seed_postprocessor"] = {
        "schema": transformed.get("schema"),
        "applied_transforms": list(transformed.get("applied_transforms") or []),
        "seed_preserved": bool(transformed.get("seed_preserved")),
        "exact_postvalidation": bool(transformed.get("exact_postvalidation")),
        "model_dependency_count": int(transformed.get("model_dependency_count") or 0),
        "network_used": bool(transformed.get("network_used")),
        "incremental_spend_usd": transformed.get("incremental_spend_usd", 0),
    }
    out["model_dependency_count"] = 0
    out["cognition_dependency_class"] = "MODEL_INDEPENDENT"
    return out
