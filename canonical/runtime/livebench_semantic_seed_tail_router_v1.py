#!/usr/bin/env python3
"""Fail-closed LiveBench router that separates a verified formal suffix from semantic work.

The router never invents a semantic answer. It only:
1) identifies a terminal suffix made entirely of constraints already understood by
   instruction_constraint_compiler_v1,
2) runs the remaining semantic prefix through the existing model-independent route,
3) applies the already-verified seed-preserving postprocessor to the detached suffix,
4) exact-postvalidates the final response.

If any boundary is ambiguous, the current V2 adapter is used unchanged.
"""
from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any, Mapping

from canonical.runtime import instruction_constraint_compiler_v1 as compiler
from canonical.runtime import root2_livebench_if_astra_inference_adapter_v2 as baseline_v2
from canonical.runtime import seed_preserving_instruction_postprocessor_v1 as postprocessor

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_SEMANTIC_SEED_TAIL_ROUTER_V1"
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


def _constraint_signal(constraints: compiler.ConstraintSet) -> bool:
    d = asdict(constraints)
    return any([
        d["exact_response"] is not None,
        d["prefix"] is not None,
        d["suffix"] is not None,
        d["min_words"] is not None,
        d["max_words"] is not None,
        d["min_unique_words"] is not None,
        d["exact_numbers"] is not None,
        bool(d["lowercase_only"]),
        bool(d["uppercase_only"]),
        bool(d["required_literals"]),
        bool(d["forbidden_literals"]),
    ])


def _segments(text: str) -> list[str]:
    return [
        x.strip()
        for x in re.split(r"(?<=[.!?])\s+|\n+", str(text or "").strip())
        if x.strip()
    ]


def _boundary_positions(text: str) -> list[tuple[int, int]]:
    spans = []
    for m in re.finditer(r"(?<=[.!?])\s+|\n+", text):
        spans.append((m.start(), m.end()))
    out = []
    for span in spans:
        if not out or span != out[-1]:
            out.append(span)
    return out


def isolate_formal_tail(instruction: str) -> dict[str, Any]:
    text = str(instruction or "").strip()
    if not text:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "INSTRUCTION_REQUIRED"}

    try:
        full_constraints = compiler.compile_constraints(text)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "FULL_CONSTRAINT_COMPILE_FAILED:" + type(exc).__name__,
        }
    if not _constraint_signal(full_constraints):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "NO_RECOGNIZED_FORMAL_CONSTRAINTS",
        }

    boundaries = _boundary_positions(text)
    for start, end in reversed(boundaries):
        semantic = text[:start].strip()
        suffix = text[end:].strip()
        if not semantic or not suffix:
            continue

        parts = _segments(suffix)
        if not parts:
            continue

        try:
            per_part = [compiler.compile_constraints(part) for part in parts]
            suffix_constraints = compiler.compile_constraints(suffix)
            semantic_constraints = compiler.compile_constraints(semantic)
        except Exception:
            continue

        if not all(_constraint_signal(c) for c in per_part):
            continue
        if not _constraint_signal(suffix_constraints):
            continue
        if _constraint_signal(semantic_constraints):
            continue
        if asdict(suffix_constraints) != asdict(full_constraints):
            continue

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "semantic_seed_goal": semantic,
            "formal_tail": suffix,
            "formal_segment_count": len(parts),
            "constraint_signature": asdict(suffix_constraints),
            "fail_closed_boundary_proof": True,
        }

    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "error": "NO_UNAMBIGUOUS_FORMAL_SUFFIX",
    }


def infer(request: Mapping[str, Any]) -> dict[str, Any]:
    instruction = _instruction(request)

    try:
        formal_only = compiler.synthesize_formal_only(instruction)
    except Exception:
        formal_only = {"status": "BLOCKED"}
    if (
        formal_only.get("status") == "PASS"
        and formal_only.get("semantic_seed_required") is False
    ):
        return baseline_v2.infer(request)

    split = isolate_formal_tail(instruction)
    if split.get("status") != "PASS":
        return baseline_v2.infer(request)

    semantic_request = dict(request)
    semantic_request["task_payload"] = split["semantic_seed_goal"]

    seed_result = baseline_v2.infer(semantic_request)
    if seed_result.get("cognition_dependency_class") != "MODEL_INDEPENDENT":
        raise Root2InferenceBlocked("SEMANTIC_SEED_MODEL_DEPENDENCY_FORBIDDEN")
    seed = str(seed_result.get("answer") or "").strip()
    if not seed:
        raise Root2InferenceBlocked("SEMANTIC_SEED_EMPTY")

    repaired = postprocessor.transform(seed, split["formal_tail"])
    if repaired.get("status") != "PASS":
        return baseline_v2.infer(request)

    answer = str(repaired.get("response") or "")
    constraints = compiler.compile_constraints(split["formal_tail"])
    ok, errors = compiler.validate_response(answer, constraints)
    if not ok:
        raise Root2InferenceBlocked(
            "TAIL_POSTVALIDATION_FAILED:" + ",".join(errors)
        )

    return {
        "task_id": request.get("task_id"),
        "status": "PASS__MODEL_INDEPENDENT_BRAIN_RESPONSE",
        "answer": answer,
        "artifacts": seed_result.get("artifacts") or [],
        "tool_trace": seed_result.get("tool_trace") or [],
        "cognition_dependency_class": "MODEL_INDEPENDENT",
        "model_dependency_count": 0,
        "response_route": "LIVEBENCH_SEMANTIC_SEED_TAIL_ROUTER_V1",
        "semantic_seed_route": seed_result.get("response_route"),
        "formal_segment_count": split["formal_segment_count"],
        "tail_postvalidated": True,
        "terminal_authority": False,
    }
