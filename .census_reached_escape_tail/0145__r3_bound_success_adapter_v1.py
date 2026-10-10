"""Candidate adapter for checkpoint-verifiable compiled-bound successes.

This module grants no learning authority. It only converts a retained successful
compiled-bound observation into the canonical episode-shaped material consumed by
R3's independent verifier. Only the COMPILED_BOUND surface is admitted in V1.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.executable_skill_program_v7 import program_digest

SCHEMA = "PROJECT_BRAIN_R3_BOUND_SUCCESS_ADAPTER_V1"
VERIFICATION_KIND = "BOUND_CONTROLLER_CHECKPOINT_V1"


class BoundSuccessAdapterError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _items(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise BoundSuccessAdapterError(label + "_INVALID")
    out: list[str] = []
    for raw in value:
        item = str(raw or "").strip()
        if not item:
            raise BoundSuccessAdapterError(label + "_ITEM_INVALID")
        if item not in out:
            out.append(item)
    if not allow_empty and not out:
        raise BoundSuccessAdapterError(label + "_EMPTY")
    return out


def _safe_checkpoint(root: Path, relative: str) -> tuple[Path, bytes, Mapping[str, Any]]:
    rel = Path(str(relative or "").strip())
    if not rel.as_posix() or rel.is_absolute():
        raise BoundSuccessAdapterError("CHECKPOINT_PATH_INVALID")
    target = (root / rel).resolve(strict=True)
    target.relative_to(root)
    raw = target.read_bytes()
    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, Mapping):
        raise BoundSuccessAdapterError("CHECKPOINT_NOT_OBJECT")
    return target, raw, doc


def _lineage_heads(
    *,
    initial_facts: Sequence[str],
    target_effects: Sequence[str],
    steps: Sequence[Mapping[str, Any]],
    trace: Sequence[Mapping[str, Any]],
) -> tuple[str, str]:
    fact = {
        "schema": "PROJECT_BRAIN_BOUND_SUCCESS_FACT_LINEAGE_V1",
        "initial_facts": list(initial_facts),
        "target_effects": list(target_effects),
        "steps": [dict(x) for x in steps],
    }
    value = {
        "schema": "PROJECT_BRAIN_BOUND_SUCCESS_VALUE_LINEAGE_V1",
        "results": [
            {
                "capability_id": row.get("capability_id"),
                "result_sha256": row.get("result_sha256"),
                "composition_capsule_head_hash": row.get("composition_capsule_head_hash"),
            }
            for row in trace
        ],
    }
    return _sha(fact), _sha(value)


def adapt(request: Mapping[str, Any], *, repo_root: str | Path) -> Mapping[str, Any] | None:
    """Build a candidate episode from existing durable proof; never execute effects."""
    if not isinstance(request, Mapping):
        return None
    observation = request.get("observation")
    replay = request.get("replay_context")
    if not isinstance(observation, Mapping) or not isinstance(replay, Mapping):
        return None
    if str(replay.get("mode") or "").strip() != "compiled_bound":
        return None

    capsule = observation.get("proof_capsule")
    material = capsule.get("material") if isinstance(capsule, Mapping) else None
    raw_request = replay.get("request")
    if not isinstance(material, Mapping) or not isinstance(raw_request, Mapping):
        return None

    try:
        selected_plan = _items(material.get("selected_plan"), "SELECTED_PLAN", allow_empty=False)
        initial_facts = _items(raw_request.get("initial_facts", []), "INITIAL_FACTS")
        target_effects = _items(raw_request.get("target_effects"), "TARGET_EFFECTS", allow_empty=False)
        checkpoint = material.get("controller_checkpoint")
        if not isinstance(checkpoint, Mapping):
            raise BoundSuccessAdapterError("CONTROLLER_CHECKPOINT_BINDING_MISSING")
        checkpoint_path = str(checkpoint.get("path") or "").strip()
        plan_sha256 = str(checkpoint.get("plan_sha256") or "").strip()
        if len(plan_sha256) != 64:
            raise BoundSuccessAdapterError("CONTROLLER_PLAN_SHA256_INVALID")

        root = Path(repo_root).resolve(strict=True)
        _, raw_checkpoint, checkpoint_doc = _safe_checkpoint(root, checkpoint_path)
        if checkpoint_doc.get("schema") != "PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1":
            raise BoundSuccessAdapterError("CONTROLLER_CHECKPOINT_SCHEMA_INVALID")
        if checkpoint_doc.get("status") != "COMPLETE":
            raise BoundSuccessAdapterError("CONTROLLER_CHECKPOINT_NOT_COMPLETE")
        if checkpoint_doc.get("plan_sha256") != plan_sha256:
            raise BoundSuccessAdapterError("CONTROLLER_CHECKPOINT_PLAN_MISMATCH")
        completed = checkpoint_doc.get("completed_actions")
        if (
            not isinstance(completed, list)
            or len(completed) != len(selected_plan) + 1
            or not isinstance(completed[-1], Mapping)
            or (completed[-1].get("plan") or {}).get("type") != "finish"
        ):
            raise BoundSuccessAdapterError("CONTROLLER_CHECKPOINT_TRACE_SHAPE_INVALID")

        steps: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        for index, capability_id in enumerate(selected_plan):
            record = completed[index]
            if not isinstance(record, Mapping):
                raise BoundSuccessAdapterError("CONTROLLER_RECORD_INVALID")
            plan = record.get("plan")
            result = record.get("result")
            if not isinstance(plan, Mapping) or plan.get("type") != "invoke_verified_bound_capability_adapter":
                raise BoundSuccessAdapterError("CONTROLLER_RECORD_NOT_VERIFIED_BOUND_ADAPTER")
            args = plan.get("args")
            if not isinstance(args, Mapping) or str(args.get("capability_id") or "") != capability_id:
                raise BoundSuccessAdapterError("CONTROLLER_CAPABILITY_ID_MISMATCH")
            if not isinstance(result, Mapping) or result.get("pass") is not True:
                raise BoundSuccessAdapterError("BOUND_ADAPTER_RESULT_NOT_PASSING")
            requires = _items(args.get("requires", []), "STEP_REQUIRES")
            provides = _items(args.get("provides"), "STEP_PROVIDES", allow_empty=False)
            result_sha = str(result.get("result_sha256") or "").strip()
            composition_head = str(result.get("composition_capsule_head_hash") or "").strip()
            if len(result_sha) != 64 or len(composition_head) != 64:
                raise BoundSuccessAdapterError("BOUND_ADAPTER_PROOF_DIGEST_INVALID")
            steps.append({
                "index": index,
                "op": capability_id,
                "inputs": requires,
                "outputs": provides,
            })
            trace.append({
                "cycle": index,
                "capability_id": capability_id,
                "requires": requires,
                "provides": provides,
                "result_sha256": result_sha,
                "composition_capsule_head_hash": composition_head,
                "effect_outcome_sha256": result_sha,
            })

        fact_head, value_head = _lineage_heads(
            initial_facts=initial_facts,
            target_effects=target_effects,
            steps=steps,
            trace=trace,
        )
        digest = program_digest(
            steps=steps,
            preconditions=initial_facts,
            postconditions=target_effects,
            invalidators=[],
        )
        observation_id = str(observation.get("observation_id") or "").strip()
        if not observation_id:
            raise BoundSuccessAdapterError("OBSERVATION_ID_REQUIRED")
        scope_id = "bound-plan:" + _sha({
            "steps": steps,
            "preconditions": initial_facts,
            "postconditions": target_effects,
        })[:24]
        episode = {
            "episode_id": "bound-success:" + _sha({"observation_id": observation_id})[:24],
            "scope_id": scope_id,
            "steps": steps,
            "preconditions": initial_facts,
            "postconditions": target_effects,
            "invalidators": [],
            "program_sha256": digest,
        }
        problem = {
            "task_id": str(raw_request.get("task_id") or material.get("task_id") or episode["episode_id"]),
            "verification_kind": VERIFICATION_KIND,
            "initial_facts": initial_facts,
            "target_effects": target_effects,
            "selected_plan": selected_plan,
            "checkpoint_path": checkpoint_path,
            "checkpoint_sha256": sha256(raw_checkpoint).hexdigest(),
            "controller_plan_sha256": plan_sha256,
            "compiled_request": deepcopy(dict(raw_request)),
        }
        return {
            "schema": SCHEMA,
            "status": "BOUND_SUCCESS_EPISODE_CANDIDATE_READY",
            "problem": problem,
            "solver_output": {
                "pass": True,
                "status": "BOUND_SUCCESS_EPISODE_CANDIDATE_READY",
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
