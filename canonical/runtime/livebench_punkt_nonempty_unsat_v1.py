#!/usr/bin/env python3
"""General Punkt zero-sentence UNSAT lemma for frozen legacy-15 LiveBench.

The pinned NumberOfSentences checker with relation="less than" and threshold=1
requires count_sentences(response) == 0. In NLTK 3.10.3 Punkt, every response
whose rstrip() is non-empty yields at least one sentence: _slices_from_text()
unconditionally emits the final non-trailing-whitespace slice, and
_realign_boundaries() retains a non-empty slice.

Therefore any *compatible* public checker contract that itself forces at least
one non-whitespace character is jointly UNSAT with sentence<1. This module
certifies that implication only for exact active-15 contracts whose non-emptiness
follows directly from pinned checker semantics and visible slots.

No terminal rows, hidden kwargs, scores, responses, or case frequencies are read.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as archetypes

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PUNKT_NONEMPTY_UNSAT_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_INSTRUCTIONS_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
PINNED_NLTK_VERSION = "3.10.3"
PINNED_NLTK_PUNKT_SOURCE_BLOB = "48496d2448c009221d2452c8e928699027b20ebe"

SENTENCE = "length_constraints:number_sentences"
EXISTENCE = "keywords:existence"
WORDS = "length_constraints:number_words"
NTH = "length_constraints:nth_paragraph_first_word"
POSTSCRIPT = "detectable_content:postscript"
BULLETS = "detectable_format:number_bullet_lists"
TITLE = "detectable_format:title"
SECTIONS = "detectable_format:multiple_sections"
END = "startend:end_checker"
QUOTATION = "startend:quotation"

_PUBLIC_POSTSCRIPT_MARKERS = frozenset({"P.S.", "P.P.S"})
_PUBLIC_SECTION_SPLITTERS = frozenset({"Section", "SECTION"})


def _slots(contract: Mapping[str, Any]) -> dict[str, Any]:
    return dict(contract.get("slots") or {})


def _positive_int(value: Any) -> int | None:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n >= 1 else None


def is_sentence_lt_one(contract: Mapping[str, Any]) -> bool:
    if str(contract.get("instruction_id") or "") != SENTENCE:
        return False
    s = _slots(contract)
    try:
        threshold = int(s.get("num_sentences"))
    except (TypeError, ValueError):
        return False
    return (
        str(s.get("relation") or "").strip().casefold() == "less than"
        and threshold == 1
    )


def forces_nonempty_response(contract: Mapping[str, Any]) -> bool:
    """Certify that every checker-satisfying response has non-whitespace text."""
    iid = str(contract.get("instruction_id") or "")
    s = _slots(contract)

    if iid == EXISTENCE:
        # Historical generator keywords are ordinary WORD_LIST words. Requiring
        # even one non-empty alphabetic keyword forces a non-whitespace response.
        kws = [str(x) for x in (s.get("keywords") or [])]
        return any(re.fullmatch(r"[A-Za-z]+", x) is not None for x in kws)

    if iid == WORDS:
        return (
            str(s.get("relation") or "").strip().casefold() == "at least"
            and (_positive_int(s.get("num_words")) is not None)
        )

    if iid == NTH:
        first = str(s.get("first_word") or "").strip()
        nparas = _positive_int(s.get("num_paragraphs"))
        nth = _positive_int(s.get("nth_paragraph"))
        return bool(first) and nparas is not None and nth is not None and nth <= nparas

    if iid == POSTSCRIPT:
        marker = str(s.get("postscript_marker") or "").strip()
        return marker in _PUBLIC_POSTSCRIPT_MARKERS

    if iid == BULLETS:
        return _positive_int(s.get("num_bullets")) is not None

    if iid == TITLE:
        # TitleChecker requires <<[^\n]+>> with non-empty stripped interior.
        return True

    if iid == SECTIONS:
        splitter = str(s.get("section_spliter") or "").strip()
        return (
            splitter in _PUBLIC_SECTION_SPLITTERS
            and _positive_int(s.get("num_sections")) is not None
        )

    if iid == END:
        return bool(str(s.get("end_phrase") or "").strip())

    if iid == QUOTATION:
        # QuotationChecker requires len(value.strip()) > 1 plus two quote chars.
        return True

    return False


def hard_unsat_reasons(
    contracts: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    ids = tuple(str(c.get("instruction_id") or "") for c in contracts)
    if len(ids) != len(set(ids)) or not archetypes.compatible(ids):
        return ()

    sentence = next((c for c in contracts if is_sentence_lt_one(c)), None)
    if sentence is None:
        return ()

    reasons: list[str] = []
    for contract in contracts:
        iid = str(contract.get("instruction_id") or "")
        if iid == SENTENCE:
            continue
        if forces_nonempty_response(contract):
            reasons.append("SENTENCE_LT_ONE_WITH_NONEMPTY_REQUIRED:" + iid)
    return tuple(sorted(set(reasons)))


def classify_visible_contracts(
    contracts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    ids = tuple(str(c.get("instruction_id") or "") for c in contracts)
    if len(ids) != len(set(ids)):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_DUPLICATE_ID",
            "instruction_ids": sorted(ids),
            "hard_unsat_reasons": [],
            "terminal_data_used": False,
            "acceptance_credit": False,
        }
    if not archetypes.compatible(ids):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_ID_CONFLICT",
            "instruction_ids": sorted(ids),
            "hard_unsat_reasons": [],
            "terminal_data_used": False,
            "acceptance_credit": False,
        }
    reasons = hard_unsat_reasons(contracts)
    return {
        "schema": SCHEMA,
        "status": (
            "PROVED_UNSAT"
            if reasons
            else "NO_PUNKT_NONEMPTY_UNSAT_CERTIFICATE"
        ),
        "instruction_ids": sorted(ids),
        "archetype": archetypes.archetype(ids),
        "hard_unsat_reasons": list(reasons),
        "terminal_data_used": False,
        "hidden_kwargs_used": False,
        "acceptance_credit": False,
    }


def proof_summary() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "PASS__GENERAL_PUNKT_NONEMPTY_UNSAT_LEMMA_ENCODED",
        "sentence_contract": {
            "num_sentences": 1,
            "relation": "less than",
        },
        "certifiable_nonempty_checker_ids": [
            EXISTENCE,
            WORDS,
            NTH,
            POSTSCRIPT,
            BULLETS,
            TITLE,
            SECTIONS,
            END,
            QUOTATION,
        ],
        "pinned_nltk_version": PINNED_NLTK_VERSION,
        "pinned_nltk_punkt_source_blob": PINNED_NLTK_PUNKT_SOURCE_BLOB,
        "terminal_data_used": False,
        "hidden_kwargs_used": False,
        "acceptance_credit": False,
    }


def run(args=None, root=None):
    return proof_summary()


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, sort_keys=True))
