#!/usr/bin/env python3
"""Exact finite lexical quotient for frozen LiveBench legacy15 composition.

This module replaces raw enumeration over the 1,525-word public generator
domain with the checker-relevant collision signature induced by the current
semantic UNSAT kernel.

The only fixed generated words whose membership in forbidden_words can force a
hard contradiction are:
- other / anything / can / help, because they occur in the two fixed end phrases;
- section, because MultipleSections requires literal "Section X" labels.

The nth-paragraph first word is also relevant because equality with any
forbidden word is a hard contradiction.  When the nth word itself is one of the
five fixed words, that collision bit is not independent of the corresponding
fixed-word membership bit.  When it is any other public word, it is independent
except that forbidden_words contains exactly five distinct sampled words.

No terminal rows, prompts, kwargs, responses, frequencies, or scores are read.
"""
from __future__ import annotations

from itertools import product
from typing import Any, Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_LEXICAL_COLLISION_SIGNATURE_V2"

WORD_DOMAIN_SIZE = 1525
FORBIDDEN_SAMPLE_SIZE = 5
FIXED_RELEVANT_WORDS = ("other", "anything", "can", "help", "section")
NTH_CATEGORIES = (*FIXED_RELEVANT_WORDS, "generic")
END_PHRASES = (
    "Any other questions?",
    "Is there anything else I can help with?",
)

_FIXED_INDEX = {word: i for i, word in enumerate(FIXED_RELEVANT_WORDS)}


def _signature(
    *,
    end_phrase_index: int,
    nth_category: str,
    fixed_forbidden_bits: tuple[bool, ...],
    nth_is_forbidden: bool,
) -> tuple[Any, ...]:
    return (
        int(end_phrase_index),
        str(nth_category),
        tuple(bool(x) for x in fixed_forbidden_bits),
        bool(nth_is_forbidden),
    )


def enumerate_reachable_signatures() -> tuple[tuple[Any, ...], ...]:
    """Enumerate every reachable checker-relevant lexical collision signature.

    The construction is combinatorial, not a raw-word product:
    - forbidden_words is a 5-element sample without replacement;
    - the five fixed relevant words may independently be in that sample;
    - if nth_category is one of those fixed words, nth_is_forbidden equals that
      fixed membership bit;
    - if nth_category is generic, nth_is_forbidden is independently selectable
      unless all five forbidden slots are already occupied by the fixed words.

    The 1,525-word domain is vastly larger than the at-most-six distinguished
    words, so every signature admitted by these capacity constraints is
    constructively reachable.
    """
    out: set[tuple[Any, ...]] = set()
    for end_phrase_index in range(len(END_PHRASES)):
        for nth_category in NTH_CATEGORIES:
            for bits in product((False, True), repeat=len(FIXED_RELEVANT_WORDS)):
                bits = tuple(bool(x) for x in bits)
                fixed_count = sum(bits)

                if nth_category in _FIXED_INDEX:
                    nth_is_forbidden = bits[_FIXED_INDEX[nth_category]]
                    out.add(_signature(
                        end_phrase_index=end_phrase_index,
                        nth_category=nth_category,
                        fixed_forbidden_bits=bits,
                        nth_is_forbidden=nth_is_forbidden,
                    ))
                    continue

                for nth_is_forbidden in (False, True):
                    distinguished_forbidden = fixed_count + int(nth_is_forbidden)
                    if distinguished_forbidden > FORBIDDEN_SAMPLE_SIZE:
                        continue
                    # There are enough undistinguished public words to fill the
                    # remaining forbidden slots while keeping all sampled words
                    # distinct.  Keep the capacity check explicit so future
                    # source-domain shrinkage fails closed.
                    filler_needed = FORBIDDEN_SAMPLE_SIZE - distinguished_forbidden
                    excluded_distinguished = len(FIXED_RELEVANT_WORDS) + 1
                    filler_available = WORD_DOMAIN_SIZE - excluded_distinguished
                    if filler_needed > filler_available:
                        continue
                    out.add(_signature(
                        end_phrase_index=end_phrase_index,
                        nth_category=nth_category,
                        fixed_forbidden_bits=bits,
                        nth_is_forbidden=nth_is_forbidden,
                    ))

    return tuple(sorted(out, key=repr))


def lexical_unsat_reasons(signature: tuple[Any, ...]) -> tuple[str, ...]:
    """Return the hard lexical UNSAT classes represented by a signature."""
    end_phrase_index, nth_category, bits, nth_is_forbidden = signature
    bits = tuple(bool(x) for x in bits)
    if len(bits) != len(FIXED_RELEVANT_WORDS):
        raise ValueError("FIXED_FORBIDDEN_BIT_WIDTH_MISMATCH")
    if int(end_phrase_index) not in range(len(END_PHRASES)):
        raise ValueError("END_PHRASE_INDEX_OUT_OF_RANGE")
    if str(nth_category) not in NTH_CATEGORIES:
        raise ValueError("UNKNOWN_NTH_CATEGORY")

    by_word = dict(zip(FIXED_RELEVANT_WORDS, bits))
    reasons: list[str] = []

    if bool(nth_is_forbidden):
        reasons.append("NTH_FIRST_WORD_IS_FORBIDDEN_WORD")

    if int(end_phrase_index) == 0:
        if by_word["other"]:
            reasons.append("MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:other")
    else:
        for word in ("anything", "can", "help"):
            if by_word[word]:
                reasons.append("MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:" + word)

    if by_word["section"]:
        reasons.append("MANDATORY_SECTION_SPLITTER_IS_FORBIDDEN_WORD:section")

    return tuple(reasons)


def exact_reachable_signature_count() -> int:
    return len(enumerate_reachable_signatures())


def conservative_cartesian_bound() -> int:
    """Naive independent-bit bound after adding the section collision bit."""
    independent_boolean_dimensions = len(FIXED_RELEVANT_WORDS) + 1
    return (
        len(NTH_CATEGORIES)
        * len(END_PHRASES)
        * (2 ** independent_boolean_dimensions)
    )


def prove_count() -> dict[str, Any]:
    signatures = enumerate_reachable_signatures()
    fixed_category_count = (
        len(FIXED_RELEVANT_WORDS)
        * (2 ** len(FIXED_RELEVANT_WORDS))
        * len(END_PHRASES)
    )
    generic_per_end = (
        (2 ** len(FIXED_RELEVANT_WORDS))
        + ((2 ** len(FIXED_RELEVANT_WORDS)) - 1)
    )
    generic_count = generic_per_end * len(END_PHRASES)
    derived = fixed_category_count + generic_count
    if derived != len(signatures):
        raise RuntimeError("SIGNATURE_COUNT_DERIVATION_MISMATCH")
    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_REACHABLE_LEXICAL_SIGNATURE_QUOTIENT",
        "word_domain_size": WORD_DOMAIN_SIZE,
        "forbidden_sample_size": FORBIDDEN_SAMPLE_SIZE,
        "fixed_relevant_words": list(FIXED_RELEVANT_WORDS),
        "nth_categories": list(NTH_CATEGORIES),
        "end_phrase_count": len(END_PHRASES),
        "fixed_nth_category_signature_count": fixed_category_count,
        "generic_nth_signature_count": generic_count,
        "exact_reachable_signature_count": len(signatures),
        "conservative_cartesian_bound": conservative_cartesian_bound(),
        "prior_320_bound_is_sound_for_current_kernel": 320 >= len(signatures),
        "raw_word_combination_enumeration_required": False,
        "terminal_data_used": False,
        "acceptance_credit": False,
    }


def run(args=None, root=None):
    return prove_count()


if __name__ == "__main__":
    import json
    print(json.dumps(prove_count(), indent=2, sort_keys=True))
