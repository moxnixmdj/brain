"""Source-declared bounded concept registry authority V1.

This module authenticates a bounded concept registry only when a separate exact
source declaration explicitly binds:
- registry_id,
- scope_id,
- canonical registry_sha256,
- scope_completeness_authenticated = true,
- concept_semantics_authenticated = true.

The registry cannot authenticate itself. The declaration is parsed from exact
source bytes and the authority receipt is recomputed from those bytes.

Recognized line:
  Bounded concept registry authority: <canonical-json>

The JSON field set is exact:
  registry_id
  registry_sha256
  scope_id
  scope_completeness_authenticated
  concept_semantics_authenticated

This proves only what the source explicitly declares about that exact bounded
registry. It does not imply open-world ontology completeness.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping

from canonical.runtime.bounded_authenticated_concept_universe_v1 import (
    AUTHORITY_SCHEMA,
)

SCHEMA="PROJECT_BRAIN_SOURCE_DECLARED_BOUNDED_CONCEPT_REGISTRY_AUTHORITY_V1"
EVIDENCE_SCHEMA="PROJECT_BRAIN_SOURCE_DECLARED_BOUNDED_CONCEPT_REGISTRY_AUTHORITY_EVIDENCE_V1"
PREFIX="Bounded concept registry authority: "
FIELDS={
    "registry_id",
    "registry_sha256",
    "scope_id",
    "scope_completeness_authenticated",
    "concept_semantics_authenticated",
}
_SHA256=re.compile(r"^[0-9a-f]{64}$")


def _canon(value:Any)->str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "pass":False,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "semantic_truth_authority":False,
        "source_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        **extra,
    }


def _parse_line(source_text:str)->dict[str,Any]:
    if not isinstance(source_text,str) or not source_text:
        raise ValueError("SOURCE_TEXT_REQUIRED")
    matches=[]
    char_offset=0
    byte_offset=0
    for line in source_text.splitlines(keepends=True):
        body=line.rstrip("\r\n")
        if body.startswith(PREFIX):
            payload=body[len(PREFIX):]
            try:
                row=json.loads(payload)
            except Exception as exc:
                raise ValueError("AUTHORITY_JSON_INVALID") from exc
            if not isinstance(row,Mapping) or set(row)!=FIELDS:
                raise ValueError("AUTHORITY_FIELD_SET_NOT_EXACT")
            if _canon(row)!=payload:
                raise ValueError("AUTHORITY_JSON_NOT_CANONICAL")
            if not isinstance(row.get("registry_id"),str) or not row["registry_id"].strip():
                raise ValueError("REGISTRY_ID_INVALID")
            if not isinstance(row.get("scope_id"),str) or not row["scope_id"].strip():
                raise ValueError("SCOPE_ID_INVALID")
            if _SHA256.fullmatch(str(row.get("registry_sha256") or "")) is None:
                raise ValueError("REGISTRY_SHA256_INVALID")
            if row.get("scope_completeness_authenticated") is not True:
                raise ValueError("SCOPE_COMPLETENESS_NOT_DECLARED")
            if row.get("concept_semantics_authenticated") is not True:
                raise ValueError("CONCEPT_SEMANTICS_NOT_DECLARED")
            body_bytes=body.encode("utf-8")
            matches.append({
                "declaration":dict(row),
                "source_span_chars":[char_offset,char_offset+len(body)],
                "source_span_bytes":[byte_offset,byte_offset+len(body_bytes)],
                "source_text_sha256":sha256(body_bytes).hexdigest(),
            })
        char_offset+=len(line)
        byte_offset+=len(line.encode("utf-8"))
    if not matches:
        raise ValueError("AUTHORITY_DECLARATION_NOT_FOUND")
    if len(matches)!=1:
        raise ValueError("MULTIPLE_AUTHORITY_DECLARATIONS")
    return matches[0]


def make_evidence(
    source_text:str,
    *,
    source_id:str,
)->dict[str,Any]:
    if not isinstance(source_id,str) or not source_id.strip():
        raise ValueError("SOURCE_ID_REQUIRED")
    parsed=_parse_line(source_text)
    core={
        "schema":EVIDENCE_SCHEMA,
        "source_id":source_id.strip(),
        "source_text":source_text,
        "source_sha256":sha256(source_text.encode("utf-8")).hexdigest(),
        "source_span_chars":list(parsed["source_span_chars"]),
        "source_span_bytes":list(parsed["source_span_bytes"]),
        "declaration":dict(parsed["declaration"]),
    }
    out=dict(core)
    out["evidence_sha256"]=sha256(_canon(core).encode("utf-8")).hexdigest()
    return out


def supports(raw:Any)->bool:
    return isinstance(raw,Mapping) and raw.get("schema")==EVIDENCE_SCHEMA


def verify(raw:Mapping[str,Any])->dict[str,Any]:
    try:
        if not isinstance(raw,Mapping) or raw.get("schema")!=EVIDENCE_SCHEMA:
            return _fail("EVIDENCE_SCHEMA_INVALID")
        allowed={
            "schema","source_id","source_text","source_sha256",
            "source_span_chars","source_span_bytes","declaration",
            "evidence_sha256",
        }
        if set(raw)!=allowed:
            return _fail(
                "EVIDENCE_FIELD_SET_INVALID",
                extra_fields=sorted(set(raw)-allowed),
                missing_fields=sorted(allowed-set(raw)),
            )

        source_id=str(raw.get("source_id") or "").strip()
        source_text=raw.get("source_text")
        if not source_id:
            return _fail("SOURCE_ID_REQUIRED")
        if not isinstance(source_text,str) or not source_text:
            return _fail("SOURCE_TEXT_REQUIRED")
        actual_source_sha=sha256(source_text.encode("utf-8")).hexdigest()
        if raw.get("source_sha256")!=actual_source_sha:
            return _fail("SOURCE_SHA256_MISMATCH")

        core={
            key:raw[key]
            for key in (
                "schema","source_id","source_text","source_sha256",
                "source_span_chars","source_span_bytes","declaration",
            )
        }
        if raw.get("evidence_sha256")!=sha256(
            _canon(core).encode("utf-8")
        ).hexdigest():
            return _fail("EVIDENCE_SHA256_MISMATCH")

        parsed=_parse_line(source_text)
        if raw.get("source_span_chars")!=parsed["source_span_chars"]:
            return _fail("SOURCE_SPAN_CHARS_MISMATCH")
        if raw.get("source_span_bytes")!=parsed["source_span_bytes"]:
            return _fail("SOURCE_SPAN_BYTES_MISMATCH")
        if raw.get("declaration")!=parsed["declaration"]:
            return _fail("DECLARATION_MISMATCH")

        decl=parsed["declaration"]
        receipt_core={
            "pass":True,
            "schema":AUTHORITY_SCHEMA,
            "registry_sha256":decl["registry_sha256"],
            "registry_id":decl["registry_id"],
            "scope_id":decl["scope_id"],
            "scope_completeness_authenticated":True,
            "concept_semantics_authenticated":True,
            "verification_authority_mutated":False,
            "source_authority_evidence_sha256":raw["evidence_sha256"],
            "source_authority_source_id":source_id,
            "source_authority_source_sha256":actual_source_sha,
            "open_world_ontology_complete":False,
        }
        receipt=dict(receipt_core)
        receipt["receipt_sha256"]=sha256(
            _canon(receipt_core).encode("utf-8")
        ).hexdigest()
        return receipt
    except Exception as exc:
        return _fail(type(exc).__name__+":"+str(exc))
