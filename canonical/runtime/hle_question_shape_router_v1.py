#!/usr/bin/env python3
"""Brain-native HLE question-shape router V1.

This is a structural router, not a semantic solver. It uses generic public
question-form and notation features to choose a downstream *candidate lane*.
It never reads gold, never calls a model, and grants no answer authority.

The router deliberately returns multiple compatible lanes when syntax overlaps;
downstream verifiers must resolve the actual semantics or fail closed.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

SCHEMA = "PROJECT_BRAIN_HLE_QUESTION_SHAPE_ROUTER_V1"

_MATH = re.compile(
    r"\\\(|\\\[|\$|\\frac|\\sqrt|\\sum|\\int|\\lim|\\log|\\sin|\\cos|\\tan|"
    r"\\begin\{|\\mathbf|\\mathbb|\\mathrm|\^|_[A-Za-z0-9{]",
)
_NUMBER = re.compile(r"(?<![A-Za-z])[-+]?(?:\d+(?:,\d{3})*(?:\.\d+)?|\.\d+)(?![A-Za-z])")
_CODE = re.compile(
    r"```|(?:^|\n)\s*(?:def|class)\s+\w+|#include\b|public\s+static\b|"
    r"\bSELECT\s+.+\bFROM\b|(?:^|\n)\s*(?:fn|func)\s+\w+",
    re.I,
)
_TEMPORAL = re.compile(r"\b(?:when|year|date|month|day|century|decade)\b", re.I)
_ENTITY = re.compile(
    r"\b(?:who|what|which|name|called|term|known as|denoted|identify|"
    r"title|author|inventor|discoverer|species|gene|protein|enzyme|theorem)\b",
    re.I,
)
_NUMERIC_ASK = re.compile(
    r"\b(?:how many|how much|calculate|compute|evaluate|solve|find|determine|"
    r"value|number|integer|count|quantity|probability|ratio|percentage|percent|"
    r"length|area|volume|mass|energy|distance|speed|velocity|frequency|wavelength|"
    r"angle|degree|degrees)\b",
    re.I,
)
_BOOLEAN = re.compile(
    r"\b(?:true or false|is it true|whether|must it be|can it be|does there exist)\b",
    re.I,
)
_PROOF = re.compile(r"\b(?:prove|show that|demonstrate that|counterexample)\b", re.I)


class HLEQuestionShapeError(ValueError):
    pass


def _canon(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).strip().split())


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _last_question_clause(question: str) -> str:
    text = _canon(question)
    if not text:
        raise HLEQuestionShapeError("QUESTION_REQUIRED")
    q = text.rfind("?")
    end = q + 1 if q >= 0 else len(text)
    start = max(0, end - 1200)
    window = text[start:end]
    # Use only explicit sentence punctuation as a structural boundary. If this
    # yields a tiny fragment, retain the whole bounded suffix instead.
    parts = [x.strip() for x in re.split(r"(?<=[.!?])\s+", window) if x.strip()]
    tail = parts[-1] if parts else window
    return tail if len(tail) >= 12 else window


def route_question(
    *,
    task_id: str,
    answer_type: str,
    question: str,
    has_nonempty_image_payload: bool = False,
) -> dict[str, Any]:
    if not isinstance(task_id, str) or not task_id.strip():
        raise HLEQuestionShapeError("TASK_ID_REQUIRED")
    if answer_type not in {"exactMatch", "multipleChoice"}:
        raise HLEQuestionShapeError("ANSWER_TYPE_INVALID")
    if not isinstance(question, str) or not question.strip():
        raise HLEQuestionShapeError("QUESTION_REQUIRED")
    if type(has_nonempty_image_payload) is not bool:
        raise HLEQuestionShapeError("IMAGE_FLAG_INVALID")

    tail = _last_question_clause(question)
    lanes: list[str] = []
    reasons: list[str] = []

    if has_nonempty_image_payload:
        lanes.append("IMAGE_SEMANTICS_REQUIRED")
        reasons.append("NONEMPTY_IMAGE_PAYLOAD")

    if answer_type == "multipleChoice":
        lanes.append("MULTIPLE_CHOICE_TYPED_DECISION")
        reasons.append("ANSWER_TYPE_MULTIPLE_CHOICE")

    math_signal = bool(_MATH.search(question))
    number_signal = bool(_NUMBER.search(question))
    numeric_ask = bool(_NUMERIC_ASK.search(tail))
    if math_signal or (number_signal and numeric_ask):
        lanes.append("SYMBOLIC_NUMERIC_REASONING")
        reasons.append(
            "EXPLICIT_MATH_NOTATION" if math_signal else "NUMERIC_CONTENT_PLUS_NUMERIC_QUESTION_FORM"
        )

    if _CODE.search(question):
        lanes.append("PROGRAMMATIC_CODE_REASONING")
        reasons.append("CODE_LIKE_SYNTAX")

    if _BOOLEAN.search(tail):
        lanes.append("BOOLEAN_PROPOSITION")
        reasons.append("BOOLEAN_QUESTION_FORM")

    if _TEMPORAL.search(tail):
        lanes.append("TEMPORAL_LOOKUP_OR_DERIVATION")
        reasons.append("TEMPORAL_QUESTION_FORM")

    entity_signal = bool(_ENTITY.search(tail))
    if entity_signal and not numeric_ask:
        lanes.append("ENTITY_TERM_OR_RELATION_LOOKUP")
        reasons.append("ENTITY_OR_TERM_QUESTION_FORM")

    if _PROOF.search(tail):
        lanes.append("FORMAL_OR_ARGUMENT_PROOF")
        reasons.append("EXPLICIT_PROOF_REQUEST")

    if not lanes:
        lanes.append("OPEN_SEMANTIC_REASONING")
        reasons.append("NO_BOUNDED_STRUCTURAL_LANE_PROVED")

    # Preserve order but remove duplicates.
    lanes = list(dict.fromkeys(lanes))
    reasons = list(dict.fromkeys(reasons))
    return {
        "schema": SCHEMA,
        "status": "ROUTED_STRUCTURALLY",
        "task_id": task_id.strip(),
        "answer_type": answer_type,
        "question_sha256": _sha(question),
        "tail_clause_sha256": _sha(tail),
        "has_nonempty_image_payload": has_nonempty_image_payload,
        "candidate_lanes": lanes,
        "routing_reasons": reasons,
        "primary_lane": lanes[0],
        "answer_authority": False,
        "semantic_authority": False,
        "gold_accessed": False,
        "model_dependency_count": 0,
        "external_model_calls": 0,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "hard_nonclaim": (
            "STRUCTURAL_ROUTING_DOES_NOT_PROVE_QUESTION_SEMANTICS_ANSWER_CORRECTNESS_"
            "OR_LANE_SUFFICIENCY"
        ),
    }


def main() -> int:
    synthetic = route_question(
        task_id="s",
        answer_type="exactMatch",
        question=r"Let x satisfy \(x^2=9\). What is the positive value of x?",
    )
    assert "SYMBOLIC_NUMERIC_REASONING" in synthetic["candidate_lanes"]
    assert synthetic["answer_authority"] is False
    print("SELF_TEST_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
