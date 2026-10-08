"""Bounded numeric relation support v1.

Extends the bounded factual surface with deterministic Decimal claim relations:
at least, at most, greater than, less than, and inclusive between.

This module owns its numeric surface parser because the legacy equality fact parser
intentionally has a narrower dot-delimited grammar. No units, fuzzy quantities,
source authority, or world knowledge are inferred in v1.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
from typing import Any

SCHEMA="PROJECT_BRAIN_BOUNDED_NUMERIC_RELATION_SUPPORT_V1"
_NUM=r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?"
_SURFACE=re.compile(r"^(?P<entity>[A-Za-z][A-Za-z0-9_ -]*?)\s+(?P<field>[A-Za-z][A-Za-z0-9_ -]*?)\s+is\s+(?P<value>.+)$",re.I)
_PREFIXES=(
    re.compile(r"^(?P<source>.+?)\s+reports\s+that\s+(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>.+?)\s+states\s+(?P<body>.+)$",re.I),
    re.compile(r"^(?P<source>[^:]+):\s*(?P<body>.+)$",re.I),
)
_PATTERNS=(
    (re.compile(rf"^at least (?P<a>{_NUM})$",re.I),"GE"),
    (re.compile(rf"^at most (?P<a>{_NUM})$",re.I),"LE"),
    (re.compile(rf"^greater than (?P<a>{_NUM})$",re.I),"GT"),
    (re.compile(rf"^less than (?P<a>{_NUM})$",re.I),"LT"),
    (re.compile(rf"^between (?P<a>{_NUM}) and (?P<b>{_NUM})$",re.I),"BETWEEN"),
)

def _dec(x:str)->Decimal:
    try:d=Decimal(x)
    except InvalidOperation as exc:raise ValueError("DECIMAL_INVALID") from exc
    if not d.is_finite():raise ValueError("DECIMAL_NONFINITE")
    return d

def _parse_surface(text:str,*,default_source:str|None=None)->dict[str,Any]:
    if not isinstance(text,str) or not text.strip():
        return {"status":"FAIL_CLOSED","reason":"TEXT_REQUIRED"}
    raw=" ".join(text.strip().split())
    if raw.endswith("."):raw=raw[:-1].rstrip()
    source=default_source;body=raw
    for pat in _PREFIXES:
        m=pat.fullmatch(raw)
        if m:
            source=" ".join(m.group("source").split());body=m.group("body");break
    m=_SURFACE.fullmatch(body)
    if not m:
        return {"status":"UNRESOLVED","reason":"OUTSIDE_NUMERIC_FACT_SURFACE"}
    return {
      "status":"RESOLVED","entity":" ".join(m.group("entity").split()).casefold(),
      "field":" ".join(m.group("field").split()).casefold(),
      "value":" ".join(m.group("value").split()).casefold(),"source":source,
    }

def parse_numeric_relation_claim(text:str)->dict[str,Any]:
    row=_parse_surface(text,default_source="CLAIM")
    if row.get("status")!="RESOLVED":
        return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"CLAIM_OUTSIDE_NUMERIC_FACT_SURFACE","claim_in_scope":False}
    for regex,op in _PATTERNS:
        m=regex.fullmatch(row["value"])
        if not m:continue
        a=_dec(m.group("a"));b=_dec(m.group("b")) if m.groupdict().get("b") is not None else None
        if op=="BETWEEN" and a>b:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"INTERVAL_LOWER_GT_UPPER","claim_in_scope":True}
        return {"schema":SCHEMA,"status":"RESOLVED","claim_in_scope":True,
                "entity":row["entity"],"field":row["field"],"operator":op,
                "a":str(a),"b":None if b is None else str(b),"terminal_authority":False}
    return {"schema":SCHEMA,"status":"UNRESOLVED","reason":"CLAIM_OUTSIDE_NUMERIC_RELATION_GRAMMAR","claim_in_scope":False}

def classify_support(claim_text:str,evidence_text:str,*,evidence_id:str|None=None)->dict[str,Any]:
    claim=parse_numeric_relation_claim(claim_text)
    if claim.get("status")!="RESOLVED":
        return {"schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN",
                "claim_in_scope":bool(claim.get("claim_in_scope")),"reason":claim.get("reason"),
                "terminal_authority":False}
    ev=_parse_surface(evidence_text,default_source=evidence_id or "EVIDENCE")
    if ev.get("status")!="RESOLVED":
        return {"schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN","claim_in_scope":True,
                "reason":"EVIDENCE_OUTSIDE_NUMERIC_FACT_SURFACE","terminal_authority":False}
    if ev["entity"]!=claim["entity"] or ev["field"]!=claim["field"]:
        return {"schema":SCHEMA,"status":"RESOLVED","relation":"UNRELATED","claim_in_scope":True,
                "operator":claim["operator"],"terminal_authority":False}
    if re.fullmatch(_NUM,ev["value"]) is None:
        return {"schema":SCHEMA,"status":"UNRESOLVED","relation":"UNKNOWN","claim_in_scope":True,
                "reason":"EVIDENCE_VALUE_NOT_EXACT_DECIMAL","terminal_authority":False}
    value=_dec(ev["value"]);a=_dec(claim["a"]);b=_dec(claim["b"]) if claim["b"] is not None else None
    op=claim["operator"]
    if op=="GE":holds=value>=a
    elif op=="LE":holds=value<=a
    elif op=="GT":holds=value>a
    elif op=="LT":holds=value<a
    else:holds=a<=value<=b
    return {"schema":SCHEMA,"status":"RESOLVED","relation":"SUPPORTS" if holds else "CONFLICTS",
            "claim_in_scope":True,
            "claim":{"entity":claim["entity"],"field":claim["field"],"operator":op,"a":claim["a"],"b":claim["b"]},
            "evidence":{"entity":ev["entity"],"field":ev["field"],"value":str(value),"source":ev["source"]},
            "terminal_authority":False,
            "scope":"EXACT_DECIMAL_NUMERIC_RELATION_OVER_CONTROLLED_ENTITY_FIELD_VALUE_SURFACE_ONLY"}
