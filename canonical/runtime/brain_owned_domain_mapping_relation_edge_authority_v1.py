"""Brain-owned domain-mapping semantic relation edge authority V1.

Proof class: DOMAIN_MAPPING_RELATION

Recomputes a scoped LEFT_ENTAILS_RIGHT domain-mapping truth certificate from
raw mention bytes and emits the standard semantic-edge ENTAILS/NOT_ENTAILS
receipt consumed by the cross-document field lattice.

Caller candidate concepts, semantic atoms, and relation problems are inputs to
the existing proof-carrying domain-mapping system only. They have no authority
unless that system independently proves or disproves the requested relation.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.domain_mapping_truth_certificate_v1 import (
    checked_predicate_id,
    evaluate as evaluate_domain_mapping,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import RECEIPT_SCHEMA

SCHEMA="PROJECT_BRAIN_SEMANTIC_RELATION_EDGE_EVIDENCE_V1"
AUTHORITY_SCHEMA="PROJECT_BRAIN_DOMAIN_MAPPING_RELATION_EDGE_AUTHORITY_V1"
PROOF_CLASS="DOMAIN_MAPPING_RELATION"


def _canon(value:Any)->bytes:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False,
    ).encode("utf-8")


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "pass":False,"schema":AUTHORITY_SCHEMA,"status":"FAIL_CLOSED",
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


def _mention_id(raw_source_id:str,scope_id:str,raw_span:str)->str:
    return "MENTION:"+sha256(
        (raw_source_id+"\n"+scope_id+"\n"+raw_span).encode("utf-8")
    ).hexdigest()


def verify(raw:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(raw,Mapping):
        return _fail("EVIDENCE_NOT_OBJECT")
    allowed={
        "schema","proof_class","scope_id","source_id","target_id","relation",
        "domain_mapping_source",
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

    source=raw.get("domain_mapping_source")
    allowed_source={
        "source_id","raw_span","candidate_concepts","evidence",
        "candidate_semantic_atoms","relation_problems",
    }
    if not isinstance(source,Mapping) or set(source)!=allowed_source:
        return _fail("DOMAIN_MAPPING_SOURCE_INVALID")

    raw_source_id=str(source.get("source_id") or "").strip()
    raw_span=source.get("raw_span")
    candidates=source.get("candidate_concepts")
    evidence=source.get("evidence")
    atoms=source.get("candidate_semantic_atoms")
    relation_problems=source.get("relation_problems")
    if not raw_source_id:
        return _fail("RAW_SOURCE_ID_REQUIRED")
    if not isinstance(raw_span,str) or not raw_span.strip():
        return _fail("RAW_SPAN_REQUIRED")
    if not isinstance(candidates,Sequence) or isinstance(candidates,(str,bytes)):
        return _fail("CANDIDATE_CONCEPTS_REQUIRED")
    if not isinstance(evidence,Sequence) or isinstance(evidence,(str,bytes)):
        return _fail("EVIDENCE_ROWS_INVALID")
    if not isinstance(atoms,Sequence) or isinstance(atoms,(str,bytes)):
        return _fail("CANDIDATE_SEMANTIC_ATOMS_INVALID")
    if not isinstance(relation_problems,Mapping):
        return _fail("RELATION_PROBLEMS_INVALID")

    expected_source=_mention_id(raw_source_id,scope,raw_span)
    if source_id!=expected_source:
        return _fail(
            "EDGE_SOURCE_ID_DOES_NOT_BIND_RAW_MENTION",
            expected_source_id=expected_source,
        )
    if target_id not in {
        str(row.get("concept_id") or "").strip()
        for row in candidates
        if isinstance(row,Mapping)
    }:
        return _fail("TARGET_CONCEPT_NOT_IN_CANDIDATE_SET")

    required="LEFT_ENTAILS_RIGHT"
    predicate_id=checked_predicate_id(
        source_id=raw_source_id,
        raw_span=raw_span,
        scope_id=scope,
        target_concept_id=target_id,
        required_relation=required,
    )
    certificate=evaluate_domain_mapping({
        "truth_kind":"DOMAIN_MAPPING_RELATION",
        "predicate_id":predicate_id,
        "raw_span":raw_span,
        "source_id":raw_source_id,
        "scope_id":scope,
        "target_concept_id":target_id,
        "required_relation":required,
        "candidate_concepts":deepcopy(list(candidates)),
        "evidence":deepcopy(list(evidence)),
        "candidate_semantic_atoms":deepcopy(list(atoms)),
        "relation_problems":deepcopy(dict(relation_problems)),
    })

    if certificate.get("status")=="FAIL_CLOSED":
        return _fail(
            "DOMAIN_MAPPING_CERTIFICATE_FAIL_CLOSED",
            certificate_reason=certificate.get("reason"),
        )
    truth=str(certificate.get("predicate_truth") or "").upper()
    expected_truth="TRUE" if relation=="ENTAILS" else "FALSE"
    if (
        certificate.get("pass") is not True
        or certificate.get("semantic_truth_authority") is not True
        or truth!=expected_truth
        or certificate.get("predicate_id")!=predicate_id
        or certificate.get("source_id")!=raw_source_id
        or certificate.get("scope_id")!=scope
        or certificate.get("target_concept_id")!=target_id
        or certificate.get("required_relation")!=required
    ):
        return _fail(
            "DOMAIN_MAPPING_RELATION_NOT_PROVED",
            predicate_truth=truth or "UNKNOWN",
            expected_truth=expected_truth,
            certificate_status=certificate.get("status"),
        )

    evidence_sha=sha256(_canon(dict(raw))).hexdigest()
    body={
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
    receipt_sha=sha256(_canon(body)).hexdigest()
    return {
        **body,
        "receipt_sha256":receipt_sha,
        "authority_schema":AUTHORITY_SCHEMA,
        "proof_class":PROOF_CLASS,
        "domain_mapping_predicate_id":predicate_id,
        "domain_mapping_certificate":certificate,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        "boundary":"SCOPED_DOMAIN_MAPPING_LEFT_ENTAILS_RIGHT_TRUTH_ONLY__NO_OPEN_WORLD_ONTOLOGY_COMPLETENESS",
    }
