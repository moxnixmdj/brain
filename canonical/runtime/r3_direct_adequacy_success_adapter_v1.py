"""Candidate adapter for independently accepted R2 direct-adequacy successes.

This module never replays the original effect and grants no learning authority.
It converts retained direct-adequacy proof plus exact replay intent into an
episode candidate consumed by R3's independent read-only verifier.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.executable_skill_program_v7 import program_digest

SCHEMA = "PROJECT_BRAIN_R3_DIRECT_ADEQUACY_SUCCESS_ADAPTER_V1"
VERIFICATION_KIND = "R2_DIRECT_ADEQUACY_READBACK_V1"


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _request_from_replay(replay: Mapping[str, Any]) -> Mapping[str, Any] | None:
    raw = replay.get("request")
    if isinstance(raw, Mapping):
        return raw
    if isinstance(replay.get("payload"), Mapping):
        raw = replay["payload"]
        if isinstance(raw.get("request"), Mapping):
            return raw["request"]
        if "goal" in raw and "task_id" in raw:
            return raw
    if "goal" in replay and "task_id" in replay:
        return replay
    return None


def adapt(request: Mapping[str, Any], *, repo_root=None) -> Mapping[str, Any] | None:
    try:
        if not isinstance(request, Mapping):
            return None
        observation = request.get("observation")
        replay = request.get("replay_context")
        if not isinstance(observation, Mapping) or not isinstance(replay, Mapping):
            return None
        capsule = observation.get("proof_capsule")
        material = capsule.get("material") if isinstance(capsule, Mapping) else None
        if not isinstance(material, Mapping):
            return None
        if material.get("proof_kind") != VERIFICATION_KIND:
            return None
        raw_request = _request_from_replay(replay)
        if not isinstance(raw_request, Mapping):
            return None
        goal = str(raw_request.get("goal") or "").strip()
        task_id = str(raw_request.get("task_id") or "").strip()
        if not goal or not task_id:
            return None
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        if material.get("goal_sha256") != goal_sha:
            return None
        route_id = str(material.get("route_id") or "").strip()
        accepted_ids = material.get("accepted_raw_obligation_ids")
        required_count = material.get("raw_acceptance_obligation_count")
        if (
            not route_id
            or not isinstance(accepted_ids, list)
            or not accepted_ids
            or not isinstance(required_count, int)
            or isinstance(required_count, bool)
            or required_count != len(accepted_ids)
        ):
            return None
        accepted_effect = "r2.direct.accepted.sha256:" + goal_sha
        op = str(material.get("capability_id") or route_id)
        steps = [{"index": 0, "op": op, "inputs": [], "outputs": [accepted_effect]}]
        episode = {
            "episode_id": "r2-direct:" + goal_sha[:24],
            "scope_id": "r2-direct-goal-sha256:" + goal_sha,
            "steps": steps,
            "preconditions": [],
            "postconditions": [accepted_effect],
            "invalidators": [],
            "program_sha256": program_digest(
                steps=steps,
                preconditions=[],
                postconditions=[accepted_effect],
                invalidators=[],
            ),
        }
        trace = [{
            "cycle": 0,
            "route_id": route_id,
            "capability_id": material.get("capability_id"),
            "goal_sha256": goal_sha,
            "acceptance_sha256": _sha(material.get("acceptance_receipt")),
            "accepted_effect": accepted_effect,
        }]
        fact_head = _sha({
            "schema": "PROJECT_BRAIN_R2_DIRECT_FACT_LINEAGE_V1",
            "goal_sha256": goal_sha,
            "route_id": route_id,
            "accepted_effect": accepted_effect,
        })
        value_head = _sha({
            "schema": "PROJECT_BRAIN_R2_DIRECT_VALUE_LINEAGE_V1",
            "acceptance_sha256": trace[0]["acceptance_sha256"],
            "accepted_obligation_ids": accepted_ids,
        })
        problem = {
            "task_id": task_id,
            "verification_kind": VERIFICATION_KIND,
            "raw_request": deepcopy(dict(raw_request)),
            "goal_sha256": goal_sha,
            "route_id": route_id,
            "retained_direct_proof": deepcopy(dict(material)),
            "initial_facts": [],
            "target_effects": [accepted_effect],
        }
        return {
            "schema": SCHEMA,
            "status": "R2_DIRECT_SUCCESS_EPISODE_CANDIDATE_READY",
            "problem": problem,
            "solver_output": {
                "pass": True,
                "status": "R2_DIRECT_SUCCESS_EPISODE_CANDIDATE_READY",
                "current_episode": episode,
                "current_episode_verified": False,
                "trace": trace,
                "state_capsule_head_hash": fact_head,
                "value_capsule_head_hash": value_head,
                "skill_candidate": None,
            },
            "candidate_only": True,
            "execution_replayed": False,
            "promotion_authority": False,
            "terminal_authority": False,
        }
    except Exception:
        return None
