#!/usr/bin/env python3
"""Brain-native answer-blind retrieval query planner V2.

V2 preserves V1's high-precision entity/quoted seeds and adds only general
query-construction repairs learned from already-consumed public diagnostics:
normalized interrogative punctuation, ordinal/superlative preservation,
multiword-subject priority, slot-aware relation hints, and definition queries.

No answer key, model cognition, retrieval result, or correctness signal is used.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from canonical.runtime import hle_native_retrieval_query_planner_v1 as v1
from canonical.runtime.hle_native_question_contract_v3 import classify_answer_slot

SCHEMA="PROJECT_BRAIN_HLE_NATIVE_RETRIEVAL_QUERY_PLANNER_V2"

_PRESERVE={"first","second","third","last","largest","smallest","oldest","youngest","only","most","least"}
_ROLE={
 "artist","composer","author","writer","poet","mountaineer","president","scientist",
 "inventor","discoverer","explorer","actor","actress","governor","retailer","supermarket",
 "university","college","cocktail","dynasty","family","triangle","bone","film","movie",
 "opera","song","album","posters","peaks","assassinated","dropped","origin","capital",
}
_SLOT_HINTS={
 ("RELATION_TERM","KINSHIP_OR_RELATION"):["relationship","kinship"],
 ("LOCATION","COUNTRY"):["country","origin"],
 ("LOCATION","CITY"):["city"],
 ("LOCATION","REGION"):["region"],
 ("LOCATION","UNIVERSITY"):["university"],
 ("LOCATION","CAPITAL"):["capital"],
 ("TERM","TERM"):["term","definition"],
 ("ENTITY_OR_TERM","ENTITY_OR_TERM"):["name","term"],
}

def _canon(v:Any)->str:
    return " ".join(unicodedata.normalize("NFKC",str(v or "")).strip().split())

def _sha(v:str)->str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()

def _rank_proper(q:str)->list[str]:
    rows=v1._proper_seeds(q)
    ranked=sorted(
        enumerate(rows),
        key=lambda ix:(0 if len(ix[1].split())>=2 else 1,-len(ix[1].split()),ix[0])
    )
    return [x for _,x in ranked]

def _quoted(q:str)->list[str]:
    out=[]
    for raw in v1._QUOTED.findall(q):
        x=v1._clean_quoted(raw)
        if x and x.casefold() not in {z.casefold() for z in out}: out.append(x)
    return out

def _content_tokens(q:str)->list[str]:
    stop=set(v1._DROP)-_PRESERVE
    out=[]
    for raw in v1._WORD.findall(q):
        low=raw.casefold().strip("-/")
        if len(low)<2 or low in stop: continue
        if low not in {x.casefold() for x in out}: out.append(raw.strip("-/"))
    return out

def _relation_terms(q:str)->list[str]:
    out=[]
    for raw in v1._WORD.findall(q):
        low=raw.casefold().strip("-/")
        if low in v1._RELATIONS or low in _ROLE:
            if low not in out: out.append(low)
    return out

def _hints(kind:str,subtype:str)->list[str]:
    return list(_SLOT_HINTS.get((kind,subtype),[]))

def plan_queries(*,task_id:str,question:str,has_nonempty_image_payload:bool=False,max_views:int=8)->dict[str,Any]:
    if not isinstance(task_id,str) or not task_id.strip(): raise ValueError("TASK_ID_REQUIRED")
    if not isinstance(question,str) or not question.strip(): raise ValueError("QUESTION_REQUIRED")
    if type(has_nonempty_image_payload) is not bool: raise ValueError("IMAGE_FLAG_INVALID")
    max_views=max(1,min(int(max_views),12))

    slot=classify_answer_slot(question)
    normalized=_canon(slot.get("normalized_scope") or question)
    kind=str(slot.get("kind") or "OPEN_TEXT")
    subtype=str(slot.get("subtype") or kind)

    base=v1.plan_queries(
        task_id=task_id,
        question=normalized,
        has_nonempty_image_payload=has_nonempty_image_payload,
        max_views=10,
    )
    base_views=list(base.get("views") or [])
    quoted=_quoted(normalized)
    proper=_rank_proper(normalized)
    relations=_relation_terms(normalized)
    hints=_hints(kind,subtype)
    content=_content_tokens(normalized)

    raw=[]
    # Preserve the strongest V1 anchors before adding broader repaired views.
    for row in base_views:
        if row.get("method") in {"QUOTED_SEED","ENTITY_SEED"}:
            raw.append((str(row.get("method")),str(row.get("query") or "")))

    subject=(quoted[0] if quoted else (proper[0] if proper else ""))
    if subject:
        tail=[]
        for x in [*relations,*hints]:
            if x.casefold() not in {subject.casefold(),*(z.casefold() for z in tail)}:
                tail.append(x)
        if tail:
            raw.append(("SLOT_AWARE_SUBJECT_RELATION"," ".join([subject,*tail[:5]])))

    if len(proper)>=2:
        tail=[]
        for x in [*relations,*hints]:
            if x not in tail: tail.append(x)
        raw.append(("MULTI_ENTITY_RELATION"," ".join([proper[0],proper[1],*tail[:4]])))

    if content:
        raw.append(("DISCRIMINATIVE_ORDERED_CORE"," ".join(content[:12])))

    if kind in {"TERM","ENTITY_OR_TERM"} and content:
        raw.append(("DEFINITION_QUERY"," ".join([*content[:10],*hints[:2]])))

    # Finish with the remaining V1 views so V2 cannot silently discard V1 coverage.
    for row in base_views:
        raw.append((str(row.get("method") or "V1_VIEW"),str(row.get("query") or "")))

    out=[];seen=set();full=normalized.casefold()
    for method,query in raw:
        query=_canon(query)
        if not query or query.casefold()==full: continue
        key=query.casefold()
        if key in seen: continue
        seen.add(key)
        out.append({
            "method":method,
            "query":query,
            "query_sha256":_sha(query),
            "full_question_verbatim_used":False,
        })
        if len(out)>=max_views: break
    if not out: raise ValueError("QUERY_PLAN_EMPTY")

    return {
        "schema":SCHEMA,
        "status":"PLANNED__V1_ANCHORS_PLUS_NORMALIZED_SLOT_AWARE_REPAIRS",
        "task_id":task_id,
        "question_sha256":_sha(question),
        "normalized_question_sha256":_sha(normalized),
        "question_kind":kind,
        "answer_subtype":subtype,
        "views":out,
        "view_count":len(out),
        "gold_accessed":False,
        "external_model_calls":0,
        "external_reasoning_model_calls":0,
        "model_dependency_count":0,
        "candidate_answer_authority":False,
        "terminal_authority":False,
        "hard_rules":[
            "VISIBLE_QUESTION_ONLY",
            "V1_HIGH_PRECISION_ANCHORS_PRESERVED",
            "ORDINALS_AND_NUMERIC_CLUES_ARE_NOT_DROPPED_AS_GENERIC_STOPWORDS",
            "SLOT_HINTS_DESCRIBE_ANSWER_TYPE_NOT_ANSWER_VALUE",
            "NO_GOLD_RETRIEVAL_RESULT_OR_CORRECTNESS_SIGNAL_USED_IN_QUERY_PLANNING",
        ],
    }

if __name__=="__main__":
    cases=[
      ("Which. Martian city is named after the explorer Ada Example?",lambda qs:any("martian city" in q.casefold() for q in qs)),
      ("Which president was the first to be assassinated in Exampleland?",lambda qs:any("first" in q.casefold() and "president" in q.casefold() for q in qs)),
      ("Business magnate Alex Example dropped out of which university?",lambda qs:any("Alex Example" in q and "university" in q.casefold() for q in qs)),
      ("What relation was Napoleon Example to Joseph Example?",lambda qs:any("Napoleon Example" in q and "Joseph Example" in q and ("relation" in q.casefold() or "relationship" in q.casefold()) for q in qs)),
      ("What is the term for a triangle with two equal sides?",lambda qs:any("triangle" in q.casefold() and ("term" in q.casefold() or "definition" in q.casefold()) for q in qs)),
    ]
    for i,(q,pred) in enumerate(cases):
        x=plan_queries(task_id=str(i),question=q)
        qs=[v["query"] for v in x["views"]]
        assert pred(qs),(q,qs)
        assert not any(v["full_question_verbatim_used"] for v in x["views"])
        assert x["gold_accessed"] is False and x["external_model_calls"]==0
    print("SELF_TEST_PASS")
