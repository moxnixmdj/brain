#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import instruction_constraint_compiler_v1 as constraint_compiler
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v1 as fallback_v1

class Root2InferenceBlocked(RuntimeError):
    pass

BENCHMARK_ID="LIVEBENCH_IF_2026_06_25"

def _instruction(request:Mapping[str,Any])->str:
    if not isinstance(request,Mapping):
        raise Root2InferenceBlocked("REQUEST_MAPPING_REQUIRED")
    if str(request.get("benchmark_id") or "")!=BENCHMARK_ID:
        raise Root2InferenceBlocked("BENCHMARK_ID_MISMATCH")
    allowed=request.get("allowed_tools")
    if allowed not in (None,[],()):
        raise Root2InferenceBlocked("LIVEBENCH_IF_EXTERNAL_TOOLS_FORBIDDEN")
    payload=request.get("task_payload")
    if isinstance(payload,str):
        instruction=payload
    elif isinstance(payload,Mapping):
        instruction=payload.get("instruction") or payload.get("prompt") or payload.get("text")
    else:
        instruction=None
    instruction=str(instruction or "").strip()
    if not instruction:
        raise Root2InferenceBlocked("INSTRUCTION_REQUIRED")
    return instruction

def infer(request:Mapping[str,Any])->dict[str,Any]:
    instruction=_instruction(request)
    try:
        compiled=constraint_compiler.synthesize_formal_only(instruction)
    except Exception:
        # A compiler parse failure is not permission to weaken acceptance or invent
        # an answer. Preserve the previously verified V1 route unchanged.
        return fallback_v1.infer(request)

    if compiled.get("status")=="PASS" and compiled.get("semantic_seed_required") is False:
        answer=str(compiled.get("response") or "")
        ok,errors=constraint_compiler.validate_response(
            answer,
            constraint_compiler.compile_constraints(instruction),
        )
        if not ok:
            raise Root2InferenceBlocked(
                "FORMAL_COMPILER_POSTVALIDATION_FAILED:"+",".join(errors)
            )
        return {
            "task_id":request.get("task_id"),
            "status":"PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
            "answer":answer,
            "artifacts":[],
            "tool_trace":[],
            "cognition_dependency_class":"MODEL_INDEPENDENT",
            "model_dependency_count":0,
            "response_route":"VERIFIED_GENERIC_FORMAL_CONSTRAINT_COMPILER_V1",
        }

    # Structural synthesis that still needs semantic content is deliberately NOT
    # promoted into a benchmark answer. Fall through unchanged to the existing
    # Brain runtime.
    return fallback_v1.infer(request)
