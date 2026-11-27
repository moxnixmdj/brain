#!/usr/bin/env python3
"""Bounded zero-learned semantic text seed core.

This is a deliberately small white-box language capability.  It covers four
semantic text families with different *mechanically auditable* contracts:

* paraphrase: only a small set of declared truth-preserving rewrites;
* simplify: contraction expansion plus clause splitting without lexical deletion;
* summarize: strict extractive sentence selection;
* story_generation: a fixed narrative scaffold over explicit structured facts.

It is not an open-world text generator and fails closed outside the proved
envelope.  No network, model, learned parameters, random search, or dynamic code
execution is used.
"""
from __future__ import annotations

from collections import Counter
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_WHITEBOX_SEMANTIC_TEXT_CORE_V1"
PERSISTENT_LEARNED_BYTES = 0

_WORD_RE = re.compile(r"[A-Za-z0-9_']+")
_SENTENCE_RE = re.compile(r"[^.!?]+[.!?](?:['\"])?|[^.!?]+$")
_STOP = {
    "a","an","and","are","as","at","be","been","but","by","for","from","had",
    "has","have","he","her","his","i","in","is","it","its","of","on","or","she",
    "that","the","their","they","this","to","was","were","will","with",
}


class SemanticSeedError(ValueError):
    pass


def _base(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "persistent_learned_bytes": PERSISTENT_LEARNED_BYTES,
        "external_frontier_model_calls": 0,
        "external_learned_capability_calls": 0,
        "network_used": False,
        "random_search": False,
        "dynamic_code_execution": False,
        "incremental_spend_usd": 0,
        "terminal_cases_used": 0,
        **extra,
    }


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        raise SemanticSeedError("TEXT_MUST_BE_STRING")
    value = " ".join(value.strip().split())
    if not value:
        raise SemanticSeedError("TEXT_REQUIRED")
    return value


def _singular_simple(word: str) -> str | None:
    """Intentionally narrow morphology for the bounded ALL_EVERY rewrite."""
    lower = word.lower()
    if not re.fullmatch(r"[A-Za-z]+", word):
        return None
    if lower.endswith("ies") and len(word) > 3:
        stem = word[:-3] + ("y" if word[-1].islower() else "Y")
        return stem
    if lower.endswith(("sses", "shes", "ches", "xes", "zes")):
        return word[:-2]
    if lower.endswith("s") and not lower.endswith(("ss", "us", "is")) and len(word) > 2:
        return word[:-1]
    return None


def _article_for(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def paraphrase(text: Any) -> dict[str, Any]:
    source = _clean_text(text)

    # Universal affirmative: All robins are birds. -> Every robin is a bird.
    m = re.fullmatch(r"All\s+([A-Za-z]+)\s+are\s+([A-Za-z]+)\.", source)
    if m:
        subject = _singular_simple(m.group(1))
        predicate = _singular_simple(m.group(2))
        if subject and predicate:
            response = f"Every {subject} is {_article_for(predicate)} {predicate}."
            return _base(
                "PASS",
                task_family="paraphrase",
                response=response,
                rule="ALL_EVERY",
                semantic_contract="BOUNDED_UNIVERSAL_AFFIRMATIVE_EQUIVALENCE",
                source_preservation="LOGICAL_FORM_EQUIVALENCE_BY_DECLARED_RULE",
            )

    # Conditional: If P, then Q. -> Q if P.
    m = re.fullmatch(r"If\s+(.+?),\s*then\s+(.+?)\.", source, flags=re.IGNORECASE)
    if m and "," not in m.group(1) and "," not in m.group(2):
        antecedent = m.group(1).strip()
        consequent = m.group(2).strip()
        response = consequent[:1].upper() + consequent[1:] + " if " + antecedent[:1].lower() + antecedent[1:] + "."
        return _base(
            "PASS",
            task_family="paraphrase",
            response=response,
            rule="IF_THEN",
            semantic_contract="BOUNDED_MATERIAL_CONDITIONAL_REORDERING",
            source_preservation="LOGICAL_FORM_EQUIVALENCE_BY_DECLARED_RULE",
        )

    # Simple negative copula contraction.
    m = re.fullmatch(r"([A-Z][A-Za-z0-9_-]*)\s+is\s+not\s+(.+?)\.", source)
    if m:
        response = f"{m.group(1)} isn't {m.group(2)}."
        return _base(
            "PASS",
            task_family="paraphrase",
            response=response,
            rule="NEGATIVE_CONTRACTION",
            semantic_contract="COPULA_NEGATION_CONTRACTION_EQUIVALENCE",
            source_preservation="TOKEN_LEVEL_EQUIVALENT_CONTRACTION",
        )

    # Coordinate commutativity for a shared plural predicate.
    m = re.fullmatch(
        r"([A-Z][A-Za-z0-9_-]*)\s+and\s+([A-Z][A-Za-z0-9_-]*)\s+are\s+(.+?)\.",
        source,
    )
    if m and m.group(1) != m.group(2):
        response = f"{m.group(2)} and {m.group(1)} are {m.group(3)}."
        return _base(
            "PASS",
            task_family="paraphrase",
            response=response,
            rule="COORDINATE_SWAP",
            semantic_contract="SYMMETRIC_COORDINATION_REORDERING",
            source_preservation="CONJUNCT_SET_IDENTICAL",
        )

    return _base(
        "ABSTAIN_UNSUPPORTED",
        task_family="paraphrase",
        response=None,
        reason="NO_PROVED_TRUTH_PRESERVING_REWRITE",
    )


_CONTRACTIONS = (
    (re.compile(r"\bcan't\b", re.I), "cannot"),
    (re.compile(r"\bisn't\b", re.I), "is not"),
    (re.compile(r"\baren't\b", re.I), "are not"),
    (re.compile(r"\bwasn't\b", re.I), "was not"),
    (re.compile(r"\bweren't\b", re.I), "were not"),
    (re.compile(r"\bwon't\b", re.I), "will not"),
    (re.compile(r"\bdon't\b", re.I), "do not"),
    (re.compile(r"\bdoesn't\b", re.I), "does not"),
    (re.compile(r"\bdidn't\b", re.I), "did not"),
)


def _complexity(text: str) -> tuple[int, int, int]:
    sentences = [x.strip() for x in re.split(r"[.!?]+", text) if x.strip()]
    max_words = max((len(_WORD_RE.findall(x)) for x in sentences), default=0)
    return (text.count(";"), max_words, max((len(x) for x in sentences), default=0))


def _normalized_content_tokens(text: str) -> list[str]:
    value = text
    for pattern, replacement in _CONTRACTIONS:
        value = pattern.sub(replacement, value)
    return [x.lower() for x in _WORD_RE.findall(value)]


def simplify(text: Any) -> dict[str, Any]:
    source = _clean_text(text)
    candidate = source
    applied = []

    for pattern, replacement in _CONTRACTIONS:
        updated, n = pattern.subn(replacement, candidate)
        if n:
            candidate = updated
            applied.append("EXPAND_CONTRACTION")

    if ";" in candidate:
        clauses = [x.strip() for x in candidate.split(";")]
        if all(clauses):
            rebuilt = []
            for clause in clauses:
                clause = clause.strip()
                if clause.endswith((".", "!", "?")):
                    clause = clause[:-1].rstrip()
                if clause:
                    clause = clause[:1].upper() + clause[1:]
                    rebuilt.append(clause + ".")
            if len(rebuilt) >= 2:
                candidate = " ".join(rebuilt)
                applied.append("SPLIT_SEMICOLON_CLAUSES")

    if not applied or candidate == source:
        return _base(
            "ABSTAIN_UNSUPPORTED",
            task_family="simplify",
            response=None,
            reason="NO_PROVED_SIMPLIFICATION_RULE_APPLIES",
        )

    if _normalized_content_tokens(source) != _normalized_content_tokens(candidate):
        return _base(
            "FAIL_CLOSED",
            task_family="simplify",
            response=None,
            reason="CONTENT_TOKEN_PRESERVATION_FAILED",
        )

    before = _complexity(source)
    after = _complexity(candidate)
    # Lexicographic complexity: semicolon count dominates, then maximum sentence
    # word count, then maximum sentence character length.
    if not after < before:
        return _base(
            "FAIL_CLOSED",
            task_family="simplify",
            response=None,
            reason="FROZEN_COMPLEXITY_DID_NOT_DECREASE",
            complexity_before=before,
            complexity_after=after,
        )

    return _base(
        "PASS",
        task_family="simplify",
        response=candidate,
        rule="+".join(dict.fromkeys(applied)),
        semantic_contract="NORMALIZED_CONTENT_TOKENS_PRESERVED__ONLY_DECLARED_CONTRACTION_EXPANSION_AND_CLAUSE_BOUNDARY_SPLIT",
        complexity_before=before,
        complexity_after=after,
    )


def _sentences_verbatim(text: str) -> list[str]:
    out = []
    for m in _SENTENCE_RE.finditer(text):
        value = m.group(0).strip()
        if value:
            out.append(value)
    return out


def _content_words(sentence: str) -> list[str]:
    return [
        token.lower()
        for token in _WORD_RE.findall(sentence)
        if token.lower() not in _STOP and len(token) > 1
    ]


def summarize(text: Any, max_sentences: int = 2) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise SemanticSeedError("TEXT_REQUIRED")
    source = text.strip()
    sentences = _sentences_verbatim(source)
    if len(sentences) < 2:
        return _base(
            "ABSTAIN_UNSUPPORTED",
            task_family="summarize",
            response=None,
            reason="MULTI_SENTENCE_SOURCE_REQUIRED",
        )
    if not isinstance(max_sentences, int) or isinstance(max_sentences, bool) or max_sentences < 1:
        raise SemanticSeedError("MAX_SENTENCES_INVALID")
    limit = min(max_sentences, len(sentences) - 1)
    if limit < 1:
        return _base("ABSTAIN_UNSUPPORTED", task_family="summarize", response=None)

    freq = Counter()
    sentence_words = []
    for sentence in sentences:
        words = _content_words(sentence)
        sentence_words.append(words)
        freq.update(set(words))

    scored = []
    for i, words in enumerate(sentence_words):
        # Reward source-salient terms while mildly preferring compact sentences.
        unique = set(words)
        score = sum(freq[w] for w in unique) / max(1, len(words))
        scored.append((score, -len(words), -i, i))
    chosen = sorted(x[3] for x in sorted(scored, reverse=True)[:limit])
    selected = [sentences[i] for i in chosen]
    response = " ".join(selected)

    if len(selected) >= len(sentences) or len(response) >= len(source):
        return _base(
            "FAIL_CLOSED",
            task_family="summarize",
            response=None,
            reason="STRICT_COMPRESSION_FAILED",
        )
    if any(sentence not in source for sentence in selected):
        return _base(
            "FAIL_CLOSED",
            task_family="summarize",
            response=None,
            reason="EXTRACTIVE_GROUNDING_FAILED",
        )

    return _base(
        "PASS",
        task_family="summarize",
        response=response,
        rule="DETERMINISTIC_EXTRACTIVE_TERM_CENTRALITY",
        semantic_contract="STRICT_EXTRACTIVE_NO_NOVEL_SENTENCE_CLAIMS",
        source_sentence_count=len(sentences),
        summary_sentence_count=len(selected),
        selected_source_sentence_indices=chosen,
        compression_ratio=len(response) / len(source),
    )


def _story_field(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise SemanticSeedError(label + "_MUST_BE_STRING")
    value = " ".join(value.strip().split())
    if not value:
        raise SemanticSeedError(label + "_REQUIRED")
    if len(value) > 300:
        raise SemanticSeedError(label + "_TOO_LONG")
    return value


def story_generation(*, character: Any, goal: Any, obstacle: Any, setting: Any) -> dict[str, Any]:
    c = _story_field(character, "CHARACTER")
    g = _story_field(goal, "GOAL")
    o = _story_field(obstacle, "OBSTACLE")
    s = _story_field(setting, "SETTING")

    response = (
        f"In {s}, {c} set out to {g}. "
        f"Soon, {o} stood in the way. "
        f"{c} faced {o} while still trying to {g}. "
        f"The scene closed on one question: could {c} {g} despite {o}?"
    )
    required = [c, g, o, s]
    if any(value not in response for value in required):
        return _base(
            "FAIL_CLOSED",
            task_family="story_generation",
            response=None,
            reason="STRUCTURED_FACT_GROUNDING_FAILED",
        )

    return _base(
        "PASS",
        task_family="story_generation",
        response=response,
        rule="FIXED_FOUR_BEAT_GROUNDED_NARRATIVE_SCAFFOLD",
        semantic_contract="ONLY_EXPLICIT_CHARACTER_GOAL_OBSTACLE_SETTING_SLOTS_PLUS_FIXED_RELATIONAL_SCAFFOLD",
        grounded_fields={"character": c, "goal": g, "obstacle": o, "setting": s},
        all_grounded_fields_verbatim=True,
    )


def produce(task_family: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    family = str(task_family or "").strip().lower()
    if not isinstance(payload, Mapping):
        raise SemanticSeedError("PAYLOAD_MAPPING_REQUIRED")
    if family == "paraphrase":
        return paraphrase(payload.get("text"))
    if family == "simplify":
        return simplify(payload.get("text"))
    if family == "summarize":
        return summarize(payload.get("text"), int(payload.get("max_sentences", 2)))
    if family == "story_generation":
        return story_generation(
            character=payload.get("character"),
            goal=payload.get("goal"),
            obstacle=payload.get("obstacle"),
            setting=payload.get("setting"),
        )
    return _base(
        "ABSTAIN_UNSUPPORTED",
        task_family=family,
        response=None,
        reason="TASK_FAMILY_UNSUPPORTED",
    )
