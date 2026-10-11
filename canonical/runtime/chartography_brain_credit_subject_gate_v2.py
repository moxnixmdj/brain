from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_CREDIT_SUBJECT_GATE_V2"
SUBJECT_SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_CREDIT_SUBJECT_V2"

_ALLOWED_SOLVER_ROLES = {
    "BRAIN_OWNED_NATIVE_MECHANISM",
    "BRAIN_OWNED_DERIVED_MECHANISM",
}

_ALLOWED_BOUNDED_LEARNED_COMPONENTS = {
    "image.extract.ocr.tesseract.positioned.tsv": {
        "classification": "VERIFIED_BRAIN_OWNED_BOUNDED_COMPONENT",
        "verification_path": "canonical/verification/M1A_POSITIONED_OCR_TSV_BRIDGE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
        "dependency_accounting_path": "canonical/governance/TESSERACT_OCR_DEPENDENCY_ACCOUNTING_V1.json",
        "donor_runtime_required": False,
        "external_frontier_model_required": False,
    },
}


class ChartographyCreditSubjectError(ValueError):
    pass


def _zero_int(subject: Mapping[str, Any], key: str) -> None:
    value = subject.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value != 0:
        raise ChartographyCreditSubjectError(key.upper() + "_MUST_EQUAL_ZERO")


def _validate_bounded_components(subject: Mapping[str, Any]) -> list[str]:
    if subject.get("bounded_learned_component_provenance_complete") is not True:
        raise ChartographyCreditSubjectError(
            "BOUNDED_LEARNED_COMPONENT_PROVENANCE_INCOMPLETE"
        )
    rows = subject.get("bounded_learned_components")
    if not isinstance(rows, list):
        raise ChartographyCreditSubjectError("BOUNDED_LEARNED_COMPONENTS_MUST_BE_LIST")

    ids: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ChartographyCreditSubjectError("BOUNDED_LEARNED_COMPONENT_ROW_INVALID")
        required = {
            "capability_id",
            "classification",
            "verification_path",
            "dependency_accounting_path",
            "donor_runtime_required",
            "external_frontier_model_required",
        }
        if set(row) != required:
            raise ChartographyCreditSubjectError("BOUNDED_LEARNED_COMPONENT_FIELDS_INVALID")
        cid = str(row.get("capability_id") or "")
        expected = _ALLOWED_BOUNDED_LEARNED_COMPONENTS.get(cid)
        if expected is None:
            raise ChartographyCreditSubjectError(
                "BOUNDED_LEARNED_COMPONENT_NOT_ALLOWLISTED:" + cid
            )
        for key, value in expected.items():
            if row.get(key) != value:
                raise ChartographyCreditSubjectError(
                    "BOUNDED_LEARNED_COMPONENT_PROVENANCE_MISMATCH:" + cid + ":" + key
                )
        ids.append(cid)
    if len(ids) != len(set(ids)):
        raise ChartographyCreditSubjectError("BOUNDED_LEARNED_COMPONENT_DUPLICATE")
    return sorted(ids)


def admit_brain_credit_subject(subject: Mapping[str, Any]) -> dict[str, Any]:
    """Enforce model-independent Brain cognition with explicit narrow sensors.

    General-purpose producer cognition must have zero model dependencies.
    Narrow, non-semantic learned components may appear only when they are
    explicitly allowlisted as independently verified Brain-owned bounded
    components with exact dependency/provenance records.

    Passing this gate grants attribution candidacy only, never a benchmark score.
    """
    required = {
        "schema",
        "repository",
        "operative_solver_role",
        "brain_owned_operative_artifact",
        "cognition_dependency_class",
        "producer_cognition_provenance_complete",
        "runtime_dependency_inventory_complete",
        "general_purpose_model_dependency_count",
        "external_general_purpose_model_runtime_dependency_count",
        "donor_general_purpose_model_runtime_dependency_count",
        "online_teacher_call_count",
        "teacher_fallback_path_count",
        "bounded_learned_components",
        "bounded_learned_component_provenance_complete",
        "acquisition_donor_used",
        "qualification_after_donor_removal",
        "student_or_derived_artifact_distinct_from_donor",
    }
    if not isinstance(subject, Mapping) or set(subject) != required:
        raise ChartographyCreditSubjectError("SUBJECT_FIELDS_INVALID")
    if subject.get("schema") != SUBJECT_SCHEMA:
        raise ChartographyCreditSubjectError("SUBJECT_SCHEMA_MISMATCH")
    if subject.get("repository") != "moxnixmdj/brain":
        raise ChartographyCreditSubjectError("SUBJECT_REPOSITORY_MISMATCH")
    if subject.get("operative_solver_role") not in _ALLOWED_SOLVER_ROLES:
        raise ChartographyCreditSubjectError("OPERATIVE_SOLVER_NOT_BRAIN_OWNED")
    if subject.get("brain_owned_operative_artifact") is not True:
        raise ChartographyCreditSubjectError("BRAIN_OWNED_OPERATIVE_ARTIFACT_REQUIRED")
    if subject.get("cognition_dependency_class") != "MODEL_INDEPENDENT":
        raise ChartographyCreditSubjectError("COGNITION_MUST_BE_MODEL_INDEPENDENT")
    if subject.get("producer_cognition_provenance_complete") is not True:
        raise ChartographyCreditSubjectError("PRODUCER_COGNITION_PROVENANCE_INCOMPLETE")
    if subject.get("runtime_dependency_inventory_complete") is not True:
        raise ChartographyCreditSubjectError("RUNTIME_DEPENDENCY_INVENTORY_INCOMPLETE")

    for key in (
        "general_purpose_model_dependency_count",
        "external_general_purpose_model_runtime_dependency_count",
        "donor_general_purpose_model_runtime_dependency_count",
        "online_teacher_call_count",
        "teacher_fallback_path_count",
    ):
        _zero_int(subject, key)

    bounded_ids = _validate_bounded_components(subject)

    acquisition_donor_used = subject.get("acquisition_donor_used")
    if type(acquisition_donor_used) is not bool:
        raise ChartographyCreditSubjectError("ACQUISITION_DONOR_USED_MUST_BE_BOOL")
    if subject.get("qualification_after_donor_removal") is not True:
        raise ChartographyCreditSubjectError("QUALIFICATION_AFTER_DONOR_REMOVAL_REQUIRED")
    if subject.get("student_or_derived_artifact_distinct_from_donor") is not True:
        raise ChartographyCreditSubjectError("OPERATIVE_ARTIFACT_IDENTITY_ATTESTATION_REQUIRED")

    if acquisition_donor_used and subject.get("operative_solver_role") != "BRAIN_OWNED_DERIVED_MECHANISM":
        raise ChartographyCreditSubjectError("DONOR_DERIVED_SOLVER_ROLE_REQUIRED")

    return {
        "schema": SCHEMA,
        "status": "PASS__BRAIN_CREDIT_SUBJECT_ATTRIBUTION_ONLY",
        "brain_credit_subject_admissible": True,
        "cognition_dependency_class": "MODEL_INDEPENDENT",
        "model_dependency_count": 0,
        "general_purpose_model_dependency_count": 0,
        "external_general_purpose_model_runtime_dependency_count": 0,
        "donor_general_purpose_model_runtime_dependency_count": 0,
        "bounded_learned_component_count": len(bounded_ids),
        "bounded_learned_component_ids": bounded_ids,
        "benchmark_score_proved": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }
