#!/usr/bin/env python3
"""Exact two-counter kernel for frozen LiveBench keyword/letter frequency.

For an alphabetic keyword K and target letter L, let x be the frozen
KeywordFrequencyChecker's non-overlapping IGNORECASE match count and y be the
LetterFrequencyChecker's case-folded character count.

If K is the one-letter word L, x == y for every response.
Otherwise, with m = occurrences of L inside K, every keyword match consumes a
disjoint copy of K and therefore forces at least m target letters: y >= m*x.
Conversely every pair (x,y) satisfying that inequality is constructible with
separated e-mail-local-part carriers. The suffix "@0.0" adds no alphabetic
characters and prevents cross-token keyword matches.

This module solves the incremental version above an already-constructed base
response with exact (x0,y0) counts. It reads no benchmark rows or hidden kwargs.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_LEXICAL_COUNT_KERNEL_V1"
LESS = "less than"
AT_LEAST = "at least"
RELATIONS = {LESS, AT_LEAST}


class LexicalCountKernelError(ValueError):
    pass


@dataclass(frozen=True)
class Interval:
    lo: int
    hi: int | None

    def contains(self, value: int) -> bool:
        return value >= self.lo and (self.hi is None or value <= self.hi)


def _interval(relation: str, threshold: int) -> Interval:
    if relation not in RELATIONS:
        raise LexicalCountKernelError("UNSUPPORTED_RELATION")
    if not isinstance(threshold, int) or threshold < 1:
        raise LexicalCountKernelError("POSITIVE_INTEGER_THRESHOLD_REQUIRED")
    if relation == AT_LEAST:
        return Interval(threshold, None)
    return Interval(0, threshold - 1)


def _validate(keyword: str, letter: str, base_keyword_count: int, base_letter_count: int) -> tuple[str, str]:
    if not isinstance(keyword, str) or re.fullmatch(r"[A-Za-z]+", keyword) is None:
        raise LexicalCountKernelError("PUBLIC_ALPHA_KEYWORD_REQUIRED")
    if not isinstance(letter, str) or re.fullmatch(r"[A-Za-z]", letter) is None:
        raise LexicalCountKernelError("SINGLE_ALPHA_LETTER_REQUIRED")
    if base_keyword_count < 0 or base_letter_count < 0:
        raise LexicalCountKernelError("NONNEGATIVE_BASE_COUNTS_REQUIRED")
    k = keyword.lower()
    l = letter.lower()
    m = k.count(l)
    if len(k) == 1 and k == l:
        if base_keyword_count != base_letter_count:
            raise LexicalCountKernelError("IMPOSSIBLE_BASE_COUNTS_FOR_IDENTICAL_SINGLE_LETTER")
    elif base_letter_count < m * base_keyword_count:
        raise LexicalCountKernelError("IMPOSSIBLE_BASE_COUNTS_BELOW_FORCED_LETTER_FLOOR")
    return k, l


def solve_counts(
    *,
    keyword: str,
    letter: str,
    keyword_frequency: int,
    keyword_relation: str,
    letter_frequency: int,
    letter_relation: str,
    base_keyword_count: int = 0,
    base_letter_count: int = 0,
) -> dict[str, Any]:
    k, l = _validate(keyword, letter, base_keyword_count, base_letter_count)
    xi = _interval(keyword_relation, keyword_frequency)
    yi = _interval(letter_relation, letter_frequency)

    xlo = max(base_keyword_count, xi.lo)
    ylo = max(base_letter_count, yi.lo)
    if xi.hi is not None and xlo > xi.hi:
        return _unsat("BASE_OR_REQUIRED_KEYWORD_COUNT_EXCEEDS_UPPER_BOUND", k, l)
    if yi.hi is not None and ylo > yi.hi:
        return _unsat("BASE_OR_REQUIRED_LETTER_COUNT_EXCEEDS_UPPER_BOUND", k, l)

    identical = len(k) == 1 and k == l
    m = k.count(l)

    if identical:
        zlo = max(xlo, ylo)
        zhi_candidates = [v for v in (xi.hi, yi.hi) if v is not None]
        zhi = min(zhi_candidates) if zhi_candidates else None
        if zhi is not None and zlo > zhi:
            return _unsat("IDENTICAL_SINGLE_LETTER_INTERVALS_DISJOINT", k, l)
        x = y = zlo
    else:
        # Added keyword matches each force m target letters. Choosing the
        # smallest admissible x is always optimal for feasibility because x has
        # no negative contribution to any other bound.
        x = xlo
        forced_y = base_letter_count + m * (x - base_keyword_count)
        y = max(ylo, forced_y)
        if yi.hi is not None and y > yi.hi:
            return _unsat("KEYWORD_LOWER_BOUND_FORCES_LETTER_UPPER_BOUND_VIOLATION", k, l)

    dx = x - base_keyword_count
    dy = y - base_letter_count
    if identical:
        assert dx == dy
        extra_letter_only = 0
    else:
        extra_letter_only = dy - m * dx
        assert extra_letter_only >= 0

    return {
        "schema": SCHEMA,
        "status": "SAT__EXACT_COUNT_LATTICE_WITNESS",
        "keyword": k,
        "letter": l,
        "keyword_letter_multiplicity": m,
        "identical_single_letter": identical,
        "base_keyword_count": base_keyword_count,
        "base_letter_count": base_letter_count,
        "target_keyword_count": x,
        "target_letter_count": y,
        "add_keyword_matches": dx,
        "add_letter_only_occurrences": extra_letter_only,
        "addendum": build_addendum(
            keyword=k,
            letter=l,
            add_keyword_matches=dx,
            add_letter_only_occurrences=extra_letter_only,
            identical_single_letter=identical,
        ),
        "terminal_rows_used": False,
    }


def _unsat(reason: str, keyword: str, letter: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "UNSAT__EXACT_COUNT_LATTICE",
        "reason": reason,
        "keyword": keyword,
        "letter": letter,
        "terminal_rows_used": False,
    }


def build_addendum(
    *,
    keyword: str,
    letter: str,
    add_keyword_matches: int,
    add_letter_only_occurrences: int,
    identical_single_letter: bool | None = None,
) -> str:
    if add_keyword_matches < 0 or add_letter_only_occurrences < 0:
        raise LexicalCountKernelError("NONNEGATIVE_INCREMENT_REQUIRED")
    k = keyword.lower()
    l = letter.lower()
    same = (len(k) == 1 and k == l) if identical_single_letter is None else identical_single_letter
    if same and add_letter_only_occurrences:
        raise LexicalCountKernelError("IDENTICAL_SINGLE_LETTER_HAS_NO_LETTER_ONLY_INCREMENT")

    tokens: list[str] = []
    # Each token is independently delimited. The numeric domain contributes no
    # alphabetic characters and cannot create a cross-token alphabetic keyword.
    tokens.extend(f"{k}@0.0" for _ in range(add_keyword_matches))
    if not same:
        tokens.extend(f"{l}@0.0" for _ in range(add_letter_only_occurrences))
    return " ".join(tokens)


def exact_counts(text: str, keyword: str, letter: str) -> tuple[int, int]:
    return (
        len(re.findall(keyword, text, flags=re.IGNORECASE)),
        text.lower().count(letter.lower()),
    )


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = dict(args or {})
    return solve_counts(**args)


if __name__ == "__main__":
    import json, sys
    print(json.dumps(run(json.load(sys.stdin)), indent=2, sort_keys=True))
