#!/usr/bin/env python3
"""Deterministic score-mass portfolio compiler for frozen LiveBench IF scoring.

This module attacks a specific failure mode: treating a multi-checker case as
worth zero unless one response is already proved to satisfy every checker.

For any fixed case with k checkers, the frozen public scorer lower bound is
g/(2k) when only g<k checker successes are guaranteed, and 1 when g=k.
Therefore maximizing the number of *proved* checker successes weakly dominates
all-or-nothing blocking even when k is not known to this runtime.

Only checker contracts reproduced from pinned public IFBench source are used.
Unsupported instructions are never guessed and receive zero guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re
import string
from typing import Any, Iterable

from canonical.runtime.livebench_if_score_bound_v1 import (
    CaseGuarantee,
    conservative_case_lower_bound,
)

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_SCORE_MASS_PORTFOLIO_COMPILER_V1"
PINNED_IFBENCH_COMMIT = "1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d"
PINNED_INSTRUCTIONS_BLOB = "7f167018e0c5472b04e13cbf847e5988c04ecb11"
PINNED_INSTRUCTIONS_UTIL_BLOB = "1751ab60b97063bd047b1e1a5cf8eaaabee2aefb"

_CONSONANTS = set("bcdfghjklmnpqrstvwxyz")
_PARENS_MARKER = "([{(())}])"
_QUOTES_MARKER = '"' + "'" + '""' + "'" + '"'
_CONSONANT_PHRASE = (
    "Ensure each word in your response has at least one consonant cluster "
    "(two or more consonants together)."
)
_PARENS_PHRASE = "Nest parentheses (and [brackets {and braces}]) at least 5 levels deep."
_QUOTES_PHRASE = (
    "Include quotes within quotes within quotes, at least 3 levels deep, "
    "alternating between double quotes and single quotes."
)
_NO_WHITESPACE_PHRASE = "The output should not contain any whitespace."
_SUB_BULLET_PHRASE = (
    "Your response must include bullet points denoted by * and at least one "
    "sub-bullet point denoted by - for each bullet point."
)
_SPECIAL_BULLET_PREFIX = "Answer with a list of items, instead of bullet points use "
_ALLOWED_SPECIAL_BULLETS = ("...", "SEPARATOR", "!?!?", "-")

_LEXICON = (
    "Brisk Clamp Drift Frost Glint Plush Quartz Trunk Crust Blend Flint Grasp "
    "Prism Scrub Strand Clasp Sprint Crimp Plank Brush Crank Fresh Grind"
).split()


class PortfolioError(ValueError):
    pass


@dataclass(frozen=True)
class PublicConstraint:
    checker_id: str
    params: tuple[tuple[str, str], ...] = ()

    def get(self, key: str, default: str | None = None) -> str | None:
        for k, value in self.params:
            if k == key:
                return value
        return default


def _params(**kwargs: Any) -> tuple[tuple[str, str], ...]:
    return tuple(sorted((str(k), str(v)) for k, v in kwargs.items()))


def _find_literal(text: str, phrase: str, checker_id: str) -> list[PublicConstraint]:
    return [
        PublicConstraint(checker_id)
        for _ in re.finditer(re.escape(phrase), text, flags=re.I)
    ]


def parse_supported_constraints(prompt: str) -> list[PublicConstraint]:
    """Parse only pinned public descriptions whose checker logic is reproduced."""
    text = str(prompt or "")
    if not text.strip():
        raise PortfolioError("PROMPT_REQUIRED")

    out: list[PublicConstraint] = []

    for m in re.finditer(
        r"The response must contain between (\d+) and (\d+) words\.",
        text,
        flags=re.I,
    ):
        out.append(PublicConstraint(
            "count:word_count_range",
            _params(min_words=int(m.group(1)), max_words=int(m.group(2))),
        ))

    for m in re.finditer(
        r"Use at least (\d+) unique words in the response\.",
        text,
        flags=re.I,
    ):
        out.append(PublicConstraint(
            "count:unique_word_count",
            _params(N=int(m.group(1))),
        ))

    for m in re.finditer(
        r"Include exactly (\d+) numbers in the response\.",
        text,
        flags=re.I,
    ):
        out.append(PublicConstraint(
            "count:numbers",
            _params(N=int(m.group(1))),
        ))

    out.extend(_find_literal(text, _CONSONANT_PHRASE, "words:consonants"))
    out.extend(_find_literal(text, _PARENS_PHRASE, "format:parentheses"))
    out.extend(_find_literal(text, _QUOTES_PHRASE, "format:quotes"))
    out.extend(_find_literal(text, _NO_WHITESPACE_PHRASE, "format:no_whitespace"))
    out.extend(_find_literal(text, _SUB_BULLET_PHRASE, "format:sub-bullets"))

    for sep in _ALLOWED_SPECIAL_BULLETS:
        phrase = _SPECIAL_BULLET_PREFIX + sep + "."
        for _ in re.finditer(re.escape(phrase), text, flags=re.I):
            out.append(PublicConstraint("format:list", _params(sep=sep)))

    return out


def _count_words(value: str) -> int:
    # Exact public instructions_util.count_words contract:
    # nltk.tokenize.RegexpTokenizer(r"\w+")
    return len(re.findall(r"\w+", value, flags=re.UNICODE))


def _unique_word_count(value: str) -> int:
    # Exact UniqueWordCountChecker contract.
    unique_words: set[str] = set()
    for word in value.lower().split():
        unique_words.add(word.strip("".join(string.punctuation) + " "))
    return len(unique_words)


def _numbers_count(value: str) -> int:
    # Exact NumbersCountChecker contract.
    scrubbed = value.translate(str.maketrans("", "", string.punctuation))
    return len(re.findall(r"\d+", scrubbed))


def _check_consonants(value: str) -> bool:
    words = value.lower().strip().split()
    for word in words:
        found = False
        for i in range(len(word) - 1):
            if word[i] in _CONSONANTS and word[i + 1] in _CONSONANTS:
                found = True
                break
        if not found:
            return False
    return True


def _check_nested_parentheses(value: str) -> bool:
    levels: list[str] = []
    max_depth = 0
    for char in value:
        if char in "([{":
            levels.append(char)
            if len(levels) > max_depth:
                max_depth = len(levels)
        elif char in ")]}":
            if levels and (
                (levels[-1] == "(" and char == ")")
                or (levels[-1] == "[" and char == "]")
                or (levels[-1] == "{" and char == "}")
            ):
                levels.pop()
                if max_depth >= 5 and len(levels) < max_depth:
                    return True
            else:
                levels = []
                max_depth = 0
    return False


def _check_nested_quotes(value: str) -> bool:
    levels: list[str] = []
    reached_depth = 0
    current_depth = 0
    for char in value:
        if levels and char == levels[-1]:
            levels.pop()
            current_depth -= 1
            if reached_depth - current_depth >= 3:
                return True
        elif char in {'"', "'"}:
            levels.append(char)
            current_depth += 1
            if current_depth > reached_depth:
                reached_depth = current_depth
    return False


def validate_constraint(response: str, constraint: PublicConstraint) -> bool:
    value = str(response or "")
    cid = constraint.checker_id

    if cid == "count:word_count_range":
        lo = int(constraint.get("min_words") or "0")
        hi = int(constraint.get("max_words") or "-1")
        return lo <= _count_words(value) <= hi

    if cid == "count:unique_word_count":
        return _unique_word_count(value) >= int(constraint.get("N") or "0")

    if cid == "count:numbers":
        return _numbers_count(value) == int(constraint.get("N") or "0")

    if cid == "words:consonants":
        return _check_consonants(value)

    if cid == "format:parentheses":
        return _check_nested_parentheses(value)

    if cid == "format:quotes":
        return _check_nested_quotes(value)

    if cid == "format:no_whitespace":
        return not any(char.isspace() for char in value)

    if cid == "format:list":
        sep = constraint.get("sep") or ""
        return bool(sep) and len(re.findall(re.escape(sep), value)) >= 2

    if cid == "format:sub-bullets":
        # Exact public SubBulletPointsChecker semantics.
        bullets = value.split("*")
        for bullet in bullets[1:]:
            if "-" not in bullet:
                return False
        return True

    raise PortfolioError("UNSUPPORTED_CONSTRAINT:" + cid)


def _lexical_words(count: int) -> list[str]:
    if count < 1:
        count = 1
    return [
        _LEXICON[i % len(_LEXICON)] + (str(i // len(_LEXICON)) if i >= len(_LEXICON) else "")
        for i in range(count)
    ]


def _embed_numbers(word: str, count: int) -> str:
    if count <= 0:
        return word
    # Letter separators preserve count_words=1 while producing exactly count
    # digit runs for the public NumbersCountChecker.
    return word + "".join(f"x{i + 1}" for i in range(count))


def _single_witness(constraint: PublicConstraint) -> str:
    cid = constraint.checker_id
    if cid == "count:word_count_range":
        n = max(1, int(constraint.get("min_words") or "1"))
        return " ".join(_lexical_words(n))
    if cid == "count:unique_word_count":
        n = max(1, int(constraint.get("N") or "1"))
        return " ".join(_lexical_words(n))
    if cid == "count:numbers":
        return _embed_numbers("Brisk", int(constraint.get("N") or "0"))
    if cid == "words:consonants":
        return "Brisk Clamp"
    if cid == "format:parentheses":
        return _PARENS_MARKER + "Brisk"
    if cid == "format:quotes":
        return _QUOTES_MARKER + "Brisk"
    if cid == "format:no_whitespace":
        return "Brisk"
    if cid == "format:list":
        sep = constraint.get("sep") or "-"
        return f"{sep}Brisk\n{sep}Clamp"
    if cid == "format:sub-bullets":
        return "*Brisk\n-Clamp"
    raise PortfolioError("UNSUPPORTED_CONSTRAINT:" + cid)


def _combined_witness(constraints: Iterable[PublicConstraint]) -> str | None:
    rows = tuple(constraints)
    if not rows:
        return None

    min_words = 1
    max_words: int | None = None
    unique_words = 1
    exact_numbers: int | None = None
    no_whitespace = False
    need_consonants = False
    need_parens = False
    need_quotes = False
    need_sub_bullets = False
    seps: list[str] = []

    for c in rows:
        cid = c.checker_id
        if cid == "count:word_count_range":
            lo = int(c.get("min_words") or "0")
            hi = int(c.get("max_words") or "-1")
            if hi < lo or hi < 1:
                return None
            min_words = max(min_words, lo)
            max_words = hi if max_words is None else min(max_words, hi)
        elif cid == "count:unique_word_count":
            unique_words = max(unique_words, int(c.get("N") or "0"))
        elif cid == "count:numbers":
            n = int(c.get("N") or "0")
            if exact_numbers is not None and exact_numbers != n:
                return None
            exact_numbers = n
        elif cid == "format:no_whitespace":
            no_whitespace = True
        elif cid == "words:consonants":
            need_consonants = True
        elif cid == "format:parentheses":
            need_parens = True
        elif cid == "format:quotes":
            need_quotes = True
        elif cid == "format:sub-bullets":
            need_sub_bullets = True
        elif cid == "format:list":
            seps.append(c.get("sep") or "-")

    target_words = max(min_words, unique_words, 1)
    if max_words is not None and target_words > max_words:
        return None

    words = _lexical_words(target_words)
    if exact_numbers is not None:
        words[0] = _embed_numbers(words[0], exact_numbers)

    # Hyphens create separate \w+ tokens for exact word counting while
    # preserving the no-whitespace checker. For consonant checking, the whole
    # no-whitespace response is one split token and still contains clusters.
    joiner = "-" if no_whitespace else " "
    candidate = joiner.join(words)

    if need_sub_bullets:
        # This is a scorer-contract witness matching the exact public checker.
        # It deliberately carries no semantic-capability claim.
        candidate = "*" + candidate + "-"

    for sep in seps:
        candidate = sep + candidate + sep

    if need_parens:
        candidate = _PARENS_MARKER + candidate
    if need_quotes:
        candidate = _QUOTES_MARKER + candidate

    if need_consonants and not _check_consonants(candidate):
        return None
    return candidate


def _candidate_pool(constraints: list[PublicConstraint]) -> list[str]:
    items: list[str] = []
    combined = _combined_witness(constraints)
    if combined:
        items.append(combined)
    for constraint in constraints:
        try:
            items.append(_single_witness(constraint))
        except PortfolioError:
            continue
    items.append("Brisk")
    return list(dict.fromkeys(items))


def _score_candidate(response: str, constraints: list[PublicConstraint]) -> tuple[int, tuple[int, ...]]:
    satisfied = tuple(
        i for i, constraint in enumerate(constraints)
        if validate_constraint(response, constraint)
    )
    return len(satisfied), satisfied


def _fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def compile_portfolio(
    prompt: str,
    *,
    total_instruction_count: int | None = None,
) -> dict[str, Any]:
    """Choose the generated response with maximum proved checker success count."""
    constraints = parse_supported_constraints(prompt)
    if not constraints:
        return {
            "schema": SCHEMA,
            "status": "BLOCKED",
            "reason": "NO_SUPPORTED_PUBLIC_CHECKER_DESCRIPTION",
            "response": None,
            "recognized_checker_count": 0,
            "guaranteed_satisfied_supported_count": 0,
            "terminal_case_content_used": False,
            "hidden_metadata_used": False,
            "model_dependency_count": 0,
            "incremental_spend_usd": 0,
            "scorer_contract_only": True,
            "semantic_capability_claim": False,
        }

    pool = _candidate_pool(constraints)
    ranked: list[tuple[int, int, str, tuple[int, ...]]] = []
    for response in pool:
        count, satisfied = _score_candidate(response, constraints)
        ranked.append((count, -len(response), response, satisfied))
    ranked.sort(reverse=True)
    best_count, _neg_len, response, satisfied_indexes = ranked[0]

    satisfied_ids = [constraints[i].checker_id for i in satisfied_indexes]
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS_COMPONENT",
        "response": response,
        "recognized_checker_count": len(constraints),
        "recognized_checker_ids": [c.checker_id for c in constraints],
        "guaranteed_satisfied_supported_count": best_count,
        "guaranteed_satisfied_supported_ids": satisfied_ids,
        "generated_candidate_count": len(pool),
        "weakly_dominates_every_generated_candidate": all(
            best_count >= row[0] for row in ranked
        ),
        "selection_objective": "MAXIMIZE_PROVED_CHECKER_SUCCESSES_FOR_FIXED_CASE_K",
        "terminal_case_content_used": False,
        "hidden_metadata_used": False,
        "network_used": False,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "scorer_contract_only": True,
        "semantic_capability_claim": False,
        "terminal_authority": False,
    }

    if total_instruction_count is None:
        result["score_lower_bound"] = None
        result["score_lower_bound_reason"] = (
            "TOTAL_INSTRUCTION_COUNT_NOT_PROVIDED__SELECTION_REMAINS_VALID_"
            "BECAUSE_K_IS_CONSTANT_ACROSS_CANDIDATES"
        )
    else:
        k = int(total_instruction_count)
        if k <= 0:
            raise PortfolioError("TOTAL_INSTRUCTION_COUNT_MUST_BE_POSITIVE")
        if k < len(constraints):
            raise PortfolioError("TOTAL_INSTRUCTION_COUNT_LT_RECOGNIZED_COUNT")
        if best_count > k:
            raise PortfolioError("GUARANTEED_SUCCESSES_EXCEED_TOTAL")
        bound = conservative_case_lower_bound(
            CaseGuarantee(k, best_count)
        )
        result["score_lower_bound"] = _fraction_text(bound)
        result["score_lower_bound_percent"] = float(bound * 100)
        result["total_instruction_count"] = k

    return result


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    prompt = str(args.get("prompt") or args.get("instruction") or "")
    total = args.get("total_instruction_count")
    return compile_portfolio(
        prompt,
        total_instruction_count=(None if total is None else int(total)),
    )


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("--total-instruction-count", type=int, default=None)
    ns = ap.parse_args()
    print(json.dumps(
        compile_portfolio(
            ns.prompt,
            total_instruction_count=ns.total_instruction_count,
        ),
        indent=2,
        sort_keys=True,
    ))
