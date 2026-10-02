"""Bounded contextual semantic resolver for explicit discourse and reference cases.

This module deliberately owns only a decidable subset of M0A:
- exact named antecedents already frozen by explicit-definition machinery,
- simple third-person pronouns with a unique compatible antecedent in a bounded window,
- explicit discourse connectives (because/therefore/however/although/if/unless/before/after),
- fail-closed ambiguity when multiple antecedents or relation parses survive.

It does not claim general coreference, commonsense, implicit discourse, or arbitrary NL semantics.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import re, hashlib
from typing import Any, Sequence

SCHEMA="BRAIN_BOUNDED_CONTEXTUAL_SEMANTICS_V1"

_CONNECTIVES={
    "because":"CAUSE",
    "therefore":"RESULT",
    "however":"CONTRAST",
    "although":"CONCESSION",
    "if":"CONDITION",
    "unless":"EXCEPTION_CONDITION",
    "before":"TEMPORAL_BEFORE",
    "after":"TEMPORAL_AFTER",
}
_PRONOUNS={
    "he":"MASC_SINGULAR","him":"MASC_SINGULAR","his":"MASC_SINGULAR",
    "she":"FEM_SINGULAR","her":"FEM_SINGULAR","hers":"FEM_SINGULAR",
    "it":"NEUTER_SINGULAR","its":"NEUTER_SINGULAR",
    "they":"PLURAL_OR_UNKNOWN","them":"PLURAL_OR_UNKNOWN","their":"PLURAL_OR_UNKNOWN","theirs":"PLURAL_OR_UNKNOWN",
}

def _sid(text:str,start:int,end:int,kind:str)->str:
    return "CTX-"+hashlib.sha256(f"{start}\0{end}\0{kind}\0{text[start:end]}".encode()).hexdigest()[:20]

def explicit_discourse_relations(text:str)->list[dict[str,Any]]:
    if not isinstance(text,str) or not text:
        raise ValueError("text must be non-empty")
    out=[]
    for token,relation in _CONNECTIVES.items():
        for m in re.finditer(rf"\b{re.escape(token)}\b",text,re.I):
            out.append({
                "id":_sid(text,m.start(),m.end(),relation),
                "start":m.start(),"end":m.end(),"surface":m.group(0),
                "relation":relation,
                "status":"EXPLICIT_CONNECTIVE_ONLY",
            })
    return sorted(out,key=lambda x:(x["start"],x["end"],x["relation"]))

def resolve_pronouns(
    text:str,
    mentions:Sequence[dict[str,Any]],
    *,
    max_char_distance:int=400,
)->dict[str,Any]:
    """Resolve only unique, feature-compatible recent antecedents.

    mentions rows: {id,start,end,number:"singular|plural",gender:"masc|fem|neuter|unknown"}.
    No lexical/world inference is performed.
    """
    if not isinstance(text,str) or not text:
        raise ValueError("text must be non-empty")
    if not isinstance(mentions,Sequence) or isinstance(mentions,(str,bytes)):
        raise ValueError("mentions must be a sequence")
    norm=[]
    errors=[]
    for i,m in enumerate(mentions):
        if not isinstance(m,dict):
            errors.append(f"MENTION_INVALID:{i}"); continue
        mid=m.get("id"); start=m.get("start"); end=m.get("end")
        if not isinstance(mid,str) or not mid:
            errors.append(f"MENTION_ID_INVALID:{i}"); continue
        if not isinstance(start,int) or not isinstance(end,int) or start<0 or end<=start or end>len(text):
            errors.append(f"MENTION_SPAN_INVALID:{mid}"); continue
        number=m.get("number","unknown")
        gender=m.get("gender","unknown")
        if number not in {"singular","plural","unknown"}:
            errors.append(f"MENTION_NUMBER_INVALID:{mid}")
        if gender not in {"masc","fem","neuter","unknown"}:
            errors.append(f"MENTION_GENDER_INVALID:{mid}")
        norm.append({"id":mid,"start":start,"end":end,"number":number,"gender":gender})
    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),"resolutions":[]}

    resolutions=[]
    for pm in re.finditer(r"\b(he|him|his|she|her|hers|it|its|they|them|their|theirs)\b",text,re.I):
        p=pm.group(1).lower()
        cls=_PRONOUNS[p]
        candidates=[]
        for m in norm:
            if m["end"]>pm.start():
                continue
            distance=pm.start()-m["end"]
            if distance>max_char_distance:
                continue
            compatible=False
            if cls=="MASC_SINGULAR":
                compatible=m["number"] in {"singular","unknown"} and m["gender"] in {"masc","unknown"}
            elif cls=="FEM_SINGULAR":
                compatible=m["number"] in {"singular","unknown"} and m["gender"] in {"fem","unknown"}
            elif cls=="NEUTER_SINGULAR":
                compatible=m["number"] in {"singular","unknown"} and m["gender"] in {"neuter","unknown"}
            else:
                compatible=m["number"] in {"plural","unknown"}
            if compatible:
                candidates.append((distance,m))
        candidates.sort(key=lambda x:(x[0],x[1]["id"]))
        if not candidates:
            resolutions.append({
                "pronoun":p,"start":pm.start(),"end":pm.end(),
                "status":"UNRESOLVED","reason":"NO_COMPATIBLE_ANTECEDENT","terminal_authority":False,
            }); continue
        nearest_distance=candidates[0][0]
        nearest=[m for d,m in candidates if d==nearest_distance]
        if len(nearest)!=1:
            resolutions.append({
                "pronoun":p,"start":pm.start(),"end":pm.end(),
                "status":"AMBIGUOUS","reason":"MULTIPLE_EQUALLY_NEAR_COMPATIBLE_ANTECEDENTS",
                "candidate_ids":[m["id"] for m in nearest],"terminal_authority":False,
            }); continue
        # If another compatible candidate is almost equally recent, refuse to guess.
        if len(candidates)>1 and candidates[1][0]-nearest_distance <= 8:
            resolutions.append({
                "pronoun":p,"start":pm.start(),"end":pm.end(),
                "status":"AMBIGUOUS","reason":"NEAR_TIE_COMPATIBLE_ANTECEDENTS",
                "candidate_ids":[candidates[0][1]["id"],candidates[1][1]["id"]],
                "terminal_authority":False,
            }); continue
        resolutions.append({
            "pronoun":p,"start":pm.start(),"end":pm.end(),
            "status":"RESOLVED","antecedent_id":nearest[0]["id"],
            "evidence":"UNIQUE_RECENT_FEATURE_COMPATIBLE_ANTECEDENT",
            "terminal_authority":False,
        })
    return {
        "schema":SCHEMA,
        "status":"PASS" if all(r["status"]=="RESOLVED" for r in resolutions) else "PARTIAL_FAIL_CLOSED",
        "resolutions":resolutions,
        "terminal_authority":False,
        "scope":"BOUNDED_EXPLICIT_FEATURE_COMPATIBLE_PRONOUNS_AND_EXPLICIT_DISCOURSE_CONNECTIVES_ONLY",
    }

def compile_context(text:str,mentions:Sequence[dict[str,Any]])->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "pronouns":resolve_pronouns(text,mentions),
        "discourse":explicit_discourse_relations(text),
        "claims_excluded":[
            "GENERAL_COREFERENCE","COMMONSENSE_REFERENCE","IMPLICIT_DISCOURSE",
            "LONG_RANGE_WORLD_MODEL_SEMANTICS","ARBITRARY_NATURAL_LANGUAGE_UNDERSTANDING"
        ],
    }
