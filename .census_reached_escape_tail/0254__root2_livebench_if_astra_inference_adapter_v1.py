#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime import astra_runtime

class Root2InferenceBlocked(RuntimeError):
    pass

BENCHMARK_ID="LIVEBENCH_IF_2026_06_25"

def infer(request:Mapping[str,Any])->dict[str,Any]:
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
    step={
        "goal_ref":"goal",
        "allow_optional_model_planner":False,
        "max_controller_actions":16,
        "max_cycles":6,
    }
    mission={
        "mission_id":"ROOT2-LIVEBENCH-IF-INFERENCE",
        "goal":instruction,
    }
    try:
        result=astra_runtime.run_goal(step,mission)
    except Exception as exc:
        raise Root2InferenceBlocked(type(exc).__name__+":"+str(exc)) from exc
    if result.get("cognition_dependency_class")!="MODEL_INDEPENDENT":
        raise Root2InferenceBlocked("MODEL_DEPENDENCY_FORBIDDEN")
    answer=str(result.get("stdout") or result.get("final_summary") or "").strip()
    if not answer:
        raise Root2InferenceBlocked("EMPTY_ANSWER")
    return {
        "task_id":request.get("task_id"),
        "status":"PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
        "answer":answer,
        "artifacts":[],
        "tool_trace":result.get("trace") or [],
        "cognition_dependency_class":result.get("cognition_dependency_class"),
        "model_dependency_count":result.get("model_dependency_count"),
    }
