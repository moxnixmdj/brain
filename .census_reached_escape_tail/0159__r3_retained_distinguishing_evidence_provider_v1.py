"""Brain-owned retained-evidence provider for R3 verification-frontier gaps.

This provider does not create truth. It may only reconstruct fields explicitly
requested by an authenticated distinguishing-evidence request from already
retained Brain-owned proof/replay capsules and an authenticated controller
checkpoint. Returned material is candidate-only and must re-enter the ordinary
R3 proof capture + independent verification pipeline.

The provider never replays effects, never edits verification authority, and
never promotes a capability or skill.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import astra_runtime
from canonical.runtime import autonomous_verified_self_improvement_v1 as learning

SCHEMA = "PROJECT_BRAIN_R3_RETAINED_DISTINGUISHING_EVIDENCE_PROVIDER_V1"
PROVIDER_ID = "BRAIN_NATIVE_RETAINED_DISTINGUISHING_EVIDENCE_PROVIDER_V1"
CANDIDATE_SCHEMA = "PROJECT_BRAIN_R3_DISTINGUISHING_EVIDENCE_CANDIDATE_V1"
REQUEST_KIND = "R3_VERIFICATION_FRONTIER_DISTINGUISHING_EVIDENCE"
CHECKPOINT_ROUTE = "CHECKPOINTED_VERIFIED_EXECUTION"
RAW_ROUTE = "SEMANTICALLY_ACCEPTED_RAW_SUCCESS"

_CHECKPOINT_OBLIGATIONS = {
    "NONEMPTY_SELECTED_PLAN",
    "NONEMPTY_VERIFIED_TARGET_EFFECT_SET",
    "CONTROLLER_CHECKPOINT_BOUND",
    "EXECUTION_COUNT_MATCHES_SELECTED_PLAN_AND_NONZERO",
    "ALL_EXECUTION_ROWS_PASS",
    "COMPOSITION_DIGEST_PRESENT_FOR_EVERY_EXECUTION_ROW",
}
_RAW_OBLIGATIONS = {
    "SEMANTIC_ACCEPTANCE_COMPLETE",
    "RAW_GOAL_DIGEST_BOUND",
    "RAW_TASK_CONTRACT_DIGEST_BOUND",
    "RAW_GOAL_ACCEPTANCE_BINDING_PRESENT",
    "RAW_ACCEPTANCE_OBLIGATION_COUNT_POSITIVE",
    "ALL_RAW_ACCEPTANCE_OBLIGATIONS_ACCEPTED",
}


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "NO_RETAINED_DISTINGUISHING_EVIDENCE",
        "pass": False,
        "reason": reason,
        "candidate_generation_authority": False,
        "provider_truth_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _items(value: Any, *, allow_empty: bool = False) -> list[str] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return None
    out: list[str] = []
    for raw in value:
        item = str(raw or "").strip()
        if not item:
            return None
        if item not in out:
            out.append(item)
    if not allow_empty and not out:
        return None
    return out


def _replay_request(replay: Mapping[str, Any]) -> Mapping[str, Any]:
    context = replay.get("context")
    if not isinstance(context, Mapping):
        return {}
    raw = context.get("request")
    if isinstance(raw, Mapping):
        return raw
    raw = context.get("problem")
    return raw if isinstance(raw, Mapping) else {}


def _safe_checkpoint(
    binding: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> tuple[Mapping[str, Any], list[Mapping[str, Any]]] | None:
    relative = str(binding.get("path") or "").strip()
    plan_sha256 = str(binding.get("plan_sha256") or "").strip()
    if not relative or len(plan_sha256) != 64:
        return None
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    try:
        root = Path(repo_root).resolve(strict=True)
        target = (root / rel).resolve(strict=True)
        target.relative_to(root)
    except Exception:
        return None
    if not target.is_file() or target.is_symlink():
        return None
    try:
        doc = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return None
    if (
        not isinstance(doc, Mapping)
        or doc.get("schema") != "PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1"
        or doc.get("status") != "COMPLETE"
        or doc.get("plan_sha256") != plan_sha256
    ):
        return None
    completed = doc.get("completed_actions")
    if not isinstance(completed, list) or len(completed) < 2:
        return None
    plans: list[Mapping[str, Any]] = []
    for row in completed:
        if not isinstance(row, Mapping) or not isinstance(row.get("plan"), Mapping):
            return None
        plans.append(row["plan"])
    try:
        recomputed = astra_runtime._controller_plan_sha256(
            [deepcopy(dict(plan)) for plan in plans]
        )
    except Exception:
        return None
    if recomputed != plan_sha256:
        return None
    if plans[-1].get("type") != "finish":
        return None
    return doc, [row for row in completed if isinstance(row, Mapping)]


def _checkpoint_evidence(
    material: Mapping[str, Any],
    replay: Mapping[str, Any],
    missing: set[str],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    raw_request = _replay_request(replay)

    binding = material.get("controller_checkpoint")
    if not isinstance(binding, Mapping):
        candidate = raw_request.get("controller_checkpoint")
        binding = candidate if isinstance(candidate, Mapping) else None
    checked = (
        _safe_checkpoint(binding, repo_root=repo_root)
        if isinstance(binding, Mapping)
        else None
    )

    selected: list[str] | None = None
    execution: list[dict[str, Any]] | None = None
    if checked is not None:
        _doc, completed = checked
        selected = []
        execution = []
        for row in completed[:-1]:
            plan = row.get("plan")
            result = row.get("result")
            if (
                not isinstance(plan, Mapping)
                or plan.get("type") != "invoke_verified_bound_capability_adapter"
                or not isinstance(result, Mapping)
                or result.get("pass") is not True
            ):
                selected = None
                execution = None
                break
            args = plan.get("args")
            if not isinstance(args, Mapping):
                selected = None
                execution = None
                break
            capability_id = str(args.get("capability_id") or "").strip()
            composition = str(
                result.get("composition_capsule_head_hash") or ""
            ).strip()
            if not capability_id or len(composition) != 64:
                selected = None
                execution = None
                break
            selected.append(capability_id)
            execution.append({
                "capability_id": capability_id,
                "pass": True,
                "status": str(result.get("status") or "").strip() or None,
                "composition_capsule_head_hash": composition,
                "result_sha256": (
                    str(result.get("result_sha256") or "").strip() or None
                ),
            })

    if "NONEMPTY_SELECTED_PLAN" in missing and selected:
        evidence["selected_plan"] = selected

    if "NONEMPTY_VERIFIED_TARGET_EFFECT_SET" in missing:
        targets = _items(raw_request.get("target_effects"))
        if targets is not None:
            evidence["verified_target_effects"] = targets

    if "CONTROLLER_CHECKPOINT_BOUND" in missing and isinstance(binding, Mapping):
        if checked is not None:
            evidence["controller_checkpoint"] = deepcopy(dict(binding))

    if missing & {
        "EXECUTION_COUNT_MATCHES_SELECTED_PLAN_AND_NONZERO",
        "ALL_EXECUTION_ROWS_PASS",
        "COMPOSITION_DIGEST_PRESENT_FOR_EVERY_EXECUTION_ROW",
    }:
        if execution:
            evidence["execution"] = execution

    return evidence


def _raw_evidence(
    material: Mapping[str, Any],
    replay: Mapping[str, Any],
    missing: set[str],
) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    raw_request = _replay_request(replay)
    goal = str(raw_request.get("goal") or "")
    acceptance = material.get("raw_goal_acceptance")
    acceptance = acceptance if isinstance(acceptance, Mapping) else None

    if "SEMANTIC_ACCEPTANCE_COMPLETE" in missing and acceptance is not None:
        if (
            acceptance.get("pass") is True
            and acceptance.get("semantic_acceptance_complete") is True
        ):
            evidence["semantic_acceptance_complete"] = True

    if "RAW_GOAL_DIGEST_BOUND" in missing and goal:
        evidence["raw_goal_sha256"] = sha256(goal.encode("utf-8")).hexdigest()

    if "RAW_TASK_CONTRACT_DIGEST_BOUND" in missing and acceptance is not None:
        digest = str(acceptance.get("task_contract_sha256") or "").strip()
        if len(digest) == 64:
            evidence["raw_task_contract_sha256"] = digest

    # A missing acceptance receipt cannot be recreated from its own consequences.
    # If it is absent from retained material, this provider leaves that obligation
    # open rather than manufacturing a replacement.
    if "RAW_GOAL_ACCEPTANCE_BINDING_PRESENT" in missing:
        pass

    accepted_ids = None
    if acceptance is not None:
        accepted_ids = _items(
            acceptance.get("accepted_obligation_ids"),
            allow_empty=True,
        )
        if accepted_ids == []:
            accepted_ids = None

    if "RAW_ACCEPTANCE_OBLIGATION_COUNT_POSITIVE" in missing:
        if accepted_ids:
            evidence["raw_acceptance_obligation_count"] = len(accepted_ids)

    if "ALL_RAW_ACCEPTANCE_OBLIGATIONS_ACCEPTED" in missing:
        if accepted_ids:
            evidence["accepted_raw_obligation_ids"] = accepted_ids

    return evidence


def _candidate(
    compiled_request: Mapping[str, Any],
    *,
    observation_id: str,
    state_path: str | Path,
    repo_root: str | Path,
) -> dict[str, Any] | None:
    if (
        not isinstance(compiled_request, Mapping)
        or compiled_request.get("pass") is not True
        or compiled_request.get("schema")
        != "PROJECT_BRAIN_R3_DISTINGUISHING_EVIDENCE_REQUEST_V1"
    ):
        return None
    rows = compiled_request.get("candidate_evidence_bundles")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        return None
    oid = str(observation_id or "").strip()
    if not oid:
        return None
    try:
        proof = learning.get_success_proof_context(oid, state_path=state_path)
        replay = learning.get_success_replay_context(oid, state_path=state_path)
    except Exception:
        return None
    material = proof.get("material")
    if not isinstance(material, Mapping):
        return None

    candidates: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        route = str(row.get("route") or "").strip()
        obligations = row.get("missing_obligations")
        if (
            not isinstance(obligations, Sequence)
            or isinstance(obligations, (str, bytes, bytearray))
        ):
            continue
        missing = {str(x or "").strip() for x in obligations if str(x or "").strip()}
        if route == CHECKPOINT_ROUTE and missing <= _CHECKPOINT_OBLIGATIONS:
            evidence = _checkpoint_evidence(
                material,
                replay,
                missing,
                repo_root=repo_root,
            )
        elif route == RAW_ROUTE and missing <= _RAW_OBLIGATIONS:
            evidence = _raw_evidence(material, replay, missing)
        else:
            continue
        if evidence:
            candidates.append({
                "route": route,
                "evidence": evidence,
                "reconstructed_field_count": len(evidence),
            })
    if not candidates:
        return None
    candidates.sort(
        key=lambda row: (
            -int(row["reconstructed_field_count"]),
            str(row["route"]),
        )
    )
    return candidates[0]


def can_acquire(
    compiled_request: Mapping[str, Any],
    *,
    observation_id: str,
    state_path: str | Path,
    repo_root: str | Path,
) -> bool:
    try:
        return _candidate(
            compiled_request,
            observation_id=observation_id,
            state_path=state_path,
            repo_root=repo_root,
        ) is not None
    except Exception:
        return False


def acquire(
    provider_request: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    if not isinstance(provider_request, Mapping):
        return _fail("PROVIDER_REQUEST_NOT_OBJECT")
    if provider_request.get("kind") != REQUEST_KIND:
        return _fail("PROVIDER_REQUEST_KIND_NOT_ADMITTED")
    compiled = provider_request.get("distinguishing_evidence_request")
    if not isinstance(compiled, Mapping):
        return _fail("DISTINGUISHING_EVIDENCE_REQUEST_MISSING")
    request_sha = str(provider_request.get("request_sha256") or "").strip()
    if not request_sha or request_sha != str(compiled.get("request_sha256") or "").strip():
        return _fail("DISTINGUISHING_EVIDENCE_REQUEST_BINDING_MISMATCH")
    oid = str(provider_request.get("observation_id") or "").strip()
    candidate = _candidate(
        compiled,
        observation_id=oid,
        state_path=state_path,
        repo_root=repo_root,
    )
    if not isinstance(candidate, Mapping):
        return _fail("NO_REQUESTED_RETAINED_EVIDENCE_RECONSTRUCTABLE")
    return {
        "schema": CANDIDATE_SCHEMA,
        "status": "PASS__RETAINED_DISTINGUISHING_EVIDENCE_CANDIDATE",
        "pass": True,
        "request_sha256": request_sha,
        "route": candidate["route"],
        "evidence": deepcopy(dict(candidate["evidence"])),
        "provider_id": PROVIDER_ID,
        "evidence_origin": (
            "BRAIN_OWNED_AUTHENTICATED_RETAINED_PROOF_REPLAY_AND_CHECKPOINT_ONLY"
        ),
        "candidate_generation_authority": True,
        "provider_truth_authority": False,
        "truth_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
