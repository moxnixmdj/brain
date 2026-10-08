"""Independent read-only verifier for semantically accepted RAW_BOUND successes.

The verifier never replays the original effect. It rechecks the raw goal grammar,
recompiles the raw contract, reauthenticates the controller checkpoint, and asks
the existing raw semantic-acceptance verifier to reinspect current artifact bytes.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import astra_runtime, goal_compiler
from canonical.runtime.executable_skill_program_v7 import program_digest, normalize_steps
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.raw_goal_archive_acceptance_v1 import (
    CAPABILITY as ARCHIVE_CAPABILITY,
    GRAMMAR as ARCHIVE_GOAL_GRAMMAR,
    verify as verify_raw_acceptance,
)
from canonical.runtime.r3_raw_success_adapter_v1 import VERIFICATION_KIND

SCHEMA = "PROJECT_BRAIN_R3_RAW_ACCEPTED_SUCCESS_CHECKPOINT_VERIFIER_V1"
VERIFICATION_BASIS = "RAW_GOAL_CONTRACT_CHECKPOINT_AND_ARTIFACT_READBACK_V1"


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _safe_file(root: Path, relative: str) -> Path:
    rel = Path(str(relative or "").strip())
    if not rel.as_posix() or rel.is_absolute() or ".." in rel.parts:
        raise ValueError("REPOSITORY_PATH_INVALID")
    target = (root / rel).resolve(strict=True)
    target.relative_to(root)
    if not target.is_file() or target.is_symlink():
        raise ValueError("REPOSITORY_FILE_REQUIRED")
    return target


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED__RAW_ACCEPTED_SUCCESS_NOT_REVERIFIED",
        "pass": False,
        "reason": reason,
        "execution_replayed": False,
        "terminal_authority": False,
    }


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
        root = Path(repo_root).resolve(strict=True)
        goal = str(problem.get("raw_goal") or "")
        goal_sha = sha256(goal.encode("utf-8")).hexdigest()
        if not goal or problem.get("goal_sha256") != goal_sha:
            raise ValueError("RAW_GOAL_HASH_MISMATCH")
        if problem.get("selected_capability_id") != ARCHIVE_CAPABILITY:
            raise ValueError("RAW_CAPABILITY_NOT_ADMITTED")

        match = ARCHIVE_GOAL_GRAMMAR.fullmatch(goal)
        if match is None:
            raise ValueError("RAW_GOAL_NO_LONGER_MATCHES_ACCEPTED_GRAMMAR")
        inputs = {
            "manifest_path": match.group("manifest"),
            "output_path": match.group("output"),
        }
        registry = load_verified_registry()
        entry = registry.get(ARCHIVE_CAPABILITY)
        if not isinstance(entry, Mapping):
            raise ValueError("RAW_CAPABILITY_NO_LONGER_VERIFIED_OWNED")
        action_template = entry.get("action_template")
        if not isinstance(action_template, Mapping):
            raise ValueError("RAW_CAPABILITY_ACTION_TEMPLATE_MISSING")

        raw_contract = compile_contract(
            goal,
            source_id="user",
            routing_target_effects=[ARCHIVE_CAPABILITY],
        )
        if raw_contract.get("pass") is not True:
            raise ValueError("RAW_TASK_CONTRACT_RECOMPILATION_FAILED")
        if raw_contract.get("task_sha256") != goal_sha:
            raise ValueError("RAW_TASK_GOAL_BINDING_MISMATCH")
        if raw_contract.get("task_contract_sha256") != problem.get("raw_task_contract_sha256"):
            raise ValueError("RAW_TASK_CONTRACT_DIGEST_MISMATCH")

        checkpoint = _safe_file(root, str(problem.get("checkpoint_path") or ""))
        raw_checkpoint = checkpoint.read_bytes()
        if sha256(raw_checkpoint).hexdigest() != problem.get("checkpoint_sha256"):
            raise ValueError("CHECKPOINT_SHA256_MISMATCH")
        doc = json.loads(raw_checkpoint.decode("utf-8"))
        if (
            not isinstance(doc, Mapping)
            or doc.get("schema") != "PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1"
            or doc.get("status") != "COMPLETE"
        ):
            raise ValueError("CHECKPOINT_NOT_COMPLETE")
        completed = doc.get("completed_actions")
        if not isinstance(completed, list) or len(completed) != 2:
            raise ValueError("CHECKPOINT_ACTION_COUNT_INVALID")
        plans = []
        for index, row in enumerate(completed):
            if (
                not isinstance(row, Mapping)
                or row.get("cycle") != index
                or not isinstance(row.get("plan"), Mapping)
                or not isinstance(row.get("result"), Mapping)
            ):
                raise ValueError("CHECKPOINT_RECORD_INVALID")
            plans.append(deepcopy(dict(row["plan"])))
        plan_sha = astra_runtime._controller_plan_sha256(plans)
        if plan_sha != problem.get("controller_plan_sha256") or doc.get("plan_sha256") != plan_sha:
            raise ValueError("CHECKPOINT_PLAN_SHA_MISMATCH")
        expected_action = goal_compiler._render_template(
            action_template,
            dict(inputs),
        )
        if plans[0] != expected_action:
            raise ValueError("CHECKPOINT_ACTION_RECOMPILATION_MISMATCH")
        if plans[1] != {"type": "finish", "args": {"summary": "RAW_GOAL_COMPLETE"}}:
            raise ValueError("CHECKPOINT_FINISH_MISMATCH")

        execution = {
            "capability_id": ARCHIVE_CAPABILITY,
            "pass": True,
            "status": "PASS__MODEL_INDEPENDENT_CONTROLLER_ACTION",
            "result": deepcopy(dict(completed[0]["result"])),
            "execution_proof_type": "MODEL_INDEPENDENT_CONTROLLER_TRACE_V1",
            "controller_plan_sha256": plan_sha,
            "controller_trace": deepcopy(completed),
        }
        acceptance = verify_raw_acceptance(
            goal=goal,
            capability_id=ARCHIVE_CAPABILITY,
            inputs=inputs,
            execution=execution,
            raw_contract=raw_contract,
            root=root,
        )
        if acceptance.get("pass") is not True or acceptance.get("semantic_acceptance_complete") is not True:
            raise ValueError("RAW_SEMANTIC_ACCEPTANCE_READBACK_FAILED:" + str(acceptance.get("reason") or ""))
        retained = problem.get("retained_acceptance")
        if not isinstance(retained, Mapping) or _canon(dict(retained)) != _canon(dict(acceptance)):
            raise ValueError("RAW_ACCEPTANCE_RECEIPT_MISMATCH")
        if sorted(problem.get("accepted_obligation_ids") or []) != sorted(acceptance.get("accepted_obligation_ids") or []):
            raise ValueError("RAW_ACCEPTED_OBLIGATION_SET_MISMATCH")

        accepted_effect = "raw_goal.accepted.sha256:" + goal_sha
        expected_steps = [{
            "index": 0,
            "op": ARCHIVE_CAPABILITY,
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
        if episode.get("scope_id") != "raw-goal-sha256:" + goal_sha:
            raise ValueError("EPISODE_SCOPE_NOT_EXACT_RAW_GOAL")

        expected_trace = [{
            "cycle": 0,
            "capability_id": ARCHIVE_CAPABILITY,
            "goal_sha256": goal_sha,
            "task_contract_sha256": raw_contract["task_contract_sha256"],
            "acceptance_sha256": _sha(dict(acceptance)),
            "checkpoint_sha256": sha256(raw_checkpoint).hexdigest(),
            "accepted_effect": accepted_effect,
        }]
        if _canon(list(trace)) != _canon(expected_trace):
            raise ValueError("EPISODE_TRACE_MISMATCH")
        expected_fact = _sha({
            "schema": "PROJECT_BRAIN_RAW_ACCEPTED_FACT_LINEAGE_V1",
            "goal_sha256": goal_sha,
            "accepted_effect": accepted_effect,
            "trace": expected_trace,
        })
        expected_value = _sha({
            "schema": "PROJECT_BRAIN_RAW_ACCEPTED_VALUE_LINEAGE_V1",
            "acceptance_sha256": expected_trace[0]["acceptance_sha256"],
            "checkpoint_sha256": expected_trace[0]["checkpoint_sha256"],
        })
        if fact_capsule_head_hash != expected_fact:
            raise ValueError("FACT_LINEAGE_MISMATCH")
        if value_capsule_head_hash != expected_value:
            raise ValueError("VALUE_LINEAGE_MISMATCH")

        return {
            "schema": SCHEMA,
            "status": "PASS__RAW_ACCEPTED_SUCCESS_REVERIFIED_READONLY",
            "pass": True,
            "verification_basis": VERIFICATION_BASIS,
            "execution_replayed": False,
            "semantic_acceptance_reverified": True,
            "artifact_bytes_reverified": True,
            "exact_raw_goal_scope": True,
            "terminal_authority": False,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
