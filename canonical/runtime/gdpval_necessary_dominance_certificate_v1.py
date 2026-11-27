from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "PROJECT_BRAIN_GDPVAL_NECESSARY_DOMINANCE_CERTIFICATE_V1"
EXPECTED_EVALUATION = "GDPval-AA v2.1"
EXPECTED_TASK_COUNT = 220
ALLOWED_MODES = {"DIRECT_DOMINANCE", "TOP_CERTIFICATE", "HYBRID"}


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNRESOLVED",
        "reason": reason,
        "hidden_owner_relation_required": True,
        "certificate_structurally_complete": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    out.update(extra)
    return out


def _nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_evidence_list(value: Any) -> bool:
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes))
        and len(value) > 0
        and all(_nonempty_str(x) for x in value)
    )


def _validate_owner_contract(owner: Mapping[str, Any]) -> tuple[bool, str | None]:
    if owner.get("evaluation") != EXPECTED_EVALUATION:
        return False, "OWNER_EVALUATION_MISMATCH"
    if owner.get("task_count") != EXPECTED_TASK_COUNT:
        return False, "OWNER_TASK_COUNT_MISMATCH"
    if owner.get("blind_pairwise") is not True:
        return False, "OWNER_BLIND_PAIRWISE_NOT_BOUND"
    if owner.get("same_task_for_both_submissions") is not True:
        return False, "OWNER_SAME_TASK_NOT_BOUND"
    if owner.get("same_reference_files_for_both_submissions") is not True:
        return False, "OWNER_SAME_REFERENCES_NOT_BOUND"
    if owner.get("anonymized_submission_order") is not True:
        return False, "OWNER_ANONYMIZATION_NOT_BOUND"
    if owner.get("judge_context_includes_initial_task") is not True:
        return False, "OWNER_INITIAL_TASK_CONTEXT_NOT_BOUND"
    if owner.get("judge_context_includes_all_reference_files") is not True:
        return False, "OWNER_ALL_REFERENCE_FILES_CONTEXT_NOT_BOUND"
    if owner.get("judge_context_includes_all_submission_files") is not True:
        return False, "OWNER_ALL_SUBMISSION_FILES_CONTEXT_NOT_BOUND"
    if owner.get("document_files_parsed_as_text_and_images") is not True:
        return False, "OWNER_DOCUMENT_PRESENTATION_NOT_BOUND"
    if owner.get("grading_question_semantics") != "WHICH_SUBMISSION_BETTER_RESPONDS_TO_THE_TASK":
        return False, "OWNER_GRADING_QUESTION_SEMANTICS_NOT_BOUND"
    if not _valid_evidence_list(owner.get("evidence_refs")):
        return False, "OWNER_CONTRACT_EVIDENCE_MISSING"
    return True, None


def _validate_envelope(envelope: Mapping[str, Any]) -> tuple[bool, str | None]:
    if envelope.get("status") != "PROVED_SOUND_OVERAPPROXIMATION":
        return False, "OWNER_COMPATIBLE_ENVELOPE_NOT_PROVED"
    if envelope.get("contains_true_owner_relation") is not True:
        return False, "TRUE_OWNER_RELATION_CONTAINMENT_NOT_PROVED"
    if envelope.get("monotone_task_response_order") is not True:
        return False, "MONOTONE_TASK_RESPONSE_ORDER_NOT_PROVED"
    if not _valid_evidence_list(envelope.get("proof_receipts")):
        return False, "ENVELOPE_PROOF_RECEIPTS_MISSING"
    if not _valid_evidence_list(envelope.get("falsifier_classes")):
        return False, "ENVELOPE_FALSIFIERS_MISSING"
    return True, None


def _validate_dimension(dimension: Mapping[str, Any], task_id: str) -> tuple[bool, str | None]:
    dim_id = dimension.get("dimension_id")
    if not _nonempty_str(dim_id):
        return False, f"TASK_{task_id}__DIMENSION_ID_INVALID"
    relation = dimension.get("relation")
    if relation not in {"BRAIN_BETTER", "TIE", "TOP"}:
        return False, f"TASK_{task_id}__DIMENSION_{dim_id}__RELATION_NOT_CERTIFIED"
    if not _valid_evidence_list(dimension.get("evidence_refs")):
        return False, f"TASK_{task_id}__DIMENSION_{dim_id}__EVIDENCE_MISSING"
    if relation == "TOP":
        if dimension.get("upper_bound_proved") is not True:
            return False, f"TASK_{task_id}__DIMENSION_{dim_id}__TOP_BOUND_NOT_PROVED"
        if dimension.get("brain_attains_upper_bound") is not True:
            return False, f"TASK_{task_id}__DIMENSION_{dim_id}__TOP_NOT_ATTAINED"
    return True, None


def _validate_task(task: Mapping[str, Any]) -> tuple[bool, str | None]:
    task_id = task.get("task_id")
    if not _nonempty_str(task_id):
        return False, "TASK_ID_INVALID"
    if task.get("mode") not in ALLOWED_MODES:
        return False, f"TASK_{task_id}__MODE_INVALID"
    if task.get("owner_compatible_counterexample_exists") is True:
        return False, f"TASK_{task_id}__OWNER_COMPATIBLE_OPUS_WIN_COUNTEREXAMPLE"
    if task.get("owner_compatible_counterexample_search_complete") is not True:
        return False, f"TASK_{task_id}__COUNTEREXAMPLE_SEARCH_OPEN"
    if not _valid_evidence_list(task.get("counterexample_search_receipts")):
        return False, f"TASK_{task_id}__COUNTEREXAMPLE_SEARCH_RECEIPTS_MISSING"

    dimensions = task.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        return False, f"TASK_{task_id}__NO_CERTIFIED_DIMENSIONS"
    seen: set[str] = set()
    for dimension in dimensions:
        if not isinstance(dimension, Mapping):
            return False, f"TASK_{task_id}__DIMENSION_INVALID"
        dim_id = dimension.get("dimension_id")
        if dim_id in seen:
            return False, f"TASK_{task_id}__DUPLICATE_DIMENSION_{dim_id}"
        seen.add(dim_id)
        ok, reason = _validate_dimension(dimension, task_id)
        if not ok:
            return False, reason

    if task.get("dimension_basis_scope_complete") is not True:
        return False, f"TASK_{task_id}__DIMENSION_BASIS_NOT_SCOPE_COMPLETE"
    if not _valid_evidence_list(task.get("basis_completeness_receipts")):
        return False, f"TASK_{task_id}__BASIS_COMPLETENESS_RECEIPTS_MISSING"
    if task.get("necessary_preference_proved") is not True:
        return False, f"TASK_{task_id}__NECESSARY_PREFERENCE_NOT_PROVED"
    return True, None


def verify_certificate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_INVALID")
    if payload.get("schema") != SCHEMA:
        return _fail("SCHEMA_MISMATCH")

    owner = payload.get("owner_contract")
    if not isinstance(owner, Mapping):
        return _fail("OWNER_CONTRACT_MISSING")
    ok, reason = _validate_owner_contract(owner)
    if not ok:
        return _fail(reason or "OWNER_CONTRACT_INVALID")

    envelope = payload.get("owner_compatible_preference_envelope")
    if not isinstance(envelope, Mapping):
        return _fail("OWNER_COMPATIBLE_ENVELOPE_MISSING")
    ok, reason = _validate_envelope(envelope)
    if not ok:
        return _fail(reason or "OWNER_COMPATIBLE_ENVELOPE_INVALID")

    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        return _fail("TASKS_INVALID")
    if len(tasks) != EXPECTED_TASK_COUNT:
        return _fail("TASK_POPULATION_NOT_220", observed_task_count=len(tasks))

    seen: set[str] = set()
    for task in tasks:
        if not isinstance(task, Mapping):
            return _fail("TASK_RECORD_INVALID")
        task_id = task.get("task_id")
        if task_id in seen:
            return _fail("DUPLICATE_TASK_ID", task_id=task_id)
        seen.add(task_id)
        ok, reason = _validate_task(task)
        if not ok:
            return _fail(reason or "TASK_CERTIFICATE_INVALID", task_id=task_id)

    independent = payload.get("independent_verification")
    if not isinstance(independent, Mapping):
        return _fail("INDEPENDENT_VERIFICATION_MISSING")
    if independent.get("status") != "PASS":
        return _fail("INDEPENDENT_VERIFICATION_NOT_PASS")
    if not _valid_evidence_list(independent.get("receipts")):
        return _fail("INDEPENDENT_VERIFICATION_RECEIPTS_MISSING")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "STRUCTURALLY_COMPLETE_NECESSARY_DOMINANCE_CERTIFICATE",
        "task_count": EXPECTED_TASK_COUNT,
        "hidden_owner_relation_required": False,
        "exact_owner_prompt_required": False,
        "complete_owner_pairwise_graph_required": False,
        "exact_crowd_bt_reconstruction_required": False,
        "certificate_structurally_complete": True,
        "logical_consequence": (
            "IF_THE_BOUND_OWNER_COMPATIBLE_ENVELOPE_SOUNDLY_CONTAINS_THE_TRUE_OWNER_RELATION_"
            "AND_EVERY_TASK_HAS_A_SCOPE_COMPLETE_NECESSARY_PREFERENCE_CERTIFICATE_"
            "THEN_THE_TRUE_OWNER_RELATION_CANNOT_PREFER_OPUS55_ON_ANY_BOUND_TASK"
        ),
        "promotion_boundary": (
            "THIS_RUNTIME_VALIDATES_CERTIFICATE_STRUCTURE_AND_REQUIRED_RECEIPTS; "
            "IT DOES_NOT SELF-AUTHENTICATE THE_SEMANTIC_TRUTH_OF_THOSE_RECEIPTS"
        ),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
