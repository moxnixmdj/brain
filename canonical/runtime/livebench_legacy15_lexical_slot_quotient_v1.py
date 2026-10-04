#!/usr/bin/env python3
"""Exact finite lexical quotient for the frozen LiveBench legacy15 generator.

The public generator draws keyword lists with random.sample(WORD_LIST, k=5), so
existence and forbidden lists contain five distinct words. For the active15
surface, checker-relevant lexical interactions factor through:

* which of four public end-phrase words are forbidden:
    other, anything, can, help
* whether the nth-paragraph first word is forbidden
* whether that nth word is one of those four special words or a generic word
* which of the two fixed public end phrases is selected

When the nth word is one of the four special words, its forbidden bit is not
independent: it is exactly that special word's forbidden-membership bit.
Therefore the conservative 320-state bound collapses to exactly 192 reachable
signatures:

    2 end phrases * (4 special nth categories * 2^4
                     + 1 generic nth category * 2^5)
  = 2 * (64 + 32)
  = 192.

Representative forbidden sets are always exactly five distinct words, so every
emitted signature has a constructive public-generator witness. Existence keyword
identities are intentionally absent from the signature: the current constructor
uses a word+"x" carrier, existence uses raw-regex substring matching, forbidden
uses whole-word boundaries, all public words are ASCII alphabetic, and the
pinned source audit established that no WORD_LIST value plus literal "x" is
another WORD_LIST value.

This module proves only the lexical quotient. Numeric, structural, prompt-text,
and candidate-construction completeness remain separate obligations.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from typing import Any, Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_LEXICAL_SLOT_QUOTIENT_V1"

PINNED_LIVEBENCH_COMMIT = "8f8e5c381a16e3f24257776edd53471fe86f8091"
PINNED_INSTRUCTIONS_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
PINNED_GENERATOR_COMMIT = "686be1e78a0ba8036d7e355bc406e1a265da5292"
PINNED_GENERATOR_BLOB = "6ff390d6885cf90f88d9d36959735cb327613edc"

WORD_LIST_ENTRY_COUNT = 1525
WORD_LIST_UNIQUE_COUNT = 1525
GENERATED_KEYWORD_COUNT = 5

END_PHRASES = (
    "Any other questions?",
    "Is there anything else I can help with?",
)
SPECIAL_WORDS = ("other", "anything", "can", "help")
NTH_CATEGORIES = SPECIAL_WORDS + ("__generic__",)
GENERIC_NTH_WORD = "river"

# All are pinned WORD_LIST members and are disjoint from SPECIAL_WORDS and the
# generic nth representative. Five are sufficient to complete any representative
# forbidden set to the generator's exact cardinality.
GENERIC_FORBIDDEN_FILLERS = (
    "western",
    "sentence",
    "signal",
    "dump",
    "spot",
)

# Five distinct pinned WORD_LIST members used only as a constructive witness for
# the existence-keyword family. Their identities are quotient-irrelevant.
EXISTENCE_REPRESENTATIVE = (
    "apple",
    "bridge",
    "cloud",
    "dream",
    "energy",
)

SPECIAL_SET = frozenset(SPECIAL_WORDS)


@dataclass(frozen=True)
class LexicalSignature:
    end_phrase_index: int
    nth_category: str
    forbidden_other: bool
    forbidden_anything: bool
    forbidden_can: bool
    forbidden_help: bool
    nth_in_forbidden: bool

    @property
    def special_bits(self) -> dict[str, bool]:
        return {
            "other": self.forbidden_other,
            "anything": self.forbidden_anything,
            "can": self.forbidden_can,
            "help": self.forbidden_help,
        }

    @property
    def end_phrase(self) -> str:
        return END_PHRASES[self.end_phrase_index]

    @property
    def nth_word(self) -> str:
        return (
            GENERIC_NTH_WORD
            if self.nth_category == "__generic__"
            else self.nth_category
        )


def _signature(
    end_phrase_index: int,
    nth_category: str,
    special_bits: tuple[bool, bool, bool, bool],
    nth_in_forbidden: bool,
) -> LexicalSignature:
    return LexicalSignature(
        end_phrase_index=end_phrase_index,
        nth_category=nth_category,
        forbidden_other=special_bits[0],
        forbidden_anything=special_bits[1],
        forbidden_can=special_bits[2],
        forbidden_help=special_bits[3],
        nth_in_forbidden=nth_in_forbidden,
    )


def enumerate_signatures() -> tuple[LexicalSignature, ...]:
    """Enumerate every and only reachable checker-relevant lexical signature."""
    out: list[LexicalSignature] = []
    for end_phrase_index in range(len(END_PHRASES)):
        for nth_category in NTH_CATEGORIES:
            for bits in product((False, True), repeat=len(SPECIAL_WORDS)):
                special_bits = tuple(bool(x) for x in bits)
                if nth_category == "__generic__":
                    nth_values: Iterable[bool] = (False, True)
                else:
                    # The nth word is itself one of the four special words, so
                    # membership cannot vary independently.
                    index = SPECIAL_WORDS.index(nth_category)
                    nth_values = (special_bits[index],)
                for nth_in_forbidden in nth_values:
                    out.append(
                        _signature(
                            end_phrase_index,
                            nth_category,
                            special_bits,
                            nth_in_forbidden,
                        )
                    )
    return tuple(out)


def representative_forbidden_words(
    signature: LexicalSignature,
) -> tuple[str, ...]:
    """Construct one exact five-distinct-word public-generator representative."""
    selected: list[str] = [
        word
        for word, present in signature.special_bits.items()
        if present
    ]

    nth_word = signature.nth_word
    if signature.nth_in_forbidden and nth_word not in selected:
        selected.append(nth_word)

    # The logical dependency must hold even for externally constructed records.
    if signature.nth_category in SPECIAL_SET:
        expected = signature.special_bits[signature.nth_category]
        if signature.nth_in_forbidden is not expected:
            raise ValueError("INCONSISTENT_SPECIAL_NTH_MEMBERSHIP")

    if len(set(selected)) != len(selected):
        raise RuntimeError("REPRESENTATIVE_DUPLICATE_BEFORE_FILL")

    for filler in GENERIC_FORBIDDEN_FILLERS:
        if filler not in selected and filler != nth_word:
            selected.append(filler)
        if len(selected) == GENERATED_KEYWORD_COUNT:
            break

    if len(selected) != GENERATED_KEYWORD_COUNT:
        raise RuntimeError("REPRESENTATIVE_FORBIDDEN_CARDINALITY_FAILURE")
    if len(set(selected)) != GENERATED_KEYWORD_COUNT:
        raise RuntimeError("REPRESENTATIVE_FORBIDDEN_DISTINCTNESS_FAILURE")
    return tuple(sorted(selected))


def representative_slots(signature: LexicalSignature) -> dict[str, dict[str, Any]]:
    """Return lexical slot fragments composable with numeric/structural slots."""
    forbidden = representative_forbidden_words(signature)
    return {
        "keywords:existence": {
            "keywords": list(EXISTENCE_REPRESENTATIVE),
        },
        "keywords:forbidden_words": {
            "forbidden_words": list(forbidden),
        },
        "length_constraints:nth_paragraph_first_word": {
            "first_word": signature.nth_word,
        },
        "startend:end_checker": {
            "end_phrase": signature.end_phrase,
        },
    }


def predicted_hard_collisions(
    signature: LexicalSignature,
) -> tuple[str, ...]:
    """Return lexical hard-UNSAT classes implied by the signature."""
    reasons: list[str] = []
    if signature.nth_in_forbidden:
        reasons.append("NTH_FIRST_WORD_IS_FORBIDDEN_WORD")

    bits = signature.special_bits
    if signature.end_phrase_index == 0:
        if bits["other"]:
            reasons.append(
                "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:other"
            )
    elif signature.end_phrase_index == 1:
        hits = tuple(
            word for word in ("anything", "can", "help") if bits[word]
        )
        for word in hits:
            reasons.append(
                "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:" + word
            )
    else:
        raise ValueError("END_PHRASE_INDEX_OUT_OF_RANGE")

    return tuple(reasons)


def verify() -> dict[str, Any]:
    signatures = enumerate_signatures()
    if len(signatures) != 192:
        raise RuntimeError("LEXICAL_SIGNATURE_COUNT_DRIFT")
    if len(set(signatures)) != len(signatures):
        raise RuntimeError("LEXICAL_SIGNATURE_DUPLICATE")

    per_end = {i: 0 for i in range(len(END_PHRASES))}
    per_nth = {name: 0 for name in NTH_CATEGORIES}
    nth_collision_count = 0
    end_collision_count = 0
    any_collision_count = 0

    for sig in signatures:
        forbidden = representative_forbidden_words(sig)
        if len(forbidden) != GENERATED_KEYWORD_COUNT:
            raise RuntimeError("FORBIDDEN_CARDINALITY_DRIFT")
        if len(set(forbidden)) != GENERATED_KEYWORD_COUNT:
            raise RuntimeError("FORBIDDEN_DISTINCTNESS_DRIFT")

        forbidden_set = set(forbidden)
        bits = sig.special_bits
        for word in SPECIAL_WORDS:
            if (word in forbidden_set) is not bits[word]:
                raise RuntimeError("SPECIAL_MEMBERSHIP_REPRESENTATIVE_DRIFT")
        if (sig.nth_word in forbidden_set) is not sig.nth_in_forbidden:
            raise RuntimeError("NTH_MEMBERSHIP_REPRESENTATIVE_DRIFT")

        per_end[sig.end_phrase_index] += 1
        per_nth[sig.nth_category] += 1

        reasons = predicted_hard_collisions(sig)
        nth_hit = "NTH_FIRST_WORD_IS_FORBIDDEN_WORD" in reasons
        end_hit = any(
            reason.startswith(
                "MANDATORY_END_PHRASE_CONTAINS_FORBIDDEN_WORD:"
            )
            for reason in reasons
        )
        nth_collision_count += int(nth_hit)
        end_collision_count += int(end_hit)
        any_collision_count += int(nth_hit or end_hit)

    expected_per_end = {0: 96, 1: 96}
    expected_per_nth = {
        "other": 32,
        "anything": 32,
        "can": 32,
        "help": 32,
        "__generic__": 64,
    }
    if per_end != expected_per_end:
        raise RuntimeError("END_PARTITION_DRIFT")
    if per_nth != expected_per_nth:
        raise RuntimeError("NTH_PARTITION_DRIFT")
    if nth_collision_count != 96:
        raise RuntimeError("NTH_COLLISION_COUNT_DRIFT")
    if end_collision_count != 132:
        raise RuntimeError("END_COLLISION_COUNT_DRIFT")
    if any_collision_count != 155:
        raise RuntimeError("ANY_LEXICAL_COLLISION_COUNT_DRIFT")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__EXACT_192_REACHABLE_LEXICAL_SIGNATURES__"
            "RAW_1525_WORD_IDENTITY_ENUMERATION_DELETED"
        ),
        "source_binding": {
            "livebench_commit": PINNED_LIVEBENCH_COMMIT,
            "instructions_util_blob": PINNED_INSTRUCTIONS_UTIL_BLOB,
            "generator_commit": PINNED_GENERATOR_COMMIT,
            "generator_blob": PINNED_GENERATOR_BLOB,
        },
        "word_list_entry_count": WORD_LIST_ENTRY_COUNT,
        "word_list_unique_count": WORD_LIST_UNIQUE_COUNT,
        "generated_keyword_count": GENERATED_KEYWORD_COUNT,
        "signature_count": len(signatures),
        "conservative_prior_upper_bound": 320,
        "exact_reachable_signature_count": 192,
        "compression_vs_prior_upper_bound": "192/320",
        "counts_by_end_phrase_index": per_end,
        "counts_by_nth_category": per_nth,
        "nth_forbidden_collision_signature_count": nth_collision_count,
        "end_forbidden_collision_signature_count": end_collision_count,
        "any_lexical_hard_collision_signature_count": any_collision_count,
        "representative_forbidden_cardinality": GENERATED_KEYWORD_COUNT,
        "terminal_data_used": False,
        "terminal_frequency_used": False,
        "hidden_kwargs_used": False,
        "acceptance_credit": False,
        "hard_nonclaims": [
            "NO_NUMERIC_OR_STRUCTURAL_SLOT_COMPLETENESS_CLAIM",
            "NO_REPEAT_PROMPT_TEXT_DOMAIN_COMPLETENESS_CLAIM",
            "NO_CANDIDATE_CONSTRUCTOR_COMPLETENESS_CLAIM",
            "NO_ACCEPTANCE_FAMILY_CAPABILITY_OR_OWNERSHIP_CREDIT",
        ],
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
