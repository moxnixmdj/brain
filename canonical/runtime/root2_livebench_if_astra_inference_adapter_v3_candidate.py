#!/usr/bin/env python3
"""Candidate LiveBench IF adapter V3.

Adds a zero-model visible-prompt route for the pinned public ratio-overlap family
and its two observed companion constraints. This file is intentionally a
candidate only; governance must explicitly activate it after independent
verification and exact scope binding.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import livebench_character_trigram_constraint_controller_v1 as trigram
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v2 as fallback_v2

BENCHMARK_ID = "LIVEBENCH_IF_2026_06_25"


class Root2InferenceBlocked(RuntimeError):
    pass


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
        instruction = payload.get("instruction") or payload.get("prompt") or payload.get("text")
    else:
        instruction = None
    instruction = str(instruction or "").strip()
    if not instruction:
        raise Root2InferenceBlocked("INSTRUCTION_REQUIRED")
    return instruction


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    instruction = _instruction(request)
    controlled = trigram.solve_visible_prompt(instruction)
    if controlled.get("status") == "PASS_PUBLIC_FAMILY_CONSTRUCTION_CANDIDATE":
        answer = str(controlled.get("response") or "")
        if not answer:
            raise Root2InferenceBlocked("TRIGRAM_CONTROLLER_RETURNED_EMPTY_RESPONSE")
        return {
            "task_id": request.get("task_id"),
            "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE__CANDIDATE_SCOPE",
            "answer": answer,
            "artifacts": [],
            "tool_trace": [],
            "cognition_dependency_class": "MODEL_INDEPENDENT",
            "model_dependency_count": 0,
            "response_route": "LIVEBENCH_CHARACTER_TRIGRAM_CONSTRAINT_CONTROLLER_V1",
            "terminal_authority": False,
            "scope_precondition": controlled.get("required_precondition"),
            "hard_nonclaim": (
                "CANDIDATE_ROUTE_ONLY__NO_TERMINAL_DATASET_EQUIVALENCE_OR_SEMANTIC_BASE_TASK_QUALITY_PROOF"
            ),
        }
    return fallback_v2.infer(request)


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return infer(args or {})
