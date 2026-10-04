"""Zero-learned proof-carrying extractive summarizer.

This module owns one narrow semantic capability: compress a multi-sentence source
by selecting a salient subset of source sentences. Every emitted sentence is a
verbatim span of the source. The module therefore cannot invent a new lexical
claim in its output. It does not claim abstractive summarization, entailment
beyond verbatim extraction, or frontier-model parity.

The selection rule is deterministic and dependency-free:
- split only at visible sentence-final punctuation;
- score sentences from source-local content-word frequency plus a small
  position prior;
- select a bounded proper subset;
- emit selected source spans in original order with a machine-checkable proof.
"""
from __future__ import annotations

from hashlib import sha256
from math import ceil, sqrt
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_ZERO_LEARNED_EXTRACTIVE_SUMMARY_V1"
_STOP = {
    "a","an","and","are","as","at","be","been","being","but","by","for","from",
    "had","has","have","he","her","hers","him","his","i","if","in","into","is",
    "it","its","of","on","or","our","ours","she","so","that","the","their",
    "theirs","them","they","this","those","to","was","we","were","what","when",
    "where","which","who","will","with","you","your","yours",
}
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)?")
_CLOSERS = set('"\'”’)]}')


class ExtractiveSummaryError(ValueError):
    pass


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    """Return non-empty sentence-like spans without changing source bytes."""
    spans: list[tuple[int, int]] = []
    start = 0
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        if ch in ".!?":
            end = i + 1
            while end < n and text[end] in ".!?":
                end += 1
            while end < n and text[end] in _CLOSERS:
                end += 1
            if end == n or text[end].isspace():
                a = start
                while a < end and text[a].isspace():
                    a += 1
                b = end
                while b > a and text[b - 1].isspace():
                    b -= 1
                if a < b:
                    spans.append((a, b))
                start = end
                while start < n and text[start].isspace():
                    start += 1
                i = start
                continue
        i += 1

    a = start
    while a < n and text[a].isspace():
        a += 1
    b = n
    while b > a and text[b - 1].isspace():
        b -= 1
    if a < b:
        spans.append((a, b))
    return spans


def _tokens(text: str) -> list[str]:
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


def summarize(
    text: Any,
    *,
    compression_ratio: float = 0.35,
    max_sentences: int = 3,
    min_sentence_words: int = 3,
) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise ExtractiveSummaryError("TEXT_INVALID")
    if not isinstance(compression_ratio, (int, float)) or isinstance(compression_ratio, bool):
        raise ExtractiveSummaryError("COMPRESSION_RATIO_INVALID")
    compression_ratio = float(compression_ratio)
    if not 0 < compression_ratio < 1:
        raise ExtractiveSummaryError("COMPRESSION_RATIO_OUT_OF_RANGE")
    if not isinstance(max_sentences, int) or isinstance(max_sentences, bool) or max_sentences < 1:
        raise ExtractiveSummaryError("MAX_SENTENCES_INVALID")
    if not isinstance(min_sentence_words, int) or isinstance(min_sentence_words, bool) or min_sentence_words < 1:
        raise ExtractiveSummaryError("MIN_SENTENCE_WORDS_INVALID")

    raw_spans = _sentence_spans(text)
    eligible: list[dict[str, Any]] = []
    for index, (start, end) in enumerate(raw_spans):
        sentence = text[start:end]
        toks = _tokens(sentence)
        if len(toks) >= min_sentence_words:
            eligible.append({
                "source_sentence_index": index,
                "start": start,
                "end": end,
                "text": sentence,
                "tokens": toks,
            })

    if len(eligible) < 2:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "INSUFFICIENT_MULTI_SENTENCE_SOURCE",
            "response": None,
            "source_sha256": _sha(text),
            "persistent_learned_bytes": 0,
            "external_frontier_model_calls": 0,
            "external_learned_capability_calls": 0,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
        }

    freq: dict[str, int] = {}
    for row in eligible:
        for token in row["tokens"]:
            if token not in _STOP and len(token) >= 2:
                freq[token] = freq.get(token, 0) + 1

    n = len(eligible)
    desired = max(1, ceil(n * compression_ratio))
    k = min(max_sentences, desired, n - 1)

    ranked: list[tuple[float, int]] = []
    for pos, row in enumerate(eligible):
        content = [t for t in row["tokens"] if t not in _STOP and len(t) >= 2]
        unique = set(content)
        lexical = sum(freq.get(t, 0) for t in unique)
        density = lexical / sqrt(max(1, len(row["tokens"])))
        position = 0.20 if pos == 0 else (0.08 if pos == n - 1 else 0.0)
        ranked.append((density + position, pos))

    chosen_positions = sorted(
        pos for _, pos in sorted(ranked, key=lambda x: (-x[0], x[1]))[:k]
    )
    chosen = [eligible[pos] for pos in chosen_positions]
    response = " ".join(row["text"] for row in chosen)

    if not response or len(response.encode("utf-8")) >= len(text.encode("utf-8")):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "NO_STRICT_COMPRESSION",
            "response": None,
            "source_sha256": _sha(text),
            "persistent_learned_bytes": 0,
            "external_frontier_model_calls": 0,
            "external_learned_capability_calls": 0,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
        }

    proof = []
    for out_index, row in enumerate(chosen):
        span = text[row["start"]:row["end"]]
        if span != row["text"]:
            raise ExtractiveSummaryError("INTERNAL_SOURCE_SPAN_MISMATCH")
        proof.append({
            "output_sentence_index": out_index,
            "source_sentence_index": row["source_sentence_index"],
            "source_start": row["start"],
            "source_end": row["end"],
            "source_span_sha256": _sha(span),
            "source_span": span,
        })

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "response": response,
        "source_sha256": _sha(text),
        "source_sentence_count": len(raw_spans),
        "eligible_sentence_count": n,
        "selected_sentence_count": len(chosen),
        "compression_ratio_bytes": len(response.encode("utf-8")) / len(text.encode("utf-8")),
        "proof": proof,
        "proof_contract": "OUTPUT_EQUALS_SOURCE_VERBATIM_SENTENCE_SUBSET_IN_ORIGINAL_ORDER",
        "all_output_sentences_verbatim_source_spans": True,
        "new_lexical_claim_generation": False,
        "persistent_learned_bytes": 0,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "incremental_spend_usd": 0,
        "terminal_cases_used": 0,
        "terminal_authority": False,
        "hard_nonclaim": (
            "VERBATIM_EXTRACTIVE_FAITHFULNESS_DOES_NOT_PROVE_ABSTRACTIVE_QUALITY_"
            "COVERAGE_OR_OPUS_5_5_PARITY"
        ),
    }
