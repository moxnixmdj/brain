#!/usr/bin/env python3
"""Total Brain-native HLE proposal/commitment orchestrator V1.

Every task receives a precommittable final answer string. Native proposal lanes
are tried without gold or external reasoning-model output. If no lane produces a
candidate, the solver emits UNKNOWN with zero confidence. Totality is therefore
an execution property, never a correctness claim.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable, Mapping

SCHEMA = "PROJECT_BRAIN_HLE_NATIVE_TOTAL_SOLVER_V1"
_MCQ = re.compile(r"(?mi)^\s*Answer Choices:\s*$")


def _sha_text(v: str) -> str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()


def _confidence(receipt: Mapping[str, Any] | None, lane: str) -> int:
    if not receipt:
        return 0
    band = str(receipt.get("confidence_band") or "").upper()
    if band == "HIGH": return 70
    if band == "MEDIUM": return 50
    if band == "LOW": return 25
    if lane == "SYMBOLIC_SURFACE": return 60
    return 35


def solve(
    *,
    task_id: str,
    question: str,
    image: str = "",
    search_fn: Callable[..., Mapping[str, Any]] | None = None,
    fetch_fn: Callable[..., Mapping[str, Any]] | None = None,
    ocr_fn: Callable[[Any], str] | None = None,
    mcq_proposer: Callable[..., Mapping[str, Any]] | None = None,
    symbolic_proposer: Callable[..., Mapping[str, Any]] | None = None,
    retrieval_proposer: Callable[..., Mapping[str, Any]] | None = None,
    image_observer: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("TASK_ID_REQUIRED")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("QUESTION_REQUIRED")
    if not isinstance(image, str):
        raise ValueError("IMAGE_MUST_BE_STRING")

    if mcq_proposer is None:
        from canonical.runtime.hle_mcq_retrieval_vote_v1 import propose as mcq_proposer
    if symbolic_proposer is None:
        from canonical.runtime.hle_symbolic_surface_solver_v1 import propose as symbolic_proposer
    if retrieval_proposer is None:
        from canonical.runtime.hle_exact_retrieval_extract_v2 import propose as retrieval_proposer
    if image_observer is None:
        from canonical.runtime.hle_image_observation_v1 import observe as image_observer

    original_image = bool(image)
    image_receipt = None
    augmented_question = question
    image_semantics_available = False
    if original_image:
        try:
            image_receipt = image_observer(image_data_uri=image, ocr_fn=ocr_fn)
        except Exception as exc:
            image_receipt = {
                "status": "FAIL_CLOSED__IMAGE_OBSERVATION_FAILED",
                "error_class": type(exc).__name__,
                "intrinsic_brain_vision_claimed": False,
                "external_reasoning_model_calls": 0,
            }
        if image_receipt.get("status") == "OBSERVED":
            ocr = str(image_receipt.get("ocr_text") or "").strip()
            if ocr:
                augmented_question = (
                    "[LOCAL OCR TOOL OBSERVATION]\n" + ocr +
                    "\n[END LOCAL OCR TOOL OBSERVATION]\n" + question
                )
                image_semantics_available = True

    attempts = []
    chosen = None
    chosen_lane = None

    def try_lane(name: str, fn: Callable[..., Mapping[str, Any]], kwargs: dict[str, Any]):
        nonlocal chosen, chosen_lane
        try:
            receipt = dict(fn(**kwargs))
        except Exception as exc:
            receipt = {"status": "LANE_EXCEPTION", "error_class": type(exc).__name__, "candidate_answer": None}
        attempts.append({
            "lane": name,
            "status": receipt.get("status"),
            "candidate_present": isinstance(receipt.get("candidate_answer"), str) and bool(receipt.get("candidate_answer")),
            "candidate_answer_authority": bool(receipt.get("candidate_answer_authority", False)),
            "external_model_calls": int(receipt.get("external_model_calls", 0) or 0),
            "model_dependency_count": int(receipt.get("model_dependency_count", 0) or 0),
        })
        cand = receipt.get("candidate_answer")
        if chosen is None and isinstance(cand, str) and cand:
            chosen = (cand, receipt)
            chosen_lane = name

    if _MCQ.search(question):
        try_lane("MCQ_RETRIEVAL_VOTE", mcq_proposer, {
            "task_id": task_id,
            "question": augmented_question,
            "has_nonempty_image_payload": original_image and not image_semantics_available,
            "search_fn": search_fn,
            "fetch_fn": fetch_fn,
        })
    else:
        try_lane("SYMBOLIC_SURFACE", symbolic_proposer, {
            "task_id": task_id,
            "question": augmented_question,
            "has_nonempty_image_payload": original_image and not image_semantics_available,
        })
        if chosen is None:
            try_lane("EXACT_RETRIEVAL_V2", retrieval_proposer, {
                "task_id": task_id,
                "question": augmented_question,
                "has_nonempty_image_payload": original_image and not image_semantics_available,
                "search_fn": search_fn,
                "fetch_fn": fetch_fn,
            })

    if chosen is None:
        final_answer = "UNKNOWN"
        abstained = True
        confidence = 0
        explanation = "No Brain-native supported proposal lane produced a candidate."
    else:
        final_answer, receipt = chosen
        abstained = False
        confidence = _confidence(receipt, chosen_lane or "")
        explanation = f"Brain-native proposal lane: {chosen_lane}."

    final_response = (
        f"Explanation: {explanation}\n"
        f"Answer: {final_answer}\n"
        f"Confidence: {confidence}%"
    )
    input_binding = {
        "task_id": task_id,
        "question_sha256": _sha_text(question),
        "image_data_uri_sha256": _sha_text(image) if image else None,
    }
    input_sha256 = _sha_text(json.dumps(input_binding, sort_keys=True, separators=(",", ":")))
    return {
        "schema": SCHEMA,
        "status": "PRECOMMITTABLE_CANDIDATE" if not abstained else "PRECOMMITTABLE_ABSTENTION",
        "task_id": task_id,
        "input_sha256": input_sha256,
        "question_sha256": input_binding["question_sha256"],
        "image_data_uri_sha256": input_binding["image_data_uri_sha256"],
        "final_answer": final_answer,
        "final_answer_sha256": _sha_text(final_answer),
        "final_response": final_response,
        "final_response_sha256": _sha_text(final_response),
        "confidence_percent": confidence,
        "abstained": abstained,
        "selected_lane": chosen_lane,
        "attempts": attempts,
        "image_observation": ({
            "status": image_receipt.get("status"),
            "image_sha256": image_receipt.get("image_sha256"),
            "ocr_text_sha256": image_receipt.get("ocr_text_sha256"),
            "ocr_chars": image_receipt.get("ocr_chars"),
            "local_ocr_tool_used": image_receipt.get("local_ocr_tool_used", False),
            "intrinsic_brain_vision_claimed": False,
        } if image_receipt else None),
        "precommittable": True,
        "gold_accessed": False,
        "external_reasoning_model_calls": 0,
        "external_model_solver_output_used": False,
        "brain_capability_claim_from_external_model": False,
        "correctness_claimed": False,
        "target_score_claimed": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "hard_nonclaim": "TOTAL_PRECOMMITTABLE_OUTPUT_DOES_NOT_IMPLY_SCORE_ADEQUACY_OR_CORRECTNESS",
    }
