"""Certified explicit document-effect relation fragment V1.

Recognizes standalone lines:
  Effect relation: <canonical-json>

The JSON must contain the exact effect semantic fields except source_locator,
which is derived from the exact source byte span. The resulting effect is
validated by the same cross-document effect calculus used during execution.

This proves only the explicit relation on that line. It does not prove that
unrecognized prose is inert or that all effects have been enumerated.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from canonical.runtime import cross_document_effect_calculus_v1 as calculus

SCHEMA="BRAIN_CERTIFIED_DOCUMENT_EFFECT_RELATION_V1"
PREFIX="Effect relation: "
FIELDS={
    "effect_id","target_id","effect_class","value","conditions",
    "valid_from","valid_until","supersedes",
}


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _fail(status:str,reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":status,"reason":reason,
        "terminal_authority":False,**extra,
    }


def parse_effect_relations(text:str,*,source:str="source")->dict[str,Any]:
    if not isinstance(text,str) or not text:
        return _fail("FAIL_CLOSED","SOURCE_TEXT_MISSING")
    if not isinstance(source,str) or not source.strip():
        return _fail("FAIL_CLOSED","SOURCE_ID_MISSING")

    rows=[]; seen=set(); char_offset=0; byte_offset=0
    for line in text.splitlines(keepends=True):
        body=line.rstrip("\r\n")
        body_bytes=body.encode("utf-8")
        if body.startswith(PREFIX):
            payload=body[len(PREFIX):]
            try:
                obj=json.loads(payload)
            except Exception:
                return _fail("UNRESOLVED","EFFECT_RELATION_JSON_INVALID")
            if not isinstance(obj,dict) or set(obj)!=FIELDS:
                return _fail("UNRESOLVED","EFFECT_RELATION_FIELD_SET_NOT_EXACT")
            if _canon(obj)!=payload:
                return _fail("UNRESOLVED","EFFECT_RELATION_JSON_NOT_CANONICAL")

            b0=byte_offset; b1=byte_offset+len(body_bytes)
            effect=dict(obj)
            effect["source_locator"]=f"{source}:{b0}-{b1}"
            try:
                effect=calculus._validate_effect(effect)
            except Exception as exc:
                return _fail(
                    "UNRESOLVED",
                    "EFFECT_RELATION_INVALID:"+type(exc).__name__+":"+str(exc),
                )
            eid=str(effect["effect_id"])
            if eid in seen:
                return _fail("UNRESOLVED","DUPLICATE_EFFECT_RELATION_ID",effect_id=eid)
            seen.add(eid)
            digest=sha256(body_bytes).hexdigest()
            relation_id="EFFECT-RELATION-"+sha256(
                (source+"\0"+eid+"\0"+str(b0)+"\0"+str(b1)+"\0"+_canon(effect)).encode("utf-8")
            ).hexdigest()[:24]
            rows.append({
                "relation_id":relation_id,
                "source_id":source,
                "effect":effect,
                "source_span_chars":[char_offset,char_offset+len(body)],
                "source_span_bytes":[b0,b1],
                "source_text_sha256":digest,
            })
        char_offset+=len(line)
        byte_offset+=len(line.encode("utf-8"))

    return {
        "schema":SCHEMA,
        "status":"PARSED",
        "relations":sorted(rows,key=lambda x:x["effect"]["effect_id"]),
        "terminal_authority":False,
        "scope":"EXPLICIT_CANONICAL_DOCUMENT_EFFECT_RELATION_LINES_ONLY",
    }
