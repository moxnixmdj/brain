"""Semantic truth certificate for authenticated bounded TLAC/MREL sense selection V1."""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import tlac_mrel_authenticated_sense_selector_v1 as selector
from canonical.runtime import tlac_mrel_identity_discriminator_v1 as tlac

SCHEMA="PROJECT_BRAIN_TLAC_MREL_BOUNDED_SENSE_TRUTH_CERTIFICATE_V1"
TRUTH_KIND="TLAC_MREL_BOUNDED_SENSE"


def _sha(value:Any)->str:
    return sha256(
        json.dumps(
            value,sort_keys=True,separators=(",",":"),
            ensure_ascii=False,allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def checked_predicate_id(
    *,
    source_id:str,
    source_text:str,
    target_concept_id:str,
)->str:
    source_id=str(source_id or "").strip()
    target=str(target_concept_id or "").strip()
    if not source_id:
        raise ValueError("SOURCE_ID_REQUIRED")
    if not isinstance(source_text,str) or not source_text:
        raise ValueError("SOURCE_TEXT_REQUIRED")
    if target not in tlac.DOMAIN:
        raise ValueError("TARGET_CONCEPT_UNSUPPORTED")
    return "tlac-mrel-bounded-sense-sha256:"+_sha({
        "truth_kind":TRUTH_KIND,
        "source_id":source_id,
        "source_text_sha256":sha256(source_text.encode("utf-8")).hexdigest(),
        "target_concept_id":target,
        "scope_id":tlac.SCOPE_ID,
    })


def _base(status:str,*,passed:bool=False,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "predicate_truth":"UNKNOWN",
        "truthful_precommitment_observation":False,
        "semantic_truth_authority":False,
        "semantic_identity_authority":False,
        "global_identity_authority":False,
        "open_world_ontology_complete":False,
        "policy_adequacy_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        **extra,
    }


def evaluate(
    payload:Mapping[str,Any],
    *,
    repo_root:Any=None,
    projection_verifier:Any=None,
)->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _base("FAIL_CLOSED",reason="PAYLOAD_MAPPING_REQUIRED")
    allowed={
        "truth_kind","predicate_id","source_text","source_id","target_concept_id"
    }
    extra=set(payload)-allowed
    if extra:
        return _base(
            "FAIL_CLOSED",
            reason="UNMODELED_FIELDS:"+",".join(sorted(str(x) for x in extra)),
        )
    if payload.get("truth_kind") not in (None,TRUTH_KIND):
        return _base("FAIL_CLOSED",reason="TRUTH_KIND_INVALID")

    requested=str(payload.get("predicate_id") or "").strip()
    source_text=payload.get("source_text")
    source_id=str(payload.get("source_id") or "").strip()
    target=str(payload.get("target_concept_id") or "").strip()
    if not requested:
        return _base("FAIL_CLOSED",reason="PREDICATE_ID_REQUIRED")
    try:
        checked=checked_predicate_id(
            source_id=source_id,
            source_text=source_text,
            target_concept_id=target,
        )
    except Exception as exc:
        return _base("FAIL_CLOSED",reason=type(exc).__name__+":"+str(exc))

    selected=selector.resolve(
        source_text,
        source_id=source_id,
        repo_root=repo_root,
        projection_verifier=projection_verifier,
    )
    if selected.get("status")=="FAIL_CLOSED":
        return _base(
            "FAIL_CLOSED",
            reason="BOUNDED_SENSE_SELECTOR_FAIL_CLOSED:"
            +str(selected.get("reason") or "UNKNOWN"),
            predicate_id=checked,
            requested_predicate_id=requested,
            requested_predicate_id_authority=False,
            selector_result=selected,
        )
    if selected.get("pass") is not True:
        return _base(
            "OPEN__TLAC_MREL_BOUNDED_SENSE_UNRESOLVED",
            predicate_id=checked,
            requested_predicate_id=requested,
            requested_predicate_id_authority=False,
            target_concept_id=target,
            next_observation_id=selected.get("next_observation_id"),
            next_information_request=selected.get("next_information_request"),
            selector_result=selected,
            boundary=(
                "INSUFFICIENT_CONTEXT_REMAINS_UNKNOWN__"
                "MINIMUM_AUTHENTICATED_NEXT_OBSERVATION_EXPOSED_WHEN_AVAILABLE"
            ),
        )

    chosen=str(selected.get("selected_concept_id") or "")
    truth="TRUE" if chosen==target else "FALSE"
    return _base(
        "PASS__TLAC_MREL_BOUNDED_SENSE_TRUTH_PROVED",
        passed=True,
        predicate_truth=truth,
        truthful_precommitment_observation=True,
        semantic_truth_authority=True,
        semantic_identity_authority=True,
        predicate_id=checked,
        requested_predicate_id=requested,
        requested_predicate_id_authority=False,
        target_concept_id=target,
        selected_concept_id=chosen,
        selector_result=selected,
        candidate_universe_complete=True,
        candidate_universe_complete_only_for_scope_id=tlac.SCOPE_ID,
        boundary=(
            "TRUE_OR_FALSE_ONLY_INSIDE_AUTHENTICATED_COMPLETE_TLAC_MREL_PAIR_SCOPE__"
            "NO_GLOBAL_IDENTITY_OR_OPEN_WORLD_ONTOLOGY_COMPLETENESS"
        ),
    )
