#!/usr/bin/env python3
"""LiveBench IF successor V4: local semantic seed + strict constraint composition.

V4 adds one capability layer ahead of the independently verified V3 route:
a deterministic, precommitted semantic text producer for paraphrase, simplify,
summarize and story/narrative requests. The producer sees only the model-visible
instruction string. It never receives grader-only instruction IDs or kwargs.

A V4 response is emitted only when:
1. the semantic producer proves a supported, prompt-grounded seed route; and
2. the strict seed-preserving public-IFBench postprocessor proves that the final
   response contains that seed verbatim and satisfies every constraint it claims
   to model.

Any unsupported, contradictory, or unproved case falls through unchanged to V3.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import local_semantic_text_core_v1 as semantic_core
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v3 as fallback_v3
from canonical.runtime import seed_preserving_instruction_postprocessor_v2 as postprocessor

Root2InferenceBlocked = fallback_v3.Root2InferenceBlocked
BENCHMARK_ID = fallback_v3.BENCHMARK_ID


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    # Reuse the verified V2 request firewall before any semantic work. This keeps
    # benchmark identity and the no-external-tools rule unchanged.
    instruction = fallback_v3.fallback_v2._instruction(request)

    seed_result = semantic_core.produce(instruction)
    if seed_result.get("status") == "PASS":
        seed = str(seed_result.get("seed") or "")
        try:
            transformed = postprocessor.transform(seed, instruction)
        except Exception:
            transformed = {"status": "FAIL_CLOSED"}

        if (
            transformed.get("status") == "PASS"
            and transformed.get("seed_verbatim_preserved") is True
        ):
            answer = str(transformed.get("response") or "")
            if seed and seed in answer:
                return {
                    "task_id": request.get("task_id"),
                    "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
                    "answer": answer,
                    "artifacts": [],
                    "tool_trace": [],
                    "cognition_dependency_class": "MODEL_INDEPENDENT",
                    "model_dependency_count": 0,
                    "learned_parameter_count": 0,
                    "response_route": "LOCAL_SEMANTIC_TEXT_CORE_V1_PLUS_STRICT_POSTPROCESSOR_V2",
                    "semantic_intent": seed_result.get("intent"),
                    "semantic_grounding_class": seed_result.get("grounding_class"),
                    "semantic_grounding": seed_result.get("grounding"),
                    "constraint_transforms": transformed.get("applied_transforms", []),
                    "seed_verbatim_preserved": True,
                    "capability_boundary": (
                        "PROMPT_GROUNDED_LOCAL_SEMANTIC_SEED_PLUS_PROVED_"
                        "SEED_PRESERVING_FORMAL_TRANSFORMS__NO_OPUS_QUALITY_CLAIM"
                    ),
                }

    # V4 adds no permission to guess, acquire capabilities after prompt exposure,
    # use grader-only metadata, weaken constraints, or consume network/model tools.
    return fallback_v3.infer(request)
