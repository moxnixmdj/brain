"""Bounded source-grounded claim/support induction.

This module parses a deliberately explicit factual language into provenance-preserving
claim facts, then classifies evidence as supporting, conflicting, or unrelated to a
claim. It is a narrow owned primitive, not general entailment.

Supported controlled factual surfaces:
- "<entity> <field> is <value>."
- "<source> reports that <entity> <field> is <value>."
- "<source> states <entity> <field> is <value>."
- "<source>: <entity> <field> is <value>."

Values are normalized strings; numeric strings are canonicalized. Same (entity, field)
with a different value is conflict, same value is support. Missing semantic identity
fails closed rather than relying on lexical similarity alone.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_BOUNDED_CLAIM_SUPPORT_V1"

_PREFIXES=(
    re.compile(r"^(?P<source>.+?)\s+reports\s+that\s+(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>.+?)\s+states\s+(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>[^:]+):\s*(?P<body>.+)$",re.I),
)
_FACT=re.compile(
    r"^(?P<entity>[A-Za-z][A-Za-z0-9_ -]*?)\s+"
    r"(?P<field>[A-Za-z][A-Za-z0-9_ -]*?)\s+is\s+"
    r"(?P<value>[^.]+?)\s*\.?$",
    re.I,
)


@dataclass(frozen=True)
class Fact:
    entity:str
    field:str
    value:str
    source:str|None
    source_text:str


def _norm_words(x:Any)->str:
    return " ".join(str(x if x is not None else "").strip().lower().split())


def _norm_value(x:Any)->str:
    raw=" ".join(str(x if x is not None else "").strip().split())
    try:
        d=Decimal(raw)
        return format(d.normalize(),"f")
    except (InvalidOperation,ValueError):
        return raw.lower()


def parse_fact(text:str, *, default_source:str|None=None)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"TEXT_REQUIRED"}
    raw=" ".join(text.strip().split())
    source=default_source
    body=raw
    for pat in _PREFIXES:
        m=pat.fullmatch(raw)
        if m:
            source=" ".join(m.group("source").split())
            body=m.group("body")
            break
    m=_FACT.fullmatch(body)
    if not m:
        return {
            "schema":SCHEMA,
            "status":"UNRESOLVED",
            "reason":"OUTSIDE_BOUNDED_FACT_GRAMMAR",
            "source_text":raw,
        }
    entity=_norm_words(m.group("entity"))
    field=_norm_words(m.group("field"))
    value=_norm_value(m.group("value"))
    if not entity or not field or not value:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"EMPTY_FACT_SLOT"}
    fact=Fact(entity,field,value,source,raw)
    return {"schema":SCHEMA,"status":"RESOLVED","fact":asdict(fact),"terminal_authority":False}


def classify_support(claim_text:str,evidence_text:str,*,evidence_id:str|None=None)->dict[str,Any]:
    claim=parse_fact(claim_text,default_source="CLAIM")
    ev=parse_fact(evidence_text,default_source=evidence_id or "EVIDENCE")
    if claim.get("status")!="RESOLVED" or ev.get("status")!="RESOLVED":
        return {
            "schema":SCHEMA,
            "status":"UNRESOLVED",
            "relation":"UNKNOWN",
            "claim_parse":claim.get("status"),
            "evidence_parse":ev.get("status"),
            "terminal_authority":False,
        }
    c=claim["fact"]; e=ev["fact"]
    if c["entity"]!=e["entity"] or c["field"]!=e["field"]:
        relation="UNRELATED"
    elif c["value"]==e["value"]:
        relation="SUPPORTS"
    else:
        relation="CONFLICTS"
    return {
        "schema":SCHEMA,
        "status":"RESOLVED",
        "relation":relation,
        "claim":{"entity":c["entity"],"field":c["field"],"value":c["value"]},
        "evidence":{
            "entity":e["entity"],"field":e["field"],"value":e["value"],
            "source":e["source"],"source_text":e["source_text"],
        },
        "terminal_authority":False,
    }


def build_support_graph(
    claims:Sequence[Mapping[str,Any]],
    evidence:Sequence[Mapping[str,Any]],
)->dict[str,Any]:
    if isinstance(claims,(str,bytes)) or isinstance(evidence,(str,bytes)):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"ROWS_MUST_BE_SEQUENCES"}
    claim_ids=[]; evidence_ids=[]
    for row in claims:
        if not isinstance(row,Mapping) or not isinstance(row.get("claim_id"),str) or not isinstance(row.get("text"),str):
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"CLAIM_ROW_INVALID"}
        claim_ids.append(row["claim_id"])
    for row in evidence:
        if not isinstance(row,Mapping) or not isinstance(row.get("evidence_id"),str) or not isinstance(row.get("text"),str):
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"EVIDENCE_ROW_INVALID"}
        evidence_ids.append(row["evidence_id"])
    if len(claim_ids)!=len(set(claim_ids)) or len(evidence_ids)!=len(set(evidence_ids)):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"DUPLICATE_IDS"}

    edges=[]; unresolved=[]
    for c in claims:
        for e in evidence:
            r=classify_support(c["text"],e["text"],evidence_id=e["evidence_id"])
            if r.get("status")!="RESOLVED":
                unresolved.append({"claim_id":c["claim_id"],"evidence_id":e["evidence_id"]})
                continue
            if r["relation"]!="UNRELATED":
                edges.append({
                    "claim_id":c["claim_id"],
                    "evidence_id":e["evidence_id"],
                    "relation":r["relation"],
                })
    return {
        "schema":SCHEMA,
        "status":"COMPILED_WITH_UNKNOWNS" if unresolved else "COMPILED",
        "edges":sorted(edges,key=lambda x:(x["claim_id"],x["evidence_id"],x["relation"])),
        "unresolved":sorted(unresolved,key=lambda x:(x["claim_id"],x["evidence_id"])),
        "terminal_authority":False,
        "scope":"BOUNDED_EXPLICIT_ENTITY_FIELD_VALUE_FACTS_ONLY",
    }
