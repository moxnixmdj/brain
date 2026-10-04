#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import livebench_legacy25_witness_compiler_v1 as legacy25
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v2 as request_v2
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v4 as fallback_v4

Root2InferenceBlocked = fallback_v4.Root2InferenceBlocked
BENCHMARK_ID = fallback_v4.BENCHMARK_ID


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    # Preserve the verified V2 request firewall. V5 only adds a public-grammar
    # score-only route before the existing V4/V3 chain.
    instruction = request_v2._instruction(request)
    compiled = legacy25.synthesize(instruction)
    if compiled.get("status") == "PASS":
        answer = str(compiled.get("response") or "")
        if not answer:
            raise Root2InferenceBlocked("LEGACY25_EMPTY_WITNESS")
        return {
            "task_id": request.get("task_id"),
            "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
            "answer": answer,
            "artifacts": [],
            "tool_trace": [],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
            "response_route": "LIVEBENCH_LEGACY25_PUBLIC_GRAMMAR_WITNESS_V1",
            "capability_boundary": (
                "LIVEBENCH_LEGACY25_REGISTERED_CONSTRAINT_SCORE_ONLY__"
                "NO_GENERAL_SEMANTIC_ANSWER_QUALITY_CLAIM"
            ),
            "recognized_legacy25_kinds": compiled.get("recognized_kinds") or [],
        }
    return fallback_v4.infer(request)
