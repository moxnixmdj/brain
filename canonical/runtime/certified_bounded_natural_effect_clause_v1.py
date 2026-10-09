"""Certified bounded natural-language document-effect clauses V1.

This module recognizes a deliberately small, source-exact English subset.
It does NOT claim general English understanding.

Supported standalone sentences:
  The only effects on <target> are <effect ids>.
  The only effect targets are <targets>.

  Effect <id> defines <target> as <json>.
  Effect <id> replaces <target> with <json>.
  Effect <id> overrides <target> with <json>.
  Effect <id> creates an exception for <target> with value <json>.

  Effect <id> is unconditional.
  Effect <id> applies when <json-object>.
  Effect <id> is valid from <YYYY-MM-DD>.
  Effect <id> has no start date.
  Effect <id> is valid until <YYYY-MM-DD>.
  Effect <id> has no end date.
  Effect <id> supersedes <effect ids>.
  Effect <id> supersedes nothing.

Every recognized clause returns exact source spans/hashes plus semantic claims.
Unrecognized text is simply not certified.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
import re
from typing import Any, Mapping

from canonical.runtime import cross_document_effect_calculus_v1 as calculus

SCHEMA="BRAIN_CERTIFIED_BOUNDED_NATURAL_EFFECT_CLAUSE_V1"
_TOKEN=r"[A-Za-z0-9_.:-]+"
_LIST_TOKEN=re.compile(r"^[A-Za-z0-9_.:-]+$")

_RE_SCOPE=re.compile(r"^The only effect targets are (?P<items>.+)\.$")
_RE_INVENTORY=re.compile(
    rf"^The only effects on (?P<target>{_TOKEN}) are (?P<items>.+)\.$"
)
_RE_DEFINE=re.compile(
    rf"^Effect (?P<eid>{_TOKEN}) defines (?P<target>{_TOKEN}) as (?P<value>.+)\.$"
)
_RE_REPLACE=re.compile(
    rf"^Effect (?P<eid>{_TOKEN}) replaces (?P<target>{_TOKEN}) with (?P<value>.+)\.$"
)
_RE_OVERRIDE=re.compile(
    rf"^Effect (?P<eid>{_TOKEN}) overrides (?P<target>{_TOKEN}) with (?P<value>.+)\.$"
)
_RE_EXCEPTION=re.compile(
    rf"^Effect (?P<eid>{_TOKEN}) creates an exception for (?P<target>{_TOKEN}) with value (?P<value>.+)\.$"
)
_RE_UNCONDITIONAL=re.compile(rf"^Effect (?P<eid>{_TOKEN}) is unconditional\.$")
_RE_WHEN=re.compile(rf"^Effect (?P<eid>{_TOKEN}) applies when (?P<conditions>.+)\.$")
_RE_FROM=re.compile(rf"^Effect (?P<eid>{_TOKEN}) is valid from (?P<date>\d{{4}}-\d{{2}}-\d{{2}})\.$")
_RE_NO_FROM=re.compile(rf"^Effect (?P<eid>{_TOKEN}) has no start date\.$")
_RE_UNTIL=re.compile(rf"^Effect (?P<eid>{_TOKEN}) is valid until (?P<date>\d{{4}}-\d{{2}}-\d{{2}})\.$")
_RE_NO_UNTIL=re.compile(rf"^Effect (?P<eid>{_TOKEN}) has no end date\.$")
_RE_SUPERSEDES=re.compile(rf"^Effect (?P<eid>{_TOKEN}) supersedes (?P<items>.+)\.$")
_RE_SUPERSEDES_NONE=re.compile(rf"^Effect (?P<eid>{_TOKEN}) supersedes nothing\.$")


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _token(v:str,name:str)->str:
    if not isinstance(v,str) or not v or v.strip()!=v or not _LIST_TOKEN.match(v):
        raise ValueError(name+"_INVALID")
    return v


def _list(text:str,name:str)->list[str]:
    if not isinstance(text,str) or not text.strip():
        raise ValueError(name+"_EMPTY")
    normalized=text.replace(", and "," and ")
    parts=[]
    for chunk in normalized.split(" and "):
        parts.extend(chunk.split(", "))
    out=[_token(x,name+"_ITEM") for x in parts]
    if not out or len(out)!=len(set(out)):
        raise ValueError(name+"_INVALID_OR_DUPLICATE")
    return out


def _json_value(raw:str,name:str)->Any:
    try:
        value=json.loads(raw)
    except Exception as exc:
        raise ValueError(name+"_JSON_INVALID") from exc
    if _canon(value)!=raw:
        raise ValueError(name+"_JSON_NOT_CANONICAL")
    return value


def _date(raw:str,name:str)->str:
    try:
        parsed=date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(name+"_INVALID") from exc
    if parsed.isoformat()!=raw:
        raise ValueError(name+"_NOT_CANONICAL")
    return raw


def _record(
    *,
    source:str,
    kind:str,
    payload:Mapping[str,Any],
    char_start:int,
    char_end:int,
    byte_start:int,
    byte_end:int,
    body_bytes:bytes,
)->dict[str,Any]:
    digest=sha256(body_bytes).hexdigest()
    clause_id="NAT-EFFECT-"+sha256(
        (
            source+"\0"+kind+"\0"+str(byte_start)+"\0"+str(byte_end)
            +"\0"+_canon(dict(payload))
        ).encode("utf-8")
    ).hexdigest()[:24]
    return {
        "clause_id":clause_id,
        "source_id":source,
        "kind":kind,
        **dict(payload),
        "source_span_chars":[char_start,char_end],
        "source_span_bytes":[byte_start,byte_end],
        "source_text_sha256":digest,
    }


def parse_natural_effect_clauses(text:str,*,source:str="source")->dict[str,Any]:
    if not isinstance(text,str) or not text:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "reason":"SOURCE_TEXT_MISSING","terminal_authority":False,
        }
    if not isinstance(source,str) or not source.strip():
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "reason":"SOURCE_ID_MISSING","terminal_authority":False,
        }

    clauses=[]
    seen_slots=set()
    char_offset=0
    byte_offset=0

    def add(kind:str,payload:dict[str,Any],body:str,body_bytes:bytes):
        slot=None
        if kind=="TARGET_SCOPE":
            slot=("TARGET_SCOPE",)
        elif kind=="INVENTORY":
            slot=("INVENTORY",payload["target_id"])
        elif kind=="FIELD":
            slot=("FIELD",payload["effect_id"],payload["field"])
        if slot in seen_slots:
            raise ValueError("DUPLICATE_NATURAL_SEMANTIC_SLOT:"+":".join(slot))
        seen_slots.add(slot)
        clauses.append(_record(
            source=source,kind=kind,payload=payload,
            char_start=char_offset,char_end=char_offset+len(body),
            byte_start=byte_offset,byte_end=byte_offset+len(body_bytes),
            body_bytes=body_bytes,
        ))

    try:
        for line in text.splitlines(keepends=True):
            body=line.rstrip("\r\n")
            body_bytes=body.encode("utf-8")
            m=_RE_SCOPE.match(body)
            if m:
                add("TARGET_SCOPE",{"target_ids":_list(m.group("items"),"TARGET_SCOPE")},body,body_bytes)
            else:
                m=_RE_INVENTORY.match(body)
                if m:
                    add("INVENTORY",{
                        "target_id":_token(m.group("target"),"TARGET_ID"),
                        "effect_ids":_list(m.group("items"),"EFFECT_IDS"),
                    },body,body_bytes)
                else:
                    matched=False
                    for regex,cls,word in (
                        (_RE_DEFINE,"DEFINE","value"),
                        (_RE_REPLACE,"REPLACE","value"),
                        (_RE_OVERRIDE,"OVERRIDE","value"),
                        (_RE_EXCEPTION,"EXCEPTION","value"),
                    ):
                        m=regex.match(body)
                        if not m:
                            continue
                        eid=_token(m.group("eid"),"EFFECT_ID")
                        target=_token(m.group("target"),"TARGET_ID")
                        value=_json_value(m.group(word),"VALUE")
                        add("FIELD",{"effect_id":eid,"field":"target_id","value":target},body,body_bytes)
                        add("FIELD",{"effect_id":eid,"field":"effect_class","value":cls},body,body_bytes)
                        add("FIELD",{"effect_id":eid,"field":"value","value":value},body,body_bytes)
                        matched=True
                        break
                    if not matched:
                        m=_RE_UNCONDITIONAL.match(body)
                        if m:
                            add("FIELD",{"effect_id":_token(m.group("eid"),"EFFECT_ID"),"field":"conditions","value":{}},body,body_bytes)
                        else:
                            m=_RE_WHEN.match(body)
                            if m:
                                conditions=_json_value(m.group("conditions"),"CONDITIONS")
                                if not isinstance(conditions,Mapping):
                                    raise ValueError("CONDITIONS_NOT_OBJECT")
                                add("FIELD",{"effect_id":_token(m.group("eid"),"EFFECT_ID"),"field":"conditions","value":dict(conditions)},body,body_bytes)
                            else:
                                m=_RE_FROM.match(body)
                                if m:
                                    add("FIELD",{"effect_id":_token(m.group("eid"),"EFFECT_ID"),"field":"valid_from","value":_date(m.group("date"),"VALID_FROM")},body,body_bytes)
                                else:
                                    m=_RE_NO_FROM.match(body)
                                    if m:
                                        add("FIELD",{"effect_id":_token(m.group("eid"),"EFFECT_ID"),"field":"valid_from","value":None},body,body_bytes)
                                    else:
                                        m=_RE_UNTIL.match(body)
                                        if m:
                                            add("FIELD",{"effect_id":_token(m.group("eid"),"EFFECT_ID"),"field":"valid_until","value":_date(m.group("date"),"VALID_UNTIL")},body,body_bytes)
                                        else:
                                            m=_RE_NO_UNTIL.match(body)
                                            if m:
                                                add("FIELD",{"effect_id":_token(m.group("eid"),"EFFECT_ID"),"field":"valid_until","value":None},body,body_bytes)
                                            else:
                                                m=_RE_SUPERSEDES_NONE.match(body)
                                                if m:
                                                    add("FIELD",{"effect_id":_token(m.group("eid"),"EFFECT_ID"),"field":"supersedes","value":[]},body,body_bytes)
                                                else:
                                                    m=_RE_SUPERSEDES.match(body)
                                                    if m:
                                                        items=m.group("items")
                                                        if items!="nothing":
                                                            add("FIELD",{"effect_id":_token(m.group("eid"),"EFFECT_ID"),"field":"supersedes","value":_list(items,"SUPERSEDES")},body,body_bytes)
            char_offset+=len(line)
            byte_offset+=len(line.encode("utf-8"))
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"UNRESOLVED",
            "reason":type(exc).__name__+":"+str(exc),
            "terminal_authority":False,
        }

    return {
        "schema":SCHEMA,
        "status":"PARSED",
        "clauses":clauses,
        "terminal_authority":False,
        "scope":"BOUNDED_UNAMBIGUOUS_NATURAL_EFFECT_CLAUSES_ONLY",
    }
