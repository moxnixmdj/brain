"""Certified explicit document-effect dimension fragment V1.

Recognizes standalone source lines:
  Effect <ID> target: <TARGET>.
  Effect <ID> class: <DEFINE|REPLACE|EXCEPTION|OVERRIDE>.
  Effect <ID> value JSON: <canonical-json>.
  Effect <ID> conditions JSON: <canonical-json-object>.
  Effect <ID> valid from: <YYYY-MM-DD|none>.
  Effect <ID> valid until: <YYYY-MM-DD|none>.
  Effect <ID> supersedes: <comma-separated IDs|none>.

Each line proves only one dimension. Duplicate declarations for the same
(effect_id, dimension) make that dimension unresolved. No line proves inventory
completeness or the meaning of unrelated prose.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
import re
from typing import Any

from canonical.runtime.cross_document_effect_calculus_v1 import EFFECT_CLASSES

SCHEMA="BRAIN_CERTIFIED_DOCUMENT_EFFECT_DIMENSION_V1"
_ID=r"[A-Za-z0-9_.:-]+"
_PATTERNS=[
    ("target",re.compile(rf"^Effect\s+(?P<eid>{_ID})\s+target:\s*(?P<value>{_ID})\.$")),
    ("effect_class",re.compile(rf"^Effect\s+(?P<eid>{_ID})\s+class:\s*(?P<value>[A-Za-z]+)\.$")),
    ("value",re.compile(rf"^Effect\s+(?P<eid>{_ID})\s+value JSON:\s*(?P<value>.+)\.$")),
    ("conditions",re.compile(rf"^Effect\s+(?P<eid>{_ID})\s+conditions JSON:\s*(?P<value>.+)\.$")),
    ("valid_from",re.compile(rf"^Effect\s+(?P<eid>{_ID})\s+valid from:\s*(?P<value>[^.]+)\.$")),
    ("valid_until",re.compile(rf"^Effect\s+(?P<eid>{_ID})\s+valid until:\s*(?P<value>[^.]+)\.$")),
    ("supersedes",re.compile(rf"^Effect\s+(?P<eid>{_ID})\s+supersedes:\s*(?P<value>.+)\.$")),
]


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _parse_value(dim:str,raw:str)->Any:
    if dim=="target":
        return raw.strip()
    if dim=="effect_class":
        val=raw.strip().upper()
        if val not in EFFECT_CLASSES:
            raise ValueError("EFFECT_CLASS_UNSUPPORTED:"+val)
        return val
    if dim=="value":
        try: val=json.loads(raw)
        except Exception as exc: raise ValueError("VALUE_JSON_INVALID") from exc
        if _canon(val)!=raw:
            raise ValueError("VALUE_JSON_NOT_CANONICAL")
        return val
    if dim=="conditions":
        try: val=json.loads(raw)
        except Exception as exc: raise ValueError("CONDITIONS_JSON_INVALID") from exc
        if not isinstance(val,dict):
            raise ValueError("CONDITIONS_NOT_OBJECT")
        if _canon(val)!=raw:
            raise ValueError("CONDITIONS_JSON_NOT_CANONICAL")
        for key in val:
            if not isinstance(key,str) or not key.strip():
                raise ValueError("CONDITION_KEY_INVALID")
        return dict(sorted(val.items()))
    if dim in {"valid_from","valid_until"}:
        txt=raw.strip()
        if txt.lower()=="none":
            return None
        try: return date.fromisoformat(txt).isoformat()
        except ValueError as exc: raise ValueError(dim.upper()+"_INVALID") from exc
    if dim=="supersedes":
        txt=raw.strip()
        if txt.lower()=="none":
            return []
        vals=[x.strip() for x in txt.split(",")]
        if any(not x for x in vals):
            raise ValueError("SUPERSEDES_INVALID")
        if len(vals)!=len(set(vals)):
            raise ValueError("SUPERSEDES_DUPLICATE")
        if any(re.fullmatch(_ID,x) is None for x in vals):
            raise ValueError("SUPERSEDES_ID_INVALID")
        return vals
    raise ValueError("DIMENSION_UNSUPPORTED:"+dim)


def parse_effect_dimensions(text:str,*,source:str="source")->dict[str,Any]:
    if not isinstance(text,str) or not text:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"SOURCE_TEXT_MISSING","terminal_authority":False}
    if not isinstance(source,str) or not source.strip():
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"SOURCE_ID_MISSING","terminal_authority":False}

    rows=[]; seen={}; duplicates=[]; char_offset=0; byte_offset=0
    for line in text.splitlines(keepends=True):
        body=line.rstrip("\r\n")
        body_bytes=body.encode("utf-8")
        matched=None
        for dim,regex in _PATTERNS:
            m=regex.fullmatch(body)
            if m is not None:
                matched=(dim,m)
                break
        if matched is not None:
            dim,m=matched
            eid=m.group("eid")
            key=(eid,dim)
            if key in seen:
                duplicates.append({"effect_id":eid,"dimension":dim})
            try:
                value=_parse_value(dim,m.group("value"))
            except Exception as exc:
                return {
                    "schema":SCHEMA,"status":"UNRESOLVED",
                    "reason":type(exc).__name__+":"+str(exc),
                    "effect_id":eid,"dimension":dim,
                    "terminal_authority":False,
                }
            b0=byte_offset; b1=byte_offset+len(body_bytes)
            row={
                "effect_id":eid,
                "dimension":dim,
                "value":value,
                "source_id":source,
                "source_span_chars":[char_offset,char_offset+len(body)],
                "source_span_bytes":[b0,b1],
                "source_text_sha256":sha256(body_bytes).hexdigest(),
            }
            row["dimension_id"]="EFFECT-DIM-"+sha256(
                (source+"\0"+eid+"\0"+dim+"\0"+str(b0)+"\0"+str(b1)+"\0"+_canon(value)).encode("utf-8")
            ).hexdigest()[:24]
            rows.append(row)
            seen[key]=row
        char_offset+=len(line)
        byte_offset+=len(line.encode("utf-8"))

    if duplicates:
        return {
            "schema":SCHEMA,"status":"UNRESOLVED",
            "reason":"DUPLICATE_EFFECT_DIMENSION_DECLARATION",
            "duplicates":sorted(duplicates,key=lambda x:(x["effect_id"],x["dimension"])),
            "terminal_authority":False,
        }
    return {
        "schema":SCHEMA,
        "status":"PARSED",
        "dimensions":sorted(rows,key=lambda x:(x["effect_id"],x["dimension"])),
        "terminal_authority":False,
        "scope":"EXPLICIT_SINGLE_EFFECT_DIMENSION_LINES_ONLY",
    }
