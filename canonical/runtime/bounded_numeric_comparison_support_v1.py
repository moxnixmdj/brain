"""Bounded numeric comparison claim/evidence relation v1.

A required claim in the controlled entity/field/value grammar may use one of:
  at least N, at most N, more than N, less than N, exactly N, not exactly N.
Evidence must state an exact Decimal value for the same normalized entity/field.
No units conversion, approximation, paraphrase, source authority, or world
knowledge is inferred.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
import re
from typing import Any

SCHEMA="PROJECT_BRAIN_BOUNDED_NUMERIC_COMPARISON_SUPPORT_V1"

_NUM=r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?"
_WORDS=r"[A-Za-z][A-Za-z0-9_ -]*?"
_PREFIXES=(
    re.compile(r"^(?P<source>.+?)\s+reports\s+that\s+(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>.+?)\s+states\s+(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>[^:]+):\s*(?P<body>.+)$",re.I),
)
_CLAIM=re.compile(
    rf"^(?P<entity>{_WORDS})\s+(?P<field>{_WORDS})\s+is\s+"
    rf"(?P<op>at least|at most|more than|less than|exactly|not exactly)\s+"
    rf"(?P<num>{_NUM})\s*\.?$",re.I,
)
_EVIDENCE=re.compile(
    rf"^(?P<entity>{_WORDS})\s+(?P<field>{_WORDS})\s+is\s+"
    rf"(?P<num>{_NUM})\s*\.?$",re.I,
)
_OPS={
    "at least":"GE","at most":"LE","more than":"GT",
    "less than":"LT","exactly":"EQ","not exactly":"NE",
}

def _norm_words(x:Any)->str:
    return " ".join(str(x if x is not None else "").strip().lower().split())

def _body(text:str)->tuple[str,str|None]|None:
    if not isinstance(text,str) or not text.strip():
        return None
    raw=" ".join(text.strip().split())
    body=raw; source=None
    for pat in _PREFIXES:
        m=pat.fullmatch(raw)
        if m:
            source=" ".join(m.group("source").split())
            body=m.group("body")
            break
    return body,source

def _decimal(raw:Any)->Decimal|None:
    if not isinstance(raw,str) or re.fullmatch(_NUM,raw) is None:
        return None
    try:
        x=Decimal(raw)
    except InvalidOperation:
        return None
    return x if x.is_finite() else None

def parse_comparison_claim(claim_text:str)->dict[str,Any]|None:
    parsed=_body(claim_text)
    if parsed is None:
        return None
    body,_=parsed
    m=_CLAIM.fullmatch(body)
    if not m:
        return None
    threshold=_decimal(m.group("num"))
    if threshold is None:
        return None
    return {
        "entity":_norm_words(m.group("entity")),
        "field":_norm_words(m.group("field")),
        "operator":_OPS[m.group("op").casefold()],
        "threshold":threshold,
        "threshold_text":m.group("num"),
    }

def _parse_numeric_evidence(evidence_text:str)->dict[str,Any]|None:
    parsed=_body(evidence_text)
    if parsed is None:
        return None
    body,source=parsed
    m=_EVIDENCE.fullmatch(body)
    if not m:
        return None
    value=_decimal(m.group("num"))
    if value is None:
        return None
    return {
        "entity":_norm_words(m.group("entity")),
        "field":_norm_words(m.group("field")),
        "value":value,
        "value_text":m.group("num"),
        "source":source,
    }

def classify_support(claim_text:str,evidence_text:str,*,evidence_id:str|None=None)->dict[str,Any]:
    c=parse_comparison_claim(claim_text)
    if c is None:
        return {
            "schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
            "claim_numeric_comparison":False,
            "reason":"CLAIM_NOT_BOUNDED_NUMERIC_COMPARISON",
            "terminal_authority":False,
        }
    f=_parse_numeric_evidence(evidence_text)
    if f is None:
        return {
            "schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
            "claim_numeric_comparison":True,
            "reason":"EVIDENCE_OUTSIDE_BOUNDED_NUMERIC_FACT_GRAMMAR",
            "terminal_authority":False,
        }
    if f["entity"]!=c["entity"] or f["field"]!=c["field"]:
        return {
            "schema":SCHEMA,"status":"RESOLVED","relation":"UNRELATED",
            "claim_numeric_comparison":True,
            "claim_entity":c["entity"],"claim_field":c["field"],
            "evidence_entity":f["entity"],"evidence_field":f["field"],
            "terminal_authority":False,
        }
    value=f["value"]
    t=c["threshold"]; op=c["operator"]
    holds=(
        value>=t if op=="GE" else
        value<=t if op=="LE" else
        value>t if op=="GT" else
        value<t if op=="LT" else
        value==t if op=="EQ" else
        value!=t
    )
    return {
        "schema":SCHEMA,"status":"RESOLVED",
        "relation":"SUPPORTS" if holds else "CONFLICTS",
        "claim_numeric_comparison":True,
        "entity":c["entity"],"field":c["field"],
        "operator":op,"threshold":c["threshold_text"],
        "evidence_value":f["value_text"],
        "evidence_id":evidence_id,
        "terminal_authority":False,
        "scope":"EXACT_DECIMAL_COMPARISON_OVER_SHARED_BOUNDED_ENTITY_FIELD_KEY",
    }
