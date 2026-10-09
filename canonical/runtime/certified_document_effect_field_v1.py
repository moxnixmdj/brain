"""Certified explicit document-effect field fragment V1.

Recognizes standalone source lines of the exact form:

    Effect field: {"effect_id":"B.t","field":"effect_class","value":"REPLACE"}

The payload must be canonical JSON with the exact field set:
    effect_id, field, value

Each line proves only one semantic coordinate of one effect. Cross-field
consistency is deliberately NOT inferred here; the semantic lattice assembles
and validates the complete effect only after all required coordinates are exact.

Supported fields:
    target_id
    effect_class
    value
    conditions
    valid_from
    valid_until
    supersedes
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import cross_document_effect_calculus_v1 as calculus

SCHEMA="BRAIN_CERTIFIED_DOCUMENT_EFFECT_FIELD_V1"
PREFIX="Effect field: "
FIELDS=frozenset({
    "target_id",
    "effect_class",
    "value",
    "conditions",
    "valid_from",
    "valid_until",
    "supersedes",
})


def _canon(value:Any)->str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _token(value:Any,name:str)->str:
    if not isinstance(value,str) or not value.strip():
        raise ValueError(name+"_INVALID")
    cleaned=value.strip()
    if cleaned!=value:
        raise ValueError(name+"_NOT_CANONICAL")
    return cleaned


def _normalize_field(field:str,value:Any)->Any:
    if field=="target_id":
        return _token(value,"TARGET_ID")

    if field=="effect_class":
        raw=_token(value,"EFFECT_CLASS")
        upper=raw.upper()
        if raw!=upper:
            raise ValueError("EFFECT_CLASS_NOT_CANONICAL")
        if upper not in calculus.EFFECT_CLASSES:
            raise ValueError("EFFECT_CLASS_UNSUPPORTED:"+upper)
        return upper

    if field=="conditions":
        if not isinstance(value,Mapping):
            raise ValueError("CONDITIONS_NOT_OBJECT")
        clean={}
        for key,item in value.items():
            k=_token(key,"CONDITION_KEY")
            _canon(item)
            clean[k]=item
        return dict(sorted(clean.items()))

    if field in {"valid_from","valid_until"}:
        if value is None:
            return None
        if not isinstance(value,str):
            raise ValueError(field.upper()+"_INVALID")
        try:
            parsed=date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(field.upper()+"_INVALID") from exc
        if parsed.isoformat()!=value:
            raise ValueError(field.upper()+"_NOT_CANONICAL")
        return value

    if field=="supersedes":
        if (
            not isinstance(value,Sequence)
            or isinstance(value,(str,bytes))
            or any(not isinstance(x,str) or not x.strip() for x in value)
        ):
            raise ValueError("SUPERSEDES_INVALID")
        clean=[_token(x,"SUPERSEDES_ID") for x in value]
        if len(clean)!=len(set(clean)):
            raise ValueError("SUPERSEDES_DUPLICATE")
        return clean

    if field=="value":
        _canon(value)
        return value

    raise ValueError("FIELD_UNSUPPORTED:"+field)


def parse_effect_fields(text:str,*,source:str="source")->dict[str,Any]:
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

    rows=[]
    seen=set()
    char_offset=0
    byte_offset=0

    for line in text.splitlines(keepends=True):
        body=line.rstrip("\r\n")
        body_bytes=body.encode("utf-8")
        if body.startswith(PREFIX):
            payload=body[len(PREFIX):]
            try:
                parsed=json.loads(payload)
            except Exception:
                return {
                    "schema":SCHEMA,"status":"UNRESOLVED",
                    "reason":"EFFECT_FIELD_JSON_INVALID",
                    "terminal_authority":False,
                }
            if not isinstance(parsed,Mapping) or set(parsed)!={"effect_id","field","value"}:
                return {
                    "schema":SCHEMA,"status":"UNRESOLVED",
                    "reason":"EFFECT_FIELD_FIELD_SET_NOT_EXACT",
                    "terminal_authority":False,
                }
            if _canon(parsed)!=payload:
                return {
                    "schema":SCHEMA,"status":"UNRESOLVED",
                    "reason":"EFFECT_FIELD_JSON_NOT_CANONICAL",
                    "terminal_authority":False,
                }

            try:
                effect_id=_token(parsed.get("effect_id"),"EFFECT_ID")
                field=_token(parsed.get("field"),"FIELD")
                if field not in FIELDS:
                    raise ValueError("FIELD_UNSUPPORTED:"+field)
                value=_normalize_field(field,parsed.get("value"))
            except Exception as exc:
                return {
                    "schema":SCHEMA,"status":"UNRESOLVED",
                    "reason":"EFFECT_FIELD_INVALID:"+type(exc).__name__+":"+str(exc),
                    "terminal_authority":False,
                }

            slot=(effect_id,field)
            if slot in seen:
                return {
                    "schema":SCHEMA,"status":"UNRESOLVED",
                    "reason":"DUPLICATE_EFFECT_FIELD_SLOT",
                    "effect_id":effect_id,
                    "field":field,
                    "terminal_authority":False,
                }
            seen.add(slot)

            c0=char_offset
            c1=char_offset+len(body)
            b0=byte_offset
            b1=byte_offset+len(body_bytes)
            digest=sha256(body_bytes).hexdigest()
            field_id="EFFECT-FIELD-"+sha256(
                (
                    source+"\0"+effect_id+"\0"+field+"\0"
                    +str(b0)+"\0"+str(b1)+"\0"+_canon(value)
                ).encode("utf-8")
            ).hexdigest()[:24]
            rows.append({
                "field_id":field_id,
                "source_id":source,
                "effect_id":effect_id,
                "field":field,
                "value":value,
                "source_span_chars":[c0,c1],
                "source_span_bytes":[b0,b1],
                "source_text_sha256":digest,
            })

        char_offset+=len(line)
        byte_offset+=len(line.encode("utf-8"))

    return {
        "schema":SCHEMA,
        "status":"PARSED",
        "fields":sorted(rows,key=lambda x:(x["effect_id"],x["field"])),
        "terminal_authority":False,
        "scope":"EXPLICIT_CANONICAL_DOCUMENT_EFFECT_FIELD_LINES_ONLY",
    }
