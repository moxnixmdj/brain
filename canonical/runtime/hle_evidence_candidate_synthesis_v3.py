#!/usr/bin/env python3
"""Brain-native case-safe typed evidence synthesis V3.

V3 removes V2's principal false-positive mechanism: case-insensitive matching
no longer applies to entity captures. Function words are matched case
insensitively in scoped groups while PERSON/LOCATION/WORK_TITLE captures retain
case structure. Demonym->country is restricted to country-answer contracts.
No model calls, no gold, no correctness authority.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_HLE_EVIDENCE_CANDIDATE_SYNTHESIS_V3"
_WORD=re.compile(r"[^\W_]+(?:[-/][^\W_]+)*",re.UNICODE)
_PERSON=(
    r"(?:(?:Dr|Prof|Professor|Sir|Dame|Saint|St)\.?\s+)?"
    r"[A-Z][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]+"
    r"(?:\s+(?:(?:de|del|da|di|la|le|van|von|of|the)\s+)?"
    r"[A-Z][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]+){0,5}"
)
_LOC=(
    r"[A-Z][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]+"
    r"(?:\s+(?:[A-Z][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]+|of|the|de|la|New|North|South|East|West)){0,6}"
)
_TITLE=(
    # Do not admit a sentence-ending period inside a title token. Otherwise
    # the previous sentence's final proper noun can fuse with the next title.
    r"[A-Z][A-Za-z0-9'’:&-]+"
    r"(?:\s+(?:[A-Z][A-Za-z0-9'’:&-]+|for|of|the|and|a|an|to|in|on)){0,10}"
)
_KINSHIP="nephew|niece|son|daughter|brother|sister|uncle|aunt|grandson|granddaughter|grandfather|grandmother|cousin|husband|wife"
_DEMONYM={
    "german":"Germany","french":"France","italian":"Italy","spanish":"Spain",
    "japanese":"Japan","chinese":"China","canadian":"Canada","australian":"Australia",
    "american":"United States","british":"United Kingdom","english":"United Kingdom",
    "scottish":"Scotland","irish":"Ireland","dutch":"Netherlands","swedish":"Sweden",
    "norwegian":"Norway","danish":"Denmark","finnish":"Finland","swiss":"Switzerland",
    "austrian":"Austria","belgian":"Belgium","greek":"Greece","portuguese":"Portugal",
    "russian":"Russia","indian":"India","brazilian":"Brazil","mexican":"Mexico",
}

def _canon(v:Any)->str:
    return " ".join(unicodedata.normalize("NFKC",str(v or "")).strip().split())

def _sha(v:str)->str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()

def _tokens(v:str)->list[str]:
    out=[]
    for x in _WORD.findall(_canon(v)):
        t=x.casefold().strip("-/")
        if len(t)>=2 and t not in out: out.append(t)
    return out

def _anchors(focus_terms:Sequence[str],evidence:str)->tuple[list[str],float]:
    vals=[]
    for raw in focus_terms:
        vals.extend(_tokens(str(raw)))
    vals=list(dict.fromkeys(vals))
    low=_canon(evidence).casefold()
    matched=[x for x in vals if re.search(r"(?<!\w)"+re.escape(x)+r"(?!\w)",low)]
    return matched,(len(matched)/len(vals) if vals else 0.0)

def _focus_replay(answer:str,focus_terms:Sequence[str])->bool:
    ct=set(_tokens(answer)); ft=set()
    for x in focus_terms: ft.update(_tokens(str(x)))
    return bool(ct) and bool(ft) and ct.issubset(ft)

def _clean(v:str)->str|None:
    x=_canon(v).strip(" \t\r\n,;:.()[]{}\"'“”‘’")
    if not x or len(x)>140 or len(x.split())>12:return None
    return x

def _emit(out:list[tuple[str,str]],raw:str,relation:str,focus_terms:Sequence[str])->None:
    x=_clean(raw)
    if not x or _focus_replay(x,focus_terms):return
    if x.casefold() not in {a.casefold() for a,_ in out}:out.append((x,relation))

def _case_safe_person(text:str,focus_terms:Sequence[str])->list[tuple[str,str]]:
    out=[]
    pats=[
      r"\b(?i:written|composed|created|painted|founded|invented|discovered|directed|performed|recorded)\s+by\s+("+_PERSON+r")",
      r"\b("+_PERSON+r")\s+(?i:wrote|composed|created|painted|founded|invented|discovered|directed|performed|recorded)\b",
      r"\b("+_PERSON+r")\s+(?i:was|is)\s+(?:(?i:the|a|an)\s+)?(?i:composer|author|artist|mountaineer|president|inventor|discoverer|explorer|writer|poet|actor|actress)\b",
      r"\b("+_PERSON+r")\s+(?i:was|is)\s+(?i:the)\s+(?i:first)\s+(?i:person|man|woman|mountaineer|president|explorer|inventor|discoverer)\b",
      r"\b("+_PERSON+r")\s+(?i:was|is)\s+(?:(?i:the|a|an)\s+)?(?i:"+_KINSHIP+r")\s+(?i:of)\b",
      r"\b(?i:first)\s+(?i:person|man|woman|mountaineer|president|explorer)\s+[^.;]{0,90}?\b(?i:was|is)\s+("+_PERSON+r")",
    ]
    for p in pats:
        for m in re.finditer(p,text):
            _emit(out,m.group(1),"CASE_SAFE_PERSON_RELATION",focus_terms)
    return out

def _case_safe_location(text:str,focus_terms:Sequence[str],subtype:str)->list[tuple[str,str]]:
    out=[]
    pats=[
      r"\b(?i:capital)(?:\s+(?i:and largest city))?\s+(?i:of)\s+[^,.;]{1,80}?\s+(?i:is|was)\s+("+_LOC+r")(?=[,.;]|$)",
      r"\b("+_LOC+r")\s+(?i:is|was)\s+(?i:the)\s+(?i:capital)\s+(?i:of)\b",
      r"\b(?i:born)\s+(?:\w+\s+){0,5}?(?i:in|at)\s+("+_LOC+r")(?=[,.;]|$)",
      r"\b(?i:came|comes|originated|originates)\s+(?i:from)\s+("+_LOC+r")(?=[,.;]|$)",
    ]
    if subtype in {"REGION","LOCATION","CITY","UNIVERSITY"}:
        pats.append(r"\b(?i:from)\s+("+_LOC+r")(?=[,.;]|$)")
    for p in pats:
        for m in re.finditer(p,text):
            _emit(out,m.group(1),"CASE_SAFE_LOCATION_RELATION",focus_terms)
    if subtype=="COUNTRY":
        low=text.casefold()
        for dem,country in _DEMONYM.items():
            if re.search(r"\b"+re.escape(dem)+r"\b",low):
                _emit(out,country,"COUNTRY_DEMONYM_RELATION",focus_terms)
    return out

def _case_safe_work(text:str,focus_terms:Sequence[str])->list[tuple[str,str]]:
    out=[]
    pats=[
      r"\b("+_TITLE+r")\s+(?i:is|was)\s+(?:(?i:a|an|the)\s+)?(?i:play|film|movie|opera|novel|book|song|album|game)\b",
      r"\b(?i:play|film|movie|opera|novel|book|song|album|game)\s+(?:titled\s+)?("+_TITLE+r")(?=[,.;]|$)",
      r"\b(?i:film|movie)\s+(?:(?i:adaptation)\s+(?i:of)\s+)?("+_TITLE+r")(?=[,.;]|$)",
      r"\b(?i:appears|featured|features)\s+(?i:in)\s+(?:(?i:the)\s+)?(?:(?i:film|movie|play)\s+)?("+_TITLE+r")(?=[,.;]|$)",
    ]
    for p in pats:
        for m in re.finditer(p,text):
            _emit(out,m.group(1),"CASE_SAFE_WORK_RELATION",focus_terms)
    return out

def _term(text:str,focus_terms:Sequence[str])->list[tuple[str,str]]:
    out=[]
    pats=[
      r"\b(?i:also known as|known as|called|termed|designated|named)\s+(?:(?i:a|an|the)\s+)?([^,.;]{1,90})(?=[,.;]|$)",
      r"\b(?i:means|equals|equal to|gives)\s+(?:(?i:the)\s+)?([^,.;]{1,70})(?=[,.;]|$)",
    ]
    for p in pats:
        for m in re.finditer(p,text):
            _emit(out,m.group(1),"EXPLICIT_TERM_RELATION",focus_terms)
    return out

def synthesize(*,contract:Mapping[str,Any],focus_terms:Sequence[str],evidence:str)->dict[str,Any]:
    if not isinstance(contract,Mapping):raise ValueError("CONTRACT_REQUIRED")
    kind=str(contract.get("kind") or "").upper()
    subtype=str(contract.get("subtype") or kind).upper()
    polarity=str(contract.get("polarity") or "POSITIVE").upper()
    matched,coverage=_anchors(focus_terms,evidence)
    base={
      "schema":SCHEMA,"kind":kind,"subtype":subtype,"polarity":polarity,
      "evidence_sha256":_sha(evidence),"matched_focus_terms":matched,"focus_coverage":coverage,
      "candidate_answer_authority":False,"semantic_truth_authority":False,
      "gold_accessed":False,"external_model_calls":0,"external_reasoning_model_calls":0,
      "model_dependency_count":0,"incremental_spend_usd":0,
      "terminal_authority":False,"terminal_credit_delta":0,
    }
    if polarity!="POSITIVE":return {**base,"status":"NO_CANDIDATE__NONPOSITIVE_POLARITY","candidates":[]}
    if not matched:return {**base,"status":"NO_CANDIDATE__NO_OBJECTIVE_ANCHOR","candidates":[]}

    text=_canon(evidence)
    if kind=="PERSON": rows=_case_safe_person(text,focus_terms)
    elif kind=="LOCATION": rows=_case_safe_location(text,focus_terms,subtype)
    elif kind=="WORK_TITLE": rows=_case_safe_work(text,focus_terms)
    elif kind=="RELATION_TERM":
        rows=[]
        for m in re.finditer(r"\b(?i:was|is)\s+(?:(?i:the)\s+)?("+_KINSHIP+r")\s+(?i:of)\b",text):
            _emit(rows,m.group(1),"EXPLICIT_KINSHIP_RELATION",focus_terms)
    elif kind in {"TERM","ENTITY_OR_TERM"}: rows=_term(text,focus_terms)
    else: rows=[]

    if len(rows)!=1:
        return {**base,"status":"NO_CANDIDATE__RELATION_ABSENT_OR_AMBIGUOUS","candidates":[],
                "raw_candidate_count":len(rows),"relation_classes_seen":sorted({r for _,r in rows})}
    answer,relation=rows[0]
    return {**base,"status":"ONE_RELATION_BOUND_CANDIDATE","relation_class":relation,
            "candidates":[{"answer":answer,"answer_sha256":_sha(answer),"relation":"SUPPORTS",
                           "support_authority":True,"correctness_authority":False}],
            "hard_nonclaim":"CASE_SAFE_TYPED_RELATION_IS_A_PROPOSAL_NOT_CORRECTNESS_AUTHORITY"}

if __name__=="__main__":
    tests=[
      ({"kind":"PERSON","subtype":"PERSON"},["operas"],"The operas were composed by Richard Example.","Richard Example"),
      ({"kind":"LOCATION","subtype":"CAPITAL"},["fictionland","capital"],"The capital of Fictionland is Nova City.","Nova City"),
      ({"kind":"LOCATION","subtype":"COUNTRY"},["country","origin"],"ExampleCo is a German retailer.","Germany"),
      ({"kind":"WORK_TITLE","subtype":"WORK_TITLE"},["shakespeare","play"],"Measure for Example is a play by William Example.","Measure for Example"),
    ]
    for c,f,e,a in tests:
      x=synthesize(contract=c,focus_terms=f,evidence=e)
      assert x["candidates"][0]["answer"]==a,(x,a)
    print("SELF_TEST_PASS")
