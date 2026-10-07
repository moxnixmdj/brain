"""Verified skill ratchet for the Universal Verified Adaptive Solver.

A successful solver run can become an episode candidate. Reuse is forbidden until
the episode is independently verified through content-addressed receipts. Multiple
verified episodes with the same executable skeleton may induce a skill candidate;
that skill candidate itself still requires a second independent content-addressed
verification before reuse is authorized.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import executable_skill_program_v7 as skill
from canonical.runtime.skill_receipt_authenticator_v1 import (
    authenticate_episode_receipt,
    authenticate_candidate_receipt,
)

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_VERIFIED_SKILL_RATCHET_V1"


def episode_candidate_from_solver(
    solver_result: Mapping[str, Any],
    *,
    episode_id: str,
    scope_id: str,
    preconditions: Sequence[str] = (),
    postconditions: Sequence[str] = (),
    invalidators: Sequence[str] = (),
) -> dict[str, Any]:
    if solver_result.get("pass") is not True or solver_result.get("status") != "SOLVED__ALL_TARGET_EFFECTS_VERIFIED":
        raise ValueError("SOLVER_RUN_NOT_VERIFIED_SUCCESS")
    if not isinstance(episode_id, str) or not episode_id.strip():
        raise ValueError("EPISODE_ID_INVALID")
    if not isinstance(scope_id, str) or not scope_id.strip():
        raise ValueError("SCOPE_ID_INVALID")
    trace = solver_result.get("trace")
    if not isinstance(trace, list) or not trace:
        raise ValueError("SOLVER_TRACE_EMPTY")

    steps = []
    for row in trace:
        if not isinstance(row, Mapping):
            raise ValueError("TRACE_ROW_INVALID")
        cid = row.get("capability_id")
        verifier = row.get("verifier_id")
        outputs = row.get("new_verified_facts")
        if not isinstance(cid, str) or not cid:
            raise ValueError("TRACE_CAPABILITY_ID_INVALID")
        if not isinstance(verifier, str) or not verifier:
            raise ValueError("TRACE_VERIFIER_ID_INVALID")
        if not isinstance(outputs, list) or not outputs:
            raise ValueError("TRACE_OUTPUTS_INVALID")
        steps.append({
            "op": cid,
            "inputs": ["VERIFIER::" + verifier],
            "outputs": [str(x) for x in outputs],
        })

    digest = skill.program_digest(
        steps=steps,
        preconditions=preconditions,
        postconditions=postconditions,
        invalidators=invalidators,
    )
    return {
        "schema": SCHEMA,
        "status": "EPISODE_CANDIDATE_ONLY",
        "episode_id": episode_id.strip(),
        "scope_id": scope_id.strip(),
        "steps": skill.normalize_steps(steps),
        "preconditions": sorted(set(str(x) for x in preconditions if str(x))),
        "postconditions": sorted(set(str(x) for x in postconditions if str(x))),
        "invalidators": sorted(set(str(x) for x in invalidators if str(x))),
        "program_sha256": digest,
        "solver_trace_proof_digests": [
            str(row.get("proof_digest") or "") for row in trace
        ],
        "verified_episode": False,
        "reuse_authorized": False,
        "terminal_authority": False,
    }


def bind_verified_episode(
    episode_candidate: Mapping[str, Any],
    references: Mapping[str, Any],
    *,
    repo_root: str,
) -> dict[str, Any]:
    receipt = authenticate_episode_receipt(references, repo_root=repo_root)
    if receipt["episode_id"] != episode_candidate.get("episode_id"):
        raise ValueError("EPISODE_RECEIPT_ID_MISMATCH")
    if receipt["scope_id"] != episode_candidate.get("scope_id"):
        raise ValueError("EPISODE_RECEIPT_SCOPE_MISMATCH")
    if receipt["program_sha256"] != episode_candidate.get("program_sha256"):
        raise ValueError("EPISODE_RECEIPT_PROGRAM_MISMATCH")
    return {
        "episode_id": episode_candidate["episode_id"],
        "scope_id": episode_candidate["scope_id"],
        "steps": episode_candidate["steps"],
        "preconditions": episode_candidate.get("preconditions", []),
        "postconditions": episode_candidate.get("postconditions", []),
        "invalidators": episode_candidate.get("invalidators", []),
        "verification_receipt": receipt,
    }


def induce_skill_candidate(verified_episodes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return skill.induce_candidate(verified_episodes)


def bind_verified_skill(
    candidate: Mapping[str, Any],
    references: Mapping[str, Any],
    *,
    repo_root: str,
) -> dict[str, Any]:
    receipt = authenticate_candidate_receipt(references, repo_root=repo_root)
    return skill.verify_candidate(candidate=candidate, verification_receipt=receipt)
