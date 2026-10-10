"""Candidate-only distinguishing-evidence acquisition for R3 verification gaps.

A provider receives one exact minimum structural evidence request and may return
only evidence fields explicitly named by one candidate request bundle. It never
returns or replaces the complete success subject.

The Brain merges admitted evidence into the retained proof subject itself, so
task identity and all unrequested retained fields remain Brain-owned. The merged
candidate still has zero truth/verification/promotion/acceptance authority and
must strictly reduce the gap before being re-ingested as an ordinary unverified
R3 success observation.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_success_adapter_author_context_v1 as author_context
from canonical.runtime import r3_verification_frontier_repair_reducer_v1 as reducer
from canonical.runtime import r3_distinguishing_evidence_request_v1 as request_compiler

SCHEMA = "PROJECT_BRAIN_R3_DISTINGUISHING_EVIDENCE_ACQUISITION_V1"
CANDIDATE_SCHEMA = "PROJECT_BRAIN_R3_DISTINGUISHING_EVIDENCE_CANDIDATE_V1"
SURFACE = "R3_DISTINGUISHING_EVIDENCE_ACQUISITION"

_OBLIGATION_FIELDS = {
    "NONEMPTY_SELECTED_PLAN": "selected_plan",
    "NONEMPTY_VERIFIED_TARGET_EFFECT_SET": "verified_target_effects",
    "CONTROLLER_CHECKPOINT_BOUND": "controller_checkpoint",
    "EXECUTION_COUNT_MATCHES_SELECTED_PLAN_AND_NONZERO": "execution",
    "ALL_EXECUTION_ROWS_PASS": "execution",
    "COMPOSITION_DIGEST_PRESENT_FOR_EVERY_EXECUTION_ROW": "execution",
    "SEMANTIC_ACCEPTANCE_COMPLETE": "semantic_acceptance_complete",
    "RAW_GOAL_DIGEST_BOUND": "raw_goal_sha256",
    "RAW_TASK_CONTRACT_DIGEST_BOUND": "raw_task_contract_sha256",
    "RAW_GOAL_ACCEPTANCE_BINDING_PRESENT": "raw_goal_acceptance",
    "RAW_ACCEPTANCE_OBLIGATION_COUNT_POSITIVE": "raw_acceptance_obligation_count",
    "ALL_RAW_ACCEPTANCE_OBLIGATIONS_ACCEPTED": "accepted_raw_obligation_ids",
}


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "progress": False,
        "provider_truth_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _bundle_for_route(
    compiled_request: Mapping[str, Any],
    route: str,
) -> Mapping[str, Any] | None:
    rows = compiled_request.get("candidate_evidence_bundles")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        return None
    matched = [
        row
        for row in rows
        if isinstance(row, Mapping) and str(row.get("route") or "") == route
    ]
    return matched[0] if len(matched) == 1 else None


def _allowed_fields(bundle: Mapping[str, Any]) -> set[str] | None:
    obligations = bundle.get("missing_obligations")
    if (
        not isinstance(obligations, Sequence)
        or isinstance(obligations, (str, bytes, bytearray))
    ):
        return None
    out: set[str] = set()
    for raw in obligations:
        obligation = str(raw or "").strip()
        field = _OBLIGATION_FIELDS.get(obligation)
        if not field:
            return None
        out.add(field)
    return out


def _candidate_from_retained_material(
    material: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    out = deepcopy(dict(material))
    out["schema"] = material.get("source_schema")
    out["status"] = material.get("source_status")
    out["pass"] = True
    for key, value in evidence.items():
        out[key] = deepcopy(value)
    return out


def acquire(
    compiled_request: Mapping[str, Any],
    *,
    observation_id: str,
    state_path,
    provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
    provider_id: str,
    improvement_work_id: str | None = None,
    blocked_success_work_id: str | None = None,
) -> dict[str, Any]:
    if (
        not isinstance(compiled_request, Mapping)
        or compiled_request.get("pass") is not True
        or compiled_request.get("schema")
        != "PROJECT_BRAIN_R3_DISTINGUISHING_EVIDENCE_REQUEST_V1"
    ):
        return _fail("DISTINGUISHING_EVIDENCE_REQUEST_NOT_AUTHENTICATED")
    request_sha = str(compiled_request.get("request_sha256") or "").strip()
    if not request_sha:
        return _fail("DISTINGUISHING_EVIDENCE_REQUEST_DIGEST_MISSING")
    request_base = deepcopy(dict(compiled_request))
    request_base.pop("request_sha256", None)
    expected_request_sha = request_compiler._digest(request_base)
    if request_sha != expected_request_sha:
        return _fail(
            "DISTINGUISHING_EVIDENCE_REQUEST_DIGEST_MISMATCH",
            expected_request_sha256=expected_request_sha,
            observed_request_sha256=request_sha,
        )
    oid = str(observation_id or "").strip()
    if not oid:
        return _fail("SOURCE_OBSERVATION_ID_REQUIRED")

    provider_request = {
        "kind": "R3_VERIFICATION_FRONTIER_DISTINGUISHING_EVIDENCE",
        "request_sha256": request_sha,
        "observation_id": oid,
        "improvement_work_id": str(improvement_work_id or "").strip() or None,
        "blocked_success_work_id": str(blocked_success_work_id or "").strip() or None,
        "distinguishing_evidence_request": deepcopy(dict(compiled_request)),
        "provider_contract": {
            "candidate_evidence_only": True,
            "complete_success_subject_may_not_be_replaced": True,
            "automatic_effectful_replay_authorized": False,
            "provider_truth_authority": False,
            "provider_verification_authority": False,
            "provider_promotion_authority": False,
            "provider_acceptance_authority": False,
            "provider_terminal_authority": False,
            "required_downstream_action": (
                "MERGE_ONLY_REQUESTED_EVIDENCE_INTO_RETAINED_PROOF__"
                "REINGEST_AS_NEW_SUCCESS_OBSERVATION__THEN_USE_EXISTING_"
                "ADAPTER_AND_INDEPENDENT_VERIFICATION_PIPELINE"
            ),
        },
    }
    result = provider(deepcopy(provider_request))
    if not isinstance(result, Mapping):
        return _fail("DISTINGUISHING_EVIDENCE_PROVIDER_RETURNED_NO_RESULT")

    for key in (
        "provider_truth_authority",
        "truth_authority",
        "verification_authority",
        "promotion_authority",
        "acceptance_authority",
        "terminal_authority",
    ):
        if result.get(key) is True:
            return _fail(
                "DISTINGUISHING_EVIDENCE_PROVIDER_AUTHORITY_ESCALATION_REJECTED",
                authority_field=key,
            )
    if (
        result.get("schema") != CANDIDATE_SCHEMA
        or result.get("pass") is not True
        or str(result.get("request_sha256") or "").strip() != request_sha
    ):
        return _fail("DISTINGUISHING_EVIDENCE_CANDIDATE_BINDING_INVALID")

    route = str(result.get("route") or "").strip()
    bundle = _bundle_for_route(compiled_request, route)
    if not isinstance(bundle, Mapping):
        return _fail("DISTINGUISHING_EVIDENCE_ROUTE_NOT_REQUESTED")
    allowed_fields = _allowed_fields(bundle)
    if allowed_fields is None:
        return _fail("DISTINGUISHING_EVIDENCE_REQUEST_BUNDLE_INVALID")
    evidence = result.get("evidence")
    if not isinstance(evidence, Mapping):
        return _fail("DISTINGUISHING_EVIDENCE_FIELDS_NOT_OBJECT")
    evidence_keys = {str(key) for key in evidence}
    if not evidence_keys:
        return _fail("DISTINGUISHING_EVIDENCE_FIELDS_EMPTY")
    unrequested = sorted(evidence_keys - allowed_fields)
    if unrequested:
        return _fail(
            "DISTINGUISHING_EVIDENCE_UNREQUESTED_FIELDS_REJECTED",
            unrequested_fields=unrequested,
        )

    proof = learning.get_success_proof_context(oid, state_path=state_path)
    replay = learning.get_success_replay_context(oid, state_path=state_path)
    material = proof.get("material")
    if not isinstance(material, Mapping):
        return _fail("SOURCE_PROOF_MATERIAL_INVALID")

    candidate = _candidate_from_retained_material(material, evidence)
    candidate_proof = learning._make_success_proof_capsule(candidate)
    if not isinstance(candidate_proof, Mapping):
        return _fail("DISTINGUISHING_EVIDENCE_CANDIDATE_PROOF_CAPSULE_UNAVAILABLE")

    candidate_context = author_context.compile_context(
        {
            "proof_capsule_sha256": candidate_proof.get("sha256"),
            "material": candidate_proof.get("material"),
        },
        replay,
    )
    if candidate_context.get("pass") is not True:
        return _fail(
            "DISTINGUISHING_EVIDENCE_CANDIDATE_CONTEXT_INVALID",
            candidate_context=deepcopy(dict(candidate_context)),
        )
    reduced = reducer.reduce_author_context(candidate_context)
    if reduced.get("pass") is not True:
        return _fail(
            "DISTINGUISHING_EVIDENCE_CANDIDATE_REDUCTION_FAILED",
            repair_class_reduction=deepcopy(dict(reduced)),
        )

    admissible = set(reduced.get("admissible_repair_classes") or [])
    improved = reducer.ADAPTER in admissible or reducer.READONLY_VERIFIER in admissible
    next_request = None
    if not improved and reduced.get("must_acquire_new_distinguishing_evidence") is True:
        next_request = request_compiler.compile_request(candidate_context)
        old_min = compiled_request.get("minimum_missing_obligation_count")
        new_min = next_request.get("minimum_missing_obligation_count")
        improved = (
            next_request.get("pass") is True
            and isinstance(old_min, int)
            and not isinstance(old_min, bool)
            and isinstance(new_min, int)
            and not isinstance(new_min, bool)
            and new_min < old_min
        )
    if not improved:
        return _fail(
            "DISTINGUISHING_EVIDENCE_CANDIDATE_DID_NOT_REDUCE_GAP",
            repair_class_reduction=deepcopy(dict(reduced)),
            next_distinguishing_evidence_request=(
                deepcopy(dict(next_request))
                if isinstance(next_request, Mapping)
                else None
            ),
        )

    recorded = learning.record_success_observation(
        candidate,
        surface=SURFACE,
        state_path=state_path,
        replay_context=replay.get("context"),
    )
    if (
        recorded.get("pass") is not True
        or recorded.get("proof_available") is not True
        or not str(recorded.get("observation_id") or "").strip()
    ):
        return _fail(
            "DISTINGUISHING_EVIDENCE_REINGESTION_DID_NOT_PERSIST_PROOF",
            reingestion=deepcopy(dict(recorded)),
        )

    return {
        "schema": SCHEMA,
        "status": "PASS__DISTINGUISHING_EVIDENCE_CANDIDATE_REINGESTED",
        "pass": True,
        "progress": True,
        "source_observation_id": oid,
        "new_observation_id": recorded.get("observation_id"),
        "new_improvement_work_id": recorded.get("improvement_work_id"),
        "request_sha256": request_sha,
        "selected_route": route,
        "accepted_evidence_keys": sorted(evidence_keys),
        "provider_id": str(provider_id or "").strip() or "UNSPECIFIED_PROVIDER",
        "repair_class_reduction": deepcopy(dict(reduced)),
        "provider_truth_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
