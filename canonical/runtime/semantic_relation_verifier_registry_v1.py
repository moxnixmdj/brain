"""Brain-owned semantic relation verifier registry V1.

Purpose:
  turn portable evidence envelopes into canonical semantic-relation edge receipts
  without caller-supplied executable verifier callbacks.

V1 registers one self-contained verifier family:
  SEMANTIC_RELATION_CONTROL_EDGE_V1

That verifier recomputes semantic_relation_control_v1 from content-addressed,
portable evidence. It intentionally forbids relation-control branches that
themselves require external verifier callbacks:
  - shared_concept_identity_receipt
  - terminal_signature_authority_receipt
  - entailment_dag_evidence

Supported authority in V1 therefore comes from Brain-owned source-explicit
definition logic and/or the content-addressed bounded semantic relation proof.

A caller-provided verifier_id is not authority. Envelope schema determines the
candidate verifier. Unsupported or multiply matching evidence fails closed.

The returned receipt is exactly the schema expected by
semantic_relation_entailment_dag_v1. The registry grants no execution,
acceptance, policy-adequacy, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.semantic_relation_control_v1 import resolve
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    RECEIPT_SCHEMA,
)

SCHEMA="PROJECT_BRAIN_SEMANTIC_RELATION_VERIFIER_REGISTRY_V1"
CONTROL_EDGE_EVIDENCE_SCHEMA=(
    "PROJECT_BRAIN_SEMANTIC_RELATION_CONTROL_EDGE_EVIDENCE_V1"
)
SUPPORTED_RELATIONS={"ENTAILS","NOT_ENTAILS"}

_FORBIDDEN_CONTROL_FIELDS={
    "shared_concept_identity_receipt",
    "terminal_signature_rows",
    "terminal_signature_authority_receipt",
    "entailment_dag_evidence",
    "expected_entailment_dag_sha256",
}


def _canon(value:Any)->bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value:Any)->str:
    return sha256(_canon(value)).hexdigest()


def _token(value:Any,name:str)->str:
    if not isinstance(value,str) or not value.strip():
        raise ValueError(name+"_INVALID")
    cleaned=value.strip()
    if cleaned!=value:
        raise ValueError(name+"_NOT_CANONICAL")
    return cleaned


def evidence_sha256(problem:Mapping[str,Any])->str:
    if not isinstance(problem,Mapping):
        raise ValueError("PROBLEM_NOT_OBJECT")
    return _sha(dict(problem))


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":"FAIL_CLOSED",
        "pass":False,
        "reason":reason,
        "semantic_relation_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        **extra,
    }


def _control_candidate(raw:Mapping[str,Any])->dict[str,Any]:
    if set(raw)!={
        "schema",
        "relation",
        "problem",
        "expected_problem_sha256",
    }:
        return _fail("CONTROL_EDGE_ENVELOPE_FIELD_SET_NOT_EXACT")

    relation=_token(raw.get("relation"),"RELATION").upper()
    if relation not in SUPPORTED_RELATIONS:
        return _fail("RELATION_UNSUPPORTED:"+relation)

    problem=raw.get("problem")
    if not isinstance(problem,Mapping):
        return _fail("CONTROL_PROBLEM_NOT_OBJECT")
    problem=deepcopy(dict(problem))

    expected=str(raw.get("expected_problem_sha256") or "")
    actual=_sha(problem)
    if expected!=actual:
        return _fail(
            "CONTROL_PROBLEM_CONTENT_ADDRESS_MISMATCH",
            expected_problem_sha256=expected,
            actual_problem_sha256=actual,
        )

    forbidden=sorted(_FORBIDDEN_CONTROL_FIELDS & set(problem))
    if forbidden:
        return _fail(
            "CONTROL_PROBLEM_REQUIRES_EXTERNAL_VERIFIER:"
            +",".join(forbidden)
        )

    left=_token(problem.get("left_id"),"LEFT_ID")
    right=_token(problem.get("right_id"),"RIGHT_ID")
    scope=_token(problem.get("scope_id"),"SCOPE_ID")
    if left==right:
        return _fail("DISTINCT_LEFT_RIGHT_IDS_REQUIRED")

    if problem.get("required_relation")!="LEFT_ENTAILS_RIGHT":
        return _fail(
            "CONTROL_REQUIRED_RELATION_MUST_BE_LEFT_ENTAILS_RIGHT"
        )

    result=resolve(problem)
    if not isinstance(result,Mapping):
        return _fail("SEMANTIC_RELATION_CONTROL_RETURNED_NO_RESULT")

    if str(result.get("status") or "").startswith("FAIL_CLOSED"):
        return _fail(
            "SEMANTIC_RELATION_CONTROL_FAIL_CLOSED:"
            +str(result.get("reason") or result.get("status")),
            control_result=deepcopy(dict(result)),
        )

    if (
        result.get("scope_id")!=scope
        or result.get("left_id")!=left
        or result.get("right_id")!=right
    ):
        return _fail(
            "SEMANTIC_RELATION_CONTROL_BINDING_MISMATCH",
            control_result=deepcopy(dict(result)),
        )

    if relation=="ENTAILS":
        proved=(
            result.get("pass") is True
            and isinstance(result.get("proved_facts"),Mapping)
            and result["proved_facts"].get("left_entails_right") is True
        )
        if not proved:
            return {
                "schema":SCHEMA,
                "status":"UNKNOWN__REGISTERED_RELATION_NOT_PROVED",
                "pass":False,
                "reason":"LEFT_ENTAILS_RIGHT_NOT_PROVED",
                "control_result":deepcopy(dict(result)),
                "semantic_relation_authority":False,
                "execution_authority":False,
                "acceptance_authority":False,
                "terminal_authority":False,
            }
    else:
        disproved=(
            result.get("required_relation_disproved") is True
            and result.get("pass") is not True
        )
        if not disproved:
            return {
                "schema":SCHEMA,
                "status":"UNKNOWN__REGISTERED_COUNTEREXAMPLE_NOT_PROVED",
                "pass":False,
                "reason":"LEFT_ENTAILS_RIGHT_NOT_DISPROVED",
                "control_result":deepcopy(dict(result)),
                "semantic_relation_authority":False,
                "execution_authority":False,
                "acceptance_authority":False,
                "terminal_authority":False,
            }

    evidence_bundle={
        "registry_schema":SCHEMA,
        "registered_verifier":"SEMANTIC_RELATION_CONTROL_EDGE_V1",
        "relation":relation,
        "scope_id":scope,
        "source_id":left,
        "target_id":right,
        "problem_sha256":actual,
        "control_status":result.get("status"),
        "strongest_proved_relation":result.get(
            "strongest_proved_relation"
        ),
        "required_relation_disproved":result.get(
            "required_relation_disproved"
        ),
        "bounded_extension_proof":deepcopy(
            result.get("bounded_extension_proof")
        ),
        "explicit_equivalence":deepcopy(
            result.get("explicit_equivalence")
        ),
    }
    receipt={
        "pass":True,
        "schema":RECEIPT_SCHEMA,
        "scope_id":scope,
        "source_id":left,
        "target_id":right,
        "relation":relation,
        "source_semantics_authenticated":True,
        "target_semantics_authenticated":True,
        "relation_semantics_authenticated":True,
        "verification_authority_mutated":False,
        "evidence_sha256":_sha(evidence_bundle),
    }
    receipt["receipt_sha256"]=_sha(receipt)
    receipt["registry_verifier_id"]="SEMANTIC_RELATION_CONTROL_EDGE_V1"
    receipt["registry_problem_sha256"]=actual
    return {
        "schema":SCHEMA,
        "status":"PASS__REGISTERED_SEMANTIC_RELATION_RECOMPUTED",
        "pass":True,
        "receipt":receipt,
        "control_result":deepcopy(dict(result)),
        "semantic_relation_authority":True,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
    }


def verify(raw:Mapping[str,Any])->Mapping[str,Any]|None:
    """Relation-verifier callback compatible with entailment DAG V1.

    Returns the canonical edge receipt on success.
    Unsupported evidence returns None. Matching evidence that is malformed,
    unresolved, or disproved returns None; callers that need diagnostics should
    use evaluate().
    """
    out=evaluate(raw)
    if out.get("pass") is True and isinstance(out.get("receipt"),Mapping):
        return deepcopy(dict(out["receipt"]))
    return None


def evaluate(raw:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(raw,Mapping):
        return _fail("EDGE_EVIDENCE_NOT_OBJECT")
    schema=raw.get("schema")
    if schema==CONTROL_EDGE_EVIDENCE_SCHEMA:
        return _control_candidate(raw)
    return {
        "schema":SCHEMA,
        "status":"UNRESOLVED__NO_REGISTERED_RELATION_VERIFIER_MATCHED",
        "pass":False,
        "evidence_schema":schema,
        "semantic_relation_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
    }
