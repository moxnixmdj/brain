"""Fail-closed repair-class reducer for R3 verification-frontier gaps.

This module never creates verification evidence and grants no acquisition,
execution, verification, promotion, acceptance, or terminal authority.

It answers one narrower question from already-redacted retained proof shape:

Which repair classes remain even *structurally possible* without inventing
evidence that the current success record does not contain?

The reducer is intentionally conservative:
- a complete checkpointed verified execution shape may still be repaired by a
  verifier-preserving adapter or an independently verified read-only verifier;
- an independently accepted raw-success shape may also admit either route;
- status-only, digest-only, or partial evidence cannot soundly support either
  route, so only NEW_DISTINGUISHING_EVIDENCE remains.

Selection is not sufficiency. Every surviving route still requires its normal
independent verification and authority gates.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_R3_VERIFICATION_FRONTIER_REPAIR_REDUCER_V1"

ADAPTER = "VERIFIER_PRESERVING_SUCCESS_ADAPTER"
READONLY_VERIFIER = "INDEPENDENT_READONLY_SUCCESS_VERIFIER"
NEW_EVIDENCE = "NEW_DISTINGUISHING_EVIDENCE"
ALL_CLASSES = (ADAPTER, READONLY_VERIFIER, NEW_EVIDENCE)


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "admissible_repair_classes": [],
        "preferred_repair_order": [],
        "must_acquire_new_distinguishing_evidence": False,
        "candidate_selection_authority": False,
        "acquisition_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _execution_rows_complete(
    rows: Any,
    *,
    selected_plan_count: int,
) -> bool:
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes, bytearray))
        or selected_plan_count <= 0
        or len(rows) != selected_plan_count
    ):
        return False
    for row in rows:
        if not isinstance(row, Mapping):
            return False
        if row.get("pass") is not True:
            return False
        if row.get("composition_digest_present") is not True:
            return False
    return True


def reduce_author_context(
    author_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Reduce one redacted R3 gap context to structurally admissible repair classes."""
    if not isinstance(author_context, Mapping):
        return _fail("AUTHOR_CONTEXT_NOT_OBJECT")
    if author_context.get("pass") is not True:
        return _fail("AUTHOR_CONTEXT_NOT_AUTHENTICATED")
    if (
        author_context.get("schema")
        != "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_AUTHOR_CONTEXT_V1"
    ):
        return _fail("AUTHOR_CONTEXT_SCHEMA_INVALID")
    proof = author_context.get("proof")
    bindings = author_context.get("bindings")
    redaction = author_context.get("redaction_policy")
    if (
        not isinstance(proof, Mapping)
        or not isinstance(bindings, Mapping)
        or not isinstance(redaction, Mapping)
    ):
        return _fail("AUTHOR_CONTEXT_SHAPE_INVALID")
    if redaction.get("only_fixed_protocol_keys_and_sanitized_symbols_exposed") is not True:
        return _fail("AUTHOR_CONTEXT_REDACTION_POLICY_INVALID")
    if author_context.get("candidate_generation_authority") is not True:
        return _fail("AUTHOR_CONTEXT_CANDIDATE_GENERATION_NOT_AUTHORIZED")

    structural_view_complete = (
        proof.get("structural_view_complete") is True
        and redaction.get("structural_coverage_complete") is True
        and redaction.get("unmodeled_request_key_count") == 0
        and redaction.get("unmodeled_material_key_count") == 0
        and redaction.get("unmodeled_execution_key_count") == 0
    )

    selected_count = _int(proof.get("selected_plan_count")) or 0
    target_count = _int(proof.get("verified_target_effect_count")) or 0
    execution_count = _int(proof.get("execution_count")) or 0
    rows = proof.get("execution_rows")

    checkpointed_verified_execution = (
        selected_count > 0
        and target_count > 0
        and execution_count == selected_count
        and proof.get("controller_checkpoint_present") is True
        and _execution_rows_complete(rows, selected_plan_count=selected_count)
    )

    obligation_count = _int(proof.get("raw_acceptance_obligation_count"))
    accepted_count = _int(proof.get("accepted_raw_obligation_id_count")) or 0
    semantically_accepted_raw = (
        proof.get("semantic_acceptance_complete") is True
        and proof.get("raw_goal_digest_present") is True
        and proof.get("raw_task_contract_digest_present") is True
        and proof.get("raw_goal_acceptance_present") is True
        and isinstance(obligation_count, int)
        and obligation_count > 0
        and accepted_count == obligation_count
    )

    proof_capsule_bound = bool(bindings.get("proof_capsule_sha256"))
    replay_capsule_bound = bool(bindings.get("replay_capsule_sha256"))
    capsule_identity_bound = proof_capsule_bound and replay_capsule_bound

    if not structural_view_complete:
        retained_class = "REDACTED_VIEW_STRUCTURALLY_INCOMPLETE"
        admissible = [ADAPTER, READONLY_VERIFIER, NEW_EVIDENCE]
        order = [ADAPTER, READONLY_VERIFIER, NEW_EVIDENCE]
        evidence_required = False
        reason = (
            "UNMODELED_RETAINED_STRUCTURE_EXISTS__ABSENCE_FROM_THE_REDACTED_VIEW_"
            "CANNOT_PROVE_ABSENCE_FROM_THE_SUCCESS_RECORD__NO_REPAIR_CLASS_MAY_"
            "BE_ELIMINATED_FROM_INCOMPLETE_STRUCTURAL_COVERAGE"
        )
    elif checkpointed_verified_execution:
        retained_class = "CHECKPOINTED_VERIFIED_EXECUTION"
        admissible = [ADAPTER, READONLY_VERIFIER, NEW_EVIDENCE]
        order = [ADAPTER, READONLY_VERIFIER, NEW_EVIDENCE]
        evidence_required = False
        reason = (
            "RETAINED_VERIFIED_EXECUTION_STRUCTURE_CAN_SUPPORT_A_VERIFIER_"
            "PRESERVING_ADAPTER_OR_AN_INDEPENDENT_READONLY_VERIFIER__NEW_"
            "DISTINGUISHING_EVIDENCE_REMAINS_A_FALLBACK"
        )
    elif semantically_accepted_raw:
        retained_class = "SEMANTICALLY_ACCEPTED_RAW_SUCCESS"
        admissible = [ADAPTER, READONLY_VERIFIER, NEW_EVIDENCE]
        order = [ADAPTER, READONLY_VERIFIER, NEW_EVIDENCE]
        evidence_required = False
        reason = (
            "RETAINED_INDEPENDENT_ACCEPTANCE_STRUCTURE_CAN_SUPPORT_A_"
            "VERIFIER_PRESERVING_ADAPTER_OR_AN_INDEPENDENT_READONLY_VERIFIER__"
            "NEW_DISTINGUISHING_EVIDENCE_REMAINS_A_FALLBACK"
        )
    else:
        retained_class = "INSUFFICIENT_FOR_NONSELF_REFERENTIAL_VERIFICATION"
        admissible = [NEW_EVIDENCE]
        order = [NEW_EVIDENCE]
        evidence_required = True
        reason = (
            "CURRENT_RETAINED_PROOF_SHAPE_LACKS_A_COMPLETE_CHECKPOINTED_VERIFIED_"
            "EXECUTION_OR_COMPLETE_INDEPENDENT_RAW_ACCEPTANCE_SUBJECT__AN_ADAPTER_"
            "OR_NEW_VERIFIER_WOULD_HAVE_TO_INVENT_MISSING_SEMANTICS_OR_EVIDENCE"
        )

    return {
        "schema": SCHEMA,
        "status": "PASS__VERIFICATION_FRONTIER_REPAIR_CLASSES_REDUCED",
        "pass": True,
        "retained_proof_class": retained_class,
        "capsule_identity_bound": capsule_identity_bound,
        "structural_view_complete": structural_view_complete,
        "checkpointed_verified_execution": checkpointed_verified_execution,
        "semantically_accepted_raw_success": semantically_accepted_raw,
        "admissible_repair_classes": admissible,
        "preferred_repair_order": order,
        "must_acquire_new_distinguishing_evidence": evidence_required,
        "reason": reason,
        "selection_semantics": (
            "LEAST_AUTHORITY_SEARCH_ORDER_ONLY__NO_ROUTE_IS_DECLARED_SUFFICIENT_"
            "UNTIL_ITS_NORMAL_INDEPENDENT_VERIFICATION_GATES_PASS"
        ),
        "author_context_sha256": author_context.get("context_sha256"),
        "source_author_context": deepcopy({
            "schema": author_context.get("schema"),
            "context_sha256": author_context.get("context_sha256"),
        }),
        "candidate_selection_authority": True,
        "acquisition_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def reduce_gap(gap_result: Mapping[str, Any]) -> dict[str, Any]:
    """Reduce the exact gap witness emitted by r3_root1_adapter_gap_witness_v1."""
    if not isinstance(gap_result, Mapping) or gap_result.get("pass") is not True:
        return _fail("GAP_RESULT_NOT_AUTHENTICATED")
    if (
        gap_result.get("schema")
        != "PROJECT_BRAIN_R3_ROOT1_ADAPTER_GAP_WITNESS_V1"
    ):
        return _fail("GAP_RESULT_SCHEMA_INVALID")
    context = gap_result.get("adapter_author_context")
    return reduce_author_context(context if isinstance(context, Mapping) else {})


def run(args: Mapping[str, Any] | None = None) -> dict[str, Any]:
    args = args or {}
    if "gap_result" in args:
        return reduce_gap(args.get("gap_result"))
    return reduce_author_context(args.get("author_context"))
