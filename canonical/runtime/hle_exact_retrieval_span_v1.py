#!/usr/bin/env python3
"""Deterministic HLE exact-answer retrieval span candidate generator V1.

Brain-owned fallible candidate generation only:
- derive a bounded non-verbatim lexical query from the question;
- use the HLE contamination-filtered search/fetch adapter;
- extract typed candidate spans (temporal, numeric, entity/term);
- rank by question-anchor co-occurrence, source diversity, and recurrence;
- emit a candidate with explicit confidence and zero correctness authority.

No external model is called and no gold field is read.
"""
from __future__ import annotations

import hashlib
import html
import math
import re
import unicodedata
import urllib.parse
from collections import defaultdict
from typing import Any, Callable, Mapping

from canonical.runtime.hle_question_shape_router_v1 import route_question
from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as tools

SCHEMA="PROJECT_BRAIN_HLE_EXACT_RETRIEVAL_SPAN_V1"

_TAG=re.compile(r"<[^>]+>")
_SCRIPT=re.compile(r"<(?:script|style)\b.*?</(?:script|style)>",re.I|re.S)
_WORD=re.compile(r"[^\W_]+(?:[-/][^\W_]+)*",re.UNICODE)
_YEAR=re.compile(r"(?<!\d)(?:1[0-9]{3}|20[0-9]{2}|2100)(?!\d)")
_NUMBER=re.compile(
    r"(?<![\w.])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
    r"(?:\s*(?:\u00d7|x)\s*10\s*\^?\s*[-+]?\d+)?"
    r"(?:\s*(?:%|percent|degrees?|\u00b0|Hz|kHz|MHz|GHz|m|cm|mm|km|s|ms|kg|g|"
    r"J|kJ|eV|V|A|W|K|Pa|mol|M|nM|\u03bcM|uM))?(?![\w.])",
    re.I,
)
_QUOTED=re.compile(r'["\u201c](.{2,120}?)["\u201d]|[\u2018\']([^\'\n]{2,120}?)[\u2019\']')
_CAPITALIZED=re.compile(
    r"\b(?:[A-Z][A-Za-z0-9'\u2019._-]*(?:\s+(?:of|the|and|for|in|on|de|van|von|"
    r"[A-Z][A-Za-z0-9'\u2019._-]*)){0,6})\b"
)
_CUE=re.compile(
    r"\b(?:called|known as|named|termed|referred to as|defined as|designated as|"
    r"is the|was the|are the|were the)\s+([^.;:!?]{2,140})",
    re.I,
)
_STOP={
 "a","an","and","are","as","at","be","been","being","but","by","can","could","did",
 "do","does","for","from","had","has","have","how","if","in","into","is","it","may",
 "might","must","of","on","or","should","that","the","their","then","there","these",
 "this","those","to","was","were","what","when","where","which","who","whom","whose",
 "why","will","with","would","answer","calculate","compute","determine","find","give",
 "identify","name","question","value",
}


def _canon(v:Any)->str:
    return " ".join(unicodedata.normalize("NFKC",str(v or "")).strip().split())


def _tokens(v:Any)->list[str]:
    out=[]
    for raw in _WORD.findall(_canon(v)):
        t=raw.casefold().strip("-/")
        if len(t)<2 or t in _STOP: continue
        if t not in out: out.append(t)
    return out


def _plain_html(raw:str)->str:
    text=_SCRIPT.sub(" ",str(raw or ""))
    text=_TAG.sub(" ",text)
    return _canon(html.unescape(text))


def _host(url:str)->str:
    try: return (urllib.parse.urlparse(url).hostname or "").lower()
    except Exception: return ""


def _last_clause(q:str)->str:
    s=_canon(q)
    pos=s.rfind("?")
    end=pos+1 if pos>=0 else len(s)
    w=s[max(0,end-1200):end]
    parts=[x.strip() for x in re.split(r"(?<=[.!?])\s+",w) if x.strip()]
    return parts[-1] if parts else w


def _query_focus(question:str)->dict[str,Any]:
    tail=_last_clause(question)
    # Proper names / long content words from full question, then the final ask.
    proper=[]
    for m in _CAPITALIZED.finditer(question):
        x=_canon(m.group(0))
        if x and x.casefold() not in {"what","which","who","when","where","how"} and x not in proper:
            proper.append(x)
    tokens=[]
    for t in [*_tokens(tail),*_tokens(question)]:
        if t not in tokens:
            tokens.append(t)
    # Limit the chance of reproducing the benchmark wording verbatim.
    pieces=proper[:6]+tokens[:28]
    q=" ".join(pieces)
    q=" ".join(q.split()[:38])
    if len(q)>700: q=q[:700].rsplit(" ",1)[0]
    if not q: raise ValueError("QUERY_FOCUS_EMPTY")
    return {
        "query":q,
        "query_sha256":hashlib.sha256(q.encode()).hexdigest(),
        "full_question_verbatim_used":q==_canon(question),
    }


def _windows(text:str)->list[str]:
    rows=[x.strip() for x in re.split(r"(?<=[.!?;])\s+|\n+",text) if x.strip()]
    if not rows: return [text]
    out=[]
    for i in range(min(len(rows),180)):
        out.append(" ".join(rows[max(0,i-1):min(len(rows),i+2)])[:1800])
    return out


def _clean_candidate(x:str)->str:
    x=_canon(x).strip(" ,;:-()[]{}")
    # Stop cue captures at common trailing discourse conjunctions.
    x=re.split(r"\s+(?:because|while|whereas|although|which|that|when|if)\s+",x,maxsplit=1,flags=re.I)[0]
    return x.strip(" ,;:-()[]{}")


def _candidate_kind(lanes:list[str])->str:
    if "TEMPORAL_LOOKUP_OR_DERIVATION" in lanes:
        return "TEMPORAL"
    if "ENTITY_TERM_OR_RELATION_LOOKUP" in lanes:
        return "ENTITY_TERM"
    if "SYMBOLIC_NUMERIC_REASONING" in lanes:
        return "NUMERIC"
    return "OPEN_SPAN"


def _extract(window:str,kind:str)->list[str]:
    vals=[]
    def add(x):
        c=_clean_candidate(x)
        if not c or len(c)>180: return
        if c.casefold() in _STOP: return
        if c not in vals: vals.append(c)
    if kind=="TEMPORAL":
        for x in _YEAR.findall(window): add(x)
    if kind=="NUMERIC":
        for m in _NUMBER.finditer(window): add(m.group(0))
    # Cue and quoted spans are useful across entity/open modes and occasionally numeric units.
    for m in _CUE.finditer(window):
        add(m.group(1))
    for m in _QUOTED.finditer(window):
        add(m.group(1) or m.group(2) or "")
    if kind in {"ENTITY_TERM","OPEN_SPAN"}:
        for x in _CAPITALIZED.findall(window): add(x)
    return vals[:120]


def _search(fn,query,limit):
    try: return fn(query,limit=limit)
    except Exception as exc: return {"status":"FAILED","results":[],"error":type(exc).__name__}


def _fetch(fn,url):
    try: return fn(url,max_bytes=700000)
    except Exception as exc: return {"status":"FAILED","url":url,"error":type(exc).__name__}


def propose(
    *,
    task_id:str,
    question:str,
    has_nonempty_image_payload:bool=False,
    search_fn:Callable[...,Mapping[str,Any]]|None=None,
    fetch_fn:Callable[...,Mapping[str,Any]]|None=None,
    search_limit:int=14,
    max_fetches:int=12,
)->dict[str,Any]:
    routed=route_question(
        task_id=task_id,answer_type="exactMatch",question=question,
        has_nonempty_image_payload=has_nonempty_image_payload,
    )
    focus=_query_focus(question)
    kind=_candidate_kind(list(routed["candidate_lanes"]))
    search_fn=search_fn or tools.search_web
    fetch_fn=fetch_fn or tools.fetch_web
    sr=_search(search_fn,focus["query"],search_limit)
    urls=[]
    seen=set()
    for rank,row in enumerate(sr.get("results") or []):
        if not isinstance(row,Mapping): continue
        u=str(row.get("url") or "")
        if u and u not in seen:
            seen.add(u); urls.append((rank,u))
    pages=[]
    hosts=set()
    for rank,u in urls:
        if len(pages)>=max_fetches: break
        res=_fetch(fetch_fn,u)
        if res.get("status")!="PASS": continue
        txt=_plain_html(str(res.get("body_excerpt") or ""))
        if not txt: continue
        h=_host(str(res.get("final_url") or res.get("url") or u))
        pages.append({
            "rank":rank,"host":h,
            "body_sha256":res.get("body_sha256"),
            "text":txt,
        })
        if h: hosts.add(h)

    qtokens=set(_tokens(question))
    tailtokens=set(_tokens(_last_clause(question)))
    # Aggregate candidate evidence without trusting any single page.
    agg={}
    for page in pages:
        for window in _windows(page["text"]):
            wt=set(_tokens(window))
            anchor=(len(wt & qtokens)/max(1,min(len(qtokens),28)))
            tail=(len(wt & tailtokens)/max(1,min(len(tailtokens),18)))
            if anchor<=0 and tail<=0: continue
            for cand in _extract(window,kind):
                # Do not simply return a phrase copied from the question.
                if cand.casefold() in _canon(question).casefold() and len(cand)>=4:
                    continue
                key=cand.casefold()
                row=agg.setdefault(key,{
                    "surface":cand,"score":0.0,"hosts":set(),"occurrences":0,
                    "evidence_receipts":[],
                })
                local=1.7*anchor+2.1*tail+1.0/(1+page["rank"])
                row["score"]+=local
                row["occurrences"]+=1
                if page["host"]: row["hosts"].add(page["host"])
                if len(row["evidence_receipts"])<8:
                    row["evidence_receipts"].append({
                        "body_sha256":page["body_sha256"],
                        "host_sha256":hashlib.sha256(page["host"].encode()).hexdigest(),
                        "anchor_fraction":anchor,
                        "tail_anchor_fraction":tail,
                    })

    rows=[]
    for row in agg.values():
        diversity=min(len(row["hosts"]),4)
        recurrence=min(row["occurrences"],6)
        score=row["score"]+1.1*diversity+0.25*recurrence
        rows.append({
            "surface":row["surface"],"score":score,
            "independent_host_count":len(row["hosts"]),
            "occurrences":row["occurrences"],
            "evidence_receipts":row["evidence_receipts"],
        })
    rows.sort(key=lambda r:(
        -r["score"],
        -r["independent_host_count"],
        -min(len(_tokens(r["surface"])),4),
        len(r["surface"]),
        r["surface"].casefold(),
    ))
    chosen=rows[0] if rows else None
    runner=rows[1] if len(rows)>1 else None
    if chosen is None:
        return {
            "schema":SCHEMA,"status":"NO_CANDIDATE",
            "task_id":task_id,"question_sha256":routed["question_sha256"],
            "candidate_answer":None,"candidate_answer_authority":False,
            "candidate_kind":kind,"query_focus_sha256":focus["query_sha256"],
            "gold_accessed":False,"external_model_calls":0,"model_dependency_count":0,
            "incremental_spend_usd":0,"terminal_authority":False,
        }
    margin=float(chosen["score"])-(float(runner["score"]) if runner else 0.0)
    confidence=(
        "HIGH" if chosen["independent_host_count"]>=2 and margin>=2.0
        else "MEDIUM" if chosen["independent_host_count"]>=1 and margin>=0.75
        else "LOW"
    )
    return {
        "schema":SCHEMA,"status":"CANDIDATE_GENERATED",
        "task_id":task_id,"question_sha256":routed["question_sha256"],
        "candidate_answer":chosen["surface"],"candidate_answer_authority":False,
        "candidate_kind":kind,"candidate_score":chosen["score"],
        "runner_up_margin":margin,"confidence_band":confidence,
        "candidate_evidence":chosen,
        "top_candidates":rows[:8],
        "query_focus_sha256":focus["query_sha256"],
        "query_full_question_verbatim_used":focus["full_question_verbatim_used"],
        "search_status":sr.get("status"),"fetched_page_count":len(pages),
        "independent_fetched_host_count":len(hosts),
        "has_nonempty_image_payload":has_nonempty_image_payload,
        "image_semantics_used":False,
        "gold_accessed":False,"external_model_calls":0,"model_dependency_count":0,
        "incremental_spend_usd":0,"terminal_authority":False,
        "hard_nonclaim":"RETRIEVAL_SPAN_RANKING_IS_A_FALLIBLE_BRAIN_OWNED_CANDIDATE_GENERATOR_NOT_A_CORRECTNESS_PROOF",
    }
