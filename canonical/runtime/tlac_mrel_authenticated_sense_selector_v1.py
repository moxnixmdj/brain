"""Authenticated TLAC/MREL bounded context-sense selector V1.

This is the first real binding of the generic authenticated bounded sense
selector. It reuses the existing TLAC/MREL source-backed authority and exact
context compiler, but delegates candidate filtering and minimum-next-evidence
selection to the generic kernel.

Capability gain over the earlier pair resolver:
- same authenticated unique selection when context proves one side;
- when context is insufficient, returns the exact minimum matrix observation
  required next instead of only returning an open status.

Authority remains relative to the exact authenticated two-candidate task scope.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import authenticated_bounded_context_sense_selector_v1 as generic
from canonical.runtime import tlac_mrel_identity_discriminator_v1 as tlac

SCHEMA="PROJECT_BRAIN_TLAC_MREL_AUTHENTICATED_SENSE_SELECTOR_V1"


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


def _base(status:str,*,passed:bool=False,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "selected_concept_id":None,
        "bounded_scope_identity_authority":False,
        "semantic_identity_authority":False,
        "global_identity_authority":False,
        "open_world_ontology_complete":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        **extra,
    }


def resolve(
    source_text:str,
    *,
    source_id:str,
    repo_root:Any=None,
    projection_verifier:Any=None,
)->dict[str,Any]:
    if not isinstance(source_text,str) or not source_text.strip():
        return _base("FAIL_CLOSED",reason="SOURCE_TEXT_REQUIRED")
    source_id=str(source_id or "").strip()
    if not source_id:
        return _base("FAIL_CLOSED",reason="SOURCE_ID_REQUIRED")

    def authority():
        if projection_verifier is None:
            return tlac.verify_authority(repo_root=repo_root)
        return tlac.verify_authority(
            repo_root=repo_root,
            projection_verifier=projection_verifier,
        )

    def candidate_verifier(_request:Mapping[str,Any])->dict[str,Any]:
        checked=authority()
        if checked.get("pass") is not True:
            return {
                "pass":False,
                "status":"FAIL_CLOSED",
                "reason":"TLAC_MREL_AUTHORITY_FAILED",
            }
        return {
            "pass":True,
            "status":"PASS__AUTHENTICATED_TLAC_MREL_PAIR_SCOPE",
            "scope_id":tlac.SCOPE_ID,
            "candidate_ids":list(tlac.DOMAIN),
            "candidate_universe_complete":True,
            "authority_sha256":checked["authority_sha256"],
            "bounded_scope_only":True,
        }

    def matrix_verifier(_request:Mapping[str,Any])->dict[str,Any]:
        checked=authority()
        if checked.get("pass") is not True:
            return {
                "pass":False,
                "status":"FAIL_CLOSED",
                "reason":"TLAC_MREL_MATRIX_AUTHORITY_FAILED",
            }
        matrix_material={
            "scope_id":tlac.SCOPE_ID,
            "observation_id":tlac.OBSERVATION_ID,
            "candidate_domain":list(tlac.DOMAIN),
            "outcomes":dict(tlac.OUTCOMES),
            "authority_sha256":checked["authority_sha256"],
        }
        return {
            "pass":True,
            "status":"PASS__AUTHENTICATED_TLAC_MREL_DISCRIMINATOR_MATRIX",
            "scope_id":tlac.SCOPE_ID,
            "semantic_truth_authority":True,
            "candidate_domain":list(tlac.DOMAIN),
            "outcome_maps_complete_relative_to_matrix_domain":True,
            "matrix_sha256":_sha(matrix_material),
            "observations":[{
                "observation_id":tlac.OBSERVATION_ID,
                "cost_units":1,
                "outcomes":dict(tlac.OUTCOMES),
            }],
        }

    def observation_verifier(request:Mapping[str,Any])->dict[str,Any]:
        if not isinstance(request,Mapping):
            return {
                "pass":False,"status":"FAIL_CLOSED",
                "reason":"OBSERVATION_REQUEST_NOT_OBJECT",
            }
        compiled=tlac.compile_context(
            source_text,
            source_id=source_id,
        )
        if compiled.get("status")=="FAIL_CLOSED":
            return {
                "pass":False,
                "status":"FAIL_CLOSED",
                "reason":"TLAC_MREL_CONTEXT_COMPILER_FAIL_CLOSED",
                "compiler_result":compiled,
            }
        if compiled.get("pass") is not True:
            return {
                "pass":False,
                "status":compiled.get("status") or "OPEN__NO_BOUND_CONTEXT",
                "semantic_truth_authority":False,
                "scope_id":tlac.SCOPE_ID,
                "compiler_result":compiled,
            }
        if request.get("observation_id") not in (None,tlac.OBSERVATION_ID):
            return {
                "pass":False,
                "status":"FAIL_CLOSED",
                "reason":"OBSERVATION_ID_MISMATCH",
            }
        material={
            "scope_id":tlac.SCOPE_ID,
            "observation_id":tlac.OBSERVATION_ID,
            "source_id":source_id,
            "source_text_sha256":compiled.get("source_text_sha256"),
            "observed_outcome":compiled.get("observed_outcome"),
        }
        return {
            "pass":True,
            "status":"PASS__AUTHENTICATED_SOURCE_CONTEXT_OBSERVATION",
            "scope_id":tlac.SCOPE_ID,
            "semantic_truth_authority":True,
            "observation_id":tlac.OBSERVATION_ID,
            "observed_outcome":compiled["observed_outcome"],
            "authority_sha256":_sha(material),
            "compiler_result":compiled,
        }

    selected=generic.resolve(
        candidate_universe_request={"scope_id":tlac.SCOPE_ID},
        candidate_universe_verifier=candidate_verifier,
        discriminator_matrix_request={"scope_id":tlac.SCOPE_ID},
        discriminator_matrix_verifier=matrix_verifier,
        observation_requests=[{
            "observation_id":tlac.OBSERVATION_ID,
            "source_id":source_id,
        }],
        observation_verifier=observation_verifier,
    )

    if selected.get("status")=="FAIL_CLOSED":
        return _base(
            "FAIL_CLOSED",
            reason="GENERIC_BOUNDED_SELECTOR_FAIL_CLOSED:"
            +str(selected.get("reason") or "UNKNOWN"),
            selector_result=selected,
        )

    if selected.get("pass") is True:
        concept=str(selected.get("selected_candidate_id") or "")
        if concept not in tlac.DOMAIN:
            return _base(
                "FAIL_CLOSED",
                reason="SELECTED_CONCEPT_OUTSIDE_TLAC_MREL_DOMAIN",
                selector_result=selected,
            )
        return _base(
            "PASS__AUTHENTICATED_TLAC_MREL_CONTEXT_SENSE_SELECTED",
            passed=True,
            selected_concept_id=concept,
            bounded_scope_identity_authority=True,
            semantic_identity_authority=True,
            candidate_universe_complete=True,
            candidate_ids=list(tlac.DOMAIN),
            selector_result=selected,
            boundary=(
                "IDENTITY_ONLY_INSIDE_AUTHENTICATED_TLAC_MREL_PAIR_SCOPE__"
                "GENERIC_SELECTOR_RECOMPUTES_BOUND_UNIVERSE_MATRIX_AND_CONTEXT__"
                "NO_OPEN_WORLD_OR_GLOBAL_IDENTITY"
            ),
        )

    return _base(
        selected.get("status") or "OPEN__TLAC_MREL_CONTEXT_SENSE_UNRESOLVED",
        passed=False,
        candidate_ids=list(tlac.DOMAIN),
        surviving_candidate_ids=selected.get("surviving_candidate_ids"),
        next_observation_id=selected.get("next_observation_id"),
        minimum_worst_case_cost_units=selected.get(
            "minimum_worst_case_cost_units"
        ),
        next_information_request=(
            {
                "kind":"ACQUIRE_AUTHENTICATED_CONTEXT_OBSERVATION",
                "scope_id":tlac.SCOPE_ID,
                "observation_id":selected.get("next_observation_id"),
                "candidate_ids":list(tlac.DOMAIN),
            }
            if selected.get("next_observation_id")
            else None
        ),
        selector_result=selected,
        boundary=(
            "OPEN_STATE_PRESERVES_BOUNDED_PAIR_WITHOUT_GUESSING__"
            "MINIMUM_NEXT_DISCRIMINATOR_EXPOSED_WHEN_AVAILABLE"
        ),
    )
