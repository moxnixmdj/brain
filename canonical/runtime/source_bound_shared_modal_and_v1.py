"""Source-bound decomposition for one shared-modal flat AND requirement.

Recognizes only a deliberately narrow pattern:
    <prefix> MUST|SHALL|REQUIRED TO <left> AND <right>

Each derived obligation is represented by two exact source spans:
the shared modal/prefix span and one conjunct span. No claim is made that a
synthetic reconstructed clause was contiguous in the source.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "BRAIN_SOURCE_BOUND_SHARED_MODAL_AND_V1"

_MODAL = re.compile(r"\b(must|shall|should|required to|is required to)\b", re.I)
_AND = re.compile(r"\s+and\s+", re.I)
_AMBIGUOUS = re.compile(
    r"\b(unless|except|excepting|either|neither|respectively|former|latter|"
    r"it|they|them|this|that|these|those|above|below)\b",
    re.I,
)


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "terminal_authority": False,
        "semantic_completeness_claim": False,
    }


def _trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and (text[end - 1].isspace() or text[end - 1] in ".!?"):
        end -= 1
    return start, end


def bind_shared_modal_and(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return _fail("EMPTY_SOURCE")
    if "\n" in text or "\r" in text:
        return _fail("MULTILINE_UNSUPPORTED")
    if _AMBIGUOUS.search(text):
        return _fail("AMBIGUOUS_REFERENCE_OR_SCOPE")
    if ";" in text or "," in text:
        return _fail("PUNCTUATION_COORDINATION_UNSUPPORTED")
    if re.search(r"\s+or\s+", text, re.I):
        return _fail("OR_COORDINATION_UNSUPPORTED")

    modals = list(_MODAL.finditer(text))
    if len(modals) != 1:
        return _fail("EXACTLY_ONE_MODAL_REQUIRED")
    modal = modals[0]

    tail_start = modal.end()
    tail_end = len(text)
    tail_start, tail_end = _trim_span(text, tail_start, tail_end)
    if tail_start >= tail_end:
        return _fail("EMPTY_MODAL_TAIL")

    tail = text[tail_start:tail_end]
    ands = list(_AND.finditer(tail))
    if len(ands) != 1:
        return _fail("EXACTLY_ONE_FLAT_AND_REQUIRED")
    conj = ands[0]

    left_start, left_end = _trim_span(
        text, tail_start, tail_start + conj.start()
    )
    right_start, right_end = _trim_span(
        text, tail_start + conj.end(), tail_end
    )
    if left_start >= left_end or right_start >= right_end:
        return _fail("EMPTY_CONJUNCT")

    # A nested modal inside either conjunct changes scope and is not owned here.
    if _MODAL.search(text[left_start:left_end]) or _MODAL.search(
        text[right_start:right_end]
    ):
        return _fail("NESTED_MODAL")

    prefix_start = 0
    prefix_end = modal.end()
    prefix_start, prefix_end = _trim_span(text, prefix_start, prefix_end)
    if prefix_start >= prefix_end:
        return _fail("EMPTY_PREFIX")

    prefix = text[prefix_start:prefix_end]
    left = text[left_start:left_end]
    right = text[right_start:right_end]

    return {
        "schema": SCHEMA,
        "status": "BOUND_SHARED_MODAL_AND",
        "source": text,
        "shared_prefix": {
            "text": prefix,
            "span": [prefix_start, prefix_end],
            "modal_text": modal.group(0),
            "modal_span": [modal.start(), modal.end()],
        },
        "coordinator": {
            "text": text[tail_start + conj.start():tail_start + conj.end()],
            "span": [
                tail_start + conj.start(),
                tail_start + conj.end(),
            ],
        },
        "obligations": [
            {
                "index": 0,
                "shared_prefix_span": [prefix_start, prefix_end],
                "predicate_text": left,
                "predicate_span": [left_start, left_end],
                "derivation": "EXACT_SHARED_PREFIX_PLUS_EXACT_LEFT_CONJUNCT",
            },
            {
                "index": 1,
                "shared_prefix_span": [prefix_start, prefix_end],
                "predicate_text": right,
                "predicate_span": [right_start, right_end],
                "derivation": "EXACT_SHARED_PREFIX_PLUS_EXACT_RIGHT_CONJUNCT",
            },
        ],
        "obligation_count": 2,
        "source_span_binding_complete": True,
        "coordination_scope_inferred": False,
        "hidden_argument_inference_performed": False,
        "semantic_completeness_claim": False,
        "terminal_authority": False,
        "scope": "SINGLE_MODAL_SINGLE_FLAT_AND_NO_AMBIGUOUS_REFERENCE_NO_OR_NO_COMMA_NO_SEMICOLON",
    }
