"""Bridge Universal Verified Adaptive Solver V3 traces into skill induction.

A V3 solve is not automatically a permanent capability. This bridge requires a
separate content-addressed task-outcome receipt and a separate content-addressed
independent verification receipt bound to the exact V3 trajectory. Only then does
it emit an episode accepted by executable_skill_program_v7.

Two or more such episodes with the same executable skeleton may be passed to the
existing skill inducer. The induced skill remains candidate-only until that module's
separate behavior-preservation verification succeeds.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)
from canonical.runtime.executable_skill_program_v7 import (
    induce_candidate,
    program_digest,
)
from canonical.runtime.universal_verified_adaptive_solver_v3 import (
    SCHEMA as SOLVER_SCHEMA,
    task_contract_sha256,
)

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SOLVER_SKILL_BRIDGE_V1"
OUTCOME_SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SOLVER_TASK_OUTCOME_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SOLVER_TASK_OUTCOME_INDEPENDENT_VERIFICATION_V1"


class SkillBridgeError(ValueError):
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
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise SkillBridgeError(label + "_INVALID")
    return value.strip()


def trajectory_sha256(solver_result: Mapping[str, Any]) -> str:
    trace = solver_result.get("trace")
    if not isinstance(trace, list):
        raise SkillBridgeError("SOLVER_TRACE_INVALID")
    normalized = []
    for i, row in enumerate(trace):
        if not isinstance(row, Mapping):
            raise SkillBridgeError("SOLVER_TRACE_ROW_INVALID:" + str(i))
        normalized.append({
            "cycle": row.get("cycle"),
            "capability_id": row.get("capability_id"),
            "verifier_id": row.get("verifier_id"),
            "proposal_sha256": row.get("proposal_sha256"),
            "proof_digest": row.get("proof_digest"),
            "new_verified_effects": row.get("new_verified_effects"),
            "effect_semantics_receipt": row.get("effect_semantics_receipt"),
            "effect_semantics_verification": row.get("effect_semantics_verification"),
        })
    return _digest(normalized)


def _cap_map(problem: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = problem.get("capabilities")
    if not isinstance(raw, list) or not raw:
        raise SkillBridgeError("CAPABILITIES_REQUIRED")
    out = {}
    for row in raw:
        if not isinstance(row, Mapping):
            raise SkillBridgeError("CAPABILITY_NOT_OBJECT")
        cid = _token(row.get("id"), "CAPABILITY_ID")
        if cid in out:
            raise SkillBridgeError("CAPABILITY_ID_DUPLICATE:" + cid)
        out[cid] = row
    return out


def compile_episode(
    problem: Mapping[str, Any],
    solver_result: Mapping[str, Any],
    outcome_pair: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        raise SkillBridgeError("PROBLEM_NOT_OBJECT")
    if not isinstance(solver_result, Mapping):
        raise SkillBridgeError("SOLVER_RESULT_NOT_OBJECT")
    if solver_result.get("schema") != SOLVER_SCHEMA:
        raise SkillBridgeError("SOLVER_RESULT_SCHEMA_INVALID")
    if solver_result.get("pass") is not True:
        raise SkillBridgeError("SOLVER_RESULT_NOT_PASS")
    if solver_result.get("status") != "SOLVED__ALL_TARGET_EFFECTS_INDEPENDENTLY_SEMANTICS_BOUND":
        raise SkillBridgeError("SOLVER_RESULT_NOT_FINAL_V3_SOLVE")
    expected_contract = task_contract_sha256(problem)
    if solver_result.get("task_contract_sha256") != expected_contract:
        raise SkillBridgeError("SOLVER_TASK_CONTRACT_DIGEST_MISMATCH")

    trace = solver_result.get("trace")
    if not isinstance(trace, list) or not trace:
        raise SkillBridgeError("NONEMPTY_SOLVER_TRACE_REQUIRED")
    caps = _cap_map(problem)
    steps = []
    for i, row in enumerate(trace):
        if not isinstance(row, Mapping):
            raise SkillBridgeError("TRACE_ROW_INVALID:" + str(i))
        cid = _token(row.get("capability_id"), "TRACE_CAPABILITY_ID")
        cap = caps.get(cid)
        if cap is None:
            raise SkillBridgeError("TRACE_CAPABILITY_NOT_IN_PROBLEM:" + cid)
        requires = cap.get("requires")
        provides = cap.get("provides")
        if not isinstance(requires, list) or not isinstance(provides, list):
            raise SkillBridgeError("CAPABILITY_REQUIRES_PROVIDES_INVALID:" + cid)
        effects = row.get("new_verified_effects")
        if effects != provides:
            raise SkillBridgeError("TRACE_EFFECTS_DO_NOT_MATCH_CAPABILITY:" + cid)
        if row.get("effect_semantics_authenticated") is not True:
            raise SkillBridgeError("TRACE_EFFECT_SEMANTICS_NOT_AUTHENTICATED:" + cid)
        steps.append({
            "op": cid,
            "inputs": sorted(str(x) for x in requires),
            "outputs": sorted(str(x) for x in provides),
        })

    traj_sha = trajectory_sha256(solver_result)
    if not isinstance(outcome_pair, Mapping):
        raise SkillBridgeError("OUTCOME_PAIR_INVALID")
    try:
        rr = resolve_receipt_bytes(outcome_pair.get("receipt"), repo_root=repo_root)
        vr = resolve_receipt_bytes(outcome_pair.get("verification"), repo_root=repo_root)
    except ReceiptResolutionError as exc:
        raise SkillBridgeError("OUTCOME_RECEIPT_RESOLUTION_FAILED:" + str(exc)) from exc

    rd = rr["document"]
    vd = vr["document"]
    if rd.get("schema") != OUTCOME_SCHEMA:
        raise SkillBridgeError("OUTCOME_SCHEMA_INVALID")
    if vd.get("schema") != VERIFY_SCHEMA:
        raise SkillBridgeError("OUTCOME_VERIFY_SCHEMA_INVALID")
    if vd.get("subject_git_blob_sha") != rr["git_blob_sha"]:
        raise SkillBridgeError("OUTCOME_VERIFY_SUBJECT_MISMATCH")

    task_id = _token((solver_result.get("task_contract") or {}).get("task_id"), "TASK_ID")
    scope_id = _token(rd.get("scope_id"), "SCOPE_ID")
    targets = sorted(str(x) for x in (problem.get("target_effects") or []))
    preconditions = sorted(str(x) for x in (problem.get("initial_facts") or []))
    invalidators = rd.get("invalidators", [])
    if not isinstance(invalidators, list) or any(not isinstance(x, str) or not x for x in invalidators):
        raise SkillBridgeError("OUTCOME_INVALIDATORS_INVALID")

    required_outcome = {
        "task_id": task_id,
        "task_contract_sha256": expected_contract,
        "trajectory_sha256": traj_sha,
        "status": "SUCCESS",
        "postconditions": targets,
    }
    for key, expected in required_outcome.items():
        if rd.get(key) != expected:
            raise SkillBridgeError("OUTCOME_RECEIPT_MISMATCH:" + key)

    digest = program_digest(
        steps=steps,
        preconditions=preconditions,
        postconditions=targets,
        invalidators=invalidators,
    )
    required_verify = {
        "task_id": task_id,
        "task_contract_sha256": expected_contract,
        "trajectory_sha256": traj_sha,
        "scope_id": scope_id,
        "program_sha256": digest,
        "pass": True,
        "independent_verified": True,
        "behavior_verified": True,
        "exact_byte_bound": True,
    }
    for key, expected in required_verify.items():
        if vd.get(key) != expected:
            raise SkillBridgeError("OUTCOME_VERIFY_MISMATCH:" + key)
    verifier_id = _token(vd.get("independent_verifier_id"), "INDEPENDENT_VERIFIER_ID")

    episode_id = "UVAS3:" + sha256(
        (task_id + "\0" + traj_sha + "\0" + rr["git_blob_sha"]).encode("utf-8")
    ).hexdigest()[:24]
    receipt_id = vr["path"] + "@" + vr["git_blob_sha"]
    return {
        "schema": SCHEMA,
        "status": "VERIFIED_EPISODE_READY_FOR_SKILL_INDUCTION",
        "episode": {
            "episode_id": episode_id,
            "scope_id": scope_id,
            "steps": steps,
            "preconditions": preconditions,
            "postconditions": targets,
            "invalidators": invalidators,
            "verification_receipt": {
                "independent_verified": True,
                "exact_byte_bound": True,
                "conclusion": "success",
                "behavior_verified": True,
                "episode_id": episode_id,
                "scope_id": scope_id,
                "program_sha256": digest,
                "receipt_id": receipt_id,
            },
        },
        "trajectory_sha256": traj_sha,
        "outcome_receipt": {"path": rr["path"], "git_blob_sha": rr["git_blob_sha"]},
        "outcome_verification": {"path": vr["path"], "git_blob_sha": vr["git_blob_sha"]},
        "independent_verifier_id": verifier_id,
        "reuse_authorized": False,
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }


def induce_skill_candidate(episode_outputs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    episodes = []
    for i, row in enumerate(episode_outputs):
        if not isinstance(row, Mapping):
            raise SkillBridgeError("EPISODE_OUTPUT_INVALID:" + str(i))
        if row.get("schema") != SCHEMA or row.get("status") != "VERIFIED_EPISODE_READY_FOR_SKILL_INDUCTION":
            raise SkillBridgeError("EPISODE_OUTPUT_NOT_VERIFIED:" + str(i))
        episode = row.get("episode")
        if not isinstance(episode, Mapping):
            raise SkillBridgeError("EPISODE_MISSING:" + str(i))
        episodes.append(episode)
    return induce_candidate(episodes)
