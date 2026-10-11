from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_SCOPE_COMPLETE_DOMINANCE_V1"
CERT_SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_SCOPE_COMPLETE_DOMINANCE_CERTIFICATE_V1"
TARGET_SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_OPUS55_CURRENT_OWNER_TARGET_V1"
EXPECTED_BENCHMARK = "AA-Briefcase v1.1"
EXPECTED_MODEL = "Claude Opus 5.5 (Max, Default Fallback)"
EXPECTED_TASK_COUNT = 91
EXPECTED_GRADING_PROTOCOL_BLOB_SHA = "5c77f294e09d4933e3a3175c46af225b414f4702"

ROUTES = {
    "E_EXPLICIT_COMPLETE",
    "M_HIDDEN_RESTRICTED_MONOTONE",
    "U_DIRECT_TARGET_RELATION",
}
ALLOWED_DIRECT_OUTCOMES = {"BRAIN_WIN", "TIE"}


class DominanceCertificateError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _hex64(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise DominanceCertificateError(label + "_INVALID")
    return value


def canonical_set_sha256(values: Sequence[str]) -> str:
    normalized = sorted(set(values))
    if len(normalized) != len(values):
        raise DominanceCertificateError("SET_HAS_DUPLICATES")
    if not normalized or any(not isinstance(x, str) or not x for x in normalized):
        raise DominanceCertificateError("SET_MEMBER_INVALID")
    return _sha256(normalized)


def _validate_target(current_target: Mapping[str, Any]) -> tuple[str, float]:
    if not isinstance(current_target, Mapping):
        raise DominanceCertificateError("TARGET_INVALID")
    if current_target.get("schema") != TARGET_SCHEMA:
        raise DominanceCertificateError("TARGET_SCHEMA_MISMATCH")
    target = current_target.get("target")
    epoch_rule = current_target.get("epoch_rule")
    if not isinstance(target, Mapping) or not isinstance(epoch_rule, Mapping):
        raise DominanceCertificateError("TARGET_BINDING_MISSING")
    if target.get("benchmark") != EXPECTED_BENCHMARK:
        raise DominanceCertificateError("TARGET_BENCHMARK_MISMATCH")
    if target.get("model") != EXPECTED_MODEL:
        raise DominanceCertificateError("TARGET_MODEL_MISMATCH")
    observed_date = target.get("observed_date")
    if not isinstance(observed_date, str) or not observed_date:
        raise DominanceCertificateError("TARGET_OBSERVED_DATE_INVALID")
    reference = target.get("current_owner_elo")
    epoch_reference = epoch_rule.get("current_epoch_minimum_opus55_target_elo")
    if isinstance(reference, bool) or not isinstance(reference, (int, float)):
        raise DominanceCertificateError("TARGET_REFERENCE_INVALID")
    if isinstance(epoch_reference, bool) or not isinstance(epoch_reference, (int, float)):
        raise DominanceCertificateError("TARGET_EPOCH_REFERENCE_INVALID")
    if float(reference) != float(epoch_reference):
        raise DominanceCertificateError("TARGET_EPOCH_REFERENCE_DRIFT")
    return observed_date, float(reference)


def _receipt_sha(row: Mapping[str, Any], key: str) -> str:
    return _hex64(row.get(key), key.upper())


def _verify_check(row: Mapping[str, Any]) -> str:
    if not isinstance(row, Mapping):
        raise DominanceCertificateError("CHECK_NOT_OBJECT")
    check_id = row.get("check_id")
    task_id = row.get("task_id")
    route = row.get("route")
    if not isinstance(check_id, str) or not check_id:
        raise DominanceCertificateError("CHECK_ID_INVALID")
    if not isinstance(task_id, str) or not task_id:
        raise DominanceCertificateError("TASK_ID_INVALID")
    if route not in ROUTES:
        raise DominanceCertificateError("CHECK_ROUTE_INVALID:" + check_id)
    if row.get("load_bearing") is not True:
        raise DominanceCertificateError("CHECK_NOT_LOAD_BEARING:" + check_id)

    if route == "E_EXPLICIT_COMPLETE":
        _receipt_sha(row, "semantic_receipt_sha256")
        if row.get("complete_semantics_verified") is not True:
            raise DominanceCertificateError("E_SEMANTICS_NOT_COMPLETE:" + check_id)
        if row.get("brain_at_objective_top") is not True:
            raise DominanceCertificateError("E_BRAIN_NOT_AT_TOP:" + check_id)

    elif route == "M_HIDDEN_RESTRICTED_MONOTONE":
        _receipt_sha(row, "semantic_receipt_sha256")
        if row.get("monotone_class_complete_verified") is not True:
            raise DominanceCertificateError("M_CLASS_NOT_COMPLETE:" + check_id)
        mode = row.get("dominance_mode")
        if mode not in {"UNIVERSAL_TOP_SUPPORT", "MATCHED_MONOTONE_DOMINANCE"}:
            raise DominanceCertificateError("M_DOMINANCE_MODE_INVALID:" + check_id)
        if row.get("brain_noninferior") is not True:
            raise DominanceCertificateError("M_NONINFERIORITY_NOT_PROVED:" + check_id)
        if mode == "MATCHED_MONOTONE_DOMINANCE":
            _receipt_sha(row, "target_relation_receipt_sha256")

    elif route == "U_DIRECT_TARGET_RELATION":
        _receipt_sha(row, "target_relation_receipt_sha256")
        relation_kind = row.get("relation_kind")
        assignment_coverage = row.get("assignment_coverage")
        if assignment_coverage not in {"ACTUAL_OWNER_ASSIGNMENT", "ALL_BOUND_PANEL_JUDGES"}:
            raise DominanceCertificateError("U_ASSIGNMENT_COVERAGE_INVALID:" + check_id)

        if relation_kind == "PAIRWISE_PREFERENCE":
            if row.get("judge_panel_class") != "PAIRWISE_PANEL":
                raise DominanceCertificateError("U_PAIRWISE_PANEL_MISMATCH:" + check_id)
            if row.get("matched_pairwise_semantics_verified") is not True:
                raise DominanceCertificateError("U_PAIRWISE_SEMANTICS_UNVERIFIED:" + check_id)
            if assignment_coverage == "ACTUAL_OWNER_ASSIGNMENT":
                if row.get("owner_assignment_verified") is not True:
                    raise DominanceCertificateError("U_OWNER_ASSIGNMENT_UNVERIFIED:" + check_id)
                if row.get("outcome") not in ALLOWED_DIRECT_OUTCOMES:
                    raise DominanceCertificateError("U_OPUS_WIN_OR_INVALID:" + check_id)
            else:
                if row.get("panel_complete_verified") is not True:
                    raise DominanceCertificateError("U_PANEL_COMPLETENESS_UNVERIFIED:" + check_id)
                outcomes = row.get("panel_outcomes")
                if not isinstance(outcomes, list) or len(outcomes) != 3:
                    raise DominanceCertificateError("U_PAIRWISE_PANEL_OUTCOME_COUNT_INVALID:" + check_id)
                if any(outcome not in ALLOWED_DIRECT_OUTCOMES for outcome in outcomes):
                    raise DominanceCertificateError("U_OPUS_WIN_OR_INVALID:" + check_id)

        elif relation_kind == "BINARY_RUBRIC":
            if row.get("judge_panel_class") != "RUBRIC_PANEL":
                raise DominanceCertificateError("U_RUBRIC_PANEL_MISMATCH:" + check_id)
            if row.get("matched_rubric_semantics_verified") is not True:
                raise DominanceCertificateError("U_RUBRIC_SEMANTICS_UNVERIFIED:" + check_id)
            if assignment_coverage == "ACTUAL_OWNER_ASSIGNMENT":
                if row.get("owner_assignment_verified") is not True:
                    raise DominanceCertificateError("U_OWNER_ASSIGNMENT_UNVERIFIED:" + check_id)
                brain_pass = row.get("brain_pass")
                opus_pass = row.get("opus_pass")
                if not isinstance(brain_pass, bool) or not isinstance(opus_pass, bool):
                    raise DominanceCertificateError("U_RUBRIC_BITS_INVALID:" + check_id)
                if opus_pass and not brain_pass:
                    raise DominanceCertificateError("U_RUBRIC_OPUS_STRICTLY_BETTER:" + check_id)
            else:
                if row.get("panel_complete_verified") is not True:
                    raise DominanceCertificateError("U_PANEL_COMPLETENESS_UNVERIFIED:" + check_id)
                bits = row.get("panel_rubric_bits")
                if not isinstance(bits, list) or len(bits) != 3:
                    raise DominanceCertificateError("U_RUBRIC_PANEL_BIT_COUNT_INVALID:" + check_id)
                for pair in bits:
                    if not isinstance(pair, Mapping):
                        raise DominanceCertificateError("U_RUBRIC_PANEL_BITS_INVALID:" + check_id)
                    brain_pass = pair.get("brain_pass")
                    opus_pass = pair.get("opus_pass")
                    if not isinstance(brain_pass, bool) or not isinstance(opus_pass, bool):
                        raise DominanceCertificateError("U_RUBRIC_PANEL_BITS_INVALID:" + check_id)
                    if opus_pass and not brain_pass:
                        raise DominanceCertificateError("U_RUBRIC_OPUS_STRICTLY_BETTER:" + check_id)
        else:
            raise DominanceCertificateError("U_RELATION_KIND_INVALID:" + check_id)

    return route


def verify_scope_complete_dominance(
    current_target: Mapping[str, Any],
    certificate: Mapping[str, Any],
) -> dict[str, Any]:
    observed_date, reference = _validate_target(current_target)

    if not isinstance(certificate, Mapping):
        raise DominanceCertificateError("CERTIFICATE_INVALID")
    if certificate.get("schema") != CERT_SCHEMA:
        raise DominanceCertificateError("CERTIFICATE_SCHEMA_MISMATCH")
    if certificate.get("status") != "VERIFIED_SCOPE_COMPLETE_DOMINANCE":
        raise DominanceCertificateError("CERTIFICATE_STATUS_INVALID")
    if certificate.get("independent_or_owner_verified") is not True:
        raise DominanceCertificateError("CERTIFICATE_NOT_INDEPENDENT_OR_OWNER_VERIFIED")
    if certificate.get("benchmark") != EXPECTED_BENCHMARK:
        raise DominanceCertificateError("CERTIFICATE_BENCHMARK_MISMATCH")
    if certificate.get("model") != EXPECTED_MODEL:
        raise DominanceCertificateError("CERTIFICATE_MODEL_MISMATCH")
    if certificate.get("matched_current_owner_epoch") is not True:
        raise DominanceCertificateError("CERTIFICATE_EPOCH_NOT_MATCHED")
    if certificate.get("target_observed_date") != observed_date:
        raise DominanceCertificateError("CERTIFICATE_TARGET_DATE_MISMATCH")

    _hex64(certificate.get("subject_sha256"), "SUBJECT_SHA256")
    _hex64(certificate.get("opus_reference_subject_sha256"), "OPUS_REFERENCE_SUBJECT_SHA256")
    _hex64(certificate.get("private_task_population_sha256"), "PRIVATE_TASK_POPULATION_SHA256")
    _hex64(certificate.get("scope_manifest_sha256"), "SCOPE_MANIFEST_SHA256")
    _hex64(certificate.get("verification_receipt_sha256"), "VERIFICATION_RECEIPT_SHA256")
    if certificate.get("grading_protocol_manifest_git_blob_sha") != EXPECTED_GRADING_PROTOCOL_BLOB_SHA:
        raise DominanceCertificateError("GRADING_PROTOCOL_MANIFEST_DRIFT")

    task_count = certificate.get("task_count")
    if task_count != EXPECTED_TASK_COUNT:
        raise DominanceCertificateError("TASK_COUNT_MISMATCH")

    expected_check_count = certificate.get("expected_check_count")
    if isinstance(expected_check_count, bool) or not isinstance(expected_check_count, int) or expected_check_count < EXPECTED_TASK_COUNT:
        raise DominanceCertificateError("EXPECTED_CHECK_COUNT_INVALID")

    checks = certificate.get("checks")
    if not isinstance(checks, list) or len(checks) != expected_check_count:
        raise DominanceCertificateError("CHECK_POPULATION_COUNT_MISMATCH")

    ids: list[str] = []
    task_ids: list[str] = []
    route_counts: Counter[str] = Counter()
    for row in checks:
        route = _verify_check(row)
        ids.append(row["check_id"])
        task_ids.append(row["task_id"])
        route_counts[route] += 1

    if len(set(ids)) != len(ids):
        raise DominanceCertificateError("DUPLICATE_CHECK_ID")
    unique_task_ids = sorted(set(task_ids))
    if len(unique_task_ids) != EXPECTED_TASK_COUNT:
        raise DominanceCertificateError("TASK_COVERAGE_NOT_91_UNIQUE_TASKS")

    if canonical_set_sha256(ids) != certificate.get("check_id_set_sha256"):
        raise DominanceCertificateError("CHECK_ID_SET_ROOT_MISMATCH")
    if canonical_set_sha256(unique_task_ids) != certificate.get("task_id_set_sha256"):
        raise DominanceCertificateError("TASK_ID_SET_ROOT_MISMATCH")

    if certificate.get("scope_manifest_attests_complete_private_population") is not True:
        raise DominanceCertificateError("PRIVATE_SCOPE_COMPLETENESS_NOT_ATTESTED")
    if certificate.get("no_omitted_load_bearing_checks") is not True:
        raise DominanceCertificateError("LOAD_BEARING_CHECK_OMISSION_NOT_EXCLUDED")

    material = {
        "schema": SCHEMA,
        "status": "PASS_SCOPE_COMPLETE_CURRENT_EPOCH_DOMINANCE",
        "benchmark": EXPECTED_BENCHMARK,
        "target_model": EXPECTED_MODEL,
        "target_observed_date": observed_date,
        "current_owner_reference_elo_context_only": reference,
        "task_count": EXPECTED_TASK_COUNT,
        "check_count": expected_check_count,
        "route_counts": dict(sorted(route_counts.items())),
        "subject_sha256": certificate["subject_sha256"],
        "opus_reference_subject_sha256": certificate["opus_reference_subject_sha256"],
        "private_task_population_sha256": certificate["private_task_population_sha256"],
        "scope_manifest_sha256": certificate["scope_manifest_sha256"],
        "check_id_set_sha256": certificate["check_id_set_sha256"],
        "task_id_set_sha256": certificate["task_id_set_sha256"],
        "verification_receipt_sha256": certificate["verification_receipt_sha256"],
        "grading_protocol_manifest_git_blob_sha": certificate["grading_protocol_manifest_git_blob_sha"],
        "brain_weakly_dominates_current_opus55_on_every_load_bearing_check": True,
        "numeric_elo_reconstruction_required": False,
        "official_owner_elo_claimed": False,
        "historical_1822_epoch_rewritten": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
    }
    return {**material, "verdict_sha256": _sha256(material)}
