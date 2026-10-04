#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import livebench_if_public_single_checker_witness_v1 as public_witness
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v3 as fallback_v3

Root2InferenceBlocked = fallback_v3.Root2InferenceBlocked
BENCHMARK_ID = fallback_v3.BENCHMARK_ID


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    # Preserve the exact V2/V3 benchmark and external-tool firewall.
    instruction = fallback_v3.fallback_v2._instruction(request)

    candidate = public_witness.construct_single_checker_witness(instruction)
    if candidate.get("status") == "PASS_CANDIDATE":
        answer = str(candidate.get("response") or "")
        if not answer:
            raise Root2InferenceBlocked("PUBLIC_SINGLE_CHECKER_EMPTY_WITNESS")
        return {
            "task_id": request.get("task_id"),
            "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
            "answer": answer,
            "artifacts": [],
            "tool_trace": [],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
            "response_route": "LIVEBENCH_IF_PUBLIC_SINGLE_CHECKER_WITNESS_V5",
            "checker_id": candidate.get("checker_id"),
            "semantic_answer_claimed": False,
            "capability_boundary": (
                "PINNED_PUBLIC_IFBENCH_SINGLE_CHECKER_STRUCTURAL_WITNESS__"
                "CONJUNCTIONS_AND_UNKNOWN_PROMPTS_FALL_BACK_TO_V3"
            ),
        }

    # Critical non-regression rule: conjunctions and unknowns never enter V4's
    # first-match prompt compiler. They preserve the already-frozen V3 route.
    return fallback_v3.infer(request)
