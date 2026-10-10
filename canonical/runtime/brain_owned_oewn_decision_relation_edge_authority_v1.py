"""Brain-owned OEWN decision semantic-relation edge authority V1.

Proof class: OEWN_DECISION_RELATION

This authority bridges release-relative lexical ambiguity into the existing
semantic-entailment DAG used by the document-effect field lattice.

It proves only positive ENTAILS edges:
    exact source mention -> deterministic effect-field concept

Requirements:
- source_id must be the deterministic mention ID for raw source/scope/span;
- target_id must equal the deterministic effect-field concept derived from
  effect_id, field, value, and scope;
- the raw span must exactly denote the OEWN universe lemma under casefold;
- OEWN candidate senses must be complete relative to the pinned release;
- source-certified decision evidence must make the lexical decision sufficient;
- every surviving sense must yield the exact terminal signature
  {"effect_field_concept_id": target_id}.

A unique intended sense is not required. Similarity never grants authority.
Open-world English completeness is explicitly not claimed.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.certified_document_effect_field_edge_v1 import (
    field_concept_id,
)
from canonical.runtime.oewn_decision_manifest_lattice_v1 import (
    evaluate as evaluate_oewn,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import RECEIPT_SCHEMA

SCHEMA="PROJECT_BRAIN_SEMANTIC_RELATION_EDGE_EVIDENCE_V1"
AUTHORITY_SCHEMA="PROJECT_BRAIN_OEWN_DECISION_RELATION_EDGE_AUTHORITY_V1"
PROOF_CLASS="OEWN_DECISION_RELATION"


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


def _mention_id(source_id:str,scope_id:str,raw_span:str)->str:
    return "MENTION:"+sha256(
        (source_id+"\n"+scope_id+"\n"+raw_span).encode("utf-8")
    ).hexdigest()


def verify(raw:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(raw,Mapping):
        return _fail("EVIDENCE_NOT_OBJECT")
    allowed={
        "schema","proof_class","scope_id","source_id","target_id","relation",
        "oewn_decision_source",
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
    if relation!="ENTAILS":
        return _fail("ONLY_POSITIVE_ENTAILS_SUPPORTED")

    source=raw.get("oewn_decision_source")
    allowed_source={
        "source_id","raw_span","sense_universe",
        "decision_source_id","decision_source_text",
        "effect_id","field","value",
    }
    if not isinstance(source,Mapping) or set(source)!=allowed_source:
        return _fail("OEWN_DECISION_SOURCE_INVALID")

    raw_source_id=str(source.get("source_id") or "").strip()
    raw_span=source.get("raw_span")
    decision_source_id=str(source.get("decision_source_id") or "").strip()
    decision_source_text=source.get("decision_source_text")
    effect_id=str(source.get("effect_id") or "").strip()
    field=str(source.get("field") or "").strip()
    value=source.get("value")
    sense_universe=source.get("sense_universe")

    if not raw_source_id:
        return _fail("RAW_SOURCE_ID_REQUIRED")
    if not isinstance(raw_span,str) or not raw_span or raw_span.strip()!=raw_span:
        return _fail("RAW_SPAN_REQUIRED_CANONICAL")
    if not decision_source_id:
        return _fail("DECISION_SOURCE_ID_REQUIRED")
    if not isinstance(decision_source_text,str) or not decision_source_text:
        return _fail("DECISION_SOURCE_TEXT_REQUIRED")
    if not effect_id or not field:
        return _fail("EFFECT_ID_AND_FIELD_REQUIRED")
    if not isinstance(sense_universe,Mapping):
        return _fail("SENSE_UNIVERSE_REQUIRED")

    expected_source=_mention_id(raw_source_id,scope,raw_span)
    if source_id!=expected_source:
        return _fail(
            "EDGE_SOURCE_ID_DOES_NOT_BIND_RAW_MENTION",
            expected_source_id=expected_source,
        )

    try:
        expected_target=field_concept_id(
            scope_id=scope,
            effect_id=effect_id,
            field=field,
            value=value,
        )
    except Exception as exc:
        return _fail(
            "FIELD_CONCEPT_DERIVATION_FAILED:"
            +type(exc).__name__+":"+str(exc)
        )
    if target_id!=expected_target:
        return _fail(
            "EDGE_TARGET_ID_DOES_NOT_BIND_EFFECT_FIELD",
            expected_target_id=expected_target,
        )

    lemma=str(sense_universe.get("lemma") or "").strip()
    if not lemma:
        return _fail("SENSE_UNIVERSE_LEMMA_REQUIRED")
    if raw_span.casefold()!=lemma.casefold():
        return _fail(
            "RAW_SPAN_DOES_NOT_MATCH_OEWN_LEMMA",
            raw_span=raw_span,
            lemma=lemma,
        )

    decision=evaluate_oewn({
        "schema":"PROJECT_BRAIN_OEWN_DECISION_MANIFEST_LATTICE_V1",
        "scope_id":scope,
        "sense_universe":deepcopy(dict(sense_universe)),
        "source_id":decision_source_id,
        "source_text":decision_source_text,
    })
    if decision.get("status")=="FAIL_CLOSED":
        return _fail(
            "OEWN_DECISION_FAIL_CLOSED",
            decision_reason=decision.get("reason"),
        )
    if decision.get("pass") is not True or decision.get("decision_sufficient") is not True:
        return _fail(
            "OEWN_DECISION_NOT_SUFFICIENT",
            decision_status=decision.get("status"),
            surviving_sense_ids=deepcopy(decision.get("surviving_sense_ids") or []),
            next_proof_obligations=deepcopy(decision.get("next_proof_obligations") or []),
            next_observation_id=decision.get("next_observation_id"),
        )

    expected_signature={"effect_field_concept_id":target_id}
    if decision.get("terminal_signature")!=expected_signature:
        return _fail(
            "OEWN_TERMINAL_SIGNATURE_DOES_NOT_BIND_FIELD_CONCEPT",
            expected_terminal_signature=expected_signature,
            observed_terminal_signature=deepcopy(decision.get("terminal_signature")),
        )

    if decision.get("candidate_sense_set_complete_relative_to_oewn_release") is not True:
        return _fail("OEWN_RELEASE_RELATIVE_SENSE_COMPLETENESS_UNPROVED")
    if decision.get("open_world_english_sense_completeness_claimed") is not False:
        return _fail("OPEN_WORLD_ENGLISH_COMPLETENESS_MUST_REMAIN_FALSE")

    evidence_sha=sha256(_canon(dict(raw))).hexdigest()
    body={
        "pass":True,
        "schema":RECEIPT_SCHEMA,
        "scope_id":scope,
        "source_id":source_id,
        "target_id":target_id,
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
        "raw_source_id":raw_source_id,
        "raw_span_sha256":sha256(raw_span.encode("utf-8")).hexdigest(),
        "oewn_release_id":decision.get("release_id"),
        "oewn_release_sha256":decision.get("release_sha256"),
        "lemma":decision.get("lemma"),
        "surviving_sense_ids":deepcopy(decision.get("surviving_sense_ids") or []),
        "intended_sense_identified":decision.get("intended_sense_identified") is True,
        "identified_sense_id":decision.get("identified_sense_id"),
        "decision_rule":decision.get("decision_rule"),
        "effect_id":effect_id,
        "field":field,
        "value":deepcopy(value),
        "field_concept_id":target_id,
        "decision_result":decision,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        "boundary":(
            "POSITIVE_SCOPED_OEWN_RELEASE_RELATIVE_DECISION_ENTAILMENT_ONLY__"
            "RAW_SPAN_MUST_BIND_RELEASE_LEMMA__ALL_SURVIVING_SENSES_MUST_IMPLY_"
            "THE_SAME_DETERMINISTIC_EFFECT_FIELD_CONCEPT__NO_OPEN_WORLD_ENGLISH_"
            "COMPLETENESS_OR_SIMILARITY_AUTHORITY"
        ),
    }
