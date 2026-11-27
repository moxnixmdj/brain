#!/usr/bin/env python3
"""Exact reachable lexical collision quotient for frozen active15 LiveBench.

Raw lexical slots come from the frozen public 1,525-word generator domain, but
the current visible-only constructors/checkers observe only:
- whether the NTH first word is forbidden;
- whether a whole word forced by the selected fixed end phrase is forbidden.

Existence keywords do not add lexical collision state for the current
constructors: generated words are ASCII alphabetic, required carriers append a
digit/letter suffix, and the source-bound audit found no generated word equal to
the carrier. Generic word identities therefore quotient away.

This module enumerates the *reachable* quotient, not a loose Cartesian upper
bound. It consumes no terminal rows, hidden kwargs, responses, scores, or case
frequencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_LEXICAL_COLLISION_QUOTIENT_V1"

FIRST_END = "Any other questions?"
SECOND_END = "Is there anything else I can help with?"
END_PHRASES = (FIRST_END, SECOND_END)

SPECIAL_WORDS = ("other", "anything", "can", "help")
OTHER = "__OTHER_WORD_LIST_VALUE__"

# All are exact members of the source-bound 1,525-value public WORD_LIST.
# They are used only to construct canonical representatives of quotient classes.
GENERIC_REPRESENTATIVES = (
    "western",
    "sentence",
    "signal",
    "dump",
    "spot",
    "opposite",
    "bottom",
    "potato",
)

_END_RELEVANT = {
    FIRST_END: ("other",),
    SECOND_END: ("anything", "can", "help"),
}


@dataclass(frozen=True, order=True)
class Signature:
    end_phrase: str
    nth_category: str
    nth_is_forbidden: bool
    end_forbidden_mask: tuple[bool, ...]

    def as_dict(self) -> dict[str, Any]:
        words = _END_RELEVANT[self.end_phrase]
        return {
            "end_phrase": self.end_phrase,
            "nth_category": self.nth_category,
            "nth_is_forbidden": self.nth_is_forbidden,
            "end_forbidden": {
                word: bit for word, bit in zip(words, self.end_forbidden_mask)
            },
        }


def _norm_word(value: Any) -> str:
    word = str(value or "").strip().casefold()
    if not word or not word.isascii() or not word.isalpha():
        raise ValueError("WORD_MUST_BE_NONEMPTY_ASCII_ALPHA")
    return word


def nth_category(first_word: Any) -> str:
    word = _norm_word(first_word)
    return word if word in SPECIAL_WORDS else OTHER


def project(
    *,
    nth_first_word: Any,
    forbidden_words: Iterable[Any],
    end_phrase: Any,
) -> Signature:
    end = str(end_phrase or "").strip()
    if end not in END_PHRASES:
        raise ValueError("END_PHRASE_OUTSIDE_FROZEN_PUBLIC_DOMAIN")

    nth = _norm_word(nth_first_word)
    forbidden = tuple(_norm_word(x) for x in forbidden_words)
    if len(forbidden) != 5:
        raise ValueError("FORBIDDEN_WORD_COUNT_MUST_EQUAL_GENERATOR_FIVE")
    if len(set(forbidden)) != 5:
        raise ValueError("FORBIDDEN_WORDS_MUST_BE_UNIQUE")

    forbidden_set = set(forbidden)
    relevant = _END_RELEVANT[end]
    return Signature(
        end_phrase=end,
        nth_category=nth_category(nth),
        nth_is_forbidden=nth in forbidden_set,
        end_forbidden_mask=tuple(word in forbidden_set for word in relevant),
    )


def _reachable(sig: Signature) -> bool:
    relevant = _END_RELEVANT.get(sig.end_phrase)
    if relevant is None or len(sig.end_forbidden_mask) != len(relevant):
        return False
    if sig.nth_category not in (*SPECIAL_WORDS, OTHER):
        return False
    # If the NTH word is itself one of the end-relevant special words, the two
    # observations are literally the same set-membership fact and cannot vary
    # independently.
    if sig.nth_category in relevant:
        i = relevant.index(sig.nth_category)
        return sig.nth_is_forbidden == sig.end_forbidden_mask[i]
    return True


def enumerate_reachable_signatures() -> tuple[Signature, ...]:
    out: list[Signature] = []
    for end in END_PHRASES:
        width = len(_END_RELEVANT[end])
        for category in (*SPECIAL_WORDS, OTHER):
            for nth_forbidden in (False, True):
                for mask in product((False, True), repeat=width):
                    sig = Signature(end, category, nth_forbidden, tuple(mask))
                    if _reachable(sig):
                        out.append(sig)
    return tuple(sorted(set(out)))


def representative(sig: Signature) -> dict[str, Any]:
    if not _reachable(sig):
        raise ValueError("UNREACHABLE_SIGNATURE")

    nth = (
        sig.nth_category
        if sig.nth_category in SPECIAL_WORDS
        else GENERIC_REPRESENTATIVES[0]
    )
    relevant = _END_RELEVANT[sig.end_phrase]

    chosen: list[str] = [
        word for word, bit in zip(relevant, sig.end_forbidden_mask) if bit
    ]
    if sig.nth_is_forbidden and nth not in chosen:
        chosen.append(nth)

    # Fill to the exact historical five-word forbidden set using generic public
    # WORD_LIST members. Never introduce an unrequested special collision.
    for word in GENERIC_REPRESENTATIVES[1:]:
        if len(chosen) >= 5:
            break
        if word == nth and not sig.nth_is_forbidden:
            continue
        if word not in chosen:
            chosen.append(word)

    if len(chosen) != 5 or len(set(chosen)) != 5:
        raise RuntimeError("REPRESENTATIVE_CONSTRUCTION_FAILED")
    if any(
        word in chosen
        for word, bit in zip(relevant, sig.end_forbidden_mask)
        if not bit
    ):
        raise RuntimeError("REPRESENTATIVE_INTRODUCED_END_COLLISION")
    if (nth in set(chosen)) != sig.nth_is_forbidden:
        raise RuntimeError("REPRESENTATIVE_NTH_MEMBERSHIP_DRIFT")

    row = {
        "nth_first_word": nth,
        "forbidden_words": chosen,
        "end_phrase": sig.end_phrase,
    }
    if project(**row) != sig:
        raise RuntimeError("REPRESENTATIVE_ROUNDTRIP_FAILED")
    return row


def verify() -> dict[str, Any]:
    signatures = enumerate_reachable_signatures()
    first = [s for s in signatures if s.end_phrase == FIRST_END]
    second = [s for s in signatures if s.end_phrase == SECOND_END]
    if len(first) != 18:
        raise RuntimeError("FIRST_END_SIGNATURE_COUNT_DRIFT")
    if len(second) != 56:
        raise RuntimeError("SECOND_END_SIGNATURE_COUNT_DRIFT")
    if len(signatures) != 74:
        raise RuntimeError("TOTAL_SIGNATURE_COUNT_DRIFT")

    reps = [representative(sig) for sig in signatures]
    if len({project(**row) for row in reps}) != 74:
        raise RuntimeError("REPRESENTATIVE_BIJECTION_FAILED")

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_REACHABLE_LEXICAL_COLLISION_QUOTIENT_74",
        "raw_word_list_value_count": 1525,
        "prior_conservative_signature_upper_bound": 320,
        "reachable_signature_count": 74,
        "first_end_signature_count": len(first),
        "second_end_signature_count": len(second),
        "reduction_factor_from_prior_upper_bound": 320 / 74,
        "signature_fields": [
            "selected_fixed_end_phrase",
            "nth_word_category_among_other_anything_can_help_or_generic",
            "nth_word_membership_in_five_forbidden_words",
            "forbidden_membership_bits_only_for_words_forced_by_selected_end_phrase",
        ],
        "representative_count": len(reps),
        "terminal_rows_read": 0,
        "terminal_case_frequencies_used": False,
        "acceptance_credit": False,
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
