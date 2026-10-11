#!/usr/bin/env python3
"""Deterministic HLE MCQ retrieval-vote candidate generator V1.

This is a Brain-owned fallible solver proposal, not a truth oracle. It composes:
- the native HLE MCQ semantic compiler,
- the verified HLE contamination-filtered search/fetch adapter,
- deterministic lexical evidence scoring over fetched source excerpts,
- shared-stem plus option-specific search signals,
- explicit negative-question inversion.

No LLM/model is called. Gold is never read. Every emitted option is a candidate
for benchmark grading, not an internally certified fact.
"""
from __future__ import annotations

import hashlib
import html
import math
import re
import urllib.parse
import unicodedata
from collections import Counter
from typing import Any, Callable, Mapping

from canonical.runtime.hle_native_semantic_compiler_v1 import compile_question
from canonical.runtime import root2_hle_opus55_tool_adapter_v1 as tools

SCHEMA = "PROJECT_BRAIN_HLE_MCQ_RETRIEVAL_VOTE_V1"

_TAG = re.compile(r"<[^>]+>")
_SCRIPT = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
_WORD = re.compile(r"[^\W_]+(?:[-/][^\W_]+)*", re.UNICODE)
_NEG = re.compile(
    r"\b(?:not|except|false|incorrect|least likely|least consistent|does not|"
    r"isn't|is not|cannot|can't|fails to|would not)\b",
    re.I,
)
_STOP = {
    "a","an","and","are","as","at","be","been","being","but","by","can","could",
    "do","does","for","from","had","has","have","how","if","in","into","is","it",
    "may","might","must","of","on","or","should","that","the","their","then","there",
    "these","this","those","to","was","were","what","when","where","which","who",
    "whom","whose","why","will","with","would","answer","choice","choices","choose",
    "following","option","options","question","select","correct","best",
}


def _canon(v: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(v or "")).strip().split())


def _tokens(v: Any) -> list[str]:
    out=[]
    for raw in _WORD.findall(_canon(v)):
        t=raw.casefold().strip("-/")
        if len(t)<2 or t in _STOP:
            continue
        if t not in out:
            out.append(t)
    return out


def _plain_html(raw: str) -> str:
    text=_SCRIPT.sub(" ",str(raw or ""))
    text=_TAG.sub(" ",text)
    text=html.unescape(text)
    return _canon(text)


def _host(url: str) -> str:
    try:
        return (urllib.parse.urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _sentence_windows(text: str) -> list[str]:
    # Bound work and preserve local co-occurrence. Page excerpts are already bounded.
    rows=[x.strip() for x in re.split(r"(?<=[.!?;])\s+|\n+",text) if x.strip()]
    if not rows:
        return [text]
    windows=[]
    for i,row in enumerate(rows[:160]):
        block=" ".join(rows[max(0,i-1):min(len(rows),i+2)])
        windows.append(block[:1600])
    return windows


def _option_page_score(stem: str, option: str, page_text: str) -> dict[str, Any]:
    stem_t=_tokens(stem)
    opt_t=_tokens(option)
    stem_set=set(stem_t)
    discriminators=[t for t in opt_t if t not in stem_set]
    if not discriminators:
        discriminators=opt_t
    # Prefer informative longer tokens without requiring a learned IDF model.
    discr=sorted(discriminators,key=lambda t:(-len(t),t))[:16]
    anchors=sorted(stem_t,key=lambda t:(-len(t),t))[:28]
    low=_canon(page_text).casefold()
    phrase=_canon(option).casefold()
    phrase_hits=low.count(phrase) if phrase and len(phrase)>=4 else 0
    best=0.0
    best_d=0.0
    best_a=0.0
    for w in _sentence_windows(page_text):
        wt=set(_tokens(w))
        d=(sum(1 for t in discr if t in wt)/len(discr)) if discr else 0.0
        a=(sum(1 for t in anchors if t in wt)/len(anchors)) if anchors else 0.0
        # Option discriminators are load-bearing; stem anchors only establish context.
        s=3.0*d+1.25*a+(1.5 if phrase and phrase in _canon(w).casefold() else 0.0)
        if s>best:
            best=s; best_d=d; best_a=a
    return {
        "score": best + min(2,phrase_hits)*0.6,
        "max_discriminator_fraction": best_d,
        "max_stem_anchor_fraction": best_a,
        "exact_phrase_hits_capped": min(2,phrase_hits),
    }


def _search(search_fn: Callable[..., Mapping[str,Any]], query: str, limit: int) -> Mapping[str,Any]:
    try:
        return search_fn(query,limit=limit)
    except Exception as exc:
        return {"status":"FAILED","results":[],"error":type(exc).__name__}


def _fetch(fetch_fn: Callable[..., Mapping[str,Any]], url: str) -> Mapping[str,Any]:
    try:
        return fetch_fn(url,max_bytes=600000)
    except Exception as exc:
        return {"status":"FAILED","url":url,"error":type(exc).__name__}


def propose(
    *,
    task_id: str,
    question: str,
    has_nonempty_image_payload: bool=False,
    search_fn: Callable[..., Mapping[str,Any]] | None=None,
    fetch_fn: Callable[..., Mapping[str,Any]] | None=None,
    shared_search_limit: int=10,
    per_option_search_limit: int=4,
    max_fetches: int=14,
) -> dict[str,Any]:
    compiled=compile_question(
        task_id=task_id,
        answer_type="multipleChoice",
        question=question,
        has_nonempty_image_payload=has_nonempty_image_payload,
    )
    if compiled.get("pass") is not True:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED__MCQ_COMPILATION_FAILED",
            "candidate_answer":None,"candidate_answer_authority":False,
            "compile_status":compiled.get("status"),"terminal_authority":False,
        }
    typed=compiled["typed_decision"]
    stem=typed["stem"]
    alternatives=typed["alternatives"]
    search_fn=search_fn or tools.search_web
    fetch_fn=fetch_fn or tools.fetch_web

    shared_query=typed["stem_research_focus"]["query"]
    shared=_search(search_fn,shared_query,shared_search_limit)
    option_searches={}
    url_priority=[]
    seen=set()

    def add_urls(result,weight,label):
        for rank,row in enumerate(result.get("results") or []):
            if not isinstance(row,Mapping): continue
            url=str(row.get("url") or "")
            if not url: continue
            if url not in seen:
                seen.add(url)
                url_priority.append((weight/(1+rank),url,label))
            else:
                url_priority.append((weight/(1+rank),url,label))

    add_urls(shared,1.5,"SHARED_STEM")
    for alt in alternatives:
        aid=alt["id"]
        query=alt["research_focus"]["query"]
        res=_search(search_fn,query,per_option_search_limit)
        option_searches[aid]=res
        add_urls(res,1.0,"OPTION_"+aid)

    # Aggregate search-rank support by option and pick a bounded diverse fetch set.
    rank_support=Counter()
    per_url_option=Counter()
    for alt in alternatives:
        aid=alt["id"]
        for rank,row in enumerate(option_searches[aid].get("results") or []):
            if isinstance(row,Mapping) and row.get("url"):
                u=str(row["url"])
                rank_support[aid]+=1.0/(1+rank)
                per_url_option[(u,aid)]+=1.0/(1+rank)

    # Deduplicate by URL; higher combined priority first, then URL for determinism.
    pri=Counter()
    for weight,url,_ in url_priority:
        pri[url]+=weight
    ranked_urls=sorted(pri,key=lambda u:(-pri[u],u))
    selected=[]
    hosts=set()
    # first pass favors domain diversity
    for u in ranked_urls:
        h=_host(u)
        if h and h in hosts: continue
        selected.append(u); hosts.add(h)
        if len(selected)>=max_fetches: break
    if len(selected)<max_fetches:
        for u in ranked_urls:
            if u not in selected:
                selected.append(u)
                if len(selected)>=max_fetches: break

    pages=[]
    for u in selected:
        res=_fetch(fetch_fn,u)
        if res.get("status")!="PASS": continue
        plain=_plain_html(str(res.get("body_excerpt") or ""))
        if not plain: continue
        pages.append({
            "url":str(res.get("final_url") or res.get("url") or u),
            "host":_host(str(res.get("final_url") or res.get("url") or u)),
            "body_sha256":res.get("body_sha256"),
            "text":plain,
        })

    option_rows=[]
    max_rank=max([float(rank_support[a["id"]]) for a in alternatives] or [0.0])
    for alt in alternatives:
        aid=alt["id"]
        total=0.0
        host_hits=set()
        page_receipts=[]
        for page in pages:
            ev=_option_page_score(stem,alt["label"],page["text"])
            # Same page can support several options; that's allowed and handled by margin.
            total+=float(ev["score"])
            if ev["score"]>=1.2 and page["host"]:
                host_hits.add(page["host"])
            if ev["score"]>0:
                page_receipts.append({
                    "body_sha256":page["body_sha256"],
                    "host_sha256":hashlib.sha256(page["host"].encode()).hexdigest(),
                    **ev,
                })
        rank=float(rank_support[aid])
        rank_norm=(rank/max_rank) if max_rank>0 else 0.0
        diversity=min(len(host_hits),4)/4.0
        score=total+1.25*rank_norm+1.0*diversity
        option_rows.append({
            "id":aid,
            "score":score,
            "search_rank_support":rank,
            "independent_support_host_count":len(host_hits),
            "page_receipts":page_receipts,
        })

    negative=bool(_NEG.search(stem))
    # Positive asks choose strongest support; explicit negative asks choose weakest support.
    ordered=sorted(
        option_rows,
        key=(lambda r:(r["score"],r["id"])) if negative else (lambda r:(-r["score"],r["id"])),
    )
    chosen=ordered[0] if ordered else None
    runner=ordered[1] if len(ordered)>1 else None
    if chosen is None:
        return {
            "schema":SCHEMA,"status":"NO_CANDIDATE",
            "candidate_answer":None,"candidate_answer_authority":False,
            "terminal_authority":False,
        }
    if runner is None:
        margin=math.inf
    else:
        margin=abs(float(chosen["score"])-float(runner["score"]))
    strength=float(chosen["score"])
    confidence_band=(
        "HIGH" if len(pages)>=2 and margin>=2.0 and chosen["independent_support_host_count"]>=2
        else "MEDIUM" if len(pages)>=1 and margin>=0.75
        else "LOW"
    )
    return {
        "schema":SCHEMA,
        "status":"CANDIDATE_GENERATED",
        "task_id":task_id,
        "question_sha256":compiled["question_sha256"],
        "typed_decision_sha256":compiled["typed_decision_sha256"],
        "candidate_answer":chosen["id"],
        "candidate_answer_authority":False,
        "selection_mode":"MIN_SUPPORT_FOR_EXPLICIT_NEGATIVE_QUESTION" if negative else "MAX_SUPPORT",
        "negative_question_detected":negative,
        "candidate_score":strength,
        "runner_up_margin":margin,
        "confidence_band":confidence_band,
        "option_scores":option_rows,
        "search_receipts":{
            "shared_status":shared.get("status"),
            "option_status":{k:v.get("status") for k,v in option_searches.items()},
            "fetched_page_count":len(pages),
            "unique_search_url_count":len(ranked_urls),
        },
        "gold_accessed":False,
        "external_model_calls":0,
        "model_dependency_count":0,
        "incremental_spend_usd":0,
        "terminal_authority":False,
        "hard_nonclaim":"RETRIEVAL_VOTE_IS_A_FALLIBLE_BRAIN_OWNED_CANDIDATE_GENERATOR_NOT_A_CORRECTNESS_PROOF",
    }
