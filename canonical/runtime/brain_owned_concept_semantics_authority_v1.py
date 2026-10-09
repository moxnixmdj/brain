"""Brain-owned concept-semantics authority V1.

Authenticates one concept formula only when an exact canonical source declaration
binds the same scope, concept id, and formula. Produces the authority receipt
shape required by source_aligned_semantic_edge_authority_v1.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.certified_concept_semantics_source_v1 import parse
from canonical.runtime.source_aligned_semantic_edge_authority_v1 import (
    CONCEPT_SEMANTICS_RECEIPT_SCHEMA,
)

EVIDENCE_SCHEMA="PROJECT_BRAIN_CONCEPT_SEMANTICS_EVIDENCE_V1"
AUTHORITY_SCHEMA="PROJECT_BRAIN_CONCEPT_SEMANTICS_AUTHORITY_V1"


def _canon(value:Any)->bytes:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False,
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


def verify(raw:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(raw,Mapping):
        return _fail("EVIDENCE_NOT_OBJECT")
    allowed={
        "schema","scope_id","concept_id","formula","source",
    }
    if set(raw)!=allowed:
        return _fail("EVIDENCE_FIELD_SET_INVALID")
    if raw.get("schema")!=EVIDENCE_SCHEMA:
        return _fail("EVIDENCE_SCHEMA_INVALID")

    scope=str(raw.get("scope_id") or "").strip()
    concept=str(raw.get("concept_id") or "").strip()
    formula=raw.get("formula")
    source=raw.get("source")
    if not scope or not concept or not isinstance(formula,Mapping):
        return _fail("CONCEPT_BINDING_INVALID")
    if not isinstance(source,Mapping) or set(source)!={"source_id","scope_id","source_text"}:
        return _fail("SOURCE_EVIDENCE_INVALID")
    source_id=str(source.get("source_id") or "").strip()
    source_scope=str(source.get("scope_id") or "").strip()
    source_text=source.get("source_text")
    if (
        not source_id
        or source_scope!=scope
        or not isinstance(source_text,str)
        or not source_text
    ):
        return _fail("SOURCE_BINDING_INVALID")

    parsed=parse(source_text,source_id=source_id)
    if parsed.get("status")!="PARSED":
        return _fail(
            "CONCEPT_SEMANTICS_SOURCE_NOT_CERTIFIED",
            parse_status=parsed.get("status"),
            parse_reason=parsed.get("reason"),
        )
    matches=[
        row for row in parsed.get("concept_semantics") or []
        if (
            isinstance(row,Mapping)
            and row.get("scope_id")==scope
            and row.get("concept_id")==concept
        )
    ]
    if len(matches)!=1:
        return _fail(
            "EXACT_ONE_CONCEPT_SEMANTICS_DECLARATION_REQUIRED",
            match_count=len(matches),
        )
    row=matches[0]
    if dict(row.get("formula") or {})!=dict(formula):
        return _fail(
            "CONCEPT_FORMULA_MISMATCH",
            declared_formula=deepcopy(row.get("formula")),
            requested_formula=deepcopy(dict(formula)),
        )

    formula_sha=sha256(_canon(dict(formula))).hexdigest()
    receipt={
        "pass":True,
        "schema":CONCEPT_SEMANTICS_RECEIPT_SCHEMA,
        "scope_id":scope,
        "concept_id":concept,
        "formula_sha256":formula_sha,
        "definition_relation":"LOGICAL_EQUIVALENCE_IN_SCOPE",
        "concept_semantics_authenticated":True,
        "formula_semantics_authenticated":True,
        "verification_authority_mutated":False,
    }
    receipt["receipt_sha256"]=sha256(_canon(receipt)).hexdigest()
    return {
        **receipt,
        "authority_schema":AUTHORITY_SCHEMA,
        "source_id":source_id,
        "source_span_bytes":deepcopy(row.get("source_span_bytes")),
        "source_text_sha256":row.get("source_text_sha256"),
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        "boundary":"EXACT_SOURCE_DECLARED_CONCEPT_FORMULA_ONLY",
    }
