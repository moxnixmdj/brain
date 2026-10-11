#!/usr/bin/env python3
"""Answer-blind relation requirement compiler for factual research V1.

This module repairs the seam between question understanding and retrieval. It
does not retrieve, answer, score, or inspect gold. It emits a bounded set of
relation-preserving search requirements from the visible question only.

The compiler is deliberately additive: callers should compose these bridge
queries with an already-verified baseline planner rather than replace baseline
queries. That prevents a new semantic view from silently deleting old recall.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any

from canonical.runtime.hle_native_question_contract_v3 import classify_answer_slot

SCHEMA="PROJECT_BRAIN_HLE_RELATION_REQUIREMENT_COMPILER_V1"

_WORD=re.compile(r"[^\W_]+(?:[-/][^\W_]+)*",re.UNICODE)
_QUOTED=re.compile(r'["“‘\']([^"”’\']{2,180})["”’\']')
_PROPER=re.compile(
    r"\b[A-Z][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]*"
    r"(?:\s+(?:[A-Z][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.-]*|of|the|de|del|da|di|la|le|van|von)){0,6}"
)

_GENERIC_PROPER={
    "what","which","who","where","when","how",
    "business","according","following","given","american","australian","british",
    "french","german","italian","spanish","japanese","chinese","canadian",
}
_STOP={
    "what","which","who","where","when","how","is","was","were","are","be","been",
    "a","an","the","of","to","and","or","for","from","with","by","on","at","as",
    "this","that","these","those","does","do","did","has","have","had","its",
    "according","following","given","name","named","called","known",
}
_ROLE_WORDS={
    "artist","composer","author","writer","poet","mountaineer","president","scientist",
    "inventor","discoverer","explorer","actor","actress","governor","magnate","retailer",
    "city","country","region","state","university","college","dynasty","family","cocktail",
    "bone","film","movie","opera","song","album","game","triangle","peaks","poster","posters",
}
_RELATION_WORDS={
    "relation","related","kinship","nephew","niece","son","daughter","brother","sister",
    "uncle","aunt","cousin","husband","wife","named","after","dropped","university",
    "first","assassinated","climbed","peaks","produced","posters","known","called",
    "dynasty","family","equal","sides","angles","largest","bone","pelvis","sharing",
    "origin","capital","born","composer","author","wrote","film","song",
}

def _canon(v:Any)->str:
    return " ".join(unicodedata.normalize("NFKC",str(v or "")).strip().split())

def _sha(v:str)->str:
    return hashlib.sha256(v.encode("utf-8")).hexdigest()

def _tokens(v:str)->list[str]:
    out=[]
    for raw in _WORD.findall(_canon(v)):
        x=raw.casefold().strip("-/")
        if len(x)>=2 and x not in out:
            out.append(x)
    return out

def _quoted(v:str)->list[str]:
    out=[]
    for raw in _QUOTED.findall(_canon(v)):
        x=_canon(raw).strip(" ,;:.()[]{}")
        if x and x.casefold() not in {z.casefold() for z in out}:
            out.append(x)
    return out

def _proper_spans(v:str)->list[str]:
    out=[]
    for m in _PROPER.finditer(_canon(v)):
        x=_canon(m.group(0)).strip(" ,;:.()[]{}")
        if not x:
            continue
        toks=x.split()
        while toks and toks[0].casefold() in _GENERIC_PROPER:
            toks.pop(0)
        x=" ".join(toks)
        if not x:
            continue
        if len(x.split())==1 and x.casefold() in _GENERIC_PROPER:
            continue
        if x.casefold() not in {z.casefold() for z in out}:
            out.append(x)
    # Prefer informative multiword entities, but retain stable source order.
    return sorted(enumerate(out),key=lambda ix:(0 if len(ix[1].split())>=2 else 1,ix[0]))

def _proper(v:str)->list[str]:
    return [x for _,x in _proper_spans(v)]

def _discriminators(v:str,limit:int=12)->list[str]:
    out=[]
    for x in _tokens(v):
        if x in _STOP:
            continue
        if x not in out:
            out.append(x)
    return out[:limit]

def _rel_terms(v:str)->list[str]:
    return [x for x in _tokens(v) if x in _RELATION_WORDS or x in _ROLE_WORDS]

def _quote(x:str)->str:
    x=_canon(x).replace('"',"")
    return f'"{x}"' if " " in x else x

def _add(out:list[dict[str,Any]],method:str,parts:list[str],relation_type:str)->None:
    vals=[]; seen=set()
    for raw in parts:
        x=_canon(raw)
        if not x:
            continue
        k=x.casefold()
        if k in seen:
            continue
        seen.add(k); vals.append(x)
    q=" ".join(vals)
    if not q or len(q)>700:
        return
    if q.casefold() in {str(x["query"]).casefold() for x in out}:
        return
    out.append({
        "method":method,
        "relation_type":relation_type,
        "query":q,
        "query_sha256":_sha(q),
        "full_question_verbatim_used":False,
        "answer_value_inferred":False,
    })

def compile_requirements(*,task_id:str,question:str,max_queries:int=8)->dict[str,Any]:
    if not isinstance(task_id,str) or not task_id.strip():
        raise ValueError("TASK_ID_REQUIRED")
    if not isinstance(question,str) or not question.strip():
        raise ValueError("QUESTION_REQUIRED")
    max_queries=max(1,min(int(max_queries),12))

    slot=classify_answer_slot(question)
    raw_q=_canon(question)
    raw_low=raw_q.casefold()
    q=_canon(slot.get("normalized_scope") or question)
    low=q.casefold()
    kind=str(slot.get("kind") or "OPEN_TEXT")
    subtype=str(slot.get("subtype") or kind)
    proper=_proper(q)
    quoted=_quoted(q)
    discr=_discriminators(q)
    rel=_rel_terms(q)
    out=[]

    # Explicit pairwise relation / kinship. Preserve both named entities.
    if subtype=="KINSHIP_OR_RELATION" or re.search(r"\b(?:relation|related)\b",low):
        if len(proper)>=2:
            _add(out,"PAIRWISE_RELATION",[_quote(proper[0]),_quote(proper[1]),"relationship kinship relation"],"PAIRWISE_RELATION")
            _add(out,"PAIRWISE_FAMILY_RELATION",[_quote(proper[0]),_quote(proper[1]),"family nephew niece son daughter cousin"],"KINSHIP")

    # Institution relation: preserve the full subject and the actual relation
    # phrase instead of reducing a person to a first name.
    if subtype=="UNIVERSITY" or ("drop" in low and ("university" in low or "college" in low)):
        if proper:
            _add(out,"SUBJECT_INSTITUTION_RELATION",[_quote(proper[0]),'"dropped out"',"university college"],"EDUCATION_INSTITUTION")

    # Named-after relation. Search the predicate as a relation, not keyword soup.
    if "named after" in low:
        anchors=[_quote(x) for x in proper[:3]]
        _add(out,"NAMED_AFTER_RELATION",anchors+['"named after"']+[x for x in rel if x not in {"named","after"}][:3],"NAMED_AFTER")

    # Ordinal identity questions need the ordinal to stay bound to the role.
    if kind=="PERSON" and re.search(r"\bfirst\b",low):
        roles=[x for x in rel if x in _ROLE_WORDS or x in {"assassinated","climbed","peaks"}]
        _add(out,"ORDINAL_PERSON_IDENTITY",['"first '+(roles[0] if roles else "person")+'"']+roles[1:5]+discr[:8],"ORDINAL_IDENTITY")

    # Descriptive person identity: preserve named anchors plus high-value
    # predicate words such as produced/posters, mountaineer/peaks, etc.
    if kind=="PERSON":
        anchors=[_quote(x) for x in quoted[:2]+proper[:3]]
        if anchors or rel:
            _add(out,"DESCRIPTIVE_PERSON_IDENTITY",anchors+rel[:6]+discr[:10],"DESCRIPTIVE_IDENTITY")

    # Definition/name questions: turn the visible descriptive clause into a
    # definition lookup. This is intentionally generic and answer-blind.
    definition_intent = kind in {"TERM","ENTITY_OR_TERM"} or bool(re.search(r"\\bterm\\b|\\bcalled\\b|\\bwhat name\\b",raw_low))
    if definition_intent:
        definition=[x for x in _discriminators(raw_q) if x not in {"term","name"}]
        _add(out,"DEFINITION_RELATION",definition[:12]+["called term definition"],"DEFINITION")
        if quoted or proper:
            _add(out,"ALIAS_ENTITY_RELATION",[_quote(x) for x in quoted[:2]+proper[:3]]+rel[:5]+["known as called"],"ALIAS_OR_NAME")

    # Shared-name / lexical clue relation.
    if re.search(r"\b(?:sharing|shares|same)\b.{0,50}\bname\b|\bnamed?\s+like\b",low):
        _add(out,"SHARED_NAME_RELATION",[_quote(x) for x in quoted[:2]+proper[:3]]+discr[:10]+["same name also called"],"NAME_SHARING")

    # Generic relation-preserving fallback. It deliberately keeps role/predicate
    # terms next to the best entity anchors.
    anchors=[_quote(x) for x in quoted[:2]+proper[:3]]
    if anchors and rel:
        _add(out,"ENTITY_PREDICATE_BRIDGE",anchors+rel[:7],"ENTITY_PREDICATE")

    out=out[:max_queries]
    return {
        "schema":SCHEMA,
        "status":"COMPILED__ANSWER_BLIND_RELATION_REQUIREMENTS" if out else "NO_BOUNDED_RELATION_REQUIREMENT",
        "task_id":task_id,
        "question_sha256":_sha(question),
        "question_kind":kind,
        "answer_subtype":subtype,
        "requirements":out,
        "requirement_count":len(out),
        "gold_accessed":False,
        "answer_value_accessed":False,
        "external_model_calls":0,
        "external_reasoning_model_calls":0,
        "model_dependency_count":0,
        "candidate_answer_authority":False,
        "correctness_authority":False,
        "terminal_authority":False,
        "incremental_spend_usd":0,
        "hard_rules":[
            "VISIBLE_QUESTION_ONLY",
            "NO_GOLD_OR_ANSWER_METADATA",
            "RELATION_QUERIES_ARE_ADDITIVE_TO_BASELINE_NOT_REPLACEMENTS",
            "FULL_QUESTION_VERBATIM_SEARCH_IS_FORBIDDEN",
            "QUERY_REQUIREMENTS_HAVE_ZERO_ANSWER_OR_CORRECTNESS_AUTHORITY",
        ],
    }

if __name__=="__main__":
    cases=[
      ("What relation was Emperor Alpha to Emperor Beta?", "PAIRWISE_RELATION"),
      ("Business magnate Ada Example dropped out of which university?", "SUBJECT_INSTITUTION_RELATION"),
      ("Which president was the first to be assassinated in Exampleland?", "ORDINAL_PERSON_IDENTITY"),
      ("What is the term for a triangle with two equal sides?", "DEFINITION_RELATION"),
      ("Which city was named after the explorer Rowan Example?", "NAMED_AFTER_RELATION"),
      ("Which artist famously produced posters for the Red Windmill?", "DESCRIPTIVE_PERSON_IDENTITY"),
      ("Which dynasty, known as the Iron House, was based in Exampletown?", "ALIAS_ENTITY_RELATION"),
    ]
    for i,(q,method) in enumerate(cases):
        x=compile_requirements(task_id=str(i),question=q)
        assert any(r["method"]==method for r in x["requirements"]),(q,x)
        assert x["gold_accessed"] is False and x["external_model_calls"]==0
        assert not any(r["full_question_verbatim_used"] for r in x["requirements"])
    print("SELF_TEST_PASS")
