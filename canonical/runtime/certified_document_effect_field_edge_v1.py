"""Certified document-effect field from semantic entailment DAG V1.

This adapter bridges independently authenticated semantic entailment into one
exact effect-field coordinate.

It does NOT trust caller-supplied DAG receipts. The caller must provide a
relation_verifier callback; semantic_relation_entailment_dag_v1 recomputes every
edge through that verifier.

The target field concept is mechanically derived from:
    effect_id, field, normalized value, scope_id

Therefore a DAG can refine the field only when its right-hand terminal node is
exactly that canonical concept ID and the authenticated DAG proves
left => right in the same scope.

No relation_verifier => no field proof.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Callable, Mapping

from canonical.runtime.certified_document_effect_field_v1 import (
    FIELDS,
    _normalize_field,
)
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    evidence_sha256,
    prove as prove_dag,
)

SCHEMA="BRAIN_CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE_V1"
RECEIPT_SCHEMA="BRAIN_CERTIFIED_DOCUMENT_EFFECT_FIELD_EDGE_RECEIPT_V1"


def _canon(value:Any)->bytes:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False,
    ).encode("utf-8")


def _token(value:Any,name:str)->str:
    if not isinstance(value,str) or not value.strip():
        raise ValueError(name+"_INVALID")
    cleaned=value.strip()
    if cleaned!=value:
        raise ValueError(name+"_NOT_CANONICAL")
    return cleaned


def field_concept_id(
    *,
    scope_id:str,
    effect_id:str,
    field:str,
    value:Any,
)->str:
    scope=_token(scope_id,"SCOPE_ID")
    eid=_token(effect_id,"EFFECT_ID")
    fld=_token(field,"FIELD")
    if fld not in FIELDS:
        raise ValueError("FIELD_UNSUPPORTED:"+fld)
    normalized=_normalize_field(fld,value)
    payload={
        "scope_id":scope,
        "effect_id":eid,
        "field":fld,
        "value":normalized,
    }
    return "EFFECT_FIELD_CONCEPT::"+sha256(_canon(payload)).hexdigest()


def prove_field(
    *,
    scope_id:str,
    effect_id:str,
    field:str,
    value:Any,
    dag_evidence:Mapping[str,Any],
    expected_dag_sha256:str,
    relation_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None,
)->dict[str,Any]:
    try:
        scope=_token(scope_id,"SCOPE_ID")
        eid=_token(effect_id,"EFFECT_ID")
        fld=_token(field,"FIELD")
        if fld not in FIELDS:
            raise ValueError("FIELD_UNSUPPORTED:"+fld)
        normalized=_normalize_field(fld,value)
        concept_id=field_concept_id(
            scope_id=scope,
            effect_id=eid,
            field=fld,
            value=normalized,
        )
        if not isinstance(dag_evidence,Mapping):
            raise ValueError("DAG_EVIDENCE_NOT_OBJECT")
        if not callable(relation_verifier):
            return {
                "schema":SCHEMA,
                "status":"OPEN__RELATION_VERIFIER_REQUIRED",
                "pass":False,
                "reason":"RELATION_VERIFIER_REQUIRED",
                "effect_id":eid,
                "field":fld,
                "value":normalized,
                "field_concept_id":concept_id,
                "semantic_truth_authority":False,
                "execution_authority":False,
                "acceptance_authority":False,
                "terminal_authority":False,
            }

        dag=prove_dag(
            dag_evidence,
            expected_evidence_sha256=expected_dag_sha256,
            relation_verifier=relation_verifier,
        )
        if dag.get("status")=="FAIL_CLOSED":
            return {
                "schema":SCHEMA,
                "status":"FAIL_CLOSED",
                "pass":False,
                "reason":"ENTAILMENT_DAG_FAIL_CLOSED:"+str(dag.get("reason")),
                "dag_result":dag,
                "semantic_truth_authority":False,
                "execution_authority":False,
                "acceptance_authority":False,
                "terminal_authority":False,
            }

        bad=[]
        if dag.get("scope_id")!=scope:
            bad.append("SCOPE_ID")
        if dag.get("right_id")!=concept_id:
            bad.append("RIGHT_FIELD_CONCEPT_ID")
        if dag.get("left_entails_right") is not True:
            bad.append("LEFT_ENTAILS_RIGHT")
        if dag.get("left_entails_right_disproved") is True:
            bad.append("LEFT_ENTAILS_RIGHT_DISPROVED")
        if bad:
            return {
                "schema":SCHEMA,
                "status":"OPEN__FIELD_ENTAILMENT_NOT_PROVED",
                "pass":False,
                "reason":"FIELD_BINDING_REQUIREMENTS_NOT_MET:"+",".join(sorted(bad)),
                "effect_id":eid,
                "field":fld,
                "value":normalized,
                "field_concept_id":concept_id,
                "dag_result":dag,
                "semantic_truth_authority":False,
                "execution_authority":False,
                "acceptance_authority":False,
                "terminal_authority":False,
            }

        receipt={
            "schema":RECEIPT_SCHEMA,
            "pass":True,
            "scope_id":scope,
            "effect_id":eid,
            "field":fld,
            "value":normalized,
            "field_concept_id":concept_id,
            "source_semantic_node_id":dag.get("left_id"),
            "dag_evidence_sha256":evidence_sha256(dag_evidence),
            "left_to_right_path":dag.get("left_to_right_path"),
            "relation_semantics_recomputed":True,
            "field_binding_mechanically_derived":True,
            "verification_authority_mutated":False,
            "semantic_truth_authority":False,
            "execution_authority":False,
            "acceptance_authority":False,
            "terminal_authority":False,
        }
        receipt["receipt_sha256"]=sha256(_canon(receipt)).hexdigest()
        return {
            "schema":SCHEMA,
            "status":"PASS__DOCUMENT_EFFECT_FIELD_ENTAILED",
            "pass":True,
            "field_receipt":receipt,
            "dag_result":dag,
            "semantic_truth_authority":False,
            "execution_authority":False,
            "acceptance_authority":False,
            "terminal_authority":False,
            "boundary":(
                "FIELD_PROOF_RELATIVE_TO_INDEPENDENTLY_RECOMPUTED_SCOPED_"
                "ENTAILMENT_DAG__NO_RELATION_VERIFIER_MEANS_NO_FIELD_PROOF__"
                "NO_RAW_LANGUAGE_EXTRACTION_AUTHORITY"
            ),
        }
    except Exception as exc:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "pass":False,
            "reason":type(exc).__name__+":"+str(exc),
            "semantic_truth_authority":False,
            "execution_authority":False,
            "acceptance_authority":False,
            "terminal_authority":False,
        }
