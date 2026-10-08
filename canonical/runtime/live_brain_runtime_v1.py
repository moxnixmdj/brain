"""Unified live execution subruntime V1.

Subordinate compatibility runtime behind canonical.runtime.unified_cognitive_fabric_v1.run.
It integrates the Brain's already-existing verified execution, learning, and repair mechanisms.

Default routes:
- raw intent -> R2 general adequate-decision controller (P3 V12 + Universal Solver V12);
- explicit capability problem -> Universal Verified Adaptive Solver V12;
- verified execution experience -> R3 autonomous verified self-improvement state;
- compiled verified-bound tasks -> existing live integrated bound runtime;
- specialized verified inference systems -> explicit native adapters;
- capability development work -> capability-first scheduler.

The router does not erase native verification contracts and grants no acceptance,
ownership, capability-promotion, or terminal authority by itself.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_UNIFIED_LIVE_COGNITIVE_ARCHITECTURE_V1"
ROOT = Path(__file__).resolve().parents[2]

SURFACES = (
    "GENERAL_ADEQUATE_DECISION_CONTROLLER_V1",
    "UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V12",
    "AUTONOMOUS_VERIFIED_SELF_IMPROVEMENT_V1",
    "LIVE_INTEGRATED_BOUND_BRAIN_V1",
    "P3_REAL_CONTEXT_V12",
    "H100_VERIFIED_CAPABILITY_REGISTRY_V8",
    "MYSTERY_SPARSE_SYMBOLIC_V2",
    "MYSTERY_SEPARABLE_TRANSFORM_V1",
    "CAPABILITY_FIRST_SCHEDULER_V1",
    "COUNTEREXAMPLE_GUIDED_CAUSAL_ARCHITECTURE_SYNTHESIZER_V1",
    "VERIFIED_REPAIR_REPLAY_LOOP_V1",
)


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "terminal_authority": False,
        "capability_promotion_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        **extra,
    }


def _v12_run(problem: Mapping[str, Any], *, repo_root: str | Path, kwargs: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime.universal_verified_adaptive_solver_v12 import run
    return run(problem, repo_root=repo_root, **dict(kwargs))


def _decision_run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path,
    information_provider: Callable[[Mapping[str, Any], int], Mapping[str, Any] | None] | None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None,
    execution_provider: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    from canonical.runtime.general_adequate_decision_controller_v1 import run
    return run(
        request,
        repo_root=repo_root,
        information_provider=information_provider,
        proposal_provider=proposal_provider,
        capability_expander=capability_expander,
        execution_provider=execution_provider,
    )


def _learning_module():
    from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
    return learning


def _skill_plan(problem: Mapping[str, Any], skills: Sequence[Mapping[str, Any]], invalidators: Sequence[str]):
    from canonical.runtime.verified_skill_macro_planner_v1 import plan_with_skills
    return plan_with_skills(problem, skills, active_invalidators=invalidators)


def _bound_run(request: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime import live_integrated_brain_v1 as bound
    return bound.run(request)


def _raw_bound_run(request: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime import live_integrated_brain_v1 as bound
    return bound.run_raw_goal(request)


def _p3(payload: Mapping[str, Any], repo_root: str | Path) -> dict[str, Any]:
    from canonical.runtime.p3_real_context_v3_admission_v12 import evaluate
    return evaluate(payload, repo_root=repo_root)


def _rank_work(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    from canonical.runtime.capability_first_scheduler_v1 import rank_work
    return rank_work(rows)


def _causal_synthesize(manifest: Mapping[str, Any]) -> dict[str, Any]:
    from canonical.runtime.counterexample_guided_causal_architecture_synthesizer_v1 import synthesize
    return synthesize(deepcopy(dict(manifest)))


_REPAIR_EFFECT_BY_CLASS = {
    "ACQUIRE_COMPOSE_OR_INVENT_VERIFIABLE_CAPABILITY": "repair.capability.available",
    "BIND_AND_INDEPENDENTLY_VERIFY_EFFECT_SEMANTICS": "repair.effect_semantics.verified",
    "OBTAIN_OR_REPAIR_INDEPENDENT_VERIFICATION": "repair.independent_verification.available",
    "RECOVER_FROM_OBSERVED_EFFECT_WITHOUT_BLIND_REPLAY": "repair.safe_recovery.available",
    "REPLACE_FALSIFIED_ROUTE": "repair.verified_route_replacement.available",
    "RESOLVE_MINIMUM_BLOCKING_INFORMATION_AND_RETRY": "repair.blocking_information.resolved",
    "LOCALIZE_CAUSAL_FAILURE_AND_GENERATE_MINIMAL_REPAIR": "repair.causal_localization.complete",
}


def synthesize_failure_repair(
    request: Mapping[str, Any],
    *,
    state_path: str | Path | None = None,
) -> dict[str, Any]:
    """Compile one durable R3 failure class into minimum causal architecture search.

    Component semantics remain caller-declared and are independently filtered by
    the existing synthesizer. This bridge does not guess that any Brain component
    provides a repair effect.
    """
    if not isinstance(request, Mapping):
        return _fail("REPAIR_REQUEST_NOT_OBJECT")
    fingerprint = str(request.get("failure_fingerprint") or "").strip()
    components = request.get("components")
    if not fingerprint:
        return _fail("FAILURE_FINGERPRINT_REQUIRED")
    if not isinstance(components, Sequence) or isinstance(components, (str, bytes)):
        return _fail("REPAIR_COMPONENT_FRONTIER_REQUIRED")

    try:
        learning = _learning_module()
        path = learning.DEFAULT_STATE_PATH if state_path is None else Path(state_path)
        state = learning.load_state(path)
        diagnosis = state.get("failures", {}).get(fingerprint)
        if not isinstance(diagnosis, Mapping):
            return _fail("FAILURE_FINGERPRINT_UNKNOWN:" + fingerprint)

        repair_class = str(diagnosis.get("repair_class") or "").strip()
        repair_effect = _REPAIR_EFFECT_BY_CLASS.get(repair_class)
        if repair_effect is None:
            return _fail("REPAIR_CLASS_UNMAPPED:" + repair_class)

        max_components = int(request.get("max_components", 12))
        top_k = int(request.get("top_k", 8))
        initial_facts = request.get("initial_facts") or []
        if not isinstance(initial_facts, Sequence) or isinstance(initial_facts, (str, bytes)):
            return _fail("REPAIR_INITIAL_FACTS_INVALID")

        manifest = {
            "initial_facts": list(initial_facts),
            "components": deepcopy(list(components)),
            "counterexamples": deepcopy(list(request.get("counterexamples") or [])),
            "allow_candidate_components": request.get("allow_candidate_components") is True,
            "target": {
                "required_effects": [repair_effect],
                "max_components": max_components,
                "top_k": top_k,
            },
        }
        synthesis = _causal_synthesize(manifest)
        return {
            "schema": SCHEMA,
            "status": (
                "REPAIR_ARCHITECTURE_FOUND"
                if synthesis.get("pass") is True
                else "REPAIR_ARCHITECTURE_UNRESOLVED"
            ),
            "pass": synthesis.get("pass") is True,
            "failure_fingerprint": fingerprint,
            "repair_class": repair_class,
            "required_repair_effect": repair_effect,
            "causal_synthesis": synthesis,
            "candidate_only": True,
            "execution_authority": False,
            "capability_promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail("REPAIR_SYNTHESIS_EXCEPTION:" + type(exc).__name__ + ":" + str(exc))


def _compile_verified_repair_problem(
    *,
    repair: Mapping[str, Any],
    request: Mapping[str, Any],
    retry_capsule_sha256: str,
) -> dict[str, Any]:
    synthesis = repair.get("causal_synthesis")
    if not isinstance(synthesis, Mapping) or synthesis.get("pass") is not True:
        raise ValueError("REPAIR_SYNTHESIS_NOT_EXECUTABLE")
    winner = synthesis.get("winner")
    if not isinstance(winner, Mapping):
        raise ValueError("REPAIR_WINNER_MISSING")
    ids = winner.get("components")
    components = request.get("components")
    if not isinstance(ids, Sequence) or isinstance(ids, (str, bytes)) or not ids:
        raise ValueError("REPAIR_WINNER_COMPONENTS_INVALID")
    if not isinstance(components, Sequence) or isinstance(components, (str, bytes)):
        raise ValueError("REPAIR_COMPONENT_FRONTIER_REQUIRED")
    by_id = {
        str(row.get("id") or ""): row
        for row in components
        if isinstance(row, Mapping) and str(row.get("id") or "")
    }
    selected = []
    for cid in ids:
        cid = str(cid)
        source = by_id.get(cid)
        if not isinstance(source, Mapping):
            raise ValueError("REPAIR_WINNER_COMPONENT_SOURCE_MISSING:" + cid)
        if source.get("verified") is not True or source.get("brain_owned") is not True or source.get("donor_independent") is not True:
            raise ValueError("REPAIR_COMPONENT_AUTHORITY_INVALID:" + cid)
        costs = source.get("cost") or {}
        if not isinstance(costs, Mapping) or float(costs.get("incremental_spend_usd", 0)) != 0:
            raise ValueError("REPAIR_COMPONENT_NONZERO_SPEND:" + cid)
        executable = source.get("executable_capability")
        if not isinstance(executable, Mapping):
            raise ValueError("REPAIR_COMPONENT_EXECUTABLE_BINDING_REQUIRED:" + cid)
        if str(executable.get("id") or "") != cid:
            raise ValueError("REPAIR_COMPONENT_EXECUTABLE_ID_MISMATCH:" + cid)
        if sorted(executable.get("requires") or []) != sorted(source.get("requires") or []):
            raise ValueError("REPAIR_COMPONENT_REQUIRES_MISMATCH:" + cid)
        if sorted(executable.get("provides") or []) != sorted(source.get("provides") or []):
            raise ValueError("REPAIR_COMPONENT_PROVIDES_MISMATCH:" + cid)
        selected.append(deepcopy(dict(executable)))
    fingerprint = str(repair.get("failure_fingerprint") or "")
    task_id = str(request.get("repair_task_id") or (
        "repair-" + fingerprint[:16] + "-" + retry_capsule_sha256[:12]
    ))
    return {
        "task_id": task_id,
        "initial_facts": list(request.get("initial_facts") or []),
        "target_effects": [str(repair["required_repair_effect"])],
        "capabilities": selected,
        "max_solver_cycles": min(int(request.get("max_solver_cycles", 64)), 256),
    }


def _replay_retry_context(
    context: Mapping[str, Any],
    *,
    repo_root: str | Path,
    information_provider: Callable[[Mapping[str, Any], int], Mapping[str, Any] | None] | None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None,
    state_path: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(context, Mapping):
        return _fail("RETRY_CONTEXT_NOT_OBJECT")
    mode = str(context.get("mode") or "")
    if mode in {"repair_synthesis", "repair_cycle"}:
        return _fail("RETRY_CONTEXT_REPAIR_RECURSION_FORBIDDEN")
    replay_context = deepcopy(dict(context))
    # A repair is accepted only by replaying the original obligation. That replay
    # must not recursively launch another repair cycle if the repair was
    # insufficient; one observed failure therefore causes at most one automatic
    # repair attempt per live invocation.
    replay_context["auto_repair"] = False
    if state_path is not None:
        replay_context["state_path"] = str(state_path)
    return run(
        replay_context,
        repo_root=repo_root,
        information_provider=information_provider,
        proposal_provider=proposal_provider,
        capability_expander=capability_expander,
    )


def execute_failure_repair_cycle(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    state_path: str | Path | None = None,
    information_provider: Callable[[Mapping[str, Any], int], Mapping[str, Any] | None] | None = None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        return _fail("REPAIR_REQUEST_NOT_OBJECT")
    try:
        learning = _learning_module()
        path = learning.DEFAULT_STATE_PATH if state_path is None else Path(state_path)
        fingerprint = str(request.get("failure_fingerprint") or "").strip()
        if not fingerprint:
            return _fail("FAILURE_FINGERPRINT_REQUIRED")
        retry = learning.get_failure_retry_context(
            fingerprint,
            state_path=path,
            retry_capsule_sha256=request.get("retry_capsule_sha256"),
        )
        synthesized = synthesize_failure_repair(request, state_path=path)
        invention_mode = False
        if synthesized.get("pass") is not True:
            causal = synthesized.get("causal_synthesis")
            classification = (
                str(causal.get("classification") or "")
                if isinstance(causal, Mapping)
                else ""
            )
            if classification != "NEW_PRIMITIVE_REQUIRED" or capability_expander is None:
                return {
                    **synthesized,
                    "status": "REPAIR_CYCLE_UNRESOLVED_AT_SYNTHESIS",
                    "retry_capsule_sha256": retry["retry_capsule_sha256"],
                    "capability_expander_available": capability_expander is not None,
                }
            required_effect = str(synthesized.get("required_repair_effect") or "").strip()
            if not required_effect:
                return _fail("NEW_PRIMITIVE_REPAIR_EFFECT_MISSING")
            invention_targets = [required_effect]
            invention_target_source = "REPAIR_CLASS_META_EFFECT"
            if required_effect == "repair.capability.available":
                retry_context = retry.get("context")
                if isinstance(retry_context, Mapping):
                    retry_mode = str(retry_context.get("mode") or "").strip()
                    concrete = None
                    if retry_mode == "generic":
                        raw_problem = retry_context.get("problem")
                        if isinstance(raw_problem, Mapping):
                            concrete = raw_problem.get("target_effects")
                    elif retry_mode == "compiled_bound":
                        raw_request = retry_context.get("request")
                        if isinstance(raw_request, Mapping):
                            concrete = raw_request.get("target_effects")
                    if isinstance(concrete, Sequence) and not isinstance(concrete, (str, bytes)):
                        normalized = sorted({
                            str(effect).strip()
                            for effect in concrete
                            if isinstance(effect, str) and str(effect).strip()
                        })
                        if normalized:
                            invention_targets = normalized
                            invention_target_source = "STORED_ORIGINAL_OBLIGATION_TARGET_EFFECTS"
            fingerprint_prefix = fingerprint[:16]
            problem = {
                "task_id": str(
                    request.get("repair_task_id")
                    or (
                        "invent-repair-"
                        + fingerprint_prefix
                        + "-"
                        + retry["retry_capsule_sha256"][:12]
                    )
                ),
                "initial_facts": list(request.get("initial_facts") or []),
                "target_effects": invention_targets,
                "capabilities": [],
                "max_solver_cycles": min(int(request.get("max_solver_cycles", 64)), 256),
            }
            invention_mode = True
        else:
            problem = _compile_verified_repair_problem(
                repair=synthesized,
                request=request,
                retry_capsule_sha256=retry["retry_capsule_sha256"],
            )
        kwargs = dict(request.get("solver_kwargs") or {})
        kwargs.setdefault("episode_id", "repair-" + retry["retry_capsule_sha256"][:12])
        kwargs.setdefault("scope_id", "verified-repair-loop")
        if proposal_provider is not None:
            kwargs["proposal_provider"] = proposal_provider
        if capability_expander is not None:
            kwargs["capability_expander"] = capability_expander
        repair_execution = _v12_run(problem, repo_root=repo_root, kwargs=kwargs)
        repair_learning = _observe_runtime_outcome(
            repair_execution,
            state_path=path,
            learn=request.get("learn", True) is not False,
            retry_context={
                "mode": "generic",
                "problem": deepcopy(problem),
                "episode_id": kwargs["episode_id"],
                "scope_id": kwargs["scope_id"],
                "learn": True,
            },
        )
        if repair_execution.get("pass") is not True:
            return {
                "schema": SCHEMA,
                "status": "REPAIR_EXECUTION_FAILED_VERIFICATION",
                "pass": False,
                "failure_fingerprint": fingerprint,
                "retry_capsule_sha256": retry["retry_capsule_sha256"],
                "repair_synthesis": synthesized,
                "repair_problem": problem,
                "repair_execution": repair_execution,
                "repair_learning": repair_learning,
                "terminal_authority": False,
                "capability_promotion_authority": False,
                "terminal_credit_delta": 0,
            }
        replay = _replay_retry_context(
            retry["context"],
            repo_root=repo_root,
            information_provider=information_provider,
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
            state_path=path,
        )
        replay_pass = replay.get("pass") is True
        winner_components = []
        if not invention_mode:
            winner_components = list(
                synthesized["causal_synthesis"]["winner"]["components"]
            )
        repair_record = {
            "required_repair_effect": synthesized["required_repair_effect"],
            "invention_target_effects": (
                list(problem.get("target_effects") or [])
                if invention_mode else [synthesized["required_repair_effect"]]
            ),
            "invention_target_source": (
                invention_target_source
                if invention_mode else "EXISTING_REPAIR_ARCHITECTURE"
            ),
            "repair_mode": (
                "V12_AUTHENTICATED_CAPABILITY_EXPANSION"
                if invention_mode
                else "EXISTING_VERIFIED_COMPONENT_ARCHITECTURE"
            ),
            "winner_components": winner_components,
            "expanded_capability_ids": list(
                repair_execution.get("expanded_capability_ids") or []
            ),
            "capability_expansion_attempts": deepcopy(
                list(repair_execution.get("capability_expansion_attempts") or [])
            ),
            "repair_task_id": problem["task_id"],
            "repair_execution_status": repair_execution.get("status"),
            "repair_execution_pass": True,
            "original_replay_status": replay.get("status"),
            "original_replay_pass": replay_pass,
        }
        recorded = learning.record_repair_outcome(
            fingerprint,
            retry_capsule_sha256=retry["retry_capsule_sha256"],
            repair_record=repair_record,
            original_replay_pass=replay_pass,
            state_path=path,
        )
        return {
            "schema": SCHEMA,
            "status": (
                "REPAIR_VERIFIED_BY_ORIGINAL_OBLIGATION_REPLAY"
                if replay_pass else "REPAIR_EFFECT_VERIFIED__ORIGINAL_FAILURE_PERSISTS"
            ),
            "pass": replay_pass,
            "failure_fingerprint": fingerprint,
            "retry_capsule_sha256": retry["retry_capsule_sha256"],
            "repair_synthesis": synthesized,
            "repair_mode": (
                "V12_AUTHENTICATED_CAPABILITY_EXPANSION"
                if invention_mode
                else "EXISTING_VERIFIED_COMPONENT_ARCHITECTURE"
            ),
            "invention_target_effects": (
                list(problem.get("target_effects") or [])
                if invention_mode else [synthesized["required_repair_effect"]]
            ),
            "invention_target_source": (
                invention_target_source
                if invention_mode else "EXISTING_REPAIR_ARCHITECTURE"
            ),
            "repair_problem": problem,
            "repair_execution": repair_execution,
            "repair_learning": repair_learning,
            "original_replay": replay,
            "repair_receipt": recorded,
            "permanent_reuse_authorized": bool(
                isinstance(repair_learning, Mapping)
                and repair_learning.get("permanent_reuse_authorized") is True
            ),
            "capability_promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail("REPAIR_CYCLE_EXCEPTION:" + type(exc).__name__ + ":" + str(exc))


def _automatic_failure_repair(
    learning_result: Mapping[str, Any] | None,
    *,
    repo_root: str | Path,
    state_path: str | Path | None,
    initial_facts: Sequence[str] = (),
    repair_components: Sequence[Mapping[str, Any]] = (),
    information_provider: Callable[[Mapping[str, Any], int], Mapping[str, Any] | None] | None = None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
    enabled: bool = True,
) -> dict[str, Any] | None:
    """Turn a persisted live failure directly into one verified repair/replay cycle.

    This is the missing R3 control edge. It consumes only a failure already
    admitted by the durable learning layer, so it cannot invent a fingerprint or
    bypass retry-capsule integrity. The repair engine remains fail-closed and only
    reports success after the original obligation itself replays successfully.
    """
    if not enabled or not isinstance(learning_result, Mapping):
        return None
    if learning_result.get("pass") is not False:
        return None
    diagnosis = learning_result.get("diagnosis")
    if not isinstance(diagnosis, Mapping):
        return None
    fingerprint = str(diagnosis.get("failure_fingerprint") or "").strip()
    retry_sha = str(learning_result.get("retry_capsule_sha256") or "").strip()
    if not fingerprint or not retry_sha:
        return None
    if not isinstance(repair_components, Sequence) or isinstance(
        repair_components, (str, bytes)
    ):
        return _fail("AUTO_REPAIR_COMPONENT_FRONTIER_INVALID")
    normalized_components = []
    for row in repair_components:
        if not isinstance(row, Mapping):
            return _fail("AUTO_REPAIR_COMPONENT_NOT_OBJECT")
        normalized_components.append(deepcopy(dict(row)))
    facts = [
        str(x).strip()
        for x in initial_facts
        if isinstance(x, str) and str(x).strip()
    ]
    return execute_failure_repair_cycle(
        {
            "failure_fingerprint": fingerprint,
            "retry_capsule_sha256": retry_sha,
            "components": normalized_components,
            "initial_facts": facts,
            "learn": True,
        },
        repo_root=repo_root,
        state_path=state_path,
        information_provider=information_provider,
        proposal_provider=proposal_provider,
        capability_expander=capability_expander,
    )


def _active_learning_context(state_path: str | Path | None, *, scope_id: str, episode_id: str) -> dict[str, Any]:
    learning = _learning_module()
    path = learning.DEFAULT_STATE_PATH if state_path is None else Path(state_path)
    state = learning.load_state(path)
    prior = []
    for ep in state.get("episodes", {}).values():
        if not isinstance(ep, Mapping):
            continue
        if str(ep.get("scope_id") or "") != scope_id:
            continue
        if str(ep.get("episode_id") or "") == episode_id:
            continue
        prior.append(deepcopy(dict(ep)))
    prior.sort(key=lambda x: (str(x.get("episode_id") or ""), str(x.get("program_sha256") or "")))
    skills = []
    for rec in state.get("skills", {}).values():
        if not isinstance(rec, Mapping) or rec.get("active") is not True:
            continue
        skill = rec.get("skill")
        if isinstance(skill, Mapping):
            skills.append(deepcopy(dict(skill)))
    skills.sort(key=lambda x: str(x.get("candidate_sha256") or ""))
    return {
        "state_path": path,
        "state": state,
        "prior_verified_episodes": prior,
        "active_verified_skills": skills,
    }


def _integrate_learning(
    out: Mapping[str, Any],
    *,
    state_path: str | Path | None,
    retry_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    learning = _learning_module()
    path = learning.DEFAULT_STATE_PATH if state_path is None else Path(state_path)
    return learning.integrate_solver_output(
        out,
        state_path=path,
        retry_context=retry_context,
    )


def _run_learning_episode(
    problem: Mapping[str, Any],
    *,
    repo_root: str | Path,
    state_path: str | Path | None,
    episode_id: str,
    scope_id: str,
    retry_context: Mapping[str, Any] | None = None,
    known_absent_invalidators: Sequence[str] = (),
    solver_kwargs: Mapping[str, Any] | None = None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Execute through R3 so verified learned routes can control the live path."""
    learning = _learning_module()
    path = learning.DEFAULT_STATE_PATH if state_path is None else Path(state_path)
    kwargs = dict(solver_kwargs or {})
    controlled = {
        "repo_root",
        "state_path",
        "episode_id",
        "scope_id",
        "retry_context",
        "known_absent_invalidators",
        "proposal_provider",
        "capability_expander",
        "prior_verified_episode_records",
    }
    conflicts = sorted(set(kwargs) & controlled)
    if conflicts:
        raise ValueError(
            "R3_LIVE_EXECUTION_CONTROLLED_KWARGS:" + ",".join(conflicts)
        )
    return learning.run_learning_episode(
        problem,
        repo_root=repo_root,
        state_path=path,
        episode_id=episode_id,
        scope_id=scope_id,
        retry_context=retry_context,
        known_absent_invalidators=known_absent_invalidators,
        proposal_provider=proposal_provider,
        capability_expander=capability_expander,
        **kwargs,
    )


def _observe_runtime_outcome(
    out: Mapping[str, Any],
    *,
    state_path: str | Path | None,
    learn: bool,
    retry_context: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Feed every live failure into R3 while keeping success promotion fail-closed.

    Failed outcomes are always useful causal evidence and may be fingerprinted /
    deduplicated without granting capability authority. Successful non-solver
    actions are merely observed; they are never persisted as reusable learning
    unless they already carry the verified episode / skill machinery expected by
    autonomous_verified_self_improvement_v1.
    """
    if not learn:
        return None
    if not isinstance(out, Mapping):
        return None

    if out.get("pass") is not True:
        return _integrate_learning(out, state_path=state_path, retry_context=retry_context)

    learning_keys = {
        "current_episode_verified",
        "current_episode",
        "skill_candidate",
        "verified_executable_skill",
        "verified_skill_reuse_authorized",
    }
    if any(key in out for key in learning_keys):
        return _integrate_learning(out, state_path=state_path, retry_context=retry_context)

    return {
        "status": "SUCCESS_OBSERVED__NO_VERIFIED_LEARNING_ARTIFACT",
        "pass": True,
        "permanent_reuse_authorized": False,
        "terminal_authority": False,
    }


def _h100(operation: str, payload: Mapping[str, Any]) -> Any:
    from canonical.runtime import h100_verified_capability_registry_v8 as module
    if operation == "registry_snapshot":
        return module.registry_snapshot()
    if operation == "resolve":
        return module.resolve_verified_capability(
            payload.get("rows") or [],
            target=str(payload.get("target") or ""),
            input_name=payload.get("input_name"),
            exact_nrmse=float(payload.get("exact_nrmse", 1e-8)),
        )
    if operation == "predict":
        return {"status": "PREDICTION_COMPLETE", "prediction": module.predict(
            payload.get("resolution") or {}, payload.get("point") or {}
        )}
    if operation == "invoke":
        return module.invoke(str(payload.get("capability_id") or ""), payload.get("payload") or {})
    raise ValueError("H100_OPERATION_INVALID")


def _mystery_sparse(operation: str, payload: Mapping[str, Any]) -> Any:
    from canonical.runtime import mysterymechanism_sparse_symbolic_adapter_v2 as module
    if operation == "plan_experiments":
        return module.plan_experiments(payload.get("bounds") or {})
    if operation == "solve":
        return module.solve(
            payload.get("rows") or [],
            bounds=payload.get("bounds") or {},
            target=str(payload.get("target") or "out"),
            fit_threshold=float(payload.get("fit_threshold", 0.05)),
        )
    if operation == "choose_final_experiment":
        return module.choose_final_experiment(
            payload.get("rows") or [],
            bounds=payload.get("bounds") or {},
            target=str(payload.get("target") or "out"),
            grid_levels=int(payload.get("grid_levels", 5)),
        )
    if operation == "sparse_discover":
        return module.sparse_discover(
            payload.get("rows") or [],
            target=str(payload.get("target") or "out"),
            inputs=payload.get("inputs"),
            max_depth=int(payload.get("max_depth", 2)),
            beam_width=int(payload.get("beam_width", 24)),
            pair_pool=int(payload.get("pair_pool", 18)),
        )
    raise ValueError("MYSTERY_SPARSE_OPERATION_INVALID")


def _mystery_separable(operation: str, payload: Mapping[str, Any]) -> Any:
    from canonical.runtime import mysterymechanism_separable_transform_v1 as module
    if operation == "discover":
        return module.discover(
            payload.get("rows") or [],
            bounds=payload.get("bounds") or {},
            target=str(payload.get("target") or "out"),
            validation_index=int(payload.get("validation_index", -1)),
        )
    if operation == "predict":
        return {"status": "PREDICTION_COMPLETE", "prediction": module.predict(
            payload.get("candidate") or {}, payload.get("point") or {}
        )}
    if operation == "serialize":
        return {"status": "SERIALIZATION_COMPLETE", "expression": module.serialize(payload.get("candidate") or {})}
    raise ValueError("MYSTERY_SEPARABLE_OPERATION_INVALID")


def inventory(*, state_path: str | Path | None = None) -> dict[str, Any]:
    bound_count = None
    bound_error = None
    try:
        from canonical.runtime.live_integrated_brain_v1 import load_verified_registry
        bound_count = len(load_verified_registry())
    except Exception as exc:
        bound_error = type(exc).__name__ + ":" + str(exc)

    learning_stats = None
    learning_error = None
    try:
        learning = _learning_module()
        path = learning.DEFAULT_STATE_PATH if state_path is None else Path(state_path)
        learning_stats = deepcopy(dict(learning.load_state(path).get("stats") or {}))
    except Exception as exc:
        learning_error = type(exc).__name__ + ":" + str(exc)

    return {
        "schema": SCHEMA,
        "status": "UNIFIED_LIVE_BRAIN_READY",
        "pass": bound_error is None and learning_error is None,
        "public_entrypoint": "canonical.runtime.unified_cognitive_fabric_v1.run",
        "canonical_public_entrypoint": "canonical.runtime.unified_cognitive_fabric_v1.run",
        "subruntime_entrypoint": "canonical.runtime.live_brain_runtime_v1.run",
        "subruntime_public_authority": False,
        "surfaces": list(SURFACES),
        "default_raw_intent_path": "GENERAL_ADEQUATE_DECISION_CONTROLLER_V1",
        "default_explicit_execution_path": "R3_REUSE_FIRST_OVER_UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V12",
        "default_learning_scope": "unified-live-brain",
        "automatic_verified_experience_integration": True,
        "automatic_verified_failure_repair_replay": True,
        "bounded_auto_repair_attempts_per_live_invocation": 1,
        "verified_skill_execution_reuse_first": True,
        "active_skill_planning_reuse": True,
        "verified_bound_capability_count": bound_count,
        "bound_inventory_error": bound_error,
        "learning_state_stats": learning_stats,
        "learning_state_error": learning_error,
        "native_verification_boundaries_preserved": True,
        "terminal_authority": False,
        "capability_promotion_authority": False,
        "terminal_credit_delta": 0,
    }


def run_generic(
    problem: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    state_path: str | Path | None = None,
    episode_id: str = "episode",
    scope_id: str = "unified-live-brain",
    active_invalidators: Sequence[str] = (),
    known_absent_invalidators: Sequence[str] = (),
    learn: bool = True,
    auto_repair: bool = True,
    repair_components: Sequence[Mapping[str, Any]] = (),
    solver_kwargs: Mapping[str, Any] | None = None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return _fail("PROBLEM_NOT_OBJECT")
    try:
        ctx = _active_learning_context(
            state_path,
            scope_id=scope_id,
            episode_id=episode_id,
        )
        skill_plan = None
        if ctx["active_verified_skills"]:
            skill_plan = _skill_plan(
                problem,
                ctx["active_verified_skills"],
                active_invalidators,
            )

        if learn:
            learned = _run_learning_episode(
                problem,
                repo_root=repo_root,
                state_path=ctx["state_path"],
                episode_id=episode_id,
                scope_id=scope_id,
                retry_context={
                    "mode": "generic",
                    "problem": deepcopy(dict(problem)),
                    "episode_id": episode_id,
                    "scope_id": scope_id,
                    "active_invalidators": list(active_invalidators),
                    "known_absent_invalidators": list(known_absent_invalidators),
                    "learn": True,
                },
                known_absent_invalidators=known_absent_invalidators,
                solver_kwargs=solver_kwargs,
                proposal_provider=proposal_provider,
                capability_expander=capability_expander,
            )
            out = learned.get("solver_output")
            if not isinstance(out, Mapping):
                raise ValueError("R3_SOLVER_OUTPUT_MISSING")
            automatic_repair = _automatic_failure_repair(
                learned.get("learning"),
                repo_root=repo_root,
                state_path=ctx["state_path"],
                initial_facts=problem.get("initial_facts") or (),
                repair_components=repair_components,
                information_provider=None,
                proposal_provider=proposal_provider,
                capability_expander=capability_expander,
                enabled=auto_repair,
            )
            repaired = (
                isinstance(automatic_repair, Mapping)
                and automatic_repair.get("pass") is True
            )
            return {
                "schema": SCHEMA,
                "status": (
                    "UNIFIED_GENERIC_EXECUTION_REPAIRED"
                    if repaired else "UNIFIED_GENERIC_EXECUTION_COMPLETE"
                ),
                "pass": learned.get("pass") is True or repaired,
                "solver": "R3_REUSE_FIRST_OVER_UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V12",
                "solver_output": out,
                "learning": learned.get("learning"),
                "verified_prior_episode_count_reused": learned.get(
                    "prior_verified_episode_count_used", 0
                ),
                "active_verified_skill_count": len(ctx["active_verified_skills"]),
                "skill_aware_plan": skill_plan,
                "reuse_first": learned.get("reuse_first") is True,
                "reused_skill_id": learned.get("reused_skill_id"),
                "reuse_attempt": learned.get("reuse_attempt"),
                "fallback_used": learned.get("fallback_used") is True,
                "fallback_blocked_effect_may_have_occurred": (
                    learned.get("fallback_blocked_effect_may_have_occurred") is True
                ),
                "learning_persistence_enabled": True,
                "auto_repair_attempted": automatic_repair is not None,
                "automatic_repair": automatic_repair,
                "terminal_authority": False,
                "capability_promotion_authority": False,
                "terminal_credit_delta": 0,
            }

        kwargs = dict(solver_kwargs or {})
        kwargs.setdefault("episode_id", episode_id)
        kwargs.setdefault("scope_id", scope_id)
        kwargs.setdefault(
            "prior_verified_episode_records",
            ctx["prior_verified_episodes"],
        )
        if proposal_provider is not None:
            kwargs["proposal_provider"] = proposal_provider
        if capability_expander is not None:
            kwargs["capability_expander"] = capability_expander
        out = _v12_run(problem, repo_root=repo_root, kwargs=kwargs)
        return {
            "schema": SCHEMA,
            "status": "UNIFIED_GENERIC_EXECUTION_COMPLETE",
            "pass": out.get("pass") is True,
            "solver": "UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V12",
            "solver_output": out,
            "learning": None,
            "verified_prior_episode_count_reused": len(
                ctx["prior_verified_episodes"]
            ),
            "active_verified_skill_count": len(ctx["active_verified_skills"]),
            "skill_aware_plan": skill_plan,
            "reuse_first": False,
            "reused_skill_id": None,
            "reuse_attempt": None,
            "fallback_used": False,
            "fallback_blocked_effect_may_have_occurred": False,
            "learning_persistence_enabled": False,
            "terminal_authority": False,
            "capability_promotion_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(
            "GENERIC_RUNTIME_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)
        )


def run_decision(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    state_path: str | Path | None = None,
    information_provider: Callable[[Mapping[str, Any], int], Mapping[str, Any] | None] | None = None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
    known_absent_invalidators: Sequence[str] = (),
    learn: bool = True,
    auto_repair: bool = True,
    repair_components: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        return _fail("DECISION_REQUEST_NOT_OBJECT")
    try:
        bound_request = deepcopy(dict(request))
        bound_request.setdefault("scope_id", "unified-live-brain")
        learning_holder: dict[str, Any] = {}

        def learned_execution_provider(
            problem: Mapping[str, Any],
            *,
            repo_root: str | Path,
            episode_id: str,
            scope_id: str,
            proposal_provider=None,
            capability_expander=None,
        ) -> Mapping[str, Any]:
            learned = _run_learning_episode(
                problem,
                repo_root=repo_root,
                state_path=state_path,
                episode_id=episode_id,
                scope_id=scope_id,
                retry_context={
                    "mode": "decision",
                    "request": deepcopy(dict(bound_request)),
                    "known_absent_invalidators": list(known_absent_invalidators),
                    "learn": True,
                },
                known_absent_invalidators=known_absent_invalidators,
                proposal_provider=proposal_provider,
                capability_expander=capability_expander,
            )
            learning_holder["result"] = learned
            solver_output = learned.get("solver_output")
            if not isinstance(solver_output, Mapping):
                raise ValueError("R3_DECISION_SOLVER_OUTPUT_MISSING")
            return solver_output

        out = _decision_run(
            bound_request,
            repo_root=repo_root,
            information_provider=information_provider,
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
            execution_provider=learned_execution_provider if learn else None,
        )
        learned = learning_holder.get("result")
        retry_context = {
            "mode": "decision",
            "request": deepcopy(dict(bound_request)),
            "known_absent_invalidators": list(known_absent_invalidators),
            "learn": True,
        }

        learning = None
        if isinstance(learned, Mapping):
            learning = learned.get("learning")
        elif learn and out.get("pass") is not True:
            learning = _observe_runtime_outcome(
                out,
                state_path=state_path,
                learn=True,
                retry_context=retry_context,
            )

        execution_problem = bound_request.get("execution_problem")
        repair_initial_facts = (
            execution_problem.get("initial_facts") or ()
            if isinstance(execution_problem, Mapping) else ()
        )
        automatic_repair = _automatic_failure_repair(
            learning,
            repo_root=repo_root,
            state_path=state_path,
            initial_facts=repair_initial_facts,
            repair_components=repair_components,
            information_provider=information_provider,
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
            enabled=auto_repair,
        )
        repaired = (
            isinstance(automatic_repair, Mapping)
            and automatic_repair.get("pass") is True
        )

        return {
            "schema": SCHEMA,
            "status": (
                "UNIFIED_DECISION_EXECUTION_REPAIRED"
                if repaired else "UNIFIED_DECISION_EXECUTION_COMPLETE"
            ),
            "pass": out.get("pass") is True or repaired,
            "decision_controller": "GENERAL_ADEQUATE_DECISION_CONTROLLER_V1",
            "decision_output": out,
            "learning": learning,
            "reuse_first": (
                learned.get("reuse_first") is True
                if isinstance(learned, Mapping) else False
            ),
            "reused_skill_id": (
                learned.get("reused_skill_id")
                if isinstance(learned, Mapping) else None
            ),
            "reuse_attempt": (
                learned.get("reuse_attempt")
                if isinstance(learned, Mapping) else None
            ),
            "fallback_used": (
                learned.get("fallback_used") is True
                if isinstance(learned, Mapping) else False
            ),
            "fallback_blocked_effect_may_have_occurred": (
                learned.get("fallback_blocked_effect_may_have_occurred") is True
                if isinstance(learned, Mapping) else False
            ),
            "semantic_acceptance_complete": (
                out.get("semantic_acceptance_complete") is True
            ),
            "actual_goal_satisfaction_verified": (
                out.get("actual_goal_satisfaction_verified") is True
                or repaired
            ),
            "auto_repair_attempted": automatic_repair is not None,
            "automatic_repair": automatic_repair,
            "terminal_authority": False,
            "capability_promotion_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(
            "DECISION_RUNTIME_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)
        )


def run_specialized(
    surface: str,
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    state_path: str | Path | None = None,
    learn: bool = True,
    auto_repair: bool = True,
    repair_components: Sequence[Mapping[str, Any]] = (),
    information_provider: Callable[[Mapping[str, Any], int], Mapping[str, Any] | None] | None = None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("SPECIALIZED_PAYLOAD_NOT_OBJECT")
    name = str(surface or "").strip()
    try:
        if name == "P3_REAL_CONTEXT_V12":
            raw = _p3(payload, repo_root)
        elif name == "H100_VERIFIED_CAPABILITY_REGISTRY_V8":
            raw = _h100(str(payload.get("operation") or ""), payload)
        elif name == "MYSTERY_SPARSE_SYMBOLIC_V2":
            raw = _mystery_sparse(str(payload.get("operation") or ""), payload)
        elif name == "MYSTERY_SEPARABLE_TRANSFORM_V1":
            raw = _mystery_separable(str(payload.get("operation") or ""), payload)
        else:
            return _fail("SPECIALIZED_SURFACE_UNKNOWN:" + name)
        passed = not (
            isinstance(raw, Mapping)
            and str(raw.get("status") or "").startswith("FAIL_CLOSED")
        )
        observation = deepcopy(dict(raw)) if isinstance(raw, Mapping) else {
            "status": "SPECIALIZED_RESULT",
            "result": raw,
        }
        observation["pass"] = passed
        learning = _observe_runtime_outcome(
            observation,
            state_path=state_path,
            learn=learn,
            retry_context={
                "mode": "specialized",
                "surface": name,
                "payload": deepcopy(dict(payload)),
                "learn": True,
            },
        )
        automatic_repair = _automatic_failure_repair(
            learning,
            repo_root=repo_root,
            state_path=state_path,
            initial_facts=(),
            repair_components=repair_components,
            information_provider=information_provider,
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
            enabled=auto_repair,
        )
        repaired = (
            isinstance(automatic_repair, Mapping)
            and automatic_repair.get("pass") is True
        )
        return {
            "schema": SCHEMA,
            "status": (
                "UNIFIED_SPECIALIZED_EXECUTION_REPAIRED"
                if repaired else "UNIFIED_SPECIALIZED_EXECUTION_COMPLETE"
            ),
            "pass": passed or repaired,
            "surface": name,
            "raw_result": raw,
            "learning": learning,
            "auto_repair_attempted": automatic_repair is not None,
            "automatic_repair": automatic_repair,
            "terminal_authority": False,
            "capability_promotion_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail("SPECIALIZED_RUNTIME_EXCEPTION:" + type(exc).__name__ + ":" + str(exc), surface=name)


def run(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path = ROOT,
    information_provider: Callable[[Mapping[str, Any], int], Mapping[str, Any] | None] | None = None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Compatibility/subordinate execution router; the canonical public entrypoint is Unified Cognitive Fabric V1."""
    if not isinstance(request, Mapping):
        return _fail("REQUEST_NOT_OBJECT")

    mode = str(request.get("mode") or "").strip()
    if not mode:
        if isinstance(request.get("goal"), str) and request.get("goal"):
            mode = "decision"
        elif isinstance(request.get("problem"), Mapping):
            mode = "generic"
        elif all(k in request for k in ("task_id", "initial_facts", "target_effects")):
            mode = "compiled_bound"
        else:
            mode = "inventory"

    if mode == "inventory":
        return inventory(state_path=request.get("state_path"))

    if mode == "decision":
        nested = request.get("request")
        if isinstance(nested, Mapping):
            payload = nested
        else:
            allowed = {
                "task_id", "goal", "decision_payload", "goal_to_decision_binding",
                "execution_problem", "policy_execution_binding", "goal_satisfaction_binding",
                "max_information_rounds", "episode_id", "scope_id",
            }
            payload = {k: deepcopy(v) for k, v in request.items() if k in allowed}
        return run_decision(
            payload,
            repo_root=repo_root,
            state_path=request.get("state_path"),
            information_provider=information_provider,
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
            known_absent_invalidators=request.get("known_absent_invalidators") or (),
            learn=request.get("learn", True) is not False,
            auto_repair=request.get("auto_repair", True) is not False,
            repair_components=request.get("repair_components") or (),
        )

    if mode == "generic":
        problem = request.get("problem")
        if not isinstance(problem, Mapping):
            return _fail("GENERIC_PROBLEM_REQUIRED")
        return run_generic(
            problem,
            repo_root=repo_root,
            state_path=request.get("state_path"),
            episode_id=str(request.get("episode_id") or problem.get("task_id") or "episode"),
            scope_id=str(request.get("scope_id") or "unified-live-brain"),
            active_invalidators=request.get("active_invalidators") or (),
            known_absent_invalidators=request.get("known_absent_invalidators") or (),
            learn=request.get("learn", True) is not False,
            auto_repair=request.get("auto_repair", True) is not False,
            repair_components=request.get("repair_components") or (),
            solver_kwargs=request.get("solver_kwargs") or {},
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
        )

    if mode == "compiled_bound":
        nested = request.get("request")
        payload = nested if isinstance(nested, Mapping) else request
        raw = _bound_run(payload)
        learning = _observe_runtime_outcome(
            raw,
            state_path=request.get("state_path"),
            learn=request.get("learn", True) is not False,
            retry_context={
                "mode": "compiled_bound",
                "request": deepcopy(dict(payload)),
                "learn": True,
            },
        )
        automatic_repair = _automatic_failure_repair(
            learning,
            repo_root=repo_root,
            state_path=request.get("state_path"),
            initial_facts=payload.get("initial_facts") or (),
            repair_components=request.get("repair_components") or (),
            information_provider=information_provider,
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
            enabled=request.get("auto_repair", True) is not False,
        )
        repaired = (
            isinstance(automatic_repair, Mapping)
            and automatic_repair.get("pass") is True
        )
        return {
            "schema": SCHEMA,
            "status": (
                "UNIFIED_BOUND_EXECUTION_REPAIRED"
                if repaired else "UNIFIED_BOUND_EXECUTION_COMPLETE"
            ),
            "pass": raw.get("pass") is True or repaired,
            "raw_result": raw,
            "learning": learning,
            "auto_repair_attempted": automatic_repair is not None,
            "automatic_repair": automatic_repair,
            "terminal_authority": False,
            "capability_promotion_authority": False,
            "terminal_credit_delta": 0,
        }

    if mode == "raw_bound":
        nested = request.get("request")
        payload = nested if isinstance(nested, Mapping) else request
        raw = _raw_bound_run(payload)
        learning = _observe_runtime_outcome(
            raw,
            state_path=request.get("state_path"),
            learn=request.get("learn", True) is not False,
            retry_context={
                "mode": "raw_bound",
                "request": deepcopy(dict(payload)),
                "learn": True,
            },
        )
        automatic_repair = _automatic_failure_repair(
            learning,
            repo_root=repo_root,
            state_path=request.get("state_path"),
            initial_facts=payload.get("initial_facts") or (),
            repair_components=request.get("repair_components") or (),
            information_provider=information_provider,
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
            enabled=request.get("auto_repair", True) is not False,
        )
        repaired = (
            isinstance(automatic_repair, Mapping)
            and automatic_repair.get("pass") is True
        )
        return {
            "schema": SCHEMA,
            "status": (
                "UNIFIED_RAW_BOUND_EXECUTION_REPAIRED"
                if repaired else "UNIFIED_RAW_BOUND_EXECUTION_COMPLETE"
            ),
            "pass": raw.get("pass") is True or repaired,
            "raw_result": raw,
            "learning": learning,
            "semantic_acceptance_complete": (
                raw.get("semantic_acceptance_complete") is True or repaired
            ),
            "auto_repair_attempted": automatic_repair is not None,
            "automatic_repair": automatic_repair,
            "terminal_authority": False,
            "capability_promotion_authority": False,
            "terminal_credit_delta": 0,
        }

    if mode == "repair_synthesis":
        nested = request.get("request")
        payload = nested if isinstance(nested, Mapping) else request
        return synthesize_failure_repair(
            payload,
            state_path=request.get("state_path"),
        )

    if mode == "repair_cycle":
        nested = request.get("request")
        payload = nested if isinstance(nested, Mapping) else request
        return execute_failure_repair_cycle(
            payload,
            repo_root=repo_root,
            state_path=request.get("state_path"),
            information_provider=information_provider,
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
        )

    if mode == "development_schedule":
        work = request.get("work")
        if not isinstance(work, Sequence) or isinstance(work, (str, bytes)):
            return _fail("WORK_SEQUENCE_REQUIRED")
        try:
            ranked = _rank_work(work)
            return {
                "schema": SCHEMA,
                "status": "UNIFIED_DEVELOPMENT_SCHEDULE_READY",
                "pass": True,
                "scheduler_result": ranked,
                "scheduler_role": "DEVELOPMENT_PRIORITY_NOT_TASK_SUCCESS_AUTHORITY",
                "execution_authority": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }
        except Exception as exc:
            return _fail("DEVELOPMENT_SCHEDULER_EXCEPTION:" + type(exc).__name__ + ":" + str(exc))

    if mode == "specialized":
        return run_specialized(
            str(request.get("surface") or ""),
            request.get("payload") or {},
            repo_root=repo_root,
            state_path=request.get("state_path"),
            learn=request.get("learn", True) is not False,
            auto_repair=request.get("auto_repair", True) is not False,
            repair_components=request.get("repair_components") or (),
            information_provider=information_provider,
            proposal_provider=proposal_provider,
            capability_expander=capability_expander,
        )

    if mode == "skill_plan":
        problem = request.get("problem")
        if not isinstance(problem, Mapping):
            return _fail("SKILL_PLAN_PROBLEM_REQUIRED")
        try:
            ctx = _active_learning_context(
                request.get("state_path"),
                scope_id=str(request.get("scope_id") or "unified-live-brain"),
                episode_id=str(request.get("episode_id") or "planning"),
            )
            planned = _skill_plan(problem, ctx["active_verified_skills"], request.get("active_invalidators") or ())
            return {
                "schema": SCHEMA,
                "status": "UNIFIED_VERIFIED_SKILL_PLAN_READY",
                "pass": planned.get("pass") is True,
                "planner_result": planned,
                "active_verified_skill_count": len(ctx["active_verified_skills"]),
                "execution_authority": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }
        except Exception as exc:
            return _fail("SKILL_PLANNER_EXCEPTION:" + type(exc).__name__ + ":" + str(exc))

    return _fail("MODE_INVALID:" + mode)
