"""Executable consumer for the R3 durable improvement queue.

The queue is not authority. This driver only advances work when the exact
independent-verification or repair authority needed by that work is available.
Unavailable authority leaves work pending with an explicit blocker instead of
silently turning a TODO into a capability claim.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import importlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime.executable_skill_verification_authenticator_v1 import (
    authenticate_and_verify as authenticate_skill_verification,
)

SCHEMA = "PROJECT_BRAIN_R3_IMPROVEMENT_QUEUE_DRIVER_V1"
ROOT = Path(__file__).resolve().parents[2]


class ImprovementDriverError(ValueError):
    pass


def _pending(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    queue = state.get("improvement_queue", {})
    if not isinstance(queue, Mapping):
        raise ImprovementDriverError("IMPROVEMENT_QUEUE_INVALID")
    rows = [
        deepcopy(dict(row))
        for row in queue.values()
        if isinstance(row, Mapping) and row.get("status") == "PENDING"
    ]
    rows.sort(
        key=lambda row: (
            int(row.get("priority", 10**9)),
            -int(row.get("observations", 0)),
            str(row.get("work_id") or ""),
        )
    )
    return rows


def _resolve_work(
    work_id: str,
    *,
    resolved_by: str,
    state_path: str | Path,
) -> None:
    state = learning.load_state(state_path)
    queue = state.get("improvement_queue", {})
    row = queue.get(work_id) if isinstance(queue, Mapping) else None
    if not isinstance(row, dict):
        raise ImprovementDriverError("IMPROVEMENT_WORK_UNKNOWN:" + work_id)
    row["status"] = "RESOLVED"
    row["resolved_by"] = str(resolved_by or "").strip() or "R3_QUEUE_DRIVER"
    learning._refresh_stats(state)
    learning._write_state(state, state_path)


SUCCESS_ADAPTER_FRONTIER_PATHS = (
    "canonical/runtime/r3_bound_success_adapter_v1.py",
    "canonical/runtime/r3_raw_success_adapter_v1.py",
    "canonical/runtime/r3_direct_adequacy_success_adapter_v1.py",
    "canonical/runtime/r3_checkpoint_reconstruction_success_adapter_v1.py",
    "canonical/runtime/r3_structural_bound_success_adapter_v1.py",
    "canonical/runtime/R3_STRUCTURAL_BOUND_ADAPTER_RULES_V1.json",
)
SUCCESS_VERIFICATION_AUTHORITY_PATHS = (
    "canonical/runtime/r3_independent_learning_verifier_v1.py",
    "canonical/runtime/r3_bound_success_checkpoint_verifier_v1.py",
    "canonical/runtime/r3_raw_success_checkpoint_verifier_v1.py",
    "canonical/runtime/r3_direct_adequacy_success_verifier_v1.py",
)
# Preserve historical full-frontier ordering so existing full digests remain stable.
SUCCESS_LEARNING_FRONTIER_PATHS = (
    "canonical/runtime/r3_bound_success_adapter_v1.py",
    "canonical/runtime/r3_independent_learning_verifier_v1.py",
    "canonical/runtime/r3_bound_success_checkpoint_verifier_v1.py",
    "canonical/runtime/r3_raw_success_adapter_v1.py",
    "canonical/runtime/r3_raw_success_checkpoint_verifier_v1.py",
    "canonical/runtime/r3_direct_adequacy_success_adapter_v1.py",
    "canonical/runtime/r3_direct_adequacy_success_verifier_v1.py",
    "canonical/runtime/r3_checkpoint_reconstruction_success_adapter_v1.py",
    "canonical/runtime/r3_structural_bound_success_adapter_v1.py",
    "canonical/runtime/R3_STRUCTURAL_BOUND_ADAPTER_RULES_V1.json",
)

FRONTIER_EXPANSION_KIND = "EXPAND_SUCCESS_VERIFICATION_FRONTIER"
FRONTIER_EXPANSION_PRIORITY = 35

DIRECT_OWNED_OBSERVATION_SCHEMA = "PROJECT_BRAIN_R3_DIRECT_SURFACE_OBSERVATION_V1"
DIRECT_OWNED_SURFACE_PREFIX = "UNIFIED_FABRIC_DIRECT_"


def _enqueue_success_verification_frontier_expansion(
    state: dict[str, Any],
    *,
    blocked_work_id: str,
    observation_id: str,
    frontier_sha256: str,
    adapter_frontier_sha256: str,
    verification_authority_sha256: str,
) -> str:
    """Persist a non-replaying cross-root acquisition handoff for a missing verifier."""
    return learning._enqueue_improvement(
        state,
        kind=FRONTIER_EXPANSION_KIND,
        priority=FRONTIER_EXPANSION_PRIORITY,
        identity={
            "blocked_success_work_id": blocked_work_id,
            "verification_frontier_sha256": frontier_sha256,
        },
        payload={
            "blocked_success_work_id": blocked_work_id,
            "observation_id": observation_id,
            "verification_frontier_sha256": frontier_sha256,
            "adapter_frontier_sha256": adapter_frontier_sha256,
            "verification_authority_sha256": verification_authority_sha256,
            "required_capability_class": (
                "INDEPENDENT_READONLY_SUCCESS_VERIFIER_OR_ADAPTER"
            ),
            "boundary_root": "R1_CAPABILITY_ACQUISITION",
            "replay_original_success": False,
            "candidate_generation_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
        },
    )


def _frontier_sha256(
    paths: Sequence[str],
    *,
    repo_root: str | Path = ROOT,
) -> str:
    root = Path(repo_root).resolve(strict=True)
    rows: list[dict[str, str]] = []
    for relative in paths:
        target = (root / relative).resolve(strict=True)
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ImprovementDriverError(
                "SUCCESS_LEARNING_FRONTIER_PATH_ESCAPES_REPOSITORY"
            ) from exc
        rows.append({
            "path": relative,
            "sha256": sha256(target.read_bytes()).hexdigest(),
        })
    raw = json.dumps(
        rows,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def _owned_success_learning_frontier_sha256(
    *,
    repo_root: str | Path = ROOT,
) -> str:
    return _frontier_sha256(
        SUCCESS_LEARNING_FRONTIER_PATHS,
        repo_root=repo_root,
    )


def _owned_success_adapter_frontier_sha256(
    *,
    repo_root: str | Path = ROOT,
) -> str:
    return _frontier_sha256(
        SUCCESS_ADAPTER_FRONTIER_PATHS,
        repo_root=repo_root,
    )


def _owned_success_verification_authority_sha256(
    *,
    repo_root: str | Path = ROOT,
) -> str:
    return _frontier_sha256(
        SUCCESS_VERIFICATION_AUTHORITY_PATHS,
        repo_root=repo_root,
    )


def _current_frontier_repair_reduction(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Classify one pending frontier handoff without granting repair authority."""
    payload = work.get("payload")
    if not isinstance(payload, Mapping):
        return {
            "pass": False,
            "status": "FRONTIER_REPAIR_REDUCTION_UNAVAILABLE",
            "reason": "FRONTIER_EXPANSION_PAYLOAD_INVALID",
        }
    observation_id = str(payload.get("observation_id") or "").strip()
    blocked_id = str(payload.get("blocked_success_work_id") or "").strip()
    wid = str(work.get("work_id") or "").strip()
    if not observation_id or not blocked_id or not wid:
        return {
            "pass": False,
            "status": "FRONTIER_REPAIR_REDUCTION_UNAVAILABLE",
            "reason": "FRONTIER_HANDOFF_IDENTITY_INCOMPLETE",
        }
    try:
        state = learning.load_state(state_path)
        queue = state.get("improvement_queue")
        observations = state.get("observations")
        if not isinstance(queue, Mapping) or not isinstance(observations, Mapping):
            raise ImprovementDriverError("R3_STATE_INVALID")
        canonical = queue.get(wid)
        if (
            not isinstance(canonical, Mapping)
            or canonical.get("kind") != FRONTIER_EXPANSION_KIND
            or canonical.get("status") != "PENDING"
            or canonical.get("payload") != payload
        ):
            raise ImprovementDriverError("FRONTIER_HANDOFF_NOT_CURRENT_PENDING_WORK")
        blocked = queue.get(blocked_id)
        if (
            not isinstance(blocked, Mapping)
            or blocked.get("kind") != "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE"
            or blocked.get("status") != "PARKED"
            or blocked.get("frontier_expansion_work_id") != wid
            or blocked.get("parked_reason") != "NO_CURRENT_OWNED_VERIFICATION_PATH"
        ):
            raise ImprovementDriverError("BLOCKED_SUCCESS_WORK_NOT_CURRENT_PARKED_ADAPTER_GAP")
        observation = observations.get(observation_id)
        if (
            not isinstance(observation, Mapping)
            or observation.get("observation_id") != observation_id
            or observation.get("learning_disposition_reason")
            != "OWNED_SUCCESS_ADAPTER_RETURNED_NO_CANDIDATE"
            or observation.get("frontier_expansion_work_id") != wid
        ):
            raise ImprovementDriverError("SUCCESS_OBSERVATION_NOT_PROVEN_ADAPTER_FRONTIER_MISS")

        from canonical.runtime import r3_success_adapter_author_context_v1 as author_context
        from canonical.runtime import r3_verification_frontier_repair_reducer_v1 as repair_reducer
        from canonical.runtime import r3_distinguishing_evidence_request_v1 as evidence_request

        proof = learning.get_success_proof_context(
            observation_id,
            state_path=state_path,
        )
        replay = learning.get_success_replay_context(
            observation_id,
            state_path=state_path,
        )
        context = author_context.compile_context(proof, replay)
        if context.get("pass") is not True:
            return {
                "pass": False,
                "status": "FRONTIER_REPAIR_REDUCTION_UNAVAILABLE",
                "reason": "ADAPTER_AUTHOR_CONTEXT_COMPILATION_FAILED",
                "adapter_author_context": deepcopy(dict(context)),
            }
        reduction = repair_reducer.reduce_author_context(context)
        if reduction.get("pass") is not True:
            return {
                "pass": False,
                "status": "FRONTIER_REPAIR_REDUCTION_UNAVAILABLE",
                "reason": "VERIFICATION_FRONTIER_REPAIR_CLASS_REDUCTION_FAILED",
                "repair_class_reduction": deepcopy(dict(reduction)),
            }

        current_adapter = _owned_success_adapter_frontier_sha256(
            repo_root=repo_root,
        )
        current_authority = _owned_success_verification_authority_sha256(
            repo_root=repo_root,
        )
        stored_adapter = str(payload.get("adapter_frontier_sha256") or "")
        stored_authority = str(payload.get("verification_authority_sha256") or "")
        if (
            stored_adapter != current_adapter
            or str(blocked.get("adapter_frontier_sha256") or "") != current_adapter
            or str(observation.get("adapter_frontier_sha256") or "") != current_adapter
        ):
            return {
                "pass": False,
                "status": "FRONTIER_REPAIR_REDUCTION_UNAVAILABLE",
                "reason": "SUCCESS_ADAPTER_FRONTIER_CHANGED",
            }
        if (
            stored_authority != current_authority
            or str(blocked.get("verification_authority_sha256") or "") != current_authority
            or str(observation.get("verification_authority_sha256") or "") != current_authority
        ):
            return {
                "pass": False,
                "status": "FRONTIER_REPAIR_REDUCTION_UNAVAILABLE",
                "reason": "VERIFICATION_AUTHORITY_FRONTIER_CHANGED",
            }
        out = deepcopy(dict(reduction))
        if (
            reduction.get("must_acquire_new_distinguishing_evidence") is True
            and reduction.get("admissible_repair_classes")
            == [repair_reducer.NEW_EVIDENCE]
        ):
            compiled_request = evidence_request.compile_request(context)
            out["distinguishing_evidence_request"] = deepcopy(
                dict(compiled_request)
            )
        return out
    except Exception as exc:
        return {
            "pass": False,
            "status": "FRONTIER_REPAIR_REDUCTION_UNAVAILABLE",
            "reason": type(exc).__name__ + ":" + str(exc),
        }


def _assert_owned_success_module_origin(
    module: Any,
    *,
    relative_path: str,
    repo_root: str | Path = ROOT,
) -> dict[str, str]:
    """Bind an imported frontier module to the exact repository file being hashed."""
    root = Path(repo_root).resolve(strict=True)
    target = (root / relative_path).resolve(strict=True)
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ImprovementDriverError(
            "SUCCESS_FRONTIER_MODULE_PATH_ESCAPES_REPOSITORY:" + relative_path
        ) from exc

    raw_origin = getattr(module, "__file__", None)
    if not isinstance(raw_origin, str) or not raw_origin.strip():
        raise ImprovementDriverError(
            "SUCCESS_FRONTIER_MODULE_ORIGIN_MISSING:" + relative_path
        )
    origin = Path(raw_origin).resolve(strict=True)
    if origin != target:
        raise ImprovementDriverError(
            "SUCCESS_FRONTIER_MODULE_ORIGIN_MISMATCH:"
            + relative_path
            + ":"
            + str(origin)
        )
    return {
        "module": str(getattr(module, "__name__", "") or ""),
        "relative_path": relative_path,
        "origin": str(origin),
    }


def _activate_owned_success_adapter_frontier(
    *,
    expected_adapter_frontier_sha256: str,
    expected_verification_authority_sha256: str,
    repo_root: str | Path = ROOT,
) -> dict[str, Any]:
    """Activate candidate adapters only; the acquisition worker may not rewrite its judge."""
    for value, label in (
        (expected_adapter_frontier_sha256, "EXPECTED_ADAPTER_FRONTIER_SHA256"),
        (expected_verification_authority_sha256, "EXPECTED_VERIFICATION_AUTHORITY_SHA256"),
    ):
        if not isinstance(value, str) or len(value) != 64:
            raise ImprovementDriverError(label + "_INVALID")

    authority_before = _owned_success_verification_authority_sha256(
        repo_root=repo_root,
    )
    if authority_before != expected_verification_authority_sha256:
        raise ImprovementDriverError(
            "SUCCESS_VERIFICATION_AUTHORITY_CHANGED_BEFORE_ADAPTER_ACTIVATION"
        )

    importlib.invalidate_caches()
    from canonical.runtime import r3_bound_success_adapter_v1 as bound_success_adapter
    from canonical.runtime import r3_raw_success_adapter_v1 as raw_success_adapter
    from canonical.runtime import r3_direct_adequacy_success_adapter_v1 as direct_success_adapter
    from canonical.runtime import r3_checkpoint_reconstruction_success_adapter_v1 as checkpoint_success_adapter
    from canonical.runtime import r3_structural_bound_success_adapter_v1 as structural_success_adapter

    modules = (
        (
            bound_success_adapter,
            "canonical/runtime/r3_bound_success_adapter_v1.py",
        ),
        (
            raw_success_adapter,
            "canonical/runtime/r3_raw_success_adapter_v1.py",
        ),
        (
            direct_success_adapter,
            "canonical/runtime/r3_direct_adequacy_success_adapter_v1.py",
        ),
        (
            checkpoint_success_adapter,
            "canonical/runtime/r3_checkpoint_reconstruction_success_adapter_v1.py",
        ),
        (
            structural_success_adapter,
            "canonical/runtime/r3_structural_bound_success_adapter_v1.py",
        ),
    )
    activated: list[dict[str, str]] = []
    for module, relative_path in modules:
        _assert_owned_success_module_origin(
            module,
            relative_path=relative_path,
            repo_root=repo_root,
        )
        reloaded = importlib.reload(module)
        activated.append(
            _assert_owned_success_module_origin(
                reloaded,
                relative_path=relative_path,
                repo_root=repo_root,
            )
        )

    adapter_after = _owned_success_adapter_frontier_sha256(repo_root=repo_root)
    authority_after = _owned_success_verification_authority_sha256(
        repo_root=repo_root,
    )
    if adapter_after != expected_adapter_frontier_sha256:
        raise ImprovementDriverError(
            "SUCCESS_ADAPTER_FRONTIER_CHANGED_DURING_ACTIVATION"
        )
    if authority_after != expected_verification_authority_sha256:
        raise ImprovementDriverError(
            "SUCCESS_VERIFICATION_AUTHORITY_CHANGED_DURING_ADAPTER_ACTIVATION"
        )
    return {
        "schema": SCHEMA,
        "status": "SUCCESS_ADAPTER_FRONTIER_ACTIVATED__VERIFICATION_AUTHORITY_UNCHANGED",
        "pass": True,
        "adapter_frontier_sha256": adapter_after,
        "verification_authority_sha256": authority_after,
        "activated_module_bindings": activated,
        "terminal_authority": False,
    }


def _park_success_work(
    work: Mapping[str, Any],
    *,
    observation_id: str,
    frontier_sha256: str,
    state_path: str | Path,
    repo_root: str | Path,
) -> None:
    """Park a success only relative to the exact currently owned verifier frontier.

    PARKED is deliberately not RESOLVED. New evidence reopens it through the normal
    enqueue path; a verifier-frontier change or an injected external authority also
    reactivates it automatically.
    """
    wid = str(work.get("work_id") or "").strip()
    if not wid:
        raise ImprovementDriverError("SUCCESS_WORK_ID_MISSING")
    state = learning.load_state(state_path)
    queue = state.get("improvement_queue", {})
    row = queue.get(wid) if isinstance(queue, Mapping) else None
    if not isinstance(row, dict) or row.get("status") != "PENDING":
        raise ImprovementDriverError("SUCCESS_WORK_NOT_PENDING:" + wid)
    row["status"] = "PARKED"
    row["parked_reason"] = "NO_CURRENT_OWNED_VERIFICATION_PATH"
    adapter_frontier_sha256 = _owned_success_adapter_frontier_sha256(
        repo_root=repo_root,
    )
    verification_authority_sha256 = _owned_success_verification_authority_sha256(
        repo_root=repo_root,
    )
    row["verification_frontier_sha256"] = frontier_sha256
    row["adapter_frontier_sha256"] = adapter_frontier_sha256
    row["verification_authority_sha256"] = verification_authority_sha256
    row["parked_observations"] = int(row.get("observations", 0))
    row["epistemic_nonlearnability_proved"] = False
    row["observational_inseparability_proved"] = False
    row["frontier_expansion_required"] = True

    observations = state.get("observations", {})
    observation = observations.get(observation_id) if isinstance(observations, Mapping) else None
    if isinstance(observation, dict):
        observation["learning_disposition"] = (
            "UNRESOLVED_WITH_CURRENT_OWNED_VERIFICATION_FRONTIER"
        )
        observation["learning_disposition_reason"] = (
            "OWNED_SUCCESS_ADAPTER_RETURNED_NO_CANDIDATE"
        )
        observation["learning_disposition_frontier_sha256"] = frontier_sha256
        observation["adapter_frontier_sha256"] = adapter_frontier_sha256
        observation["verification_authority_sha256"] = verification_authority_sha256
        observation["epistemic_nonlearnability_proved"] = False
        observation["observational_inseparability_proved"] = False
        observation["frontier_expansion_required"] = True
        observation["permanent_nonlearnability_claimed"] = False

    expansion_work_id = _enqueue_success_verification_frontier_expansion(
        state,
        blocked_work_id=wid,
        observation_id=observation_id,
        frontier_sha256=frontier_sha256,
        adapter_frontier_sha256=adapter_frontier_sha256,
        verification_authority_sha256=verification_authority_sha256,
    )
    row["frontier_expansion_work_id"] = expansion_work_id
    if isinstance(observation, dict):
        observation["frontier_expansion_work_id"] = expansion_work_id

    learning._refresh_stats(state)
    learning._write_state(state, state_path)


def _reactivate_parked_successes(
    *,
    state_path: str | Path,
    repo_root: str | Path,
    external_authority_available: bool,
    external_adapter_available: bool = False,
) -> dict[str, Any]:
    """Reopen only after exact-origin adapter activation with immutable verifier authority."""
    frontier = _owned_success_learning_frontier_sha256(repo_root=repo_root)
    adapter_frontier = _owned_success_adapter_frontier_sha256(repo_root=repo_root)
    verification_authority = _owned_success_verification_authority_sha256(
        repo_root=repo_root,
    )
    state = learning.load_state(state_path)
    queue = state.get("improvement_queue", {})
    reopened: list[str] = []
    reopened_by: dict[str, str] = {}
    resolved_frontier_handoffs: list[str] = []
    frontier_activation: dict[str, Any] | None = None
    state_changed = False

    safe_owned_adapter_change = False
    if isinstance(queue, Mapping):
        for raw in queue.values():
            if (
                not isinstance(raw, dict)
                or raw.get("status") != "PARKED"
                or raw.get("kind") != "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE"
            ):
                continue
            stored_adapter = str(raw.get("adapter_frontier_sha256") or "")
            stored_authority = str(raw.get("verification_authority_sha256") or "")
            if not stored_adapter or not stored_authority:
                raw["adapter_frontier_sha256"] = adapter_frontier
                raw["verification_authority_sha256"] = verification_authority
                raw["verification_frontier_sha256"] = frontier
                raw["frontier_partition_initialized_fail_closed"] = True
                state_changed = True
                continue
            if stored_authority != verification_authority:
                if (
                    raw.get("verification_authority_change_blocked") is not True
                    or raw.get("blocked_verification_authority_sha256")
                    != verification_authority
                ):
                    raw["verification_authority_change_blocked"] = True
                    raw["blocked_verification_authority_sha256"] = verification_authority
                    state_changed = True
                continue
            if stored_adapter != adapter_frontier:
                safe_owned_adapter_change = True

    if (
        safe_owned_adapter_change
        and not external_authority_available
        and not external_adapter_available
    ):
        try:
            frontier_activation = _activate_owned_success_adapter_frontier(
                expected_adapter_frontier_sha256=adapter_frontier,
                expected_verification_authority_sha256=verification_authority,
                repo_root=repo_root,
            )
        except Exception as exc:
            frontier_activation = {
                "schema": SCHEMA,
                "status": "SUCCESS_ADAPTER_FRONTIER_ACTIVATION_FAILED",
                "pass": False,
                "adapter_frontier_sha256": adapter_frontier,
                "verification_authority_sha256": verification_authority,
                "reason": type(exc).__name__ + ":" + str(exc),
                "terminal_authority": False,
            }

    if isinstance(queue, Mapping):
        for wid, raw in list(queue.items()):
            if (
                not isinstance(raw, dict)
                or raw.get("status") != "PARKED"
                or raw.get("kind") != "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE"
            ):
                continue
            stored_adapter = str(raw.get("adapter_frontier_sha256") or "")
            stored_authority = str(raw.get("verification_authority_sha256") or "")
            authority_unchanged = stored_authority == verification_authority
            adapter_changed = stored_adapter != adapter_frontier
            owned_adapter_change_active = (
                authority_unchanged
                and adapter_changed
                and isinstance(frontier_activation, Mapping)
                and frontier_activation.get("pass") is True
            )
            external_adapter_safe = (
                external_adapter_available and authority_unchanged
            )
            if (
                external_authority_available
                or external_adapter_safe
                or owned_adapter_change_active
            ):
                raw["status"] = "PENDING"
                raw["reopen_count"] = int(raw.get("reopen_count", 0)) + 1
                raw["reactivated_by"] = (
                    "EXTERNAL_VERIFICATION_AUTHORITY_AVAILABLE"
                    if external_authority_available
                    else (
                        "EXTERNAL_SUCCESS_ADAPTER_AVAILABLE__AUTHORITY_UNCHANGED"
                        if external_adapter_safe
                        else "OWNED_SUCCESS_ADAPTER_FRONTIER_CHANGED__AUTHORITY_UNCHANGED"
                    )
                )
                raw["previous_verification_frontier_sha256"] = raw.get(
                    "verification_frontier_sha256"
                )
                raw["verification_frontier_sha256"] = frontier
                raw["adapter_frontier_sha256"] = adapter_frontier
                raw["verification_authority_sha256"] = verification_authority
                raw.pop("verification_authority_change_blocked", None)
                raw.pop("blocked_verification_authority_sha256", None)
                reopened.append(str(wid))
                reopened_by[str(wid)] = str(raw["reactivated_by"])
                state_changed = True

        if reopened_by:
            for handoff_id, handoff in list(queue.items()):
                if (
                    not isinstance(handoff, dict)
                    or handoff.get("status") != "PENDING"
                    or handoff.get("kind") != FRONTIER_EXPANSION_KIND
                ):
                    continue
                payload = handoff.get("payload")
                blocked = (
                    str(payload.get("blocked_success_work_id") or "")
                    if isinstance(payload, Mapping)
                    else ""
                )
                if blocked not in reopened_by:
                    continue
                handoff["status"] = "RESOLVED"
                handoff["resolved_by"] = reopened_by[blocked]
                handoff["resolved_frontier_sha256"] = frontier
                resolved_frontier_handoffs.append(str(handoff_id))
                state_changed = True
    if state_changed:
        learning._refresh_stats(state)
        learning._write_state(state, state_path)
    return {
        "frontier_sha256": frontier,
        "adapter_frontier_sha256": adapter_frontier,
        "verification_authority_sha256": verification_authority,
        "frontier_activation": deepcopy(frontier_activation),
        "reopened_work_ids": sorted(reopened),
        "resolved_frontier_handoff_work_ids": sorted(resolved_frontier_handoffs),
    }

def _resolve_legacy_direct_owned_success_no_delta(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
) -> dict[str, Any] | None:
    """Retire legacy direct-success adapter work that never contained learning evidence.

    Older canonical Fabric versions recorded bounded direct-capability success as a
    generic success observation, which queued ADAPT_SUCCESS work despite stripping
    replay and proof material. Those records are executions of already-owned direct
    surfaces, not evidence of a new executable capability. Resolve them before
    same-evidence backoff can hide them forever.
    """
    if str(work.get("kind") or "") != "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE":
        return None
    payload = work.get("payload")
    if not isinstance(payload, Mapping):
        return None
    if payload.get("proof_available") is True or payload.get("replayable") is True:
        return None
    observation_id = str(payload.get("observation_id") or "").strip()
    if not observation_id:
        return None

    state = learning.load_state(state_path)
    observations = state.get("observations", {})
    queue = state.get("improvement_queue", {})
    observation = (
        observations.get(observation_id)
        if isinstance(observations, Mapping)
        else None
    )
    wid = str(work.get("work_id") or "").strip()
    row = queue.get(wid) if isinstance(queue, Mapping) else None
    if not isinstance(observation, dict) or not isinstance(row, dict):
        return None
    surface = str(observation.get("surface") or "")
    if (
        observation.get("schema") != DIRECT_OWNED_OBSERVATION_SCHEMA
        or not surface.startswith(DIRECT_OWNED_SURFACE_PREFIX)
        or observation.get("proof_capsule") is not None
        or observation.get("replay_capsule") is not None
        or row.get("status") != "PENDING"
    ):
        return None

    row["status"] = "RESOLVED"
    row["resolved_by"] = "DIRECT_OWNED_SUCCESS_NO_NEW_EXECUTABLE_CAPABILITY_EVIDENCE"
    row["resolved_without_promotion"] = True
    observation["learning_disposition"] = (
        "NO_NEW_EXECUTABLE_CAPABILITY_EVIDENCE_FROM_OWNED_DIRECT_SURFACE"
    )
    observation["learning_disposition_reason"] = (
        "LEGACY_DIRECT_SURFACE_SUCCESS_CONTAINED_NO_EPISODE_SKILL_REPLAY_OR_PROOF_EVIDENCE"
    )
    observation["frontier_expansion_required"] = False
    observation["permanent_nonlearnability_claimed"] = False
    observation["existing_capability_authority_unchanged"] = True
    observation["legacy_adapter_debt_retired"] = True
    learning._refresh_stats(state)
    learning._write_state(state, state_path)
    return {
        "schema": SCHEMA,
        "status": (
            "IMPROVEMENT_RESOLVED__LEGACY_DIRECT_OWNED_SUCCESS__"
            "NO_NEW_EXECUTABLE_CAPABILITY_EVIDENCE"
        ),
        "pass": True,
        "progress": False,
        "disposition_recorded": True,
        "work_id": wid,
        "observation_id": observation_id,
        "resolved_without_promotion": True,
        "frontier_expansion_required": False,
        "permanent_nonlearnability_claimed": False,
        "terminal_authority": False,
    }


def _repark_stale_replayable_success_after_resolved_handoff(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
) -> dict[str, Any] | None:
    """Normalize a replayable adapter miss whose prior frontier handoff was resolved.

    A historical external-verifier wake can resolve the acquisition handoff and
    reopen the blocked ADAPT_SUCCESS work even when the owned success adapter
    still returns no candidate. If that second adaptation consumes the same
    evidence, generic backoff would otherwise hide the still-real Root1 adapter
    gap forever. Re-park exactly that work and reopen its deterministic handoff
    before same-evidence backoff is consulted.
    """
    if str(work.get("kind") or "") != "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE":
        return None
    if str(work.get("status") or "") != "PENDING":
        return None
    payload = work.get("payload")
    if not isinstance(payload, Mapping):
        return None
    if payload.get("replayable") is not True:
        return None
    replay_capsule_sha256 = str(payload.get("replay_capsule_sha256") or "").strip()
    if len(replay_capsule_sha256) != 64:
        return None
    if (
        str(work.get("last_attempt_status") or "")
        != "IMPROVEMENT_PROVIDER_RETURNED_NO_SUCCESS_ADAPTATION"
    ):
        return None
    last = work.get("last_attempt_observations")
    if last is None or int(last) < int(work.get("observations", 0)):
        return None

    wid = str(work.get("work_id") or "").strip()
    observation_id = str(payload.get("observation_id") or "").strip()
    prior_handoff_id = str(work.get("frontier_expansion_work_id") or "").strip()
    if not wid or not observation_id or not prior_handoff_id:
        return None

    state = learning.load_state(state_path)
    queue = state.get("improvement_queue", {})
    observations = state.get("observations", {})
    row = queue.get(wid) if isinstance(queue, Mapping) else None
    handoff = queue.get(prior_handoff_id) if isinstance(queue, Mapping) else None
    observation = (
        observations.get(observation_id)
        if isinstance(observations, Mapping)
        else None
    )
    if (
        not isinstance(row, dict)
        or row.get("status") != "PENDING"
        or not isinstance(handoff, Mapping)
        or handoff.get("kind") != FRONTIER_EXPANSION_KIND
        or handoff.get("status") != "RESOLVED"
        or not isinstance(observation, Mapping)
    ):
        return None
    handoff_payload = handoff.get("payload")
    if (
        not isinstance(handoff_payload, Mapping)
        or str(handoff_payload.get("blocked_success_work_id") or "") != wid
        or str(handoff_payload.get("observation_id") or "") != observation_id
    ):
        return None

    # Require the retained replay capsule to remain authentic before creating
    # any new acquisition debt. This does not replay the success.
    replay = learning.get_success_replay_context(
        observation_id,
        state_path=state_path,
    )
    if replay.get("replay_capsule_sha256") != replay_capsule_sha256:
        raise ImprovementDriverError(
            "STALE_SUCCESS_REPLAY_CAPSULE_BINDING_MISMATCH:" + wid
        )

    current_frontier = _owned_success_learning_frontier_sha256(repo_root=repo_root)
    current_adapter = _owned_success_adapter_frontier_sha256(repo_root=repo_root)
    current_authority = _owned_success_verification_authority_sha256(
        repo_root=repo_root,
    )
    stored_authority = str(row.get("verification_authority_sha256") or "")
    if stored_authority and stored_authority != current_authority:
        return None

    _park_success_work(
        work,
        observation_id=observation_id,
        frontier_sha256=current_frontier,
        state_path=state_path,
        repo_root=repo_root,
    )
    updated = learning.load_state(state_path)
    updated_queue = updated.get("improvement_queue", {})
    updated_row = (
        updated_queue.get(wid)
        if isinstance(updated_queue, Mapping)
        else None
    )
    new_handoff_id = (
        str(updated_row.get("frontier_expansion_work_id") or "")
        if isinstance(updated_row, Mapping)
        else ""
    )
    new_handoff = (
        updated_queue.get(new_handoff_id)
        if isinstance(updated_queue, Mapping)
        else None
    )
    if (
        not isinstance(updated_row, Mapping)
        or updated_row.get("status") != "PARKED"
        or not new_handoff_id
        or not isinstance(new_handoff, Mapping)
        or new_handoff.get("kind") != FRONTIER_EXPANSION_KIND
        or new_handoff.get("status") != "PENDING"
    ):
        raise ImprovementDriverError(
            "STALE_SUCCESS_HANDOFF_RECONCILIATION_DID_NOT_REPARK:" + wid
        )

    return {
        "schema": SCHEMA,
        "status": (
            "IMPROVEMENT_REPARKED__STALE_RESOLVED_FRONTIER_HANDOFF__"
            "ADAPTER_MISS_STILL_OPEN"
        ),
        "pass": True,
        "progress": False,
        "disposition_recorded": True,
        "work_id": wid,
        "observation_id": observation_id,
        "prior_frontier_handoff_work_id": prior_handoff_id,
        "frontier_expansion_work_id": new_handoff_id,
        "adapter_frontier_sha256": current_adapter,
        "verification_authority_sha256": current_authority,
        "replay_original_success": False,
        "terminal_authority": False,
    }


def _episode_pools(
    state: Mapping[str, Any],
    current_episode: Mapping[str, Any],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    scope = str(current_episode.get("scope_id") or "").strip()
    eid = str(current_episode.get("episode_id") or "").strip()
    same_scope: list[Mapping[str, Any]] = []
    other_scope: list[Mapping[str, Any]] = []
    for raw in state.get("episodes", {}).values():
        if not isinstance(raw, Mapping):
            continue
        if str(raw.get("episode_id") or "").strip() == eid:
            continue
        target = same_scope if str(raw.get("scope_id") or "").strip() == scope else other_scope
        target.append(deepcopy(dict(raw)))
    return same_scope, other_scope


def _verify_episode_work(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
    episode_verification_provider,
    skill_verification_provider,
) -> dict[str, Any]:
    payload = work.get("payload")
    if not isinstance(payload, Mapping):
        raise ImprovementDriverError("VERIFY_EPISODE_PAYLOAD_INVALID")
    episode = payload.get("episode")
    problem = payload.get("problem")
    trace = payload.get("trace")
    if not isinstance(episode, Mapping):
        raise ImprovementDriverError("VERIFY_EPISODE_MATERIAL_MISSING:episode")
    if not isinstance(problem, Mapping):
        raise ImprovementDriverError("VERIFY_EPISODE_MATERIAL_MISSING:problem")
    if not isinstance(trace, Sequence) or isinstance(trace, (str, bytes)):
        raise ImprovementDriverError("VERIFY_EPISODE_MATERIAL_MISSING:trace")

    state = learning.load_state(state_path)
    prior, generalization = _episode_pools(state, episode)
    candidate = {
        "pass": True,
        "status": "PENDING_INDEPENDENT_EPISODE_VERIFICATION",
        "current_episode": deepcopy(dict(episode)),
        "current_episode_verified": False,
        "trace": deepcopy(list(trace)),
        "state_capsule_head_hash": str(payload.get("fact_capsule_head_hash") or ""),
        "value_capsule_head_hash": str(payload.get("value_capsule_head_hash") or ""),
    }
    verified = learning._post_execution_independent_verification(
        candidate,
        problem=problem,
        prior_verified_episode_records=prior,
        generalization_episode_records=generalization,
        repo_root=repo_root,
        episode_verification_provider=episode_verification_provider,
        skill_verification_provider=skill_verification_provider,
        effect_root=payload.get("effect_root"),
    )
    if verified.get("current_episode_verified") is not True:
        return {
            "schema": SCHEMA,
            "status": "IMPROVEMENT_ATTEMPT_FAILED_INDEPENDENT_EPISODE_VERIFICATION",
            "pass": False,
            "work_id": work.get("work_id"),
            "verification_error": (
                verified.get("episode_verification_error")
                or verified.get("post_execution_episode_verification_error")
            ),
            "terminal_authority": False,
        }
    integrated = learning.integrate_solver_output(
        verified,
        state_path=state_path,
        repo_root=repo_root,
        verification_problem=problem,
    )
    return {
        "schema": SCHEMA,
        "status": "IMPROVEMENT_ADVANCED__EPISODE_VERIFIED",
        "pass": True,
        "work_id": work.get("work_id"),
        "learning": integrated,
        "terminal_authority": False,
    }


def _verify_skill_work(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
    skill_verification_provider,
) -> dict[str, Any]:
    payload = work.get("payload")
    if not isinstance(payload, Mapping):
        raise ImprovementDriverError("VERIFY_SKILL_PAYLOAD_INVALID")
    candidate = payload.get("candidate")
    if not isinstance(candidate, Mapping):
        raise ImprovementDriverError("VERIFY_SKILL_CANDIDATE_MISSING")
    binding = skill_verification_provider({
        "kind": "SKILL_VERIFICATION",
        "candidate": deepcopy(dict(candidate)),
        "current_episode": {},
        "improvement_work_id": work.get("work_id"),
    })
    if binding is None:
        return {
            "schema": SCHEMA,
            "status": "IMPROVEMENT_PROVIDER_RETURNED_NO_SKILL_BINDING",
            "pass": False,
            "work_id": work.get("work_id"),
            "terminal_authority": False,
        }
    if not isinstance(binding, Mapping):
        raise ImprovementDriverError("SKILL_VERIFICATION_PROVIDER_RESULT_INVALID")
    auth = authenticate_skill_verification(candidate, binding, repo_root=repo_root)
    if auth.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "IMPROVEMENT_ATTEMPT_FAILED_INDEPENDENT_SKILL_VERIFICATION",
            "pass": False,
            "work_id": work.get("work_id"),
            "verification_error": auth.get("reason"),
            "terminal_authority": False,
        }
    verified_skill = auth["verified_skill"]
    integrated = learning.integrate_solver_output(
        {
            "pass": True,
            "status": "SOLVED__VERIFIED_EXECUTABLE_SKILL_READY",
            "skill_candidate": deepcopy(dict(candidate)),
            "verified_executable_skill": deepcopy(dict(verified_skill)),
            "verified_skill_reuse_authorized": bool(verified_skill.get("reuse_authorized")),
        },
        state_path=state_path,
        repo_root=repo_root,
    )
    return {
        "schema": SCHEMA,
        "status": "IMPROVEMENT_ADVANCED__SKILL_VERIFIED_AND_PARETO_ADJUDICATED",
        "pass": True,
        "work_id": work.get("work_id"),
        "learning": integrated,
        "terminal_authority": False,
    }


def _verify_scope_generalization_work(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
    skill_verification_provider,
) -> dict[str, Any]:
    """Promote a verified skill to a broader proved scope through one authority path."""
    payload = work.get("payload")
    if not isinstance(payload, Mapping):
        raise ImprovementDriverError("SCOPE_GENERALIZATION_PAYLOAD_INVALID")
    identity = work.get("identity")
    skill_id = str(
        payload.get("skill_id")
        or (identity.get("skill_id") if isinstance(identity, Mapping) else "")
        or ""
    ).strip()
    if not skill_id:
        raise ImprovementDriverError("SCOPE_GENERALIZATION_SKILL_ID_MISSING")

    state = learning.load_state(state_path)
    record = state.get("skills", {}).get(skill_id)
    raw_skill = record.get("skill") if isinstance(record, Mapping) else None
    if not isinstance(raw_skill, Mapping):
        raise ImprovementDriverError("SCOPE_GENERALIZATION_SKILL_MISSING:" + skill_id)
    authority = learning.reauthenticate_skill_record(
        raw_skill,
        repo_root=repo_root,
    )
    authenticated_skill = authority.get("verified_skill")
    if (
        authority.get("pass") is not True
        or not isinstance(authenticated_skill, Mapping)
        or learning._skill_id(authenticated_skill) != skill_id
    ):
        return {
            "schema": SCHEMA,
            "status": "SCOPE_GENERALIZATION_SOURCE_SKILL_AUTHORITY_INVALID",
            "pass": False,
            "work_id": work.get("work_id"),
            "verification_error": authority.get("reason"),
            "terminal_authority": False,
        }

    candidate = learning._candidate_from_verified_skill(authenticated_skill)
    predicate = learning.VERIFIED_SUPERSET_SCOPE_PREDICATE
    binding = skill_verification_provider({
        "kind": "SKILL_SCOPE_GENERALIZATION_VERIFICATION",
        "candidate": deepcopy(dict(candidate)),
        "current_episode": {},
        "improvement_work_id": work.get("work_id"),
        "requested_scope_relation": "PROVEN_SUPERSET",
        "requested_scope_predicate": predicate,
        "supported_scope_predicates": [predicate],
    })
    if binding is None:
        return {
            "schema": SCHEMA,
            "status": "IMPROVEMENT_PROVIDER_RETURNED_NO_SCOPE_GENERALIZATION_BINDING",
            "pass": False,
            "work_id": work.get("work_id"),
            "terminal_authority": False,
        }
    if not isinstance(binding, Mapping):
        raise ImprovementDriverError("SCOPE_GENERALIZATION_PROVIDER_RESULT_INVALID")

    auth = authenticate_skill_verification(candidate, binding, repo_root=repo_root)
    if auth.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "IMPROVEMENT_ATTEMPT_FAILED_INDEPENDENT_SCOPE_GENERALIZATION",
            "pass": False,
            "work_id": work.get("work_id"),
            "verification_error": auth.get("reason"),
            "terminal_authority": False,
        }
    verified_skill = auth.get("verified_skill")
    if not isinstance(verified_skill, Mapping):
        raise ImprovementDriverError("SCOPE_GENERALIZATION_VERIFIED_SKILL_MISSING")
    if (
        str(verified_skill.get("scope_relation") or "") != "PROVEN_SUPERSET"
        or str(verified_skill.get("scope_predicate") or "") != predicate
    ):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__GENERALIZATION_PROOF_NOT_SUPERSET",
            "pass": False,
            "work_id": work.get("work_id"),
            "verification_error": "BOUND_PROVEN_SUPERSET_STRUCTURAL_MATCH_REQUIRED",
            "terminal_authority": False,
        }

    integrated = learning.integrate_solver_output(
        {
            "pass": True,
            "status": "SOLVED__VERIFIED_EXECUTABLE_SKILL_READY",
            "skill_candidate": deepcopy(dict(candidate)),
            "verified_executable_skill": deepcopy(dict(verified_skill)),
            "verified_skill_reuse_authorized": True,
        },
        state_path=state_path,
        repo_root=repo_root,
    )
    return {
        "schema": SCHEMA,
        "status": "IMPROVEMENT_ADVANCED__SCOPE_GENERALIZATION_VERIFIED_AND_PARETO_ADJUDICATED",
        "pass": True,
        "work_id": work.get("work_id"),
        "learning": integrated,
        "scope_relation": verified_skill.get("scope_relation"),
        "scope_predicate": verified_skill.get("scope_predicate"),
        "terminal_authority": False,
    }


def _adapt_success_work(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
    success_episode_adapter_provider,
    episode_verification_provider,
    skill_verification_provider,
) -> dict[str, Any]:
    payload = work.get("payload")
    if not isinstance(payload, Mapping):
        raise ImprovementDriverError("SUCCESS_ADAPTATION_PAYLOAD_INVALID")
    observation_id = str(payload.get("observation_id") or "").strip()
    if not observation_id:
        raise ImprovementDriverError("SUCCESS_OBSERVATION_ID_MISSING")
    replay = learning.get_success_replay_context(
        observation_id,
        state_path=state_path,
    )
    state = learning.load_state(state_path)
    observation = state.get("observations", {}).get(observation_id)
    if not isinstance(observation, Mapping):
        raise ImprovementDriverError("SUCCESS_OBSERVATION_UNKNOWN:" + observation_id)

    adapted = success_episode_adapter_provider({
        "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
        "observation": deepcopy(dict(observation)),
        "replay_context": deepcopy(dict(replay["context"])),
        "improvement_work_id": work.get("work_id"),
        "authority_requested": "CANDIDATE_ONLY",
    })
    if not isinstance(adapted, Mapping):
        return {
            "schema": SCHEMA,
            "status": "IMPROVEMENT_PROVIDER_RETURNED_NO_SUCCESS_ADAPTATION",
            "pass": False,
            "work_id": work.get("work_id"),
            "terminal_authority": False,
        }
    problem = adapted.get("problem")
    solver_output = adapted.get("solver_output")
    if not isinstance(problem, Mapping):
        raise ImprovementDriverError("SUCCESS_ADAPTER_PROBLEM_MISSING")
    if not isinstance(solver_output, Mapping) or solver_output.get("pass") is not True:
        raise ImprovementDriverError("SUCCESS_ADAPTER_SOLVER_OUTPUT_INVALID")
    episode = solver_output.get("current_episode")
    trace = solver_output.get("trace")
    if not isinstance(episode, Mapping):
        raise ImprovementDriverError("SUCCESS_ADAPTER_EPISODE_CANDIDATE_MISSING")
    if not isinstance(trace, Sequence) or isinstance(trace, (str, bytes)):
        raise ImprovementDriverError("SUCCESS_ADAPTER_TRACE_MISSING")

    prior, generalization = _episode_pools(state, episode)
    verified = learning._post_execution_independent_verification(
        solver_output,
        problem=problem,
        prior_verified_episode_records=prior,
        generalization_episode_records=generalization,
        repo_root=repo_root,
        episode_verification_provider=episode_verification_provider,
        skill_verification_provider=skill_verification_provider,
    )
    if verified.get("current_episode_verified") is not True:
        return {
            "schema": SCHEMA,
            "status": "SUCCESS_ADAPTATION_NOT_INDEPENDENTLY_VERIFIED",
            "pass": False,
            "work_id": work.get("work_id"),
            "verification_error": (
                verified.get("episode_verification_error")
                or verified.get("post_execution_episode_verification_error")
            ),
            "terminal_authority": False,
        }
    integrated = learning.integrate_solver_output(
        verified,
        state_path=state_path,
        verification_problem=problem,
    )
    resolved_by = str(integrated.get("episode_key") or "VERIFIED_SUCCESS_EPISODE")
    _resolve_work(
        str(work.get("work_id") or ""),
        resolved_by=resolved_by,
        state_path=state_path,
    )
    return {
        "schema": SCHEMA,
        "status": "IMPROVEMENT_ADVANCED__SUCCESS_BECAME_VERIFIED_EPISODE",
        "pass": True,
        "work_id": work.get("work_id"),
        "learning": integrated,
        "terminal_authority": False,
    }


def _internal_failure_repair(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Use the Brain's own verified repair/replay cycle as the default R3 worker."""
    payload = work.get("payload")
    if not isinstance(payload, Mapping):
        raise ImprovementDriverError("FAILURE_REPAIR_PAYLOAD_INVALID")
    fingerprint = str(payload.get("failure_fingerprint") or "").strip()
    retry_sha = str(payload.get("retry_capsule_sha256") or "").strip()
    if not fingerprint:
        raise ImprovementDriverError("FAILURE_REPAIR_FINGERPRINT_MISSING")
    if not retry_sha:
        retired = learning.retire_orphaned_failure_repair_work(
            fingerprint,
            state_path=state_path,
            work_id=str(work.get("work_id") or ""),
        )
        if retired.get("pass") is True:
            return {
                "schema": SCHEMA,
                "status": "IMPROVEMENT_ADVANCED__ORPHANED_FAILURE_TELEMETRY_RETIRED",
                "pass": True,
                "failure_fingerprint": fingerprint,
                "orphan_telemetry_retired": True,
                "original_failure_repaired": False,
                "terminal_obligation_established": False,
                "retirement": deepcopy(dict(retired)),
                "terminal_authority": False,
            }
        return {
            "schema": SCHEMA,
            "status": "IMPROVEMENT_REPAIR_BLOCKED__REPLAY_CAPSULE_REQUIRED",
            "pass": False,
            "failure_fingerprint": fingerprint,
            "terminal_authority": False,
        }

    from canonical.runtime import live_brain_runtime_v1 as live_brain

    return live_brain.execute_failure_repair_cycle(
        {
            "failure_fingerprint": fingerprint,
            "retry_capsule_sha256": retry_sha,
            "components": [],
            "initial_facts": [],
            "learn": True,
            "autonomous": True,
        },
        repo_root=repo_root,
        state_path=state_path,
    )


ATTEMPT_BACKOFF_KINDS = {
    "VERIFY_SKILL_CANDIDATE",
    "VERIFY_EPISODE",
    "REPAIR_FAILURE_CLASS",
    "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE",
    "REVERIFY_QUARANTINED_SKILL",
    "SEEK_VERIFIED_SCOPE_GENERALIZATION",
}


def _attempt_already_consumed_current_evidence(work: Mapping[str, Any]) -> bool:
    if str(work.get("kind") or "") not in ATTEMPT_BACKOFF_KINDS:
        return False
    last = work.get("last_attempt_observations")
    if last is None:
        return False
    return int(last) >= int(work.get("observations", 0))


def _frontier_acquisition_attempt_consumed(
    work: Mapping[str, Any],
    *,
    provider_id: str,
    repo_root: str | Path,
) -> bool:
    """Back off only for the same provider identity and unchanged owned frontier."""
    if str(work.get("kind") or "") != FRONTIER_EXPANSION_KIND:
        return False
    last = work.get("last_attempt_observations")
    if last is None:
        return False
    if int(last) < int(work.get("observations", 0)):
        return False
    if str(work.get("last_attempt_provider_id") or "") != provider_id:
        return False
    current = _owned_success_learning_frontier_sha256(repo_root=repo_root)
    return str(work.get("last_attempt_frontier_sha256") or "") == current


def _record_frontier_acquisition_attempt(
    work_id: str,
    *,
    provider_id: str,
    frontier_sha256: str,
    status: str,
    reason: str | None,
    state_path: str | Path,
) -> None:
    learning._record_improvement_attempt(
        work_id,
        status=status,
        reason=reason,
        state_path=state_path,
    )
    state = learning.load_state(state_path)
    queue = state.get("improvement_queue", {})
    row = queue.get(work_id) if isinstance(queue, Mapping) else None
    if not isinstance(row, dict):
        raise ImprovementDriverError("IMPROVEMENT_WORK_UNKNOWN:" + work_id)
    row["last_attempt_provider_id"] = provider_id
    row["last_attempt_frontier_sha256"] = frontier_sha256
    learning._refresh_stats(state)
    learning._write_state(state, state_path)


def _execute_frontier_acquisition(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
    provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None],
    provider_id: str,
    repair_reduction: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = work.get("payload")
    if not isinstance(payload, Mapping):
        raise ImprovementDriverError("FRONTIER_EXPANSION_PAYLOAD_INVALID")
    wid = str(work.get("work_id") or "").strip()
    before = _owned_success_learning_frontier_sha256(repo_root=repo_root)
    before_adapter = _owned_success_adapter_frontier_sha256(repo_root=repo_root)
    before_authority = _owned_success_verification_authority_sha256(
        repo_root=repo_root,
    )
    request = {
        "kind": FRONTIER_EXPANSION_KIND,
        "improvement_work_id": wid,
        "blocked_success_work_id": payload.get("blocked_success_work_id"),
        "observation_id": payload.get("observation_id"),
        "verification_frontier_sha256": before,
        "adapter_frontier_sha256": before_adapter,
        "verification_authority_sha256": before_authority,
        "required_capability_class": (
            "VERIFIER_PRESERVING_SUCCESS_ADAPTER"
            if isinstance(repair_reduction, Mapping)
            and repair_reduction.get("pass") is True
            else payload.get("required_capability_class")
        ),
        "admissible_repair_classes": (
            deepcopy(list(repair_reduction.get("admissible_repair_classes") or []))
            if isinstance(repair_reduction, Mapping)
            and repair_reduction.get("pass") is True
            else None
        ),
        "preferred_repair_order": (
            deepcopy(list(repair_reduction.get("preferred_repair_order") or []))
            if isinstance(repair_reduction, Mapping)
            and repair_reduction.get("pass") is True
            else None
        ),
        "must_acquire_new_distinguishing_evidence": (
            repair_reduction.get("must_acquire_new_distinguishing_evidence") is True
            if isinstance(repair_reduction, Mapping)
            and repair_reduction.get("pass") is True
            else False
        ),
        "boundary_root": payload.get("boundary_root"),
        "allowed_frontier_change_class": (
            "SUCCESS_ADAPTER_ONLY__VERIFICATION_AUTHORITY_IMMUTABLE"
        ),
        "verification_authority_change_allowed": False,
        "replay_original_success": False,
        "candidate_generation_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }
    result = provider(deepcopy(request))
    if not isinstance(result, Mapping):
        status = "FRONTIER_ACQUISITION_PROVIDER_RETURNED_NO_RESULT"
        _record_frontier_acquisition_attempt(
            wid,
            provider_id=provider_id,
            frontier_sha256=before,
            status=status,
            reason=status,
            state_path=state_path,
        )
        return {
            "schema": SCHEMA,
            "status": status,
            "pass": False,
            "progress": False,
            "work_id": wid,
            "attempt_backoff_recorded": True,
            "terminal_authority": False,
        }

    after = _owned_success_learning_frontier_sha256(repo_root=repo_root)
    after_adapter = _owned_success_adapter_frontier_sha256(repo_root=repo_root)
    after_authority = _owned_success_verification_authority_sha256(
        repo_root=repo_root,
    )

    if after_authority != before_authority:
        status = "FRONTIER_ACQUISITION_REJECTED__VERIFICATION_AUTHORITY_REWRITTEN"
        reason = str(result.get("reason") or result.get("status") or status)
        _record_frontier_acquisition_attempt(
            wid,
            provider_id=provider_id,
            frontier_sha256=after,
            status=status,
            reason=reason,
            state_path=state_path,
        )
        return {
            "schema": SCHEMA,
            "status": status,
            "pass": False,
            "progress": False,
            "work_id": wid,
            "provider_result": deepcopy(dict(result)),
            "verification_frontier_sha256_before": before,
            "verification_frontier_sha256_after": after,
            "adapter_frontier_sha256_before": before_adapter,
            "adapter_frontier_sha256_after": after_adapter,
            "verification_authority_sha256_before": before_authority,
            "verification_authority_sha256_after": after_authority,
            "verification_authority_change_accepted": False,
            "attempt_backoff_recorded": True,
            "terminal_authority": False,
        }

    if after_adapter == before_adapter:
        status = "FRONTIER_ACQUISITION_DID_NOT_CHANGE_OWNED_SUCCESS_ADAPTER_FRONTIER"
        reason = str(result.get("reason") or result.get("status") or status)
        _record_frontier_acquisition_attempt(
            wid,
            provider_id=provider_id,
            frontier_sha256=after,
            status=status,
            reason=reason,
            state_path=state_path,
        )
        return {
            "schema": SCHEMA,
            "status": status,
            "pass": False,
            "progress": False,
            "work_id": wid,
            "provider_result": deepcopy(dict(result)),
            "verification_frontier_sha256_before": before,
            "verification_frontier_sha256_after": after,
            "adapter_frontier_sha256_before": before_adapter,
            "adapter_frontier_sha256_after": after_adapter,
            "verification_authority_sha256_before": before_authority,
            "verification_authority_sha256_after": after_authority,
            "attempt_backoff_recorded": True,
            "terminal_authority": False,
        }

    reactivation = _reactivate_parked_successes(
        state_path=state_path,
        repo_root=repo_root,
        external_authority_available=False,
        external_adapter_available=False,
    )
    blocked = str(payload.get("blocked_success_work_id") or "")
    reopened = set(reactivation.get("reopened_work_ids") or [])
    if blocked not in reopened:
        activation = reactivation.get("frontier_activation")
        status = (
            "ADAPTER_FRONTIER_CHANGED_BUT_RUNTIME_ACTIVATION_FAILED"
            if isinstance(activation, Mapping)
            and activation.get("pass") is not True
            else "ADAPTER_FRONTIER_CHANGED_BUT_BLOCKED_SUCCESS_NOT_REOPENED"
        )
        reason = (
            str(activation.get("reason") or activation.get("status") or status)
            if isinstance(activation, Mapping)
            else status
        )
        _record_frontier_acquisition_attempt(
            wid,
            provider_id=provider_id,
            frontier_sha256=after,
            status=status,
            reason=reason,
            state_path=state_path,
        )
        return {
            "schema": SCHEMA,
            "status": status,
            "pass": False,
            "progress": False,
            "work_id": wid,
            "blocked_success_work_id": blocked,
            "provider_result": deepcopy(dict(result)),
            "verification_frontier_sha256_before": before,
            "verification_frontier_sha256_after": after,
            "adapter_frontier_sha256_before": before_adapter,
            "adapter_frontier_sha256_after": after_adapter,
            "verification_authority_sha256_before": before_authority,
            "verification_authority_sha256_after": after_authority,
            "frontier_activation": deepcopy(activation),
            "attempt_backoff_recorded": True,
            "terminal_authority": False,
        }
    return {
        "schema": SCHEMA,
        "status": "IMPROVEMENT_ADVANCED__SUCCESS_ADAPTER_FRONTIER_EXPANDED_AND_SUCCESS_REOPENED",
        "pass": True,
        "progress": True,
        "work_id": wid,
        "blocked_success_work_id": blocked,
        "provider_result": deepcopy(dict(result)),
        "verification_frontier_sha256_before": before,
        "verification_frontier_sha256_after": after,
        "adapter_frontier_sha256_before": before_adapter,
        "adapter_frontier_sha256_after": after_adapter,
        "verification_authority_sha256_before": before_authority,
        "verification_authority_sha256_after": after_authority,
        "verification_authority_unchanged": True,
        "frontier_activation": deepcopy(reactivation.get("frontier_activation")),
        "reopened_work_ids": sorted(reopened),
        "resolved_frontier_handoff_work_ids": reactivation.get(
            "resolved_frontier_handoff_work_ids"
        ) or [],
        "terminal_authority": False,
    }

def _record_failed_action_attempt(
    work_id: str,
    out: Mapping[str, Any],
    *,
    state_path: str | Path,
) -> None:
    learning._record_improvement_attempt(
        work_id,
        status=str(out.get("status") or "IMPROVEMENT_ACTION_FAILED"),
        reason=(
            str(
                out.get("reason")
                or out.get("verification_error")
                or out.get("autonomous_replay_reason")
                or ""
            ).strip()
            or None
        ),
        state_path=state_path,
    )


def advance_once(
    *,
    state_path: str | Path = learning.DEFAULT_STATE_PATH,
    repo_root: str | Path = ROOT,
    episode_verification_provider=None,
    skill_verification_provider=None,
    success_episode_adapter_provider=None,
    failure_repair_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    verification_frontier_acquisition_provider: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    verification_frontier_acquisition_provider_id: str = (
        "HOST_VERIFICATION_FRONTIER_ACQUISITION_PROVIDER"
    ),
    distinguishing_evidence_provider: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    distinguishing_evidence_provider_id: str = (
        "HOST_R3_DISTINGUISHING_EVIDENCE_PROVIDER"
    ),
) -> dict[str, Any]:
    """Execute the highest-priority *actionable* pending improvement exactly once."""
    external_episode_verifier = episode_verification_provider is not None
    external_success_adapter = success_episode_adapter_provider is not None
    reactivation = _reactivate_parked_successes(
        state_path=state_path,
        repo_root=repo_root,
        external_authority_available=external_episode_verifier,
        external_adapter_available=external_success_adapter,
    )

    # Missing host providers are not treated as missing capability when the Brain
    # owns a proof-producing worker for the admitted scope. External providers
    # still override these defaults; the existing authenticators remain the sole
    # promotion authority.
    if episode_verification_provider is None or skill_verification_provider is None:
        from canonical.runtime import r3_independent_learning_verifier_v1 as independent

        if episode_verification_provider is None:
            episode_verification_provider = lambda request: independent.verify_episode_request(
                request,
                repo_root=repo_root,
            )
        if skill_verification_provider is None:
            skill_verification_provider = lambda request: independent.verify_skill_request(
                request,
                repo_root=repo_root,
                state_path=state_path,
            )

    if success_episode_adapter_provider is None:
        from canonical.runtime import r3_bound_success_adapter_v1 as bound_success_adapter
        from canonical.runtime import r3_raw_success_adapter_v1 as raw_success_adapter
        from canonical.runtime import r3_direct_adequacy_success_adapter_v1 as direct_success_adapter
        from canonical.runtime import r3_checkpoint_reconstruction_success_adapter_v1 as checkpoint_success_adapter
        from canonical.runtime import r3_structural_bound_success_adapter_v1 as structural_success_adapter

        def _owned_success_adapter(request):
            adapted = bound_success_adapter.adapt(request, repo_root=repo_root)
            if adapted is not None:
                return adapted
            adapted = raw_success_adapter.adapt(request, repo_root=repo_root)
            if adapted is not None:
                return adapted
            adapted = direct_success_adapter.adapt(request, repo_root=repo_root)
            if adapted is not None:
                return adapted
            adapted = checkpoint_success_adapter.adapt(request, repo_root=repo_root)
            if adapted is not None:
                return adapted
            return structural_success_adapter.adapt(request, repo_root=repo_root)

        success_episode_adapter_provider = _owned_success_adapter

    state = learning.load_state(state_path)
    pending = _pending(state)
    blockers: list[dict[str, Any]] = []
    if not pending:
        return {
            "schema": SCHEMA,
            "status": "IMPROVEMENT_QUEUE_EMPTY",
            "pass": True,
            "progress": False,
            "pending_count": 0,
            "terminal_authority": False,
        }

    for work in pending:
        kind = str(work.get("kind") or "")
        wid = str(work.get("work_id") or "")
        legacy_direct = _resolve_legacy_direct_owned_success_no_delta(
            work,
            state_path=state_path,
        )
        if legacy_direct is not None:
            return {
                **legacy_direct,
                "blockers_skipped": blockers,
            }
        stale_repark = _repark_stale_replayable_success_after_resolved_handoff(
            work,
            state_path=state_path,
            repo_root=repo_root,
        )
        if stale_repark is not None:
            return {
                **stale_repark,
                "blockers_skipped": blockers,
            }
        if kind == "REPAIR_FAILURE_CLASS":
            payload = work.get("payload") if isinstance(work.get("payload"), Mapping) else {}
            identity = work.get("identity") if isinstance(work.get("identity"), Mapping) else {}
            fingerprint = str(
                payload.get("failure_fingerprint")
                or identity.get("failure_fingerprint")
                or ""
            ).strip()
            retry_sha = str(
                payload.get("retry_capsule_sha256")
                or identity.get("retry_capsule_sha256")
                or ""
            ).strip()
            if fingerprint and not retry_sha:
                retired = learning.retire_orphaned_failure_repair_work(
                    fingerprint,
                    state_path=state_path,
                    work_id=wid,
                )
                if retired.get("pass") is True:
                    return {
                        "schema": SCHEMA,
                        "status": "IMPROVEMENT_ADVANCED__ORPHANED_FAILURE_TELEMETRY_RETIRED",
                        "pass": True,
                        "progress": True,
                        "work_id": wid,
                        "repair": deepcopy(dict(retired)),
                        "original_failure_repaired": False,
                        "attempt_backoff_recorded": False,
                        "blockers_skipped": blockers,
                        "terminal_authority": False,
                    }

        if _frontier_acquisition_attempt_consumed(
            work,
            provider_id=verification_frontier_acquisition_provider_id,
            repo_root=repo_root,
        ):
            blockers.append({
                "work_id": wid,
                "kind": kind,
                "blocker": "FRONTIER_ACQUISITION_ALREADY_ATTEMPTED_FOR_CURRENT_PROVIDER_AND_FRONTIER",
            })
            continue
        if _attempt_already_consumed_current_evidence(work):
            blockers.append({
                "work_id": wid,
                "kind": kind,
                "blocker": "WORK_ALREADY_ATTEMPTED_FOR_CURRENT_EVIDENCE",
            })
            continue
        try:
            if kind == "VERIFY_SKILL_CANDIDATE":
                payload = work.get("payload") if isinstance(work.get("payload"), Mapping) else {}
                if not isinstance(payload.get("candidate"), Mapping):
                    blockers.append({
                        "work_id": wid,
                        "kind": kind,
                        "blocker": "LEGACY_SKILL_VERIFICATION_MATERIAL_INCOMPLETE",
                    })
                    continue
                if skill_verification_provider is None:
                    blockers.append({"work_id": wid, "kind": kind, "blocker": "SKILL_VERIFICATION_PROVIDER_REQUIRED"})
                    continue
                out = _verify_skill_work(
                    work,
                    state_path=state_path,
                    repo_root=repo_root,
                    skill_verification_provider=skill_verification_provider,
                )
                failed = out.get("pass") is not True
                if failed:
                    _record_failed_action_attempt(wid, out, state_path=state_path)
                return {
                    **out,
                    "progress": out.get("pass") is True,
                    "attempt_backoff_recorded": failed,
                    "blockers_skipped": blockers,
                }

            if kind == "VERIFY_EPISODE":
                if episode_verification_provider is None:
                    blockers.append({"work_id": wid, "kind": kind, "blocker": "EPISODE_VERIFICATION_PROVIDER_REQUIRED"})
                    continue
                payload = work.get("payload") if isinstance(work.get("payload"), Mapping) else {}
                if not all(payload.get(k) is not None for k in ("episode", "trace", "problem")):
                    blockers.append({"work_id": wid, "kind": kind, "blocker": "LEGACY_EPISODE_VERIFICATION_MATERIAL_INCOMPLETE"})
                    continue
                out = _verify_episode_work(
                    work,
                    state_path=state_path,
                    repo_root=repo_root,
                    episode_verification_provider=episode_verification_provider,
                    skill_verification_provider=skill_verification_provider,
                )
                failed = out.get("pass") is not True
                if failed:
                    _record_failed_action_attempt(wid, out, state_path=state_path)
                return {
                    **out,
                    "progress": out.get("pass") is True,
                    "attempt_backoff_recorded": failed,
                    "blockers_skipped": blockers,
                }

            if kind == "REPAIR_FAILURE_CLASS":
                if failure_repair_provider is None:
                    repaired = _internal_failure_repair(
                        work,
                        state_path=state_path,
                        repo_root=repo_root,
                    )
                else:
                    repaired = failure_repair_provider(deepcopy(dict(work)))
                if not isinstance(repaired, Mapping):
                    raise ImprovementDriverError("FAILURE_REPAIR_PROVIDER_RESULT_INVALID")
                repaired_pass = repaired.get("pass") is True
                if not repaired_pass:
                    learning._record_improvement_attempt(
                        wid,
                        status=str(
                            repaired.get("status")
                            or "IMPROVEMENT_REPAIR_ATTEMPT_DID_NOT_CLOSE_ORIGINAL_OBLIGATION"
                        ),
                        reason=(
                            str(
                                repaired.get("reason")
                                or repaired.get("autonomous_replay_reason")
                                or ""
                            ).strip()
                            or None
                        ),
                        state_path=state_path,
                    )
                orphan_retired = repaired.get("orphan_telemetry_retired") is True
                return {
                    "schema": SCHEMA,
                    "status": (
                        "IMPROVEMENT_ADVANCED__ORPHANED_FAILURE_TELEMETRY_RETIRED"
                        if orphan_retired
                        else (
                            "IMPROVEMENT_ADVANCED__FAILURE_REPAIR_REPLAY_VERIFIED"
                            if repaired_pass
                            else "IMPROVEMENT_REPAIR_ATTEMPT_DID_NOT_CLOSE_ORIGINAL_OBLIGATION"
                        )
                    ),
                    "pass": repaired_pass,
                    "progress": repaired_pass,
                    "work_id": wid,
                    "repair": deepcopy(dict(repaired)),
                    "original_failure_repaired": (
                        repaired.get("original_failure_repaired")
                        if orphan_retired
                        else repaired_pass
                    ),
                    "attempt_backoff_recorded": not repaired_pass,
                    "blockers_skipped": blockers,
                    "terminal_authority": False,
                }

            if kind == "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE":
                if episode_verification_provider is None:
                    blockers.append({"work_id": wid, "kind": kind, "blocker": "EPISODE_VERIFICATION_PROVIDER_REQUIRED"})
                    continue
                out = _adapt_success_work(
                    work,
                    state_path=state_path,
                    repo_root=repo_root,
                    success_episode_adapter_provider=success_episode_adapter_provider,
                    episode_verification_provider=episode_verification_provider,
                    skill_verification_provider=skill_verification_provider,
                )
                if (
                    out.get("status")
                    == "IMPROVEMENT_PROVIDER_RETURNED_NO_SUCCESS_ADAPTATION"
                    and not external_success_adapter
                    and not external_episode_verifier
                ):
                    payload = (
                        work.get("payload")
                        if isinstance(work.get("payload"), Mapping)
                        else {}
                    )
                    observation_id = str(payload.get("observation_id") or "").strip()
                    _park_success_work(
                        work,
                        observation_id=observation_id,
                        frontier_sha256=reactivation["frontier_sha256"],
                        state_path=state_path,
                        repo_root=repo_root,
                    )
                    return {
                        "schema": SCHEMA,
                        "status": (
                            "IMPROVEMENT_PARKED__"
                            "CURRENT_OWNED_VERIFICATION_FRONTIER_INCOMPLETE"
                        ),
                        "pass": True,
                        "progress": False,
                        "disposition_recorded": True,
                        "work_id": wid,
                        "observation_id": observation_id,
                        "verification_frontier_sha256": reactivation[
                            "frontier_sha256"
                        ],
                        "epistemic_nonlearnability_proved": False,
                        "observational_inseparability_proved": False,
                        "frontier_expansion_required": True,
                        "permanent_nonlearnability_claimed": False,
                        "blockers_skipped": blockers,
                        "terminal_authority": False,
                    }
                failed = out.get("pass") is not True
                if failed:
                    _record_failed_action_attempt(wid, out, state_path=state_path)
                return {
                    **out,
                    "progress": out.get("pass") is True,
                    "attempt_backoff_recorded": failed,
                    "blockers_skipped": blockers,
                }

            if kind == "REVERIFY_QUARANTINED_SKILL":
                payload = work.get("payload") if isinstance(work.get("payload"), Mapping) else {}
                if payload.get("scope_contraction_safe") is not True:
                    blockers.append({
                        "work_id": wid,
                        "kind": kind,
                        "blocker": "COUNTEREXAMPLE_REVERIFICATION_REQUIRES_FRESH_CANDIDATE_OR_REPLACEMENT",
                    })
                    continue
                from canonical.runtime.r3_quarantine_recovery_v1 import recover_exact_scope
                out = recover_exact_scope(
                    work,
                    state_path=state_path,
                    repo_root=repo_root,
                    skill_verification_provider=skill_verification_provider,
                )
                failed = out.get("pass") is not True
                if failed:
                    _record_failed_action_attempt(wid, out, state_path=state_path)
                return {
                    **out,
                    "progress": out.get("pass") is True,
                    "attempt_backoff_recorded": failed,
                    "blockers_skipped": blockers,
                }

            if kind == "SEEK_VERIFIED_SCOPE_GENERALIZATION":
                if skill_verification_provider is None:
                    blockers.append({
                        "work_id": wid,
                        "kind": kind,
                        "blocker": "SKILL_VERIFICATION_PROVIDER_REQUIRED",
                    })
                    continue
                out = _verify_scope_generalization_work(
                    work,
                    state_path=state_path,
                    repo_root=repo_root,
                    skill_verification_provider=skill_verification_provider,
                )
                failed = out.get("pass") is not True
                if failed:
                    _record_failed_action_attempt(wid, out, state_path=state_path)
                return {
                    **out,
                    "progress": out.get("pass") is True,
                    "attempt_backoff_recorded": failed,
                    "blockers_skipped": blockers,
                }

            if kind == FRONTIER_EXPANSION_KIND:
                payload = work.get("payload")
                repair_reduction = _current_frontier_repair_reduction(
                    work,
                    state_path=state_path,
                    repo_root=repo_root,
                )
                admissible = (
                    set(repair_reduction.get("admissible_repair_classes") or [])
                    if repair_reduction.get("pass") is True
                    else set()
                )
                if (
                    repair_reduction.get("pass") is True
                    and "VERIFIER_PRESERVING_SUCCESS_ADAPTER" not in admissible
                ):
                    evidence_request = repair_reduction.get(
                        "distinguishing_evidence_request"
                    )
                    request_ready = (
                        isinstance(evidence_request, Mapping)
                        and evidence_request.get("pass") is True
                    )
                    evidence_provider = distinguishing_evidence_provider
                    evidence_provider_id = distinguishing_evidence_provider_id
                    if request_ready and evidence_provider is None:
                        from canonical.runtime import r3_retained_distinguishing_evidence_provider_v1 as native_retained_evidence

                        observation_id = str(
                            (payload or {}).get("observation_id") or ""
                        ).strip()
                        if native_retained_evidence.can_acquire(
                            evidence_request,
                            observation_id=observation_id,
                            state_path=state_path,
                            repo_root=repo_root,
                        ):
                            evidence_provider = lambda request: native_retained_evidence.acquire(
                                request,
                                state_path=state_path,
                                repo_root=repo_root,
                            )
                            evidence_provider_id = native_retained_evidence.PROVIDER_ID

                    if request_ready and evidence_provider is not None:
                        if _frontier_acquisition_attempt_consumed(
                            work,
                            provider_id=evidence_provider_id,
                            repo_root=repo_root,
                        ):
                            blockers.append({
                                "work_id": wid,
                                "kind": kind,
                                "blocker": (
                                    "DISTINGUISHING_EVIDENCE_ALREADY_ATTEMPTED_"
                                    "FOR_CURRENT_PROVIDER_AND_FRONTIER"
                                ),
                            })
                            continue
                        from canonical.runtime import r3_distinguishing_evidence_acquisition_v1 as evidence_acquisition

                        acquired = evidence_acquisition.acquire(
                            evidence_request,
                            observation_id=str(
                                (payload or {}).get("observation_id") or ""
                            ),
                            state_path=state_path,
                            provider=evidence_provider,
                            provider_id=evidence_provider_id,
                            improvement_work_id=wid,
                            blocked_success_work_id=str(
                                (payload or {}).get("blocked_success_work_id") or ""
                            ),
                        )
                        if acquired.get("pass") is not True:
                            status = str(
                                acquired.get("status")
                                or "DISTINGUISHING_EVIDENCE_ACQUISITION_FAILED"
                            )
                            _record_frontier_acquisition_attempt(
                                wid,
                                provider_id=evidence_provider_id,
                                frontier_sha256=_owned_success_learning_frontier_sha256(
                                    repo_root=repo_root
                                ),
                                status=status,
                                reason=str(
                                    acquired.get("reason") or status
                                ),
                                state_path=state_path,
                            )
                            return {
                                **acquired,
                                "progress": False,
                                "attempt_backoff_recorded": True,
                                "blockers_skipped": blockers,
                            }
                        new_observation_id = str(
                            acquired.get("new_observation_id") or ""
                        ).strip()
                        _resolve_work(
                            wid,
                            resolved_by=(
                                "DISTINGUISHING_EVIDENCE:"
                                + new_observation_id
                            ),
                            state_path=state_path,
                        )
                        return {
                            **acquired,
                            "progress": True,
                            "attempt_backoff_recorded": False,
                            "blockers_skipped": blockers,
                        }

                    blockers.append({
                        "work_id": wid,
                        "kind": kind,
                        "blocker": (
                            "R3_VERIFICATION_FRONTIER_NEW_DISTINGUISHING_EVIDENCE_REQUIRED"
                            if request_ready
                            else "R3_VERIFICATION_FRONTIER_DISTINGUISHING_EVIDENCE_REQUEST_UNAVAILABLE"
                        ),
                        "boundary_root": (
                            payload.get("boundary_root")
                            if isinstance(payload, Mapping)
                            else "R1_CAPABILITY_ACQUISITION"
                        ),
                        "repair_class_reduction": deepcopy(
                            dict(repair_reduction)
                        ),
                        "distinguishing_evidence_request": (
                            deepcopy(dict(evidence_request))
                            if isinstance(evidence_request, Mapping)
                            else None
                        ),
                        "distinguishing_evidence_provider_bound": (
                            evidence_provider is not None
                        ),
                        "adapter_acquisition_provider_skipped": True,
                        "replay_original_success": False,
                    })
                    continue

                acquisition_provider = verification_frontier_acquisition_provider
                acquisition_provider_id = verification_frontier_acquisition_provider_id
                if acquisition_provider is None:
                    from canonical.runtime import r3_structural_bound_rule_acquisition_v1 as native_structural_acquisition

                    if native_structural_acquisition.can_acquire(
                        work,
                        state_path=state_path,
                        repo_root=repo_root,
                    ):
                        acquisition_provider = lambda request: native_structural_acquisition.acquire(
                            request,
                            state_path=state_path,
                            repo_root=repo_root,
                        )
                        acquisition_provider_id = native_structural_acquisition.PROVIDER_ID

                if acquisition_provider is None:
                    from canonical.runtime import r3_root1_adapter_gap_witness_v1 as root1_gap

                    compiled_gap = root1_gap.compile_gap(
                        work,
                        state_path=state_path,
                        repo_root=repo_root,
                        acquisition_provider_bound=False,
                    )
                    gap_established = (
                        isinstance(compiled_gap, Mapping)
                        and compiled_gap.get("pass") is True
                        and compiled_gap.get("root1_positive_gap_established") is True
                    )
                    blockers.append({
                        "work_id": wid,
                        "kind": kind,
                        "blocker": (
                            "ROOT1_CONSTRUCTIVE_R3_VERIFICATION_FRONTIER_GAP__"
                            "NO_BOUND_ACQUISITION_ROUTE"
                            if gap_established
                            else "ROOT1_VERIFICATION_CAPABILITY_ACQUISITION_REQUIRED"
                        ),
                        "boundary_root": (
                            payload.get("boundary_root")
                            if isinstance(payload, Mapping)
                            else "R1_CAPABILITY_ACQUISITION"
                        ),
                        "required_capability_class": (
                            payload.get("required_capability_class")
                            if isinstance(payload, Mapping)
                            else None
                        ),
                        "root1_positive_gap_established": gap_established,
                        "root1_gap_witness": deepcopy(dict(compiled_gap)),
                        "replay_original_success": False,
                    })
                    continue
                out = _execute_frontier_acquisition(
                    work,
                    state_path=state_path,
                    repo_root=repo_root,
                    provider=acquisition_provider,
                    provider_id=acquisition_provider_id,
                    repair_reduction=(
                        repair_reduction
                        if repair_reduction.get("pass") is True
                        else None
                    ),
                )
                return {
                    **out,
                    "blockers_skipped": blockers,
                }

            if kind == "COLLECT_MATCHING_VERIFIED_EPISODE":
                blockers.append({
                    "work_id": wid,
                    "kind": kind,
                    "blocker": "WAITING_FOR_NEW_INDEPENDENTLY_VERIFIED_EXPERIENCE",
                })
                continue

            blockers.append({"work_id": wid, "kind": kind, "blocker": "UNSUPPORTED_IMPROVEMENT_KIND"})
        except Exception as exc:
            failure = {
                "schema": SCHEMA,
                "status": "IMPROVEMENT_ACTION_EXCEPTION",
                "pass": False,
                "progress": False,
                "work_id": wid,
                "kind": kind,
                "reason": type(exc).__name__ + ":" + str(exc),
                "attempt_backoff_recorded": True,
                "blockers_skipped": blockers,
                "terminal_authority": False,
            }
            _record_failed_action_attempt(wid, failure, state_path=state_path)
            return failure

    return {
        "schema": SCHEMA,
        "status": "IMPROVEMENT_QUEUE_HAS_NO_CURRENTLY_ACTIONABLE_WORK",
        "pass": True,
        "progress": False,
        "pending_count": len(pending),
        "blockers": blockers,
        "terminal_authority": False,
    }


def drain(
    *,
    state_path: str | Path = learning.DEFAULT_STATE_PATH,
    repo_root: str | Path = ROOT,
    episode_verification_provider=None,
    skill_verification_provider=None,
    success_episode_adapter_provider=None,
    failure_repair_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    verification_frontier_acquisition_provider: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    verification_frontier_acquisition_provider_id: str = (
        "HOST_VERIFICATION_FRONTIER_ACQUISITION_PROVIDER"
    ),
    distinguishing_evidence_provider: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    distinguishing_evidence_provider_id: str = (
        "HOST_R3_DISTINGUISHING_EVIDENCE_PROVIDER"
    ),
    max_actions: int = 4,
) -> dict[str, Any]:
    if isinstance(max_actions, bool) or not isinstance(max_actions, int) or max_actions < 1 or max_actions > 32:
        raise ImprovementDriverError("MAX_ACTIONS_INVALID")
    actions: list[dict[str, Any]] = []
    for _ in range(max_actions):
        result = advance_once(
            state_path=state_path,
            repo_root=repo_root,
            episode_verification_provider=episode_verification_provider,
            skill_verification_provider=skill_verification_provider,
            success_episode_adapter_provider=success_episode_adapter_provider,
            failure_repair_provider=failure_repair_provider,
            verification_frontier_acquisition_provider=(
                verification_frontier_acquisition_provider
            ),
            verification_frontier_acquisition_provider_id=(
                verification_frontier_acquisition_provider_id
            ),
            distinguishing_evidence_provider=distinguishing_evidence_provider,
            distinguishing_evidence_provider_id=distinguishing_evidence_provider_id,
        )
        actions.append(result)
        if result.get("progress") is not True:
            if (
                result.get("attempt_backoff_recorded") is True
                or result.get("disposition_recorded") is True
            ):
                # Failed attempts back off until evidence changes. A parked success
                # is terminal only for the exact current retained evidence +
                # verifier frontier. Neither may starve unrelated compounding work.
                continue
            break
    final_state = learning.load_state(state_path)
    return {
        "schema": SCHEMA,
        "status": (
            "IMPROVEMENT_QUEUE_ADVANCED"
            if any(row.get("progress") is True for row in actions)
            else "IMPROVEMENT_QUEUE_STABLE"
        ),
        "pass": all(row.get("pass") is True for row in actions),
        "progress_count": sum(1 for row in actions if row.get("progress") is True),
        "actions": actions,
        "next_improvement_action": learning.next_improvement_action(state_path=state_path),
        "state_stats": deepcopy(final_state.get("stats", {})),
        "terminal_authority": False,
    }
