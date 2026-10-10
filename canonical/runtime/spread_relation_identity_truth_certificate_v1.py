"""Positive-only semantic truth certificate for bounded spread relation identity."""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import spread_relation_context_identity_v1 as identity

SCHEMA="PROJECT_BRAIN_SPREAD_RELATION_IDENTITY_TRUTH_CERTIFICATE_V1"
TRUTH_KIND="SPREAD_RELATION_IDENTITY"
KNOWN={identity.BID_ASK,identity.CORP_TSY}


def _fail(reason:str,**detail:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "predicate_id":None,"predicate_truth":"UNKNOWN",
        "truthful_precommitment_observation":False,
        "semantic_truth_authority":False,"semantic_identity_authority":False,
        "global_identity_authority":False,"policy_adequacy_authority":False,
        "execution_authority":False,"acceptance_authority":False,
        "promotion_authority":False,"terminal_authority":False,
        "terminal_credit_delta":0,**detail,
    }


def checked_predicate_id(*,source_id:str,source_text:str,start:int,end:int,target_concept_id:str)->str:
    if (
        not isinstance(source_text,str) or not source_text
        or isinstance(start,bool) or not isinstance(start,int)
        or isinstance(end,bool) or not isinstance(end,int)
        or start<0 or end<=start or end>len(source_text)
    ):
        raise ValueError("SOURCE_SPAN_INVALID")
    sid=str(source_id or "").strip()
    target=str(target_concept_id or "").strip()
    if not sid:
        raise ValueError("SOURCE_ID_REQUIRED")
    if target not in KNOWN:
        raise ValueError("TARGET_CONCEPT_UNSUPPORTED")
    material={
        "source_id":sid,
        "source_text_sha256":sha256(source_text.encode("utf-8")).hexdigest(),
        "source_span":[start,end],
        "source_span_sha256":sha256(source_text[start:end].encode("utf-8")).hexdigest(),
        "target_concept_id":target,
        "certificate_schema":SCHEMA,
    }
    raw=json.dumps(material,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "spread-relation-identity-sha256:"+sha256(raw).hexdigest()


def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    allowed={"truth_kind","predicate_id","source_text","source_id","start","end","target_concept_id"}
    extra=set(payload)-allowed
    if extra:
        return _fail("UNMODELED_FIELDS:"+",".join(sorted(str(x) for x in extra)))
    if payload.get("truth_kind") not in (None,TRUTH_KIND):
        return _fail("TRUTH_KIND_INVALID")
    requested=str(payload.get("predicate_id") or "").strip()
    if not requested:
        return _fail("PREDICATE_ID_REQUIRED")
    source_text=payload.get("source_text")
    source_id=str(payload.get("source_id") or "").strip()
    start=payload.get("start")
    end=payload.get("end")
    target=str(payload.get("target_concept_id") or "").strip()
    try:
        checked=checked_predicate_id(
            source_id=source_id,source_text=source_text,start=start,end=end,
            target_concept_id=target,
        )
    except Exception as exc:
        return _fail(type(exc).__name__+":"+str(exc))

    resolved=identity.resolve_occurrence(source_text,start=start,end=end)
    if resolved.get("status")=="FAIL_CLOSED":
        return _fail("SPREAD_RELATION_AUTHORITY_FAIL_CLOSED",resolution=resolved)
    if resolved.get("pass") is not True:
        return {
            "schema":SCHEMA,"pass":False,
            "status":"UNKNOWN__SPREAD_RELATION_IDENTITY_NOT_PROVED",
            "reason":str(resolved.get("status") or "UNRESOLVED"),
            "predicate_id":checked,"requested_predicate_id":requested,
            "requested_predicate_id_authority":False,"predicate_truth":"UNKNOWN",
            "target_concept_id":target,"resolution":resolved,
            "truthful_precommitment_observation":False,
            "semantic_truth_authority":False,"semantic_identity_authority":False,
            "global_identity_authority":False,"policy_adequacy_authority":False,
            "execution_authority":False,"acceptance_authority":False,
            "promotion_authority":False,"terminal_authority":False,
            "terminal_credit_delta":0,
        }

    selected=str(resolved.get("concept_id") or "")
    if selected!=target:
        return {
            "schema":SCHEMA,"pass":False,
            "status":"UNKNOWN__DIFFERENT_PROVED_SPREAD_IDENTITY",
            "reason":"DIFFERENT_PROVED_IDENTITY_DOES_NOT_BY_ITSELF_PROVE_NEGATION",
            "predicate_id":checked,"requested_predicate_id":requested,
            "requested_predicate_id_authority":False,"predicate_truth":"UNKNOWN",
            "target_concept_id":target,"selected_concept_id":selected,
            "resolution":resolved,
            "truthful_precommitment_observation":False,
            "semantic_truth_authority":False,"semantic_identity_authority":False,
            "global_identity_authority":False,"policy_adequacy_authority":False,
            "execution_authority":False,"acceptance_authority":False,
            "promotion_authority":False,"terminal_authority":False,
            "terminal_credit_delta":0,
        }

    return {
        "schema":SCHEMA,"pass":True,
        "status":"PASS__SOURCE_BOUND_SPREAD_RELATION_IDENTITY_PROVED_TRUE",
        "predicate_id":checked,"requested_predicate_id":requested,
        "requested_predicate_id_authority":False,"predicate_truth":"TRUE",
        "target_concept_id":target,"selected_concept_id":selected,
        "resolution":resolved,
        "truthful_precommitment_observation":True,
        "semantic_truth_authority":True,"semantic_identity_authority":True,
        "global_identity_authority":False,"open_world_finance_semantics_complete":False,
        "policy_adequacy_authority":False,"execution_authority":False,
        "acceptance_authority":False,"promotion_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,
        "boundary":"RELATION_ENDPOINT_BOUND_SPREAD_IDENTITY_ONLY__NO_GLOBAL_WORD_SENSE_OR_OPEN_WORLD_COMPLETENESS",
    }
