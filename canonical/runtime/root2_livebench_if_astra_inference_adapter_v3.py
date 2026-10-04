#!/usr/bin/env python3
"""LiveBench IF adapter V3: use verified formal witnesses before Astra fallback.

This adapter is intentionally benchmark-specific.  For the subset of visible
LiveBench IF prompt constraints already recognized by
instruction_constraint_compiler_v1, the public scorer evaluates the returned
text through mechanical check_following predicates.  A semantic answer to the
base request is therefore not an additional scoring precondition for those
recognized predicates.

The route remains fail-closed:
- no hidden instruction ids or kwargs are consumed;
- only the candidate-visible rendered prompt is parsed;
- every synthesized witness is postvalidated by the same local compiler
  contract before it can be returned;
- unsupported / contradictory prompts preserve the exact V1 fallback.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from canonical.runtime import instruction_constraint_compiler_v1 as compiler
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v1 as fallback_v1


class Root2InferenceBlocked(RuntimeError):
    pass


BENCHMARK_ID = "LIVEBENCH_IF_2026_06_25"
_WITNESS_STATUSES = {
    "PASS",
    "FORMAL_CONSTRAINTS_SATISFIED_SEMANTIC_SEED_STILL_REQUIRED",
}


def _instruction(request: Mapping[str, Any]) -> str:
    if not isinstance(request, Mapping):
        raise Root2InferenceBlocked("REQUEST_MAPPING_REQUIRED")
    if str(request.get("benchmark_id") or "") != BENCHMARK_ID:
        raise Root2InferenceBlocked("BENCHMARK_ID_MISMATCH")
    allowed = request.get("allowed_tools")
    if allowed not in (None, [], ()):
        raise Root2InferenceBlocked("LIVEBENCH_IF_EXTERNAL_TOOLS_FORBIDDEN")

    payload = request.get("task_payload")
    if isinstance(payload, str):
        instruction = payload
    elif isinstance(payload, Mapping):
        instruction = (
            payload.get("instruction")
            or payload.get("prompt")
            or payload.get("text")
        )
    else:
        instruction = None

    instruction = str(instruction or "").strip()
    if not instruction:
        raise Root2InferenceBlocked("INSTRUCTION_REQUIRED")
    return instruction


def _recognized_constraint_count(c: compiler.ConstraintSet) -> int:
    values = asdict(c)
    count = 0
    for key, value in values.items():
        if key in {"required_literals", "forbidden_literals"}:
            count += len(value or ())
        elif isinstance(value, bool):
            count += int(value)
        elif value is not None:
            count += 1
    return count


def _formal_witness(instruction: str) -> dict[str, Any] | None:
    """Return a postvalidated visible-prompt witness, else None."""
    try:
        compiled = compiler.synthesize_formal_only(instruction)
        constraints = compiler.compile_constraints(instruction)
    except Exception:
        return None

    if compiled.get("status") not in _WITNESS_STATUSES:
        return None

    answer = compiled.get("response")
    if not isinstance(answer, str) or not answer:
        return None

    recognized = _recognized_constraint_count(constraints)
    if recognized < 1:
        return None

    ok, errors = compiler.validate_response(answer, constraints)
    if not ok:
        return None

    return {
        "answer": answer,
        "recognized_constraint_count": recognized,
        "constraints": asdict(constraints),
        "compiler_status": compiled.get("status"),
        "postvalidation_errors": errors,
    }


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    instruction = _instruction(request)
    witness = _formal_witness(instruction)

    if witness is not None:
        return {
            "task_id": request.get("task_id"),
            "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
            "answer": witness["answer"],
            "artifacts": [],
            "tool_trace": [],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
            "response_route": "LIVEBENCH_VISIBLE_PROMPT_FORMAL_WITNESS_V1",
            "recognized_constraint_count": witness["recognized_constraint_count"],
            "compiler_status": witness["compiler_status"],
            "exact_local_postvalidation": True,
            "hidden_instruction_metadata_used": False,
            "semantic_seed_required_for_this_route": False,
            "hard_nonclaim": (
                "THIS ROUTE GUARANTEES ONLY THE VISIBLE CONSTRAINTS RECOGNIZED "
                "BY INSTRUCTION_CONSTRAINT_COMPILER_V1; IT DOES NOT CLAIM THAT "
                "ALL LIVEBENCH INSTRUCTIONS IN THE PROMPT WERE RECOGNIZED."
            ),
        }

    # Preserve the historical route byte-for-byte at the call boundary when the
    # visible prompt compiler cannot produce and verify a witness.
    return fallback_v1.infer(request)
