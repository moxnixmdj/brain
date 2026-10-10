"""Candidate adapter for independently accepted RAW_BOUND successes.

Only semantically-complete raw successes are admitted. This module grants no
learning authority; it converts retained proof into an episode candidate for the
independent R3 verifier.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.executable_skill_program_v7 import program_digest
from canonical.runtime.raw_goal_archive_acceptance_v1 import CAPABILITY as ARCHIVE_CAPABILITY

SCHEMA = "PROJECT_BRAIN_R3_RAW_ACCEPTED_SUCCESS_ADAPTER_V1"
VERIFICATION_KIND = "RAW_ACCEPTED_CHECKPOINT_READBACK_V1"


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _safe_file(root: Path, relative: str) -> tuple[Path, bytes]:
    rel = Path(str(relative or "").strip())
    if not rel.as_posix() or rel.is_absolute() or ".." in rel.parts:
        raise ValueError("CHECKPOINT_PATH_INVALID")
    target = (root / rel).resolve(strict=True)
    target.relative_to(root)
    if not target.is_file() or target.is_symlink():
        raise ValueError("CHECKPOINT_FILE_INVALID")
    return target, target.read_bytes()


def adapt(request: Mapping[str, Any], *, repo_root: str | Path) -> Mapping[str, Any] | None:
    try:
        if not isinstance(request, Mapping):
            return None
        observation = request.get("observation")
        replay = request.get("replay_context")
        if not isinstance(observation, Mapping) or not isinstance(replay, Mapping):
            return None
        if str(replay.get("mode") or "").strip() != "raw_bound":
            return None

        capsule = observation.get("proof_capsule")
        material = capsule.get("material") if isinstance(capsule, Mapping) else None
        raw_request = replay.get("request")
        if not isinstance(material, Mapping) or not isinstance(raw_request, Mapping):
            return None
        if material.get("semantic_acceptance_complete") is not True:
            return None

        acceptance = material.get("raw_goal_acceptance")
        if (
            not isinstance(acceptance, Mapping)
            or acceptance.get("pass") is not True
            or acceptance.get("semantic_acceptance_complete") is not True
        ):
            return None

        goal = str(raw_request.get("goal") or "").strip()
        task_id = str(raw_request.get("task_id") or material.get("task_id") or "").strip()
        if not goal or not task_id:
            return None
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        if material.get("raw_goal_sha256") != goal_sha:
            return None
        if acceptance.get("goal_sha256") != goal_sha:
            return None
        if acceptance.get("task_contract_sha256") != material.get("raw_task_contract_sha256"):
            return None

        selected = material.get("selected_plan")
        if not isinstance(selected, Sequence) or isinstance(selected, (str, bytes)):
            return None
        selected = [str(x) for x in selected]
        if selected != [ARCHIVE_CAPABILITY]:
            return None

        checkpoint = material.get("controller_checkpoint")
        if not isinstance(checkpoint, Mapping):
            return None
        checkpoint_path = str(checkpoint.get("path") or "").strip()
        plan_sha = str(checkpoint.get("plan_sha256") or "").strip()
        if len(plan_sha) != 64:
            return None
        root = Path(repo_root).resolve(strict=True)
        _, raw_checkpoint = _safe_file(root, checkpoint_path)

        obligation_ids = material.get("accepted_raw_obligation_ids")
        if not isinstance(obligation_ids, list) or not obligation_ids:
            return None
        if sorted(obligation_ids) != sorted(acceptance.get("accepted_obligation_ids") or []):
            return None
        if material.get("raw_acceptance_obligation_count") != len(obligation_ids):
            return None

        accepted_effect = "raw_goal.accepted.sha256:" + goal_sha
        steps = [{
            "index": 0,
            "op": ARCHIVE_CAPABILITY,
            "inputs": [],
            "outputs": [accepted_effect],
        }]
        episode = {
            "episode_id": "raw-accepted:" + goal_sha[:24],
            "scope_id": "raw-goal-sha256:" + goal_sha,
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
            "capability_id": ARCHIVE_CAPABILITY,
            "goal_sha256": goal_sha,
            "task_contract_sha256": material.get("raw_task_contract_sha256"),
            "acceptance_sha256": _sha(dict(acceptance)),
            "checkpoint_sha256": sha256(raw_checkpoint).hexdigest(),
            "accepted_effect": accepted_effect,
        }]
        fact_head = _sha({
            "schema": "PROJECT_BRAIN_RAW_ACCEPTED_FACT_LINEAGE_V1",
            "goal_sha256": goal_sha,
            "accepted_effect": accepted_effect,
            "trace": trace,
        })
        value_head = _sha({
            "schema": "PROJECT_BRAIN_RAW_ACCEPTED_VALUE_LINEAGE_V1",
            "acceptance_sha256": trace[0]["acceptance_sha256"],
            "checkpoint_sha256": trace[0]["checkpoint_sha256"],
        })
        problem = {
            "task_id": task_id,
            "verification_kind": VERIFICATION_KIND,
            "raw_goal": goal,
            "goal_sha256": goal_sha,
            "raw_task_contract_sha256": material.get("raw_task_contract_sha256"),
            "accepted_obligation_ids": deepcopy(obligation_ids),
            "retained_acceptance": deepcopy(dict(acceptance)),
            "selected_capability_id": ARCHIVE_CAPABILITY,
            "checkpoint_path": checkpoint_path,
            "checkpoint_sha256": trace[0]["checkpoint_sha256"],
            "controller_plan_sha256": plan_sha,
            "initial_facts": [],
            "target_effects": [accepted_effect],
        }
        return {
            "schema": SCHEMA,
            "status": "RAW_ACCEPTED_SUCCESS_EPISODE_CANDIDATE_READY",
            "problem": problem,
            "solver_output": {
                "pass": True,
                "status": "RAW_ACCEPTED_SUCCESS_EPISODE_CANDIDATE_READY",
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
