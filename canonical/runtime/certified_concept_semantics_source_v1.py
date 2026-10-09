"""Certified explicit concept-semantics source declarations V1.

Recognizes canonical standalone lines:
  Concept semantics: {"concept_id":"C","formula":{"id":"ATOM","op":"ATOM"},"scope_id":"s"}

The declaration is exact only for the named concept and scope. It grants no
open-world concept inventory or ontology completeness.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA="BRAIN_CERTIFIED_CONCEPT_SEMANTICS_SOURCE_V1"
PREFIX="Concept semantics: "


def _canon(value:Any)->str:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False,
    )


def _token(value:Any,name:str)->str:
    if not isinstance(value,str) or not value.strip() or value.strip()!=value:
        raise ValueError(name+"_INVALID")
    return value


def parse(text:str,*,source_id:str)->dict[str,Any]:
    if not isinstance(text,str) or not text:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "reason":"SOURCE_TEXT_REQUIRED","terminal_authority":False,
        }
    try:
        source=_token(source_id,"SOURCE_ID")
    except Exception as exc:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "reason":type(exc).__name__+":"+str(exc),
            "terminal_authority":False,
        }

    rows={}
    char_offset=0
    byte_offset=0
    for line in text.splitlines(keepends=True):
        body=line.rstrip("\r\n")
        raw=body.encode("utf-8")
        if body.startswith(PREFIX):
            payload=body[len(PREFIX):]
            try:
                obj=json.loads(payload)
                if (
                    not isinstance(obj,Mapping)
                    or set(obj)!={"scope_id","concept_id","formula"}
                    or _canon(obj)!=payload
                ):
                    raise ValueError("CONCEPT_SEMANTICS_JSON_NOT_EXACT_CANONICAL")
                scope=_token(obj.get("scope_id"),"SCOPE_ID")
                concept=_token(obj.get("concept_id"),"CONCEPT_ID")
                formula=obj.get("formula")
                if not isinstance(formula,Mapping):
                    raise ValueError("FORMULA_NOT_OBJECT")
                _canon(formula)
                key=(scope,concept)
                if key in rows:
                    raise ValueError("DUPLICATE_CONCEPT_SEMANTICS_SLOT")
                rows[key]={
                    "scope_id":scope,
                    "concept_id":concept,
                    "formula":dict(formula),
                    "source_id":source,
                    "source_span_chars":[char_offset,char_offset+len(body)],
                    "source_span_bytes":[byte_offset,byte_offset+len(raw)],
                    "source_text_sha256":sha256(raw).hexdigest(),
                }
            except Exception as exc:
                return {
                    "schema":SCHEMA,"status":"UNRESOLVED",
                    "reason":type(exc).__name__+":"+str(exc),
                    "source_span_chars":[char_offset,char_offset+len(body)],
                    "source_span_bytes":[byte_offset,byte_offset+len(raw)],
                    "terminal_authority":False,
                }

        char_offset+=len(line)
        byte_offset+=len(line.encode("utf-8"))

    return {
        "schema":SCHEMA,
        "status":"PARSED",
        "source_id":source,
        "concept_semantics":[rows[k] for k in sorted(rows)],
        "terminal_authority":False,
        "boundary":"EXACT_CANONICAL_CONCEPT_FORMULA_DECLARATIONS_ONLY",
    }
