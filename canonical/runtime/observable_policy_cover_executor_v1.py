"""Live executor for an authenticated observable policy-cover tree.

This is the missing live seam between the already-owned
observable_policy_cover_totality_gate_v1 proof and R2 execution.

The raw totality gate deliberately operates on supplied finite proof objects. This
adapter adds two authority boundaries before the gate can influence a live
decision:

1. the complete policy-cover problem must be content-addressed and independently
   authenticated; and
2. every runtime observation used to traverse the tree must be content-addressed,
   independently verified, truth-preserving, safe, and precommitted.

A positive result selects one Brain-owned policy already certified adequate for
the entire surviving world class. It does not itself execute that policy and does
not certify the caller's original goal as satisfied.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.observable_policy_cover_totality_gate_v1 import (
    evaluate as evaluate_cover,
)

SCHEMA = "PROJECT_BRAIN_OBSERVABLE_POLICY_COVER_EXECUTOR_V1"
COVER_BINDING_SCHEMA = "PROJECT_BRAIN_OBSERVABLE_POLICY_COVER_INPUT_BINDING_V1"
COVER_BINDING_VERIFY_SCHEMA = (
    "PROJECT_BRAIN_OBSERVABLE_POLICY_COVER_INPUT_BINDING_INDEPENDENT_VERIFICATION_V1"
)
OBSERVATION_SCHEMA = "PROJECT_BRAIN_POLICY_COVER_OBSERVATION_BINDING_V1"
OBSERVATION_VERIFY_SCHEMA = (
    "PROJECT_BRAIN_POLICY_COVER_OBSERVATION_BINDING_INDEPENDENT_VERIFICATION_V1"
)
MAX_OBSERVATIONS = 64


class PolicyCoverExecutionError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canon(value).encode("utf-8")).hexdigest()


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _bound_json(
    ref: Mapping[str, Any] | None,
    *,
    repo_root: Path,
    prefixes: tuple[str, ...],
) -> tuple[dict[str, Any], str, str]:
    if not isinstance(ref, Mapping):
        raise PolicyCoverExecutionError("BOUND_REF_REQUIRED")
    rel = str(ref.get("path") or "").strip()
    expected = str(ref.get("git_blob_sha") or "").strip()
    path = Path(rel)
    if not rel or path.is_absolute() or ".." in path.parts:
        raise PolicyCoverExecutionError("BOUND_PATH_INVALID")
    if not any(rel.startswith(prefix) for prefix in prefixes):
        raise PolicyCoverExecutionError("BOUND_PATH_OUTSIDE_ALLOWED_SCOPE")
    full = repo_root / path
    if not full.is_file():
        raise PolicyCoverExecutionError("BOUND_FILE_MISSING:" + rel)
    actual = _git_blob_sha(full)
    if expected != actual:
        raise PolicyCoverExecutionError("BOUND_BLOB_DRIFT:" + rel)
    doc = json.loads(full.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise PolicyCoverExecutionError("BOUND_JSON_NOT_OBJECT:" + rel)
    return doc, rel, actual


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "policy_selection_authorized": False,
        "selected_policy_adequacy_verified": False,
        "actual_goal_satisfaction_verified": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _open(status: str, *, reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": False,
        "reason": reason,
        "policy_selection_authorized": False,
        "selected_policy_adequacy_verified": False,
        "actual_goal_satisfaction_verified": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _authenticate_cover_binding(
    binding: Mapping[str, Any] | None,
    *,
    problem: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        return {
            "pass": False,
            "status": "OPEN__POLICY_COVER_INPUT_BINDING_REQUIRED",
        }
    try:
        receipt, receipt_path, receipt_blob = _bound_json(
            binding.get("receipt"),
            repo_root=repo_root,
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verification, verification_path, verification_blob = _bound_json(
            binding.get("verification"),
            repo_root=repo_root,
            prefixes=("canonical/verification/",),
        )
        state_id = problem.get("state_id")
        problem_sha = _digest(problem)
        if receipt.get("schema") != COVER_BINDING_SCHEMA:
            raise PolicyCoverExecutionError("COVER_BINDING_SCHEMA_INVALID")
        if receipt.get("state_id") != state_id:
            raise PolicyCoverExecutionError("COVER_BINDING_STATE_MISMATCH")
        if receipt.get("problem_sha256") != problem_sha:
            raise PolicyCoverExecutionError("COVER_BINDING_PROBLEM_MISMATCH")
        for field in (
            "cover_inputs_authenticated",
            "policy_relevant_world_set_completeness_authenticated",
            "all_policy_adequacy_receipts_authenticated",
            "all_discriminator_truth_safety_receipts_authenticated",
            "brain_owned_and_resource_bounds_authenticated",
        ):
            if receipt.get(field) is not True:
                raise PolicyCoverExecutionError(
                    "COVER_BINDING_PREMISE_UNPROVED:" + field
                )

        if verification.get("schema") != COVER_BINDING_VERIFY_SCHEMA:
            raise PolicyCoverExecutionError("COVER_BINDING_VERIFY_SCHEMA_INVALID")
        if verification.get("subject_git_blob_sha") != receipt_blob:
            raise PolicyCoverExecutionError("COVER_BINDING_VERIFY_SUBJECT_MISMATCH")
        if verification.get("state_id") != state_id:
            raise PolicyCoverExecutionError("COVER_BINDING_VERIFY_STATE_MISMATCH")
        if verification.get("problem_sha256") != problem_sha:
            raise PolicyCoverExecutionError("COVER_BINDING_VERIFY_PROBLEM_MISMATCH")
        for field in (
            "pass",
            "independent_verified",
            "input_authentication_verified",
            "policy_adequacy_authentication_verified",
            "discriminator_semantics_authentication_verified",
        ):
            if verification.get(field) is not True:
                raise PolicyCoverExecutionError(
                    "COVER_BINDING_VERIFY_PREMISE_UNPROVED:" + field
                )
        verifier_id = verification.get("independent_verifier_id")
        if not isinstance(verifier_id, str) or not verifier_id.strip():
            raise PolicyCoverExecutionError(
                "COVER_BINDING_INDEPENDENT_VERIFIER_ID_MISSING"
            )
        return {
            "pass": True,
            "status": "PASS__POLICY_COVER_INPUTS_AUTHENTICATED",
            "state_id": state_id,
            "problem_sha256": problem_sha,
            "receipt_path": receipt_path,
            "receipt_git_blob_sha": receipt_blob,
            "verification_path": verification_path,
            "verification_git_blob_sha": verification_blob,
            "independent_verifier_id": verifier_id.strip(),
        }
    except Exception as exc:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__POLICY_COVER_INPUT_BINDING_INVALID",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _authenticate_observation(
    binding: Mapping[str, Any] | None,
    *,
    state_id: str,
    discriminator_id: str,
    repo_root: Path,
) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        return {
            "pass": False,
            "status": "OPEN__POLICY_COVER_OBSERVATION_BINDING_REQUIRED",
        }
    try:
        receipt, receipt_path, receipt_blob = _bound_json(
            binding.get("receipt"),
            repo_root=repo_root,
            prefixes=("canonical/governance/", "canonical/verification/"),
        )
        verification, verification_path, verification_blob = _bound_json(
            binding.get("verification"),
            repo_root=repo_root,
            prefixes=("canonical/verification/",),
        )
        if receipt.get("schema") != OBSERVATION_SCHEMA:
            raise PolicyCoverExecutionError("OBSERVATION_SCHEMA_INVALID")
        if receipt.get("state_id") != state_id:
            raise PolicyCoverExecutionError("OBSERVATION_STATE_MISMATCH")
        if receipt.get("discriminator_id") != discriminator_id:
            raise PolicyCoverExecutionError("OBSERVATION_DISCRIMINATOR_MISMATCH")
        if "outcome" not in receipt:
            raise PolicyCoverExecutionError("OBSERVATION_OUTCOME_MISSING")
        outcome = receipt["outcome"]
        outcome_sha = _digest(outcome)
        for field in (
            "observation_proved",
            "truth_preserving",
            "safe_observation",
            "precommitment",
        ):
            if receipt.get(field) is not True:
                raise PolicyCoverExecutionError(
                    "OBSERVATION_PREMISE_UNPROVED:" + field
                )

        if verification.get("schema") != OBSERVATION_VERIFY_SCHEMA:
            raise PolicyCoverExecutionError("OBSERVATION_VERIFY_SCHEMA_INVALID")
        if verification.get("subject_git_blob_sha") != receipt_blob:
            raise PolicyCoverExecutionError("OBSERVATION_VERIFY_SUBJECT_MISMATCH")
        if verification.get("state_id") != state_id:
            raise PolicyCoverExecutionError("OBSERVATION_VERIFY_STATE_MISMATCH")
        if verification.get("discriminator_id") != discriminator_id:
            raise PolicyCoverExecutionError(
                "OBSERVATION_VERIFY_DISCRIMINATOR_MISMATCH"
            )
        if verification.get("outcome_sha256") != outcome_sha:
            raise PolicyCoverExecutionError("OBSERVATION_VERIFY_OUTCOME_MISMATCH")
        for field in (
            "pass",
            "independent_verified",
            "observation_semantics_verified",
            "precommitment_verified",
        ):
            if verification.get(field) is not True:
                raise PolicyCoverExecutionError(
                    "OBSERVATION_VERIFY_PREMISE_UNPROVED:" + field
                )
        verifier_id = verification.get("independent_verifier_id")
        if not isinstance(verifier_id, str) or not verifier_id.strip():
            raise PolicyCoverExecutionError(
                "OBSERVATION_INDEPENDENT_VERIFIER_ID_MISSING"
            )
        return {
            "pass": True,
            "status": "PASS__POLICY_COVER_OBSERVATION_AUTHENTICATED",
            "state_id": state_id,
            "discriminator_id": discriminator_id,
            "outcome": outcome,
            "outcome_sha256": outcome_sha,
            "receipt_path": receipt_path,
            "receipt_git_blob_sha": receipt_blob,
            "verification_path": verification_path,
            "verification_git_blob_sha": verification_blob,
            "independent_verifier_id": verifier_id.strip(),
        }
    except Exception as exc:
        return {
            "pass": False,
            "status": "FAIL_CLOSED__POLICY_COVER_OBSERVATION_BINDING_INVALID",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _problem_maps(
    problem: Mapping[str, Any],
) -> tuple[list[str], dict[str, Mapping[str, Any]], dict[str, set[str]]]:
    worlds = problem.get("worlds")
    policies = problem.get("policies")
    discriminators = problem.get("discriminators", [])
    if (
        not isinstance(worlds, Sequence)
        or isinstance(worlds, (str, bytes))
        or not isinstance(policies, Sequence)
        or isinstance(policies, (str, bytes))
        or not isinstance(discriminators, Sequence)
        or isinstance(discriminators, (str, bytes))
    ):
        raise PolicyCoverExecutionError("POLICY_COVER_PROBLEM_SHAPE_INVALID")
    world_ids = [str(row.get("world_id")) for row in worlds if isinstance(row, Mapping)]
    if len(world_ids) != len(worlds) or any(not x for x in world_ids):
        raise PolicyCoverExecutionError("POLICY_COVER_WORLD_IDS_INVALID")
    discriminator_map: dict[str, Mapping[str, Any]] = {}
    for row in discriminators:
        if not isinstance(row, Mapping):
            raise PolicyCoverExecutionError("POLICY_COVER_DISCRIMINATOR_INVALID")
        did = row.get("discriminator_id")
        if not isinstance(did, str) or not did:
            raise PolicyCoverExecutionError("POLICY_COVER_DISCRIMINATOR_ID_INVALID")
        discriminator_map[did] = row
    policy_regions: dict[str, set[str]] = {}
    for row in policies:
        if not isinstance(row, Mapping):
            raise PolicyCoverExecutionError("POLICY_COVER_POLICY_INVALID")
        pid = row.get("policy_id")
        members = row.get("adequate_world_ids")
        if (
            not isinstance(pid, str)
            or not pid
            or not isinstance(members, Sequence)
            or isinstance(members, (str, bytes))
        ):
            raise PolicyCoverExecutionError("POLICY_COVER_POLICY_REGION_INVALID")
        policy_regions[pid] = {str(x) for x in members}
    return world_ids, discriminator_map, policy_regions


def evaluate(
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    try:
        if not isinstance(payload, Mapping):
            return _fail("PAYLOAD_MAPPING_REQUIRED")
        allowed = {
            "problem",
            "cover_binding",
            "observation_bindings_by_discriminator_id",
            "max_observations",
        }
        extra = set(payload) - allowed
        if extra:
            return _fail("UNMODELED_EXECUTOR_FIELDS", extra=sorted(extra))

        problem = payload.get("problem")
        if not isinstance(problem, Mapping):
            return _fail("POLICY_COVER_PROBLEM_REQUIRED")
        state_id = problem.get("state_id")
        if not isinstance(state_id, str) or not state_id:
            return _fail("STATE_ID_REQUIRED")

        cover_auth = _authenticate_cover_binding(
            payload.get("cover_binding"),
            problem=problem,
            repo_root=root,
        )
        if cover_auth.get("pass") is not True:
            return _open(
                str(
                    cover_auth.get("status")
                    or "OPEN__POLICY_COVER_INPUT_BINDING_REQUIRED"
                ),
                reason="POLICY_COVER_INPUTS_NOT_INDEPENDENTLY_AUTHENTICATED",
                cover_binding=cover_auth,
            )

        cover = evaluate_cover(problem)
        if cover.get("pass") is not True:
            return _open(
                "OPEN__OBSERVABLE_POLICY_COVER_NOT_PROVED",
                reason=str(
                    cover.get("reason")
                    or cover.get("status")
                    or "POLICY_COVER_GATE_UNRESOLVED"
                ),
                policy_cover_result=cover,
                cover_binding=cover_auth,
                unresolved_observational_classes=cover.get(
                    "unresolved_observational_classes"
                ),
                negative_impossibility_authorized=(
                    cover.get("negative_impossibility_authorized") is True
                ),
            )
        if cover.get("bound_state_totality_proved") is not True:
            return _fail(
                "POLICY_COVER_GATE_PASS_WITHOUT_TOTALITY",
                policy_cover_result=cover,
            )

        observations = payload.get("observation_bindings_by_discriminator_id", {})
        if not isinstance(observations, Mapping):
            return _fail("OBSERVATION_BINDINGS_MAP_INVALID")
        max_observations = payload.get("max_observations", MAX_OBSERVATIONS)
        if (
            isinstance(max_observations, bool)
            or not isinstance(max_observations, int)
            or max_observations < 0
            or max_observations > MAX_OBSERVATIONS
        ):
            return _fail("MAX_OBSERVATIONS_INVALID")

        world_ids, discriminator_map, policy_regions = _problem_maps(problem)
        current_worlds = set(world_ids)
        node = cover.get("decision_tree")
        if not isinstance(node, Mapping):
            return _fail("POLICY_COVER_DECISION_TREE_INVALID")
        trace: list[dict[str, Any]] = []

        for step in range(max_observations + 1):
            policy_id = node.get("terminal_policy_id")
            if isinstance(policy_id, str) and policy_id:
                region = policy_regions.get(policy_id)
                if region is None:
                    return _fail(
                        "SELECTED_POLICY_NOT_IN_BOUND_PROBLEM",
                        selected_policy_id=policy_id,
                    )
                if not current_worlds.issubset(region):
                    return _fail(
                        "SELECTED_POLICY_DOES_NOT_COVER_SURVIVING_CLASS",
                        selected_policy_id=policy_id,
                        surviving_world_ids=sorted(current_worlds),
                    )
                return {
                    "schema": SCHEMA,
                    "status": "PASS__AUTHENTICATED_OBSERVABLE_POLICY_SELECTED",
                    "pass": True,
                    "state_id": state_id,
                    "selected_policy_id": policy_id,
                    "surviving_world_ids": sorted(current_worlds),
                    "observation_count": len(trace),
                    "observation_trace": trace,
                    "minimum_worst_case_resource_bound_units": cover.get(
                        "minimum_worst_case_resource_bound_units"
                    ),
                    "policy_cover_result": cover,
                    "cover_binding": cover_auth,
                    "bound_state_totality_proved": True,
                    "policy_selection_authorized": True,
                    "selected_policy_adequacy_verified": True,
                    "actual_goal_satisfaction_verified": False,
                    "u_empty_authorized": False,
                    "terminal_authority": False,
                    "terminal_credit_delta": 0,
                    "boundary": (
                        "BOUND_FINITE_POLICY_RELEVANT_STATE_ONLY__"
                        "POLICY_SELECTION_AND_ADEQUACY_ONLY__"
                        "EXECUTION_AND_ACTUAL_GOAL_ACCEPTANCE_REMAIN_SEPARATE"
                    ),
                }

            discriminator_id = node.get("discriminator_id")
            partitions = node.get("outcome_partitions")
            if (
                not isinstance(discriminator_id, str)
                or not discriminator_id
                or not isinstance(partitions, list)
                or len(partitions) < 2
            ):
                return _fail(
                    "POLICY_COVER_TREE_NODE_INVALID",
                    step=step,
                    node=dict(node),
                )
            if step >= max_observations:
                return _open(
                    "OPEN__POLICY_COVER_OBSERVATION_BOUND_EXHAUSTED",
                    reason="MAX_OBSERVATIONS_REACHED_BEFORE_TERMINAL_POLICY",
                    selected_discriminator_id=discriminator_id,
                    surviving_world_ids=sorted(current_worlds),
                    observation_trace=trace,
                    policy_cover_result=cover,
                    cover_binding=cover_auth,
                )

            disc = discriminator_map.get(discriminator_id)
            if not isinstance(disc, Mapping):
                return _fail(
                    "TREE_DISCRIMINATOR_NOT_IN_BOUND_PROBLEM",
                    discriminator_id=discriminator_id,
                )
            outcomes = disc.get("outcomes")
            if not isinstance(outcomes, Mapping):
                return _fail(
                    "BOUND_DISCRIMINATOR_OUTCOME_MAP_INVALID",
                    discriminator_id=discriminator_id,
                )

            binding = observations.get(discriminator_id)
            obs_auth = _authenticate_observation(
                binding if isinstance(binding, Mapping) else None,
                state_id=state_id,
                discriminator_id=discriminator_id,
                repo_root=root,
            )
            if obs_auth.get("pass") is not True:
                return _open(
                    str(
                        obs_auth.get("status")
                        or "OPEN__POLICY_COVER_OBSERVATION_BINDING_REQUIRED"
                    ),
                    reason="SELECTED_POLICY_CHANGING_OBSERVATION_NOT_AUTHENTICATED",
                    next_observation_request={
                        "schema": "PROJECT_BRAIN_POLICY_COVER_OBSERVATION_REQUEST_V1",
                        "state_id": state_id,
                        "discriminator_id": discriminator_id,
                        "surviving_world_ids": sorted(current_worlds),
                        "observation_authority": False,
                    },
                    observation_binding=obs_auth,
                    observation_trace=trace,
                    policy_cover_result=cover,
                    cover_binding=cover_auth,
                )

            observed_key = _canon(obs_auth["outcome"])
            expected_worlds = {
                wid
                for wid in current_worlds
                if wid in outcomes and _canon(outcomes[wid]) == observed_key
            }
            if not expected_worlds:
                return _fail(
                    "AUTHENTICATED_OBSERVATION_HAS_NO_SURVIVING_BOUND_WORLD",
                    discriminator_id=discriminator_id,
                    observed_outcome_sha256=obs_auth["outcome_sha256"],
                    surviving_world_ids=sorted(current_worlds),
                )

            matched = []
            for part in partitions:
                if not isinstance(part, Mapping):
                    return _fail("POLICY_COVER_TREE_PARTITION_INVALID")
                ids = part.get("world_ids")
                nxt = part.get("next")
                if (
                    not isinstance(ids, list)
                    or not ids
                    or any(not isinstance(x, str) for x in ids)
                    or not isinstance(nxt, Mapping)
                ):
                    return _fail("POLICY_COVER_TREE_PARTITION_INVALID")
                if set(ids) == expected_worlds:
                    matched.append((set(ids), nxt))
            if len(matched) != 1:
                return _fail(
                    "OBSERVATION_TO_TREE_PARTITION_BINDING_INVALID",
                    discriminator_id=discriminator_id,
                    expected_world_ids=sorted(expected_worlds),
                    matching_partition_count=len(matched),
                )

            current_worlds, node = matched[0]
            trace.append(
                {
                    "step": step,
                    "discriminator_id": discriminator_id,
                    "outcome_sha256": obs_auth["outcome_sha256"],
                    "surviving_world_ids": sorted(current_worlds),
                    "observation_binding": {
                        "receipt_path": obs_auth["receipt_path"],
                        "receipt_git_blob_sha": obs_auth["receipt_git_blob_sha"],
                        "verification_path": obs_auth["verification_path"],
                        "verification_git_blob_sha": obs_auth[
                            "verification_git_blob_sha"
                        ],
                        "independent_verifier_id": obs_auth[
                            "independent_verifier_id"
                        ],
                    },
                }
            )

        return _fail("UNREACHABLE_EXECUTOR_STATE")
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return evaluate(args or {}, repo_root=root)
