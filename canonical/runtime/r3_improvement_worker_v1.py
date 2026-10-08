"""Bounded executor for R3's durable improvement queue.

The R3 state machine already knows what should improve next. This module turns
the actionable subset of that queue into work immediately when the required
independent verifier is available. It never self-certifies: providers propose
content-addressed verification bindings and the existing authenticators remain
the only authority.

Non-actionable evidence-acquisition items remain pending rather than being
falsely resolved.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import autonomous_verified_self_improvement_v1 as r3

SCHEMA = "PROJECT_BRAIN_R3_IMPROVEMENT_WORKER_V1"
DEFAULT_MAX_ACTIONS = 4
MAX_EVIDENCE_BYTES = 1_000_000


def _pending(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    queue = state.get("improvement_queue", {})
    if not isinstance(queue, Mapping):
        return []
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


def _identity_matches_episode(work: Mapping[str, Any], episode: Mapping[str, Any]) -> bool:
    identity = work.get("identity", {})
    if not isinstance(identity, Mapping):
        return False
    return (
        str(identity.get("episode_id") or "") == str(episode.get("episode_id") or "")
        and str(identity.get("scope_id") or "") == str(episode.get("scope_id") or "")
        and str(identity.get("program_sha256") or "") == str(episode.get("program_sha256") or "")
        and str(identity.get("trace_sha256") or "") == str(episode.get("trace_sha256") or "")
    )


def _safe_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
    r3._validate_retry_value(value, path="improvement_evidence")
    copied = deepcopy(dict(value))
    raw = json.dumps(
        copied,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    ).encode("utf-8")
    if len(raw) > MAX_EVIDENCE_BYTES:
        raise r3.SelfImprovementError("IMPROVEMENT_EVIDENCE_TOO_LARGE")
    return copied


def capture_pending_episode_evidence(
    solver_output: Mapping[str, Any] | None,
    *,
    problem: Mapping[str, Any],
    state_path: str | Path = r3.DEFAULT_STATE_PATH,
    retry_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Retain the minimum replay/authentication evidence for deferred verification."""
    if not isinstance(solver_output, Mapping) or solver_output.get("pass") is not True:
        return {"schema": SCHEMA, "status": "NO_SUCCESS_EPISODE_TO_CAPTURE", "pass": True}
    if solver_output.get("current_episode_verified") is True:
        return {"schema": SCHEMA, "status": "EPISODE_ALREADY_VERIFIED", "pass": True}

    episode = solver_output.get("current_episode")
    trace = solver_output.get("trace")
    if not isinstance(episode, Mapping):
        return {"schema": SCHEMA, "status": "NO_CURRENT_EPISODE_TO_CAPTURE", "pass": True}
    if not isinstance(trace, list):
        return {
            "schema": SCHEMA,
            "status": "DEFERRED_EPISODE_EVIDENCE_BLOCKED__TRACE_NOT_LIST",
            "pass": False,
        }

    state = r3.load_state(state_path)
    work = next(
        (
            row
            for row in _pending(state)
            if row.get("kind") == "VERIFY_EPISODE"
            and _identity_matches_episode(row, episode)
        ),
        None,
    )
    if not isinstance(work, Mapping):
        return {
            "schema": SCHEMA,
            "status": "NO_MATCHING_VERIFY_EPISODE_WORK",
            "pass": True,
        }

    evidence = {
        "problem": deepcopy(dict(problem)),
        "solver_output": deepcopy(dict(solver_output)),
        "retry_context": deepcopy(dict(retry_context)) if isinstance(retry_context, Mapping) else None,
    }
    try:
        evidence = _safe_evidence(evidence)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "DEFERRED_EPISODE_EVIDENCE_BLOCKED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "work_id": work.get("work_id"),
        }

    store = state.setdefault("improvement_evidence", {})
    if not isinstance(store, dict):
        return {
            "schema": SCHEMA,
            "status": "IMPROVEMENT_EVIDENCE_STORE_INVALID",
            "pass": False,
        }
    wid = str(work.get("work_id") or "")
    store[wid] = {
        "schema": "PROJECT_BRAIN_R3_DEFERRED_EPISODE_EVIDENCE_V1",
        "work_id": wid,
        "episode_id": episode.get("episode_id"),
        "scope_id": episode.get("scope_id"),
        "program_sha256": episode.get("program_sha256"),
        "trace_sha256": episode.get("trace_sha256"),
        "evidence": evidence,
    }
    r3._write_state(state, state_path)
    return {
        "schema": SCHEMA,
        "status": "DEFERRED_EPISODE_EVIDENCE_PERSISTED",
        "pass": True,
        "work_id": wid,
    }


def _mark_attempt(
    work_id: str,
    *,
    state_path: str | Path,
    status: str,
    reason: str | None = None,
) -> None:
    state = r3.load_state(state_path)
    row = state.get("improvement_queue", {}).get(work_id)
    if isinstance(row, dict) and row.get("status") == "PENDING":
        row["worker_attempts"] = int(row.get("worker_attempts", 0)) + 1
        row["last_worker_status"] = status
        row["last_worker_reason"] = reason
        r3._write_state(state, state_path)


def _source_episodes(state: Mapping[str, Any], candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    wanted = {str(x) for x in candidate.get("source_episode_ids", []) if str(x)}
    rows = []
    for raw in state.get("episodes", {}).values():
        if not isinstance(raw, Mapping):
            continue
        if str(raw.get("episode_id") or "") in wanted:
            rows.append(deepcopy(dict(raw)))
    rows.sort(key=lambda row: (str(row.get("scope_id") or ""), str(row.get("episode_id") or "")))
    return rows


def _verify_episode_work(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
    episode_verification_provider,
    skill_verification_provider,
) -> dict[str, Any]:
    wid = str(work.get("work_id") or "")
    state = r3.load_state(state_path)
    evidence_store = state.get("improvement_evidence", {})
    record = evidence_store.get(wid) if isinstance(evidence_store, Mapping) else None
    if not isinstance(record, Mapping):
        return {
            "pass": False,
            "status": "VERIFY_EPISODE_BLOCKED__EVIDENCE_MISSING",
            "work_id": wid,
        }
    evidence = record.get("evidence")
    if not isinstance(evidence, Mapping):
        return {
            "pass": False,
            "status": "VERIFY_EPISODE_BLOCKED__EVIDENCE_INVALID",
            "work_id": wid,
        }
    problem = evidence.get("problem")
    solver_output = evidence.get("solver_output")
    if not isinstance(problem, Mapping) or not isinstance(solver_output, Mapping):
        return {
            "pass": False,
            "status": "VERIFY_EPISODE_BLOCKED__EVIDENCE_INVALID",
            "work_id": wid,
        }
    episode = solver_output.get("current_episode")
    trace = solver_output.get("trace")
    if not isinstance(episode, Mapping) or not isinstance(trace, list):
        return {
            "pass": False,
            "status": "VERIFY_EPISODE_BLOCKED__EPISODE_OR_TRACE_INVALID",
            "work_id": wid,
        }

    request = {
        "kind": "EPISODE_VERIFICATION",
        "problem": deepcopy(dict(problem)),
        "episode": deepcopy(dict(episode)),
        "trace": deepcopy(trace),
        "fact_capsule_head_hash": str(solver_output.get("state_capsule_head_hash") or ""),
        "value_capsule_head_hash": str(solver_output.get("value_capsule_head_hash") or ""),
    }
    binding = episode_verification_provider(deepcopy(request))
    if binding is None:
        return {
            "pass": False,
            "status": "VERIFY_EPISODE_PROVIDER_RETURNED_NO_BINDING",
            "work_id": wid,
        }
    if not isinstance(binding, Mapping):
        return {
            "pass": False,
            "status": "VERIFY_EPISODE_PROVIDER_RESULT_INVALID",
            "work_id": wid,
        }

    auth = r3.authenticate_episode_verification(
        binding,
        problem=problem,
        episode=episode,
        trace=trace,
        fact_capsule_head_hash=request["fact_capsule_head_hash"],
        value_capsule_head_hash=request["value_capsule_head_hash"],
        repo_root=repo_root,
    )
    if auth.get("pass") is not True:
        return {
            "pass": False,
            "status": "VERIFY_EPISODE_AUTHENTICATION_FAILED",
            "reason": str(auth.get("reason") or ""),
            "work_id": wid,
        }

    verified_out = deepcopy(dict(solver_output))
    verified_out["current_episode"] = deepcopy(dict(auth["authenticated_episode"]))
    verified_out["current_episode_verified"] = True
    verified_out["episode_verification_authentication"] = deepcopy(dict(auth))
    verified_out["episode_verification_error"] = None

    current = verified_out["current_episode"]
    prior = r3._prior_verified_episodes(
        state,
        scope_id=str(current.get("scope_id") or ""),
        episode_id=str(current.get("episode_id") or ""),
    )
    generalization = r3._all_prior_verified_episodes(
        state,
        episode_id=str(current.get("episode_id") or ""),
    )
    verified_out = r3._post_execution_independent_verification(
        verified_out,
        problem=problem,
        prior_verified_episode_records=prior,
        generalization_episode_records=generalization,
        repo_root=repo_root,
        episode_verification_provider=None,
        skill_verification_provider=skill_verification_provider,
    )
    integrated = r3.integrate_solver_output(
        verified_out,
        state_path=state_path,
        retry_context=(
            evidence.get("retry_context")
            if isinstance(evidence.get("retry_context"), Mapping)
            else None
        ),
    )

    fresh = r3.load_state(state_path)
    store = fresh.get("improvement_evidence")
    if isinstance(store, dict):
        store.pop(wid, None)
        r3._write_state(fresh, state_path)
    return {
        "pass": True,
        "status": "VERIFY_EPISODE_COMPLETED",
        "work_id": wid,
        "learning": integrated,
        "skill_promoted_in_same_turn": integrated.get("permanent_reuse_authorized") is True,
    }


def _verify_skill_work(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
    skill_verification_provider,
) -> dict[str, Any]:
    wid = str(work.get("work_id") or "")
    payload = work.get("payload")
    candidate = payload.get("candidate") if isinstance(payload, Mapping) else None
    if not isinstance(candidate, Mapping):
        return {
            "pass": False,
            "status": "VERIFY_SKILL_BLOCKED__CANDIDATE_MISSING",
            "work_id": wid,
        }
    state = r3.load_state(state_path)
    sources = _source_episodes(state, candidate)
    request = {
        "kind": "SKILL_VERIFICATION",
        "candidate": deepcopy(dict(candidate)),
        "current_episode": deepcopy(sources[-1]) if sources else {},
    }
    binding = skill_verification_provider(deepcopy(request))
    if binding is None:
        return {
            "pass": False,
            "status": "VERIFY_SKILL_PROVIDER_RETURNED_NO_BINDING",
            "work_id": wid,
        }
    if not isinstance(binding, Mapping):
        return {
            "pass": False,
            "status": "VERIFY_SKILL_PROVIDER_RESULT_INVALID",
            "work_id": wid,
        }
    auth = r3.authenticate_skill_verification(candidate, binding, repo_root=repo_root)
    if auth.get("pass") is not True:
        return {
            "pass": False,
            "status": "VERIFY_SKILL_AUTHENTICATION_FAILED",
            "reason": str(auth.get("reason") or ""),
            "work_id": wid,
        }
    verified = auth.get("verified_skill")
    if not isinstance(verified, Mapping):
        return {
            "pass": False,
            "status": "VERIFY_SKILL_AUTHENTICATOR_OUTPUT_INVALID",
            "work_id": wid,
        }
    integrated = r3.integrate_solver_output(
        {
            "pass": True,
            "status": "SOLVED__VERIFIED_EXECUTABLE_SKILL_READY",
            "skill_candidate": deepcopy(dict(candidate)),
            "verified_executable_skill": deepcopy(dict(verified)),
            "verified_skill_reuse_authorized": verified.get("reuse_authorized") is True,
        },
        state_path=state_path,
    )
    return {
        "pass": True,
        "status": "VERIFY_SKILL_COMPLETED",
        "work_id": wid,
        "learning": integrated,
        "permanent_reuse_authorized": integrated.get("permanent_reuse_authorized") is True,
    }


def advance_improvement_queue(
    *,
    state_path: str | Path = r3.DEFAULT_STATE_PATH,
    repo_root: str | Path = r3.ROOT,
    episode_verification_provider=None,
    skill_verification_provider=None,
    max_actions: int = DEFAULT_MAX_ACTIONS,
) -> dict[str, Any]:
    """Consume currently actionable R3 work, bounded and fail-closed.

    Evidence-acquisition items are intentionally left pending. They are event-driven
    prerequisites, not tasks the worker is allowed to fake as complete.
    """
    if not isinstance(max_actions, int) or isinstance(max_actions, bool) or not 1 <= max_actions <= 16:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "MAX_ACTIONS_INVALID",
        }

    attempted: set[str] = set()
    results: list[dict[str, Any]] = []
    for _ in range(max_actions):
        state = r3.load_state(state_path)
        selected = None
        for work in _pending(state):
            wid = str(work.get("work_id") or "")
            if not wid or wid in attempted:
                continue
            kind = str(work.get("kind") or "")
            if kind == "VERIFY_EPISODE" and episode_verification_provider is not None:
                evidence = state.get("improvement_evidence", {})
                if isinstance(evidence, Mapping) and isinstance(evidence.get(wid), Mapping):
                    selected = work
                    break
            if kind == "VERIFY_SKILL_CANDIDATE" and skill_verification_provider is not None:
                selected = work
                break
        if selected is None:
            break

        wid = str(selected.get("work_id") or "")
        attempted.add(wid)
        try:
            if selected.get("kind") == "VERIFY_EPISODE":
                result = _verify_episode_work(
                    selected,
                    state_path=state_path,
                    repo_root=repo_root,
                    episode_verification_provider=episode_verification_provider,
                    skill_verification_provider=skill_verification_provider,
                )
            else:
                result = _verify_skill_work(
                    selected,
                    state_path=state_path,
                    repo_root=repo_root,
                    skill_verification_provider=skill_verification_provider,
                )
        except Exception as exc:
            result = {
                "pass": False,
                "status": "IMPROVEMENT_ACTION_EXCEPTION",
                "reason": type(exc).__name__ + ":" + str(exc),
                "work_id": wid,
            }

        _mark_attempt(
            wid,
            state_path=state_path,
            status=str(result.get("status") or ""),
            reason=str(result.get("reason") or "") or None,
        )
        results.append(result)

    state = r3.load_state(state_path)
    pending = _pending(state)
    blocked_kinds = sorted(
        {
            str(row.get("kind") or "")
            for row in pending
            if str(row.get("work_id") or "") not in attempted
        }
    )
    return {
        "schema": SCHEMA,
        "status": (
            "IMPROVEMENT_QUEUE_ADVANCED"
            if any(row.get("pass") is True for row in results)
            else "NO_ACTIONABLE_VERIFICATION_WORK"
        ),
        "pass": True,
        "attempted_count": len(results),
        "completed_count": sum(1 for row in results if row.get("pass") is True),
        "results": results,
        "pending_count": len(pending),
        "pending_nonactionable_or_unprovided_kinds": blocked_kinds,
        "next_improvement_action": r3.next_improvement_action(state_path=state_path),
        "terminal_authority": False,
    }
