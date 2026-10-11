from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_CREDIT_SUBJECT_GATE_V1"
SUBJECT_SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_CREDIT_SUBJECT_V1"

_ALLOWED_SOLVER_ROLES = {
    "BRAIN_OWNED_NATIVE_MECHANISM",
    "BRAIN_OWNED_DERIVED_MECHANISM",
}


class ChartographyCreditSubjectError(ValueError):
    pass


def _zero_int(subject: Mapping[str, Any], key: str) -> None:
    value = subject.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value != 0:
        raise ChartographyCreditSubjectError(key.upper() + "_MUST_EQUAL_ZERO")


def admit_brain_credit_subject(subject: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed on any producer-path model cognition.

    This gate is an attribution/ownership gate only. Passing it grants no
    Chartography score or benchmark credit by itself.
    """
    required = {
        "schema",
        "repository",
        "operative_solver_role",
        "brain_owned_operative_artifact",
        "cognition_dependency_class",
        "producer_cognition_provenance_complete",
        "runtime_dependency_inventory_complete",
        "model_dependency_count",
        "external_model_runtime_dependency_count",
        "donor_runtime_dependency_count",
        "online_teacher_call_count",
        "teacher_fallback_path_count",
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
        "model_dependency_count",
        "external_model_runtime_dependency_count",
        "donor_runtime_dependency_count",
        "online_teacher_call_count",
        "teacher_fallback_path_count",
    ):
        _zero_int(subject, key)

    acquisition_donor_used = subject.get("acquisition_donor_used")
    if type(acquisition_donor_used) is not bool:
        raise ChartographyCreditSubjectError("ACQUISITION_DONOR_USED_MUST_BE_BOOL")

    if acquisition_donor_used:
        if subject.get("operative_solver_role") != "BRAIN_OWNED_DERIVED_MECHANISM":
            raise ChartographyCreditSubjectError("DONOR_DERIVED_SOLVER_ROLE_REQUIRED")
        if subject.get("qualification_after_donor_removal") is not True:
            raise ChartographyCreditSubjectError("POST_DONOR_REMOVAL_QUALIFICATION_REQUIRED")
        if subject.get("student_or_derived_artifact_distinct_from_donor") is not True:
            raise ChartographyCreditSubjectError("DERIVED_ARTIFACT_MUST_BE_DISTINCT_FROM_DONOR")
    else:
        if subject.get("qualification_after_donor_removal") is not True:
            raise ChartographyCreditSubjectError("QUALIFICATION_ISOLATION_ATTESTATION_REQUIRED")
        if subject.get("student_or_derived_artifact_distinct_from_donor") is not True:
            raise ChartographyCreditSubjectError("OPERATIVE_ARTIFACT_IDENTITY_ATTESTATION_REQUIRED")

    return {
        "schema": SCHEMA,
        "status": "PASS__BRAIN_CREDIT_SUBJECT_ATTRIBUTION_ONLY",
        "brain_credit_subject_admissible": True,
        "cognition_dependency_class": "MODEL_INDEPENDENT",
        "model_dependency_count": 0,
        "external_model_runtime_dependency_count": 0,
        "donor_runtime_dependency_count": 0,
        "benchmark_score_proved": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }
