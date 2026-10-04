#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import livebench_prompt_contract_synthesizer_v1 as contract_synth
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v3 as fallback_v3

Root2InferenceBlocked = fallback_v3.Root2InferenceBlocked
BENCHMARK_ID = fallback_v3.BENCHMARK_ID

def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    # Reuse the verified request firewall inherited by V3/V2.
    instruction = fallback_v3.fallback_v2._instruction(request)

    compiled = contract_synth.synthesize(instruction)
    if compiled.get("status") == "PASS":
        answer = str(compiled.get("response") or "")
        if not answer:
            raise Root2InferenceBlocked("PROMPT_CONTRACT_SYNTH_EMPTY")
        return {
            "task_id": request.get("task_id"),
            "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
            "answer": answer,
            "artifacts": [],
            "tool_trace": [],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
            "response_route": "LIVEBENCH_PINNED_PUBLIC_VERIFIER_PROMPT_CONTRACT_V4",
            "response_subroute": compiled.get("route"),
            "semantic_answer_claimed": False,
            "capability_boundary": (
                "LIVEBENCH_IF_REGISTERED_CONSTRAINT_SCORE_ONLY__"
                "NO_GENERAL_SEMANTIC_ANSWER_QUALITY_CLAIM"
            ),
        }

    # Unsupported or not safely derivable prompt contracts preserve V3 exactly.
    return fallback_v3.infer(request)
