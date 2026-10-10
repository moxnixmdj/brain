"""Brain-owned scoped domain-mapping relation edge authority V1.

Proof class: DOMAIN_MAPPING_SCOPED_RELATION

This authority preserves the existing domain-mapping truth kernel but stops
throwing away already-proved relation direction. It may emit a standard ENTAILS
edge in either direction only when domain_mapping_truth_certificate_v1
independently proves a relation strong enough for that exact direction.

No similarity/model score is authoritative. CURRENT_DECISION_SUBSTITUTION is
deliberately not promoted to logical entailment.
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
AUTHORITY_SCHEMA="PROJECT_BRAIN_SCOPED_DOMAIN_MAPPING_RELATION_EDGE_AUTHORITY_V1"
PROOF_CLASS="DOMAIN_MAPPING_SCOPED_RELATION"

MENTION_TO_CONCEPT="MENTION_TO_CONCEPT"
CONCEPT_TO_MENTION="CONCEPT_TO_MENTION"
_FORWARD_RELATIONS={
    "SEMANTIC_IDENTITY",
    "LOGICAL_EQUIVALENCE_IN_SCOPE",
    "LEFT_ENTAILS_RIGHT",
}
_REVERSE_RELATIONS={
    "SEMANTIC_IDENTITY",
    "LOGICAL_EQUIVALENCE_IN_SCOPE",
    "RIGHT_ENTAILS_LEFT",
}


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
    edge_source=str(raw.get("source_id") or "").strip()
    edge_target=str(raw.get("target_id") or "").strip()
    edge_relation=str(raw.get("relation") or "").strip().upper()
    if not scope:
        return _fail("SCOPE_ID_REQUIRED")
    if not edge_source or not edge_target or edge_source==edge_target:
        return _fail("DISTINCT_SOURCE_TARGET_IDS_REQUIRED")
    if edge_relation!="ENTAILS":
        return _fail("ONLY_STANDARD_ENTAILS_EDGE_SUPPORTED")

    src=raw.get("domain_mapping_source")
    source_allowed={
        "source_id","raw_span","target_concept_id","required_relation",
        "edge_direction","candidate_concepts","evidence",
        "candidate_semantic_atoms","relation_problems",
    }
    if not isinstance(src,Mapping) or set(src)!=source_allowed:
        return _fail("DOMAIN_MAPPING_SOURCE_INVALID")

    raw_source_id=str(src.get("source_id") or "").strip()
    raw_span=src.get("raw_span")
    concept_id=str(src.get("target_concept_id") or "").strip()
    required=str(src.get("required_relation") or "").strip().upper()
    direction=str(src.get("edge_direction") or "").strip().upper()
    candidates=src.get("candidate_concepts")
    evidence=src.get("evidence")
    atoms=src.get("candidate_semantic_atoms")
    relation_problems=src.get("relation_problems")

    if not raw_source_id:
        return _fail("RAW_SOURCE_ID_REQUIRED")
    if not isinstance(raw_span,str) or not raw_span.strip():
        return _fail("RAW_SPAN_REQUIRED")
    if not concept_id:
        return _fail("TARGET_CONCEPT_ID_REQUIRED")
    if direction not in {MENTION_TO_CONCEPT,CONCEPT_TO_MENTION}:
        return _fail("EDGE_DIRECTION_INVALID")
    allowed_relations=(
        _FORWARD_RELATIONS if direction==MENTION_TO_CONCEPT
        else _REVERSE_RELATIONS
    )
    if required not in allowed_relations:
        return _fail(
            "REQUIRED_RELATION_DOES_NOT_AUTHORIZE_EDGE_DIRECTION",
            required_relation=required,
            edge_direction=direction,
        )
    if not isinstance(candidates,Sequence) or isinstance(candidates,(str,bytes)):
        return _fail("CANDIDATE_CONCEPTS_REQUIRED")
    if not isinstance(evidence,Sequence) or isinstance(evidence,(str,bytes)):
        return _fail("EVIDENCE_ROWS_INVALID")
    if not isinstance(atoms,Sequence) or isinstance(atoms,(str,bytes)):
        return _fail("CANDIDATE_SEMANTIC_ATOMS_INVALID")
    if not isinstance(relation_problems,Mapping):
        return _fail("RELATION_PROBLEMS_INVALID")

    candidate_ids={
        str(row.get("concept_id") or "").strip()
        for row in candidates
        if isinstance(row,Mapping)
    }
    if concept_id not in candidate_ids:
        return _fail("TARGET_CONCEPT_NOT_IN_CANDIDATE_SET")

    mention=_mention_id(raw_source_id,scope,raw_span)
    expected_source,expected_target=(
        (mention,concept_id)
        if direction==MENTION_TO_CONCEPT
        else (concept_id,mention)
    )
    if edge_source!=expected_source or edge_target!=expected_target:
        return _fail(
            "EDGE_ENDPOINT_BINDING_INVALID",
            expected_source_id=expected_source,
            expected_target_id=expected_target,
        )

    predicate_id=checked_predicate_id(
        source_id=raw_source_id,
        raw_span=raw_span,
        scope_id=scope,
        target_concept_id=concept_id,
        required_relation=required,
    )
    certificate=evaluate_domain_mapping({
        "truth_kind":"DOMAIN_MAPPING_RELATION",
        "predicate_id":predicate_id,
        "raw_span":raw_span,
        "source_id":raw_source_id,
        "scope_id":scope,
        "target_concept_id":concept_id,
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
    if (
        certificate.get("pass") is not True
        or certificate.get("semantic_truth_authority") is not True
        or truth!="TRUE"
        or certificate.get("predicate_id")!=predicate_id
        or certificate.get("source_id")!=raw_source_id
        or certificate.get("scope_id")!=scope
        or certificate.get("target_concept_id")!=concept_id
        or certificate.get("required_relation")!=required
    ):
        return _fail(
            "SCOPED_DOMAIN_MAPPING_RELATION_NOT_PROVED",
            predicate_truth=truth or "UNKNOWN",
            required_relation=required,
            certificate_status=certificate.get("status"),
        )

    evidence_sha=sha256(_canon(dict(raw))).hexdigest()
    body={
        "pass":True,
        "schema":RECEIPT_SCHEMA,
        "scope_id":scope,
        "source_id":edge_source,
        "target_id":edge_target,
        "relation":"ENTAILS",
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
        "edge_direction":direction,
        "proved_required_relation":required,
        "domain_mapping_predicate_id":predicate_id,
        "domain_mapping_certificate":certificate,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        "boundary":(
            "STANDARD_ENTAILS_EDGE_ONLY_WHEN_BRAIN_OWNED_DOMAIN_MAPPING_CERTIFICATE_"
            "PROVES_THE_EXACT_DIRECTION__SEMANTIC_IDENTITY_OR_SCOPED_LOGICAL_"
            "EQUIVALENCE_MAY_AUTHORIZE_BOTH_DIRECTIONS_VIA_SEPARATELY_RECOMPUTED_"
            "RECEIPTS__CURRENT_DECISION_SUBSTITUTION_AND_SIMILARITY_NEVER_MINT_"
            "ENTAILMENT"
        ),
    }
