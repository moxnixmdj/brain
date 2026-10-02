"""Bounded explicit predicate-argument semantics for normative clauses.

Owns a deliberately narrow M0A slice:
- simple active modal clauses: SUBJECT must/shall/should [not] VERB OBJECT
- simple passive modal clauses: SUBJECT must/shall/should [not] be VERBED by AGENT
- one explicit leading IF/WHEN condition plus one simple modal consequence

Every emitted subject/predicate/object/condition is source-span bound. Coordination,
nested clauses, missing arguments, pronoun inference, ellipsis, and world knowledge
fail closed or remain unresolved. This is not a general semantic parser.
"""
from __future__ import annotations
import re
from typing import Any

SCHEMA="BRAIN_BOUNDED_PREDICATE_ARGUMENT_SEMANTICS_V1"

_MODAL=r"(must|shall|should)"
_WORD=r"[A-Za-z][A-Za-z0-9_-]*"
_ACTIVE=re.compile(
    rf"^\s*(?P<subject>.+?)\s+(?P<modal>{_MODAL})\s+(?P<neg>not\s+)?(?P<verb>{_WORD})\s+(?P<object>.+?)\s*[.]?\s*$",
    re.I,
)
_PASSIVE=re.compile(
    rf"^\s*(?P<subject>.+?)\s+(?P<modal>{_MODAL})\s+(?P<neg>not\s+)?be\s+(?P<verb>{_WORD}(?:ed|en))\s+by\s+(?P<agent>.+?)\s*[.]?\s*$",
    re.I,
)
_COND=re.compile(r"^\s*(?P<marker>if|when)\s+(?P<condition>.+?),\s*(?P<consequence>.+)$",re.I)
_COORD=re.compile(r"\b(and|or|nor)\b|[;/]",re.I)
_PRONOUN=re.compile(r"^(he|she|it|they|him|her|them|his|hers|its|their|theirs|this|that|these|those)\b",re.I)

def _span(text:str, value:str, start_hint:int=0)->list[int]:
    i=text.find(value,start_hint)
    if i<0:
        raise ValueError("source span not found")
    return [i,i+len(value)]

def _clean_arg(x:str)->str:
    return x.strip().rstrip(".").strip()

def _unsafe_argument(x:str)->bool:
    return not x or bool(_COORD.search(x)) or bool(_PRONOUN.search(x))

def _parse_simple(text:str, *, offset:int=0)->dict[str,Any]:
    raw=text.strip()
    if not raw:
        return {"status":"FAIL_CLOSED","reason":"EMPTY_CLAUSE"}
    if _COORD.search(raw):
        return {"status":"FAIL_CLOSED","reason":"COORDINATED_OR_MULTI_CLAUSE_FORM"}

    m=_PASSIVE.match(raw)
    voice="PASSIVE"
    if not m:
        m=_ACTIVE.match(raw)
        voice="ACTIVE"
    if not m:
        return {"status":"UNRESOLVED","reason":"OUTSIDE_BOUNDED_MODAL_GRAMMAR"}

    gd=m.groupdict()
    subject=_clean_arg(gd["subject"])
    modal=gd["modal"].lower()
    neg=bool(gd.get("neg"))
    verb=gd["verb"].lower()
    if voice=="PASSIVE":
        obj=subject
        agent=_clean_arg(gd["agent"])
        if _unsafe_argument(subject) or _unsafe_argument(agent):
            return {"status":"UNRESOLVED","reason":"AMBIGUOUS_OR_CONTEXT_DEPENDENT_ARGUMENT"}
        subj_for_graph=agent
        object_for_graph=obj
    else:
        object_for_graph=_clean_arg(gd["object"])
        subj_for_graph=subject
        if _unsafe_argument(subj_for_graph) or _unsafe_argument(object_for_graph):
            return {"status":"UNRESOLVED","reason":"AMBIGUOUS_OR_CONTEXT_DEPENDENT_ARGUMENT"}

    try:
        ss=_span(text,subj_for_graph)
        vs=_span(text,gd["verb"])
        os=_span(text,object_for_graph)
    except ValueError:
        return {"status":"FAIL_CLOSED","reason":"SOURCE_SPAN_BINDING_FAILED"}

    return {
        "status":"RESOLVED",
        "voice":voice,
        "subject":subj_for_graph,
        "predicate":verb,
        "object":object_for_graph,
        "modality":modal,
        "polarity":"PROHIBITED" if neg else "REQUIRED",
        "subject_span":[ss[0]+offset,ss[1]+offset],
        "predicate_span":[vs[0]+offset,vs[1]+offset],
        "object_span":[os[0]+offset,os[1]+offset],
    }

def parse_clause(text:str)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"EMPTY_SOURCE","terminal_authority":False}

    cm=_COND.match(text)
    condition_span=None
    condition_text=None
    consequence=text
    consequence_offset=0
    relation=None
    if cm:
        condition_text=_clean_arg(cm.group("condition"))
        consequence=cm.group("consequence")
        consequence_offset=text.find(consequence)
        condition_start=text.find(cm.group("condition"))
        condition_span=[condition_start,condition_start+len(cm.group("condition"))]
        relation="CONDITION_IF" if cm.group("marker").lower()=="if" else "CONDITION_WHEN"
        if _COORD.search(condition_text):
            return {
                "schema":SCHEMA,"status":"UNRESOLVED",
                "reason":"COMPOUND_CONDITION_OUTSIDE_BOUNDED_GRAMMAR",
                "terminal_authority":False,
            }

    core=_parse_simple(consequence,offset=consequence_offset)
    if core["status"]!="RESOLVED":
        return {"schema":SCHEMA,**core,"terminal_authority":False}

    out={
        "schema":SCHEMA,
        "status":"RESOLVED",
        "semantic_graph":{
            "subject":core["subject"],
            "predicate":core["predicate"],
            "object":core["object"],
            "modality":core["modality"],
            "polarity":core["polarity"],
            "voice":core["voice"],
            "subject_span":core["subject_span"],
            "predicate_span":core["predicate_span"],
            "object_span":core["object_span"],
        },
        "terminal_authority":False,
        "scope":"SIMPLE_EXPLICIT_MODAL_PREDICATE_ARGUMENT_CLAUSES_ONLY",
    }
    if condition_text is not None:
        out["condition"]={
            "relation":relation,
            "text":condition_text,
            "span":condition_span,
        }
    return out

def consensus_proposal(text:str, *, route_id:str="bounded_predicate_argument", independence_group:str="deterministic_modal_grammar")->dict[str,Any]:
    parsed=parse_clause(text)
    proposal={"route_id":route_id,"independence_group":independence_group,"bindings":[],"relations":[],"obligations":[]}
    if parsed.get("status")!="RESOLVED":
        return {"schema":SCHEMA,"status":parsed.get("status"),"reason":parsed.get("reason"),"proposal":proposal}
    g=parsed["semantic_graph"]
    ob={
        "subject_span":g["subject_span"],
        "predicate_span":g["predicate_span"],
        "object_span":g["object_span"],
        "modality":g["polarity"].lower(),
    }
    if "condition" in parsed:
        ob["condition_span"]=parsed["condition"]["span"]
    proposal["obligations"].append(ob)
    return {"schema":SCHEMA,"status":"PROPOSAL","proposal":proposal,"terminal_authority":False}
