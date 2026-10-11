"""Successor semantic truth certificate for bounded loss-cushion grounding.

V6 preserves the exact V5 predicate identity function. The only new input is an
optional checker-owned governing-requirement candidate that V8 may use as one
additional observation over the already-bound four-way candidate inventory.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import regcap_loss_cushion_truth_certificate_v5 as prior
from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v8 as grounding

SCHEMA = "PROJECT_BRAIN_REGCAP_LOSS_CUSHION_TRUTH_CERTIFICATE_V6"
TRUTH_KIND = prior.TRUTH_KIND
CLAIMS = prior.CLAIMS
checked_predicate_id = prior.checked_predicate_id


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "predicate_id": None,
        "predicate_truth": "UNKNOWN",
        "truthful_precommitment_observation": False,
        "semantic_truth_authority": False,
        "semantic_identity_authority": False,
        "global_identity_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **detail,
    }


def _unknown(
    *,
    checked_id: str,
    requested_id: str,
    claim_kind: str,
    target: str,
    reason: str,
    grounding_result: Mapping[str, Any],
) -> dict[str, Any]:
    request = grounding_result.get("minimum_policy_changing_information_request")
    next_fields: dict[str, Any] = {}
    if (
        grounding_result.get("minimum_policy_changing_information_request_available")
        is True
        and isinstance(request, Mapping)
    ):
        next_fields = {
            "next_information_request": dict(request),
            "next_required_edge": (
                "REGCAP_LOSS_CUSHION_MINIMUM_POLICY_CHANGING_INFORMATION"
            ),
            "next_information_request_source": grounding.SCHEMA,
        }
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNKNOWN__REGCAP_LOSS_CUSHION_CLAIM_NOT_PROVED",
        "reason": reason,
        "predicate_id": checked_id,
        "requested_predicate_id": requested_id,
        "requested_predicate_id_authority": False,
        "predicate_truth": "UNKNOWN",
        "claim_kind": claim_kind,
        "target_concept_id": target,
        "grounding_result": dict(grounding_result),
        "truthful_precommitment_observation": False,
        "semantic_truth_authority": False,
        "semantic_identity_authority": False,
        "global_identity_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **next_fields,
    }


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")
    allowed = {
        "truth_kind",
        "predicate_id",
        "claim_kind",
        "source_text",
        "source_id",
        "start",
        "end",
        "target_concept_id",
        "governing_requirement_candidate",
    }
    extra = set(payload) - allowed
    if extra:
        return _fail("UNMODELED_FIELDS:" + ",".join(sorted(str(x) for x in extra)))
    if payload.get("truth_kind") not in (None, TRUTH_KIND):
        return _fail("TRUTH_KIND_INVALID")

    requested_id = str(payload.get("predicate_id") or "").strip()
    claim_kind = str(payload.get("claim_kind") or "").strip().upper()
    source_text = payload.get("source_text")
    source_id = str(payload.get("source_id") or "").strip()
    start = payload.get("start")
    end = payload.get("end")
    target = str(payload.get("target_concept_id") or "").strip()
    if not requested_id:
        return _fail("PREDICATE_ID_REQUIRED")
    if claim_kind not in CLAIMS:
        return _fail("CLAIM_KIND_INVALID")

    try:
        checked = checked_predicate_id(
            source_id=source_id,
            source_text=source_text,
            start=start,
            end=end,
            claim_kind=claim_kind,
            target_concept_id=target,
        )
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))

    result = grounding.ground(
        source_text,
        source_id=source_id,
        start=start,
        end=end,
        governing_requirement_candidate=payload.get("governing_requirement_candidate"),
    )
    if result.get("status") == "FAIL_CLOSED":
        return _fail(
            "REGCAP_GROUNDING_FAIL_CLOSED",
            grounding_reason=result.get("reason"),
            grounding_result=result,
        )

    identity_authority = False
    relative_authority = False
    if claim_kind == "RELATIVE_RIVAL_SELECTION":
        selected = result.get("relative_selected_concept_id")
        if result.get("relative_selection_authority") is not True or not selected:
            return _unknown(
                checked_id=checked,
                requested_id=requested_id,
                claim_kind=claim_kind,
                target=target,
                reason="UNIQUE_BOUND_RIVAL_SELECTION_NOT_PROVED",
                grounding_result=result,
            )
        relative_authority = True
        if selected == target:
            truth = "TRUE"
            status = "PASS__BOUND_RIVAL_SELECTION_PROVED_TRUE"
        elif target in (result.get("candidate_concept_ids") or []):
            truth = "FALSE"
            status = "PASS__BOUND_RIVAL_SELECTION_PROVED_FALSE"
        else:
            return _unknown(
                checked_id=checked,
                requested_id=requested_id,
                claim_kind=claim_kind,
                target=target,
                reason="TARGET_OUTSIDE_DECLARED_BOUND_RIVALS",
                grounding_result=result,
            )
    else:
        mapped = result.get("mapped_concept_id")
        if result.get("semantic_identity_authority") is not True or not mapped:
            return _unknown(
                checked_id=checked,
                requested_id=requested_id,
                claim_kind=claim_kind,
                target=target,
                reason="SOURCE_LOCAL_IDENTITY_NOT_PROVED",
                grounding_result=result,
            )
        if mapped != target:
            return _unknown(
                checked_id=checked,
                requested_id=requested_id,
                claim_kind=claim_kind,
                target=target,
                reason="DIFFERENT_SOURCE_LOCAL_IDENTITY_DOES_NOT_BY_ITSELF_PROVE_NEGATION",
                grounding_result=result,
            )
        truth = "TRUE"
        status = "PASS__SOURCE_LOCAL_IDENTITY_PROVED_TRUE"
        identity_authority = True

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": status,
        "predicate_id": checked,
        "requested_predicate_id": requested_id,
        "requested_predicate_id_authority": False,
        "predicate_truth": truth,
        "claim_kind": claim_kind,
        "target_concept_id": target,
        "grounding_result": result,
        "truthful_precommitment_observation": True,
        "semantic_truth_authority": True,
        "relative_selection_authority": relative_authority,
        "semantic_identity_authority": identity_authority,
        "global_identity_authority": False,
        "candidate_universe_complete": False,
        "open_world_ontology_complete": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "predicate_identity_compatibility": "EXACT_V5_CHECKED_PREDICATE_ID_PRESERVED",
        "boundary": (
            "AUTHORITY_CANDIDATE_IS_ADDITIONAL_OBSERVATION_NOT_PREDICATE_REPLACEMENT__"
            "NO_OPEN_WORLD_COMPLETENESS_OR_TERMINAL_AUTHORITY"
        ),
    }
