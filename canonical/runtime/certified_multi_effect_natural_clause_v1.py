"""Certified bounded complete multi-effect natural clause V1.

Recognizes a deliberately constrained block:

  The complete effects on <target> are <effect-id list>.
  Effect <id> on <target> defines it as <json>, <condition>, <start>, <end>, and <supersession>.
  Effect <id> on <target> replaces it with <json>, ...
  ...

For every declared target, exactly one complete body is required for every listed
effect ID, and no undeclared effect body may target that target. The declaration
therefore certifies the finite query-target effect inventory while each body
certifies every required field.

Unrecognized prose has zero authority.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
import re
from typing import Any, Mapping

SCHEMA="BRAIN_CERTIFIED_MULTI_EFFECT_NATURAL_CLAUSE_V1"
_TOKEN=r"[A-Za-z0-9_.:-]+"
_LIST_TOKEN=re.compile(r"^[A-Za-z0-9_.:-]+$")
_RE_HEADER=re.compile(
    rf"^The complete effects on (?P<target>{_TOKEN}) are (?P<items>.+)\.$"
)
_RE_BODY=re.compile(
    rf"^Effect (?P<eid>{_TOKEN}) on (?P<target>{_TOKEN}) "
    rf"(?P<body>.+), (?P<condition>.+), (?P<start>.+), "
    rf"(?P<end>.+), and (?P<sup>.+)\.$"
)
_ACTIONS=(
    ("defines it as ","DEFINE"),
    ("replaces it with ","REPLACE"),
    ("overrides it with ","OVERRIDE"),
    ("creates an exception for it with value ","EXCEPTION"),
)

def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def _token(v:str,name:str)->str:
    if not isinstance(v,str) or not v or v.strip()!=v or not _LIST_TOKEN.match(v):
        raise ValueError(name+"_INVALID")
    return v

def _ids(raw:str,name:str)->list[str]:
    normalized=raw.replace(", and "," and ")
    parts=[]
    for chunk in normalized.split(" and "):
        parts.extend(chunk.split(", "))
    out=[_token(x,name+"_ITEM") for x in parts]
    if not out or len(out)!=len(set(out)):
        raise ValueError(name+"_INVALID_OR_DUPLICATE")
    return out

def _json(raw:str,name:str)->Any:
    try: value=json.loads(raw)
    except Exception as exc: raise ValueError(name+"_JSON_INVALID") from exc
    if _canon(value)!=raw: raise ValueError(name+"_JSON_NOT_CANONICAL")
    return value

def _date(raw:str,name:str)->str:
    try: parsed=date.fromisoformat(raw)
    except ValueError as exc: raise ValueError(name+"_INVALID") from exc
    if parsed.isoformat()!=raw: raise ValueError(name+"_NOT_CANONICAL")
    return raw

def _body_fields(m:re.Match[str])->dict[str,Any]:
    action=m.group("body")
    effect_class=None; value=None
    for prefix,cls in _ACTIONS:
        if action.startswith(prefix):
            effect_class=cls
            value=_json(action[len(prefix):],"VALUE")
            break
    if effect_class is None: raise ValueError("ACTION_UNSUPPORTED")

    cond=m.group("condition")
    if cond=="is unconditional":
        conditions={}
    elif cond.startswith("applies when "):
        conditions=_json(cond[len("applies when "):],"CONDITIONS")
        if not isinstance(conditions,Mapping): raise ValueError("CONDITIONS_NOT_OBJECT")
        conditions=dict(conditions)
    else:
        raise ValueError("CONDITION_UNSUPPORTED")

    start=m.group("start")
    if start=="has no start date":
        valid_from=None
    elif start.startswith("is valid from "):
        valid_from=_date(start[len("is valid from "):],"VALID_FROM")
    else:
        raise ValueError("START_UNSUPPORTED")

    end=m.group("end")
    if end=="has no end date":
        valid_until=None
    elif end.startswith("is valid until "):
        valid_until=_date(end[len("is valid until "):],"VALID_UNTIL")
    else:
        raise ValueError("END_UNSUPPORTED")

    sup=m.group("sup")
    if not sup.startswith("supersedes "): raise ValueError("SUPERSESSION_UNSUPPORTED")
    supersedes=_ids(sup[len("supersedes "):],"SUPERSEDES") if sup!="supersedes nothing" else []

    return {
        "effect_class":effect_class,
        "value":value,
        "conditions":conditions,
        "valid_from":valid_from,
        "valid_until":valid_until,
        "supersedes":supersedes,
    }

def parse_multi_effect_clauses(text:str,*,source:str="source")->dict[str,Any]:
    if not isinstance(text,str) or not text:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"SOURCE_TEXT_MISSING","terminal_authority":False}
    if not isinstance(source,str) or not source.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"SOURCE_ID_MISSING","terminal_authority":False}

    headers={}
    bodies={}
    char_offset=0; byte_offset=0
    try:
        for line in text.splitlines(keepends=True):
            body=line.rstrip("\r\n")
            raw=body.encode("utf-8")
            hm=_RE_HEADER.match(body)
            bm=_RE_BODY.match(body)
            if hm:
                target=_token(hm.group("target"),"TARGET_ID")
                if target in headers: raise ValueError("DUPLICATE_COMPLETE_TARGET:"+target)
                ids=_ids(hm.group("items"),"EFFECT_IDS")
                headers[target]={
                    "target_id":target,
                    "effect_ids":ids,
                    "source_span_chars":[char_offset,char_offset+len(body)],
                    "source_span_bytes":[byte_offset,byte_offset+len(raw)],
                    "source_text_sha256":sha256(raw).hexdigest(),
                }
            elif bm:
                eid=_token(bm.group("eid"),"EFFECT_ID")
                target=_token(bm.group("target"),"TARGET_ID")
                key=(target,eid)
                if key in bodies: raise ValueError("DUPLICATE_EFFECT_BODY:"+target+":"+eid)
                fields=_body_fields(bm)
                bodies[key]={
                    "effect_id":eid,"target_id":target,**fields,
                    "source_span_chars":[char_offset,char_offset+len(body)],
                    "source_span_bytes":[byte_offset,byte_offset+len(raw)],
                    "source_text_sha256":sha256(raw).hexdigest(),
                }
            char_offset+=len(line)
            byte_offset+=len(line.encode("utf-8"))

        groups=[]
        for target,h in sorted(headers.items()):
            declared=set(h["effect_ids"])
            actual={eid for (t,eid) in bodies if t==target}
            if actual!=declared:
                missing=sorted(declared-actual); extra=sorted(actual-declared)
                raise ValueError(
                    "COMPLETE_EFFECT_BODY_SET_MISMATCH:"+target
                    +":MISSING="+",".join(missing)+":EXTRA="+",".join(extra)
                )
            effects=[]
            for eid in h["effect_ids"]:
                row=bodies[(target,eid)]
                effect={
                    "effect_id":eid,
                    "target_id":target,
                    "effect_class":row["effect_class"],
                    "value":row["value"],
                    "conditions":row["conditions"],
                    "valid_from":row["valid_from"],
                    "valid_until":row["valid_until"],
                    "supersedes":row["supersedes"],
                }
                effects.append({
                    "effect":effect,
                    "body_source_span_chars":row["source_span_chars"],
                    "body_source_span_bytes":row["source_span_bytes"],
                    "body_source_text_sha256":row["source_text_sha256"],
                })
            gid="MULTI-EFFECT-"+sha256(
                (source+"\0"+target+"\0"+_canon({"ids":h["effect_ids"],"effects":[x["effect"] for x in effects]})).encode("utf-8")
            ).hexdigest()[:24]
            groups.append({
                "group_id":gid,
                "source_id":source,
                "inventory":{"target_id":target,"effect_ids":list(h["effect_ids"])},
                "effects":effects,
                "header_source_span_chars":h["source_span_chars"],
                "header_source_span_bytes":h["source_span_bytes"],
                "header_source_text_sha256":h["source_text_sha256"],
            })

        # Bodies without a matching complete header cannot create authority.
        orphan=sorted((t,eid) for (t,eid) in bodies if t not in headers)
        if orphan:
            raise ValueError("EFFECT_BODY_WITHOUT_COMPLETE_HEADER:"+",".join(t+":"+e for t,e in orphan))

        return {
            "schema":SCHEMA,
            "status":"PARSED",
            "groups":groups,
            "terminal_authority":False,
            "scope":"BOUNDED_COMPLETE_MULTI_EFFECT_SET_PER_TARGET",
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,"status":"UNRESOLVED",
            "reason":type(exc).__name__+":"+str(exc),
            "terminal_authority":False,
        }
