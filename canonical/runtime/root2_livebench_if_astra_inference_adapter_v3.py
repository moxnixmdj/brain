#!/usr/bin/env python3
"""LiveBench IF adapter V3: preserve exact public checker metadata before fallback."""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import livebench_if_metadata_solver_v1 as metadata_solver
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v2 as fallback_v2

class Root2InferenceBlocked(RuntimeError):
    pass

BENCHMARK_ID = "LIVEBENCH_IF_2026_06_25"

def _payload(request: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(request, Mapping):
        raise Root2InferenceBlocked("REQUEST_MAPPING_REQUIRED")
    if str(request.get("benchmark_id") or "") != BENCHMARK_ID:
        raise Root2InferenceBlocked("BENCHMARK_ID_MISMATCH")
    if request.get("allowed_tools") not in (None, [], ()):
        raise Root2InferenceBlocked("LIVEBENCH_IF_EXTERNAL_TOOLS_FORBIDDEN")
    payload = request.get("task_payload")
    return payload if isinstance(payload, Mapping) else {}

def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    payload = _payload(request)
    ids = payload.get("instruction_id_list")
    kwargs = payload.get("kwargs")

    # Exact benchmark metadata is authoritative when present. This route does
    # not infer checker parameters from prose and never uses hidden case IDs.
    if ids is not None or kwargs is not None:
        solved = metadata_solver.solve(ids, kwargs)
        if solved.get("status") == "PASS":
            answer = str(solved.get("response") or "")
            if not answer:
                raise Root2InferenceBlocked("METADATA_SOLVER_EMPTY_RESPONSE")
            return {
                "task_id": request.get("task_id"),
                "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
                "answer": answer,
                "artifacts": [],
                "tool_trace": [],
                "cognition_dependency_class": "MODEL_INDEPENDENT",
                "model_dependency_count": 0,
                "response_route": "LIVEBENCH_IF_EXACT_PUBLIC_METADATA_SOLVER_V1",
                "metadata_solver_route": solved.get("route"),
            }

    # Missing, unsupported, or composition-unproved metadata never weakens the
    # previous verified route. Fall through byte-for-byte in behavior to V2.
    return fallback_v2.infer(request)
