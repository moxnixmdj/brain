"""Fail-closed transport of already-proved exact residual behaviors across family labels.

A proof belongs to a behavioral contract, not to an accounting label.  Transport
is allowed only when the source family has exactly one active residual contract,
the source family is currently accepted/owned, and the load-bearing proof is
scope-complete objective-ceiling/absolute-dominance evidence rather than finite
sample generalization.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

REGISTRY = "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
MANIFEST = "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json"

EXPECTED_BLOBS = {
    REGISTRY: "ee187f611a0e82b2de495ee377682f39bc31dd31",
    MANIFEST: "bcf12c8845e90e6bfdd689458586bdebd59824a3",
    "canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json": "981c8ac9b66ee7fccf5b531525849e29df9be483",
    "canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json": "913d171b3c855000d322e183b142b3200eeaf0a9",
    "canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json": "f44e2378cf00f86a59159cb9d8edb35f0a7c27f4",
    "canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json": "d04f2a8c5594d261158835db1cae3822411b6b23",
    "canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json": "955ac8f4bd0db2527bfbb465fc8252df6d916156",
}

RECOVERY = "canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json"
TOOL_ACCEPTANCE = "canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
TOOL_SCOPE = "canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
DELEGATION_ACCEPTANCE = "canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
DELEGATION_SCOPE = "canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"

TRANSPORTS = {
    "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001": {
        "source_family": "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
        "proof_kind": "recovery",
    },
    "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001": {
        "source_family": "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
        "proof_kind": "tool",
    },
    "TASK_TO_DELEGATION_GRAPH_001": {
        "source_family": "SUBAGENT_DELEGATION_AND_COORDINATION",
        "proof_kind": "delegation",
    },
}


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _load(root: Path, rel: str) -> tuple[dict[str, Any], str]:
    data = (root / rel).read_bytes()
    return json.loads(data.decode("utf-8")), git_blob_sha(data)


def load_documents(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    docs: dict[str, dict[str, Any]] = {}
    for rel, expected in EXPECTED_BLOBS.items():
        doc, actual = _load(root, rel)
        docs[rel] = doc
        if actual != expected:
            errors.append(f"BLOB_DRIFT:{rel}:{actual}:{expected}")
    return docs[REGISTRY], docs[MANIFEST], docs, errors


def _owned_family(manifest: dict[str, Any], family_id: str) -> bool:
    families = {f.get("id"): f for f in manifest.get("families", []) if isinstance(f, dict)}
    node = families.get(family_id)
    if not isinstance(node, dict):
        return False
    return (
        node.get("opus55_acceptance_state") == "PASS"
        and node.get("opus55_acceptance_calibrated") is True
        and node.get("ownership_status") == "VERIFIED_OWNED_EQUAL_OR_BETTER"
    )


def _proof_errors(kind: str, proofs: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if kind == "recovery":
        v = proofs[RECOVERY].get("verified", {})
        if v.get("scope_complete") is not True:
            errors.append("RECOVERY_SCOPE_NOT_COMPLETE")
        if v.get("objective_ceiling_or_floor") is not True:
            errors.append("RECOVERY_NOT_OBJECTIVE_CEILING_OR_FLOOR")
        if v.get("historical_relation_observed_bound_used_as_proof") is not False:
            errors.append("RECOVERY_HISTORICAL_EMPIRICAL_BOUND_LOAD_BEARING")
        if v.get("exact_opus_case_level_access_required") is not False:
            errors.append("RECOVERY_UNEXPECTED_OPUS_CASE_DEPENDENCY")
    elif kind == "tool":
        a = proofs[TOOL_ACCEPTANCE].get("verified", {})
        s = proofs[TOOL_SCOPE].get("verified", {})
        if a.get("proof_kind") != "ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS":
            errors.append("TOOL_PROOF_KIND_NOT_ABSOLUTE_UNIVERSAL")
        if a.get("scope_complete") is not True or a.get("objective_ceiling") is not True:
            errors.append("TOOL_ACCEPTANCE_NOT_SCOPE_COMPLETE_OBJECTIVE_CEILING")
        if a.get("uses_empirical_generalization") is not False:
            errors.append("TOOL_ACCEPTANCE_USES_EMPIRICAL_GENERALIZATION")
        if s.get("universal_scope_proved") is not True:
            errors.append("TOOL_UNIVERSAL_SCOPE_NOT_PROVED")
        if s.get("uses_empirical_generalization") is not False:
            errors.append("TOOL_SCOPE_USES_EMPIRICAL_GENERALIZATION")
    elif kind == "delegation":
        a = proofs[DELEGATION_ACCEPTANCE].get("verified_result", {})
        s = proofs[DELEGATION_SCOPE].get("verified", [])
        if a.get("closure_mode") != "ABSOLUTE_DOMINANCE":
            errors.append("DELEGATION_NOT_ABSOLUTE_DOMINANCE")
        if a.get("witness_reason") != "THEORETICAL_CEILING_DOMINANCE":
            errors.append("DELEGATION_NOT_THEORETICAL_CEILING")
        if a.get("scope_completeness_basis") != "UNIVERSAL_FORMAL_SCOPE_PROOF":
            errors.append("DELEGATION_SCOPE_BASIS_NOT_UNIVERSAL")
        if "UNIVERSAL_SCOPE_PROVED_TRUE" not in s:
            errors.append("DELEGATION_UNIVERSAL_SCOPE_NOT_PROVED")
        if "NO_EMPIRICAL_GENERALIZATION" not in s:
            errors.append("DELEGATION_EMPIRICAL_GENERALIZATION_NOT_EXCLUDED")
    else:
        errors.append("UNKNOWN_PROOF_KIND:" + kind)
    return errors


def validate_documents(
    registry: dict[str, Any],
    manifest: dict[str, Any],
    proofs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    if registry.get("schema") != "PROJECT_BRAIN_BEHAVIORAL_CONTRACT_REGISTRY_V1":
        errors.append("REGISTRY_SCHEMA")
    if manifest.get("schema") != "PROJECT_BRAIN_TERMINAL_CLOSURE_MANIFEST_V1":
        errors.append("MANIFEST_SCHEMA")

    family_map = registry.get("family_to_residual_contracts")
    if not isinstance(family_map, dict):
        return {"valid": False, "errors": ["FAMILY_MAP_MISSING"], "transports": {}}

    result: dict[str, list[str]] = {}
    for behavior_id, spec in TRANSPORTS.items():
        source = spec["source_family"]
        source_contracts = family_map.get(source)
        if source_contracts != [behavior_id]:
            errors.append(f"SOURCE_NOT_SINGLE_RESIDUAL:{source}:{behavior_id}")
        if not _owned_family(manifest, source):
            errors.append(f"SOURCE_NOT_CURRENTLY_OWNED:{source}")
        errors.extend(_proof_errors(spec["proof_kind"], proofs))

        target_families = sorted(
            family_id
            for family_id, contracts in family_map.items()
            if isinstance(contracts, list) and behavior_id in contracts
        )
        if source not in target_families:
            errors.append(f"SOURCE_MAPPING_MISSING:{source}:{behavior_id}")
        result[behavior_id] = target_families

    return {
        "schema": "PROJECT_BRAIN_CROSS_FAMILY_RESIDUAL_PROOF_TRANSPORT_DERIVATION_V1",
        "valid": not errors,
        "errors": sorted(set(errors)),
        "transports": result,
        "credit_rule": "IDENTICAL_RESIDUAL_ONLY__NO_TARGET_FAMILY_OR_PUBLIC_BAR_CREDIT",
    }


def derive(root: Path = ROOT) -> dict[str, Any]:
    registry, manifest, proofs, blob_errors = load_documents(root)
    out = validate_documents(registry, manifest, proofs)
    errors = sorted(set(blob_errors + out["errors"]))
    out["errors"] = errors
    out["valid"] = not errors
    out["exact_blob_binding"] = not blob_errors
    return out


if __name__ == "__main__":
    print(json.dumps(derive(), sort_keys=True, indent=2))
