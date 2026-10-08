"""Independent read-only verifier for rule-adapted direct R2 successes."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.executable_skill_program_v7 import program_digest, normalize_steps
from canonical.runtime import raw_goal_exact_literal_acceptance_v1 as literal_acceptance
from canonical.runtime import raw_goal_literal_json_acceptance_v1 as literal_json_acceptance
from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct
from canonical.runtime.r3_direct_r2_success_adapter_v1 import (
    VERIFICATION_KIND, RULES_PATH,
)

SCHEMA = "PROJECT_BRAIN_R3_DIRECT_R2_SUCCESS_CHECKPOINT_VERIFIER_V1"
NON_EFFECTFUL_VERIFICATION_BASIS = "SEPARATE_R3_EVIDENCE_RECOMPUTATION_WORKER"
EFFECTFUL_READBACK_VERIFICATION_BASIS = (
    "SEPARATE_R3_EVIDENCE_RECOMPUTATION_PLUS_EFFECT_READBACK_V1"
)


def _canon(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False, default=str,
    )


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED__DIRECT_R2_SUCCESS_NOT_REVERIFIED",
        "pass": False,
        "reason": reason,
        "execution_replayed": False,
        "terminal_authority": False,
    }


def _current_rules_sha(repo_root: str | Path) -> str:
    root = Path(repo_root).resolve(strict=True)
    target = (root / RULES_PATH).resolve(strict=True)
    target.relative_to(root)
    return sha256(target.read_bytes()).hexdigest()


def verify_material(
    *,
    problem: Mapping[str, Any],
    episode: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    fact_capsule_head_hash: str,
    value_capsule_head_hash: str,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        if problem.get("verification_kind") != VERIFICATION_KIND:
            raise ValueError("VERIFICATION_KIND_INVALID")
        route_id = str(problem.get("route_id") or "")
        if route_id not in {
            direct.EXACT_LITERAL_ROUTE_ID,
            direct.LITERAL_JSON_ROUTE_ID,
        }:
            raise ValueError("DIRECT_R2_ROUTE_NOT_ADMITTED")

        goal = str(problem.get("raw_goal") or "")
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        if not goal or problem.get("goal_sha256") != goal_sha:
            raise ValueError("RAW_GOAL_HASH_MISMATCH")
        raw_result = problem.get("raw_result")
        retained = problem.get("retained_acceptance")
        if not isinstance(raw_result, Mapping) or not isinstance(retained, Mapping):
            raise ValueError("DIRECT_R2_RETAINED_MATERIAL_INVALID")

        if route_id == direct.EXACT_LITERAL_ROUTE_ID:
            acceptance = literal_acceptance.verify(goal=goal, raw_result=raw_result)
            non_effectful = True
            artifact_readback = False
            basis = NON_EFFECTFUL_VERIFICATION_BASIS
        else:
            acceptance = literal_json_acceptance.verify(goal=goal, raw_result=raw_result)
            non_effectful = False
            artifact_readback = True
            basis = EFFECTFUL_READBACK_VERIFICATION_BASIS

        if (
            acceptance.get("pass") is not True
            or acceptance.get("semantic_acceptance_complete") is not True
            or acceptance.get("actual_goal_satisfaction_verified") is not True
        ):
            raise ValueError("DIRECT_R2_ACCEPTANCE_RECOMPUTATION_FAILED")
        if _canon(dict(retained)) != _canon(dict(acceptance)):
            raise ValueError("DIRECT_R2_ACCEPTANCE_RECEIPT_MISMATCH")
        accepted_ids = list(acceptance.get("accepted_obligation_ids") or [])
        if accepted_ids != list(problem.get("accepted_obligation_ids") or []):
            raise ValueError("DIRECT_R2_ACCEPTED_OBLIGATION_SET_MISMATCH")
        if problem.get("raw_acceptance_obligation_count") != len(accepted_ids):
            raise ValueError("DIRECT_R2_ACCEPTANCE_COUNT_MISMATCH")

        rules_sha = _current_rules_sha(repo_root)
        if rules_sha != problem.get("rules_sha256"):
            raise ValueError("SUCCESS_ADAPTER_RULE_FRONTIER_CHANGED")

        accepted_effect = "r2.direct.route.accepted:" + route_id
        expected_steps = [{
            "index": 0,
            "op": "R2_DIRECT_ROUTE::" + route_id,
            "inputs": [],
            "outputs": [accepted_effect],
        }]
        if normalize_steps(episode.get("steps")) != normalize_steps(expected_steps):
            raise ValueError("EPISODE_STEPS_MISMATCH")
        if list(episode.get("preconditions") or []) != []:
            raise ValueError("EPISODE_PRECONDITIONS_MISMATCH")
        if list(episode.get("postconditions") or []) != [accepted_effect]:
            raise ValueError("EPISODE_POSTCONDITIONS_MISMATCH")
        if list(episode.get("invalidators") or []) != []:
            raise ValueError("EPISODE_INVALIDATORS_NOT_EMPTY")
        expected_program = program_digest(
            steps=expected_steps,
            preconditions=[],
            postconditions=[accepted_effect],
            invalidators=[],
        )
        if episode.get("program_sha256") != expected_program:
            raise ValueError("EPISODE_PROGRAM_DIGEST_MISMATCH")
        if episode.get("scope_id") != "direct-r2-goal-sha256:" + goal_sha:
            raise ValueError("EPISODE_SCOPE_NOT_EXACT_RAW_GOAL")

        raw_result_sha = _sha(dict(raw_result))
        acceptance_sha = _sha(dict(acceptance))
        expected_trace = [{
            "cycle": 0,
            "route_id": route_id,
            "goal_sha256": goal_sha,
            "raw_result_sha256": raw_result_sha,
            "acceptance_sha256": acceptance_sha,
            "rules_sha256": rules_sha,
            "accepted_effect": accepted_effect,
        }]
        if _canon(list(trace)) != _canon(expected_trace):
            raise ValueError("EPISODE_TRACE_MISMATCH")
        expected_fact = _sha({
            "schema": "PROJECT_BRAIN_DIRECT_R2_SUCCESS_FACT_LINEAGE_V1",
            "goal_sha256": goal_sha,
            "route_id": route_id,
            "accepted_effect": accepted_effect,
            "trace": expected_trace,
        })
        expected_value = _sha({
            "schema": "PROJECT_BRAIN_DIRECT_R2_SUCCESS_VALUE_LINEAGE_V1",
            "raw_result_sha256": raw_result_sha,
            "acceptance_sha256": acceptance_sha,
            "rules_sha256": rules_sha,
        })
        if fact_capsule_head_hash != expected_fact:
            raise ValueError("FACT_LINEAGE_MISMATCH")
        if value_capsule_head_hash != expected_value:
            raise ValueError("VALUE_LINEAGE_MISMATCH")

        return {
            "schema": SCHEMA,
            "status": "PASS__DIRECT_R2_SUCCESS_REVERIFIED_READONLY",
            "pass": True,
            "verification_basis": basis,
            "execution_replayed": False,
            "semantic_acceptance_reverified": True,
            "artifact_bytes_reverified": artifact_readback,
            "non_effectful_trace": non_effectful,
            "exact_raw_goal_scope": True,
            "terminal_authority": False,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
