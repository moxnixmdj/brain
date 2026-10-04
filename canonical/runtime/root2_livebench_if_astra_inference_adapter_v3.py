#!/usr/bin/env python3
"""LiveBench IF successor: compose a verified semantic seed with verified formal constraints.

This candidate preserves the V2 zero-semantic fast path. For requests that need
semantic content, it uses the existing V1 model-independent Brain route as the
semantic producer, then applies the independently verified seed-preserving
postprocessor. Unsafe semantic invention/deletion fails closed instead of
silently emitting a response already known to violate a supported constraint.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import root2_livebench_if_astra_inference_adapter_v2 as v2
from canonical.runtime import seed_preserving_instruction_postprocessor_v1 as postprocessor

Root2InferenceBlocked = v2.Root2InferenceBlocked
BENCHMARK_ID = v2.BENCHMARK_ID

_V2_FAST_ROUTE = "VERIFIED_GENERIC_FORMAL_CONSTRAINT_COMPILER_V1"
_V3_ROUTE = "V1_SEMANTIC_SEED__VERIFIED_SEED_PRESERVING_POSTPROCESSOR_V1"


def _has_formal_constraint(constraints: Mapping[str, Any]) -> bool:
    for value in constraints.values():
        if value not in (None, False, (), [], ""):
            return True
    return False


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    # Reuse V2's exact request/policy validation and its independently verified
    # zero-semantic formal fast path.
    instruction = v2._instruction(request)
    base = v2.infer(request)

    if base.get("response_route") == _V2_FAST_ROUTE:
        return base

    answer = str(base.get("answer") or "")
    if base.get("status") != "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE" or not answer:
        return base
    if base.get("cognition_dependency_class") != "MODEL_INDEPENDENT":
        raise Root2InferenceBlocked("MODEL_DEPENDENCY_FORBIDDEN")
    if int(base.get("model_dependency_count") or 0) != 0:
        raise Root2InferenceBlocked("MODEL_DEPENDENCY_FORBIDDEN")

    transformed = postprocessor.transform(answer, instruction)
    constraints = transformed.get("constraints") or {}

    # No supported formal constraint was found. Preserve the exact V2/V1
    # semantic route unchanged rather than decorating a no-op as progress.
    if not _has_formal_constraint(constraints):
        return base

    if transformed.get("status") != "PASS":
        errors = transformed.get("validation_errors") or [transformed.get("error") or "UNKNOWN"]
        raise Root2InferenceBlocked(
            "FORMAL_CONSTRAINT_POSTPROCESS_FAILED:" + ",".join(str(x) for x in errors)
        )

    out = dict(base)
    out["answer"] = str(transformed.get("response") or "")
    out["response_route"] = _V3_ROUTE
    out["formal_postvalidation"] = True
    out["postprocessor_schema"] = transformed.get("schema")
    out["postprocessor_applied_transforms"] = transformed.get("applied_transforms") or []
    out["semantic_seed_sha256"] = __import__("hashlib").sha256(answer.encode()).hexdigest()
    return out
