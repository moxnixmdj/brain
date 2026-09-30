#!/usr/bin/env python3
"""Deterministic research-query focus for broad open-research objectives.

This module strips orchestration language and preserves the decision-bearing
technical subject. It does not infer facts, choose authorities, or establish
semantic entailment. The output is only a bounded search/ranking query.
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
_RELATION_NOISE=re.compile(
    r"\b(?:is|are|was|were|be|being|been|whether|than|the|a|an|of|to|and|or|"
    r"greater|higher|larger|lower|less|smaller|more|fewer|equal|equals|"
    r"exceeds?|exceeded|differ(?:s|ed)?|difference|at\s+most|at\s+least|"
    r"no\s+more\s+than|no\s+less\s+than)\b",
    re.IGNORECASE,
)
_CONTROL_START=re.compile(
    r"\b(?:use|using|autonomously|independently|choose|select|identify|state|"
    r"preserve|produce|provide|discover|verify|run|execute|save)\b",
    re.IGNORECASE,
)
_TOKEN=re.compile(r"[A-Za-z0-9]+(?:[-/.][A-Za-z0-9]+)*")
_STOP={
    "assess","determine","evaluate","investigate","estimate","quantify","compare",
    "analyze","analyse","whether","use","using","authoritative","primary",
    "technical","evidence","real","executable","check","autonomously","discover",
    "verify","relevant","choose","selected","select","run","zero-cost","zero",
    "cost","method","identify","material","limitations","limitation","independently",
    "consequential","result","produce","decision-quality","decision","quality",
    "answer","provenance","reference","reported",
    "the","a","an","of","to","and","or","is","are","was","were","be","than",
    "greater","higher","larger","lower","less","smaller","more","fewer",
}

def _canon(value):
    return " ".join(str(value or "").strip().split())

def _decision_clause(objective):
    text=_canon(objective)
    if not text:
        return ""
    # The frozen parent-task grammar places the decision question first and
    # orchestration instructions after it. Prefer the first sentence.
    first=re.split(r"(?<=[.!?])\s+",text,maxsplit=1)[0].strip(" .!?")
    first=_BROAD_LEAD.sub("",first).strip()
    # For single-sentence objectives, cut at the first orchestration verb only
    # after a substantive subject has already appeared.
    m=_CONTROL_START.search(first)
    if m and m.start()>24:
        first=first[:m.start()].rstrip(" ,;:")
    return _canon(first)

def _tokens(text):
    out=[]
    for raw in _TOKEN.findall(text):
        t=raw.lower().strip("-/.")
        if len(t)<2 or t in _STOP:
            continue
        # Keep stable identifiers/numbers and technical words. Remove pure
        # relation/control vocabulary, which search engines otherwise overfit.
        if t not in out:
            out.append(t)
    return out

def focus(objective,max_tokens=24):
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
    clause=_decision_clause(original)
    tokens=_tokens(clause)
    if not tokens:
        return {**base,"status":"UNRESOLVED","reason":"NO_DISCRIMINATIVE_SUBJECT_TOKENS","query":"","tokens":[]}
    tokens=tokens[:max(2,min(int(max_tokens),40))]
    # Preserve the human-readable technical clause where possible, but delete
    # relation filler. Search identity is also bound to the token sequence.
    reduced=_RELATION_NOISE.sub(" ",clause)
    reduced=_canon(re.sub(r"\s*[,;:]\s*"," ",reduced))
    query_tokens=_tokens(reduced)
    query_tokens=(query_tokens or tokens)[:len(tokens)]
    query=" ".join(query_tokens)
    if not query:
        query=" ".join(tokens)
    return {
        **base,
        "status":"FOCUSED",
        "decision_clause":clause,
        "query":query,
        "tokens":query_tokens or tokens,
        "query_sha256":hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "method":"FIRST_DECISION_CLAUSE_PLUS_CONTROL_AND_RELATION_NOISE_REMOVAL",
        "claim_scope":"DETERMINISTIC_RESEARCH_SUBJECT_QUERY_ONLY",
    }
