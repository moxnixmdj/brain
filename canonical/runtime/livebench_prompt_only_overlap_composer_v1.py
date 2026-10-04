from __future__ import annotations

import re

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_PROMPT_ONLY_OVERLAP_COMPOSER_V1"
TOLERANCE_PERCENT = 2.0

_OVERLAP_RE = re.compile(
    r"Maintain a trigram overlap of (\d+(?:\.\d+)?)% \(±2%\) with the provided reference text\.",
    flags=re.IGNORECASE,
)
_KEYWORD_RE = re.compile(
    r'The response must include keyword\s+["“]?([A-Za-z0-9_-]+)["”]?\s+in the\s+(\d+)-(?:st|nd|rd|th)\s+sentence\.',
    flags=re.IGNORECASE,
)
_CONSONANT_TEXT = (
    "Ensure each word in your response has at least one consonant cluster "
    "(two or more consonants together)."
)
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\ufeff]")
_CHUNK_RE = re.compile(r"[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*")
_CONSONANT_CLUSTER_RE = re.compile(r"[bcdfghjklmnpqrstvwxyz]{2}", flags=re.IGNORECASE)


class PromptOnlyOverlapError(ValueError):
    pass


def normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def char_trigrams(value: str) -> set[str]:
    value = str(value)
    return {value[i : i + 3] for i in range(max(0, len(value) - 2))}


def _is_private_use(ch: str) -> bool:
    cp = ord(ch)
    return 0xE000 <= cp <= 0xF8FF


def parse_supported_prompt(prompt: str) -> dict:
    """Recover only the public ratio-overlap subgrammar handled by this composer.

    This parser deliberately recognizes exactly three public instruction surfaces:
    ratio:overlap, sentence:keyword, and words:consonants. It does not claim that
    every IFBench instruction combination is segmentable here.
    """
    text = str(prompt or "")
    matches = list(_OVERLAP_RE.finditer(text))
    if len(matches) != 1:
        raise PromptOnlyOverlapError("EXACTLY_ONE_RATIO_OVERLAP_DESCRIPTION_REQUIRED")
    percentage = float(matches[0].group(1))
    text = _OVERLAP_RE.sub(" ", text)

    keyword_matches = list(_KEYWORD_RE.finditer(text))
    if len(keyword_matches) > 1:
        raise PromptOnlyOverlapError("MULTIPLE_KEYWORD_SENTENCE_CONSTRAINTS_UNSUPPORTED")
    keyword = None
    keyword_sentence = None
    if keyword_matches:
        keyword = keyword_matches[0].group(1)
        keyword_sentence = int(keyword_matches[0].group(2))
        if keyword_sentence < 1:
            raise PromptOnlyOverlapError("KEYWORD_SENTENCE_OUT_OF_RANGE")
        text = _KEYWORD_RE.sub(" ", text)

    consonant_cluster = _CONSONANT_TEXT.lower() in text.lower()
    if consonant_cluster:
        text = re.sub(re.escape(_CONSONANT_TEXT), " ", text, flags=re.IGNORECASE)

    # Public row 3 contains a zero-width separator adjacent to the injected
    # constraint. It carries no reference-text semantics and must not poison
    # the recovered normalized base request.
    text = _ZERO_WIDTH_RE.sub("", text)
    surface = normalize_ws(text)
    if len(surface) < 3:
        raise PromptOnlyOverlapError("RECOVERED_REFERENCE_SURFACE_TOO_SHORT")

    return {
        "schema": SCHEMA,
        "normalized_reference_surface": surface,
        "percentage": percentage,
        "keyword": keyword,
        "keyword_sentence": keyword_sentence,
        "consonant_cluster_required": consonant_cluster,
        "supported_auxiliary_constraint_count": int(keyword is not None) + int(consonant_cluster),
    }


def _chunks(surface: str) -> list[str]:
    unique = sorted(
        set(x for x in _CHUNK_RE.findall(surface) if len(x) >= 3),
        key=lambda x: (-len(char_trigrams(x)), -len(x), x),
    )
    return unique


def _has_consonant_cluster(value: str) -> bool:
    return bool(_CONSONANT_CLUSTER_RE.search(value))


def _novel_private_use_chars(forbidden_surface: str, count: int) -> str:
    if count < 0:
        raise PromptOnlyOverlapError("NEGATIVE_PRIVATE_USE_COUNT")
    out: list[str] = []
    forbidden = set(forbidden_surface)
    for cp in range(0xE000, 0xF8FF + 1):
        ch = chr(cp)
        if ch in forbidden:
            continue
        out.append(ch)
        if len(out) == count:
            return "".join(out)
    raise PromptOnlyOverlapError("INSUFFICIENT_PRIVATE_USE_ALPHABET")


def robust_overlap_percent(response: str, normalized_reference_surface: str) -> float:
    """Exact score for the whitespace-variant equivalence class.

    Every generated response is whitespace-free. Any trigram containing one of
    our private-use separators is absent from the public normalized surface by
    construction. Every remaining trigram contains no whitespace, so its
    membership is invariant under whitespace-run changes in the raw reference.
    """
    grams = char_trigrams(response)
    if not grams:
        raise PromptOnlyOverlapError("RESPONSE_TOO_SHORT_FOR_TRIGRAMS")
    ref = char_trigrams(normalized_reference_surface)
    hit = 0
    for gram in grams:
        if any(_is_private_use(ch) for ch in gram):
            continue
        if any(ch.isspace() for ch in gram):
            raise PromptOnlyOverlapError("INTERNAL_WHITESPACE_TRIGRAM_CONSTRUCTION_BUG")
        if gram in ref:
            hit += 1
    return 100.0 * hit / len(grams)


def construct_from_prompt(
    prompt: str,
    *,
    tolerance_percent: float = TOLERANCE_PERCENT,
    max_seed_chunks: int = 20,
    max_filler_chars: int = 512,
) -> dict:
    parsed = parse_supported_prompt(prompt)
    surface = parsed["normalized_reference_surface"]
    percentage = float(parsed["percentage"])
    keyword = parsed["keyword"]
    keyword_sentence = parsed["keyword_sentence"]
    consonant_required = bool(parsed["consonant_cluster_required"])

    if not 0.0 <= percentage <= 100.0:
        raise PromptOnlyOverlapError("PERCENTAGE_OUT_OF_RANGE")
    if not 0.0 <= tolerance_percent <= 100.0:
        raise PromptOnlyOverlapError("TOLERANCE_OUT_OF_RANGE")
    if max_seed_chunks < 1 or max_seed_chunks > 128:
        raise PromptOnlyOverlapError("MAX_SEED_CHUNKS_OUT_OF_RANGE")
    if max_filler_chars < 0 or max_filler_chars > 4096:
        raise PromptOnlyOverlapError("MAX_FILLER_OUT_OF_RANGE")

    chunks = _chunks(surface)
    if consonant_required:
        chunks = [x for x in chunks if _has_consonant_cluster(x)] + [
            x for x in chunks if not _has_consonant_cluster(x)
        ]
    if not chunks:
        raise PromptOnlyOverlapError("NO_REFERENCE_CHUNKS")

    # Reserve enough absent symbols for seed separators, sentence scaffolding,
    # and the largest filler search. All are unique so every trigram containing
    # them is a distinct guaranteed miss against the reference.
    reserve = max_filler_chars + 2 * (keyword_sentence or 0) + max_seed_chunks + 32
    alphabet = _novel_private_use_chars(surface + (keyword or ""), reserve)

    best: dict | None = None
    for seed_count in range(1, min(max_seed_chunks, len(chunks)) + 1):
        cursor = 0
        seed_parts: list[str] = []
        for index in range(seed_count):
            if index:
                seed_parts.append(alphabet[cursor])
                cursor += 1
            seed_parts.append(chunks[index])
        seed = "".join(seed_parts)
        if consonant_required and not _has_consonant_cluster(seed):
            continue

        scaffold_parts: list[str] = []
        if keyword is not None:
            assert keyword_sentence is not None
            for sentence_index in range(1, keyword_sentence + 1):
                scaffold_parts.append(alphabet[cursor])
                cursor += 1
                if sentence_index == keyword_sentence:
                    scaffold_parts.append(keyword)
                    scaffold_parts.append(alphabet[cursor])
                    cursor += 1
                scaffold_parts.append(".")
        scaffold = "".join(scaffold_parts)
        base = seed + scaffold

        for filler_len in range(max_filler_chars + 1):
            response = base + alphabet[cursor : cursor + filler_len]
            if any(ch.isspace() for ch in response):
                raise PromptOnlyOverlapError("INTERNAL_WHITESPACE_CONSTRUCTION_BUG")
            score = robust_overlap_percent(response, surface)
            error = abs(score - percentage)
            inside = error <= tolerance_percent + 1e-12
            record = {
                "schema": SCHEMA,
                "status": "PASS" if inside else "SEARCHING",
                "response": response,
                "requested_percent": percentage,
                "score_percent": score,
                "absolute_error_percent": error,
                "within_tolerance": inside,
                "seed_chunk_count": seed_count,
                "filler_len": filler_len,
                "response_len": len(response),
                "normalized_reference_surface": surface,
                "keyword": keyword,
                "keyword_sentence": keyword_sentence,
                "consonant_cluster_required": consonant_required,
                "raw_reference_text_required": False,
                "hidden_kwargs_required": False,
                "whitespace_free_response": True,
            }
            key = (0 if inside else 1, len(response), error, seed_count, filler_len)
            if best is None or key < best["_key"]:
                best = dict(record)
                best["_key"] = key

    if best is None or not best["within_tolerance"]:
        raise PromptOnlyOverlapError("NO_PROMPT_ONLY_WITNESS_FOUND")
    best.pop("_key", None)
    return best


def run(args: dict, root=None) -> dict:
    prompt = str((args or {}).get("prompt") or (args or {}).get("instruction") or "")
    return construct_from_prompt(prompt)
