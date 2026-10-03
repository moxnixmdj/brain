#!/usr/bin/env python3
"""Mandatory retrieval-authority gate for live Tool Discovery scheduling.

This gate makes the verified residual-witness retrieval authority a mechanical
precondition of every live action targeting TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR.

It is intentionally fail closed:
- the exact Tool Discovery action must bind the active V2 retrieval activation;
- the activation and its independent receipt must match exact git blob SHAs;
- the residual compiler, backend router, and GitHub provider must match the
  independently verified bytes;
- V1 and the consumed GitHub source epoch must remain disabled;
- no search result may be interpreted as nonexistence or acceptance credit.

The gate grants no acceptance, family, capability, execution, or promotion credit.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_RETRIEVAL_AUTHORITY_GATE_V1"
TARGET = "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
ACTION_ID = "BUILD_TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE"

EXPECTED = {
    "activation_path": "canonical/governance/TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V2_ACTIVATION_V1.json",
    "activation_blob": "c916c095cfb52b4b3d8dd863dfb0be0f05529f2e",
    "activation_verification_path": "canonical/verification/TOOL_DISCOVERY_RETRIEVAL_FRONTIER_V2_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "activation_verification_blob": "bbbd34e192aa65ba94c4bda19a1a1eb9c2b5b406",
    "compiler_path": "canonical/runtime/residual_witness_retrieval_compiler_v1.py",
    "compiler_blob": "9daa8d590f3356b3fc51eccf75c56cbf515239e4",
    "compiler_verification_path": "canonical/verification/RESIDUAL_WITNESS_RETRIEVAL_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "compiler_verification_blob": "f0a68c8219d704875535543060f63b9ecaca6dd5",
    "router_path": "canonical/runtime/residual_witness_backend_router_v1.py",
    "router_blob": "578c5f87901a458b12d7df984e0a6a525d367456",
    "github_provider_path": "canonical/runtime/github_public_retrieval_provider_v1.py",
    "github_provider_blob": "29b808935559382ab7ddc81aaa08fe0611a05df8",
    "backend_verification_path": "canonical/verification/GITHUB_PUBLIC_RETRIEVAL_SURFACES_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "backend_verification_blob": "ca5acd7afbf14b7cce568ec482c160c3795e57ba",
}


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "target_predicate": TARGET,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def validate(
    hypergraph: Mapping[str, Any],
    activation: Mapping[str, Any],
    activation_verification: Mapping[str, Any],
    compiler_verification: Mapping[str, Any],
    backend_verification: Mapping[str, Any],
    actual_blobs: Mapping[str, str],
) -> dict[str, Any]:
    errors: list[str] = []

    actions = hypergraph.get("actions")
    if not isinstance(actions, list):
        return _fail("HYPERGRAPH_ACTIONS_NOT_LIST")

    target_actions = [
        x for x in actions
        if isinstance(x, Mapping) and TARGET in (x.get("target_predicates") or [])
    ]
    if len(target_actions) != 1:
        errors.append(f"TOOL_DISCOVERY_TARGET_ACTION_COUNT_NE_1:{len(target_actions)}")
        action = {}
    else:
        action = target_actions[0]

    if action.get("id") != ACTION_ID:
        errors.append("TOOL_DISCOVERY_ACTION_ID_MISMATCH")

    binding = action.get("mandatory_retrieval_authority")
    if not isinstance(binding, Mapping):
        errors.append("MANDATORY_RETRIEVAL_AUTHORITY_MISSING")
        binding = {}

    for key, expected in EXPECTED.items():
        if binding.get(key) != expected:
            errors.append(f"AUTHORITY_BINDING_MISMATCH:{key}")
        if key.endswith("_blob") and actual_blobs.get(key) != expected:
            errors.append(f"ACTUAL_BLOB_MISMATCH:{key}")

    if activation.get("schema") != "PROJECT_BRAIN_TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V2_ACTIVATION_V1":
        errors.append("ACTIVATION_SCHEMA_INVALID")
    if not str(activation.get("status") or "").startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("ACTIVATION_NOT_ACTIVE_INDEPENDENT_PASS")
    policy = activation.get("operational_policy")
    if not isinstance(policy, Mapping):
        errors.append("ACTIVATION_POLICY_MISSING")
    else:
        if policy.get("repeat_v1_source_epoch") is not False:
            errors.append("V1_SOURCE_EPOCH_REPLAY_NOT_DISABLED")
        if policy.get("repeat_v2_github_source_epoch") is not False:
            errors.append("V2_GITHUB_SOURCE_EPOCH_REPLAY_NOT_DISABLED")
        if policy.get("current_state") != "UNKNOWN_SCOPE_RELATION__STRICT_ACCEPTANCE_OPEN":
            errors.append("ACTIVATION_UNKNOWN_STATE_NOT_PRESERVED")

    if activation_verification.get("schema") != "PROJECT_BRAIN_TOOL_DISCOVERY_RETRIEVAL_FRONTIER_V2_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1":
        errors.append("ACTIVATION_VERIFICATION_SCHEMA_INVALID")
    runner = activation_verification.get("independent_runner")
    if not isinstance(runner, Mapping) or runner.get("conclusion") != "success":
        errors.append("ACTIVATION_INDEPENDENT_RUNNER_NOT_SUCCESS")
    verified = activation_verification.get("verified")
    if not isinstance(verified, Mapping):
        errors.append("ACTIVATION_VERIFIED_BLOCK_MISSING")
    else:
        for field in (
            "exact_activation_blob_verified",
            "exact_frontier_binding_verified",
            "exact_frontier_verification_binding_verified",
            "unknown_scope_relation_preserved",
            "v1_source_epoch_repeat_disabled",
            "v2_github_source_epoch_repeat_disabled",
            "zero_credit_preserved",
        ):
            if verified.get(field) is not True:
                errors.append("ACTIVATION_VERIFICATION_FALSE:" + field)

    if compiler_verification.get("schema") != "PROJECT_BRAIN_RESIDUAL_WITNESS_RETRIEVAL_PUBLIC_RUNNER_VERIFICATION_20261003_V1":
        errors.append("COMPILER_VERIFICATION_SCHEMA_INVALID")
    c_runner = compiler_verification.get("independent_runner")
    if not isinstance(c_runner, Mapping) or c_runner.get("conclusion") != "success":
        errors.append("COMPILER_INDEPENDENT_RUNNER_NOT_SUCCESS")
    c_verified = compiler_verification.get("verified")
    if not isinstance(c_verified, Mapping):
        errors.append("COMPILER_VERIFIED_BLOCK_MISSING")
    else:
        for field in (
            "unicode_focus",
            "unicode_relevance",
            "no_result_nonexistence_firewall",
            "candidate_only_self_verification_blocked",
            "first_verified_witness_stop",
            "orthogonal_surface_diversification",
            "scope_limited_exhaustive_closure",
        ):
            if c_verified.get(field) is not True:
                errors.append("COMPILER_VERIFICATION_FALSE:" + field)

    if backend_verification.get("schema") != "PROJECT_BRAIN_GITHUB_PUBLIC_RETRIEVAL_SURFACES_PUBLIC_RUNNER_VERIFICATION_20261003_V1":
        errors.append("BACKEND_VERIFICATION_SCHEMA_INVALID")
    b_runner = backend_verification.get("independent_runner")
    if not isinstance(b_runner, Mapping) or b_runner.get("conclusion") != "success":
        errors.append("BACKEND_INDEPENDENT_RUNNER_NOT_SUCCESS")
    b_verified = backend_verification.get("verified")
    if not isinstance(b_verified, Mapping):
        errors.append("BACKEND_VERIFIED_BLOCK_MISSING")
    else:
        for field in (
            "unicode_query_transport_preserved",
            "descriptionless_repository_candidates_retained",
            "code_content_discovery_independent_of_repository_description_and_stars",
            "candidate_only_authority_preserved",
            "no_result_nonexistence_inference_forbidden",
        ):
            if b_verified.get(field) is not True:
                errors.append("BACKEND_VERIFICATION_FALSE:" + field)

    if action.get("new_reality_units") != 0:
        errors.append("TOOL_DISCOVERY_RETRIEVAL_EDGE_FRESH_REALITY_NONZERO")

    if errors:
        return _fail(*errors)

    return {
        "schema": SCHEMA,
        "status": "PASS__LIVE_TOOL_DISCOVERY_EDGE_MECHANICALLY_BOUND_TO_VERIFIED_V2_RETRIEVAL_AUTHORITY",
        "pass": True,
        "target_predicate": TARGET,
        "action_id": ACTION_ID,
        "exact_binding": dict(EXPECTED),
        "unknown_preserved": True,
        "same_epoch_replay_disabled": True,
        "acceptance_credit": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "errors": [],
    }


def evaluate_repository(root: Path) -> dict[str, Any]:
    def raw(rel: str) -> bytes:
        return (root / rel).read_bytes()

    def load(rel: str) -> dict[str, Any]:
        return json.loads(raw(rel).decode("utf-8"))

    actual_blobs = {
        "activation_blob": git_blob_sha(raw(EXPECTED["activation_path"])),
        "activation_verification_blob": git_blob_sha(raw(EXPECTED["activation_verification_path"])),
        "compiler_blob": git_blob_sha(raw(EXPECTED["compiler_path"])),
        "compiler_verification_blob": git_blob_sha(raw(EXPECTED["compiler_verification_path"])),
        "router_blob": git_blob_sha(raw(EXPECTED["router_path"])),
        "github_provider_blob": git_blob_sha(raw(EXPECTED["github_provider_path"])),
        "backend_verification_blob": git_blob_sha(raw(EXPECTED["backend_verification_path"])),
    }
    return validate(
        load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
        load(EXPECTED["activation_path"]),
        load(EXPECTED["activation_verification_path"]),
        load(EXPECTED["compiler_verification_path"]),
        load(EXPECTED["backend_verification_path"]),
        actual_blobs,
    )


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    out = evaluate_repository(root)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
