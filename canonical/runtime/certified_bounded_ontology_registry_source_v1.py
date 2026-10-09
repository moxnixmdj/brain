"""Certified bounded ontology registry source V1.

Recognizes one exact source declaration:

    Bounded ontology registry: <canonical-json>

The JSON payload is the existing bounded concept-registry schema. This parser
does not infer an ontology. It only binds exact source bytes to a finite registry
declaration, then reuses the Brain's canonical registry validator.

The source declaration itself explicitly carries bounded-finite scope,
concept surfaces/attributes, complete terminal signatures, and complete
observation maps. No open-world ontology completeness is claimed.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from canonical.runtime.bounded_authenticated_concept_universe_v1 import (
    REGISTRY_SCHEMA,
    validate_registry,
)

SCHEMA="PROJECT_BRAIN_CERTIFIED_BOUNDED_ONTOLOGY_REGISTRY_SOURCE_V1"
PREFIX="Bounded ontology registry: "


def _canon(v:Any)->str:
    return json.dumps(
        v,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"FAIL_CLOSED",
        "pass":False,
        "reason":reason,
        "semantic_truth_authority":False,
        "terminal_authority":False,
        **extra,
    }


def parse(source_text:str,*,source_id:str="source")->dict[str,Any]:
    if not isinstance(source_text,str) or not source_text:
        return _fail("SOURCE_TEXT_MISSING")
    if not isinstance(source_id,str) or not source_id.strip():
        return _fail("SOURCE_ID_MISSING")
    if "\n" in source_text or "\r" in source_text:
        return _fail("EXACT_SINGLE_SOURCE_LINE_REQUIRED")
    if not source_text.startswith(PREFIX):
        return _fail("BOUNDED_ONTOLOGY_REGISTRY_PREFIX_REQUIRED")
    payload=source_text[len(PREFIX):]
    try:
        raw=json.loads(payload)
    except Exception as exc:
        return _fail("REGISTRY_JSON_INVALID",detail=type(exc).__name__+":"+str(exc))
    if not isinstance(raw,dict):
        return _fail("REGISTRY_JSON_NOT_OBJECT")
    if raw.get("schema")!=REGISTRY_SCHEMA:
        return _fail("REGISTRY_SCHEMA_INVALID")
    if _canon(raw)!=payload:
        return _fail("REGISTRY_JSON_NOT_CANONICAL")
    try:
        checked=validate_registry(raw)
    except Exception as exc:
        return _fail("REGISTRY_VALIDATION_FAILED",detail=type(exc).__name__+":"+str(exc))

    registry=checked["registry"]
    return {
        "schema":SCHEMA,
        "status":"PARSED",
        "pass":True,
        "source_id":source_id.strip(),
        "source_text_sha256":sha256(source_text.encode("utf-8")).hexdigest(),
        "source_span_bytes":[0,len(source_text.encode("utf-8"))],
        "registry":registry,
        "registry_sha256":checked["registry_sha256"],
        "registry_id":registry["registry_id"],
        "scope_id":registry["scope_id"],
        "concept_ids":checked["concept_ids"],
        "semantic_truth_authority":False,
        "terminal_authority":False,
        "boundary":"EXACT_SOURCE_DECLARED_BOUNDED_FINITE_ONTOLOGY_REGISTRY_ONLY__NO_OPEN_WORLD_COMPLETENESS",
    }
