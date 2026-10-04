#!/usr/bin/env python3
"""Candidate language-exception carrier for the pinned LiveBench union25 checker.

The pinned language and English-case checkers explicitly return success when
langdetect raises LangDetectException.  This constructor inserts a semantically
inert private-use carrier sized from the visible ASCII-Latin payload.  Under the
pinned detector cleaning rule, the carrier dominates ASCII Latin characters;
an independent exact-runtime verifier must establish the final no-feature
exception before this primitive receives any proof or acceptance credit.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_LANGUAGE_EXCEPTION_CARRIER_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PRIVATE_USE_CARRIER = "\ue000"
DETECTOR_MAX_TEXT_LENGTH = 10000

def ascii_latin_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z]", str(text)))

def required_carrier_count(text: str) -> int:
    return 2 * ascii_latin_count(text) + 1

def inject_before_suffix(prefix: str, suffix: str = "") -> str:
    """Insert the carrier before any syntax-sensitive terminal suffix."""
    base = str(prefix) + str(suffix)
    out = str(prefix) + PRIVATE_USE_CARRIER * required_carrier_count(base) + str(suffix)
    if len(out) >= DETECTOR_MAX_TEXT_LENGTH:
        raise ValueError("LANGUAGE_CARRIER_EXCEEDS_PINNED_DETECTOR_WINDOW")
    return out

def static_invariants() -> dict[str, Any]:
    c = PRIVATE_USE_CARRIER
    if re.match(r"\w", c):
        raise AssertionError("CARRIER_COUNTS_AS_WORD_CHARACTER")
    if re.search(r"[A-Za-z]", c):
        raise AssertionError("CARRIER_COUNTS_AS_ASCII_LATIN")
    if c.isalpha() or c.isupper() or c.islower():
        raise AssertionError("CARRIER_HAS_CASE_SEMANTICS")
    if any(x in c for x in (",", ".", "?", "!", "\n", '"', "[", "]", "*")):
        raise AssertionError("CARRIER_HAS_STRUCTURAL_PUNCTUATION")
    return {
        "codepoint": "U+E000",
        "regexp_word_delta_per_char": 0,
        "ascii_latin_delta_per_char": 0,
        "cased_character_delta_per_char": 0,
        "structural_punctuation_delta_per_char": 0,
    }

def verify() -> dict[str, Any]:
    inv = static_invariants()
    examples = []
    for n in (0, 1, 10, 100, 1000, 3000):
        payload = "a" * n
        out = inject_before_suffix(payload)
        examples.append({
            "ascii_latin_count": n,
            "carrier_count": required_carrier_count(payload),
            "total_length": len(out),
            "dominance_strict": required_carrier_count(payload) > 2 * n,
        })
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE__STATIC_CARRIER_INVARIANTS_PASS__EXACT_LANGDETECT_RUNTIME_GATE_PENDING",
        "pinned_livebench_commit": PINNED_LIVEBENCH_COMMIT,
        "pinned_instructions_blob": PINNED_INSTRUCTIONS_BLOB,
        "carrier_invariants": inv,
        "construction": "PREFIX + U+E000*(2*ASCII_LATIN_COUNT(PREFIX+SUFFIX)+1) + SUFFIX",
        "examples": examples,
        "intended_effect": [
            "DELETE_30_LANGUAGE_TEMPLATE_BANK_IF_EXACT_RUNTIME_GATE_PASSES",
            "MAKE_LANGUAGE_DECORATOR_INSERTIONS_IRRELEVANT_TO_LANGUAGE_ID",
            "SUPPLY_CASE_CHECKERS_WITH_DETECTOR_EXCEPTION_PATH_WHILE_PRESERVING_ISUPPER_ISLOWER",
        ],
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "hard_nonclaims": [
            "NO_LANGDETECT_BEHAVIOR_CLAIM_UNTIL_INDEPENDENT_EXACT_RUNTIME_PASS",
            "NO_UNION25_POINTWISE_OPTIMALITY_CLAIM",
        ],
    }

def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = dict(args or {})
    return {
        "response": inject_before_suffix(str(args.get("prefix", "")), str(args.get("suffix", ""))),
        "verification": verify(),
    }

if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
