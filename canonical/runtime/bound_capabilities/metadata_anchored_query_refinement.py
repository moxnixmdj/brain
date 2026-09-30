#!/usr/bin/env python3
"""Deterministic metadata-anchored refinement for open-research discovery.

When a registry/metadata candidate has strictly stronger lexical coverage of
an already-focused research query than every live-web search candidate, use
the shared query terms as a second-pass web query. This does not assert
factual relevance or authority; it only prevents useful metadata from being
thrown away before retrievable evidence can be discovered.
"""
from __future__ import annotations
import re

SCHEMA="PROJECT_BRAIN_METADATA_ANCHORED_QUERY_REFINEMENT_V1"
WORD_RE=re.compile(r"[a-z0-9]+(?:[._/-][a-z0-9]+)*",re.I)

def _canon(value):
    return " ".join(str(value or "").strip().split())

def _tokens(value):
    out=[]
    for raw in WORD_RE.findall(_canon(value).lower()):
        token=raw.strip("._/-")
        if len(token)<2:
            continue
        if token not in out:
            out.append(token)
    return out

def _candidate_tokens(candidate):
    c=dict(candidate or {})
    return set(_tokens(" ".join([
        _canon(c.get("title")),
        _canon(c.get("record_title")),
        _canon(c.get("snippet")),
        _canon(c.get("publisher")),
    ])))

def overlap(query,candidate):
    q=_tokens(query)
    ct=_candidate_tokens(candidate)
    matched=[t for t in q if t in ct]
    return {
        "query_tokens":q,
        "matched_terms":matched,
        "matched_term_count":len(matched),
    }

def select(query,web_candidates,metadata_candidates):
    query=_canon(query)
    base={
        "schema":SCHEMA,
        "status":"NO_REFINEMENT",
        "query":query,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
    if not query:
        return {**base,"reason":"QUERY_REQUIRED"}
    web=list(web_candidates or [])
    meta=list(metadata_candidates or [])
    if not meta:
        return {**base,"reason":"NO_METADATA_CANDIDATES"}

    web_rows=[(overlap(query,c),i,c) for i,c in enumerate(web)]
    meta_rows=[(overlap(query,c),i,c) for i,c in enumerate(meta)]
    web_rows.sort(key=lambda x:(-x[0]["matched_term_count"],x[1]))
    meta_rows.sort(key=lambda x:(-x[0]["matched_term_count"],x[1]))
    best_web=web_rows[0] if web_rows else ({"matched_term_count":0,"matched_terms":[]},-1,None)
    best_meta=meta_rows[0]

    if best_meta[0]["matched_term_count"]<=best_web[0]["matched_term_count"]:
        return {
            **base,
            "reason":"METADATA_NOT_STRICTLY_STRONGER_THAN_WEB",
            "best_web_overlap":best_web[0],
            "best_metadata_overlap":best_meta[0],
        }
    if not best_meta[0]["matched_terms"]:
        return {**base,"reason":"NO_SHARED_QUERY_TERMS"}

    refined=" ".join(best_meta[0]["matched_terms"])
    if not refined or refined==query:
        return {**base,"reason":"NO_DISTINCT_REFINED_QUERY"}

    return {
        **base,
        "status":"REFINEMENT_READY",
        "refined_query":refined,
        "best_web_overlap":best_web[0],
        "best_metadata_overlap":best_meta[0],
        "metadata_candidate":best_meta[2],
        "selection_rule":"STRICTLY_GREATER_FOCUSED_QUERY_TERM_COVERAGE__NO_ABSOLUTE_SCORE_THRESHOLD",
    }
