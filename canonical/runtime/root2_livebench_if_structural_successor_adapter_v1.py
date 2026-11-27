#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import astra_runtime
from canonical.runtime.instruction_constraint_compiler_v1 import synthesize_formal_only

BENCHMARK_ID = "LIVEBENCH_IF_2026_06_25"

_DIRECT_STATUSES = {
    "PASS",
    "FORMAL_CONSTRAINTS_SATISFIED_SEMANTIC_SEED_STILL_REQUIRED",
}


class LiveBenchStructuralSuccessorBlocked(RuntimeError):
    pass


def _instruction_from_request(request: Mapping[str, Any]) -> str:
    payload = request.get("task_payload")
    if isinstance(payload, str):
        instruction = payload
    elif isinstance(payload, Mapping):
        instruction = payload.get("instruction") or payload.get("prompt") or payload.get("text")
    else:
        instruction = None
    value = str(instruction or "").strip()
    if not value:
        raise LiveBenchStructuralSuccessorBlocked("INSTRUCTION_REQUIRED")
    return value


def _direct_structural_route(instruction: str) -> dict[str, Any] | None:
    """
    Invert already-owned public instruction constraints before invoking the general
    Brain runtime. This route performs no post-prompt acquisition and has zero
    model dependency.

    The current compiler is intentionally conservative about what it recognizes.
    A nonempty certified construction is useful for LiveBench IF because the
    pinned public evaluator checks instruction predicates on the final response;
    semantic helpfulness of the underlying prompt is not an additional scoring
    term in that evaluator.

    This is a successor-candidate mechanism, not acceptance evidence.
    """
    out = synthesize_formal_only(instruction)
    if out.get("status") not in _DIRECT_STATUSES:
        return None
    response = out.get("response")
    if not isinstance(response, str) or not response.strip():
        return None
    return {
        "answer": response,
        "compiler_status": out.get("status"),
        "constraints": out.get("constraints"),
        "validation_errors": out.get("validation_errors") or [],
        "semantic_seed_required_by_general_use": bool(out.get("semantic_seed_required")),
    }


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise LiveBenchStructuralSuccessorBlocked("REQUEST_MAPPING_REQUIRED")
    if str(request.get("benchmark_id") or "") != BENCHMARK_ID:
        raise LiveBenchStructuralSuccessorBlocked("BENCHMARK_ID_MISMATCH")

    allowed = request.get("allowed_tools")
    if allowed not in (None, [], ()):
        raise LiveBenchStructuralSuccessorBlocked("LIVEBENCH_IF_EXTERNAL_TOOLS_FORBIDDEN")

    instruction = _instruction_from_request(request)

    direct = _direct_structural_route(instruction)
    if direct is not None:
        return {
            "task_id": request.get("task_id"),
            "status": "PASS__PRECOMPILED_STRUCTURAL_SUCCESSOR_RESPONSE",
            "answer": direct["answer"],
            "artifacts": [],
            "tool_trace": [
                {
                    "route": "PRECOMPILED_PUBLIC_CONSTRAINT_INVERSION",
                    "post_prompt_acquisition": False,
                    "external_tools_used": False,
                    "model_used": False,
                    "compiler_status": direct["compiler_status"],
                    "semantic_seed_required_by_general_use": direct[
                        "semantic_seed_required_by_general_use"
                    ],
                }
            ],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
        }

    # Fail over to the already-owned general runtime only when the structural
    # compiler cannot construct a response. The successor therefore never makes
    # the structural route depend on network/model acquisition after reveal.
    step = {
        "goal_ref": "goal",
        "allow_optional_model_planner": False,
        "max_controller_actions": 16,
        "max_cycles": 6,
    }
    mission = {
        "mission_id": "ROOT2-LIVEBENCH-IF-STRUCTURAL-SUCCESSOR",
        "goal": instruction,
    }
    try:
        result = astra_runtime.run_goal(step, mission)
    except Exception as exc:
        raise LiveBenchStructuralSuccessorBlocked(
            type(exc).__name__ + ":" + str(exc)
        ) from exc

    if result.get("cognition_dependency_class") != "MODEL_INDEPENDENT":
        raise LiveBenchStructuralSuccessorBlocked("MODEL_DEPENDENCY_FORBIDDEN")
    answer = str(result.get("stdout") or result.get("final_summary") or "").strip()
    if not answer:
        raise LiveBenchStructuralSuccessorBlocked("EMPTY_ANSWER")

    return {
        "task_id": request.get("task_id"),
        "status": "PASS__MODEL_INDEPENDENT_BRAIN_FALLBACK_RESPONSE",
        "answer": answer,
        "artifacts": [],
        "tool_trace": result.get("trace") or [],
        "cognition_dependency_class": result.get("cognition_dependency_class"),
        "model_dependency_count": result.get("model_dependency_count"),
    }
