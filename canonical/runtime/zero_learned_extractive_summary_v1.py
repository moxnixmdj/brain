"""Deterministic zero-learned extractive summarization.

The contract is deliberately narrow: select a bounded number of verbatim source
sentences using lexical centrality. Because the producer never invents sentence
content, factual faithfulness of emitted claims to the supplied source is
structural. This does not claim abstractive summarization or open-world semantic
understanding.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

SCHEMA = "PROJECT_BRAIN_ZERO_LEARNED_EXTRACTIVE_SUMMARY_V1"
_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?")
_SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)", re.DOTALL)
_STOP = frozenset({
    "a","an","and","are","as","at","be","been","being","but","by","can",
    "could","did","do","does","for","from","had","has","have","he","her",
    "hers","him","his","i","if","in","into","is","it","its","may","might",
    "more","most","no","not","of","on","or","our","ours","she","should",
    "so","some","such","than","that","the","their","theirs","them","they",
    "this","those","to","was","we","were","what","when","where","which",
    "while","who","will","with","would","you","your","yours",
})


def _sentences(text: str) -> list[str]:
    out: list[str] = []
    for match in _SENTENCE_RE.finditer(text):
        sentence = match.group(0).strip()
        if sentence:
            out.append(sentence)
    return out


def _tokens(sentence: str) -> set[str]:
    words = {m.group(0).lower() for m in _WORD_RE.finditer(sentence)}
    content = words - _STOP
    return content or words


def _centrality(sentence_tokens: list[set[str]]) -> list[float]:
    document_frequency = Counter(
        token for token_set in sentence_tokens for token in token_set
    )
    scores: list[float] = []
    for i, own in enumerate(sentence_tokens):
        if not own:
            scores.append(0.0)
            continue
        repeated_mass = sum(max(document_frequency[token] - 1, 0) for token in own)
        pair_mass = 0.0
        for j, other in enumerate(sentence_tokens):
            if i == j or not other:
                continue
            union = own | other
            if union:
                pair_mass += len(own & other) / len(union)
        density = (repeated_mass + pair_mass) / math.sqrt(max(len(own), 1))
        lead_tiebreak = 1e-9 / (i + 1)
        scores.append(density + lead_tiebreak)
    return scores


def summarize(text: Any, *, max_sentences: int = 2) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("TEXT_INVALID")
    if not isinstance(max_sentences, int) or isinstance(max_sentences, bool) or max_sentences < 1:
        raise ValueError("MAX_SENTENCES_INVALID")

    sentences = _sentences(text)
    base = {
        "schema": SCHEMA,
        "source_sentence_count": len(sentences),
        "persistent_learned_bytes": 0,
        "external_model_calls": 0,
        "network_calls": 0,
        "hard_nonclaim": "EXTRACTIVE_FAITHFULNESS_IS_NOT_ABSTRACTIVE_SUMMARIZATION_OR_OPEN_WORLD_LANGUAGE_UNDERSTANDING",
    }
    if len(sentences) <= max_sentences:
        return {
            **base,
            "status": "ABSTAIN_NOT_COMPRESSIBLE",
            "summary": "",
            "summary_sentences": [],
            "summary_sentence_count": 0,
            "selected_indices": [],
            "extractive_faithfulness_verified": True,
        }

    token_sets = [_tokens(sentence) for sentence in sentences]
    scores = _centrality(token_sets)
    ranked = sorted(range(len(sentences)), key=lambda i: (-scores[i], i))
    selected = sorted(ranked[:max_sentences])
    selected_sentences = [sentences[i] for i in selected]

    if any(sentence not in text for sentence in selected_sentences):
        raise RuntimeError("EXTRACTIVE_INVARIANT_BROKEN")

    return {
        **base,
        "status": "SUMMARY_READY",
        "summary": " ".join(selected_sentences),
        "summary_sentences": selected_sentences,
        "summary_sentence_count": len(selected_sentences),
        "selected_indices": selected,
        "selection_scores": [scores[i] for i in selected],
        "extractive_faithfulness_verified": True,
    }
