"""Executable consumer for the R3 durable improvement queue.

The queue is not authority. This driver only advances work when the exact
independent-verification or repair authority needed by that work is available.
Unavailable authority leaves work pending with an explicit blocker instead of
silently turning a TODO into a capability claim.
"""
from __future__ import annotations

from copy import deepcopy
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

    candidate = learning._candidate_from_verified_skill(raw_skill)
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
    "SEEK_VERIFIED_SCOPE_GENERALIZATION",
}


def _attempt_already_consumed_current_evidence(work: Mapping[str, Any]) -> bool:
    if str(work.get("kind") or "") not in ATTEMPT_BACKOFF_KINDS:
        return False
    last = work.get("last_attempt_observations")
    if last is None:
        return False
    return int(last) >= int(work.get("observations", 0))


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
) -> dict[str, Any]:
    """Execute the highest-priority *actionable* pending improvement exactly once."""
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
        if _attempt_already_consumed_current_evidence(work):
            blockers.append({
                "work_id": wid,
                "kind": kind,
                "blocker": "WORK_ALREADY_ATTEMPTED_FOR_CURRENT_EVIDENCE",
            })
            continue
        try:
            if kind == "VERIFY_SKILL_CANDIDATE":
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
                return {
                    "schema": SCHEMA,
                    "status": (
                        "IMPROVEMENT_ADVANCED__FAILURE_REPAIR_REPLAY_VERIFIED"
                        if repaired_pass
                        else "IMPROVEMENT_REPAIR_ATTEMPT_DID_NOT_CLOSE_ORIGINAL_OBLIGATION"
                    ),
                    "pass": repaired_pass,
                    "progress": repaired_pass,
                    "work_id": wid,
                    "repair": deepcopy(dict(repaired)),
                    "attempt_backoff_recorded": not repaired_pass,
                    "blockers_skipped": blockers,
                    "terminal_authority": False,
                }

            if kind == "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE":
                if success_episode_adapter_provider is None:
                    blockers.append({"work_id": wid, "kind": kind, "blocker": "SUCCESS_EPISODE_ADAPTER_PROVIDER_REQUIRED"})
                    continue
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
                blockers.append({
                    "work_id": wid,
                    "kind": kind,
                    "blocker": "COUNTEREXAMPLE_REVERIFICATION_REQUIRES_FRESH_CANDIDATE_OR_REPLACEMENT",
                })
                continue

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
        )
        actions.append(result)
        if result.get("progress") is not True:
            if result.get("attempt_backoff_recorded") is True:
                # The failed attempt is now suppressed until its evidence
                # observation count changes. Continue immediately so a rejected
                # verifier/adapter item cannot starve unrelated compounding work.
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
