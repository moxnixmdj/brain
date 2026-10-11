#!/usr/bin/env python3
"""Brain-native answer-blind retrieval query planner V1.

Purpose: retrieve the subject/evidence page before attempting answer extraction.
It emits short entity-seed, quoted-anchor, relation-pair, and ordered-core
queries from the visible question only. No gold, model call, or answer authority.
"""
from __future__ import annotations
import hashlib,re,unicodedata
from typing import Any

from canonical.runtime.hle_native_question_contract_v3 import compile_question

SCHEMA="PROJECT_BRAIN_HLE_NATIVE_RETRIEVAL_QUERY_PLANNER_V1"
_WORD=re.compile(r"[^\W_]+(?:[-/][^\W_]+)*",re.UNICODE)
_QUOTED=re.compile(r'["“‘\']([^"”’\']{2,160})["”’\']')
_PROPER=re.compile(
    r"\b[A-Z][A-Za-z0-9'’.-]*"
    r"(?:\s+(?:[A-Z][A-Za-z0-9'’.-]*|of|the|de|del|van|von|and)){0,6}"
)
_DROP={
 "what","which","who","where","when","how","in","according","sharing","business",
 "you","us","the","a","an","is","was","were","are","does","do","did","to","of",
 "for","from","with","by","on","at","as","its","this","that","these","those",
 "name","given","called","known","most","famous","first",
}
_RELATIONS={
 "capital","origin","born","birth","composer","author","wrote","written","play","film",
 "movie","opera","song","album","game","games","cocktail","university","college",
 "region","country","city","relation","daughter","son","nephew","niece","equal",
 "equals","identifier","posters","produced","dynasty","triangle","sides","angles",
 "assassinated","dropped","mountaineer","peaks","pelvis","bone","sugar","dextrose",
}

def _canon(v:Any)->str:return " ".join(unicodedata.normalize("NFKC",str(v or "")).strip().split())
def _sha(v:str)->str:return hashlib.sha256(v.encode()).hexdigest()
def _tokens(v:str)->list[str]:
    out=[]
    for raw in _WORD.findall(_canon(v)):
        x=raw.casefold().strip("-/")
        if len(x)>=2 and x not in out:out.append(x)
    return out

def _clean_seed(x:str)->str|None:
    x=_canon(x).strip(" ,;:.()[]{}")
    if not x:return None
    toks=x.split()
    while toks and toks[0].casefold() in _DROP:toks.pop(0)
    while toks and toks[-1].casefold() in _DROP:toks.pop()
    x=" ".join(toks)
    if not x or len(x)>120 or len(x.split())>7:return None
    if x.casefold() in _DROP:return None
    return x

def _clean_quoted(x:str)->str|None:
    # Quoted spans are entity/title candidates. Their leading words can be
    # semantically essential ("When You Wish Upon a Star"), so never apply the
    # interrogative/function-word stripping used for ordinary question text.
    x=_canon(x).strip(" ,;:.()[]{}")
    if not x or len(x)>160 or len(x.split())>14:return None
    return x

def _proper_seeds(q:str)->list[str]:
    out=[]
    for m in _PROPER.finditer(q):
        x=_clean_seed(m.group(0))
        if not x:continue
        # Require either a multiword name, an acronym/code, or a non-generic
        # single capitalized token. Sentence-initial glue is removed above.
        if len(x.split())==1 and x.casefold() in {"french","german","australian","mississippi","japan"}:
            continue
        if x.casefold() not in {z.casefold() for z in out}:out.append(x)
    return out

def _ordered_core(q:str,limit:int=9)->str:
    vals=[]
    for raw in _WORD.findall(q):
        x=raw.casefold().strip("-/")
        if len(x)<2 or x in _DROP:continue
        if x not in vals:vals.append(x)
    return " ".join(vals[:limit])

def plan_queries(*,task_id:str,question:str,has_nonempty_image_payload:bool=False,max_views:int=7)->dict[str,Any]:
    if not isinstance(task_id,str) or not task_id.strip():raise ValueError("TASK_ID_REQUIRED")
    if not isinstance(question,str) or not question.strip():raise ValueError("QUESTION_REQUIRED")
    if type(has_nonempty_image_payload) is not bool:raise ValueError("IMAGE_FLAG_INVALID")
    contract=compile_question(task_id=task_id,question=question,has_nonempty_image_payload=has_nonempty_image_payload)
    q=_canon(question)
    quoted=[]
    for raw in _QUOTED.findall(q):
        x=_clean_quoted(raw)
        if x and x.casefold() not in {z.casefold() for z in quoted}:quoted.append(x)
    proper=_proper_seeds(q)
    rel=[x for x in _tokens(q) if x in _RELATIONS]
    core=_ordered_core(q)

    raw=[]
    # The shortest, highest-precision seeds go first.
    for x in quoted[:2]:raw.append(("QUOTED_SEED",x))
    for x in proper[:3]:raw.append(("ENTITY_SEED",x))
    if len(proper)>=2:raw.append(("ENTITY_PAIR"," ".join(proper[:2])))
    if proper:
        rr=" ".join([proper[0]]+rel[:3])
        raw.append(("ENTITY_RELATION",rr))
    if quoted and rel:
        raw.append(("QUOTED_RELATION"," ".join([quoted[0]]+rel[:3])))
    if core:raw.append(("ORDERED_CORE",core))
    # A compact relation core is useful when there are no named entities.
    relcore=[]
    for x in _tokens(q):
        if x in _RELATIONS or len(x)>=7:
            if x not in relcore:relcore.append(x)
    if relcore:raw.append(("RELATION_CORE"," ".join(relcore[:8])))

    out=[];seen=set()
    full=q.casefold()
    for method,query in raw:
        query=_canon(query)
        if not query or query.casefold()==full:continue
        k=query.casefold()
        if k in seen:continue
        seen.add(k)
        out.append({"method":method,"query":query,"query_sha256":_sha(query),
                    "full_question_verbatim_used":False})
        if len(out)>=max(1,min(int(max_views),10)):break
    if not out:raise ValueError("QUERY_PLAN_EMPTY")
    return {
      "schema":SCHEMA,"status":"PLANNED__SHORT_SEEDS_AND_ORDERED_CORE","task_id":task_id,
      "question_sha256":_sha(question),"question_kind":contract.get("question_kind"),
      "answer_subtype":contract.get("answer_subtype"),"views":out,"view_count":len(out),
      "gold_accessed":False,"external_model_calls":0,"external_reasoning_model_calls":0,
      "model_dependency_count":0,"candidate_answer_authority":False,"terminal_authority":False,
      "hard_nonclaim":"QUERY_PLANNING_HAS_ZERO_ANSWER_OR_CORRECTNESS_AUTHORITY"
    }

if __name__=="__main__":
    qs=[
      ("What is the capital of the Dominican Republic?","Dominican Republic"),
      ("What is the country of origin of the supermarket chain Aldi?","Aldi"),
      ("William the Conqueror came from which French region?","William the Conqueror"),
      ("Which composer wrote the operas 'Lohengrin' and 'Tannhauser'?","Lohengrin"),
      ("In which Walt Disney film does the song 'When You Wish Upon a Star' appear?","When You Wish Upon a Star"),
    ]
    for i,(q,needle) in enumerate(qs):
        x=plan_queries(task_id=str(i),question=q)
        assert any(needle.casefold() in v["query"].casefold() for v in x["views"]),(q,x)
    print("SELF_TEST_PASS")
