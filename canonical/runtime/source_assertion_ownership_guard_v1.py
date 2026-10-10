"""Bounded assertion-ownership guard for source-aligned semantic projection V1.

This module grants no semantic truth. It is a veto layer that prevents a
positive inner clause from being laundered out of quotation, attribution,
denial, interrogation, or hypothetical/conditional scope.

V1 is deliberately conservative. Unknown or structurally unsafe ownership
remains unresolved rather than being treated as a direct assertion.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_SOURCE_ASSERTION_OWNERSHIP_GUARD_V1"

_STANCE = re.compile(
    r"\b(?:say|says|said|claim|claims|claimed|report|reports|reported|"
    r"argue|argues|argued|allege|alleges|alleged|believe|believes|believed|"
    r"suggest|suggests|suggested|assert|asserts|asserted|state|states|stated|"
    r"deny|denies|denied|reject|rejects|rejected|dispute|disputes|disputed)\b",
    re.I,
)
_ATTRIBUTIVE = re.compile(
    r"\b(?:according\s+to|allegedly|reportedly|purportedly)\b",
    re.I,
)
_NEGATION = re.compile(
    r"\b(?:not|never|no\s+longer|cannot|can't|cant|isn't|isnt|wasn't|wasnt|"
    r"doesn't|doesnt|didn't|didnt)\b",
    re.I,
)
_HYPOTHETICAL = re.compile(
    r"\b(?:if|assuming|assume|supposing|suppose|hypothetically|whether|"
    r"would|might|could|perhaps|possibly)\b",
    re.I,
)
_QUOTE_CHARS = {'"': '"', "“": "”", "‘": "’"}


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "safe_for_direct_semantic_projection": False,
        "semantic_truth_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _sentence_spans(text: str):
    start = 0
    n = len(text)
    for i, ch in enumerate(text):
        boundary = ch in "!?";
        if ch == ".":
            decimal = (
                i > 0
                and i + 1 < n
                and text[i - 1].isdigit()
                and text[i + 1].isdigit()
            )
            boundary = not decimal
        if not boundary:
            continue
        raw = text[start:i + 1]
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        if right > left:
            yield start + left, start + right, raw[left:right]
        start = i + 1
    if start < n:
        raw = text[start:]
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        if right > left:
            yield start + left, start + right, raw[left:right]


def containing_sentence(
    source_text: str,
    *,
    start: int,
    end: int,
) -> tuple[int, int, str] | None:
    for left, right, sentence in _sentence_spans(source_text):
        if left <= start and end <= right:
            return left, right, sentence
    return None


def _contains_balanced_quote(sentence: str) -> bool:
    for opening, closing in _QUOTE_CHARS.items():
        if opening == closing:
            if sentence.count(opening) >= 2:
                return True
        elif opening in sentence and closing in sentence:
            return True
    return False


def check_direct_assertion(
    source_text: str,
    *,
    start: int,
    end: int,
    require_selected_span_is_complete_sentence: bool = True,
) -> dict[str, Any]:
    if not isinstance(source_text, str) or not source_text:
        return _base("FAIL_CLOSED", reason="SOURCE_TEXT_REQUIRED")
    if (
        isinstance(start, bool)
        or not isinstance(start, int)
        or isinstance(end, bool)
        or not isinstance(end, int)
        or start < 0
        or end <= start
        or end > len(source_text)
    ):
        return _base("FAIL_CLOSED", reason="SOURCE_SPAN_INVALID")

    selected_surface = source_text[start:end]
    if _contains_balanced_quote(selected_surface):
        return _base(
            "UNRESOLVED__QUOTED_SCOPE",
            selected_span=[start, end],
        )

    found = containing_sentence(source_text, start=start, end=end)
    if found is None:
        return _base("FAIL_CLOSED", reason="CONTAINING_SENTENCE_NOT_FOUND")
    sentence_start, sentence_end, sentence = found

    if require_selected_span_is_complete_sentence and (
        start != sentence_start or end != sentence_end
    ):
        return _base(
            "UNRESOLVED__ASSERTION_COMPLETE_SPAN_UNPROVED",
            reason="SELECTED_SPAN_IS_PROPER_SUBSPAN_OF_CONTAINING_SENTENCE",
            selected_span=[start, end],
            containing_sentence_span=[sentence_start, sentence_end],
            containing_sentence=sentence,
        )

    if sentence.rstrip().endswith("?"):
        return _base(
            "UNRESOLVED__INTERROGATIVE_SCOPE",
            containing_sentence_span=[sentence_start, sentence_end],
        )
    if _contains_balanced_quote(sentence):
        return _base(
            "UNRESOLVED__QUOTED_SCOPE",
            containing_sentence_span=[sentence_start, sentence_end],
        )
    if _STANCE.search(sentence) or _ATTRIBUTIVE.search(sentence):
        return _base(
            "UNRESOLVED__ATTRIBUTED_OR_STANCE_SCOPE",
            containing_sentence_span=[sentence_start, sentence_end],
        )
    if _NEGATION.search(sentence):
        return _base(
            "UNRESOLVED__NEGATED_SCOPE",
            containing_sentence_span=[sentence_start, sentence_end],
        )
    if _HYPOTHETICAL.search(sentence):
        return _base(
            "UNRESOLVED__HYPOTHETICAL_OR_CONDITIONAL_SCOPE",
            containing_sentence_span=[sentence_start, sentence_end],
        )

    return _base(
        "PASS__DIRECT_ASSERTION_OWNERSHIP_NOT_CONTRADICTED",
        passed=True,
        safe_for_direct_semantic_projection=True,
        selected_span=[start, end],
        containing_sentence_span=[sentence_start, sentence_end],
        containing_sentence=sentence,
        boundary=(
            "VETO_ONLY__NO_SEMANTIC_TRUTH_AUTHORITY__"
            "CONSERVATIVE_DIRECT_ASSERTION_SCOPE_FOR_BOUNDED_SOURCE_PROJECTION"
        ),
    )
