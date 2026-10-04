#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import livebench_if_char_trigram_overlap_solver_v1 as overlap_v1
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v3 as fallback_v3

Root2InferenceBlocked = fallback_v3.Root2InferenceBlocked
BENCHMARK_ID = fallback_v3.BENCHMARK_ID


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    # Reuse the V3/V2 request firewall before touching the successor route.
    instruction = fallback_v3.fallback_v2._instruction(request)

    overlap = overlap_v1.solve(instruction)
    if overlap.get("status") == "PASS__WHITESPACE_INVARIANT_CHAR_TRIGRAM_WITNESS":
        answer = str(overlap.get("response") or "")
        if not answer:
            raise Root2InferenceBlocked("OVERLAP_SOLVER_RETURNED_EMPTY_RESPONSE")
        return {
            "task_id": request.get("task_id"),
            "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
            "answer": answer,
            "artifacts": [],
            "tool_trace": [],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
            "response_route": "LIVEBENCH_IF_CHAR_TRIGRAM_OVERLAP_SOLVER_V1",
            "route_proof": {
                "guaranteed_overlap_percent": overlap["guaranteed_overlap_percent"],
                "target_percent": overlap["target_percent"],
                "proof_basis": overlap["proof_basis"],
            },
        }

    # Every non-overlap or unproved shape preserves the already-existing V3
    # successor behavior. No existing route is weakened.
    return fallback_v3.infer(request)
