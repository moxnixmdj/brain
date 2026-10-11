#!/usr/bin/env python3
"""Brain-native HLE research solver V5.

Successor to retired V4. Composition:
  question-contract V3
  -> bounded multi-query Bing/Wikipedia retrieval reused from open-domain V5
  -> case-safe typed relation synthesis V3
  -> cross-view Wikipedia-title consensus
  -> existing exact-retrieval V2 as an agreement/rescue lane only.

No external general-purpose model cognition, no gold, no correctness authority.
"""
from __future__ import annotations

import hashlib
import re
import urllib.parse
from collections import defaultdict
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.hle_native_question_contract_v3 import compile_question, v2
from canonical.runtime.hle_evidence_candidate_synthesis_v3 import synthesize
from canonical.runtime import hle_native_open_domain_research_v5 as retrieval

SCHEMA="PROJECT_BRAIN_HLE_NATIVE_RESEARCH_SOLVER_V5"
_SENTENCE=re.compile(r"(?<=[.!?;])\s+|\n+")
_NEG=re.compile(r"\b(?:not|never|except|excluding|incorrect|false|least likely|cannot|can't|doesn't|does not|isn't|is not)\b",re.I)

def _sha(v:str)->str:return hashlib.sha256(v.encode("utf-8")).hexdigest()
def _canon(v:Any)->str:return " ".join(str(v or "").strip().split())
def _tokens(v:str)->list[str]:return v2._tokens(v)

def _host(url:str)->str:
    try:h=(urllib.parse.urlsplit(str(url or "")).hostname or "").lower().strip(".")
    except Exception:return ""
    return h[4:] if h.startswith("www.") else h

def _windows(text:str,limit:int=180)->list[str]:
    rows=[_canon(x) for x in _SENTENCE.split(_canon(text)) if _canon(x)]
    out=[]
    for i in range(min(len(rows),limit)):
        for a,b in ((i,i+1),(max(0,i-1),min(len(rows),i+2))):
            w=" ".join(rows[a:b]).strip()
            if w and w not in out:out.append(w[:2400])
    return out

def _focus(query:str)->list[str]:
    x=_tokens(query)
    return x[:24] if x else [query]

def _focus_replay(candidate:str,focus_terms:Sequence[str])->bool:
    ct=set(_tokens(candidate));ft=set()
    for x in focus_terms:ft.update(_tokens(str(x)))
    return bool(ct) and bool(ft) and ct.issubset(ft)

def _slot_compatible(kind:str,subtype:str,title:str)->bool:
    x=_canon(title).strip(" ,;:.()[]{}")
    if not x or len(x)>120 or len(x.split())>12:return False
    low=x.casefold()
    if low.startswith(("list of ","category:","template:","portal:","outline of ","history of ")):return False
    words=x.split()
    if kind=="PERSON":
        if not (2<=len(words)<=6):return False
        particles={"de","del","da","di","la","le","van","von","of","the"}
        return sum(1 for w in words if w.casefold() not in particles and w[:1].isupper())>=2
    if kind=="YEAR":return bool(re.fullmatch(r"(?:1[0-9]{3}|20[0-9]{2}|21[0-9]{2})",x))
    if kind=="NUMBER":return bool(re.fullmatch(r"[-+]?\d+(?:\.\d+)?",x))
    if kind=="LOCATION":
        return len(words)<=7 and not any(z in low for z in ("disambiguation","geography of"))
    if kind=="WORK_TITLE":return len(words)<=11
    if kind in {"TERM","ENTITY_OR_TERM","SHORT_TEXT","OPEN_TEXT"}:return len(words)<=10
    if kind=="RELATION_TERM":return len(words)<=3
    return False

def _candidate_key(x:str)->str:
    return re.sub(r"[^a-z0-9]+"," ",_canon(x).casefold()).strip()

def propose(
    *,
    task_id:str,
    question:str,
    has_nonempty_image_payload:bool=False,
    rich_search_fn:Callable[...,list[dict[str,Any]]]=retrieval.rich_search,
    wiki_search_fn:Callable[...,list[dict[str,Any]]]=retrieval.wikipedia_search,
    wiki_extracts_fn:Callable[...,dict[int,str]]=retrieval.wikipedia_extracts,
    exact_retrieval_proposer:Callable[...,Mapping[str,Any]]|None=None,
    exact_search_fn:Callable[...,Mapping[str,Any]]|None=None,
    exact_fetch_fn:Callable[...,Mapping[str,Any]]|None=None,
    max_views:int=4,
)->dict[str,Any]:
    if not isinstance(task_id,str) or not task_id.strip():raise ValueError("TASK_ID_REQUIRED")
    if not isinstance(question,str) or not question.strip():raise ValueError("QUESTION_REQUIRED")
    if type(has_nonempty_image_payload) is not bool:raise ValueError("IMAGE_FLAG_INVALID")
    base={
      "schema":SCHEMA,"task_id":task_id,"question_sha256":_sha(question),
      "candidate_answer":None,"candidate_answer_authority":False,"correctness_claimed":False,
      "gold_accessed":False,"external_model_calls":0,"external_reasoning_model_calls":0,
      "model_dependency_count":0,"incremental_spend_usd":0,
      "terminal_authority":False,"terminal_credit_delta":0,
    }
    if has_nonempty_image_payload:return {**base,"status":"NO_CANDIDATE__IMAGE_SEMANTICS_REQUIRED_UPSTREAM"}
    if _NEG.search(question):return {**base,"status":"NO_CANDIDATE__NEGATIVE_POLARITY_NOT_IN_V5"}

    contract=compile_question(task_id=task_id,question=question,has_nonempty_image_payload=False)
    if contract.get("pass") is not True:return {**base,"status":"NO_CANDIDATE__QUESTION_CONTRACT_UNRESOLVED"}
    kind=str(contract.get("question_kind") or "")
    subtype=str(contract.get("answer_subtype") or kind)
    if kind=="BARE_OPTION_LETTER":return {**base,"status":"NO_CANDIDATE__MCQ_DEFER_TO_MCQ_LANE","question_kind":kind}
    if kind in {"SYMBOLIC_OR_NUMBER","SYMBOLIC_EXPRESSION","NUMBER"}:
        return {**base,"status":"NO_CANDIDATE__SYMBOLIC_DEFER_TO_SYMBOLIC_LANE","question_kind":kind}

    views=list(contract.get("research_views") or [])[:max(1,min(int(max_views),6))]
    evidence=[];wiki_pages={};receipts=[]
    for vi,view in enumerate(views,1):
        query=str(view.get("query") or "").strip()
        if not query:continue
        try: rows=list(rich_search_fn(query,limit=8)); rs="PASS"
        except Exception as exc: rows=[];rs="FAILED:"+type(exc).__name__
        receipts.append({"source":"BING_RSS","view":vi,"query_sha256":_sha(query),"status":rs,"result_count":len(rows)})
        for r in rows:
            url=str(r.get("url") or "")
            evidence.append({"source":"BING_RSS","source_key":"BING:"+url,"host":_host(url),
                             "title":_canon(r.get("title")),"text":_canon(r.get("snippet")),
                             "rank":int(r.get("rank") or 99),"view":vi,"query":query})
        try:wrows=list(wiki_search_fn(query,limit=8));ws="PASS"
        except Exception as exc:wrows=[];ws="FAILED:"+type(exc).__name__
        receipts.append({"source":"WIKIPEDIA","view":vi,"query_sha256":_sha(query),"status":ws,"result_count":len(wrows)})
        for r in wrows:
            pid=int(r.get("pageid") or 0)
            if pid<=0:continue
            rec=wiki_pages.setdefault(pid,{"pageid":pid,"title":_canon(r.get("title")),
                "snippet":_canon(r.get("snippet")),"rank":int(r.get("rank") or 99),
                "views":set(),"queries":{}})
            rec["rank"]=min(rec["rank"],int(r.get("rank") or 99));rec["views"].add(vi);rec["queries"][vi]=query

    selected=sorted(wiki_pages.values(),key=lambda x:(x["rank"],-len(x["views"]),x["title"]))[:28]
    try:extracts=wiki_extracts_fn([x["pageid"] for x in selected]) if selected else {}
    except Exception:extracts={}
    for r in selected:
        for vi in sorted(r["views"]):
            evidence.append({"source":"WIKIPEDIA","source_key":"WIKI:"+str(r["pageid"]),"host":"wikipedia.org",
                "title":r["title"],"text":_canon(r["snippet"]+" "+str(extracts.get(r["pageid"],""))),
                "rank":r["rank"],"view":vi,"query":r["queries"].get(vi,"")})

    by_candidate:dict[str,dict[str,Any]]={}
    def add(answer:str,relation:str,ev:Mapping[str,Any],strong:bool,coverage:float=0.0)->None:
        ans=_canon(answer).strip(" ,;:.()[]{}")
        if not _slot_compatible(kind,subtype,ans):return
        focus=_focus(str(ev.get("query") or ""))
        if _focus_replay(ans,focus):return
        key=_candidate_key(ans)
        if not key:return
        rec=by_candidate.setdefault(key,{"answer":ans,"views":set(),"sources":set(),"hosts":set(),
            "relations":set(),"strong_sources":set(),"score":0.0})
        src=str(ev.get("source_key") or "")
        if src and src not in rec["sources"]:
            rec["sources"].add(src);rec["score"]+=(4.0 if strong else 1.0)+coverage
        if strong and src:rec["strong_sources"].add(src)
        h=str(ev.get("host") or "")
        if h:rec["hosts"].add(h)
        rec["views"].add(int(ev.get("view") or 0));rec["relations"].add(relation)

    answer_contract=dict(contract.get("answer_contract") or {})
    answer_contract["polarity"]="POSITIVE"
    for ev in evidence:
        text=_canon(str(ev.get("title") or "")+". "+str(ev.get("text") or ""))
        focus=_focus(str(ev.get("query") or ""))
        for window in _windows(text):
            try:o=synthesize(contract=answer_contract,focus_terms=focus,evidence=window)
            except Exception:continue
            if o.get("status")!="ONE_RELATION_BOUND_CANDIDATE":continue
            rows=o.get("candidates") or []
            if len(rows)==1 and rows[0].get("support_authority") is True:
                add(str(rows[0].get("answer") or ""),str(o.get("relation_class") or "TYPED_RELATION"),
                    ev,True,float(o.get("focus_coverage") or 0.0))
        if ev.get("source")=="WIKIPEDIA" and int(ev.get("rank") or 99)<=5:
            add(str(ev.get("title") or ""),"WIKIPEDIA_TITLE_CROSS_VIEW",ev,False,0.0)

    ranked=sorted(by_candidate.values(),key=lambda r:(
        -len(r["strong_sources"]),-len(r["views"]),-len(r["sources"]),-r["score"],r["answer"].casefold()))
    chosen=None;chosen_reason=None
    for r in ranked:
        if len(r["strong_sources"])>=1:
            chosen=r;chosen_reason="CASE_SAFE_TYPED_RELATION";break
    if chosen is None:
        for r in ranked:
            if len(r["views"])>=2 and r["score"]>=2.0:
                chosen=r;chosen_reason="WIKIPEDIA_CROSS_VIEW_CONSENSUS";break

    exact_receipt=None
    if chosen is None and ranked:
        if exact_retrieval_proposer is None:
            from canonical.runtime.hle_exact_retrieval_extract_v2 import propose as exact_retrieval_proposer
        try:
            exact_receipt=dict(exact_retrieval_proposer(
                task_id=task_id,question=question,has_nonempty_image_payload=False,
                search_fn=exact_search_fn,fetch_fn=exact_fetch_fn))
        except Exception as exc:
            exact_receipt={"status":"LANE_EXCEPTION","error_class":type(exc).__name__,"candidate_answer":None,
                           "external_model_calls":0,"model_dependency_count":0,"gold_accessed":False}
        ext=int(exact_receipt.get("external_model_calls",0) or 0)
        dep=int(exact_receipt.get("model_dependency_count",0) or 0)
        ec=str(exact_receipt.get("candidate_answer") or "").strip()
        ek=_candidate_key(ec)
        if ext==0 and dep==0 and ec and ek in by_candidate and _slot_compatible(kind,subtype,ec):
            chosen=by_candidate[ek];chosen_reason="EXACT_RETRIEVAL_V2_AGREES_WITH_MULTIQUERY_CANDIDATE"

    if chosen is None:
        return {**base,"status":"NO_CANDIDATE__NO_CROSS_VALIDATED_TYPED_EVIDENCE",
            "question_kind":kind,"answer_subtype":subtype,"research_view_count":len(views),
            "evidence_item_count":len(evidence),"candidate_count":len(ranked),
            "exact_retrieval_status":exact_receipt.get("status") if exact_receipt else None,
            "query_receipts":receipts}

    ans=chosen["answer"]
    return {**base,"status":"CANDIDATE_GENERATED__CROSS_VALIDATED_RESEARCH_V5",
        "question_kind":kind,"answer_subtype":subtype,"candidate_answer":ans,
        "candidate_answer_sha256":_sha(ans),"selection_reason":chosen_reason,
        "research_view_count":len(views),"evidence_item_count":len(evidence),
        "supporting_view_count":len(chosen["views"]),"supporting_source_count":len(chosen["sources"]),
        "strong_relation_source_count":len(chosen["strong_sources"]),
        "relation_classes":sorted(chosen["relations"]),
        "exact_retrieval_status":exact_receipt.get("status") if exact_receipt else None,
        "query_receipts":receipts,
        "hard_nonclaim":"CROSS_VALIDATED_ZERO_MODEL_PROPOSAL_IS_NOT_CORRECTNESS_OR_TARGET_SCORE_AUTHORITY"}

if __name__=="__main__":print("IMPORT_OK")
