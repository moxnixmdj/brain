"""Universal Verified Adaptive Solver V5: authenticated continuation.

V5 operationalizes authenticated resume for the V4 universal adaptive solver.

Fresh missions delegate to V4.
Resumed missions first pass universal_solver_resume_authenticator_v1, which
re-verifies:
- the full task/capability contract,
- historical built-in verifier results,
- independently authenticated effect semantics,
- historical verified tool-pack identity,
- current external filesystem bytes,
- global state-capsule lineage.

Only then may V5 continue planning from the authenticated verified facts and
capsule without replaying prior effects.

V5 preserves V4's route tournament and skill-induction boundaries. It also
rejects a newly executed effect that mutates an external target already bound by
the resumed state: the effect has occurred, but the old logical state may now be
invalid, so authenticated recovery/reconciliation is required before any new
fact is minted.

No terminal/capability/ownership credit is granted here.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.capability_planner import PlanningFailure, plan_capabilities
from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime import universal_verified_adaptive_solver_v4 as v4
from canonical.runtime.universal_solver_resume_authenticator_v1 import authenticate
from canonical.runtime.universal_solver_state_capsule_v1 import (
    append_verified_transition as append_state_transition,
    verify_targets as verify_state_targets,
)
from canonical.runtime.executable_skill_program_v7 import (
    ExecutableSkillProgramError,
    induce_candidate,
)

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V5"


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        **extra,
    }


def _effect_targets_from_outcome(outcome: Mapping[str, Any]) -> set[str]:
    sandbox = outcome.get("sandbox_rel")
    receipts = outcome.get("receipts")
    if not isinstance(sandbox, str) or not isinstance(receipts, list):
        return set()
    out: set[str] = set()
    for row in receipts:
        if isinstance(row, Mapping) and isinstance(row.get("path"), str):
            out.add(sandbox.rstrip("/") + "/" + row["path"].lstrip("/"))
    return out


def _prior_effect_targets(authenticated: Mapping[str, Any]) -> set[str]:
    out: set[str] = set()
    for row in authenticated.get("reverified_effects") or []:
        if not isinstance(row, Mapping):
            continue
        for rec in row.get("current_world_receipts") or []:
            if isinstance(rec, Mapping) and isinstance(rec.get("path"), str):
                out.add(rec["path"])
    return out


def _finish(
    *,
    problem: Mapping[str, Any],
    current: list[str],
    trace: list[dict[str, Any]],
    capsule: Mapping[str, Any],
    attempts: list[dict[str, Any]],
    counterexamples: list[dict[str, Any]],
    falsified: set[str],
    deferred: set[str],
    episode_id: str,
    scope_id: str,
    episode_verification_receipt: Mapping[str, Any] | None,
    prior_verified_episodes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    targets = v4._tokens(problem.get("target_effects", []), "TARGET_EFFECTS", allow_empty=False)
    verdict = verify_state_targets(capsule, targets)
    if verdict.get("pass") is not True:
        return _fail("TARGET_FACTS_WITHOUT_VALID_GLOBAL_LINEAGE", state_target_verdict=verdict)
    caps = v4._caps(problem)
    invalidators = (
        ["route_falsified:" + x for x in sorted(falsified)]
        + ["route_deferred:" + x for x in sorted(deferred)]
    )
    ep = v4._episode(
        problem,
        trace,
        caps,
        episode_id,
        scope_id,
        invalidators,
        episode_verification_receipt,
    )
    ep_ok, ep_error = v4._episode_receipt_ok(ep, episode_verification_receipt)
    candidate = None
    candidate_error = None
    if ep_ok and prior_verified_episodes:
        try:
            candidate = induce_candidate([*prior_verified_episodes, ep])
        except ExecutableSkillProgramError as exc:
            candidate_error = str(exc)
    return {
        "schema": SCHEMA,
        "status": (
            "SOLVED__SKILL_CANDIDATE_READY" if candidate is not None
            else "SOLVED__VERIFIED_EPISODE" if ep_ok
            else "SOLVED__EPISODE_VERIFICATION_REQUIRED"
        ),
        "pass": True,
        "verified_facts": current,
        "trace": trace,
        "attempts": attempts,
        "counterexamples": counterexamples,
        "falsified_capability_ids": sorted(falsified),
        "deferred_capability_ids": sorted(deferred),
        "state_capsule": deepcopy(dict(capsule)),
        "state_capsule_head_hash": capsule.get("head_hash"),
        "state_target_verdict": verdict,
        "current_episode": ep,
        "current_episode_verified": ep_ok,
        "episode_verification_error": ep_error,
        "skill_candidate": candidate,
        "skill_candidate_error": candidate_error,
        "skill_candidate_reuse_authorized": bool(
            candidate and candidate.get("reuse_authorized")
        ),
        "resumed_execution": True,
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def run(
    problem: Mapping[str, Any],
    *,
    proposal_packets: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    repo_root: str | Path,
    effect_root: str | Path | None = None,
    resume_state: Mapping[str, Any] | None = None,
    episode_id: str = "episode",
    scope_id: str = "scope",
    episode_verification_receipt: Mapping[str, Any] | None = None,
    prior_verified_episodes: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Run fresh via V4, or continue only from an authenticated resume state."""
    if resume_state is None:
        return v4.run(
            problem,
            proposal_packets=proposal_packets,
            repo_root=repo_root,
            effect_root=None if effect_root is None else str(effect_root),
            episode_id=episode_id,
            scope_id=scope_id,
            episode_verification_receipt=episode_verification_receipt,
            prior_verified_episodes=prior_verified_episodes,
        )

    try:
        auth = authenticate(
            problem,
            resume_state,
            repo_root=repo_root,
            effect_root=effect_root,
        )
        if auth.get("pass") is not True:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__RESUME_AUTHENTICATION_FAILED",
                "pass": False,
                "resume_authentication": auth,
                "terminal_authority": False,
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
            }

        caps = v4._caps(problem)
        semantics = {
            cid: v4._authenticate_effect_semantics(problem, cap, repo_root=repo_root)
            for cid, cap in caps.items()
        }
        targets = v4._tokens(problem.get("target_effects", []), "TARGET_EFFECTS", allow_empty=False)
        current = list(auth["verified_facts"])
        trace = [dict(x) for x in auth["trace"]]
        capsule = deepcopy(dict(auth["state_capsule"]))
        existing_effect_targets = _prior_effect_targets(auth)
        attempts: list[dict[str, Any]] = []
        counterexamples: list[dict[str, Any]] = []
        falsified: set[str] = set()
        deferred: set[str] = set()
        excluded: set[str] = set()
        pending: list[dict[str, Any]] = []

        max_cycles = int(problem.get("max_solver_cycles", 256))
        if max_cycles < 1 or max_cycles > 10000:
            return _fail("MAX_SOLVER_CYCLES_INVALID")
        episode_id = v4._tok(episode_id, "EPISODE_ID")
        scope_id = v4._tok(scope_id, "SCOPE_ID")

        for local_cycle in range(max_cycles):
            if set(targets).issubset(current):
                return _finish(
                    problem=problem,
                    current=current,
                    trace=trace,
                    capsule=capsule,
                    attempts=attempts,
                    counterexamples=counterexamples,
                    falsified=falsified,
                    deferred=deferred,
                    episode_id=episode_id,
                    scope_id=scope_id,
                    episode_verification_receipt=episode_verification_receipt,
                    prior_verified_episodes=prior_verified_episodes,
                )

            planning_problem = v4._filtered_problem(problem, current, excluded)
            if not planning_problem.get("capabilities"):
                break
            try:
                plan = plan_capabilities(planning_problem)
            except PlanningFailure:
                break
            if not plan.get("plan"):
                break
            cid = str(plan["plan"][0])
            cap = caps[cid]
            single = v4._single_problem(problem, current, cap)
            out = v1.run(
                single,
                proposal_packets=proposal_packets,
                effect_root=None if effect_root is None else str(effect_root),
            )
            attempts.append({
                "local_cycle": local_cycle,
                "global_cycle": len(trace),
                "capability_id": cid,
                "status": out.get("status"),
                "excluded_capability_ids": sorted(excluded),
            })

            if out.get("pass") is True and out.get("status") == "SOLVED__ALL_TARGET_EFFECTS_VERIFIED":
                rows = [
                    x for x in (out.get("trace") or [])
                    if isinstance(x, Mapping) and x.get("capability_id") == cid
                ]
                if len(rows) != 1:
                    return _fail("SINGLE_CAPABILITY_TRACE_CARDINALITY_INVALID:" + cid)
                row = dict(rows[0])
                row["cycle"] = len(trace)
                row["verifier_success_condition"] = semantics[cid]["verifier_success_condition"]
                row["effect_semantics_receipt"] = semantics[cid]["receipt"]
                row["effect_semantics_verification"] = semantics[cid]["verification"]
                row["effect_semantics_authenticated"] = True
                row["independent_effect_semantics_verifier_id"] = semantics[cid]["independent_verifier_id"]
                row["new_verified_facts"] = list(semantics[cid]["effects"])

                if row.get("effect_outcome") is not None:
                    outcome = row["effect_outcome"]
                    new_targets = _effect_targets_from_outcome(outcome)
                    collisions = sorted(existing_effect_targets & new_targets)
                    if collisions:
                        return {
                            "schema": SCHEMA,
                            "status": "EFFECT_TARGET_COLLISION__AUTHENTICATED_RECOVERY_REQUIRED",
                            "pass": False,
                            "capability_id": cid,
                            "colliding_effect_targets": collisions,
                            "verified_facts": current,
                            "trace": trace,
                            "state_capsule": capsule,
                            "state_capsule_head_hash": capsule.get("head_hash"),
                            "effect_already_occurred": True,
                            "reason": (
                                "NEW_EFFECT_MUTATED_A_TARGET_BOUND_BY_THE_RESUMED_STATE__"
                                "OLD_LOGICAL_FACTS_MAY_NO_LONGER_DESCRIBE_CURRENT_WORLD"
                            ),
                            "terminal_authority": False,
                            "capability_credit_delta": 0,
                            "ownership_credit_delta": 0,
                        }
                    existing_effect_targets.update(new_targets)

                capsule = append_state_transition(
                    capsule,
                    capability=cap,
                    trace_row=row,
                )
                current = sorted(set(current) | set(row["new_verified_facts"]))
                trace.append(row)
                continue

            if v4._effect_may_have_occurred(cap, out):
                return {
                    "schema": SCHEMA,
                    "status": "EFFECT_OUTCOME_UNRESOLVED__AUTHENTICATED_RECOVERY_REQUIRED",
                    "pass": False,
                    "capability_id": cid,
                    "solver_v1_result": out,
                    "verified_facts": current,
                    "trace": trace,
                    "attempts": attempts,
                    "state_capsule": capsule,
                    "state_capsule_head_hash": capsule.get("head_hash"),
                    "terminal_authority": False,
                    "capability_credit_delta": 0,
                    "ownership_credit_delta": 0,
                }

            complete = v4._complete_route_failure(cap, out)
            counterexamples.append({
                "local_cycle": local_cycle,
                "global_cycle": len(trace),
                "capability_id": cid,
                "solver_status": out.get("status"),
                "route_falsified_for_current_contract": complete,
                "reason": out.get("reason"),
            })
            pending.append(out)
            excluded.add(cid)
            (falsified if complete else deferred).add(cid)

        if deferred:
            first = next(
                (
                    x for x in pending
                    if x.get("next_capability_id") in deferred
                    and x.get("status") in {"NEED_PROPOSAL", "NEED_MORE_INFORMATION"}
                ),
                pending[0] if pending else None,
            )
            return {
                "schema": SCHEMA,
                "status": (
                    "AUTHENTICATED_RESUME_REQUIRED_AFTER_PARTIAL_EFFECTFUL_PROGRESS"
                    if existing_effect_targets
                    else "UNRESOLVED__ALTERNATIVE_ROUTES_EXHAUSTED__DEFERRED_ROUTE_REMAINS"
                ),
                "pass": False,
                "verified_facts": current,
                "trace": trace,
                "attempts": attempts,
                "counterexamples": counterexamples,
                "falsified_capability_ids": sorted(falsified),
                "deferred_capability_ids": sorted(deferred),
                "next_required_input": None if first is None else {
                    "capability_id": first.get("next_capability_id"),
                    "status": first.get("status"),
                    "proposal_request": first.get("proposal_request"),
                    "reason": first.get("reason"),
                    "detail": first.get("detail"),
                },
                "state_capsule": capsule,
                "state_capsule_head_hash": capsule.get("head_hash"),
                "terminal_authority": False,
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
            }

        return {
            "schema": SCHEMA,
            "status": (
                "AUTHENTICATED_RESUME_REQUIRED_FOR_CAPABILITY_DISCOVERY_AFTER_EFFECT"
                if existing_effect_targets
                else "CAPABILITY_DISCOVERY_REQUIRED__ALL_DECLARED_ROUTES_FALSIFIED_OR_UNREACHABLE"
            ),
            "pass": False,
            "verified_facts": current,
            "trace": trace,
            "attempts": attempts,
            "counterexamples": counterexamples,
            "falsified_capability_ids": sorted(falsified),
            "deferred_capability_ids": sorted(deferred),
            "target_effects": targets,
            "state_capsule": capsule,
            "state_capsule_head_hash": capsule.get("head_hash"),
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
