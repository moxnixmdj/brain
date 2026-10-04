#!/usr/bin/env python3
"""Deterministic local semantic seed producer for the LiveBench Root1 repair lane.

This module deliberately does not use a model, network, benchmark metadata, or
terminal-case-specific rules. It creates conservative semantic seeds from the
model-visible prompt only:

* summarize: extractive frequency/position ranking, preserving source sentences;
* simplify: conservative meaning-preserving phrase simplification and clause
  boundary cleanup;
* paraphrase/rewrite: conservative lexical/discourse rewrites while retaining
  nearly all source content;
* story/screenplay/narrative: prompt-grounded narrative scaffold containing the
  premise verbatim plus generic causal structure.

It is not claimed to match Opus-quality prose. Its purpose is narrower and
load-bearing: establish a precommitted, zero-cost, auditable semantic producer
that can be composed with verified structural-constraint postprocessors without
post-prompt capability acquisition.
"""
from __future__ import annotations

from collections import Counter
import math
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LOCAL_SEMANTIC_TEXT_CORE_V1"

_INTENT_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("summarize", (r"\bsummari[sz]e\b", r"\bsummary\b", r"\bcondense\b")),
    ("simplify", (r"\bsimplif(?:y|ied|ication)\b", r"\bmake (?:it|this|the text) easier\b")),
    ("paraphrase", (r"\bparaphrase\b", r"\brephrase\b", r"\brewrite\b")),
    (
        "story",
        (
            r"\bstory\b",
            r"\bscreenplay\b",
            r"\bnarrative\b",
            r"\bfiction(?:al)?\b",
            r"\btale\b",
        ),
    ),
)

_HIGH_CONFIDENCE_CONSTRAINT_CUES = (
    "the response must ",
    "your response must ",
    "the answer must ",
    "your answer must ",
    "maintain a trigram overlap",
    "ensure each word ",
    "ensure every word ",
    "the response should include keyword",
    "the response must include keyword",
    "include keyword ",
    "include exactly ",
    "use exactly ",
    "use at least ",
    "use at most ",
    "write each word on a new line",
    "nest parentheses ",
    "include quotes within quotes",
    "use every standard punctuation mark",
)

_STOPWORDS = {
    "a","an","and","are","as","at","be","because","been","being","but","by",
    "can","could","did","do","does","for","from","had","has","have","he","her",
    "hers","him","his","i","if","in","into","is","it","its","me","more","most",
    "my","no","not","of","on","or","our","ours","she","so","some","such","than",
    "that","the","their","theirs","them","then","there","these","they","this",
    "those","to","too","up","us","very","was","we","were","what","when","where",
    "which","while","who","why","will","with","would","you","your",
}

_SAFE_SIMPLIFICATIONS: tuple[tuple[str, str], ...] = (
    ("due to the fact that", "because"),
    ("at this point in time", "now"),
    ("in order to", "to"),
    ("has the ability to", "can"),
    ("have the ability to", "can"),
    ("a large number of", "many"),
    ("prior to", "before"),
    ("subsequent to", "after"),
    ("approximately", "about"),
    ("utilization", "use"),
    ("utilize", "use"),
    ("utilizes", "uses"),
    ("utilized", "used"),
    ("commence", "start"),
    ("commences", "starts"),
    ("commenced", "started"),
    ("terminate", "end"),
    ("terminates", "ends"),
    ("terminated", "ended"),
    ("facilitate", "help"),
    ("facilitates", "helps"),
    ("facilitated", "helped"),
    ("demonstrate", "show"),
    ("demonstrates", "shows"),
    ("demonstrated", "showed"),
    ("subsequent", "next"),
    ("numerous", "many"),
    ("additional", "more"),
)

_SAFE_PARAPHRASE_REWRITES: tuple[tuple[str, str], ...] = (
    ("furthermore", "also"),
    ("moreover", "also"),
    ("in addition", "also"),
    ("nevertheless", "still"),
    ("nonetheless", "still"),
    ("therefore", "so"),
    ("consequently", "as a result"),
    ("for example", "for instance"),
    ("in contrast", "by contrast"),
    ("in particular", "especially"),
    ("take into account", "consider"),
    ("with regard to", "about"),
    ("in the event that", "if"),
)

_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)?")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])(?:[\"')\]]*)\s+|\n+")


def _normalize_space(text: str) -> str:
    return re.sub(r"[ \t]+", " ", str(text or "")).strip()


def _sentences(text: str) -> list[str]:
    text = _normalize_space(text.replace("\r", "\n"))
    if not text:
        return []
    parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(text) if p.strip()]
    return parts if parts else [text]


def _content_tokens(text: str) -> list[str]:
    return [
        t.lower()
        for t in _WORD_RE.findall(text)
        if len(t) > 2 and t.lower() not in _STOPWORDS
    ]


def _overlap(source: str, candidate: str) -> dict[str, float]:
    s = set(_content_tokens(source))
    c = set(_content_tokens(candidate))
    if not s and not c:
        return {"source_coverage": 1.0, "jaccard": 1.0}
    if not s:
        return {"source_coverage": 0.0, "jaccard": 0.0}
    inter = len(s & c)
    union = len(s | c) or 1
    return {
        "source_coverage": inter / len(s),
        "jaccard": inter / union,
    }


def classify_intent(prompt: str) -> str | None:
    text = str(prompt or "").lower()
    for intent, patterns in _INTENT_PATTERNS:
        if any(re.search(p, text) for p in patterns):
            return intent
    return None


def _is_constraint_sentence(sentence: str) -> bool:
    low = _normalize_space(sentence).lower()
    return any(cue in low for cue in _HIGH_CONFIDENCE_CONSTRAINT_CUES)


def _strip_constraint_tail(text: str) -> str:
    """Remove only high-confidence grader-style instruction sentences.

    The removal is intentionally conservative. A sentence is removable only
    after at least one semantic sentence has been retained.
    """
    kept: list[str] = []
    for sentence in _sentences(text):
        if kept and _is_constraint_sentence(sentence):
            continue
        kept.append(sentence)
    return " ".join(kept).strip()


def _strip_leading_directive(text: str, intent: str) -> str:
    text = text.strip()
    patterns = {
        "summarize": (
            r"^\s*(?:please\s+)?(?:summari[sz]e|condense)\s+"
            r"(?:(?:the\s+)?(?:following|text|passage|paragraph|content)\s*)?[:\-]?\s*",
        ),
        "simplify": (
            r"^\s*(?:please\s+)?(?:simplify|make\s+(?:this|the following|the text)\s+"
            r"(?:simpler|easier(?:\s+to\s+understand)?))\s*[:\-]?\s*",
        ),
        "paraphrase": (
            r"^\s*(?:please\s+)?(?:paraphrase|rephrase|rewrite(?:\s+it\s+better)?)\s*"
            r"(?:(?:the\s+)?(?:following|text|passage|paragraph|content)\s*)?[:\-]?\s*",
        ),
        "story": (
            r"^\s*(?:please\s+)?(?:write|create|generate|compose)\s+"
            r"(?:a\s+|an\s+)?(?:descriptive\s+|believable\s+|fictional\s+|imaginative\s+|"
            r"sci[\s-]*fi\s+|detailed\s+)*(?:story|screenplay|narrative|tale)\s*"
            r"(?:about|where|in\s+which|with|of|:)?\s*",
        ),
    }
    pattern = patterns.get(intent)
    if pattern:
        candidate = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE)
        if candidate.strip():
            text = candidate.strip()
    return text


def extract_semantic_source(prompt: str, intent: str | None = None) -> str:
    prompt = str(prompt or "").strip()
    if not prompt:
        return ""
    intent = intent or classify_intent(prompt)
    text = _strip_constraint_tail(prompt)
    if intent:
        text = _strip_leading_directive(text, intent)
    return _normalize_space(text)


def _preserve_case(source: str, replacement: str) -> str:
    if source.isupper():
        return replacement.upper()
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def _replace_phrase(text: str, old: str, new: str) -> tuple[str, int]:
    pattern = re.compile(r"(?<!\w)" + re.escape(old) + r"(?!\w)", re.IGNORECASE)
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return _preserve_case(match.group(0), new)

    return pattern.sub(repl, text), count


def summarize(source: str) -> tuple[str, dict[str, Any]]:
    sents = _sentences(source)
    if not sents:
        return "", {"method": "EXTRACTIVE_FREQUENCY_POSITION", "selected": []}
    if len(sents) == 1:
        return sents[0], {"method": "EXTRACTIVE_FREQUENCY_POSITION", "selected": [0]}

    frequencies = Counter(_content_tokens(source))
    target = max(1, min(4, math.ceil(len(sents) * 0.35)))
    scored: list[tuple[float, int]] = []
    for i, sentence in enumerate(sents):
        tokens = _content_tokens(sentence)
        if not tokens:
            lexical = 0.0
        else:
            lexical = sum(frequencies[t] for t in tokens) / math.sqrt(len(tokens))
        position_bonus = 0.35 / (i + 1)
        scored.append((lexical + position_bonus, i))
    selected = sorted(i for _, i in sorted(scored, reverse=True)[:target])
    seed = " ".join(sents[i] for i in selected)
    return seed, {
        "method": "EXTRACTIVE_FREQUENCY_POSITION",
        "selected": selected,
        "sentence_count": len(sents),
    }


def simplify(source: str) -> tuple[str, dict[str, Any]]:
    candidate = source
    changes = 0
    for old, new in _SAFE_SIMPLIFICATIONS:
        candidate, n = _replace_phrase(candidate, old, new)
        changes += n

    # Semicolons often connect independent clauses. A period is a conservative
    # readability transform that preserves both clauses byte-for-byte otherwise.
    semicolons = candidate.count(";")
    if semicolons:
        candidate = re.sub(r";\s*", ". ", candidate)
        changes += semicolons

    # Collapse accidental complexity in punctuation without deleting lexical facts.
    candidate = re.sub(r"\s+([,.;:!?])", r"\1", candidate)
    candidate = _normalize_space(candidate)
    return candidate, {
        "method": "CONSERVATIVE_RULE_SIMPLIFICATION",
        "rewrite_count": changes,
        "source_word_count": len(_WORD_RE.findall(source)),
        "seed_word_count": len(_WORD_RE.findall(candidate)),
    }


def paraphrase(source: str) -> tuple[str, dict[str, Any]]:
    candidate = source
    changes = 0
    for old, new in _SAFE_PARAPHRASE_REWRITES:
        candidate, n = _replace_phrase(candidate, old, new)
        changes += n

    # Conservative causal-clause rotation. Both clauses are retained verbatim.
    # Example: "X because Y." -> "Because Y, X."
    rotated: list[str] = []
    rotations = 0
    for sentence in _sentences(candidate):
        m = re.match(
            r"^(.{8,}?)\s+because\s+(.{8,}?)([.!?])?$",
            sentence,
            flags=re.IGNORECASE,
        )
        if m and "," not in m.group(1):
            left = m.group(1).strip()
            right = m.group(2).strip()
            punct = m.group(3) or "."
            sentence = "Because " + right[:1].lower() + right[1:] + ", " + left[:1].lower() + left[1:] + punct
            rotations += 1
        rotated.append(sentence)
    candidate = " ".join(rotated)
    changes += rotations

    # If no safe lexical/syntactic rewrite fired, mark the reformulation
    # explicitly instead of inventing synonyms. This preserves every source fact.
    if changes == 0 and candidate:
        candidate = "In other words, " + candidate[:1].lower() + candidate[1:]
        changes = 1

    return _normalize_space(candidate), {
        "method": "CONSERVATIVE_SEMANTIC_REFORMULATION",
        "rewrite_count": changes,
        "clause_rotations": rotations,
    }


def story(source: str) -> tuple[str, dict[str, Any]]:
    premise = _normalize_space(source)
    content = _content_tokens(premise)
    if len(content) < 5:
        return "", {
            "method": "PROMPT_GROUNDED_NARRATIVE_SCAFFOLD",
            "error": "PREMISE_TOO_THIN",
        }

    # The premise is retained verbatim. The added sentences encode narrative
    # structure but introduce no concrete external-world facts.
    seed = (
        "The story opens with this premise: "
        + premise
        + " At first, the situation seems stable enough for the people involved to act on it. "
        + "Then a complication changes what they can safely do. "
        + "Their next choices follow from the conflict already described in the premise. "
        + "The pressure builds until one decision becomes unavoidable. "
        + "After that decision, its consequences provide the resolution."
    )
    return seed, {
        "method": "PROMPT_GROUNDED_NARRATIVE_SCAFFOLD",
        "premise_verbatim_preserved": premise in seed,
        "narrative_stages": 5,
    }


def produce(prompt: str) -> dict[str, Any]:
    prompt = str(prompt or "")
    intent = classify_intent(prompt)
    if intent is None:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "UNRECOGNIZED_SEMANTIC_INTENT",
            "model_dependency_count": 0,
            "network_used": False,
            "incremental_spend_usd": 0,
        }

    source = extract_semantic_source(prompt, intent)
    if len(_content_tokens(source)) < 3:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "intent": intent,
            "error": "SEMANTIC_SOURCE_TOO_THIN",
            "model_dependency_count": 0,
            "network_used": False,
            "incremental_spend_usd": 0,
        }

    if intent == "summarize":
        seed, evidence = summarize(source)
        grounding_class = "EXTRACTIVE_SOURCE_SENTENCE_SUBSET"
    elif intent == "simplify":
        seed, evidence = simplify(source)
        grounding_class = "CONSERVATIVE_SOURCE_REWRITE"
    elif intent == "paraphrase":
        seed, evidence = paraphrase(source)
        grounding_class = "CONSERVATIVE_SOURCE_REFORMULATION"
    elif intent == "story":
        seed, evidence = story(source)
        grounding_class = "PROMPT_PREMISE_VERBATIM_GROUNDED_NARRATIVE"
    else:
        raise AssertionError("unreachable intent")

    if not seed:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "intent": intent,
            "error": evidence.get("error", "EMPTY_SEMANTIC_SEED"),
            "model_dependency_count": 0,
            "network_used": False,
            "incremental_spend_usd": 0,
        }

    overlap = _overlap(source, seed)
    # Guard against accidental semantic detachment. Story adds generic scaffolding
    # but keeps the entire premise; transformations retain most source content.
    minimum_coverage = 0.45 if intent == "summarize" else 0.65
    if overlap["source_coverage"] < minimum_coverage:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "intent": intent,
            "error": "GROUNDING_COVERAGE_BELOW_BOUND",
            "grounding": overlap,
            "model_dependency_count": 0,
            "network_used": False,
            "incremental_spend_usd": 0,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "intent": intent,
        "source": source,
        "seed": seed,
        "grounding_class": grounding_class,
        "grounding": overlap,
        "evidence": evidence,
        "model_dependency_count": 0,
        "learned_parameter_count": 0,
        "network_used": False,
        "external_tools_used": [],
        "incremental_spend_usd": 0,
        "terminal_cases_used": 0,
        "hard_nonclaim": (
            "THIS_PROVES_A_LOCAL_AUDITABLE_SEMANTIC_SEED_ROUTE_FOR_SUPPORTED_"
            "TRANSFORMATIONS; IT_DOES_NOT_PROVE_OPUS_5_5_QUALITY_OR_LIVEBENCH_PASS"
        ),
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return produce(str(args.get("prompt") or args.get("instruction") or ""))
