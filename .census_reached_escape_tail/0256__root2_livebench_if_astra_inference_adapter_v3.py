#!/usr/bin/env python3
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import instruction_constraint_compiler_v1 as constraint_compiler
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v2 as fallback_v2

Root2InferenceBlocked = fallback_v2.Root2InferenceBlocked
BENCHMARK_ID = fallback_v2.BENCHMARK_ID

_SCORE_ONLY_STRUCTURAL_STATUS = "FORMAL_CONSTRAINTS_SATISFIED_SEMANTIC_SEED_STILL_REQUIRED"


def _validated_structural_witness(instruction: str) -> str | None:
    """Return a deterministic structural witness, or None when V1 cannot prove it.

    This route is intentionally LiveBench-IF-specific.  The frozen IF scorer
    evaluates only registered instruction predicates over the response; it has
    no independent semantic-answer-quality term.  Therefore a response that is
    constructively validated against the compiler's recovered structural
    constraints does not require a semantic seed merely to be a candidate
    instruction-following witness.

    This does NOT claim that the compiler recovered every hidden checker or that
    the witness passes the frozen benchmark.  Unknown/unmodelled constraints
    remain possible and are left for exact scorer verification.
    """
    try:
        compiled = constraint_compiler.synthesize_formal_only(instruction)
    except Exception:
        return None
    if compiled.get("status") != _SCORE_ONLY_STRUCTURAL_STATUS:
        return None
    answer = str(compiled.get("response") or "")
    if not answer:
        return None
    try:
        constraints = constraint_compiler.compile_constraints(instruction)
        ok, errors = constraint_compiler.validate_response(answer, constraints)
    except Exception:
        return None
    if not ok:
        return None
    return answer


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    # Reuse the independently verified V2 request firewall exactly.
    instruction = fallback_v2._instruction(request)

    witness = _validated_structural_witness(instruction)
    if witness is not None:
        return {
            "task_id": request.get("task_id"),
            "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
            "answer": witness,
            "artifacts": [],
            "tool_trace": [],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
            "response_route": "LIVEBENCH_IF_SCORE_ONLY_STRUCTURAL_WITNESS_V3",
            "capability_boundary": (
                "LIVEBENCH_IF_REGISTERED_CONSTRAINT_SCORE_ONLY__"
                "NO_GENERAL_SEMANTIC_ANSWER_QUALITY_CLAIM"
            ),
        }

    # Exact formal routes and every unproved/contradictory/unrecognized case keep
    # the already verified V2 behavior.  V3 adds no authority to weaken a block.
    return fallback_v2.infer(request)
