"""Fail-closed three-way proof router for Tool Discovery.

Consumes independently verified, exact-byte-bound program soundness, exact
common Brain/Opus tool-identity authority, and an independently verified
Observability Partition V2 result. It routes exactly one region:
universal proof, safe observation, or irreducible matched comparator.

Scheduling only. Grants no acceptance, capability, family, execution, or
promotion credit.
"""
from __future__ import annotations
import hashlib
import json
import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_PROOF_ROUTER_V2"
PARTITION_SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_OBSERVABILITY_PARTITION_V2"

def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def _sha(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canon(value)).hexdigest()

def _fail(*failures: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "failures": sorted(set(failures)),
        "acceptance_proved": False,
        "terminal_results_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }

def _policy_version(value: Any) -> int | None:
    m = re.fullmatch(r"V(\d+)", str(value or ""))
    return int(m.group(1)) if m else None

def route(
    *,
    policy_receipt: Mapping[str, Any],
    identity_scope_receipt: Mapping[str, Any],
    partition_result: Mapping[str, Any],
    partition_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []

    if policy_receipt.get("independent_verified") is not True:
        failures.append("POLICY_NOT_INDEPENDENTLY_VERIFIED")
    if policy_receipt.get("exact_byte_bound") is not True:
        failures.append("POLICY_NOT_EXACT_BYTE_BOUND")
    if policy_receipt.get("program_soundness_verified") is not True:
        failures.append("PROGRAM_SOUNDNESS_NOT_VERIFIED")
    version = _policy_version(policy_receipt.get("policy_version"))
    if version is None or version < 6:
        failures.append("POLICY_NOT_V6_OR_SUCCESSOR")

    if identity_scope_receipt.get("independent_verified") is not True:
        failures.append("IDENTITY_SCOPE_NOT_INDEPENDENTLY_VERIFIED")
    if identity_scope_receipt.get("identity_scope_complete") is not True:
        failures.append("IDENTITY_SCOPE_NOT_COMPLETE")
    if identity_scope_receipt.get("scope_relation") != "EXACT":
        failures.append("IDENTITY_SCOPE_RELATION_NOT_EXACT")
    if identity_scope_receipt.get("common_brain_opus_authority") is not True:
        failures.append("COMMON_BRAIN_OPUS_AUTHORITY_NOT_VERIFIED")

    if partition_receipt.get("independent_verified") is not True:
        failures.append("PARTITION_NOT_INDEPENDENTLY_VERIFIED")
    if partition_receipt.get("partition_version") != "V2":
        failures.append("PARTITION_NOT_V2")
    if partition_receipt.get("minimum_reality_partition_verified") is not True:
        failures.append("MINIMUM_REALITY_PARTITION_NOT_VERIFIED")
    if str(partition_receipt.get("partition_result_sha256") or "") != _sha(partition_result):
        failures.append("PARTITION_RECEIPT_RESULT_DIGEST_MISMATCH")

    if partition_result.get("schema") != PARTITION_SCHEMA:
        failures.append("PARTITION_RESULT_SCHEMA_NOT_V2")
    if partition_result.get("identity_scope_complete") is not True:
        failures.append("PARTITION_IDENTITY_PRECONDITION_NOT_MET")

    if failures:
        return _fail(*failures)

    universal = partition_result.get("universal_proof_eligible") is True
    safe = partition_result.get("safe_progress_available") is True
    matched = partition_result.get("matched_comparator_required_now") is True
    if sum((universal, safe, matched)) != 1:
        return _fail("PARTITION_NOT_EXACTLY_ONE_OF_THREE_REGIONS")

    action = str(partition_result.get("minimum_reality_action") or "")
    status = str(partition_result.get("status") or "")

    common = {
        "schema": SCHEMA,
        "policy_version": f"V{version}",
        "identity_scope_relation": "EXACT_COMMON_BRAIN_OPUS_AUTHORITY",
        "partition_result_sha256": _sha(partition_result),
        "acceptance_proved": False,
        "terminal_results_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }

    if universal:
        if action != "UNIVERSAL_PROOF" or not status.startswith("UNIVERSAL_PROOF_ELIGIBLE"):
            return _fail("UNIVERSAL_REGION_ACTION_OR_STATUS_MISMATCH")
        if partition_result.get("recommended_safe_probe") not in (None, {}):
            return _fail("UNIVERSAL_REGION_CARRIES_SAFE_PROBE")
        return {
            **common,
            "status": "UNIVERSAL_REGION__FORMAL_PROGRAM_PROOF_ONLY",
            "next_required_fact": "FORMAL_V6_OR_SUCCESSOR_CORRECTNESS_OVER_THIS_OBSERVABILITY_CLOSED_COMMON_AUTHORITY_PARTITION",
            "matched_comparator_allowed_now": False,
            "safe_observation_required_now": False,
        }

    if safe:
        if action != "SAFE_PROBE" or not status.startswith("SAFE_PROGRESS_REQUIRED"):
            return _fail("SAFE_REGION_ACTION_OR_STATUS_MISMATCH")
        probe = partition_result.get("recommended_safe_probe")
        if not isinstance(probe, Mapping):
            return _fail("SAFE_REGION_WITHOUT_PROBE")
        tool_id = str(probe.get("tool_id") or "")
        capability = str(probe.get("capability") or "")
        if not tool_id or not capability:
            return _fail("SAFE_REGION_PROBE_INCOMPLETE")
        return {
            **common,
            "status": "SAFE_OBSERVATION_REQUIRED__MATCHED_EVIDENCE_FORBIDDEN_YET",
            "next_required_fact": "INDEPENDENT_CURRENT_EPOCH_SAFE_PROBE_RECEIPT_FOR_THE_CHEAPEST_DECISION_FRONTIER",
            "recommended_safe_probe": {"tool_id": tool_id, "capability": capability},
            "matched_comparator_allowed_now": False,
            "safe_observation_required_now": True,
        }

    if action != "MATCHED_COMPARATOR" or not status.startswith("MATCHED_COMPARATOR_REQUIRED"):
        return _fail("MATCHED_REGION_ACTION_OR_STATUS_MISMATCH")
    irreducible = partition_result.get("irreducible_routes")
    if not isinstance(irreducible, list) or not irreducible:
        return _fail("MATCHED_REGION_WITHOUT_IRREDUCIBILITY_WITNESS")
    if partition_result.get("recommended_safe_probe") not in (None, {}):
        return _fail("MATCHED_REGION_STILL_CARRIES_SAFE_PROBE")
    return {
        **common,
        "status": "MATCHED_ONLY_RESIDUAL__SAFE_OBSERVATION_CLOSED",
        "next_required_fact": "MATCHED_OPUS_EVIDENCE_ONLY_FOR_THE_IRREDUCIBLE_CHEAPEST_DECISION_FRONTIER",
        "irreducible_route_count": len(irreducible),
        "matched_comparator_allowed_now": True,
        "safe_observation_required_now": False,
    }
