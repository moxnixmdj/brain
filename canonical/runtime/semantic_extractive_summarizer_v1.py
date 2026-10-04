#!/usr/bin/env python3
"""Deterministic source-preserving extractive summarizer.

This is a bounded zero-learned semantic primitive. It selects verbatim sentence
spans from the supplied source text; it does not rewrite, paraphrase, invent, or
claim abstractive faithfulness.

The useful guarantee is deliberately narrow:
  every selected sentence is an exact substring of the input source.

That makes the primitive suitable as a fail-closed semantic seed candidate for
summarization tasks whose acceptance envelope permits extractive summaries.
"""
from __future__ import annotations

from collections import Counter
import math
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_SEMANTIC_EXTRACTIVE_SUMMARIZER_V1"

_STOP_WORDS = frozenset(
    """
    a an and are as at be been being but by for from had has have he her hers him
    his i if in into is it its me my of on or our ours she so than that the
    their theirs them then there they this to was we were what when where which
    who will with you your yours
    """.split()
)


class ExtractiveSummaryError(ValueError):
    pass


def _sentence_spans(text: str) -> list[tuple[int, int, str]]:
    value = str(text or "")
    spans: list[tuple[int, int, str]] = []
    start = 0
    boundary = re.compile(r'(?<=[.!?])(?:["\')\]]*)\s+|\n+')
    for match in boundary.finditer(value):
        raw = value[start:match.start()]
        if raw.strip():
            left = len(raw) - len(raw.lstrip())
            right = len(raw.rstrip())
            a = start + left
            b = start + right
            spans.append((a, b, value[a:b]))
        start = match.end()
    raw = value[start:]
    if raw.strip():
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        a = start + left
        b = start + right
        spans.append((a, b, value[a:b]))
    return spans


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9']+", text)]


def summarize(text: str, max_sentences: int = 2) -> dict[str, Any]:
    source = str(text or "")
    if not source.strip():
        raise ExtractiveSummaryError("TEXT_REQUIRED")
    try:
        limit = int(max_sentences)
    except Exception as exc:
        raise ExtractiveSummaryError("MAX_SENTENCES_NOT_INTEGER") from exc
    if limit < 1 or limit > 20:
        raise ExtractiveSummaryError("MAX_SENTENCES_OUT_OF_RANGE")

    spans = _sentence_spans(source)
    if not spans:
        raise ExtractiveSummaryError("NO_SENTENCE_SPANS")

    content_tokens = [
        [token for token in _tokens(sentence) if token not in _STOP_WORDS]
        for _, _, sentence in spans
    ]
    frequencies = Counter(
        token for sentence_tokens in content_tokens for token in sentence_tokens
    )

    scores: list[float] = []
    for index, sentence_tokens in enumerate(content_tokens):
        if sentence_tokens:
            lexical = sum(math.log1p(frequencies[token]) for token in sentence_tokens)
            lexical /= math.sqrt(len(sentence_tokens))
        else:
            lexical = 0.0
        # Small deterministic lead prior. It never overrides the source-preserving
        # guarantee; it only breaks/softens ranking ties.
        scores.append(lexical + 0.15 / (index + 1))

    if len(spans) <= limit:
        selected = list(range(len(spans)))
    else:
        ranked = sorted(
            range(len(spans)),
            key=lambda index: (-scores[index], index),
        )[:limit]
        selected = sorted(ranked)

    selected_spans = [
        {
            "sentence_index": index,
            "start": spans[index][0],
            "end": spans[index][1],
            "text": spans[index][2],
            "score": scores[index],
        }
        for index in selected
    ]
    summary = " ".join(item["text"] for item in selected_spans)

    # Internal proof check: every emitted lexical sentence must be an exact
    # source span at the declared coordinates.
    for item in selected_spans:
        if source[item["start"]:item["end"]] != item["text"]:
            raise AssertionError("SOURCE_SPAN_CERTIFICATE_BROKEN")

    return {
        "schema": SCHEMA,
        "status": "PASS__SOURCE_PRESERVING_EXTRACTIVE_SUMMARY",
        "summary": summary,
        "selected_spans": selected_spans,
        "source_sentence_count": len(spans),
        "selected_sentence_count": len(selected_spans),
        "compressed_sentence_count": max(0, len(spans) - len(selected_spans)),
        "persistent_learned_bytes": 0,
        "external_model_calls": 0,
        "network_used": False,
        "source_preservation_proved": True,
        "guarantee": (
            "EVERY_SELECTED_SENTENCE_IS_A_VERBATIM_SOURCE_SPAN__"
            "NO_ABSTRACTIVE_FAITHFULNESS_OR_GENERAL_SUMMARIZATION_QUALITY_CLAIM"
        ),
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return summarize(
        str(args.get("text") or args.get("source_text") or ""),
        args.get("max_sentences", 2),
    )


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--max-sentences", type=int, default=2)
    ns = parser.parse_args()
    print(json.dumps(summarize(ns.text, ns.max_sentences), indent=2, ensure_ascii=False))
