#!/usr/bin/env python3
"""Brain-native relation-bound research solver V4.

V4 composes the V2 multi-query question contract with typed evidence synthesis V2.
It reuses the deterministic web/Wikipedia retrieval primitives from open-domain V5
but replaces V5's generic first-span ranking with answer-slot-aware relations and
cross-query support. No model calls, no gold, no correctness authority.
"""
from __future__ import annotations

import hashlib
import re
import urllib.parse
from collections import defaultdict
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.hle_native_question_contract_v2 import compile_question, _tokens
from canonical.runtime.hle_evidence_candidate_synthesis_v2 import synthesize
from canonical.runtime import hle_native_open_domain_research_v5 as retrieval

SCHEMA = "PROJECT_BRAIN_HLE_NATIVE_RESEARCH_SOLVER_V4"
_SENTENCE = re.compile(r"(?<=[.!?;])\s+|\n+")
_NEG = re.compile(r"\b(?:not|never|except|excluding|incorrect|false|least\s+likely|cannot|can't|doesn't|does\s+not|isn't|is\s+not)\b",re.I)

def _sha(v: str) -> str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()

def _host(url: str) -> str:
    try:
        h=(urllib.parse.urlsplit(str(url or "")).hostname or "").lower().strip(".")
    except Exception:
        return ""
    return h[4:] if h.startswith("www.") else h

def _canon(v: Any) -> str:
    return " ".join(str(v or "").strip().split())

def _windows(text: str, limit: int = 160) -> list[str]:
    rows=[_canon(x) for x in _SENTENCE.split(_canon(text)) if _canon(x)]
    if not rows:
        return [_canon(text)] if _canon(text) else []
    out=[]
    for i in range(min(len(rows),limit)):
        for a,b in ((i,i+1),(max(0,i-1),min(len(rows),i+2))):
            w=" ".join(rows[a:b]).strip()
            if w and w not in out:
                out.append(w[:2400])
    return out

def _focus(query: str) -> list[str]:
    toks=_tokens(query)
    return toks[:20] if toks else [query]

def _candidate_replays_focus(answer: str, focus_terms: Sequence[str]) -> bool:
    ct=set(_tokens(answer))
    ft=set()
    for x in focus_terms:
        ft.update(_tokens(str(x)))
    return bool(ct) and bool(ft) and ct.issubset(ft)

def _title_slot_compatible(kind: str, title: str) -> bool:
    x=_canon(title)
    if not x or len(x)>100 or len(x.split())>10:
        return False
    low=x.casefold()
    if low.startswith(("list of ","category:","template:","portal:","outline of ")):
        return False
    if kind=="PERSON":
        parts=x.split()
        return 1 <= len(parts) <= 6 and any(ch.isupper() for ch in x)
    if kind in {"LOCATION","LOCATION_OR_ENTITY","WORK_TITLE","TERM","ENTITY_OR_TERM","SHORT_TEXT","RELATION_TERM"}:
        return 1 <= len(x.split()) <= 8
    if kind=="YEAR":
        return bool(re.fullmatch(r"(?:1[0-9]{3}|20[0-9]{2}|21[0-9]{2})",x))
    return False

def _coverage(focus_terms: Sequence[str], text: str) -> float:
    vals=[x.casefold() for x in focus_terms if str(x).strip()]
    if not vals:
        return 0.0
    low=_canon(text).casefold()
    return sum(1 for x in vals if x in low)/len(vals)

def propose(
    *,
    task_id: str,
    question: str,
    has_nonempty_image_payload: bool = False,
    rich_search_fn: Callable[..., list[dict[str,Any]]] = retrieval.rich_search,
    wiki_search_fn: Callable[..., list[dict[str,Any]]] = retrieval.wikipedia_search,
    wiki_extracts_fn: Callable[..., dict[int,str]] = retrieval.wikipedia_extracts,
    max_views: int = 4,
) -> dict[str,Any]:
    if not isinstance(task_id,str) or not task_id.strip():
        raise ValueError("TASK_ID_REQUIRED")
    if not isinstance(question,str) or not question.strip():
        raise ValueError("QUESTION_REQUIRED")
    if type(has_nonempty_image_payload) is not bool:
        raise ValueError("IMAGE_FLAG_INVALID")
    base={
        "schema":SCHEMA,"task_id":task_id,"question_sha256":_sha(question),
        "candidate_answer":None,"candidate_answer_authority":False,
        "correctness_claimed":False,"gold_accessed":False,
        "external_model_calls":0,"external_reasoning_model_calls":0,
        "model_dependency_count":0,"incremental_spend_usd":0,
        "terminal_authority":False,"terminal_credit_delta":0,
    }
    if has_nonempty_image_payload:
        return {**base,"status":"NO_CANDIDATE__IMAGE_SEMANTICS_REQUIRED_UPSTREAM"}

    contract=compile_question(task_id=task_id,question=question,has_nonempty_image_payload=False)
    if contract.get("pass") is not True:
        return {**base,"status":"NO_CANDIDATE__QUESTION_CONTRACT_UNRESOLVED"}
    kind=str(contract.get("question_kind") or "")
    if kind=="BARE_OPTION_LETTER":
        return {**base,"status":"NO_CANDIDATE__MCQ_DEFER_TO_MCQ_LANE","question_kind":kind}
    if kind in {"SYMBOLIC_OR_NUMBER","SYMBOLIC_EXPRESSION","NUMBER"}:
        return {**base,"status":"NO_CANDIDATE__SYMBOLIC_DEFER_TO_SYMBOLIC_LANE","question_kind":kind}
    if _NEG.search(question):
        return {**base,"status":"NO_CANDIDATE__NEGATIVE_POLARITY_NOT_IN_V4","question_kind":kind}

    views=list(contract.get("research_views") or [])[:max(1,min(int(max_views),6))]
    if not views:
        return {**base,"status":"NO_CANDIDATE__RESEARCH_VIEWS_EMPTY","question_kind":kind}

    evidence=[]
    wiki_pages: dict[int,dict[str,Any]]={}
    receipts=[]
    for vi,view in enumerate(views,1):
        query=str(view.get("query") or "").strip()
        if not query:
            continue
        try:
            rows=list(rich_search_fn(query,limit=8))
            rs="PASS"
        except Exception as exc:
            rows=[];rs="FAILED:"+type(exc).__name__
        receipts.append({"source":"BING_RSS","view":vi,"query_sha256":_sha(query),"status":rs,"result_count":len(rows)})
        for r in rows:
            url=str(r.get("url") or "")
            evidence.append({
                "source":"BING_RSS","source_key":"BING:"+url,"host":_host(url),
                "title":_canon(r.get("title")),"text":_canon(r.get("snippet")),
                "rank":int(r.get("rank") or 99),"view":vi,"query":query,
            })
        try:
            wrows=list(wiki_search_fn(query,limit=6))
            ws="PASS"
        except Exception as exc:
            wrows=[];ws="FAILED:"+type(exc).__name__
        receipts.append({"source":"WIKIPEDIA","view":vi,"query_sha256":_sha(query),"status":ws,"result_count":len(wrows)})
        for r in wrows:
            pid=int(r.get("pageid") or 0)
            if pid<=0:
                continue
            rec=wiki_pages.setdefault(pid,{
                "pageid":pid,"title":_canon(r.get("title")),"snippet":_canon(r.get("snippet")),
                "rank":int(r.get("rank") or 99),"views":set(),"queries":{},
            })
            rec["rank"]=min(rec["rank"],int(r.get("rank") or 99))
            rec["views"].add(vi);rec["queries"][vi]=query

    selected=sorted(wiki_pages.values(),key=lambda x:(x["rank"],-len(x["views"]),x["title"]))[:24]
    try:
        extracts=wiki_extracts_fn([x["pageid"] for x in selected]) if selected else {}
    except Exception:
        extracts={}
    for r in selected:
        for vi in sorted(r["views"]):
            evidence.append({
                "source":"WIKIPEDIA","source_key":"WIKI:"+str(r["pageid"]),"host":"wikipedia.org",
                "title":r["title"],"text":_canon(r["snippet"]+" "+str(extracts.get(r["pageid"],""))),
                "rank":r["rank"],"view":vi,"query":r["queries"].get(vi,""),
            })

    by_candidate: dict[str,dict[str,Any]]={}
    def add(answer: str, *, relation: str, coverage: float, ev: Mapping[str,Any], strong: bool) -> None:
        ans=_canon(answer).strip(" ,;:.()[]{}")
        if not ans or len(ans)>120 or len(ans.split())>10:
            return
        f=_focus(str(ev.get("query") or ""))
        if _candidate_replays_focus(ans,f):
            return
        key=ans.casefold()
        rec=by_candidate.setdefault(key,{
            "answer":ans,"sources":set(),"hosts":set(),"views":set(),"relations":set(),
            "strong_relations":0,"score":0.0,"best_coverage":0.0,
        })
        sk=str(ev.get("source_key") or "")
        if sk and sk not in rec["sources"]:
            rec["sources"].add(sk)
            rec["score"] += (3.0 if strong else 1.25) + coverage
        h=str(ev.get("host") or "")
        if h: rec["hosts"].add(h)
        rec["views"].add(int(ev.get("view") or 0))
        rec["relations"].add(relation)
        rec["best_coverage"]=max(rec["best_coverage"],coverage)
        if strong:
            rec["strong_relations"] += 1

    for ev in evidence:
        query=str(ev.get("query") or "")
        focus=_focus(query)
        text=_canon((str(ev.get("title") or "")+". "+str(ev.get("text") or "")).strip())
        for window in _windows(text):
            try:
                out=synthesize(contract={"kind":kind,"polarity":"POSITIVE"},focus_terms=focus,evidence=window)
            except Exception:
                continue
            if out.get("status")!="ONE_RELATION_BOUND_CANDIDATE":
                continue
            rows=out.get("candidates") or []
            if len(rows)!=1 or rows[0].get("support_authority") is not True:
                continue
            add(str(rows[0].get("answer") or ""),relation=str(out.get("relation_class") or "RELATION"),
                coverage=float(out.get("focus_coverage") or 0.0),ev=ev,strong=True)

        # Wikipedia page titles are useful only as a cross-query candidate and never
        # receive correctness authority on their own.
        if ev.get("source")=="WIKIPEDIA":
            title=str(ev.get("title") or "")
            cov=_coverage(focus,text)
            if int(ev.get("rank") or 99)<=3 and cov>=0.20 and _title_slot_compatible(kind,title):
                add(title,relation="WIKIPEDIA_TITLE_CROSS_QUERY",coverage=cov,ev=ev,strong=False)

    ranked=sorted(by_candidate.values(),key=lambda r:(
        -r["strong_relations"],-len(r["views"]),-len(r["sources"]),-r["score"],r["answer"].casefold()
    ))
    if not ranked:
        return {**base,"status":"NO_CANDIDATE__NO_TYPED_EVIDENCE","question_kind":kind,
                "research_view_count":len(views),"evidence_item_count":len(evidence),"query_receipts":receipts}
    best=ranked[0]; second=ranked[1] if len(ranked)>1 else None
    margin=best["score"]-(second["score"] if second else 0.0)
    accepted=(
        best["strong_relations"]>=1
        or (len(best["views"])>=2 and len(best["sources"])>=1 and best["score"]>=2.5)
        or (len(best["sources"])>=2 and best["score"]>=3.0 and margin>=0.25)
    )
    if not accepted:
        return {**base,"status":"NO_CANDIDATE__TYPED_EVIDENCE_BELOW_GATE","question_kind":kind,
                "research_view_count":len(views),"evidence_item_count":len(evidence),
                "candidate_count":len(ranked),"top_score":best["score"],"top_margin":margin,
                "top_view_count":len(best["views"]),"top_source_count":len(best["sources"]),
                "query_receipts":receipts}

    ans=best["answer"]
    return {
        **base,"status":"CANDIDATE_GENERATED__TYPED_MULTIQUERY_RESEARCH_V4",
        "question_kind":kind,"candidate_answer":ans,"candidate_answer_sha256":_sha(ans),
        "confidence_band":"HIGH" if best["strong_relations"]>=2 or len(best["views"])>=3 else "MEDIUM",
        "research_view_count":len(views),"evidence_item_count":len(evidence),
        "supporting_source_count":len(best["sources"]),"supporting_host_count":len(best["hosts"]),
        "supporting_view_count":len(best["views"]),"strong_relation_hits":best["strong_relations"],
        "relation_classes":sorted(best["relations"]),"support_score":best["score"],
        "top_margin":margin,"query_receipts":receipts,
        "hard_nonclaim":"TYPED_MULTIQUERY_PROPOSAL_IS_NOT_CORRECTNESS_OR_TARGET_SCORE_AUTHORITY",
    }

if __name__=="__main__":
    print("IMPORT_OK")
