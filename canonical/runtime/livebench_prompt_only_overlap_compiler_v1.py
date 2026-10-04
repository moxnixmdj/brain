from __future__ import annotations

import re
from dataclasses import dataclass

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PROMPT_ONLY_OVERLAP_COMPILER_V1"
TOLERANCE = 2.0

_OVERLAP_RE = re.compile(
    r"Maintain a trigram overlap of\s*(\d+(?:\.\d+)?)%\s*\(±2%\)\s*with the provided reference text\.",
    re.I,
)
_KEYWORD_RE = re.compile(
    r'The response must include keyword\s+(?:"([^"]+)"|([^\s]+))\s+in the\s+(\d+)(?:-(?:st|nd|rd|th))?\s+sentence\.',
    re.I,
)
_CONSONANT_TEXT = (
    "Ensure each word in your response has at least one consonant cluster "
    "(two or more consonants together)."
)
_ASCII_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9'_-]{2,}")
_CONSONANT_CLUSTER_RE = re.compile(r"[bcdfghjklmnpqrstvwxyz]{2}", re.I)


class PromptOnlyOverlapError(ValueError):
    pass


def char_trigrams(value: str) -> set[str]:
    value = str(value)
    return {value[i : i + 3] for i in range(max(0, len(value) - 2))}


def overlap_percent(response: str, reference: str) -> float:
    grams = char_trigrams(response)
    if not grams:
        raise PromptOnlyOverlapError("RESPONSE_TOO_SHORT")
    return 100.0 * len(grams & char_trigrams(reference)) / len(grams)


@dataclass(frozen=True)
class ParsedPrompt:
    percentage: float
    residual: str
    keyword: str | None
    keyword_sentence: int | None
    consonant_cluster: bool


def parse_supported_prompt(prompt: str) -> ParsedPrompt:
    prompt = str(prompt or "")
    overlap = list(_OVERLAP_RE.finditer(prompt))
    if len(overlap) != 1:
        raise PromptOnlyOverlapError("EXACTLY_ONE_OVERLAP_INSTRUCTION_REQUIRED")
    percentage = float(overlap[0].group(1))

    keyword_matches = list(_KEYWORD_RE.finditer(prompt))
    if len(keyword_matches) > 1:
        raise PromptOnlyOverlapError("MULTIPLE_KEYWORD_SENTENCE_INSTRUCTIONS_UNSUPPORTED")
    keyword = keyword_sentence = None
    if keyword_matches:
        m = keyword_matches[0]
        keyword = m.group(1) or m.group(2)
        keyword_sentence = int(m.group(3))

    consonant_cluster = _CONSONANT_TEXT.lower() in prompt.lower()

    residual = _OVERLAP_RE.sub(" ", prompt)
    residual = _KEYWORD_RE.sub(" ", residual)
    residual = re.sub(re.escape(_CONSONANT_TEXT), " ", residual, flags=re.I)
    residual = re.sub(r"\s+", " ", residual).strip()

    if not _ASCII_TOKEN_RE.search(residual):
        raise PromptOnlyOverlapError("NO_PROMPT_VISIBLE_BASE_TOKEN")
    return ParsedPrompt(
        percentage=percentage,
        residual=residual,
        keyword=keyword,
        keyword_sentence=keyword_sentence,
        consonant_cluster=consonant_cluster,
    )


def _novel_chars(prompt: str, count: int, *, start: int = 0) -> str:
    if count < 0:
        raise PromptOnlyOverlapError("NEGATIVE_FILLER_COUNT")
    if count == 0:
        return ""
    out: list[str] = []
    seen = 0
    for cp in range(0xE000, 0xF8FF + 1):
        ch = chr(cp)
        if ch in prompt:
            continue
        if seen < start:
            seen += 1
            continue
        out.append(ch)
        if len(out) == count:
            return "".join(out)
    raise PromptOnlyOverlapError("INSUFFICIENT_PRIVATE_USE_FILLER")


def _tokens(residual: str, *, require_cluster: bool = False) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for token in _ASCII_TOKEN_RE.findall(residual):
        if require_cluster and not _CONSONANT_CLUSTER_RE.search(token):
            continue
        if token not in seen and char_trigrams(token):
            items.append(token)
            seen.add(token)
    items.sort(key=lambda x: (-len(char_trigrams(x)), -len(x), x))
    return items


def _score_known_from_residual(response: str, residual: str) -> float:
    """Exact under the public construction invariant used by this component.

    Any candidate trigram containing a private-use character is deliberately
    novel. Any remaining candidate trigram is counted as overlapping iff it is
    literally present in the prompt-visible residual carrier.
    """
    grams = char_trigrams(response)
    if not grams:
        raise PromptOnlyOverlapError("RESPONSE_TOO_SHORT")
    overlap = 0
    for gram in grams:
        if any(0xE000 <= ord(ch) <= 0xF8FF for ch in gram):
            continue
        if gram in residual:
            overlap += 1
    return 100.0 * overlap / len(grams)


def _within(score: float, target: float) -> bool:
    return target - TOLERANCE <= score <= target + TOLERANCE


def _simple_candidate(parsed: ParsedPrompt, prompt: str, max_filler: int) -> dict:
    tokens = _tokens(parsed.residual, require_cluster=parsed.consonant_cluster)
    if not tokens:
        raise PromptOnlyOverlapError("NO_SAFE_TOKEN_FOR_SUPPORTED_CONSTRAINTS")
    for token in tokens:
        for filler_len in range(max_filler + 1):
            response = token + _novel_chars(prompt, filler_len)
            score = _score_known_from_residual(response, parsed.residual)
            if _within(score, parsed.percentage):
                return {
                    "response": response,
                    "predicted_percent": score,
                    "selected_tokens": [token],
                    "filler_chars": filler_len,
                }
    raise PromptOnlyOverlapError("NO_SIMPLE_WITNESS")


def _sentence_keyword_candidate(parsed: ParsedPrompt, prompt: str, max_filler: int) -> dict:
    assert parsed.keyword is not None and parsed.keyword_sentence is not None
    if parsed.keyword_sentence < 1 or parsed.keyword_sentence > 256:
        raise PromptOnlyOverlapError("KEYWORD_SENTENCE_OUT_OF_RANGE")

    tokens = _tokens(parsed.residual, require_cluster=parsed.consonant_cluster)
    if not tokens:
        raise PromptOnlyOverlapError("NO_SAFE_TOKEN_FOR_SUPPORTED_CONSTRAINTS")

    max_tokens = min(len(tokens), 48)
    for token_count in range(1, max_tokens + 1):
        selected = tokens[:token_count]
        for extra in range(max_filler + 1):
            cursor = 0
            first = ""
            for token in selected:
                first += token + _novel_chars(prompt, 1, start=cursor)
                cursor += 1
            first += _novel_chars(prompt, extra, start=cursor)
            cursor += extra

            sentences = [first + "."]
            for _ in range(2, parsed.keyword_sentence):
                sentences.append(_novel_chars(prompt, 1, start=cursor) + ".")
                cursor += 1
            sentences.append(
                parsed.keyword + _novel_chars(prompt, 1, start=cursor) + "."
            )
            response = "".join(sentences)
            score = _score_known_from_residual(response, parsed.residual)
            if _within(score, parsed.percentage):
                return {
                    "response": response,
                    "predicted_percent": score,
                    "selected_tokens": selected,
                    "filler_chars": extra,
                    "sentence_count": parsed.keyword_sentence,
                    "keyword": parsed.keyword,
                }
    raise PromptOnlyOverlapError("NO_SENTENCE_KEYWORD_WITNESS")


def construct_from_prompt(prompt: str, *, max_filler: int = 512) -> dict:
    """Build a prompt-only witness for the currently supported overlap grammar.

    Scope is intentionally narrow and fail-closed. The algorithm never accepts
    reference_text or hidden kwargs. It uses only:
      * visible overlap percentage,
      * visible prompt carrier tokens,
      * visible sentence-keyword constraint when present,
      * visible consonant-cluster constraint when present.

    The proof object is component-level. It does not claim that no other
    benchmark constraint is present or satisfied.
    """
    if max_filler < 0 or max_filler > 4096:
        raise PromptOnlyOverlapError("MAX_FILLER_OUT_OF_RANGE")
    parsed = parse_supported_prompt(prompt)

    if parsed.keyword is not None:
        witness = _sentence_keyword_candidate(parsed, prompt, max_filler)
        route = "RATIO_PLUS_SENTENCE_KEYWORD"
    else:
        witness = _simple_candidate(parsed, prompt, max_filler)
        route = "RATIO_PLUS_CONSONANTS" if parsed.consonant_cluster else "RATIO_ONLY"

    return {
        "schema": SCHEMA,
        "status": "PASS_COMPONENT",
        "route": route,
        "requested_percent": parsed.percentage,
        "tolerance_percent": TOLERANCE,
        "residual_carrier": parsed.residual,
        "hidden_reference_required": False,
        "hidden_kwargs_required": False,
        "terminal_case_identity_required": False,
        "component_only": True,
        **witness,
    }
