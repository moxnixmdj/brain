"""Certified compositional bounded natural document-effect clause V1.

Recognizes one deliberately constrained complete-effect sentence:

  The complete effect <id> on <target> <verb> it <prep> <json>,
  <condition-clause>, <start-clause>, <end-clause>, and <supersession-clause>.

Supported verbs:
  defines it as
  replaces it with
  overrides it with
  creates an exception for it with value

Condition clauses:
  is unconditional
  applies when <canonical-json-object>

Start clauses:
  has no start date
  is valid from YYYY-MM-DD

End clauses:
  has no end date
  is valid until YYYY-MM-DD

Supersession clauses:
  supersedes nothing
  supersedes <effect-id list>

The word "complete" is part of the syntax and certifies a one-effect inventory
for the named target. This grammar is bounded and exact. Unrecognized prose has
zero authority.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
import re
from typing import Any, Mapping

SCHEMA="BRAIN_CERTIFIED_COMPOSITIONAL_NATURAL_EFFECT_CLAUSE_V1"
_TOKEN=r"[A-Za-z0-9_.:-]+"
_LIST_TOKEN=re.compile(r"^[A-Za-z0-9_.:-]+$")

_RE=re.compile(
    rf"^The complete effect (?P<eid>{_TOKEN}) on (?P<target>{_TOKEN}) "
    rf"(?P<body>.+), (?P<condition>.+), (?P<start>.+), "
    rf"(?P<end>.+), and (?P<sup>.+)\.$"
)

_ACTIONS=(
    ("defines it as ", "DEFINE"),
    ("replaces it with ", "REPLACE"),
    ("overrides it with ", "OVERRIDE"),
    ("creates an exception for it with value ", "EXCEPTION"),
)


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _token(v:str,name:str)->str:
    if not isinstance(v,str) or not v or v.strip()!=v or not _LIST_TOKEN.match(v):
        raise ValueError(name+"_INVALID")
    return v


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


def _ids(raw:str)->list[str]:
    if raw=="nothing":
        return []
    normalized=raw.replace(", and "," and ")
    parts=[]
    for chunk in normalized.split(" and "):
        parts.extend(chunk.split(", "))
    out=[_token(x,"SUPERSEDES_ID") for x in parts]
    if not out or len(out)!=len(set(out)):
        raise ValueError("SUPERSEDES_IDS_INVALID_OR_DUPLICATE")
    return out


def parse_compositional_effect_clauses(text:str,*,source:str="source")->dict[str,Any]:
    if not isinstance(text,str) or not text:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"SOURCE_TEXT_MISSING","terminal_authority":False}
    if not isinstance(source,str) or not source.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"SOURCE_ID_MISSING","terminal_authority":False}

    clauses=[]; char_offset=0; byte_offset=0; seen_targets=set()
    try:
        for line in text.splitlines(keepends=True):
            body=line.rstrip("\r\n")
            raw_bytes=body.encode("utf-8")
            m=_RE.match(body)
            if m:
                eid=_token(m.group("eid"),"EFFECT_ID")
                target=_token(m.group("target"),"TARGET_ID")
                if target in seen_targets:
                    raise ValueError("DUPLICATE_COMPLETE_TARGET:"+target)
                seen_targets.add(target)

                action_text=m.group("body")
                effect_class=None; value=None
                for prefix,cls in _ACTIONS:
                    if action_text.startswith(prefix):
                        effect_class=cls
                        value=_json(action_text[len(prefix):],"VALUE")
                        break
                if effect_class is None:
                    raise ValueError("ACTION_UNSUPPORTED")

                cond=m.group("condition")
                if cond=="is unconditional":
                    conditions={}
                elif cond.startswith("applies when "):
                    conditions=_json(cond[len("applies when "):],"CONDITIONS")
                    if not isinstance(conditions,Mapping):
                        raise ValueError("CONDITIONS_NOT_OBJECT")
                    conditions=dict(conditions)
                else:
                    raise ValueError("CONDITION_CLAUSE_UNSUPPORTED")

                start=m.group("start")
                if start=="has no start date":
                    valid_from=None
                elif start.startswith("is valid from "):
                    valid_from=_date(start[len("is valid from "):],"VALID_FROM")
                else:
                    raise ValueError("START_CLAUSE_UNSUPPORTED")

                end=m.group("end")
                if end=="has no end date":
                    valid_until=None
                elif end.startswith("is valid until "):
                    valid_until=_date(end[len("is valid until "):],"VALID_UNTIL")
                else:
                    raise ValueError("END_CLAUSE_UNSUPPORTED")

                sup=m.group("sup")
                if not sup.startswith("supersedes "):
                    raise ValueError("SUPERSESSION_CLAUSE_UNSUPPORTED")
                supersedes=_ids(sup[len("supersedes "):])

                payload={
                    "effect_id":eid,
                    "target_id":target,
                    "effect_class":effect_class,
                    "value":value,
                    "conditions":conditions,
                    "valid_from":valid_from,
                    "valid_until":valid_until,
                    "supersedes":supersedes,
                }
                start_char=char_offset
                end_char=char_offset+len(body)
                start_byte=byte_offset
                end_byte=byte_offset+len(raw_bytes)
                digest=sha256(raw_bytes).hexdigest()
                clause_id="COMP-EFFECT-"+sha256(
                    (source+"\0"+str(start_byte)+"\0"+str(end_byte)+"\0"+_canon(payload)).encode("utf-8")
                ).hexdigest()[:24]
                clauses.append({
                    "clause_id":clause_id,
                    "source_id":source,
                    "effect":payload,
                    "inventory":{"target_id":target,"effect_ids":[eid]},
                    "source_span_chars":[start_char,end_char],
                    "source_span_bytes":[start_byte,end_byte],
                    "source_text_sha256":digest,
                })
            char_offset+=len(line)
            byte_offset+=len(line.encode("utf-8"))
    except Exception as exc:
        return {
            "schema":SCHEMA,"status":"UNRESOLVED",
            "reason":type(exc).__name__+":"+str(exc),
            "terminal_authority":False,
        }

    return {
        "schema":SCHEMA,
        "status":"PARSED",
        "clauses":clauses,
        "terminal_authority":False,
        "scope":"BOUNDED_COMPLETE_SINGLE_EFFECT_SENTENCE_PER_TARGET",
    }
