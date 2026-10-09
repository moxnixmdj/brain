"""Compile minimum structural evidence requests for R3 evidence-only gaps.

This module does not acquire evidence and does not infer semantics. It only asks:
given one authenticated, structurally complete redacted success context that the
verified repair reducer classified as NEW_DISTINGUISHING_EVIDENCE-only, which
explicit structural premises are still missing from the two already-owned
non-self-referential verification routes?

The output is a content-bound request normal form. A provider may propose
evidence for the requested obligations, but provider output has zero truth,
verification, promotion, acceptance, or terminal authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime import r3_success_adapter_author_context_v1 as author_context
from canonical.runtime import r3_verification_frontier_repair_reducer_v1 as reducer

SCHEMA = "PROJECT_BRAIN_R3_DISTINGUISHING_EVIDENCE_REQUEST_V1"
REQUEST_KIND = "R3_VERIFICATION_FRONTIER_DISTINGUISHING_EVIDENCE"

CHECKPOINT_ROUTE = "CHECKPOINTED_VERIFIED_EXECUTION"
RAW_ROUTE = "SEMANTICALLY_ACCEPTED_RAW_SUCCESS"

CHECKPOINT_OBLIGATIONS = (
    "NONEMPTY_SELECTED_PLAN",
    "NONEMPTY_VERIFIED_TARGET_EFFECT_SET",
    "CONTROLLER_CHECKPOINT_BOUND",
    "EXECUTION_COUNT_MATCHES_SELECTED_PLAN_AND_NONZERO",
    "ALL_EXECUTION_ROWS_PASS",
    "COMPOSITION_DIGEST_PRESENT_FOR_EVERY_EXECUTION_ROW",
)
RAW_OBLIGATIONS = (
    "SEMANTIC_ACCEPTANCE_COMPLETE",
    "RAW_GOAL_DIGEST_BOUND",
    "RAW_TASK_CONTRACT_DIGEST_BOUND",
    "RAW_GOAL_ACCEPTANCE_BINDING_PRESENT",
    "RAW_ACCEPTANCE_OBLIGATION_COUNT_POSITIVE",
    "ALL_RAW_ACCEPTANCE_OBLIGATIONS_ACCEPTED",
)


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canon(value).encode("utf-8")).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "request_kind": REQUEST_KIND,
        "candidate_evidence_bundles": [],
        "minimum_missing_obligation_count": None,
        "acquisition_authority": False,
        "provider_truth_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _count(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def _rows(value: Any) -> list[Mapping[str, Any]] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return None
    out: list[Mapping[str, Any]] = []
    for row in value:
        if not isinstance(row, Mapping):
            return None
        out.append(row)
    return out


def _checkpoint_missing(proof: Mapping[str, Any]) -> list[str]:
    selected = _count(proof.get("selected_plan_count"))
    target_count = _count(proof.get("verified_target_effect_count"))
    execution_count = _count(proof.get("execution_count"))
    rows = _rows(proof.get("execution_rows"))

    present = {
        "NONEMPTY_SELECTED_PLAN": selected is not None and selected > 0,
        "NONEMPTY_VERIFIED_TARGET_EFFECT_SET": (
            target_count is not None and target_count > 0
        ),
        "CONTROLLER_CHECKPOINT_BOUND": (
            proof.get("controller_checkpoint_present") is True
        ),
        "EXECUTION_COUNT_MATCHES_SELECTED_PLAN_AND_NONZERO": (
            selected is not None
            and selected > 0
            and execution_count is not None
            and execution_count == selected
            and rows is not None
            and len(rows) == selected
        ),
        "ALL_EXECUTION_ROWS_PASS": (
            rows is not None
            and bool(rows)
            and all(row.get("pass") is True for row in rows)
        ),
        "COMPOSITION_DIGEST_PRESENT_FOR_EVERY_EXECUTION_ROW": (
            rows is not None
            and bool(rows)
            and all(row.get("composition_digest_present") is True for row in rows)
        ),
    }
    return [item for item in CHECKPOINT_OBLIGATIONS if not present[item]]


def _raw_missing(proof: Mapping[str, Any]) -> list[str]:
    obligation_count = _count(proof.get("raw_acceptance_obligation_count"))
    accepted_count = _count(proof.get("accepted_raw_obligation_id_count"))
    present = {
        "SEMANTIC_ACCEPTANCE_COMPLETE": (
            proof.get("semantic_acceptance_complete") is True
        ),
        "RAW_GOAL_DIGEST_BOUND": proof.get("raw_goal_digest_present") is True,
        "RAW_TASK_CONTRACT_DIGEST_BOUND": (
            proof.get("raw_task_contract_digest_present") is True
        ),
        "RAW_GOAL_ACCEPTANCE_BINDING_PRESENT": (
            proof.get("raw_goal_acceptance_present") is True
        ),
        "RAW_ACCEPTANCE_OBLIGATION_COUNT_POSITIVE": (
            obligation_count is not None and obligation_count > 0
        ),
        "ALL_RAW_ACCEPTANCE_OBLIGATIONS_ACCEPTED": (
            obligation_count is not None
            and obligation_count > 0
            and accepted_count is not None
            and accepted_count == obligation_count
        ),
    }
    return [item for item in RAW_OBLIGATIONS if not present[item]]


def _bundle(route: str, missing: list[str]) -> dict[str, Any]:
    return {
        "route": route,
        "missing_obligations": list(missing),
        "missing_obligation_count": len(missing),
        "completion_claim": (
            "STRUCTURAL_ROUTE_PREMISES_ONLY__DOWNSTREAM_INDEPENDENT_"
            "REAUTHENTICATION_AND_NORMAL_VERIFICATION_REMAIN_MANDATORY"
        ),
    }


def compile_request(context: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(context, Mapping):
        return _fail("AUTHOR_CONTEXT_NOT_OBJECT")
    if (
        context.get("schema")
        != "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_AUTHOR_CONTEXT_V1"
        or context.get("pass") is not True
    ):
        return _fail("AUTHOR_CONTEXT_NOT_AUTHENTICATED")

    expected_context_sha = author_context.context_sha256(context)
    if context.get("context_sha256") != expected_context_sha:
        return _fail(
            "AUTHOR_CONTEXT_DIGEST_MISMATCH",
            expected_context_sha256=expected_context_sha,
            observed_context_sha256=context.get("context_sha256"),
        )

    proof = context.get("proof")
    bindings = context.get("bindings")
    redaction = context.get("redaction_policy")
    if (
        not isinstance(proof, Mapping)
        or not isinstance(bindings, Mapping)
        or not isinstance(redaction, Mapping)
    ):
        return _fail("AUTHOR_CONTEXT_SHAPE_INVALID")
    if (
        proof.get("structural_view_complete") is not True
        or redaction.get("structural_coverage_complete") is not True
        or redaction.get("unmodeled_request_key_count") != 0
        or redaction.get("unmodeled_material_key_count") != 0
        or redaction.get("unmodeled_execution_key_count") != 0
    ):
        return _fail("STRUCTURAL_VIEW_INCOMPLETE__MINIMUM_REQUEST_UNPROVED")

    reduction = reducer.reduce_author_context(context)
    if reduction.get("pass") is not True:
        return _fail(
            "REPAIR_REDUCTION_FAILED",
            repair_class_reduction=deepcopy(dict(reduction)),
        )
    if (
        reduction.get("must_acquire_new_distinguishing_evidence") is not True
        or reduction.get("admissible_repair_classes")
        != [reducer.NEW_EVIDENCE]
    ):
        return _fail(
            "NEW_DISTINGUISHING_EVIDENCE_NOT_THE_ONLY_ADMISSIBLE_REPAIR_CLASS",
            repair_class_reduction=deepcopy(dict(reduction)),
        )

    checkpoint_missing = _checkpoint_missing(proof)
    raw_missing = _raw_missing(proof)
    candidates = [
        _bundle(CHECKPOINT_ROUTE, checkpoint_missing),
        _bundle(RAW_ROUTE, raw_missing),
    ]

    # A zero-missing route would contradict the reducer's evidence-only verdict.
    if any(row["missing_obligation_count"] == 0 for row in candidates):
        return _fail(
            "REDUCER_CONTRADICTION__COMPLETE_ROUTE_PRESENT",
            candidate_evidence_bundles=candidates,
            repair_class_reduction=deepcopy(dict(reduction)),
        )

    minimum = min(row["missing_obligation_count"] for row in candidates)
    minimal = [
        deepcopy(row)
        for row in candidates
        if row["missing_obligation_count"] == minimum
    ]

    base = {
        "schema": SCHEMA,
        "status": "PASS__MINIMUM_STRUCTURAL_DISTINGUISHING_EVIDENCE_REQUEST_READY",
        "pass": True,
        "request_kind": REQUEST_KIND,
        "author_context_sha256": expected_context_sha,
        "proof_capsule_sha256": bindings.get("proof_capsule_sha256"),
        "replay_capsule_sha256": bindings.get("replay_capsule_sha256"),
        "repair_class_reduction": {
            "schema": reduction.get("schema"),
            "status": reduction.get("status"),
            "retained_proof_class": reduction.get("retained_proof_class"),
            "admissible_repair_classes": deepcopy(
                list(reduction.get("admissible_repair_classes") or [])
            ),
            "must_acquire_new_distinguishing_evidence": True,
        },
        "candidate_evidence_bundles": minimal,
        "all_route_deltas": candidates,
        "minimum_missing_obligation_count": minimum,
        "minimum_semantics": (
            "MINIMUM_BY_MISSING_STRUCTURAL_OBLIGATION_COUNT_ONLY__NO_CLAIM_"
            "ABOUT_REAL_WORLD_ACQUISITION_COST_AVAILABILITY_OR_SEMANTIC_SUFFICIENCY"
        ),
        "provider_contract": {
            "provider_may_return_candidate_evidence_only": True,
            "provider_truth_authority": False,
            "provider_verification_authority": False,
            "provider_acceptance_authority": False,
            "provider_terminal_authority": False,
            "required_downstream_action": (
                "REINGEST_THROUGH_EXISTING_PROOF_CAPTURE_AND_INDEPENDENT_"
                "VERIFICATION_PIPELINE_THEN_RECOMPUTE_REPAIR_REDUCTION"
            ),
        },
        "acquisition_authority": False,
        "provider_truth_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    base["request_sha256"] = _digest(base)
    return base


def run(args: Mapping[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    return compile_request(args.get("author_context"))
