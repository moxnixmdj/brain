#!/usr/bin/env python3
"""Deterministic research-query focus for broad open-research objectives.

This module removes research-orchestration framing while preserving the
decision-bearing technical subject. It does not infer facts, choose
authorities, or establish semantic entailment. The output is only a bounded
search/ranking query.
"""
from __future__ import annotations
import hashlib
import re

SCHEMA="PROJECT_BRAIN_RESEARCH_QUERY_FOCUS_V1"

_BROAD_LEAD=re.compile(
    r"^(?:(?:determine|assess|evaluate|investigate|estimate|quantify|compare|analy[sz]e)"
    r"(?:\s+whether)?\s+)",
    re.IGNORECASE,
)
# Cut only at an actual sentence boundary followed by an orchestration
# instruction. This deliberately does NOT split on arbitrary periods, so
# abbreviations such as "U.S. GDP" remain intact.
_CONTROL_SENTENCE_BOUNDARY=re.compile(
    r"(?<=[.!?])\s+(?=(?:use|using|autonomously|independently|choose|select|"
    r"identify|state|preserve|produce|provide|discover|verify|run|execute|save|"
    r"cite|report|return)\b)",
    re.IGNORECASE,
)
# For one-sentence objectives, allow an orchestration tail to be removed only
# when it starts after explicit clause punctuation or an "and <control>"
# boundary. Technical noun usage such as "CPU use" or "run length" is retained.
_CONTROL_CLAUSE_BOUNDARY=re.compile(
    r"(?:\s*[,;:]\s*|\s+\band\s+)"
    r"(?=(?:use|using|autonomously|independently|choose|select|identify|state|"
    r"preserve|produce|provide|discover|verify|run|execute|save|cite|report|return)\b)",
    re.IGNORECASE,
)
_TOKEN=re.compile(r"[A-Za-z0-9]+(?:[-/.][A-Za-z0-9]+)*")
# Keep technical nouns/adjectives (including "primary", "reference",
# "higher/lower", and noun "use"). Orchestration sentences are removed
# structurally instead of by deleting potentially meaningful domain words.
_STOP={
    "assess","determine","evaluate","investigate","estimate","quantify","compare",
    "analyze","analyse","whether",
    "the","a","an","of","to","and","or","is","are","was","were","be","being","been",
    "that","this","these","those","in","on","at","by","for","from","with","without",
    "as","than",
}

def _canon(value):
    return " ".join(str(value or "").strip().split())

def _decision_clause(objective):
    text=_canon(objective)
    if not text:
        return ""
    # Preserve all decision text until the first explicit orchestration
    # sentence. This is abbreviation-safe and allows more than one technical
    # decision sentence when the objective genuinely contains one.
    decision=_CONTROL_SENTENCE_BOUNDARY.split(text,maxsplit=1)[0]
    decision=_BROAD_LEAD.sub("",decision).strip()
    # One-sentence form: cut only at a syntactic control-clause boundary.
    m=_CONTROL_CLAUSE_BOUNDARY.search(decision)
    if m and m.start()>24:
        decision=decision[:m.start()].rstrip(" ,;:")
    return _canon(decision.strip(" .!?"))

def _tokens(text):
    out=[]
    for raw in _TOKEN.findall(text):
        t=raw.lower().strip("-/.")
        if len(t)<2 or t in _STOP:
            continue
        if t not in out:
            out.append(t)
    return out

def focus(objective,max_tokens=32):
    original=_canon(objective)
    base={
        "schema":SCHEMA,
        "objective":original or None,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
        "semantic_entailment_status":"UNVERIFIED",
        "factual_correctness_status":"UNVERIFIED",
    }
    if not original:
        return {**base,"status":"UNRESOLVED","reason":"OBJECTIVE_REQUIRED","query":"","tokens":[]}
    if len(original)>4000:
        return {**base,"status":"UNRESOLVED","reason":"OBJECTIVE_TOO_LONG","query":"","tokens":[]}
    clause=_decision_clause(original)
    tokens=_tokens(clause)
    if not tokens:
        return {**base,"status":"UNRESOLVED","reason":"NO_DISCRIMINATIVE_SUBJECT_TOKENS","query":"","tokens":[]}
    tokens=tokens[:max(2,min(int(max_tokens),48))]
    query=" ".join(tokens)
    return {
        **base,
        "status":"FOCUSED",
        "decision_clause":clause,
        "query":query,
        "tokens":tokens,
        "query_sha256":hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "method":"DECISION_TEXT_UNTIL_EXPLICIT_ORCHESTRATION_BOUNDARY_PLUS_MINIMAL_FUNCTION_WORD_FILTER",
        "claim_scope":"DETERMINISTIC_RESEARCH_SUBJECT_QUERY_ONLY",
    }
