"""Candidate-only distinguishing-evidence acquisition for R3 verification gaps.

A provider may return one complete candidate success output bound to an exact
minimum distinguishing-evidence request. The provider gains no truth,
verification, promotion, acceptance, execution, or terminal authority.

A candidate is admitted only when:
- it is bound to the exact request digest and original task identity;
- it yields a valid bounded success proof capsule;
- its redacted retained-proof shape strictly reduces the current evidence gap
  or reopens an already-owned verifier-preserving route.

Admitted candidates are re-ingested as ordinary R3 success observations and
must pass the existing adapter + independent verification pipeline later.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_success_adapter_author_context_v1 as author_context
from canonical.runtime import r3_verification_frontier_repair_reducer_v1 as reducer
from canonical.runtime import r3_distinguishing_evidence_request_v1 as request_compiler

SCHEMA = "PROJECT_BRAIN_R3_DISTINGUISHING_EVIDENCE_ACQUISITION_V1"
CANDIDATE_SCHEMA = "PROJECT_BRAIN_R3_DISTINGUISHING_EVIDENCE_CANDIDATE_V1"
SURFACE = "R3_DISTINGUISHING_EVIDENCE_ACQUISITION"


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
            "automatic_effectful_replay_authorized": False,
            "provider_truth_authority": False,
            "provider_verification_authority": False,
            "provider_promotion_authority": False,
            "provider_acceptance_authority": False,
            "provider_terminal_authority": False,
            "required_downstream_action": (
                "REINGEST_AS_NEW_SUCCESS_OBSERVATION_THEN_USE_EXISTING_"
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

    candidate = result.get("candidate_success_output")
    if not isinstance(candidate, Mapping) or candidate.get("pass") is not True:
        return _fail("DISTINGUISHING_EVIDENCE_CANDIDATE_SUCCESS_OUTPUT_INVALID")
    for key in (
        "verification_authority",
        "promotion_authority",
        "acceptance_authority",
        "terminal_authority",
    ):
        if candidate.get(key) is True:
            return _fail(
                "DISTINGUISHING_EVIDENCE_CANDIDATE_OUTPUT_AUTHORITY_ESCALATION_REJECTED",
                authority_field=key,
            )

    proof = learning.get_success_proof_context(oid, state_path=state_path)
    replay = learning.get_success_replay_context(oid, state_path=state_path)
    material = proof.get("material")
    if not isinstance(material, Mapping):
        return _fail("SOURCE_PROOF_MATERIAL_INVALID")
    original_task = str(material.get("task_id") or "").strip()
    candidate_task = str(candidate.get("task_id") or "").strip()
    if original_task and candidate_task != original_task:
        return _fail("DISTINGUISHING_EVIDENCE_CANDIDATE_TASK_BINDING_MISMATCH")

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
        "provider_id": str(provider_id or "").strip() or "UNSPECIFIED_PROVIDER",
        "repair_class_reduction": deepcopy(dict(reduced)),
        "provider_truth_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
