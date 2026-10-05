from __future__ import annotations

import re
import string
from dataclasses import dataclass
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_NGRAM_PUBLIC_FAMILY_COMPILER_V2"
TOLERANCE_PERCENT = 2.0
PUBLIC_SCOPE = "PINNED_PUBLIC_IFBENCH_RATIO_OVERLAP_GRAMMAR_V2"

_RATIO_DESC_RE = re.compile(
    r"Maintain a trigram overlap of (?P<percentage>\d+(?:\.\d+)?)% \(±2%\) "
    r"with the provided reference text\."
)
_KEYWORD_DESC_RE = re.compile(
    r'The response must include keyword\s+"?(?P<word>[^"\s]+)"?\s+in the\s+'
    r'(?P<N>\d+)-(?:st|nd|rd|th) sentence\.'
)
_CONSONANT_DESC = (
    "Ensure each word in your response has at least one consonant cluster "
    "(two or more consonants together)."
)
_BOUNDARY_IGNORABLE_RE = re.compile(
    r"^[\s\u200B\u200C\u200D\u2060\uFEFF]+|"
    r"[\s\u200B\u200C\u200D\u2060\uFEFF]+$"
)
_CONSONANTS = set("bcdfghjklmnpqrstvwxyz")
_ASCII_LETTERS = set(string.ascii_lowercase)


class PublicFamilyCompilerError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedPrompt:
    normalized_reference: str
    percentage: float
    keyword: str | None
    keyword_sentence: int | None
    consonant_cluster_required: bool


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _trim_boundary_ignorables(value: str) -> str:
    return _BOUNDARY_IGNORABLE_RE.sub("", str(value))


def char_trigrams(value: str) -> set[str]:
    value = str(value)
    return {value[i : i + 3] for i in range(max(0, len(value) - 2))}


def overlap_percent(response: str, reference: str) -> float:
    grams = char_trigrams(response)
    if not grams:
        raise PublicFamilyCompilerError("RESPONSE_TOO_SHORT_FOR_TRIGRAMS")
    ref = char_trigrams(reference)
    return 100.0 * len(grams & ref) / len(grams)


def consonant_cluster_pass(value: str) -> bool:
    words = value.lower().strip().split()
    for word in words:
        if all(char not in _ASCII_LETTERS for char in word):
            continue
        if not any(
            word[i] in _CONSONANTS and word[i + 1] in _CONSONANTS
            for i in range(len(word) - 1)
        ):
            return False
    return True


def parse_public_ratio_prompt(prompt: str) -> ParsedPrompt:
    s = normalize_ws(prompt)
    ratio_matches = list(_RATIO_DESC_RE.finditer(s))
    if len(ratio_matches) != 1:
        raise PublicFamilyCompilerError("RATIO_DESCRIPTION_COUNT_NOT_ONE")
    percentage = float(ratio_matches[0].group("percentage"))

    keyword_matches = list(_KEYWORD_DESC_RE.finditer(s))
    if len(keyword_matches) > 1:
        raise PublicFamilyCompilerError("KEYWORD_DESCRIPTION_COUNT_GT_ONE")
    keyword = None
    keyword_sentence = None
    if keyword_matches:
        keyword = keyword_matches[0].group("word")
        keyword_sentence = int(keyword_matches[0].group("N"))
        if keyword_sentence < 1:
            raise PublicFamilyCompilerError("KEYWORD_SENTENCE_LT_ONE")

    consonant_required = _CONSONANT_DESC in s

    # Strip only the exact public companion descriptions proved in the pinned
    # public family. The residual visible text is the whitespace-normalized
    # reference. This is deliberately not a universal prompt parser.
    s = _RATIO_DESC_RE.sub(" ", s, count=1)
    s = _KEYWORD_DESC_RE.sub(" ", s)
    s = s.replace(_CONSONANT_DESC, " ")
    s = _trim_boundary_ignorables(normalize_ws(s))
    s = normalize_ws(s)

    if len(s) < 3:
        raise PublicFamilyCompilerError("RECOVERED_REFERENCE_TOO_SHORT")
    if _RATIO_DESC_RE.search(s):
        raise PublicFamilyCompilerError("RATIO_DESCRIPTION_REMAINS")
    if _KEYWORD_DESC_RE.search(s):
        raise PublicFamilyCompilerError("KEYWORD_DESCRIPTION_REMAINS")
    if _CONSONANT_DESC in s:
        raise PublicFamilyCompilerError("CONSONANT_DESCRIPTION_REMAINS")

    return ParsedPrompt(
        normalized_reference=s,
        percentage=percentage,
        keyword=keyword,
        keyword_sentence=keyword_sentence,
        consonant_cluster_required=consonant_required,
    )


def _fresh_chars(reference: str, count: int) -> str:
    if count < 0:
        raise PublicFamilyCompilerError("NEGATIVE_FRESH_COUNT")
    out: list[str] = []
    for cp in range(0xE000, 0xF8FF + 1):
        ch = chr(cp)
        if ch not in reference:
            out.append(ch)
            if len(out) == count:
                return "".join(out)
    if count == 0:
        return ""
    raise PublicFamilyCompilerError("INSUFFICIENT_PRIVATE_USE_SENTINELS")


def _candidate_token_substrings(reference: str) -> Iterable[str]:
    for token in normalize_ws(reference).split(" "):
        if len(token) < 3:
            continue
        for start in range(len(token) - 2):
            for end in range(start + 3, len(token) + 1):
                yield token[start:end]


def _strictly_in_band(score: float, target: float) -> bool:
    return target - TOLERANCE_PERCENT < score < target + TOLERANCE_PERCENT


def _construct_ordinary(
    reference: str,
    target: float,
    *,
    consonant_cluster_required: bool,
    max_filler_chars: int = 256,
) -> dict:
    fresh = _fresh_chars(reference, max_filler_chars)
    best: tuple[tuple, dict] | None = None
    for base in _candidate_token_substrings(reference):
        for filler_len in range(max_filler_chars + 1):
            response = base + fresh[:filler_len]
            if consonant_cluster_required and not consonant_cluster_pass(response):
                continue
            score = overlap_percent(response, reference)
            if not _strictly_in_band(score, target):
                continue
            record = {
                "response": response,
                "score_against_normalized_reference_percent": score,
                "base": base,
                "filler_len": filler_len,
                "composition": "ORDINARY_WHITESPACE_FREE",
            }
            key = (len(response), abs(score - target), response)
            if best is None or key < best[0]:
                best = (key, record)
    if best is None:
        raise PublicFamilyCompilerError("NO_ORDINARY_WITNESS_FOUND")
    return best[1]


def _reference_tokens_for_keyword_composition(reference: str) -> list[str]:
    tokens = {token for token in normalize_ws(reference).split(" ") if len(token) >= 3}
    return sorted(tokens, key=lambda t: (-len(char_trigrams(t)), -len(t), t))


def _constructed_keyword_sentence_pass(
    response: str, keyword: str, sentence_number: int
) -> bool:
    # The constructor emits only "." as sentence punctuation and emits neither
    # whitespace nor abbreviation-shaped ASCII around the periods before the
    # target. Under the pinned splitter those periods are exact sentence stops.
    sentences = response.split(".")
    if sentences and sentences[-1] == "":
        sentences = sentences[:-1]
    return (
        len(sentences) >= sentence_number
        and keyword.lower() in sentences[sentence_number - 1].lower()
    )


def _construct_keyword(
    reference: str,
    target: float,
    keyword: str,
    sentence_number: int,
    *,
    max_extra_filler: int = 1024,
) -> dict:
    if not keyword or any(ch.isspace() for ch in keyword):
        raise PublicFamilyCompilerError("KEYWORD_NOT_SINGLE_VISIBLE_TOKEN")
    tokens = _reference_tokens_for_keyword_composition(reference)
    fresh = _fresh_chars(
        reference,
        sentence_number + len(tokens) + max_extra_filler + 8,
    )
    prefix = "".join(fresh[i] + "." for i in range(sentence_number - 1))
    best: tuple[tuple, dict] | None = None

    selected: list[str] = []
    token_variants: list[list[str]] = [[]]
    for token in tokens:
        selected = [*selected, token]
        token_variants.append(selected)

    for selected_tokens in token_variants:
        idx = sentence_number - 1
        core = fresh[idx] + keyword
        idx += 1
        for token in selected_tokens:
            core += fresh[idx] + token
            idx += 1
        core += fresh[idx]
        idx += 1

        for extra in range(max_extra_filler + 1):
            response = prefix + core + fresh[idx : idx + extra] + "."
            score = overlap_percent(response, reference)
            if _strictly_in_band(score, target):
                if not _constructed_keyword_sentence_pass(
                    response, keyword, sentence_number
                ):
                    raise AssertionError("INTERNAL_KEYWORD_SENTENCE_CONSTRUCTION_BUG")
                record = {
                    "response": response,
                    "score_against_normalized_reference_percent": score,
                    "selected_reference_tokens": selected_tokens,
                    "extra_filler_len": extra,
                    "composition": "KEYWORD_SENTENCE_WHITESPACE_FREE",
                }
                key = (
                    len(response),
                    abs(score - target),
                    len(selected_tokens),
                    extra,
                    response,
                )
                if best is None or key < best[0]:
                    best = (key, record)
            elif score < target - TOLERANCE_PERCENT:
                break

    if best is None:
        raise PublicFamilyCompilerError("NO_KEYWORD_WITNESS_FOUND")
    return best[1]


def construct_from_public_ratio_prompt(prompt: str) -> dict:
    parsed = parse_public_ratio_prompt(prompt)
    if parsed.keyword is not None:
        if parsed.keyword_sentence is None:
            raise AssertionError("INTERNAL_KEYWORD_SENTENCE_MISSING")
        if parsed.consonant_cluster_required:
            raise PublicFamilyCompilerError("UNPROVED_KEYWORD_PLUS_CONSONANT_COMPOSITION")
        witness = _construct_keyword(
            parsed.normalized_reference,
            parsed.percentage,
            parsed.keyword,
            parsed.keyword_sentence,
        )
    else:
        witness = _construct_ordinary(
            parsed.normalized_reference,
            parsed.percentage,
            consonant_cluster_required=parsed.consonant_cluster_required,
        )

    response = witness["response"]
    if any(ch.isspace() for ch in response):
        raise AssertionError("INTERNAL_WHITESPACE_CONSTRUCTION_BUG")
    score = overlap_percent(response, parsed.normalized_reference)
    if not _strictly_in_band(score, parsed.percentage):
        raise AssertionError("INTERNAL_OUT_OF_BAND_CONSTRUCTION_BUG")
    if parsed.consonant_cluster_required and not consonant_cluster_pass(response):
        raise AssertionError("INTERNAL_CONSONANT_CONSTRUCTION_BUG")

    return {
        "schema": SCHEMA,
        "scope": PUBLIC_SCOPE,
        "visible_prompt_only": True,
        "exact_raw_reference_required": False,
        "normalized_reference_recovered_from_visible_prompt": True,
        "requested_percent": parsed.percentage,
        "strict_interior_band": True,
        "whitespace_free": True,
        "keyword_companion": parsed.keyword is not None,
        "keyword_sentence": parsed.keyword_sentence,
        "consonant_cluster_companion": parsed.consonant_cluster_required,
        **witness,
    }
