"""R3 candidate adapter for verified R2 direct-adequacy successes.

The adapter never executes effects and grants no verification/promotion authority.
It converts an already independently accepted direct R2 success into an exact-goal
episode candidate. The dedicated direct-success verifier must re-read the current
artifact/source state before R3 may persist the episode.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime.executable_skill_program_v7 import program_digest

SCHEMA = "PROJECT_BRAIN_R3_DIRECT_ADEQUACY_SUCCESS_ADAPTER_V1"
VERIFICATION_KIND = "R2_DIRECT_ADEQUACY_READBACK_V1"

SUPPORTED_ROUTE_IDS = frozenset({
    "DIRECT_ADEQUACY::STRUCTURED_BINARY_CODEC_FAMILY_V1",
    "DIRECT_ADEQUACY::STRUCTURED_TABLE_ARTIFACT_FAMILY_V1",
    "DIRECT_ADEQUACY::LITERAL_DOCX_OOXML_FAMILY_V1",
    "DIRECT_ADEQUACY::DOCX_JSON_RECORD_FAMILY_V1",
    "DIRECT_ADEQUACY::TYPED_EVIDENCE_DECISION_FAMILY_V1",
    "DIRECT_ADEQUACY::VISUAL_CODE_QR_CODE128_FAMILY_V1",
    "DIRECT_ADEQUACY::PLAIN_MARKDOWN_PDF_FAMILY_V1",
    "DIRECT_ADEQUACY::TYPED_JSON_TRANSFORM_FAMILY_V1",
})


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _proof_material(observation: Mapping[str, Any]) -> Mapping[str, Any] | None:
    capsule = observation.get("proof_capsule")
    if not isinstance(capsule, Mapping):
        return None
    if capsule.get("schema") != "PROJECT_BRAIN_DIRECT_ADEQUACY_SUCCESS_PROOF_CAPSULE_V1":
        return None
    material = capsule.get("material")
    expected = str(capsule.get("sha256") or "")
    if not isinstance(material, Mapping) or len(expected) != 64:
        return None
    if learning._sha(material) != expected:
        return None
    return material


def adapt(request: Mapping[str, Any], *, repo_root) -> Mapping[str, Any] | None:
    try:
        if not isinstance(request, Mapping):
            return None
        observation = request.get("observation")
        replay = request.get("replay_context")
        if not isinstance(observation, Mapping) or not isinstance(replay, Mapping):
            return None
        if str(observation.get("surface") or "") != "ADEQUATE_DECISION_DIRECT_SUCCESS":
            return None
        if str(replay.get("mode") or "") != "decision":
            return None

        material = _proof_material(observation)
        if not isinstance(material, Mapping):
            return None
        route_id = str(material.get("route_id") or "")
        capability_id = str(material.get("capability_id") or "")
        policy_id = str(material.get("selected_policy_id") or "")
        goal_sha256 = str(material.get("goal_sha256") or "")
        if route_id not in SUPPORTED_ROUTE_IDS:
            return None
        if not capability_id or len(goal_sha256) != 64:
            return None

        raw_request = replay.get("request")
        if not isinstance(raw_request, Mapping):
            return None
        goal = str(raw_request.get("goal") or "")
        task_id = str(raw_request.get("task_id") or "")
        if not goal or not task_id:
            return None
        if sha256(goal.encode("utf-8")).hexdigest() != goal_sha256:
            return None

        proof_sha256 = _sha(dict(material))
        accepted_effect = "r2.direct_adequacy.accepted.sha256:" + goal_sha256
        steps = [{
            "index": 0,
            "op": capability_id,
            "inputs": [],
            "outputs": [accepted_effect],
        }]
        episode = {
            "episode_id": "r2-direct:" + _sha({
                "route_id": route_id,
                "goal_sha256": goal_sha256,
                "capability_id": capability_id,
                "proof_sha256": proof_sha256,
            })[:24],
            "scope_id": "r2-direct-goal-sha256:" + goal_sha256,
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
            "capability_id": capability_id,
            "route_id": route_id,
            "selected_policy_id": policy_id or None,
            "goal_sha256": goal_sha256,
            "accepted_effect": accepted_effect,
            "direct_proof_sha256": str(proof_sha256 or ""),
        }]
        fact_head = _sha({
            "schema": "PROJECT_BRAIN_R3_DIRECT_ADEQUACY_FACT_LINEAGE_V1",
            "route_id": route_id,
            "goal_sha256": goal_sha256,
            "accepted_effect": accepted_effect,
            "trace": trace,
        })
        value_head = _sha({
            "schema": "PROJECT_BRAIN_R3_DIRECT_ADEQUACY_VALUE_LINEAGE_V1",
            "direct_proof_sha256": proof_sha256,
            "accepted_raw_obligation_ids": material.get("accepted_raw_obligation_ids"),
            "raw_acceptance_obligation_count": material.get("raw_acceptance_obligation_count"),
        })
        problem = {
            "task_id": task_id,
            "verification_kind": VERIFICATION_KIND,
            "route_id": route_id,
            "capability_id": capability_id,
            "selected_policy_id": policy_id or None,
            "goal_sha256": goal_sha256,
            "raw_request": deepcopy(dict(raw_request)),
            "direct_proof": deepcopy(dict(material)),
            "accepted_raw_obligation_ids": deepcopy(
                material.get("accepted_raw_obligation_ids") or []
            ),
            "raw_acceptance_obligation_count": material.get(
                "raw_acceptance_obligation_count"
            ),
            "initial_facts": [],
            "target_effects": [accepted_effect],
        }
        return {
            "schema": SCHEMA,
            "status": "DIRECT_ADEQUACY_SUCCESS_EPISODE_CANDIDATE_READY",
            "problem": problem,
            "solver_output": {
                "pass": True,
                "status": "DIRECT_ADEQUACY_SUCCESS_EPISODE_CANDIDATE_READY",
                "current_episode": episode,
                "current_episode_verified": False,
                "trace": trace,
                "state_capsule_head_hash": fact_head,
                "value_capsule_head_hash": value_head,
                "skill_candidate": None,
            },
            "candidate_only": True,
            "execution_replayed": False,
            "execution_authority": False,
            "verification_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
        }
    except Exception:
        return None
