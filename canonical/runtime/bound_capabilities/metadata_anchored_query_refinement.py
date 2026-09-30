#!/usr/bin/env python3
"""Deterministic metadata-anchored refinement for open-research discovery.

A bibliographically verified candidate may contain stronger subject identity
than every currently retrievable web candidate. This primitive constructs one
bounded refinement query from shared focused-query terms plus discriminative
metadata-only title terms, and later verifies that a materialized live
candidate preserves both kinds of anchors.

It does not establish factual correctness, authority, primary-source status,
or evidence sufficiency.
"""
from __future__ import annotations
import re

SCHEMA="PROJECT_BRAIN_METADATA_ANCHORED_QUERY_REFINEMENT_V2"
WORD_RE=re.compile(r"[a-z0-9]+(?:[._/-][a-z0-9]+)*",re.I)
GENERIC={
    "a","an","and","are","as","at","be","by","for","from","how","in","is","it",
    "of","on","or","that","the","this","to","was","were","what","when","where",
    "which","who","why","with","whether","using","estimated","estimate",
}

def _canon(value):
    return " ".join(str(value or "").strip().split())

def _tokens(value):
    out=[]
    for raw in WORD_RE.findall(_canon(value).lower()):
        token=raw.strip("._/-")
        if len(token)<2 or token in GENERIC:
            continue
        if token not in out:
            out.append(token)
    return out

def _candidate_tokens(candidate):
    c=dict(candidate or {})
    return _tokens(" ".join([
        _canon(c.get("title")),
        _canon(c.get("record_title")),
        _canon(c.get("snippet")),
        _canon(c.get("publisher")),
    ]))

def overlap(query,candidate):
    q=_tokens(query)
    ct=set(_candidate_tokens(candidate))
    matched=[t for t in q if t in ct]
    return {
        "query_tokens":q,
        "matched_terms":matched,
        "matched_term_count":len(matched),
    }

def refine(query,metadata_candidate,web_candidates,max_anchor_terms=6):
    query=_canon(query)
    meta=dict(metadata_candidate or {})
    base={
        "schema":SCHEMA,
        "status":"NO_REFINEMENT",
        "query":query,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
    if not query:
        return {**base,"reason":"QUERY_REQUIRED"}
    if not meta:
        return {**base,"reason":"METADATA_CANDIDATE_REQUIRED"}

    meta_overlap=overlap(query,meta)
    web_rows=[overlap(query,c) for c in list(web_candidates or [])]
    best_web=max((x["matched_term_count"] for x in web_rows),default=0)
    if meta_overlap["matched_term_count"]<=best_web:
        return {
            **base,
            "reason":"METADATA_NOT_STRICTLY_STRONGER_THAN_WEB",
            "best_web_matched_term_count":best_web,
            "metadata_overlap":meta_overlap,
        }
    shared=list(meta_overlap["matched_terms"])
    if not shared:
        return {**base,"reason":"NO_SHARED_FOCUSED_QUERY_TERMS"}

    query_set=set(_tokens(query))
    metadata_tokens=_candidate_tokens(meta)
    anchors=[
        t for t in metadata_tokens
        if t not in query_set and not t.isdigit() and len(t)>=3
    ][:max(1,min(int(max_anchor_terms),10))]
    if not anchors:
        return {**base,"reason":"NO_DISCRIMINATIVE_METADATA_ONLY_ANCHORS"}

    parts=shared+anchors
    doi=_canon(meta.get("doi"))
    if doi:
        parts.append(doi)
    refined=_canon(" ".join(parts))
    if not refined or refined==query:
        return {**base,"reason":"NO_DISTINCT_REFINED_QUERY"}

    return {
        **base,
        "status":"REFINEMENT_READY",
        "refined_query":refined,
        "shared_query_terms":shared,
        "metadata_anchor_terms":anchors,
        "metadata_candidate":{
            "url":meta.get("url"),
            "doi":meta.get("doi"),
            "title":meta.get("title"),
            "record_title":meta.get("record_title"),
            "publisher":meta.get("publisher"),
            "source_class":meta.get("source_class"),
        },
        "metadata_overlap":meta_overlap,
        "best_web_matched_term_count":best_web,
        "selection_rule":"METADATA_STRICTLY_STRONGER_FOCUSED_QUERY_COVERAGE_PLUS_DISTINCT_METADATA_ANCHOR",
    }

def continuity(refinement,candidate):
    ref=dict(refinement or {})
    c=dict(candidate or {})
    base={
        "schema":"PROJECT_BRAIN_METADATA_REFINEMENT_CONTINUITY_V1",
        "status":"UNVERIFIED",
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
    if ref.get("status")!="REFINEMENT_READY":
        return {**base,"reason":"QUALIFIED_REFINEMENT_REQUIRED"}
    tokens=set(_candidate_tokens(c))
    shared=[t for t in ref.get("shared_query_terms") or [] if t in tokens]
    anchors=[t for t in ref.get("metadata_anchor_terms") or [] if t in tokens]
    verified=bool(shared) and bool(anchors)
    return {
        **base,
        "status":"CONTINUITY_VERIFIED" if verified else "UNVERIFIED",
        "shared_query_terms_matched":shared,
        "metadata_anchor_terms_matched":anchors,
        "required_shared_match_count":1,
        "required_metadata_anchor_match_count":1,
        "output_verified":verified,
        "claim_scope":"LEXICAL_METADATA_TO_LIVE_CANDIDATE_CONTINUITY_ONLY",
    }
