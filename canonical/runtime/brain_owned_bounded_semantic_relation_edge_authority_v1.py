"""Brain-owned bounded-extension semantic relation edge authority V1.

This authority authenticates a second internal semantic-edge proof class:
EXPLICIT_BOUNDED_EXTENSION.

The completeness assumptions required by bounded_semantic_relation_proof_v1 are
not trusted from caller booleans. They are reconstructed from exact canonical
source declarations parsed by certified_bounded_semantic_extension_source_v1.

Supported standard edge receipts:
  ENTAILS      iff source extension is a subset of target extension.
  NOT_ENTAILS  iff an exact source\target witness exists.

No open-world claim is made outside the declared complete bounded universe.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.certified_bounded_semantic_extension_source_v1 import parse
from canonical.runtime.bounded_semantic_relation_proof_v1 import (
    EVIDENCE_SCHEMA as BOUNDED_EVIDENCE_SCHEMA,
    evidence_sha256 as bounded_evidence_sha256,
    prove as prove_bounded,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import RECEIPT_SCHEMA

SCHEMA="PROJECT_BRAIN_SEMANTIC_RELATION_EDGE_EVIDENCE_V1"
AUTHORITY_SCHEMA="PROJECT_BRAIN_BOUNDED_SEMANTIC_RELATION_EDGE_AUTHORITY_V1"
PROOF_CLASS="EXPLICIT_BOUNDED_EXTENSION"


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
        "relation","bounded_extension_source",
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

    scope=str(raw.get("scope_id") or "").strip()
    source_id=str(raw.get("source_id") or "").strip()
    target_id=str(raw.get("target_id") or "").strip()
    relation=str(raw.get("relation") or "").strip().upper()
    if not scope:
        return _fail("SCOPE_ID_REQUIRED")
    if not source_id or not target_id or source_id==target_id:
        return _fail("DISTINCT_SOURCE_TARGET_IDS_REQUIRED")
    if relation not in {"ENTAILS","NOT_ENTAILS"}:
        return _fail("RELATION_UNSUPPORTED")

    source=raw.get("bounded_extension_source")
    if not isinstance(source,Mapping) or set(source)!={"source_id","scope_id","source_text"}:
        return _fail("BOUNDED_EXTENSION_SOURCE_INVALID")
    declaration_source_id=str(source.get("source_id") or "").strip()
    declaration_scope=str(source.get("scope_id") or "").strip()
    declaration_text=source.get("source_text")
    if (
        not declaration_source_id
        or declaration_scope!=scope
        or not isinstance(declaration_text,str)
        or not declaration_text
    ):
        return _fail("BOUNDED_EXTENSION_SOURCE_BINDING_INVALID")

    parsed=parse(declaration_text,source_id=declaration_source_id)
    if parsed.get("status")!="PARSED":
        return _fail(
            "BOUNDED_EXTENSION_SOURCE_NOT_CERTIFIED",
            parse_status=parsed.get("status"),
            parse_reason=parsed.get("reason"),
        )

    universes=[
        row for row in parsed.get("universes") or []
        if isinstance(row,Mapping) and row.get("scope_id")==scope
    ]
    if len(universes)!=1:
        return _fail(
            "EXACT_ONE_SCOPE_UNIVERSE_REQUIRED",
            universe_count=len(universes),
        )

    extension_by_id={}
    for row in parsed.get("extensions") or []:
        if not isinstance(row,Mapping) or row.get("scope_id")!=scope:
            continue
        cid=str(row.get("concept_id") or "")
        if cid in extension_by_id:
            return _fail("DUPLICATE_SCOPE_EXTENSION:"+cid)
        extension_by_id[cid]=row

    if source_id not in extension_by_id:
        return _fail("SOURCE_EXTENSION_NOT_DECLARED")
    if target_id not in extension_by_id:
        return _fail("TARGET_EXTENSION_NOT_DECLARED")

    universe=list(universes[0].get("members") or [])
    left=list(extension_by_id[source_id].get("members") or [])
    right=list(extension_by_id[target_id].get("members") or [])

    evidence={
        "schema":BOUNDED_EVIDENCE_SCHEMA,
        "scope_id":scope,
        "left_id":source_id,
        "right_id":target_id,
        "universe_complete":True,
        "left_extension_complete":True,
        "right_extension_complete":True,
        "universe":universe,
        "left_members":left,
        "right_members":right,
    }
    proof=prove_bounded(
        evidence,
        expected_evidence_sha256=bounded_evidence_sha256(evidence),
    )
    if proof.get("pass") is not True:
        return _fail(
            "BOUNDED_RELATION_PROOF_FAIL_CLOSED",
            bounded_status=proof.get("status"),
            bounded_reason=proof.get("reason"),
        )

    if relation=="ENTAILS":
        proved=proof.get("left_entails_right") is True
        if not proved:
            return _fail(
                "ENTAILMENT_DISPROVED_OR_UNPROVED",
                left_not_right_witnesses=deepcopy(
                    proof.get("left_not_right_witnesses") or []
                ),
            )
    else:
        proved=proof.get("left_entails_right_disproved") is True
        if not proved:
            return _fail("NOT_ENTAILS_UNPROVED")

    evidence_sha=sha256(_canon(dict(raw))).hexdigest()
    receipt_body={
        "pass":True,
        "schema":RECEIPT_SCHEMA,
        "scope_id":scope,
        "source_id":source_id,
        "target_id":target_id,
        "relation":relation,
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
        "bounded_relation_proof":proof,
        "source_declaration_receipt":{
            "source_id":declaration_source_id,
            "scope_id":scope,
            "universe_source_span_bytes":deepcopy(
                universes[0].get("source_span_bytes")
            ),
            "source_extension_span_bytes":deepcopy(
                extension_by_id[source_id].get("source_span_bytes")
            ),
            "target_extension_span_bytes":deepcopy(
                extension_by_id[target_id].get("source_span_bytes")
            ),
        },
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        "boundary":"EXACT_ONLY_IN_SOURCE_DECLARED_COMPLETE_BOUNDED_UNIVERSE_AND_EXTENSIONS",
    }
