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
from canonical.runtime.live_integrated_brain_v1 import (
    compile_against_live_registry,
    load_verified_registry,
)
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.raw_goal_archive_acceptance_v1 import (
    CAPABILITY as ARCHIVE_CAPABILITY,
    GRAMMAR as ARCHIVE_GOAL_GRAMMAR,
    verify as verify_raw_acceptance,
)
from canonical.runtime.raw_goal_trace_acceptance_v1 import (
    verify as verify_raw_goal_trace_acceptance,
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


def _verify_generic(
    *,
    problem: Mapping[str, Any],
    episode: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    fact_capsule_head_hash: str,
    value_capsule_head_hash: str,
    root: Path,
    goal: str,
    goal_sha: str,
) -> dict[str, Any]:
    """Re-verify an accepted RAW_BOUND success for ANY owned compiled plan.

    The archive branch above is one hard-coded sentence: it matches a regex,
    recompiles one capability, and asks one sentence-specific acceptance
    verifier. Every other goal -- including goals whose semantic acceptance had
    already been independently verified and retained -- was rejected with
    RAW_CAPABILITY_NOT_ADMITTED and could never become verified experience.

    This is the same argument in its general form, and it is strictly
    read-only:

      * the goal text is re-hashed and bound to a freshly recompiled raw task
        contract whose routing target effects are the goal's own selected plan;
      * every capability in that plan must still be a verified owned capability
        in the registry -- the allowlist is the registry, not a constant;
      * the controller checkpoint is re-opened from disk, its sha256 compared,
        its schema/status checked, its per-cycle records checked against the
        selected plan position by position, and its plan digest recomputed with
        the controller's own digest function;
      * the semantic acceptance receipt is re-derived from the checkpoint's own
        recorded results by the GENERIC trace acceptance verifier, which
        re-opens the produced artifacts from disk, and must byte-match the
        receipt retained at acceptance time.

    Nothing is replayed and nothing is believed from the producer.
    """
    selected = problem.get("selected_plan")
    if (
        not isinstance(selected, Sequence)
        or isinstance(selected, (str, bytes))
        or not selected
    ):
        raise ValueError("RAW_SELECTED_PLAN_MISSING")
    selected = [str(x) for x in selected]
    if any(not cid for cid in selected):
        raise ValueError("RAW_SELECTED_PLAN_INVALID")
    if problem.get("selected_capability_id") != selected[-1]:
        raise ValueError("RAW_CAPABILITY_NOT_ADMITTED")

    # Recompile from the goal text with the front door's own single policy
    # function, so the routing target effects are re-derived rather than taken
    # on trust from the retained problem.
    registry, _admissible, compiled = compile_against_live_registry(goal, root)
    for cid in selected:
        if not isinstance(registry.get(cid), Mapping):
            raise ValueError("RAW_CAPABILITY_NO_LONGER_VERIFIED_OWNED")

    routing_targets = list(compiled.get("target_effects") or [])
    if not routing_targets:
        for part in compiled.get("compiled_parts") or []:
            if isinstance(part, Mapping):
                for effect in part.get("target_effects") or []:
                    if isinstance(effect, str) and effect and effect not in routing_targets:
                        routing_targets.append(effect)
    if not routing_targets:
        raise ValueError("RAW_ROUTING_TARGET_EFFECTS_MISSING")

    raw_contract = compile_contract(
        goal,
        source_id="user",
        routing_target_effects=routing_targets,
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
    if not isinstance(completed, list) or len(completed) != len(selected) + 1:
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
        plan = row["plan"]
        args = plan.get("args") if isinstance(plan.get("args"), Mapping) else None
        if index < len(selected):
            if not isinstance(args, Mapping) or args.get("capability_id") != selected[index]:
                raise ValueError("CHECKPOINT_ACTION_CAPABILITY_MISMATCH")
        elif plan.get("type") != "finish":
            raise ValueError("CHECKPOINT_FINISH_MISMATCH")
        # The digest is over the DECLARED plan, exactly as the bound checkpoint
        # verifier does: the runtime may rewrite an action as it executes it, and
        # the controller's own recorded plan_sha256 is over what was declared.
        declared = row.get("declared_plan")
        plans.append(deepcopy(dict(declared if isinstance(declared, Mapping) else plan)))
    plan_sha = astra_runtime._controller_plan_sha256(plans)
    if plan_sha != problem.get("controller_plan_sha256") or doc.get("plan_sha256") != plan_sha:
        raise ValueError("CHECKPOINT_PLAN_SHA_MISMATCH")

    acceptance = verify_raw_goal_trace_acceptance(
        goal=goal,
        compiled_plan=compiled,
        execution=deepcopy(completed),
        raw_contract=raw_contract,
        root=root,
    )
    if (
        not isinstance(acceptance, Mapping)
        or acceptance.get("pass") is not True
        or acceptance.get("semantic_acceptance_complete") is not True
    ):
        raise ValueError(
            "RAW_SEMANTIC_ACCEPTANCE_READBACK_FAILED:"
            + str((acceptance or {}).get("reason") or "")
        )
    retained = problem.get("retained_acceptance")
    if not isinstance(retained, Mapping) or _canon(dict(retained)) != _canon(dict(acceptance)):
        raise ValueError("RAW_ACCEPTANCE_RECEIPT_MISMATCH")
    if sorted(problem.get("accepted_obligation_ids") or []) != sorted(
        acceptance.get("accepted_obligation_ids") or []
    ):
        raise ValueError("RAW_ACCEPTED_OBLIGATION_SET_MISMATCH")

    accepted_effect = "raw_goal.accepted.sha256:" + goal_sha
    expected_steps = [{
        "index": index,
        "op": cid,
        "inputs": [],
        "outputs": [accepted_effect] if index == len(selected) - 1 else [],
    } for index, cid in enumerate(selected)]
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
        "capability_id": selected[-1],
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
        "generic_owned_plan_verified": True,
        "selected_plan": list(selected),
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
        selected_plan = problem.get("selected_plan")
        is_archive_sentence = (
            problem.get("selected_capability_id") == ARCHIVE_CAPABILITY
            and selected_plan in (None, [ARCHIVE_CAPABILITY])
        )
        if not is_archive_sentence:
            # Every other owned plan is verified by the general read-only
            # argument rather than being refused outright.
            return _verify_generic(
                problem=problem,
                episode=episode,
                trace=trace,
                fact_capsule_head_hash=fact_capsule_head_hash,
                value_capsule_head_hash=value_capsule_head_hash,
                root=root,
                goal=goal,
                goal_sha=goal_sha,
            )

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
