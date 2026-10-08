"""Candidate adapter for durable R2 direct-adequacy successes.

The adapter never replays the original producer and grants no learning authority.
It maps one retained, content-addressed direct-success proof into an exact-goal
episode candidate. Independent read-only verification remains mandatory.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.executable_skill_program_v7 import program_digest

SCHEMA = "PROJECT_BRAIN_R3_DIRECT_ADEQUACY_SUCCESS_ADAPTER_V1"
VERIFICATION_KIND = "R2_DIRECT_ADEQUACY_READBACK_V1"

SUPPORTED_READBACK_ROUTES = frozenset({
    "DIRECT_ADEQUACY::LITERAL_JSON_RECORDS_V1",
    "DIRECT_ADEQUACY::STRUCTURED_TABLE_ARTIFACT_FAMILY_V1",
    "DIRECT_ADEQUACY::LITERAL_DOCX_OOXML_FAMILY_V1",
    "DIRECT_ADEQUACY::DOCX_JSON_RECORD_FAMILY_V1",
    "DIRECT_ADEQUACY::TYPED_EVIDENCE_DECISION_FAMILY_V1",
    "DIRECT_ADEQUACY::PLAIN_MARKDOWN_PDF_FAMILY_V1",
    "DIRECT_ADEQUACY::TYPED_JSON_TRANSFORM_FAMILY_V1",
    "DIRECT_ADEQUACY::VISUAL_CODE_QR_CODE128_FAMILY_V1",
})


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _request_from_replay(replay: Mapping[str, Any]) -> Mapping[str, Any] | None:
    raw = replay.get("request")
    if isinstance(raw, Mapping):
        return raw
    payload = replay.get("payload")
    if isinstance(payload, Mapping):
        nested = payload.get("request")
        if isinstance(nested, Mapping):
            return nested
        if isinstance(payload.get("goal"), str) and isinstance(payload.get("task_id"), str):
            return payload
    if isinstance(replay.get("goal"), str) and isinstance(replay.get("task_id"), str):
        return replay
    return None


def adapt(
    request: Mapping[str, Any],
    *,
    repo_root=None,
) -> Mapping[str, Any] | None:
    try:
        if not isinstance(request, Mapping):
            return None
        observation = request.get("observation")
        replay = request.get("replay_context")
        if not isinstance(observation, Mapping) or not isinstance(replay, Mapping):
            return None

        capsule = observation.get("proof_capsule")
        material = capsule.get("material") if isinstance(capsule, Mapping) else None
        expected_capsule_sha = (
            str(capsule.get("sha256") or "")
            if isinstance(capsule, Mapping)
            else ""
        )
        if not isinstance(material, Mapping):
            return None
        if material.get("proof_kind") != VERIFICATION_KIND:
            return None
        if len(expected_capsule_sha) != 64 or _sha(material) != expected_capsule_sha:
            return None

        route_id = str(material.get("route_id") or "").strip()
        if route_id not in SUPPORTED_READBACK_ROUTES:
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

        accepted_ids = material.get("accepted_raw_obligation_ids")
        required_count = material.get("raw_acceptance_obligation_count")
        if (
            not isinstance(accepted_ids, list)
            or not accepted_ids
            or any(not isinstance(x, str) or not x for x in accepted_ids)
            or len(set(accepted_ids)) != len(accepted_ids)
            or not isinstance(required_count, int)
            or isinstance(required_count, bool)
            or required_count != len(accepted_ids)
        ):
            return None

        capability_id = str(material.get("capability_id") or "").strip() or None
        accepted_effect = "r2.direct.accepted.sha256:" + goal_sha
        op = capability_id or route_id
        steps = [{
            "index": 0,
            "op": op,
            "inputs": [],
            "outputs": [accepted_effect],
        }]
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
            "capability_id": capability_id,
            "goal_sha256": goal_sha,
            "proof_capsule_sha256": expected_capsule_sha,
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
            "proof_capsule_sha256": expected_capsule_sha,
            "accepted_obligation_ids": accepted_ids,
        })
        problem = {
            "task_id": task_id,
            "verification_kind": VERIFICATION_KIND,
            "raw_request": deepcopy(dict(raw_request)),
            "goal_sha256": goal_sha,
            "route_id": route_id,
            "retained_direct_proof": deepcopy(dict(material)),
            "proof_capsule_sha256": expected_capsule_sha,
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
