"""Adapt authenticated observable policy-cover totality into Escape Gap-A proofs.

Composition only. This module mints no new semantic or execution authority.
It reuses the current content-authenticated observable-policy-cover seam and
emits a Gap-A proof only when the remaining current-availability/acquirability
premise is independently content-bound.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.escape_progress_shared_gap_audit_v3 import GAP_A
from canonical.runtime import escape_progress_shared_gap_audit_v5 as current_gap_audit
from canonical.runtime.observable_policy_cover_executor_v1 import (
    _authenticate_cover_binding,
    _bound_json,
)
from canonical.runtime.observable_policy_cover_totality_gate_v1 import (
    evaluate as evaluate_cover,
)

SCHEMA = "PROJECT_BRAIN_ESCAPE_GAP_A_POLICY_COVER_ADAPTER_V1"
MANIFEST_SCHEMA = "PROJECT_BRAIN_ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_V2"
MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "governance"
    / "ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"
)

POLICY_AVAILABILITY_SCHEMA = (
    "PROJECT_BRAIN_GAP_A_POLICY_CURRENT_AVAILABILITY_RECEIPT_V1"
)
POLICY_AVAILABILITY_VERIFY_SCHEMA = (
    "PROJECT_BRAIN_GAP_A_POLICY_CURRENT_AVAILABILITY_INDEPENDENT_VERIFICATION_V1"
)
DISCRIMINATOR_ACQUIRABILITY_SCHEMA = (
    "PROJECT_BRAIN_GAP_A_DISCRIMINATOR_CURRENT_ACQUIRABILITY_RECEIPT_V1"
)
DISCRIMINATOR_ACQUIRABILITY_VERIFY_SCHEMA = (
    "PROJECT_BRAIN_GAP_A_DISCRIMINATOR_CURRENT_ACQUIRABILITY_INDEPENDENT_VERIFICATION_V1"
)


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _proof_sha(proof: Mapping[str, Any]) -> str:
    return sha256(_canon(dict(proof))).hexdigest()


def _base(status: str, *, passed: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "row_proof_emitted": False,
        "row_credit_delta": 0,
        "cc_r3_credit_delta": 0,
        "capability_credit_delta": 0,
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _manifest_row(obligation_id: str, root: Path) -> Mapping[str, Any]:
    """Resolve one row through the same current projection used by audit V5.

    The successor manifest is historical provenance. Current route-group
    membership is authority-owned by the mutable current classification ->
    current shared binding -> verified effective projection chain.
    """
    resolved = current_gap_audit._load_current_manifest_binding(repo_root=root)
    doc = resolved.get("manifest")
    binding = resolved.get("binding")
    if not isinstance(doc, Mapping) or doc.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("CURRENT_MANIFEST_SCHEMA_INVALID")
    if not isinstance(binding, Mapping):
        raise ValueError("CURRENT_ESCAPE_BINDING_INVALID")

    rows = [
        row
        for row in doc.get("rows", [])
        if isinstance(row, Mapping) and row.get("obligation_id") == obligation_id
    ]
    if len(rows) != 1:
        raise ValueError("OBLIGATION_ID_NOT_UNIQUE_IN_CURRENT_MANIFEST")

    projection = binding.get("current_effective_projection")
    if not isinstance(projection, Mapping):
        raise ValueError("CURRENT_EFFECTIVE_PROJECTION_MISSING")
    overrides = projection.get("route_group_overrides", {})
    parked = projection.get("parked_rows", [])
    if not isinstance(overrides, Mapping):
        raise ValueError("CURRENT_ROUTE_GROUP_OVERRIDES_INVALID")
    if not isinstance(parked, list) or any(not isinstance(x, str) for x in parked):
        raise ValueError("CURRENT_PARKED_ROWS_INVALID")
    if obligation_id in parked:
        raise ValueError("OBLIGATION_PARKED_NOT_CURRENT_GAP_A")

    row = dict(rows[0])
    effective_route_group = overrides.get(obligation_id, row.get("route_group"))
    if effective_route_group != GAP_A:
        raise ValueError("OBLIGATION_NOT_CURRENT_GAP_A")
    row["route_group"] = effective_route_group
    return row


def _verify_policy_availability(
    binding: Mapping[str, Any] | None,
    *,
    root: Path,
    state_id: str,
    obligation_id: str,
    policy_id: str,
) -> dict[str, Any]:
    try:
        if not isinstance(binding, Mapping):
            return {"pass": False, "status": "OPEN__POLICY_CURRENT_AVAILABILITY_REQUIRED"}
        receipt, receipt_path, receipt_blob = _bound_json(
            binding.get("receipt"),
            repo_root=root,
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verify, verify_path, verify_blob = _bound_json(
            binding.get("verification"),
            repo_root=root,
            prefixes=("canonical/verification/",),
        )
        expected = {
            "state_id": state_id,
            "obligation_id": obligation_id,
            "common_policy_id": policy_id,
        }
        if receipt.get("schema") != POLICY_AVAILABILITY_SCHEMA:
            raise ValueError("POLICY_AVAILABILITY_SCHEMA_INVALID")
        for key, value in expected.items():
            if receipt.get(key) != value:
                raise ValueError("POLICY_AVAILABILITY_BINDING_MISMATCH:" + key)
        if receipt.get("currently_available") is not True:
            raise ValueError("POLICY_CURRENT_AVAILABILITY_NOT_PROVED")
        if receipt.get("resource_admissible") is not True:
            raise ValueError("POLICY_RESOURCE_ADMISSIBILITY_NOT_PROVED")

        if verify.get("schema") != POLICY_AVAILABILITY_VERIFY_SCHEMA:
            raise ValueError("POLICY_AVAILABILITY_VERIFY_SCHEMA_INVALID")
        if verify.get("subject_git_blob_sha") != receipt_blob:
            raise ValueError("POLICY_AVAILABILITY_VERIFY_SUBJECT_MISMATCH")
        for key, value in expected.items():
            if verify.get(key) != value:
                raise ValueError("POLICY_AVAILABILITY_VERIFY_BINDING_MISMATCH:" + key)
        for key in (
            "pass",
            "independent_verified",
            "current_availability_verified",
            "resource_admissibility_verified",
        ):
            if verify.get(key) is not True:
                raise ValueError("POLICY_AVAILABILITY_VERIFY_PREMISE_UNPROVED:" + key)
        verifier = verify.get("independent_verifier_id")
        if not isinstance(verifier, str) or not verifier.strip():
            raise ValueError("POLICY_AVAILABILITY_INDEPENDENT_VERIFIER_MISSING")
        return {
            "pass": True,
            "receipt_path": receipt_path,
            "receipt_git_blob_sha": receipt_blob,
            "verification_path": verify_path,
            "verification_git_blob_sha": verify_blob,
            "independent_verifier_id": verifier.strip(),
        }
    except Exception as exc:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__POLICY_CURRENT_AVAILABILITY_BINDING_INVALID",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _verify_discriminator_acquirability(
    binding: Mapping[str, Any] | None,
    *,
    root: Path,
    state_id: str,
    obligation_id: str,
    discriminator_id: str,
) -> dict[str, Any]:
    try:
        if not isinstance(binding, Mapping):
            return {"pass": False, "status": "OPEN__DISCRIMINATOR_CURRENT_ACQUIRABILITY_REQUIRED"}
        receipt, receipt_path, receipt_blob = _bound_json(
            binding.get("receipt"),
            repo_root=root,
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verify, verify_path, verify_blob = _bound_json(
            binding.get("verification"),
            repo_root=root,
            prefixes=("canonical/verification/",),
        )
        expected = {
            "state_id": state_id,
            "obligation_id": obligation_id,
            "discriminator_id": discriminator_id,
        }
        if receipt.get("schema") != DISCRIMINATOR_ACQUIRABILITY_SCHEMA:
            raise ValueError("DISCRIMINATOR_ACQUIRABILITY_SCHEMA_INVALID")
        for key, value in expected.items():
            if receipt.get(key) != value:
                raise ValueError("DISCRIMINATOR_ACQUIRABILITY_BINDING_MISMATCH:" + key)
        if receipt.get("currently_acquirable") is not True:
            raise ValueError("DISCRIMINATOR_CURRENT_ACQUIRABILITY_NOT_PROVED")

        if verify.get("schema") != DISCRIMINATOR_ACQUIRABILITY_VERIFY_SCHEMA:
            raise ValueError("DISCRIMINATOR_ACQUIRABILITY_VERIFY_SCHEMA_INVALID")
        if verify.get("subject_git_blob_sha") != receipt_blob:
            raise ValueError("DISCRIMINATOR_ACQUIRABILITY_VERIFY_SUBJECT_MISMATCH")
        for key, value in expected.items():
            if verify.get(key) != value:
                raise ValueError("DISCRIMINATOR_ACQUIRABILITY_VERIFY_BINDING_MISMATCH:" + key)
        for key in ("pass", "independent_verified", "current_acquirability_verified"):
            if verify.get(key) is not True:
                raise ValueError("DISCRIMINATOR_ACQUIRABILITY_VERIFY_PREMISE_UNPROVED:" + key)
        verifier = verify.get("independent_verifier_id")
        if not isinstance(verifier, str) or not verifier.strip():
            raise ValueError("DISCRIMINATOR_ACQUIRABILITY_INDEPENDENT_VERIFIER_MISSING")
        return {
            "pass": True,
            "receipt_path": receipt_path,
            "receipt_git_blob_sha": receipt_blob,
            "verification_path": verify_path,
            "verification_git_blob_sha": verify_blob,
            "independent_verifier_id": verifier.strip(),
        }
    except Exception as exc:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__DISCRIMINATOR_CURRENT_ACQUIRABILITY_BINDING_INVALID",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def adapt(
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    try:
        if not isinstance(payload, Mapping):
            return _base("FAIL_CLOSED", reason="PAYLOAD_MAPPING_REQUIRED")
        allowed = {
            "obligation_id",
            "problem",
            "cover_binding",
            "policy_availability_binding",
            "discriminator_acquirability_binding",
        }
        extra = set(payload) - allowed
        if extra:
            return _base("FAIL_CLOSED", reason="UNMODELED_FIELDS:" + ",".join(sorted(extra)))

        obligation_id = payload.get("obligation_id")
        problem = payload.get("problem")
        if not isinstance(obligation_id, str) or not obligation_id:
            return _base("FAIL_CLOSED", reason="OBLIGATION_ID_REQUIRED")
        if not isinstance(problem, Mapping):
            return _base("FAIL_CLOSED", reason="POLICY_COVER_PROBLEM_REQUIRED")
        state_id = problem.get("state_id")
        if state_id != obligation_id:
            return _base("FAIL_CLOSED", reason="STATE_ID_MUST_EQUAL_OBLIGATION_ID")

        _manifest_row(obligation_id, root)

        cover_auth = _authenticate_cover_binding(
            payload.get("cover_binding"),
            problem=problem,
            repo_root=root,
        )
        if cover_auth.get("pass") is not True:
            return _base(
                str(cover_auth.get("status") or "OPEN__POLICY_COVER_INPUT_BINDING_REQUIRED"),
                reason="POLICY_COVER_INPUTS_NOT_INDEPENDENTLY_AUTHENTICATED",
                cover_binding=cover_auth,
            )

        cover = evaluate_cover(problem)
        if (
            cover.get("pass") is not True
            or cover.get("bound_state_totality_proved") is not True
            or cover.get("policy_safety_coverage_proved") is not True
        ):
            return _base(
                "OPEN__AUTHENTICATED_POLICY_COVER_TOTALITY_NOT_PROVED",
                reason=str(cover.get("reason") or cover.get("status") or "COVER_OPEN"),
                policy_cover_result=cover,
                cover_binding=cover_auth,
            )

        tree = cover.get("decision_tree")
        if not isinstance(tree, Mapping):
            return _base("FAIL_CLOSED", reason="POLICY_COVER_DECISION_TREE_INVALID")

        policy_id = tree.get("terminal_policy_id")
        if isinstance(policy_id, str) and policy_id:
            availability = _verify_policy_availability(
                payload.get("policy_availability_binding"),
                root=root,
                state_id=state_id,
                obligation_id=obligation_id,
                policy_id=policy_id,
            )
            if availability.get("pass") is not True:
                return _base(
                    str(availability.get("status") or "OPEN__POLICY_CURRENT_AVAILABILITY_REQUIRED"),
                    reason="CURRENT_POLICY_AVAILABILITY_OR_RESOURCE_ADMISSIBILITY_NOT_PROVED",
                    policy_availability=availability,
                    policy_cover_result=cover,
                    cover_binding=cover_auth,
                )
            proof = {
                "route_group": GAP_A,
                "resolution_mode": "TERMINAL_COMMON_POLICY",
                "currently_available": True,
                "common_policy_id": policy_id,
                "authenticated_scope_complete_certificate": True,
                "brain_owned": True,
                "adequate_over_entire_current_decision_region": True,
                "safe_over_entire_current_decision_region": True,
                "resource_admissible": True,
                "source_adapter_schema": SCHEMA,
                "cover_binding_receipt_git_blob_sha": cover_auth["receipt_git_blob_sha"],
                "cover_binding_verification_git_blob_sha": cover_auth["verification_git_blob_sha"],
                "availability_receipt_git_blob_sha": availability["receipt_git_blob_sha"],
                "availability_verification_git_blob_sha": availability["verification_git_blob_sha"],
            }
            proof["proof_sha256"] = _proof_sha(proof)
            return _base(
                "PASS__GAP_A_TERMINAL_COMMON_POLICY_PROOF_ADAPTED",
                passed=True,
                row_proof_emitted=True,
                obligation_id=obligation_id,
                row_proof=proof,
                policy_cover_result=cover,
                cover_binding=cover_auth,
                policy_availability=availability,
            )

        discriminator_id = tree.get("discriminator_id")
        partitions = tree.get("outcome_partitions")
        if (
            not isinstance(discriminator_id, str)
            or not discriminator_id
            or not isinstance(partitions, Sequence)
            or isinstance(partitions, (str, bytes))
            or len(partitions) < 2
        ):
            return _base("FAIL_CLOSED", reason="POLICY_COVER_ROOT_NOT_TERMINAL_OR_STRICT")

        before = len(problem.get("worlds", [])) if isinstance(problem.get("worlds"), Sequence) else 0
        partition_sets: list[tuple[str, ...]] = []
        for part in partitions:
            if not isinstance(part, Mapping):
                return _base("FAIL_CLOSED", reason="POLICY_COVER_PARTITION_INVALID")
            ids = part.get("world_ids")
            if (
                not isinstance(ids, list)
                or not ids
                or any(not isinstance(x, str) or not x for x in ids)
            ):
                return _base("FAIL_CLOSED", reason="POLICY_COVER_PARTITION_INVALID")
            partition_sets.append(tuple(sorted(set(ids))))
        after = max(len(x) for x in partition_sets)
        if before <= 1 or after < 1 or after >= before:
            return _base("FAIL_CLOSED", reason="ROOT_DISCRIMINATOR_NOT_STRICT")

        acquirability = _verify_discriminator_acquirability(
            payload.get("discriminator_acquirability_binding"),
            root=root,
            state_id=state_id,
            obligation_id=obligation_id,
            discriminator_id=discriminator_id,
        )
        if acquirability.get("pass") is not True:
            return _base(
                str(acquirability.get("status") or "OPEN__DISCRIMINATOR_CURRENT_ACQUIRABILITY_REQUIRED"),
                reason="CURRENT_DISCRIMINATOR_ACQUIRABILITY_NOT_PROVED",
                discriminator_acquirability=acquirability,
                policy_cover_result=cover,
                cover_binding=cover_auth,
            )

        outcome_ids = [
            "partition:" + sha256(_canon(list(ids))).hexdigest()
            for ids in partition_sets
        ]
        if len(set(outcome_ids)) != len(outcome_ids):
            return _base("FAIL_CLOSED", reason="ROOT_DISCRIMINATOR_PARTITIONS_NOT_DISTINCT")
        proof = {
            "route_group": GAP_A,
            "resolution_mode": "STRICT_DISCRIMINATOR",
            "currently_acquirable": True,
            "discriminator_id": discriminator_id,
            "finite_outcome_ids": outcome_ids,
            "outcome_map_complete": True,
            "decision_region_size_before": before,
            "max_nonterminal_decision_region_size_after": after,
            "authenticated_truth_preserving": True,
            "safe": True,
            "source_adapter_schema": SCHEMA,
            "cover_binding_receipt_git_blob_sha": cover_auth["receipt_git_blob_sha"],
            "cover_binding_verification_git_blob_sha": cover_auth["verification_git_blob_sha"],
            "acquirability_receipt_git_blob_sha": acquirability["receipt_git_blob_sha"],
            "acquirability_verification_git_blob_sha": acquirability["verification_git_blob_sha"],
        }
        proof["proof_sha256"] = _proof_sha(proof)
        return _base(
            "PASS__GAP_A_STRICT_DISCRIMINATOR_PROOF_ADAPTED",
            passed=True,
            row_proof_emitted=True,
            obligation_id=obligation_id,
            row_proof=proof,
            policy_cover_result=cover,
            cover_binding=cover_auth,
            discriminator_acquirability=acquirability,
        )
    except Exception as exc:
        return _base("FAIL_CLOSED", reason=type(exc).__name__ + ":" + str(exc))


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return adapt(args or {}, repo_root=root)
