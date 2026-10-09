"""Brain-owned semantic relation edge authority V1.

This module eliminates an arbitrary verifier callback for the subset of semantic
relations the Brain can already authenticate end-to-end from raw source bytes.

Supported proof class:
  EXPLICIT_SOURCE_IDENTITY

The evidence binds:
- exact scope,
- left/right concept ids and surfaces,
- exact source-definition rows,
- requested edge relation.

The authority recomputes semantic_relation_control_v1. Only a proved semantic
identity may emit ENTAILS in either direction. NOT_ENTAILS is deliberately not
derived from absence of a definition.

Unsupported proof classes remain unproved.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.semantic_relation_control_v1 import resolve
from canonical.runtime.semantic_relation_entailment_dag_v1 import RECEIPT_SCHEMA

SCHEMA="PROJECT_BRAIN_SEMANTIC_RELATION_EDGE_EVIDENCE_V1"
AUTHORITY_SCHEMA="PROJECT_BRAIN_SEMANTIC_RELATION_EDGE_AUTHORITY_V1"
PROOF_CLASS="EXPLICIT_SOURCE_IDENTITY"


def _canon(value:Any)->bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "pass":False,
        "schema":AUTHORITY_SCHEMA,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        **extra,
    }


def supports(raw:Any)->bool:
    return (
        isinstance(raw,Mapping)
        and raw.get("schema")==SCHEMA
        and raw.get("proof_class")==PROOF_CLASS
    )


def verify(raw:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(raw,Mapping):
        return _fail("EVIDENCE_NOT_OBJECT")
    allowed={
        "schema","proof_class","scope_id","source_id","target_id",
        "source_surface","target_surface","relation",
        "explicit_definition_sources",
    }
    if set(raw)!=allowed:
        return _fail(
            "EVIDENCE_FIELD_SET_INVALID",
            extra_fields=sorted(set(raw)-allowed),
            missing_fields=sorted(allowed-set(raw)),
        )
    if raw.get("schema")!=SCHEMA:
        return _fail("EVIDENCE_SCHEMA_INVALID")
    if raw.get("proof_class")!=PROOF_CLASS:
        return _fail("PROOF_CLASS_UNSUPPORTED")

    scope_id=str(raw.get("scope_id") or "").strip()
    source_id=str(raw.get("source_id") or "").strip()
    target_id=str(raw.get("target_id") or "").strip()
    source_surface=str(raw.get("source_surface") or "").strip()
    target_surface=str(raw.get("target_surface") or "").strip()
    relation=str(raw.get("relation") or "").strip().upper()

    if not scope_id:
        return _fail("SCOPE_ID_REQUIRED")
    if not source_id or not target_id or source_id==target_id:
        return _fail("DISTINCT_SOURCE_TARGET_IDS_REQUIRED")
    if not source_surface or not target_surface:
        return _fail("SOURCE_TARGET_SURFACES_REQUIRED")
    if relation not in {"ENTAILS","NOT_ENTAILS"}:
        return _fail("RELATION_UNSUPPORTED")

    rows=raw.get("explicit_definition_sources")
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows:
        return _fail("EXPLICIT_DEFINITION_SOURCES_REQUIRED")
    clean=[]
    for i,row in enumerate(rows):
        if not isinstance(row,Mapping):
            return _fail("DEFINITION_SOURCE_NOT_OBJECT",index=i)
        if set(row)!={"source_id","scope_id","source_text"}:
            return _fail("DEFINITION_SOURCE_FIELD_SET_INVALID",index=i)
        sid=str(row.get("source_id") or "").strip()
        scope=str(row.get("scope_id") or "").strip()
        text=row.get("source_text")
        if not sid or scope!=scope_id or not isinstance(text,str) or not text.strip():
            return _fail("DEFINITION_SOURCE_BINDING_INVALID",index=i)
        clean.append({
            "source_id":sid,
            "scope_id":scope,
            "source_text":text,
        })

    control=resolve({
        "left_id":source_id,
        "right_id":target_id,
        "left_surface":source_surface,
        "right_surface":target_surface,
        "scope_id":scope_id,
        "required_relation":"SEMANTIC_IDENTITY",
        "explicit_definition_sources":clean,
    })
    if control.get("pass") is not True:
        return _fail(
            "SEMANTIC_IDENTITY_NOT_PROVED",
            control_status=control.get("status"),
            control_reason=control.get("reason"),
        )

    if relation=="NOT_ENTAILS":
        return _fail(
            "NOT_ENTAILS_NOT_DERIVABLE_FROM_SEMANTIC_IDENTITY_PROOF"
        )

    evidence_sha=sha256(_canon(dict(raw))).hexdigest()
    receipt_body={
        "pass":True,
        "schema":RECEIPT_SCHEMA,
        "scope_id":scope_id,
        "source_id":source_id,
        "target_id":target_id,
        "relation":"ENTAILS",
        "source_semantics_authenticated":True,
        "target_semantics_authenticated":True,
        "relation_semantics_authenticated":True,
        "verification_authority_mutated":False,
        "evidence_sha256":evidence_sha,
    }
    receipt_sha=sha256(_canon(receipt_body)).hexdigest()
    return {
        **receipt_body,
        "receipt_sha256":receipt_sha,
        "authority_schema":AUTHORITY_SCHEMA,
        "proof_class":PROOF_CLASS,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
    }
