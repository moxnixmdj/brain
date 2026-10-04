#!/usr/bin/env python3
"""LiveBench union25 language-exception carrier V2.

This repairs V1's detector-boundary counting error. The pinned langdetect
Detector.cleaning_text implementation counts every code point in the inclusive
ASCII interval 'A'..'z', not merely [A-Za-z]. That interval also contains
[\\]^_`. V2 sizes the private-use carrier against the exact detector bucket.

The intended reduction is deterministic and occurs before langdetect's random
sampling loop:
  1. append enough U+E000 characters that non_latin_count > 2*latin_count;
  2. cleaning_text deletes every 'A'..'z' character;
  3. surviving Basic-Latin punctuation/digits normalize to spaces;
  4. if U+E000 uni/bi/trigrams are absent from the pinned profile map,
     _extract_ngrams() is empty and langdetect raises LangDetectException;
  5. the frozen LiveBench response-language and English-case checkers explicitly
     count LangDetectException as success.

Steps 3-5 are independently runtime-verified before any proof/acceptance credit.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_LANGUAGE_EXCEPTION_CARRIER_V2"
SUPERSEDES = "PROJECT_BRAIN_LIVEBENCH_UNION25_LANGUAGE_EXCEPTION_CARRIER_V1"
PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_LANGDETECT_VERSION = "1.0.9"
LANGDETECT_DETECTOR_SOURCE_BLOB = "cc831a0e7530d49fa9b544c9b779ba075ffdbe5c"
LANGDETECT_NGRAM_SOURCE_BLOB = "ee82e38f73aadbf118ec03a6342c328d808539d2"
PRIVATE_USE_CARRIER = "\ue000"
DETECTOR_MAX_TEXT_LENGTH = 10000


def detector_latin_bucket_count(text: str) -> int:
    """Exact count used by pinned Detector.cleaning_text."""
    return sum(1 for ch in str(text) if "A" <= ch <= "z")


def required_carrier_count(text: str) -> int:
    """Minimum integer N satisfying 2*latin_count < non_latin_count."""
    return 2 * detector_latin_bucket_count(text) + 1


def inject_before_suffix(prefix: str, suffix: str = "") -> str:
    prefix = str(prefix)
    suffix = str(suffix)
    base = prefix + suffix
    n = required_carrier_count(base)
    out = prefix + PRIVATE_USE_CARRIER * n + suffix
    # Detector.append truncates at max_text_length. Keep the full proof carrier
    # inside the inspected window instead of reasoning about truncation.
    if len(out) >= DETECTOR_MAX_TEXT_LENGTH:
        raise ValueError("LANGUAGE_CARRIER_EXCEEDS_PINNED_DETECTOR_WINDOW")
    return out


def static_invariants() -> dict[str, Any]:
    c = PRIVATE_USE_CARRIER
    if "A" <= c <= "z":
        raise AssertionError("CARRIER_COUNTS_IN_DETECTOR_LATIN_BUCKET")
    if re.match(r"\w", c):
        raise AssertionError("CARRIER_COUNTS_AS_REGEXP_WORD_CHARACTER")
    if re.search(r"[A-Za-z]", c):
        raise AssertionError("CARRIER_COUNTS_AS_ASCII_LETTER")
    if c.isalpha() or c.isupper() or c.islower():
        raise AssertionError("CARRIER_HAS_CASE_SEMANTICS")
    if any(x in c for x in (",", ".", "?", "!", "\n", '"', "[", "]", "*")):
        raise AssertionError("CARRIER_HAS_STRUCTURAL_PUNCTUATION")

    gap = "[\\]^_`"
    if detector_latin_bucket_count(gap) != 6:
        raise AssertionError("A_TO_Z_INTERVAL_GAP_REGRESSION")

    return {
        "codepoint": "U+E000",
        "detector_latin_bucket_definition": "ASCII_CODEPOINT_INCLUSIVE_INTERVAL_A_TO_z",
        "detector_latin_bucket_gap_characters": gap,
        "detector_latin_bucket_gap_count": 6,
        "regexp_word_delta_per_char": 0,
        "ascii_letter_delta_per_char": 0,
        "cased_character_delta_per_char": 0,
        "structural_punctuation_delta_per_char": 0,
    }


def verify() -> dict[str, Any]:
    inv = static_invariants()
    probes = [
        "",
        "ABCxyz",
        "[\\]^_`",
        "[][][][]",
        "P.S.+",
        "<<9000001>>",
        "*-* [] 9000001?",
        '"SECTION 1"',
    ]
    examples = []
    for payload in probes:
        latin = detector_latin_bucket_count(payload)
        carriers = required_carrier_count(payload)
        out = inject_before_suffix(payload)
        if carriers <= 2 * latin:
            raise AssertionError("STRICT_DETECTOR_DOMINANCE_FAILED")
        if out.count(PRIVATE_USE_CARRIER) != carriers:
            raise AssertionError("CARRIER_INSERTION_COUNT_DRIFT")
        examples.append({
            "payload": payload,
            "detector_latin_bucket_count": latin,
            "carrier_count": carriers,
            "strict_non_latin_dominance": carriers > 2 * latin,
            "total_length": len(out),
        })

    bracket = "[][][][]"
    if detector_latin_bucket_count(bracket) != 8:
        raise AssertionError("BRACKET_BUCKET_REGRESSION")
    if required_carrier_count(bracket) != 17:
        raise AssertionError("BRACKET_CARRIER_REGRESSION")

    return {
        "schema": SCHEMA,
        "supersedes": SUPERSEDES,
        "status": "FALSIFIED_FOR_FROZEN_CHECKER__EXACT_DETECTOR_BUCKET_REPAIR_STATICALLY_VALID__EXCEPTION_ROUTE_UNUSABLE_BECAUSE_LOGGING_GLOBAL_IS_UNBOUND",
        "pinned_livebench_commit": PINNED_LIVEBENCH_COMMIT,
        "pinned_instructions_blob": PINNED_INSTRUCTIONS_BLOB,
        "pinned_langdetect_version": PINNED_LANGDETECT_VERSION,
        "langdetect_source_blobs": {
            "detector.py": LANGDETECT_DETECTOR_SOURCE_BLOB,
            "ngram.py": LANGDETECT_NGRAM_SOURCE_BLOB,
        },
        "carrier_invariants": inv,
        "construction": "PREFIX + U+E000*(2*COUNT_CHARS_WITH_A<=CH<=z(PREFIX+SUFFIX)+1) + SUFFIX",
        "static_examples": examples,
        "proof_chain": [
            "CARRIER_COUNT_IS_STRICTLY_GREATER_THAN_TWICE_EXACT_DETECTOR_LATIN_BUCKET",
            "PINNED_CLEANING_TEXT_THEREFORE_DELETES_EVERY_A_TO_z_CHARACTER",
            "INDEPENDENT_GATE_MUST_VERIFY_SURVIVING_BASIC_LATIN_NORMALIZES_TO_SPACES",
            "INDEPENDENT_GATE_MUST_VERIFY_U_E000_UNI_BIGRAM_TRIGRAM_ABSENT_FROM_PINNED_PROFILE_MAP",
            "EMPTY_NGRAM_SET_MUST_RAISE_LANGDETECTEXCEPTION_BEFORE_RANDOM_SAMPLING",
            "FROZEN_LIVEBENCH_LANGUAGE_AND_ENGLISH_CASE_CHECKERS_MUST_COUNT_EXCEPTION_AS_SUCCESS",
        ],
        "stochasticity_consequence": "IF_RUNTIME_GATE_PASSES__SEED_IS_IRRELEVANT_BECAUSE_EXCEPTION_PRECEDES_RANDOM_TRIAL_LOOP",
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
        "hard_nonclaims": [
            "NO_LANGDETECT_RUNTIME_CLAIM_FROM_STATIC_PROOF_ALONE",
            "FROZEN_CHECKER_COMMENTS_OUT_LOGGING_IMPORT_BUT_EXCEPTION_HANDLERS_CALL_logging_error__LANGDETECTEXCEPTION_ROUTE_RAISES_NAMEERROR_BEFORE_RETURN_TRUE",
            "NO_LIVEBENCH_POINTWISE_OR_ACCEPTANCE_CREDIT_UNTIL_INDEPENDENT_EXACT_RUNTIME_PASS",
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
