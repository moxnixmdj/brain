"""Semantic truth certificate for bounded loss-cushion regulatory-capital grounding.

Two deliberately distinct claim types:
- RELATIVE_RIVAL_SELECTION: which concept is selected within the existing
  current expanded bound rival frontier when a relative selection is actually re-proved. This is not concept identity.
- SOURCE_LOCAL_IDENTITY: exact source-local concept identity, only when the inherited stronger source-specific path
  inherits a stronger source-specific proof such as the NY Fed path.

No open-world ontology completeness, policy adequacy, execution, acceptance,
promotion, or terminal authority is granted.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import loss_absorbing_cushion_regcap_grounding_v7 as grounding

SCHEMA = "PROJECT_BRAIN_REGCAP_LOSS_CUSHION_TRUTH_CERTIFICATE_V5"
TRUTH_KIND = "REGCAP_LOSS_CUSHION_GROUNDING"
CLAIMS = {"RELATIVE_RIVAL_SELECTION", "SOURCE_LOCAL_IDENTITY"}


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


def checked_predicate_id(
    *,
    source_id: str,
    source_text: str,
    start: int,
    end: int,
    claim_kind: str,
    target_concept_id: str,
) -> str:
    if (
        not isinstance(source_text, str)
        or not source_text
        or not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end <= start
        or end > len(source_text)
    ):
        raise ValueError("SOURCE_SPAN_INVALID")
    source_id = str(source_id or "").strip()
    claim_kind = str(claim_kind or "").strip().upper()
    target = str(target_concept_id or "").strip()
    if not source_id or claim_kind not in CLAIMS or not target:
        raise ValueError("PREDICATE_IDENTITY_FIELDS_INVALID")
    material = {
        "source_id": source_id,
        "source_text_sha256": sha256(source_text.encode("utf-8")).hexdigest(),
        "source_span": [start, end],
        "source_span_sha256": sha256(source_text[start:end].encode("utf-8")).hexdigest(),
        "claim_kind": claim_kind,
        "target_concept_id": target,
        "grounding_schema": grounding.SCHEMA,
    }
    raw = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return "regcap-loss-cushion-sha256:" + sha256(raw).hexdigest()


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
            "checker_materialization_template": {
                "schema": "PROJECT_BRAIN_SEMANTIC_TRUTH_MATERIALIZATION_TEMPLATE_V1",
                "truth_kind": TRUTH_KIND,
                "claim_kind": claim_kind,
                "target_concept_id": target,
                "requested_predicate_id": requested_id,
                "requested_predicate_id_authority": False,
                "completion_kind": (
                    "AUTHENTICATED_BOUND_CONTEXT_OR_OBSERVATION_REPAIR_FOR_ORIGINAL_PREDICATE"
                ),
                "required_evidence_fields": [
                    "source_text",
                    "source_id",
                    "start",
                    "end",
                ],
                "source_span_must_be_rederived": True,
                "replacement_source_does_not_inherit_original_predicate_identity": True,
                "provider_semantic_truth_authority": False,
                "terminal_authority": False,
            },
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
    )
    if result.get("status") == "FAIL_CLOSED":
        return _fail(
            "REGCAP_GROUNDING_FAIL_CLOSED",
            grounding_reason=result.get("reason"),
            grounding_result=result,
        )

    truth = None
    status = None
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
        "boundary": (
            "RELATIVE_RIVAL_SELECTION_REQUIRES_CURRENT_MREL_AWARE_COMPOSED_FRONTIER_AUTHORITY__RELATIVE_RIVAL_SELECTION_IS_NOT_CONCEPT_IDENTITY__"
            "SOURCE_LOCAL_IDENTITY_REQUIRES_THE_STRONGER_GROUNDING_PATH__"
            "NO_OPEN_WORLD_COMPLETENESS_OR_TERMINAL_AUTHORITY"
        ),
    }
