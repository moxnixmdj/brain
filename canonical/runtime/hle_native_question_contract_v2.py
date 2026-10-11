#!/usr/bin/env python3
"""Brain-native HLE question contract V2.

V2 repairs interrogative-scope errors and compiles several answer-key-blind
research views for exact-match questions. It does not retrieve, solve, read
gold, call a model, or grant answer authority.
"""
from __future__ import annotations
import hashlib,re,unicodedata
from typing import Any
from canonical.runtime import hle_native_question_contract_v1 as v1

SCHEMA="PROJECT_BRAIN_HLE_NATIVE_QUESTION_CONTRACT_V2"
_WORD=re.compile(r"[^\W_]+(?:[-/][^\W_]+)*",re.UNICODE)
_QUOTED=re.compile(r'["“‘\']([^"”’\']{2,120})["”’\']')
_STOP=set(v1._STOP)|{"please","according","following","given","use","using"}
_PERSON_HEAD={"person","composer","author","artist","mountaineer","president","scientist","inventor","discoverer","explorer","actor","actress","writer","poet"}
_LOCATION_HEAD={"country","city","capital","region","place","location","state","province","island","university","college","continent"}
_TIME_HEAD={"year","date","month","day","century","decade"}
_WORK_HEAD={"film","movie","play","book","novel","opera","song","album","game","games","work","works"}
_TERM_HEAD={"name","term","relation","law","principle","theorem","compound","material","molecule","organism","species","gene","protein","enzyme","dynasty","family","cocktail","bone"}

def _canon(x:Any)->str:
    return " ".join(unicodedata.normalize("NFKC",str(x or "")).strip().split())
def _sha(x:str)->str:return hashlib.sha256(x.encode()).hexdigest()
def _tokens(x:str)->list[str]:
    out=[]
    for r in _WORD.findall(_canon(x)):
        t=r.casefold().strip("-/")
        if len(t)>=2 and t not in _STOP and t not in out:out.append(t)
    return out

def _tail(q:str)->str:
    c=_canon(q); parts=[x.strip() for x in re.split(r"(?<=[.!?])\s+",c) if x.strip()]
    return parts[-1] if parts else c

def _head_after_wh(tail:str)->str|None:
    m=re.match(r"^\s*(?:what|which)\s+([A-Za-z][A-Za-z-]*)\b",tail,re.I)
    return m.group(1).casefold() if m else None

def classify_answer_slot(question:str)->dict[str,Any]:
    t=_tail(question); low=t.casefold()
    # Only answer-bearing interrogatives control the slot. Relative-clause wh
    # words inside clues are deliberately ignored.
    if re.match(r"^\s*who\b",t,re.I): kind="PERSON"
    elif re.match(r"^\s*where\b",t,re.I): kind="LOCATION"
    elif re.match(r"^\s*when\b",t,re.I): kind="DATE_OR_TIME"
    elif re.search(r"\b(?:what|which)\s+year\b|\bin\s+(?:what|which)\s+year\b",t,re.I): kind="YEAR"
    elif re.search(r"\bhow\s+(?:many|much)\b",t,re.I): kind="NUMBER"
    elif re.match(r"^\s*what\s+relation\b",t,re.I): kind="RELATION_TERM"
    elif re.match(r"^\s*what\s+name\b",t,re.I) or re.search(r"\bname\s+(?:is\s+)?given\b",t,re.I): kind="TERM"
    else:
        head=_head_after_wh(t)
        if head in _PERSON_HEAD: kind="PERSON"
        elif head in _LOCATION_HEAD: kind="LOCATION"
        elif head in _TIME_HEAD: kind="YEAR" if head=="year" else "DATE_OR_TIME"
        elif head in _WORK_HEAD: kind="WORK_TITLE"
        elif head in _TERM_HEAD: kind="TERM"
        elif re.search(r"\b(?:from|in|at)\s+which\s+(?:[A-Za-z-]+\s+){0,2}(?:country|city|region|state|province|university|college)\b",t,re.I): kind="LOCATION"
        elif re.search(r"\bwhich\s+(?:composer|author|artist|mountaineer|president|scientist|inventor|explorer|actor|writer|poet)\b",t,re.I): kind="PERSON"
        elif re.match(r"^\s*(?:calculate|compute|evaluate|solve|derive)\b",t,re.I): kind="SYMBOLIC_OR_NUMBER"
        elif re.match(r"^\s*(?:what|which)\b",t,re.I): kind="SHORT_TEXT"
        elif re.match(r"^\s*(?:identify|name)\b",t,re.I): kind="ENTITY_OR_TERM"
        elif re.match(r"^\s*(?:is|are|was|were|does|do|did|can|could|has|have|had|will|would)\b",t,re.I): kind="BOOLEAN"
        else: kind="OPEN_TEXT"
    return {"kind":kind,"tail":t,"tail_sha256":_sha(t)}

def _dedupe_query(parts:list[str],full:str)->str|None:
    vals=[];seen=set()
    for p in parts:
        p=_canon(p)
        if not p:continue
        k=p.casefold()
        if k in seen:continue
        seen.add(k);vals.append(p)
    q=" ".join(vals[:30])
    if len(q)>600:q=q[:600].rsplit(" ",1)[0]
    if not q or q.casefold()==_canon(full).casefold():return None
    return q

def compile_research_views(question:str,slot_kind:str)->list[dict[str,Any]]:
    q=_canon(question); tail=_tail(q)
    quoted=[_canon(x) for x in _QUOTED.findall(q) if _canon(x)]
    toks=_tokens(q); tail_toks=_tokens(tail)
    rare=sorted(toks,key=lambda x:(-len(x),toks.index(x)))
    proper=[]
    for m in re.finditer(r"\b[A-Z][A-Za-z0-9'’.-]*(?:\s+(?:[A-Z][A-Za-z0-9'’.-]*|of|the|de|van|von)){0,5}",q):
        x=_canon(m.group(0))
        if x.casefold() not in {"what","which","who","where","when","how"} and x not in proper:proper.append(x)
    relation_tokens=[]
    for t in ["capital","born","composer","author","wrote","written","named","called","known","origin","dropped","university","first","largest","equal","identifier","film","song","cocktail","relation"]:
        if re.search(r"\b"+re.escape(t)+r"\b",q,re.I):relation_tokens.append(t)
    candidates=[
        ("QUOTED_ANCHORS",quoted[:2]+proper[:3]+rare[:8]),
        ("ASK_CLAUSE",tail_toks[:12]+proper[:3]),
        ("ENTITY_RELATION",proper[:4]+relation_tokens[:5]+rare[:8]),
        ("CONTENT_DISCRIMINATORS",rare[:16]),
    ]
    out=[];seen=set()
    for method,parts in candidates:
        query=_dedupe_query(parts,q)
        if not query or query.casefold() in seen:continue
        seen.add(query.casefold())
        out.append({"method":method,"query":query,"query_sha256":_sha(query),
                    "token_count":len(query.split()),"full_question_verbatim_used":False})
    if not out:
        raise ValueError("RESEARCH_VIEWS_EMPTY")
    return out

def compile_question(*,task_id:str,question:str,has_nonempty_image_payload:bool=False)->dict[str,Any]:
    if not isinstance(task_id,str) or not task_id.strip():raise ValueError("TASK_ID_REQUIRED")
    if not isinstance(question,str) or not question.strip():raise ValueError("QUESTION_REQUIRED")
    if type(has_nonempty_image_payload) is not bool:raise ValueError("IMAGE_FLAG_INVALID")
    if v1._MC_MARKER.search(question):
        old=v1.compile_question(task_id=task_id,question=question,has_nonempty_image_payload=has_nonempty_image_payload)
        old=dict(old);old["schema"]=SCHEMA;old["contract_version"]="V2_REUSES_VERIFIED_MCQ_V1"
        return old
    slot=classify_answer_slot(question)
    views=compile_research_views(question,slot["kind"])
    return {
        "schema":SCHEMA,"status":"COMPILED__ANSWER_SLOT_AND_MULTI_QUERY_RESEARCH_VIEWS",
        "pass":True,"task_id":task_id.strip(),"question_sha256":_sha(question),
        "question_kind":slot["kind"],"tail_clause_sha256":slot["tail_sha256"],
        "answer_contract":{"kind":slot["kind"],"format_authority":False},
        "research_views":views,"research_view_count":len(views),
        "has_nonempty_image_payload":has_nonempty_image_payload,
        "gold_accessed":False,"answer_type_metadata_consumed":False,
        "external_model_calls":0,"model_dependency_count":0,"incremental_spend_usd":0,
        "candidate_answer_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
        "hard_rules":[
          "RELATIVE_CLAUSE_INTERROGATIVES_DO_NOT_CONTROL_ANSWER_SLOT",
          "MULTI_QUERY_VIEWS_USE_VISIBLE_QUESTION_ONLY",
          "FULL_QUESTION_VERBATIM_SEARCH_IS_FORBIDDEN",
          "RESEARCH_VIEW_COMPILATION_HAS_ZERO_ANSWER_AUTHORITY"
        ]
    }
if __name__=="__main__":
    x=compile_question(task_id="s",question="Which Australian city is named after the Scotsman who was Governor?")
    assert x["question_kind"]=="LOCATION"
    assert x["research_view_count"]>=2
    print("SELF_TEST_PASS")
