from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_POST_BUILD_AUDIT_V1"
MANIFEST_SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_POST_BUILD_AUDIT_MANIFEST_V1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class PostBuildAuditError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _rows(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(x, Mapping) for x in value):
        raise PostBuildAuditError(label + "_INVALID")
    return value


def _id_map(rows: list[Mapping[str, Any]], key: str, label: str) -> dict[str, Mapping[str, Any]]:
    out = {}
    for row in rows:
        rid = row.get(key)
        if not isinstance(rid, str) or not rid.strip():
            raise PostBuildAuditError(label + "_ID_INVALID")
        rid = rid.strip()
        if rid in out:
            raise PostBuildAuditError(label + "_ID_DUPLICATE:" + rid)
        out[rid] = row
    return out


def _strings(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise PostBuildAuditError(label + "_INVALID")
    if not allow_empty and not value:
        raise PostBuildAuditError(label + "_EMPTY")
    if any(not isinstance(x, str) or not x.strip() for x in value):
        raise PostBuildAuditError(label + "_MEMBER_INVALID")
    out = [x.strip() for x in value]
    if len(out) != len(set(out)):
        raise PostBuildAuditError(label + "_DUPLICATE")
    return out


def _receipt(row: Mapping[str, Any], label: str) -> None:
    value = row.get("verification_receipt")
    if not isinstance(value, str) or not value.strip():
        raise PostBuildAuditError(label + "_VERIFICATION_RECEIPT_MISSING")


def verify_post_build_audit(
    pre_generation_verdict: Mapping[str, Any],
    contract: Mapping[str, Any],
    audit: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(pre_generation_verdict, Mapping):
        raise PostBuildAuditError("PRE_GENERATION_VERDICT_INVALID")
    if pre_generation_verdict.get("status") != "PASS__PRE_GENERATION_STRUCTURAL_CONTRACT_COMPLETE":
        raise PostBuildAuditError("PRE_GENERATION_NOT_PASSED")
    contract_sha = pre_generation_verdict.get("pre_generation_contract_sha256")
    if not isinstance(contract_sha, str) or not HEX64.fullmatch(contract_sha):
        raise PostBuildAuditError("PRE_GENERATION_CONTRACT_SHA_INVALID")

    if not isinstance(contract, Mapping) or contract.get("schema") != "PROJECT_BRAIN_AA_BRIEFCASE_PRE_GENERATION_CONTRACT_MANIFEST_V1":
        raise PostBuildAuditError("CONTRACT_INVALID")
    if not isinstance(audit, Mapping) or audit.get("schema") != MANIFEST_SCHEMA:
        raise PostBuildAuditError("AUDIT_SCHEMA_INVALID")
    if audit.get("pre_generation_contract_sha256") != contract_sha:
        raise PostBuildAuditError("AUDIT_PRE_GENERATION_BINDING_MISMATCH")

    requirement_by_id = _id_map(_rows(contract.get("requirements"), "CONTRACT_REQUIREMENTS"), "id", "CONTRACT_REQUIREMENT")
    dimension_by_id = _id_map(_rows(contract.get("dimensions"), "CONTRACT_DIMENSIONS"), "dimension_id", "CONTRACT_DIMENSION")
    convention_by_id = _id_map(_rows(contract.get("conventions"), "CONTRACT_CONVENTIONS"), "convention_id", "CONTRACT_CONVENTION")
    scenario_by_id = _id_map(_rows(contract.get("scenario_axes"), "CONTRACT_SCENARIOS"), "axis_id", "CONTRACT_SCENARIO")
    reconciliation_by_id = _id_map(_rows(contract.get("reconciliations"), "CONTRACT_RECONCILIATIONS"), "reconciliation_id", "CONTRACT_RECONCILIATION")
    output_by_id = _id_map(_rows(contract.get("outputs"), "CONTRACT_OUTPUTS"), "output_id", "CONTRACT_OUTPUT")
    authority_by_path = _id_map(_rows(contract.get("authority_sources"), "CONTRACT_AUTHORITY_SOURCES"), "source_path", "CONTRACT_SOURCE")

    deliverable_set = {row.get("deliverable_path") for row in output_by_id.values()}
    if None in deliverable_set:
        raise PostBuildAuditError("CONTRACT_DELIVERABLE_INVALID")

    artifacts = _id_map(_rows(audit.get("artifacts"), "ARTIFACTS"), "deliverable_path", "ARTIFACT")
    if set(artifacts) != deliverable_set:
        raise PostBuildAuditError("ARTIFACT_DELIVERABLE_SET_MISMATCH")
    for path, row in artifacts.items():
        digest = row.get("artifact_sha256")
        n = row.get("artifact_bytes")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            raise PostBuildAuditError("ARTIFACT_SHA_INVALID:" + path)
        if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
            raise PostBuildAuditError("ARTIFACT_SIZE_INVALID:" + path)
        if row.get("mechanical_integrity_verified") is not True:
            raise PostBuildAuditError("ARTIFACT_MECHANICAL_INTEGRITY_UNVERIFIED:" + path)
        _receipt(row, "ARTIFACT:" + path)

    req_results = _id_map(_rows(audit.get("requirement_results"), "REQUIREMENT_RESULTS"), "requirement_id", "REQUIREMENT_RESULT")
    if set(req_results) != set(requirement_by_id):
        raise PostBuildAuditError("REQUIREMENT_RESULT_SET_MISMATCH")
    for rid, row in req_results.items():
        if row.get("pass") is not True:
            raise PostBuildAuditError("REQUIREMENT_FAILED:" + rid)
        locations = _strings(row.get("artifact_locations"), "REQUIREMENT_LOCATIONS:" + rid)
        outputs = _strings(row.get("output_ids"), "REQUIREMENT_OUTPUTS:" + rid)
        if set(outputs) != set(requirement_by_id[rid].get("output_ids") or []):
            raise PostBuildAuditError("REQUIREMENT_OUTPUT_BINDING_MISMATCH:" + rid)
        _receipt(row, "REQUIREMENT:" + rid)

    dim_results = _id_map(_rows(audit.get("dimension_results"), "DIMENSION_RESULTS"), "dimension_id", "DIMENSION_RESULT")
    if set(dim_results) != set(dimension_by_id):
        raise PostBuildAuditError("DIMENSION_RESULT_SET_MISMATCH")
    for did, row in dim_results.items():
        if row.get("pass") is not True:
            raise PostBuildAuditError("DIMENSION_FAILED:" + did)
        _strings(row.get("artifact_locations"), "DIMENSION_LOCATIONS:" + did)
        _receipt(row, "DIMENSION:" + did)

    conv_results = _id_map(_rows(audit.get("convention_results"), "CONVENTION_RESULTS"), "convention_id", "CONVENTION_RESULT")
    if set(conv_results) != set(convention_by_id):
        raise PostBuildAuditError("CONVENTION_RESULT_SET_MISMATCH")
    for cid, row in conv_results.items():
        if row.get("pass") is not True:
            raise PostBuildAuditError("CONVENTION_FAILED:" + cid)
        if row.get("effective_source_path") != convention_by_id[cid].get("effective_source_path"):
            raise PostBuildAuditError("CONVENTION_EFFECTIVE_SOURCE_MISMATCH:" + cid)
        _strings(row.get("artifact_locations"), "CONVENTION_LOCATIONS:" + cid)
        _receipt(row, "CONVENTION:" + cid)

    scenario_results = _id_map(_rows(audit.get("scenario_results"), "SCENARIO_RESULTS"), "axis_id", "SCENARIO_RESULT")
    if set(scenario_results) != set(scenario_by_id):
        raise PostBuildAuditError("SCENARIO_RESULT_SET_MISMATCH")
    for aid, row in scenario_results.items():
        if row.get("pass") is not True:
            raise PostBuildAuditError("SCENARIO_FAILED:" + aid)
        expected_states = set(scenario_by_id[aid].get("states") or [])
        realized = set(_strings(row.get("realized_states"), "SCENARIO_REALIZED_STATES:" + aid))
        if realized != expected_states:
            raise PostBuildAuditError("SCENARIO_STATE_COVERAGE_MISMATCH:" + aid)
        rationales = row.get("state_rationales")
        if not isinstance(rationales, Mapping) or set(rationales) != expected_states:
            raise PostBuildAuditError("SCENARIO_RATIONALE_SET_MISMATCH:" + aid)
        if any(not isinstance(v, str) or not v.strip() for v in rationales.values()):
            raise PostBuildAuditError("SCENARIO_RATIONALE_EMPTY:" + aid)
        _strings(row.get("artifact_locations"), "SCENARIO_LOCATIONS:" + aid)
        _receipt(row, "SCENARIO:" + aid)

    recon_results = _id_map(_rows(audit.get("reconciliation_results"), "RECONCILIATION_RESULTS"), "reconciliation_id", "RECONCILIATION_RESULT")
    if set(recon_results) != set(reconciliation_by_id):
        raise PostBuildAuditError("RECONCILIATION_RESULT_SET_MISMATCH")
    for xid, row in recon_results.items():
        if row.get("pass") is not True:
            raise PostBuildAuditError("RECONCILIATION_FAILED:" + xid)
        expected_methods = set(reconciliation_by_id[xid].get("method_ids") or [])
        methods = set(_strings(row.get("method_ids"), "RECONCILIATION_METHODS:" + xid))
        if methods != expected_methods:
            raise PostBuildAuditError("RECONCILIATION_METHOD_SET_MISMATCH:" + xid)
        if row.get("variance_explained") is not True:
            raise PostBuildAuditError("RECONCILIATION_VARIANCE_UNEXPLAINED:" + xid)
        if row.get("output_id") != reconciliation_by_id[xid].get("output_id"):
            raise PostBuildAuditError("RECONCILIATION_OUTPUT_MISMATCH:" + xid)
        _strings(row.get("artifact_locations"), "RECONCILIATION_LOCATIONS:" + xid)
        _receipt(row, "RECONCILIATION:" + xid)

    trace_results = _id_map(_rows(audit.get("source_traceability"), "SOURCE_TRACEABILITY"), "source_path", "SOURCE_TRACE")
    if set(trace_results) != set(authority_by_path):
        raise PostBuildAuditError("SOURCE_TRACE_SET_MISMATCH")
    for path, row in trace_results.items():
        if row.get("source_sha256") != authority_by_path[path].get("content_sha256"):
            raise PostBuildAuditError("SOURCE_TRACE_HASH_MISMATCH:" + path)
        if row.get("provenance_recorded") is not True:
            raise PostBuildAuditError("SOURCE_PROVENANCE_NOT_RECORDED:" + path)
        _strings(row.get("artifact_locations"), "SOURCE_TRACE_LOCATIONS:" + path)
        _receipt(row, "SOURCE_TRACE:" + path)

    if audit.get("formula_or_structural_error_scan_pass") is not True:
        raise PostBuildAuditError("FORMULA_OR_STRUCTURAL_ERROR_SCAN_FAILED")
    if audit.get("all_declared_outputs_reopened_after_write") is not True:
        raise PostBuildAuditError("OUTPUT_REOPEN_VERIFICATION_MISSING")
    if audit.get("freeze_after_audit") is not True:
        raise PostBuildAuditError("OUTPUT_NOT_FROZEN_AFTER_AUDIT")

    material = {
        "schema": SCHEMA,
        "status": "PASS__AA_PROFESSIONAL_DELIVERABLE_POST_BUILD_AUDIT",
        "pre_generation_contract_sha256": contract_sha,
        "artifact_count": len(artifacts),
        "requirement_count": len(req_results),
        "dimension_count": len(dim_results),
        "convention_count": len(conv_results),
        "scenario_axis_count": len(scenario_results),
        "reconciliation_count": len(recon_results),
        "source_trace_count": len(trace_results),
        "all_requirements_verified_in_artifact": True,
        "all_dimensions_verified_in_artifact": True,
        "all_conventions_verified_in_artifact": True,
        "all_scenario_states_and_rationales_verified": True,
        "all_reconciliations_verified": True,
        "all_sources_traceable_in_artifact": True,
        "mechanical_integrity_verified": True,
        "pre_freeze_audit_complete": True,
        "professional_quality_relative_to_opus_proved": False,
        "official_aa_acceptance_claimed": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    return {**material, "post_build_audit_sha256": _sha(_canon(material))}
