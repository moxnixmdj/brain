#!/usr/bin/env python3
"""Brain-native HLE semantic compiler V1.

Scope is deliberately narrow and fail-closed:
- compile HLE multipleChoice questions whose inline options follow the public
  ``Answer Choices:`` + ``A. ...`` convention into a typed alternative set;
- derive bounded, contamination-safer lexical research queries from the stem
  and each option without emitting the whole benchmark question as a search query;
- preserve exact task/input hashes and raw spans for later verified execution;
- reject unsupported or ambiguous syntax;
- do NOT solve the question, call a model, inspect gold, or claim terminal credit.

Exact-match semantic compilation remains explicitly unresolved in V1.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_HLE_NATIVE_SEMANTIC_COMPILER_V1"
_MC = "multipleChoice"
_EXACT = "exactMatch"
_MARKER = re.compile(r"(?mi)^[ \t]*Answer Choices:[ \t]*$")
_OPTION_START = re.compile(r"(?m)^[ \t]*([A-Z])\.[ \t]+")
_WORD = re.compile(r"[^\W_]+(?:[-/][^\W_]+)*", re.UNICODE)
_STOP = {
    "a","an","and","are","as","at","be","been","being","but","by","can","could",
    "do","does","for","from","had","has","have","how","if","in","into","is","it",
    "may","might","must","of","on","or","should","that","the","their","then","there",
    "these","this","those","to","was","were","what","when","where","which","who",
    "whom","whose","why","will","with","would","answer","answers","choice","choices",
    "choose","following","option","options","question","select","correct","best",
}
_MAX_QUESTION_CHARS = 200_000
_MAX_CHOICES = 26
_MAX_QUERY_TOKENS = 36
_MAX_QUERY_CHARS = 700


class HLESemanticCompileError(ValueError):
    pass


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canon_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).strip().split())


def _tokens(value: str) -> list[str]:
    out: list[str] = []
    for raw in _WORD.findall(_canon_text(value)):
        token = raw.casefold().strip("-/")
        if len(token) < 2 or token in _STOP:
            continue
        if token not in out:
            out.append(token)
    return out


def _bounded_query(stem: str, option_text: str | None = None) -> dict[str, Any]:
    stem_tokens = _tokens(stem)
    option_tokens = _tokens(option_text or "")
    # Keep option-specific discriminators first, then the stem subject. This is
    # intentionally lexical and never uses the full raw question verbatim.
    merged: list[str] = []
    for token in [*option_tokens[:14], *stem_tokens]:
        if token not in merged:
            merged.append(token)
        if len(merged) >= _MAX_QUERY_TOKENS:
            break
    query = " ".join(merged)
    if len(query) > _MAX_QUERY_CHARS:
        query = query[:_MAX_QUERY_CHARS].rsplit(" ", 1)[0]
    if not query:
        raise HLESemanticCompileError("RESEARCH_QUERY_EMPTY")
    return {
        "query": query,
        "query_sha256": _sha_text(query),
        "token_count": len(query.split()),
        "full_question_verbatim_used": False,
        "method": "OPTION_DISCRIMINATORS_THEN_DEDUPLICATED_STEM_CONTENT_TOKENS",
    }


def _parse_mc(question: str) -> tuple[str, list[dict[str, Any]]]:
    markers = list(_MARKER.finditer(question))
    if len(markers) != 1:
        raise HLESemanticCompileError(
            "ANSWER_CHOICES_MARKER_CARDINALITY:" + str(len(markers))
        )
    marker = markers[0]
    stem = question[:marker.start()].strip()
    block = question[marker.end():]
    if not stem:
        raise HLESemanticCompileError("QUESTION_STEM_EMPTY")

    starts = list(_OPTION_START.finditer(block))
    if len(starts) < 2 or len(starts) > _MAX_CHOICES:
        raise HLESemanticCompileError("OPTION_COUNT_OUT_OF_RANGE")
    letters = [m.group(1) for m in starts]
    expected = [chr(ord("A") + i) for i in range(len(letters))]
    if letters != expected:
        raise HLESemanticCompileError(
            "OPTION_LETTERS_NOT_CONTIGUOUS_FROM_A:" + ",".join(letters)
        )

    leading = block[:starts[0].start()]
    if leading.strip():
        raise HLESemanticCompileError("TEXT_BEFORE_FIRST_OPTION")

    choices: list[dict[str, Any]] = []
    for i, m in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(block)
        text_start = m.end()
        raw_text = block[text_start:end].strip()
        if not raw_text:
            raise HLESemanticCompileError("OPTION_TEXT_EMPTY:" + m.group(1))
        # Exact spans bind the compiler output to source bytes/chars without
        # requiring downstream components to trust reparsed labels.
        abs_label_start = marker.end() + m.start()
        abs_text_start = marker.end() + text_start
        abs_end = marker.end() + end
        choices.append({
            "id": m.group(1),
            "label": raw_text,
            "source_span_chars": [abs_text_start, abs_end],
            "source_label_span_chars": [abs_label_start, abs_text_start],
            "label_sha256": _sha_text(raw_text),
        })
    return stem, choices


def compile_question(
    *,
    task_id: str,
    answer_type: str,
    question: str,
    has_nonempty_image_payload: bool = False,
) -> dict[str, Any]:
    if not isinstance(task_id, str) or not task_id.strip():
        raise HLESemanticCompileError("TASK_ID_REQUIRED")
    if answer_type not in {_MC, _EXACT}:
        raise HLESemanticCompileError("ANSWER_TYPE_INVALID")
    if not isinstance(question, str) or not question.strip():
        raise HLESemanticCompileError("QUESTION_REQUIRED")
    if len(question) > _MAX_QUESTION_CHARS:
        raise HLESemanticCompileError("QUESTION_TOO_LONG")
    if type(has_nonempty_image_payload) is not bool:
        raise HLESemanticCompileError("IMAGE_FLAG_MUST_BE_BOOLEAN")

    base = {
        "schema": SCHEMA,
        "task_id": task_id.strip(),
        "answer_type": answer_type,
        "question_sha256": _sha_text(question),
        "has_nonempty_image_payload": has_nonempty_image_payload,
        "gold_accessed": False,
        "external_model_calls": 0,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

    if answer_type == _EXACT:
        return {
            **base,
            "status": "UNRESOLVED__EXACT_MATCH_SEMANTIC_COMPILATION_NOT_IN_V1",
            "pass": False,
            "reason": "V1_ONLY_PROVES_THE_PUBLIC_INLINE_MULTIPLE_CHOICE_SYNTAX_LANE",
            "candidate_answer_authority": False,
        }

    try:
        stem, choices = _parse_mc(question)
        stem_focus = _bounded_query(stem)
        alternatives = []
        for choice in choices:
            alternatives.append({
                **choice,
                "research_focus": _bounded_query(stem, choice["label"]),
            })
    except HLESemanticCompileError as exc:
        return {
            **base,
            "status": "FAIL_CLOSED__MCQ_SYNTAX_UNRESOLVED",
            "pass": False,
            "reason": str(exc),
            "candidate_answer_authority": False,
        }

    typed = {
        "schema": "PROJECT_BRAIN_HLE_TYPED_MULTIPLE_CHOICE_DECISION_V1",
        "task_id": task_id.strip(),
        "question_sha256": base["question_sha256"],
        "stem": stem,
        "stem_sha256": _sha_text(stem),
        "stem_research_focus": stem_focus,
        "alternatives": alternatives,
        "answer_contract": {
            "kind": "BARE_OPTION_LETTER",
            "allowed_values": [x["id"] for x in alternatives],
        },
        "image_requirement": (
            "IMAGE_SEMANTICS_REQUIRED_UPSTREAM"
            if has_nonempty_image_payload
            else "NO_NONEMPTY_IMAGE_PAYLOAD"
        ),
    }
    typed_sha = hashlib.sha256(
        json.dumps(typed, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        **base,
        "status": "COMPILED__MCQ_TYPED_ALTERNATIVES__ANSWER_NOT_DECIDED",
        "pass": True,
        "typed_decision": typed,
        "typed_decision_sha256": typed_sha,
        "candidate_answer_authority": False,
        "next_required_capability": (
            "VERIFIED_IMAGE_SEMANTICS_AND_OPTION_RELATION_EVIDENCE"
            if has_nonempty_image_payload
            else "VERIFIED_OPTION_RELATION_EVIDENCE"
        ),
        "hard_nonclaim": "SYNTACTIC_AND_LEXICAL_COMPILATION_DOES_NOT_ESTABLISH_WHICH_OPTION_IS_CORRECT",
    }


def main() -> int:
    # Self-test uses synthetic content only.
    q = """Synthetic stem about alpha beta?
Answer Choices:
A. First synthetic option
B. Second synthetic option
C. Third synthetic option"""
    out = compile_question(task_id="synthetic", answer_type=_MC, question=q)
    assert out["pass"] is True
    assert [x["id"] for x in out["typed_decision"]["alternatives"]] == ["A", "B", "C"]
    assert out["candidate_answer_authority"] is False
    assert all(
        x["research_focus"]["full_question_verbatim_used"] is False
        for x in out["typed_decision"]["alternatives"]
    )
    exact = compile_question(task_id="synthetic2", answer_type=_EXACT, question="2+2?")
    assert exact["pass"] is False
    print("SELF_TEST_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
