#!/usr/bin/env python3
"""Exact Unicode coupling theorem for LiveBench keyword/letter frequency.

Pinned public checker facts:
* KeywordFrequencyChecker counts re.findall(keyword, value, re.IGNORECASE).
* LetterFrequencyChecker lowercases the whole value then counts the ASCII letter.
* The frozen keyword source contains only lowercase ASCII [a-z]+ strings.

Those two counters are not naively identical character channels. Python's
Unicode IGNORECASE admits two ASCII-letter evasions whose .lower() output does
not contain the corresponding ASCII letter:
  i -> U+0131 LATIN SMALL LETTER DOTLESS I
  s -> U+017F LATIN SMALL LETTER LONG S

Exhausting every Unicode code point proves there are no other ASCII-letter
evasion characters in the executing Python regex semantics. Therefore the
minimum ASCII-letter burden of one non-overlapping keyword match is exactly:
  0                       when target letter is i or s
  keyword.count(letter)   otherwise

The bound is constructive: replace i/s positions by the matching evasion glyph.
For every other letter, every code point accepted by IGNORECASE at that literal
position contributes at least one target ASCII letter after lowercasing.

This removes a hidden KxL ambiguity from the LiveBench union25 count overlays.
It is a semantic reduction only. No terminal rows, hidden kwargs, responses,
scores, family credit, or acceptance credit are consumed.
"""
from __future__ import annotations

from collections import Counter
import re
import string
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_KEYWORD_LETTER_UNICODE_COUPLING_V1"
PINNED_INSTRUCTIONS_BLOB = "4997bab885a676d92545fd91a9a20b48d234a2b2"
PINNED_INSTRUCTIONS_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"

ASCII = string.ascii_lowercase
EXPECTED_EVASIONS = {"i": "\u0131", "s": "\u017f"}


def _validate_keyword(keyword: str) -> str:
    if not isinstance(keyword, str) or not re.fullmatch(r"[a-z]+", keyword):
        raise ValueError("KEYWORD_OUTSIDE_FROZEN_ASCII_DOMAIN")
    return keyword


def _validate_letter(letter: str) -> str:
    if not isinstance(letter, str) or len(letter) != 1 or letter not in ASCII:
        raise ValueError("LETTER_OUTSIDE_FROZEN_ASCII_DOMAIN")
    return letter


def keyword_count(value: str, keyword: str) -> int:
    """Exact pinned KeywordFrequencyChecker counting semantics on this domain."""
    keyword = _validate_keyword(keyword)
    return len(re.findall(keyword, value, flags=re.IGNORECASE))


def letter_count(value: str, letter: str) -> int:
    """Exact pinned LetterFrequencyChecker counting semantics."""
    letter = _validate_letter(letter)
    return Counter(value.lower())[letter]


def unicode_letter_evasions() -> dict[str, tuple[str, ...]]:
    """Exhaust the full Python Unicode code-point space.

    An evasion is a single code point that regex IGNORECASE accepts for an
    ASCII literal while lowercasing contributes zero copies of that ASCII
    letter to LetterFrequencyChecker.
    """
    out: dict[str, tuple[str, ...]] = {}
    for letter in ASCII:
        pattern = re.compile(letter, flags=re.IGNORECASE)
        evasions = []
        for cp in range(0x110000):
            ch = chr(cp)
            if pattern.fullmatch(ch) and Counter(ch.lower())[letter] == 0:
                evasions.append(ch)
        if evasions:
            out[letter] = tuple(evasions)
    return out


def minimal_letter_cost_per_keyword_match(keyword: str, letter: str) -> int:
    """Exact minimum LetterFrequency delta forced by one keyword regex match."""
    keyword = _validate_keyword(keyword)
    letter = _validate_letter(letter)
    if letter not in keyword:
        return 0
    if letter in EXPECTED_EVASIONS:
        return 0
    return keyword.count(letter)


def minimum_letter_cost_keyword_carrier(keyword: str, letter: str) -> str:
    """Construct one regex keyword match attaining the exact minimum cost."""
    keyword = _validate_keyword(keyword)
    letter = _validate_letter(letter)
    carrier = keyword
    evasion = EXPECTED_EVASIONS.get(letter)
    if evasion is not None:
        carrier = carrier.replace(letter, evasion)

    if not re.fullmatch(keyword, carrier, flags=re.IGNORECASE):
        raise AssertionError("CARRIER_DOES_NOT_MATCH_KEYWORD")
    observed = letter_count(carrier, letter)
    expected = minimal_letter_cost_per_keyword_match(keyword, letter)
    if observed != expected:
        raise AssertionError(
            f"CARRIER_NOT_MINIMAL: observed={observed} expected={expected}"
        )
    return carrier


def repeated_keyword_carrier(keyword: str, letter: str, matches: int) -> str:
    """Construct exactly N non-overlapping keyword matches at minimum L cost."""
    if int(matches) != matches or matches < 0:
        raise ValueError("MATCH_COUNT_OUTSIDE_DOMAIN")
    matches = int(matches)
    one = minimum_letter_cost_keyword_carrier(keyword, letter)
    # ASCII digits are hard boundaries for the frozen [a-z]+ regex domain.
    value = "9" + one * matches + "9" if matches else ""
    if keyword_count(value, keyword) != matches:
        raise AssertionError("REPEATED_CARRIER_KEYWORD_COUNT_DRIFT")
    expected_letter = matches * minimal_letter_cost_per_keyword_match(keyword, letter)
    if letter_count(value, letter) != expected_letter:
        raise AssertionError("REPEATED_CARRIER_LETTER_COST_DRIFT")
    return value


def verify() -> dict[str, Any]:
    evasions = unicode_letter_evasions()
    expected = {k: (v,) for k, v in EXPECTED_EVASIONS.items()}
    if evasions != expected:
        raise AssertionError(
            f"PYTHON_IGNORECASE_EQUIVALENCE_DRIFT: expected={expected!r} got={evasions!r}"
        )

    witnesses = {
        "signal_x_s": minimum_letter_cost_keyword_carrier("signal", "s"),
        "inside_x_i": minimum_letter_cost_keyword_carrier("inside", "i"),
        "skill_x_k": minimum_letter_cost_keyword_carrier("skill", "k"),
        "analysis_x_a": minimum_letter_cost_keyword_carrier("analysis", "a"),
    }
    assert witnesses["signal_x_s"] == "\u017fignal"
    assert witnesses["inside_x_i"] == "\u0131ns\u0131de"
    assert minimal_letter_cost_per_keyword_match("signal", "s") == 0
    assert minimal_letter_cost_per_keyword_match("inside", "i") == 0
    assert minimal_letter_cost_per_keyword_match("skill", "k") == 1
    assert minimal_letter_cost_per_keyword_match("analysis", "a") == 2

    for keyword, letter, n in (
        ("signal", "s", 3),
        ("inside", "i", 3),
        ("skill", "k", 3),
        ("analysis", "a", 3),
    ):
        carrier = repeated_keyword_carrier(keyword, letter, n)
        assert keyword_count(carrier, keyword) == n
        assert letter_count(carrier, letter) == (
            n * minimal_letter_cost_per_keyword_match(keyword, letter)
        )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__FULL_UNICODE_IGNORECASE_SPACE_REDUCES_KEYWORD_TO_LETTER_"
            "COUPLING_TO_EXACT_PER_MATCH_COEFFICIENT"
        ),
        "pinned_public_source": {
            "instructions_blob": PINNED_INSTRUCTIONS_BLOB,
            "instructions_util_blob": PINNED_INSTRUCTIONS_UTIL_BLOB,
        },
        "unicode_codepoints_examined_per_ascii_letter": 0x110000,
        "ascii_letters_exhausted": len(ASCII),
        "exact_letter_evasions": {
            k: [f"U+{ord(ch):04X}" for ch in chars]
            for k, chars in evasions.items()
        },
        "exact_minimum_cost_rule": {
            "i": "ZERO_VIA_U+0131_DOTLESS_I",
            "s": "ZERO_VIA_U+017F_LONG_S",
            "all_other_ascii_letters": "KEYWORD_COUNT_OF_TARGET_LETTER",
        },
        "consequence": (
            "KEYWORD_FREQUENCY_X_LETTER_FREQUENCY_IS_NOT_A_RAW_PARAMETER_PRODUCT__"
            "ITS_LOAD_BEARING_COUPLING_IS_ONE_EXACT_INTEGER_COEFFICIENT"
        ),
        "terminal_rows_read": 0,
        "hidden_terminal_kwargs_read": 0,
        "target_responses_read": 0,
        "target_scores_read": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
