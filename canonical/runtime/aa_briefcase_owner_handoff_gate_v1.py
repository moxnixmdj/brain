from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping
from urllib.parse import urlparse

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_OWNER_HANDOFF_GATE_V1"
OWNER_DECISION_SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_OWNER_EXECUTION_DECISION_V1"
AUTHORITY_SCHEMA = "PROJECT_BRAIN_EXTERNAL_RESULT_AUTHORITY_RECEIPT_V1"
SUBJECT_SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_FROZEN_EVALUATION_SUBJECT_V1"
CARRIER_SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_CALLABLE_CARRIER_MANIFEST_V1"

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

ALLOWED_ROUTES = {
    "INDEPENDENT_OFFICIAL_CUSTOM_AGENT_HTTP",
    "INDEPENDENT_OFFICIAL_OWNER_RUNS_PACKAGE",
    "INDEPENDENT_OFFICIAL_FULL_STIRRUP_CONFIGURATION",
}
ALLOWED_COMPARABILITY = {
    "EXACT_FROZEN_2026_09_22_RATING_EPOCH",
    "DIRECT_MATCHED_FROZEN_OPUS55_COMPARISON",
    "OWNER_VERIFIED_CROSS_EPOCH_TRANSFORM",
}


class HandoffError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return bool(_SHA256.fullmatch(str(value or "")))


def _valid_sha40(value: Any) -> bool:
    return bool(_SHA40.fullmatch(str(value or "")))


def _aa_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname in {"artificialanalysis.ai", "www.artificialanalysis.ai"}
    )


def _authority_ok(
    authority: Mapping[str, Any],
    *,
    statement_sha256: str,
    evidence_sha256: str,
) -> bool:
    required = {
        "schema",
        "verified",
        "source_kind",
        "verifier_id",
        "statement_sha256",
        "evidence_sha256",
        "verification_authority_mutated",
        "auth_method",
        "auth_artifact_sha256",
        "receipt_sha256",
    }
    if not isinstance(authority, Mapping) or set(authority) != required:
        return False
    if authority.get("schema") != AUTHORITY_SCHEMA:
        return False
    if authority.get("verified") is not True:
        return False
    if authority.get("source_kind") != "OWNER_EVALUATOR":
        return False
    if authority.get("verification_authority_mutated") is not False:
        return False
    if authority.get("auth_method") not in {
        "OWNER_PUBLISHED_RESULT",
        "VERIFIED_DIGITAL_SIGNATURE",
    }:
        return False
    if authority.get("statement_sha256") != statement_sha256:
        return False
    if authority.get("evidence_sha256") != evidence_sha256:
        return False
    if not _valid_sha256(authority.get("auth_artifact_sha256")):
        return False
    if not _valid_sha256(authority.get("receipt_sha256")):
        return False
    verifier_id = str(authority.get("verifier_id") or "").strip()
    if not verifier_id or verifier_id in {"BRAIN", "SELF", "SUBJECT"}:
        return False
    payload = {
        str(k): v
        for k, v in authority.items()
        if str(k) != "receipt_sha256"
    }
    return authority["receipt_sha256"] == _sha(payload)


def adjudicate_owner_decision(
    decision: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "schema",
        "status",
        "benchmark",
        "benchmark_version",
        "official_private_scope",
        "independent_no_fee_coverage",
        "full_agent_execution_supported",
        "integration_route",
        "interface_contract_sha256",
        "interface_contract_uri",
        "comparability_route",
        "comparability_evidence_sha256",
        "comparability_evidence_uri",
        "owner_evidence_sha256",
        "owner_source_uri",
    }
    if not isinstance(decision, Mapping) or set(decision) != required:
        raise HandoffError("OWNER_DECISION_FIELDS_INVALID")
    if (
        decision.get("schema") != OWNER_DECISION_SCHEMA
        or decision.get("status") != "OWNER_CONFIRMED"
    ):
        raise HandoffError("OWNER_DECISION_STATUS_INVALID")
    if (
        decision.get("benchmark") != "AA-Briefcase"
        or decision.get("benchmark_version") != "1.1"
    ):
        raise HandoffError("OWNER_DECISION_TARGET_MISMATCH")
    if decision.get("official_private_scope") is not True:
        raise HandoffError("OFFICIAL_PRIVATE_SCOPE_NOT_CONFIRMED")
    if decision.get("independent_no_fee_coverage") is not True:
        raise HandoffError("NO_FEE_OFFICIAL_COVERAGE_NOT_CONFIRMED")
    if decision.get("full_agent_execution_supported") is not True:
        raise HandoffError("FULL_AGENT_EXECUTION_NOT_CONFIRMED")

    route = decision.get("integration_route")
    if route not in ALLOWED_ROUTES:
        raise HandoffError("INTEGRATION_ROUTE_INVALID")

    for key in (
        "interface_contract_sha256",
        "comparability_evidence_sha256",
        "owner_evidence_sha256",
    ):
        if not _valid_sha256(decision.get(key)):
            raise HandoffError(key.upper() + "_INVALID")

    if not _aa_url(str(decision.get("interface_contract_uri") or "")):
        raise HandoffError("INTERFACE_CONTRACT_URI_INVALID")
    if decision.get("comparability_route") not in ALLOWED_COMPARABILITY:
        raise HandoffError("COMPARABILITY_ROUTE_INVALID")
    if not _aa_url(str(decision.get("comparability_evidence_uri") or "")):
        raise HandoffError("COMPARABILITY_EVIDENCE_URI_INVALID")
    if not _aa_url(str(decision.get("owner_source_uri") or "")):
        raise HandoffError("OWNER_SOURCE_URI_INVALID")

    evidence_sha256 = str(decision["owner_evidence_sha256"])
    statement_sha256 = _sha({
        "claim": "AA_BRIEFCASE_OFFICIAL_ZERO_FEE_FULL_AGENT_HANDOFF_CONFIRMED",
        "benchmark": "AA-Briefcase",
        "benchmark_version": "1.1",
        "official_private_scope": True,
        "independent_no_fee_coverage": True,
        "full_agent_execution_supported": True,
        "integration_route": route,
        "interface_contract_sha256": decision["interface_contract_sha256"],
        "comparability_route": decision["comparability_route"],
        "comparability_evidence_sha256": decision[
            "comparability_evidence_sha256"
        ],
        "owner_evidence_sha256": evidence_sha256,
    })
    if not _authority_ok(
        authority,
        statement_sha256=statement_sha256,
        evidence_sha256=evidence_sha256,
    ):
        raise HandoffError("OWNER_AUTHORITY_RECEIPT_INVALID")

    material = {
        "schema": SCHEMA,
        "status": "READY_TO_FREEZE_CALLABLE_SUBJECT",
        "pass": True,
        "integration_route": route,
        "interface_contract_sha256": decision["interface_contract_sha256"],
        "comparability_route": decision["comparability_route"],
        "comparability_evidence_sha256": decision[
            "comparability_evidence_sha256"
        ],
        "owner_evidence_sha256": evidence_sha256,
        "owner_authority_receipt_sha256": authority["receipt_sha256"],
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }
    return {**material, "handoff_verdict_sha256": _sha(material)}


def freeze_subject(
    handoff_verdict: Mapping[str, Any],
    carrier: Mapping[str, Any],
    *,
    repository_commit_sha: str,
    execution_profile_git_blob_sha: str,
    configuration_git_blob_sha: str,
    stirrup_root_tree_sha: str,
) -> dict[str, Any]:
    if (
        handoff_verdict.get("schema") != SCHEMA
        or handoff_verdict.get("status") != "READY_TO_FREEZE_CALLABLE_SUBJECT"
        or handoff_verdict.get("pass") is not True
    ):
        raise HandoffError("HANDOFF_NOT_READY")

    required_carrier = {
        "schema",
        "carrier_kind",
        "zero_incremental_spend",
        "official_interface_contract_sha256",
        "carrier_artifact_sha256",
        "cognition_substrate_sha256",
        "tool_surface_sha256",
        "state_policy_sha256",
        "endpoint_or_package_locator_sha256",
    }
    if not isinstance(carrier, Mapping) or set(carrier) != required_carrier:
        raise HandoffError("CARRIER_FIELDS_INVALID")
    if carrier.get("schema") != CARRIER_SCHEMA:
        raise HandoffError("CARRIER_SCHEMA_INVALID")
    if carrier.get("carrier_kind") not in {
        "HTTPS_FULL_AGENT_ENDPOINT",
        "OWNER_RUNNABLE_PACKAGE",
        "FULL_STIRRUP_CONFIGURATION",
    }:
        raise HandoffError("CARRIER_KIND_INVALID")
    if carrier.get("zero_incremental_spend") is not True:
        raise HandoffError("CARRIER_ZERO_SPEND_NOT_PROVED")
    if carrier.get("official_interface_contract_sha256") != handoff_verdict.get(
        "interface_contract_sha256"
    ):
        raise HandoffError("CARRIER_INTERFACE_CONTRACT_MISMATCH")

    for key in (
        "carrier_artifact_sha256",
        "cognition_substrate_sha256",
        "tool_surface_sha256",
        "state_policy_sha256",
        "endpoint_or_package_locator_sha256",
    ):
        if not _valid_sha256(carrier.get(key)):
            raise HandoffError(key.upper() + "_INVALID")

    for label, value in (
        ("REPOSITORY_COMMIT", repository_commit_sha),
        ("EXECUTION_PROFILE_BLOB", execution_profile_git_blob_sha),
        ("CONFIGURATION_BLOB", configuration_git_blob_sha),
        ("STIRRUP_ROOT_TREE", stirrup_root_tree_sha),
    ):
        if not _valid_sha40(value):
            raise HandoffError(label + "_INVALID")

    execution_bundle = {
        "repository": "moxnixmdj/brain",
        "git_commit_sha": repository_commit_sha,
        "execution_profile_git_blob_sha": execution_profile_git_blob_sha,
        "configuration_git_blob_sha": configuration_git_blob_sha,
        "stirrup_root_tree_sha": stirrup_root_tree_sha,
        "carrier_manifest": dict(carrier),
        "handoff_verdict_sha256": handoff_verdict["handoff_verdict_sha256"],
        "comparability_route": handoff_verdict["comparability_route"],
        "comparability_evidence_sha256": handoff_verdict[
            "comparability_evidence_sha256"
        ],
    }
    subject = {
        "schema": SUBJECT_SCHEMA,
        "repository": "moxnixmdj/brain",
        "git_commit_sha": repository_commit_sha,
        "execution_profile_git_blob_sha": execution_profile_git_blob_sha,
        "configuration_git_blob_sha": configuration_git_blob_sha,
        "execution_bundle_sha256": _sha(execution_bundle),
    }
    return {
        "schema": "PROJECT_BRAIN_AA_BRIEFCASE_FROZEN_SUBJECT_COMPILER_V1",
        "status": "FROZEN_CALLABLE_SUBJECT",
        "subject": subject,
        "subject_sha256": _sha(subject),
        "execution_bundle": execution_bundle,
        "execution_bundle_sha256": subject["execution_bundle_sha256"],
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }
