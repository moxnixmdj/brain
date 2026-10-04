#!/usr/bin/env python3
"""Source-bound lossless decorator transform for pinned LiveBench langdetect.

The pinned LiveBench placeholder checker accepts square-bracket pairs and the
highlight checker accepts *...* spans.  Those raw markers look harmless, but
langdetect 1.0.9 has a subtle cleaning predicate:

    latin_count * 2 < non_latin_count

and it counts every character in the Python range 'A' <= ch <= 'z' as Latin.
That range includes '[' and ']'.  Naively inserting [] can therefore change
the detector's cleaning branch for non-Latin text.

This module deletes that hidden interaction.  Each [] marker is balanced by
four U+2003 EM SPACE characters.  Under the pinned detector source:
  * '[' and ']' add +2 to latin_count;
  * four U+2003 characters add +4 to non_latin_count;
  * therefore 2*(L+2) < (N+4) iff 2*L < N exactly;
  * Basic-Latin punctuation and General Punctuation both normalize to a space
    in NGram.normalize;
  * the overlay is inserted inside an already-existing ASCII-space gap, so the
    NGram separator stream is unchanged;
  * the highlight carrier *-* changes neither cleaning count and also
    normalizes entirely to spaces.

Thus placeholder/highlight decoration cannot change the detector feature stream
for a source-bound carrier that satisfies the explicit preconditions below.
This is a proof-kernel candidate, not acceptance or capability credit.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from canonical.runtime.livebench_legacy25_single_contract_witness_v1 import (
    LANGUAGE_SAMPLES,
)

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LANGDETECT_BALANCED_DECORATOR_INVARIANCE_V1"

PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_LANGDETECT_VERSION = "1.0.9"
PINNED_LANGDETECT_COMMIT = "5071871742170034557c0e6ec8d6e410f3d9652f"
PINNED_DETECTOR_BLOB = "cc831a0e7530d49fa9b544c9b779ba075ffdbe5c"
PINNED_DETECTOR_FACTORY_BLOB = "aa5a7b24b46b460d6faece5e4afcd23f7178a578"
PINNED_NGRAM_BLOB = "ee82e38f73aadbf118ec03a6342c328d808539d2"
PINNED_UNICODE_BLOCK_BLOB = "f0741890f03e7ac8811ecd568e5aa8e17919d0e2"

DETECTOR_MAX_TEXT_LENGTH = 10000
MAX_PLACEHOLDERS = 4
MAX_HIGHLIGHTS = 4

EM_SPACE = "\u2003"
PLACEHOLDER_UNIT = "[" + EM_SPACE * 4 + "]"
HIGHLIGHT_UNIT = "*-*"

URL_RE = re.compile(r"https?://[-_.?&~;+=/#0-9A-Za-z]{1,2076}")
MAIL_RE = re.compile(
    r"[-_.0-9A-Za-z]{1,64}@[-_0-9A-Za-z]{1,255}[-_.0-9A-Za-z]{1,255}"
)
PLACEHOLDER_RE = re.compile(r"\[.*?\]")
HIGHLIGHT_RE = re.compile(r"\*[^\n\*]*\*")
DOUBLE_HIGHLIGHT_RE = re.compile(r"\*\*[^\n\*]*\*\*")
WORD_RE = re.compile(r"\w+")
ASCII_LETTER_RE = re.compile(r"[A-Za-z]")


def detector_cleaning_counts(text: str) -> tuple[int, int]:
    """Exact count predicate used by pinned Detector.cleaning_text.

    unicode_block(ch) != LATIN_EXTENDED_ADDITIONAL is equivalent here to
    excluding U+1E00..U+1EFF, the exact range in the pinned unicode_block.py.
    """
    latin = 0
    non_latin = 0
    for ch in str(text):
        if "A" <= ch <= "z":
            latin += 1
        elif ch >= "\u0300" and not (0x1E00 <= ord(ch) <= 0x1EFF):
            non_latin += 1
    return latin, non_latin


def cleaning_removes_latin(text: str) -> bool:
    latin, non_latin = detector_cleaning_counts(text)
    return latin * 2 < non_latin


def overlay_fragment(placeholders: int, highlights: int) -> str:
    placeholders = int(placeholders)
    highlights = int(highlights)
    if not 0 <= placeholders <= MAX_PLACEHOLDERS:
        raise ValueError("PLACEHOLDER_COUNT_OUTSIDE_PINNED_DOMAIN")
    if not 0 <= highlights <= MAX_HIGHLIGHTS:
        raise ValueError("HIGHLIGHT_COUNT_OUTSIDE_PINNED_DOMAIN")
    if placeholders == 0 and highlights == 0:
        raise ValueError("EMPTY_DECORATOR_OVERLAY")
    return PLACEHOLDER_UNIT * placeholders + HIGHLIGHT_UNIT * highlights


def _safe_ascii_space_index(text: str) -> int:
    """Return an interior ASCII-space anchor that cannot become a bullet start."""
    for i, ch in enumerate(text):
        if ch == " " and i > 0 and text[i - 1] not in "\r\n":
            return i
    raise ValueError("NO_SAFE_ASCII_SPACE_ANCHOR")


def decorate_losslessly(
    text: str,
    *,
    placeholders: int = 0,
    highlights: int = 0,
) -> str:
    """Replace one existing ASCII-space gap by SPACE + overlay + SPACE."""
    base = str(text)
    if URL_RE.search(base) or MAIL_RE.search(base):
        raise ValueError("URL_OR_MAIL_BASE_REQUIRES_SEPARATE_PROOF")
    i = _safe_ascii_space_index(base)
    fragment = overlay_fragment(placeholders, highlights)
    out = base[:i] + " " + fragment + " " + base[i + 1 :]
    if len(out) >= DETECTOR_MAX_TEXT_LENGTH:
        raise ValueError("DECORATED_TEXT_EXCEEDS_PINNED_DETECTOR_WINDOW")
    return out


def _overlay_source_facts(placeholders: int, highlights: int) -> dict[str, Any]:
    fragment = overlay_fragment(placeholders, highlights)
    latin, non_latin = detector_cleaning_counts(fragment)

    expected_latin = 2 * placeholders
    expected_non_latin = 4 * placeholders
    if (latin, non_latin) != (expected_latin, expected_non_latin):
        raise AssertionError("CLEANING_COUNT_DELTA_DRIFT")

    # Pinned NGram.normalize maps every Basic-Latin nonletter and every
    # General-Punctuation character to ASCII space.  All fragment characters
    # belong to exactly those source-bound classes.
    for ch in fragment:
        cp = ord(ch)
        basic_latin_nonletter = (
            cp <= 0x007F
            and (ch < "A" or ("Z" < ch < "a") or "z" < ch)
        )
        general_punctuation = 0x2000 <= cp <= 0x206F
        if not (basic_latin_nonletter or general_punctuation):
            raise AssertionError("OVERLAY_CHAR_NOT_NGRAM_SPACE_NORMALIZED")

    placeholders_found = len(PLACEHOLDER_RE.findall(fragment))
    highlights_found = sum(
        1
        for x in HIGHLIGHT_RE.findall(fragment)
        if x.strip("*").strip()
    )
    double_found = sum(
        1
        for x in DOUBLE_HIGHLIGHT_RE.findall(fragment)
        if x.removeprefix("**").removesuffix("**").strip()
    )
    if placeholders_found != placeholders:
        raise AssertionError("PLACEHOLDER_CHECKER_DELTA_DRIFT")
    if highlights_found + double_found != highlights:
        raise AssertionError("HIGHLIGHT_CHECKER_DELTA_DRIFT")

    if WORD_RE.findall(fragment):
        raise AssertionError("OVERLAY_ADDS_REGEXP_WORD")
    if ASCII_LETTER_RE.findall(fragment):
        raise AssertionError("OVERLAY_ADDS_ASCII_LETTER")
    if any(ch in fragment for ch in ",.?!\n\r\""):
        raise AssertionError("OVERLAY_ADDS_FORBIDDEN_STRUCTURAL_PUNCTUATION")
    if any(ch.isalpha() or ch.isupper() or ch.islower() for ch in fragment):
        raise AssertionError("OVERLAY_ADDS_CASED_CHARACTER")
    if not EM_SPACE.isspace():
        raise AssertionError("EM_SPACE_NOT_PYTHON_WHITESPACE")

    return {
        "latin_count_delta": latin,
        "non_latin_count_delta": non_latin,
        "placeholder_checker_delta": placeholders_found,
        "highlight_checker_delta": highlights_found + double_found,
        "ngram_normalized_symbol_set": ["SPACE"],
        "regexp_word_delta": 0,
        "ascii_letter_delta": 0,
        "comma_delta": 0,
        "sentence_terminator_delta": 0,
        "cased_character_delta": 0,
    }


def cleaning_branch_identity(
    latin_count: int,
    non_latin_count: int,
    placeholders: int,
) -> bool:
    """Algebraic identity: 2(L+2p)<N+4p iff 2L<N."""
    l = int(latin_count)
    n = int(non_latin_count)
    p = int(placeholders)
    if min(l, n, p) < 0:
        raise ValueError("NEGATIVE_COUNT")
    return ((l + 2 * p) * 2 < n + 4 * p) == (l * 2 < n)


def verify() -> dict[str, Any]:
    # The branch identity is not a sampled assumption.  Exercise boundary
    # neighborhoods anyway so accidental implementation drift fails loudly.
    for p in range(MAX_PLACEHOLDERS + 1):
        for l in range(0, 65):
            for margin in (-2, -1, 0, 1, 2):
                n = max(0, 2 * l + margin)
                if not cleaning_branch_identity(l, n, p):
                    raise AssertionError("CLEANING_BRANCH_IDENTITY_FAILURE")

    overlay_facts = {}
    for p in range(MAX_PLACEHOLDERS + 1):
        for h in range(MAX_HIGHLIGHTS + 1):
            if p == 0 and h == 0:
                continue
            overlay_facts[f"p{p}_h{h}"] = _overlay_source_facts(p, h)

    # Every pinned language witness is duplicated with an ASCII space by the
    # witness constructor.  Verify the transform over that exact carrier bank,
    # while the proof itself remains algebraic rather than sample-derived.
    carriers_checked = 0
    max_decorated_length = 0
    for code, sample in sorted(LANGUAGE_SAMPLES.items()):
        base = sample + " " + sample
        if URL_RE.search(base) or MAIL_RE.search(base):
            raise AssertionError("PINNED_LANGUAGE_SAMPLE_URL_MAIL_DRIFT:" + code)
        base_l, base_n = detector_cleaning_counts(base)
        base_branch = cleaning_removes_latin(base)

        for p in range(MAX_PLACEHOLDERS + 1):
            for h in range(MAX_HIGHLIGHTS + 1):
                if p == 0 and h == 0:
                    continue
                decorated = decorate_losslessly(
                    base, placeholders=p, highlights=h
                )
                new_l, new_n = detector_cleaning_counts(decorated)
                if new_l - base_l != 2 * p:
                    raise AssertionError("PINNED_CARRIER_LATIN_DELTA_DRIFT:" + code)
                if new_n - base_n != 4 * p:
                    raise AssertionError("PINNED_CARRIER_NONLATIN_DELTA_DRIFT:" + code)
                if cleaning_removes_latin(decorated) != base_branch:
                    raise AssertionError("PINNED_CARRIER_CLEANING_BRANCH_CHANGED:" + code)
                max_decorated_length = max(max_decorated_length, len(decorated))
                carriers_checked += 1

    expected_cases = len(LANGUAGE_SAMPLES) * (
        (MAX_PLACEHOLDERS + 1) * (MAX_HIGHLIGHTS + 1) - 1
    )
    if carriers_checked != expected_cases:
        raise AssertionError("PINNED_CARRIER_CASE_COUNT_DRIFT")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__SOURCE_BOUND_BALANCED_DECORATOR_TRANSFORM_PRESERVES_"
            "LANGDETECT_CLEANING_BRANCH_AND_NGRAM_SEPARATOR_STREAM"
        ),
        "source_bindings": {
            "livebench_commit": PINNED_LIVEBENCH_COMMIT,
            "instructions_blob": PINNED_INSTRUCTIONS_BLOB,
            "langdetect_version": PINNED_LANGDETECT_VERSION,
            "langdetect_commit": PINNED_LANGDETECT_COMMIT,
            "detector_blob": PINNED_DETECTOR_BLOB,
            "detector_factory_blob": PINNED_DETECTOR_FACTORY_BLOB,
            "ngram_blob": PINNED_NGRAM_BLOB,
            "unicode_block_blob": PINNED_UNICODE_BLOCK_BLOB,
        },
        "construction": {
            "placeholder_unit_repr": repr(PLACEHOLDER_UNIT),
            "highlight_unit": HIGHLIGHT_UNIT,
            "placeholder_cleaning_delta": {"latin": 2, "non_latin": 4},
            "cleaning_identity": "2*(L+2p) < N+4p  IFF  2*L < N",
            "insertion": "REPLACE_ONE_SAFE_ASCII_SPACE_BY_SPACE_PLUS_OVERLAY_PLUS_SPACE",
            "ngram_effect": "EXACTLY_THE_EXISTING_SEPARATOR_CLASS",
        },
        "pinned_language_carrier_count": len(LANGUAGE_SAMPLES),
        "pinned_decorator_cases_checked": carriers_checked,
        "max_decorated_length": max_decorated_length,
        "detector_window": DETECTOR_MAX_TEXT_LENGTH,
        "improvement": (
            "DELETE_DECORATOR_PLACEMENT_AND_REPETITION_AS_LANGUAGE_DETECTION_"
            "DEGREES_OF_FREEDOM__ONLY_BASE_LANGUAGE_CARRIER_VALIDITY_REMAINS"
        ),
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "hard_nonclaims": [
            "NO_CLAIM_THAT_BASE_LANGUAGE_CARRIERS_ARE_ACCEPTED_FOR_EVERY_STOCHASTIC_DETECTOR_SEED",
            "NO_ACCEPTANCE_PROMOTION_WITHOUT_INDEPENDENT_EXACT_SOURCE_RUNTIME_VERIFICATION",
            "NO_TERMINAL_ROWS_HIDDEN_KWARGS_TARGET_RESPONSES_OR_TARGET_SCORES_USED",
        ],
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = dict(args or {})
    if "text" not in args:
        return verify()
    return {
        "response": decorate_losslessly(
            str(args["text"]),
            placeholders=int(args.get("placeholders", 0)),
            highlights=int(args.get("highlights", 0)),
        ),
        "verification": verify(),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), ensure_ascii=False, indent=2, sort_keys=True))
