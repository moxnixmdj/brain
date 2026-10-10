"""Universal Verified Adaptive Solver V8: authenticated learning evidence.

V8 preserves V7 authenticated cross-run continuity and closes the learning
self-certification boundary. Current and prior episodes may enter skill induction
only through content-addressed episode-verification receipts with separate
independent-verification receipts.

V7 preserves V6 content-bound value composition and adds authenticated resume.

A prior run may be resumed only from an independently verified, content-addressed
resume receipt that binds the exact problem, task/episode/scope identities, fact
and value capsule heads, prior trace, and reverified effect outcomes when effects
already occurred. Falsified routes stay excluded; deferred routes are retried
because new proposals or information may now exist.

V6 extends the V4 universal adaptive loop with exact verified value flow.

New property:
  a later capability may consume exact verified outputs from an earlier capability
  through {"$effect_result": {"effect": E, "field": F}} references.

Safety:
- values are read only from universal_solver_value_state_v1's content-bound
  composition capsule;
- referenced effects must be declared prerequisites;
- referenced top-level result fields must have been declared by the producer;
- any capability with dynamic value substitution OR declared result fields requires
  a content-addressed resolved-capability-semantics receipt plus separate
  independent verification for the exact current value-capsule head and resolved
  action instance;
- static capabilities with no exported result fields may continue to use V4's
  independently authenticated effect-semantics binding;
- V1 remains the single-capability proposal/search/verifier/effect execution engine;
- V6 owns global Boolean lineage, global value lineage, fallback, and learning.

Cross-run continuation never replays already verified prior effects. Resume
authority comes only from universal_solver_authenticated_resume_v1.

No terminal/capability/ownership credit is granted here.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.capability_planner import PlanningFailure, plan_capabilities
from canonical.runtime import universal_verified_adaptive_solver_v1 as v1
from canonical.runtime import universal_verified_adaptive_solver_v4 as v4
from canonical.runtime.universal_solver_state_capsule_v1 import (
    initialize as initialize_fact_capsule,
    append_verified_transition as append_fact_transition,
    verify_targets as verify_fact_targets,
)
from canonical.runtime.universal_solver_value_state_v1 import (
    initialize as initialize_value_capsule,
    append_verified_transition as append_value_transition,
    resolve_effect_results,
    project_verified_values,
)
from canonical.runtime.resolved_capability_semantics_authenticator_v1 import (
    select_and_authenticate as authenticate_resolved,
)
from canonical.runtime.executable_skill_program_v7 import (
    ExecutableSkillProgramError,
    induce_candidate,
)
from canonical.runtime.universal_solver_authenticated_resume_v1 import (
    authenticate as authenticate_resume,
)
from canonical.runtime.universal_solver_episode_verification_authenticator_v1 import (
    authenticate as authenticate_episode_verification,
    reauthenticate_record as reauthenticate_episode_record,
)

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V8"


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


def _contains_effect_ref(value: Any) -> bool:
    if isinstance(value, Mapping):
        if "$effect_result" in value:
            return True
        return any(_contains_effect_ref(x) for x in value.values())
    if isinstance(value, list):
        return any(_contains_effect_ref(x) for x in value)
    return False


def _needs_resolved_semantics(cap: Mapping[str, Any]) -> bool:
    fields = cap.get("result_fields")
    if isinstance(fields, list) and fields:
        return True
    return _contains_effect_ref(cap.get("action"))


def _effect_already_occurred(trace: Sequence[Mapping[str, Any]]) -> bool:
    return any(
        isinstance(row, Mapping) and bool(row.get("effect_outcome_sha256"))
        for row in trace
    )


def _finish(
    *,
    problem: Mapping[str, Any],
    current: list[str],
    trace: list[dict[str, Any]],
    fact_capsule: Mapping[str, Any],
    value_capsule: Mapping[str, Any],
    attempts: list[dict[str, Any]],
    counterexamples: list[dict[str, Any]],
    falsified: set[str],
    deferred: set[str],
    episode_id: str,
    scope_id: str,
    repo_root: str | Path,
    episode_verification_binding: Mapping[str, Any] | None,
    prior_verified_episode_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    targets = v4._tokens(problem.get("target_effects", []), "TARGET_EFFECTS", allow_empty=False)
    verdict = verify_fact_targets(fact_capsule, targets)
    if verdict.get("pass") is not True:
        return _fail("TARGET_FACTS_WITHOUT_VALID_GLOBAL_LINEAGE", state_target_verdict=verdict)

    caps = v4._caps(problem)
    invalidators = (
        ["route_falsified:" + x for x in sorted(falsified)]
        + ["route_deferred:" + x for x in sorted(deferred)]
    )
    ep_core = v4._episode(
        problem,
        trace,
        caps,
        episode_id,
        scope_id,
        invalidators,
        None,
    )
    episode_auth = None
    ep = ep_core
    ep_ok = False
    ep_error = "EPISODE_VERIFICATION_BINDING_REQUIRED"
    if episode_verification_binding is not None:
        episode_auth = authenticate_episode_verification(
            episode_verification_binding,
            problem=problem,
            episode=ep_core,
            trace=trace,
            fact_capsule_head_hash=str(fact_capsule.get("head_hash") or ""),
            value_capsule_head_hash=str(value_capsule.get("head_hash") or ""),
            repo_root=repo_root,
        )
        if episode_auth.get("pass") is True:
            ep = episode_auth["authenticated_episode"]
            ep_ok = True
            ep_error = None
        else:
            ep_error = str(episode_auth.get("reason") or "EPISODE_VERIFICATION_AUTHENTICATION_FAILED")

    candidate = None
    candidate_error = None
    prior_authenticated: list[Mapping[str, Any]] = []
    if ep_ok and prior_verified_episode_records:
        for record in prior_verified_episode_records:
            verdict = reauthenticate_episode_record(record, repo_root=repo_root)
            if verdict.get("pass") is not True:
                candidate_error = (
                    "PRIOR_EPISODE_REAUTHENTICATION_FAILED:"
                    + str(verdict.get("reason") or "UNKNOWN")
                )
                prior_authenticated = []
                break
            prior_authenticated.append(verdict["authenticated_episode"])
        if prior_authenticated and candidate_error is None:
            try:
                candidate = induce_candidate([*prior_authenticated, ep])
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
        "verified_target_values": project_verified_values(value_capsule, targets),
        "trace": trace,
        "attempts": attempts,
        "counterexamples": counterexamples,
        "falsified_capability_ids": sorted(falsified),
        "deferred_capability_ids": sorted(deferred),
        "state_capsule": deepcopy(dict(fact_capsule)),
        "state_capsule_head_hash": fact_capsule.get("head_hash"),
        "value_capsule": deepcopy(dict(value_capsule)),
        "value_capsule_head_hash": value_capsule.get("head_hash"),
        "state_target_verdict": verdict,
        "current_episode": ep,
        "current_episode_verified": ep_ok,
        "episode_verification_error": ep_error,
        "episode_verification_authentication": episode_auth,
        "prior_episode_records_reauthenticated": len(prior_authenticated),
        "skill_candidate": candidate,
        "skill_candidate_error": candidate_error,
        "skill_candidate_reuse_authorized": bool(
            candidate and candidate.get("reuse_authorized")
        ),
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }


def run(
    problem: Mapping[str, Any],
    *,
    proposal_packets: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    repo_root: str | Path,
    resolved_semantics_bindings: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    effect_root: str | None = None,
    episode_id: str = "episode",
    scope_id: str = "scope",
    episode_verification_binding: Mapping[str, Any] | None = None,
    prior_verified_episode_records: Sequence[Mapping[str, Any]] = (),
    resume_binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(problem, Mapping):
            return _fail("PROBLEM_NOT_OBJECT")
        v4._tok(problem.get("task_id"), "TASK_ID")
        caps = v4._caps(problem)
        initial = v4._tokens(problem.get("initial_facts", []), "INITIAL_FACTS")
        targets = v4._tokens(problem.get("target_effects", []), "TARGET_EFFECTS", allow_empty=False)
        if set(initial) & set(targets):
            return _fail("TARGET_EFFECT_MAY_NOT_BE_SELF_ASSERTED_AS_INITIAL_FACT")
        if resolved_semantics_bindings is None:
            resolved_semantics_bindings = {}
        if not isinstance(resolved_semantics_bindings, Mapping):
            return _fail("RESOLVED_SEMANTICS_BINDINGS_INVALID")
        if not isinstance(prior_verified_episode_records, Sequence) or isinstance(
            prior_verified_episode_records, (str, bytes)
        ):
            return _fail("PRIOR_VERIFIED_EPISODE_RECORDS_INVALID")
        episode_id = v4._tok(episode_id, "EPISODE_ID")
        scope_id = v4._tok(scope_id, "SCOPE_ID")

        # Static semantic bindings may be authenticated once. Value-dependent
        # instances are authenticated after resolution at the current capsule head.
        static_semantics: dict[str, dict[str, Any]] = {}
        for cid, cap in caps.items():
            if not _needs_resolved_semantics(cap):
                static_semantics[cid] = v4._authenticate_effect_semantics(
                    problem, cap, repo_root=repo_root
                )

        resume_auth = None
        if resume_binding is not None:
            resume_auth = authenticate_resume(
                resume_binding,
                problem=problem,
                repo_root=repo_root,
                expected_episode_id=episode_id,
                expected_scope_id=scope_id,
            )
            if resume_auth.get("pass") is not True:
                return {
                    "schema": SCHEMA,
                    "status": "FAIL_CLOSED__RESUME_STATE_NOT_AUTHENTICATED",
                    "pass": False,
                    "resume_authentication": resume_auth,
                    "terminal_authority": False,
                    "capability_credit_delta": 0,
                    "ownership_credit_delta": 0,
                }
            current = sorted(set(resume_auth["current_facts"]))
            falsified = set(resume_auth["falsified_capability_ids"])
            deferred = set(resume_auth["deferred_capability_ids"])
            # A verified falsification remains excluded. A deferral is not a
            # falsification and must be eligible for retry after new information.
            excluded = set(falsified)
            trace = [deepcopy(dict(x)) for x in resume_auth["trace"]]
            attempts = [deepcopy(dict(x)) for x in resume_auth["attempts"]]
            counterexamples = [
                deepcopy(dict(x)) for x in resume_auth["counterexamples"]
            ]
            fact_capsule = deepcopy(dict(resume_auth["fact_capsule"]))
            value_capsule = deepcopy(dict(resume_auth["value_capsule"]))
        else:
            current = sorted(set(initial))
            excluded = set()
            falsified = set()
            deferred = set()
            trace = []
            attempts = []
            counterexamples = []
            fact_capsule = initialize_fact_capsule(problem)
            value_capsule = initialize_value_capsule(problem)
        pending: list[dict[str, Any]] = []
        cycle_offset = len(trace)

        max_cycles = int(problem.get("max_solver_cycles", 256))
        if max_cycles < 1 or max_cycles > 10000:
            return _fail("MAX_SOLVER_CYCLES_INVALID")

        for cycle in range(max_cycles):
            if set(targets).issubset(current):
                finished = _finish(
                    problem=problem,
                    current=current,
                    trace=trace,
                    fact_capsule=fact_capsule,
                    value_capsule=value_capsule,
                    attempts=attempts,
                    counterexamples=counterexamples,
                    falsified=falsified,
                    deferred=deferred,
                    episode_id=episode_id,
                    scope_id=scope_id,
                    repo_root=repo_root,
                    episode_verification_binding=episode_verification_binding,
                    prior_verified_episode_records=prior_verified_episode_records,
                )
                finished["resumed_from_authenticated_state"] = resume_auth is not None
                if resume_auth is not None:
                    finished["resume_authentication"] = {
                        "receipt": resume_auth["receipt"],
                        "verification": resume_auth["verification"],
                        "independent_verifier_id": resume_auth["independent_verifier_id"],
                        "fact_capsule_head_hash": resume_auth["fact_capsule_head_hash"],
                        "value_capsule_head_hash": resume_auth["value_capsule_head_hash"],
                    }
                return finished

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

            resolved_action = resolve_effect_results(
                value_capsule,
                capability=cap,
                template=cap["action"],
            )
            resolved_cap = deepcopy(dict(cap))
            resolved_cap["action"] = resolved_action

            if _needs_resolved_semantics(cap):
                pairs = resolved_semantics_bindings.get(cid, [])
                semantics = authenticate_resolved(
                    problem,
                    cap,
                    resolved_action,
                    value_capsule,
                    pairs,
                    repo_root=repo_root,
                )
                if semantics.get("pass") is not True:
                    return {
                        "schema": SCHEMA,
                        "status": "FAIL_CLOSED__RESOLVED_CAPABILITY_SEMANTICS_NOT_AUTHENTICATED",
                        "pass": False,
                        "capability_id": cid,
                        "resolved_action": resolved_action,
                        "resolved_semantics_authentication": semantics,
                        "verified_facts": current,
                        "trace": trace,
                        "state_capsule": fact_capsule,
                        "value_capsule": value_capsule,
                        "terminal_authority": False,
                        "capability_credit_delta": 0,
                        "ownership_credit_delta": 0,
                    }
            else:
                semantics = static_semantics[cid]

            single = v4._single_problem(problem, current, resolved_cap)
            out = v1.run(
                single,
                proposal_packets=proposal_packets,
                effect_root=effect_root,
            )
            attempts.append({
                "cycle": cycle_offset + cycle,
                "capability_id": cid,
                "status": out.get("status"),
                "value_capsule_head_hash": value_capsule.get("head_hash"),
                "resolved_action_sha256": (
                    semantics.get("resolved_action_sha256")
                    if isinstance(semantics, Mapping)
                    else None
                ),
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
                row["verifier_success_condition"] = semantics["verifier_success_condition"]
                row["semantic_authentication_schema"] = semantics.get("schema")
                row["effect_semantics_receipt"] = semantics["receipt"]
                row["effect_semantics_verification"] = semantics["verification"]
                row["effect_semantics_authenticated"] = True
                row["independent_effect_semantics_verifier_id"] = semantics["independent_verifier_id"]
                row["new_verified_facts"] = list(
                    semantics.get("provided_effects", semantics.get("effects", []))
                )
                row["resolved_action"] = deepcopy(resolved_action)
                row["value_capsule_head_before"] = value_capsule.get("head_hash")

                fact_capsule = append_fact_transition(
                    fact_capsule,
                    capability=cap,
                    trace_row=row,
                )
                value_capsule = append_value_transition(
                    value_capsule,
                    capability=cap,
                    trace_row=row,
                )
                row["value_capsule_head_after"] = value_capsule.get("head_hash")
                current = sorted(set(current) | set(row["new_verified_facts"]))
                trace.append(row)
                deferred.discard(cid)
                continue

            if v4._effect_may_have_occurred(resolved_cap, out):
                return {
                    "schema": SCHEMA,
                    "status": "EFFECT_OUTCOME_UNRESOLVED__VALUE_RESUME_RECOVERY_REQUIRED",
                    "pass": False,
                    "capability_id": cid,
                    "solver_v1_result": out,
                    "verified_facts": current,
                    "trace": trace,
                    "attempts": attempts,
                    "state_capsule": fact_capsule,
                    "value_capsule": value_capsule,
                    "terminal_authority": False,
                    "capability_credit_delta": 0,
                    "ownership_credit_delta": 0,
                }

            complete = v4._complete_route_failure(resolved_cap, out)
            counterexamples.append({
                "cycle": cycle_offset + cycle,
                "capability_id": cid,
                "solver_status": out.get("status"),
                "route_falsified_for_current_contract": complete,
                "reason": out.get("reason"),
                "value_capsule_head_hash": value_capsule.get("head_hash"),
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
            status = (
                "AUTHENTICATED_VALUE_RESUME_REQUIRED_AFTER_PARTIAL_EFFECTFUL_PROGRESS"
                if _effect_already_occurred(trace)
                else "UNRESOLVED__ALTERNATIVE_ROUTES_EXHAUSTED__DEFERRED_ROUTE_REMAINS"
            )
            return {
                "schema": SCHEMA,
                "status": status,
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
                "state_capsule": fact_capsule,
                "state_capsule_head_hash": fact_capsule.get("head_hash"),
                "value_capsule": value_capsule,
                "value_capsule_head_hash": value_capsule.get("head_hash"),
                "resumed_from_authenticated_state": resume_auth is not None,
                "terminal_authority": False,
                "capability_credit_delta": 0,
                "ownership_credit_delta": 0,
            }

        return {
            "schema": SCHEMA,
            "status": (
                "AUTHENTICATED_VALUE_RESUME_REQUIRED_FOR_CAPABILITY_DISCOVERY_AFTER_EFFECT"
                if _effect_already_occurred(trace)
                else "CAPABILITY_DISCOVERY_REQUIRED__ALL_DECLARED_ROUTES_FALSIFIED_OR_UNREACHABLE"
            ),
            "pass": False,
            "verified_facts": current,
            "trace": trace,
            "attempts": attempts,
            "counterexamples": counterexamples,
            "falsified_capability_ids": sorted(falsified),
            "deferred_capability_ids": [],
            "target_effects": targets,
            "state_capsule": fact_capsule,
            "state_capsule_head_hash": fact_capsule.get("head_hash"),
            "value_capsule": value_capsule,
            "value_capsule_head_hash": value_capsule.get("head_hash"),
            "proposal_sources_allowed": True,
            "proposal_sources_have_authority": False,
            "resumed_from_authenticated_state": resume_auth is not None,
            "terminal_authority": False,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
