"""Certified exact bounded semantic universe/extension declarations V1.

Recognizes standalone canonical lines:

  Semantic universe: {"members":["a","b"],"scope_id":"scope"}
  Semantic extension: {"concept_id":"L","members":["a"],"scope_id":"scope"}

The words "universe" and "extension" in this deliberately bounded grammar mean
complete finite declarations for that scope. Unrecognized prose receives no
authority. Duplicate declarations for the same semantic slot fail unresolved.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA="BRAIN_CERTIFIED_BOUNDED_SEMANTIC_EXTENSION_SOURCE_V1"
UNIVERSE_PREFIX="Semantic universe: "
EXTENSION_PREFIX="Semantic extension: "


def _canon(value:Any)->str:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False,
    )


def _token(value:Any,name:str)->str:
    if not isinstance(value,str) or not value.strip() or value.strip()!=value:
        raise ValueError(name+"_INVALID")
    return value


def _members(value:Any,name:str)->list[str]:
    if not isinstance(value,list):
        raise ValueError(name+"_NOT_LIST")
    out=[_token(x,name+"_ITEM") for x in value]
    if len(out)!=len(set(out)):
        raise ValueError(name+"_DUPLICATE")
    if out!=sorted(out):
        raise ValueError(name+"_NOT_SORTED")
    return out


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

    universes={}
    extensions={}
    char_offset=0
    byte_offset=0

    for line in text.splitlines(keepends=True):
        body=line.rstrip("\r\n")
        raw=body.encode("utf-8")
        kind=None
        payload=None
        if body.startswith(UNIVERSE_PREFIX):
            kind="UNIVERSE"
            payload=body[len(UNIVERSE_PREFIX):]
        elif body.startswith(EXTENSION_PREFIX):
            kind="EXTENSION"
            payload=body[len(EXTENSION_PREFIX):]

        if kind is not None:
            try:
                obj=json.loads(payload)
                if not isinstance(obj,Mapping) or _canon(obj)!=payload:
                    raise ValueError("JSON_NOT_CANONICAL")
                scope=_token(obj.get("scope_id"),"SCOPE_ID")
                if kind=="UNIVERSE":
                    if set(obj)!={"scope_id","members"}:
                        raise ValueError("UNIVERSE_FIELD_SET_INVALID")
                    members=_members(obj.get("members"),"UNIVERSE_MEMBERS")
                    key=scope
                    if key in universes:
                        raise ValueError("DUPLICATE_UNIVERSE_SCOPE")
                    universes[key]={
                        "scope_id":scope,
                        "members":members,
                        "source_id":source,
                        "source_span_chars":[char_offset,char_offset+len(body)],
                        "source_span_bytes":[byte_offset,byte_offset+len(raw)],
                        "source_text_sha256":sha256(raw).hexdigest(),
                    }
                else:
                    if set(obj)!={"scope_id","concept_id","members"}:
                        raise ValueError("EXTENSION_FIELD_SET_INVALID")
                    concept=_token(obj.get("concept_id"),"CONCEPT_ID")
                    members=_members(obj.get("members"),"EXTENSION_MEMBERS")
                    key=(scope,concept)
                    if key in extensions:
                        raise ValueError("DUPLICATE_EXTENSION_SLOT")
                    extensions[key]={
                        "scope_id":scope,
                        "concept_id":concept,
                        "members":members,
                        "source_id":source,
                        "source_span_chars":[char_offset,char_offset+len(body)],
                        "source_span_bytes":[byte_offset,byte_offset+len(raw)],
                        "source_text_sha256":sha256(raw).hexdigest(),
                    }
            except Exception as exc:
                return {
                    "schema":SCHEMA,
                    "status":"UNRESOLVED",
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
        "universes":[universes[k] for k in sorted(universes)],
        "extensions":[extensions[k] for k in sorted(extensions)],
        "terminal_authority":False,
        "boundary":"EXACT_CANONICAL_COMPLETE_BOUNDED_UNIVERSE_AND_EXTENSION_DECLARATIONS_ONLY",
    }
