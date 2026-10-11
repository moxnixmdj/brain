#!/usr/bin/env python3
"""Brain-native HLE question-contract compiler V1.

Compiles visible question syntax into an answer-shape/research contract.
No model calls, no gold, no answer_type metadata dependency, and no answer authority.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from canonical.runtime import hle_native_semantic_compiler_v1 as mcq

SCHEMA = "PROJECT_BRAIN_HLE_NATIVE_QUESTION_CONTRACT_V1"
_WORD = re.compile(r"[^\W_]+(?:[-/][^\W_]+)*", re.UNICODE)
_MC_MARKER = re.compile(r"(?mi)^[ \t]*Answer Choices:[ \t]*$")
_NEG = re.compile(
    r"\b(?:not|never|except|excluding|incorrect|false|least\s+likely|"
    r"least\s+probable|cannot|can't|doesn't|does\s+not|isn't|is\s+not)\b",
    re.IGNORECASE,
)
_STOP = {
    "a","an","and","are","as","at","be","been","being","but","by","can","could",
    "did","do","does","for","from","had","has","have","how","if","in","into","is",
    "it","may","might","must","of","on","or","should","that","the","their","then",
    "there","these","this","those","to","was","were","what","when","where","which",
    "who","whom","whose","why","will","with","would","answer","answers","question",
    "find","determine","identify","name","calculate","compute","evaluate","solve",
    "given","following","stated","under","according","using","value","number",
}
_MAX_TOKENS = 36
_MAX_QUERY_CHARS = 700
_MAX_QUESTION_CHARS = 200_000


class QuestionContractError(ValueError):
    pass


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canon(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).strip().split())


def _tokens(text: str) -> list[str]:
    out: list[str] = []
    for raw in _WORD.findall(_canon(text)):
        tok = raw.casefold().strip("-/")
        if len(tok) < 2 or tok in _STOP:
            continue
        if tok not in out:
            out.append(tok)
    return out


def _research_focus(question: str) -> dict[str, Any]:
    canon = _canon(question)
    quoted = [
        _canon(x)
        for x in re.findall(r'["“‘\']([^"”’\']{2,120})["”’\']', canon)
        if _canon(x)
    ]
    toks = _tokens(canon)
    # Prefer long discriminators, but preserve a few early content tokens to avoid
    # turning a technical question into a bag of rare suffixes.
    long = sorted(toks, key=lambda x: (-len(x), toks.index(x)))
    ordered: list[str] = []
    for piece in [*quoted[:2], *toks[:8], *long]:
        low = piece.casefold()
        if low not in {x.casefold() for x in ordered}:
            ordered.append(piece)
        if len(ordered) >= _MAX_TOKENS:
            break
    query = " ".join(ordered)
    if len(query) > _MAX_QUERY_CHARS:
        query = query[:_MAX_QUERY_CHARS].rsplit(" ", 1)[0]
    if not query:
        raise QuestionContractError("RESEARCH_FOCUS_EMPTY")
    if _canon(query).casefold() == canon.casefold():
        # A bounded query must not simply replay the whole benchmark item.
        if len(ordered) <= 1:
            raise QuestionContractError("RESEARCH_FOCUS_WOULD_BE_VERBATIM")
        query = " ".join(ordered[:-1])
    return {
        "query": query,
        "query_sha256": _sha(query),
        "token_count": len(query.split()),
        "full_question_verbatim_used": False,
        "method": "QUOTED_ANCHORS_PLUS_BOUNDED_DEDUPLICATED_CONTENT_TOKENS",
    }


def _tail(question: str) -> str:
    canon = _canon(question)
    parts = [x.strip() for x in re.split(r"(?<=[.!?])\s+", canon) if x.strip()]
    return parts[-1] if parts else canon


def _classify(question: str) -> str | None:
    tail = _tail(question)

    if re.search(r"\b(?:what|which)\s+year\b|\bin\s+what\s+year\b", tail, re.I):
        return "YEAR"
    if re.match(r"^\s*who\b", tail, re.I):
        return "PERSON"
    if re.match(r"^\s*when\b", tail, re.I):
        return "DATE_OR_TIME"
    if re.match(r"^\s*where\b", tail, re.I):
        return "LOCATION"
    if re.match(r"^\s*(?:calculate|compute|evaluate|solve|derive)\b", tail, re.I):
        return "SYMBOLIC_OR_NUMBER"
    if re.search(r"\b(?:equation|formula|expression)\b", tail, re.I) and re.match(
        r"^\s*(?:what|which|give|write|state)\b", tail, re.I
    ):
        return "SYMBOLIC_EXPRESSION"
    if re.search(
        r"\b(?:how\s+many|how\s+much|percentage|percent|fraction|count)\b",
        tail,
        re.I,
    ):
        return "NUMBER"
    if re.search(
        r"\bwhat\s+(?:is|was|are|were)\s+the\s+"
        r"(?:value|number|count|mass|length|distance|frequency|wavelength|energy|"
        r"probability|ratio|rate|magnitude)\b",
        tail,
        re.I,
    ):
        return "NUMBER_OR_EXPRESSION"
    if re.match(r"^\s*(?:identify|name)\b", tail, re.I):
        return "ENTITY_OR_TERM"
    if re.search(
        r"\b(?:known\s+as|called|termed|designated|author|inventor|discoverer|"
        r"species|gene|protein|enzyme|theorem|compound|material|molecule|organism|"
        r"algorithm|method|law|principle)\b",
        tail,
        re.I,
    ) and re.match(r"^\s*(?:what|which|who)\b", tail, re.I):
        return "ENTITY_OR_TERM"
    if re.match(
        r"^\s*(?:is|are|was|were|does|do|did|can|could|has|have|had|will|would)\b",
        tail,
        re.I,
    ):
        return "BOOLEAN"
    if re.match(r"^\s*why\b", tail, re.I) or re.match(
        r"^\s*how\s+(?:does|do|did|can|could|is|are|was|were)\b", tail, re.I
    ):
        return "EXPLANATION"
    if re.match(r"^\s*(?:what|which)\b", tail, re.I):
        return "SHORT_TEXT"
    return None


def compile_question(
    *,
    task_id: str,
    question: str,
    has_nonempty_image_payload: bool = False,
) -> dict[str, Any]:
    if not isinstance(task_id, str) or not task_id.strip():
        raise QuestionContractError("TASK_ID_REQUIRED")
    if not isinstance(question, str) or not question.strip():
        raise QuestionContractError("QUESTION_REQUIRED")
    if len(question) > _MAX_QUESTION_CHARS:
        raise QuestionContractError("QUESTION_TOO_LONG")
    if type(has_nonempty_image_payload) is not bool:
        raise QuestionContractError("IMAGE_FLAG_MUST_BE_BOOLEAN")

    base = {
        "schema": SCHEMA,
        "task_id": task_id.strip(),
        "question_sha256": _sha(question),
        "has_nonempty_image_payload": has_nonempty_image_payload,
        "gold_accessed": False,
        "answer_type_metadata_consumed": False,
        "external_model_calls": 0,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "candidate_answer_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

    # Visible syntax is fair game: the solver itself sees the question text.
    if _MC_MARKER.search(question):
        try:
            compiled = mcq.compile_question(
                task_id=task_id,
                answer_type="multipleChoice",
                question=question,
                has_nonempty_image_payload=has_nonempty_image_payload,
            )
        except Exception as exc:
            return {
                **base,
                "status": "FAIL_CLOSED__VISIBLE_MCQ_COMPILATION_ERROR",
                "pass": False,
                "reason": type(exc).__name__ + ":" + str(exc),
            }
        if compiled.get("pass") is not True:
            return {
                **base,
                "status": "FAIL_CLOSED__VISIBLE_MCQ_SYNTAX_UNRESOLVED",
                "pass": False,
                "reason": compiled.get("reason"),
            }
        typed = compiled["typed_decision"]
        return {
            **base,
            "status": "COMPILED__VISIBLE_MCQ_ANSWER_CONTRACT",
            "pass": True,
            "answer_contract": typed["answer_contract"],
            "question_kind": "BARE_OPTION_LETTER",
            "polarity": "NEGATIVE" if _NEG.search(_tail(question)) else "POSITIVE",
            "research_focus": typed["stem_research_focus"],
            "alternatives": typed["alternatives"],
            "image_requirement": typed["image_requirement"],
            "typed_decision_sha256": compiled["typed_decision_sha256"],
            "hard_nonclaim": "QUESTION_CONTRACT_COMPILATION_DOES_NOT_ESTABLISH_THE_CORRECT_OPTION",
        }

    kind = _classify(question)
    if kind is None:
        return {
            **base,
            "status": "FAIL_CLOSED__QUESTION_SURFACE_UNRESOLVED",
            "pass": False,
            "question_kind": None,
            "reason": "NO_VERIFIED_QUESTION_SURFACE_RULE",
        }

    try:
        focus = _research_focus(question)
    except QuestionContractError as exc:
        return {
            **base,
            "status": "FAIL_CLOSED__RESEARCH_FOCUS_UNRESOLVED",
            "pass": False,
            "question_kind": kind,
            "reason": str(exc),
        }

    answer_contract = {
        "kind": kind,
        "polarity": "NEGATIVE" if _NEG.search(_tail(question)) else "POSITIVE",
        "format_authority": False,
    }
    return {
        **base,
        "status": "COMPILED__QUESTION_ANSWER_SHAPE_AND_RESEARCH_FOCUS",
        "pass": True,
        "question_kind": kind,
        "polarity": answer_contract["polarity"],
        "answer_contract": answer_contract,
        "research_focus": focus,
        "image_requirement": (
            "IMAGE_SEMANTICS_REQUIRED_UPSTREAM"
            if has_nonempty_image_payload
            else "NO_NONEMPTY_IMAGE_PAYLOAD"
        ),
        "hard_nonclaim": "ANSWER_SHAPE_AND_RESEARCH_FOCUS_DO_NOT_ESTABLISH_CANDIDATE_CORRECTNESS",
    }


if __name__ == "__main__":
    sample = compile_question(
        task_id="synthetic",
        question="Who discovered the fictional Zephyr particle?",
    )
    assert sample["pass"] is True
    assert sample["question_kind"] == "PERSON"
    assert sample["model_dependency_count"] == 0
    print("SELF_TEST_PASS")
