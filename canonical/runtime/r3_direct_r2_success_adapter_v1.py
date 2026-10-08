"""Candidate adapter for independently accepted direct R2 successes.

The adapter is deliberately rule-gated. Root1 may append only a predeclared
route rule to R3_SUCCESS_ADAPTER_RULES_V1.json; the rule grants no verification
or promotion authority. Independent verification is performed by the separate
direct-R2 checkpoint verifier.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.executable_skill_program_v7 import program_digest
from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct

SCHEMA = "PROJECT_BRAIN_R3_DIRECT_R2_SUCCESS_ADAPTER_V1"
VERIFICATION_KIND = "DIRECT_R2_READONLY_ACCEPTANCE_V1"
RULES_PATH = "canonical/runtime/R3_SUCCESS_ADAPTER_RULES_V1.json"
SUPPORTED_ROUTES = frozenset({
    direct.EXACT_LITERAL_ROUTE_ID,
    direct.LITERAL_JSON_ROUTE_ID,
})


def _canon(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False, default=str,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _load_rules(repo_root: str | Path) -> tuple[dict[str, Any], str]:
    root = Path(repo_root).resolve(strict=True)
    target = (root / RULES_PATH).resolve(strict=True)
    target.relative_to(root)
    raw = target.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    if (
        not isinstance(doc, Mapping)
        or doc.get("schema") != "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_RULES_V1"
        or doc.get("version") != 1
        or not isinstance(doc.get("rules"), list)
    ):
        raise ValueError("SUCCESS_ADAPTER_RULE_FRONTIER_INVALID")
    return dict(doc), sha256(raw).hexdigest()


def _active_rule(doc: Mapping[str, Any], route_id: str) -> Mapping[str, Any] | None:
    hits = []
    for row in doc.get("rules") or []:
        if not isinstance(row, Mapping):
            continue
        if (
            row.get("status") == "ACTIVE"
            and row.get("adapter_class") == "DIRECT_R2_READONLY_ACCEPTANCE_V1"
            and row.get("verification_kind") == VERIFICATION_KIND
            and row.get("route_id") == route_id
        ):
            hits.append(row)
    if len(hits) != 1:
        return None
    return hits[0]


def adapt(request: Mapping[str, Any], *, repo_root: str | Path) -> Mapping[str, Any] | None:
    try:
        if not isinstance(request, Mapping):
            return None
        observation = request.get("observation")
        replay = request.get("replay_context")
        if not isinstance(observation, Mapping) or not isinstance(replay, Mapping):
            return None
        if observation.get("surface") != "ADEQUATE_DECISION_DIRECT_SUCCESS":
            return None
        if str(replay.get("mode") or "").strip() != "decision":
            return None

        capsule = observation.get("proof_capsule")
        material = capsule.get("material") if isinstance(capsule, Mapping) else None
        raw_request = replay.get("request")
        if not isinstance(material, Mapping) or not isinstance(raw_request, Mapping):
            return None
        if material.get("proof_kind") != "R2_DIRECT_ADEQUACY_READONLY_REVERIFY_V1":
            return None

        route_id = str(material.get("route_id") or "")
        if route_id not in SUPPORTED_ROUTES:
            return None
        rules, rules_sha = _load_rules(repo_root)
        rule = _active_rule(rules, route_id)
        if rule is None:
            return None

        goal = str(raw_request.get("goal") or "").strip()
        task_id = str(raw_request.get("task_id") or "").strip()
        if not goal or not task_id:
            return None
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        if material.get("goal_sha256") != goal_sha:
            return None
        raw_result = material.get("raw_result")
        acceptance = material.get("acceptance_receipt")
        obligation_ids = material.get("accepted_raw_obligation_ids")
        if (
            not isinstance(raw_result, Mapping)
            or not isinstance(acceptance, Mapping)
            or acceptance.get("pass") is not True
            or acceptance.get("semantic_acceptance_complete") is not True
            or not isinstance(obligation_ids, list)
            or not obligation_ids
        ):
            return None
        if material.get("raw_acceptance_obligation_count") != len(obligation_ids):
            return None

        accepted_effect = "r2.direct.route.accepted:" + route_id
        steps = [{
            "index": 0,
            "op": "R2_DIRECT_ROUTE::" + route_id,
            "inputs": [],
            "outputs": [accepted_effect],
        }]
        episode = {
            "episode_id": "direct-r2:" + _sha({
                "observation_id": observation.get("observation_id"),
                "goal_sha256": goal_sha,
                "route_id": route_id,
            })[:24],
            "scope_id": "direct-r2-goal-sha256:" + goal_sha,
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
        raw_result_sha = _sha(dict(raw_result))
        acceptance_sha = _sha(dict(acceptance))
        trace = [{
            "cycle": 0,
            "route_id": route_id,
            "goal_sha256": goal_sha,
            "raw_result_sha256": raw_result_sha,
            "acceptance_sha256": acceptance_sha,
            "rules_sha256": rules_sha,
            "accepted_effect": accepted_effect,
        }]
        fact_head = _sha({
            "schema": "PROJECT_BRAIN_DIRECT_R2_SUCCESS_FACT_LINEAGE_V1",
            "goal_sha256": goal_sha,
            "route_id": route_id,
            "accepted_effect": accepted_effect,
            "trace": trace,
        })
        value_head = _sha({
            "schema": "PROJECT_BRAIN_DIRECT_R2_SUCCESS_VALUE_LINEAGE_V1",
            "raw_result_sha256": raw_result_sha,
            "acceptance_sha256": acceptance_sha,
            "rules_sha256": rules_sha,
        })
        problem = {
            "task_id": task_id,
            "verification_kind": VERIFICATION_KIND,
            "route_id": route_id,
            "raw_goal": goal,
            "goal_sha256": goal_sha,
            "raw_result": deepcopy(dict(raw_result)),
            "retained_acceptance": deepcopy(dict(acceptance)),
            "accepted_obligation_ids": deepcopy(obligation_ids),
            "raw_acceptance_obligation_count": len(obligation_ids),
            "rules_sha256": rules_sha,
            "rule_id": rule.get("rule_id"),
            "initial_facts": [],
            "target_effects": [accepted_effect],
        }
        return {
            "schema": SCHEMA,
            "status": "DIRECT_R2_SUCCESS_EPISODE_CANDIDATE_READY",
            "problem": problem,
            "solver_output": {
                "pass": True,
                "status": "DIRECT_R2_SUCCESS_EPISODE_CANDIDATE_READY",
                "current_episode": episode,
                "current_episode_verified": False,
                "trace": trace,
                "state_capsule_head_hash": fact_head,
                "value_capsule_head_hash": value_head,
                "skill_candidate": None,
            },
            "candidate_only": True,
            "execution_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
        }
    except Exception:
        return None
