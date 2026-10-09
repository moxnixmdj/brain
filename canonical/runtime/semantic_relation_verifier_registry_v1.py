"""Brain-owned semantic relation verifier registry V1.

V1 exposes a callback compatible with semantic_relation_entailment_dag_v1
without accepting caller-supplied executable verifiers.

Registered verifier:
  EXPLICIT_SOURCE_EFFECT_FIELD_DEFINITION_V1

It proves one ENTAILS edge only when all of the following recompute:
- the left node is the deterministic mention ID of exact source_id/scope/raw_span;
- the right node is the deterministic effect-field concept ID for
  scope/effect_id/field/normalized value;
- the target surface is the canonical JSON rendering of that normalized value;
- the exact raw source span contains an explicit named definition that
  semantic_relation_control_v1 recomputes as identity between the supplied
  left surface and that canonical target surface.

No caller boolean, verifier ID, bounded universe, similarity score, or receipt
can add authority. Unsupported evidence returns no verifier match.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.certified_document_effect_field_edge_v1 import (
    field_concept_id,
)
from canonical.runtime.certified_document_effect_field_v1 import (
    FIELDS,
    _normalize_field,
)
from canonical.runtime.semantic_relation_control_v1 import resolve
from canonical.runtime.semantic_relation_entailment_dag_v1 import (
    RECEIPT_SCHEMA,
)

SCHEMA="PROJECT_BRAIN_SEMANTIC_RELATION_VERIFIER_REGISTRY_V1"
EXPLICIT_FIELD_EDGE_SCHEMA=(
    "PROJECT_BRAIN_EXPLICIT_SOURCE_EFFECT_FIELD_DEFINITION_EDGE_V1"
)


def _canon(value:Any)->str:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),
        ensure_ascii=False,allow_nan=False,
    )


def _sha(value:Any)->str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _token(value:Any,name:str)->str:
    if not isinstance(value,str) or not value.strip():
        raise ValueError(name+"_INVALID")
    cleaned=value.strip()
    if cleaned!=value:
        raise ValueError(name+"_NOT_CANONICAL")
    return cleaned


def _mention_id(source_id:str,scope_id:str,raw_span:str)->str:
    return "MENTION:"+sha256(
        (source_id+"\n"+scope_id+"\n"+raw_span).encode("utf-8")
    ).hexdigest()


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


def _explicit_field_candidate(raw:Mapping[str,Any])->dict[str,Any]:
    allowed={
        "schema","source_id","raw_span","scope_id",
        "effect_id","field","value","left_surface",
    }
    if set(raw)!=allowed:
        return _fail("EXPLICIT_FIELD_EDGE_FIELD_SET_NOT_EXACT")

    try:
        source_id=_token(raw.get("source_id"),"SOURCE_ID")
        raw_span=raw.get("raw_span")
        if not isinstance(raw_span,str) or not raw_span.strip():
            raise ValueError("RAW_SPAN_REQUIRED")
        scope_id=_token(raw.get("scope_id"),"SCOPE_ID")
        effect_id=_token(raw.get("effect_id"),"EFFECT_ID")
        field=_token(raw.get("field"),"FIELD")
        if field not in FIELDS:
            raise ValueError("FIELD_UNSUPPORTED:"+field)
        left_surface=_token(raw.get("left_surface"),"LEFT_SURFACE")
        normalized=_normalize_field(field,raw.get("value"))
    except Exception as exc:
        return _fail(type(exc).__name__+":"+str(exc))

    left_id=_mention_id(source_id,scope_id,raw_span)
    right_id=field_concept_id(
        scope_id=scope_id,
        effect_id=effect_id,
        field=field,
        value=normalized,
    )
    right_surface=_canon(normalized)

    problem={
        "left_id":left_id,
        "right_id":right_id,
        "left_surface":left_surface,
        "right_surface":right_surface,
        "scope_id":scope_id,
        "required_relation":"LEFT_ENTAILS_RIGHT",
        "explicit_definition_sources":[{
            "source_id":source_id,
            "scope_id":scope_id,
            "source_text":raw_span,
        }],
    }
    result=resolve(problem)
    if not isinstance(result,Mapping):
        return _fail("SEMANTIC_RELATION_CONTROL_RETURNED_NO_RESULT")
    if str(result.get("status") or "").startswith("FAIL_CLOSED"):
        return _fail(
            "SEMANTIC_RELATION_CONTROL_FAIL_CLOSED:"
            +str(result.get("reason") or result.get("status")),
            control_result=deepcopy(dict(result)),
        )

    proved=(
        result.get("pass") is True
        and isinstance(result.get("proved_facts"),Mapping)
        and result["proved_facts"].get("left_entails_right") is True
        and result.get("scope_id")==scope_id
        and result.get("left_id")==left_id
        and result.get("right_id")==right_id
    )
    if not proved:
        return {
            "schema":SCHEMA,
            "status":"UNKNOWN__REGISTERED_RELATION_NOT_PROVED",
            "pass":False,
            "reason":"EXACT_SOURCE_DEFINITION_DID_NOT_PROVE_FIELD_EDGE",
            "left_id":left_id,
            "right_id":right_id,
            "right_surface":right_surface,
            "control_result":deepcopy(dict(result)),
            "semantic_relation_authority":False,
            "execution_authority":False,
            "acceptance_authority":False,
            "terminal_authority":False,
        }

    evidence_basis={
        "registered_verifier":"EXPLICIT_SOURCE_EFFECT_FIELD_DEFINITION_V1",
        "source_id":source_id,
        "raw_span_sha256":sha256(raw_span.encode("utf-8")).hexdigest(),
        "scope_id":scope_id,
        "left_id":left_id,
        "right_id":right_id,
        "left_surface":left_surface,
        "right_surface":right_surface,
        "effect_id":effect_id,
        "field":field,
        "value":normalized,
        "control_status":result.get("status"),
        "explicit_equivalence":deepcopy(
            result.get("explicit_equivalence")
        ),
    }
    receipt={
        "pass":True,
        "schema":RECEIPT_SCHEMA,
        "scope_id":scope_id,
        "source_id":left_id,
        "target_id":right_id,
        "relation":"ENTAILS",
        "source_semantics_authenticated":True,
        "target_semantics_authenticated":True,
        "relation_semantics_authenticated":True,
        "verification_authority_mutated":False,
        "evidence_sha256":_sha(evidence_basis),
    }
    receipt["receipt_sha256"]=_sha(receipt)
    receipt["registry_verifier_id"]=(
        "EXPLICIT_SOURCE_EFFECT_FIELD_DEFINITION_V1"
    )
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


def evaluate(raw:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(raw,Mapping):
        return _fail("EDGE_EVIDENCE_NOT_OBJECT")
    if raw.get("schema")==EXPLICIT_FIELD_EDGE_SCHEMA:
        return _explicit_field_candidate(raw)
    return {
        "schema":SCHEMA,
        "status":"UNRESOLVED__NO_REGISTERED_RELATION_VERIFIER_MATCHED",
        "pass":False,
        "evidence_schema":raw.get("schema"),
        "semantic_relation_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
    }


def verify(raw:Mapping[str,Any])->Mapping[str,Any]|None:
    """Callback compatible with semantic_relation_entailment_dag_v1."""
    out=evaluate(raw)
    if out.get("pass") is True and isinstance(out.get("receipt"),Mapping):
        return deepcopy(dict(out["receipt"]))
    return None
