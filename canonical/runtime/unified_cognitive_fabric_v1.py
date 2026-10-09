"""Unified Cognitive Fabric V1.

One typed live front door over the Brain's current verified execution,
adequate-decision, adaptive-solving, P3, and self-improvement systems.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import live_integrated_brain_v1 as live_brain
from canonical.runtime import p3_real_context_v3_admission_v12 as p3
from canonical.runtime import autonomous_verified_self_improvement_v1 as self_improvement
from canonical.runtime import r3_improvement_queue_driver_v1 as improvement_driver
from canonical.runtime import live_brain_runtime_v1 as live_runtime
from canonical.runtime import h100_verified_capability_registry_v8 as h100_inference
from canonical.runtime import exact_linear_parameter_polytope_v1 as mystery_polytope
from canonical.runtime import interval_information_frontier_v1 as mystery_information
from canonical.runtime import capability_first_scheduler_v1 as capability_scheduler
from canonical.runtime.brain_owned_python_closure_census_v1 import census as closure_census
from canonical.runtime.current_authority_runtime_census_v1 import run as authority_runtime_census
from canonical.runtime import live_capability_ownership_v1 as live_ownership
from canonical.runtime import live_capability_invoker_v1 as live_invoker
from canonical.runtime import live_capability_composition_v1 as live_composition
from canonical.runtime import r1_live_architecture_closure_gate_v1 as r1_closure_gate
from canonical.runtime import universal_escape_resolver_v1 as universal_escape
from canonical.runtime import certificate_gated_selected_route_runtime_entrypoint_v2 as certified_route
from canonical.runtime import terminal_autopilot_v1 as terminal_autopilot
from canonical.runtime import terminal_root_decision_gate_v1 as terminal_root
from canonical.runtime import terminal_closure_reducer as terminal_closure
from canonical.runtime.verified_bound_capability_execution_adapter_v1 import execute as execute_bound
from canonical.runtime import semantic_ambiguity_control_v1 as semantic_ambiguity
from canonical.runtime import semantic_relation_control_v1 as semantic_relation
from canonical.runtime import oewn_decision_sense_control_v1 as oewn_decision_sense
from canonical.runtime import finance_bounded_concept_registry_verify_v1 as finance_concept_verify
from canonical.runtime import one_shot_reality_closure_v2 as one_shot_reality_closure

SCHEMA = "PROJECT_BRAIN_UNIFIED_COGNITIVE_FABRIC_V1"
ROOT = Path(__file__).resolve().parents[2]

ENGINE_DESCRIPTORS = {
    "RAW_GOAL": "live_brain_runtime_v1.run(raw_bound)",
    "COMPILED_TASK": "live_brain_runtime_v1.run(compiled_bound)",
    "ADEQUATE_DECISION": "live_brain_runtime_v1.run(decision)",
    "P3": "p3_real_context_v3_admission_v12.evaluate",
    "ADAPTIVE_SOLVER": "live_brain_runtime_v1.run(generic)",
    "LEARNING_EPISODE": "autonomous_verified_self_improvement_v1.run_learning_episode",
    "IMPROVEMENT_CYCLE": "r3_improvement_queue_driver_v1.drain",
    "BOUND_CAPABILITY": "verified_bound_capability_execution_adapter_v1.execute",
    "H100_INFERENCE": "h100_verified_capability_registry_v8",
    "MYSTERY_INFERENCE": "exact_linear_parameter_polytope_v1 + interval_information_frontier_v1",
    "CAPABILITY_SCHEDULER": "capability_first_scheduler_v1.rank_work",
    "REPAIR_SYNTHESIS": "live_brain_runtime_v1.synthesize_failure_repair",
    "REPAIR_CYCLE": "live_brain_runtime_v1.execute_failure_repair_cycle",
    "UNIVERSAL_ESCAPE": "universal_escape_resolver_v1.resolve",
    "CERTIFIED_ROUTE": "certificate_gated_selected_route_runtime_entrypoint_v2",
    "TERMINAL_AUTOPILOT": "terminal_autopilot_v1",
    "TERMINAL_ROOT": "terminal_root_decision_gate_v1.evaluate",
    "TERMINAL_CLOSURE": "terminal_closure_reducer",
    "OWNERSHIP_CATALOG": "live_capability_ownership_v1.evaluate",
    "LIVE_CAPABILITY": "live_capability_invoker_v1.invoke",
    "LIVE_COMPOSITION": "live_capability_composition_v1.execute",
    "SEMANTIC_AMBIGUITY": "semantic_ambiguity_control_v1.decide",
    "SEMANTIC_RELATION": "semantic_relation_control_v1.resolve",
    "OEWN_DECISION_SENSE": "oewn_decision_sense_control_v1.resolve",
}

META_ORCHESTRATORS = {
    "ONE_SHOT_REALITY_CLOSURE": "one_shot_reality_closure_v2.run",
}

KNOWN_R1_RESIDUALS: tuple[str, ...] = ()
CROSS_ROOT_BOUNDARIES = (
    "ARBITRARY_RAW_LANGUAGE_SEMANTIC_CLOSURE_REMAINS_R2_COVERAGE_NOT_R1_ROUTING",
    "HISTORICAL_SUPERSEDED_REPOSITORY_CAPABILITY_CENSUS_IS_OUTSIDE_CURRENT_LIVE_OWNERSHIP_SCOPE",
)


R3_DIRECT_EXPERIENCE_MODES = frozenset({
    "P3",
    "H100_INFERENCE",
    "MYSTERY_INFERENCE",
    "UNIVERSAL_ESCAPE",
    "CERTIFIED_ROUTE",
    "LIVE_CAPABILITY",
    "BOUND_CAPABILITY",
})


def _bounded_r3_direct_observation(
    mode: str,
    out: Mapping[str, Any],
) -> dict[str, Any]:
    """Retain learning-relevant structure without arbitrary result payloads."""
    observation: dict[str, Any] = {
        "schema": "PROJECT_BRAIN_R3_DIRECT_SURFACE_OBSERVATION_V1",
        "pass": out.get("pass") is True,
        "status": str(out.get("status") or "").strip()
        or "UNSPECIFIED_DIRECT_SURFACE_STATUS",
        "source_mode": mode,
        "source_schema": str(out.get("schema") or "").strip() or None,
        "source_key_set": sorted(
            str(key) for key in out.keys() if isinstance(key, str)
        )[:128],
    }
    for key in (
        "failure_class",
        "capability_id",
        "route",
        "operation",
        "step_count",
        "executed_step_count",
    ):
        value = out.get(key)
        if value is None or isinstance(value, (str, int, float, bool)):
            observation[key] = value
    return observation


CANONICAL_PUBLIC_ENTRYPOINT = "canonical.runtime.unified_cognitive_fabric_v1.run"
SUBORDINATE_RUNTIME_ENTRYPOINT = "canonical.runtime.live_brain_runtime_v1.run"


class CognitiveFabricError(ValueError):
    pass


def _unwrap_live_runtime(wrapper: Mapping[str, Any], inner_key: str) -> dict[str, Any]:
    if not isinstance(wrapper, Mapping):
        raise CognitiveFabricError("SUBORDINATE_RUNTIME_RESULT_NOT_OBJECT")
    inner = wrapper.get(inner_key)
    if not isinstance(inner, Mapping):
        return deepcopy(dict(wrapper))
    out = deepcopy(dict(inner))
    if wrapper.get("pass") is True and inner.get("pass") is not True:
        out["pre_repair_status"] = inner.get("status")
        out["status"] = wrapper.get("status")
        out["pass"] = True
    out["_live_runtime"] = {
        "status": wrapper.get("status"),
        "learning": deepcopy(wrapper.get("learning")),
        "reuse_first": wrapper.get("reuse_first") is True,
        "reused_skill_id": wrapper.get("reused_skill_id"),
        "auto_repair_attempted": wrapper.get("auto_repair_attempted") is True,
        "auto_repair": deepcopy(wrapper.get("auto_repair")),
        "canonical_public_entrypoint": CANONICAL_PUBLIC_ENTRYPOINT,
        "subruntime_entrypoint": SUBORDINATE_RUNTIME_ENTRYPOINT,
    }
    return out


def _auto_mode(payload: Mapping[str, Any], options: Mapping[str, Any]) -> str:
    """Select only structurally unambiguous fabric routes; otherwise fail closed."""
    keys = set(payload)

    if {"sense_universe", "decision_manifest"} <= keys:
        return "OEWN_DECISION_SENSE"

    if {
        "ambiguity_owner",
        "hypothesis_set_complete",
        "worlds",
        "observations",
    } <= keys:
        return "SEMANTIC_AMBIGUITY"

    if {
        "left_id",
        "right_id",
        "scope_id",
        "required_relation",
    } <= keys:
        return "SEMANTIC_RELATION"

    if isinstance(payload.get("composition_steps"), list):
        return "LIVE_COMPOSITION"

    if {"capability_id", "capability_payload"} <= keys:
        return "LIVE_CAPABILITY"

    if {"capability_id", "inputs"} <= keys:
        return "BOUND_CAPABILITY"

    if isinstance(payload.get("work"), list):
        return "CAPABILITY_SCHEDULER"

    if isinstance(payload.get("failure_fingerprint"), str) and isinstance(payload.get("components"), list):
        has_executable = any(
            isinstance(row, Mapping) and isinstance(row.get("executable_capability"), Mapping)
            for row in payload["components"]
        )
        return "REPAIR_CYCLE" if has_executable else "REPAIR_SYNTHESIS"

    operation = str(payload.get("operation") or "").strip().upper()
    if operation:
        if isinstance(payload.get("problem"), Mapping):
            return "MYSTERY_INFERENCE"
        if operation in {"SNAPSHOT", "RESOLVE", "PREDICT"}:
            return "H100_INFERENCE"

    if {
        "escape_cell_id",
        "escape_membership_bound",
        "admission_candidates",
        "v9_args",
    } <= keys:
        return "UNIVERSAL_ESCAPE"

    if {"task_id", "initial_facts", "target_effects", "capability_inputs"} <= keys:
        return "COMPILED_TASK"

    if {"task_id", "capabilities", "target_effects"} <= keys:
        learning_option_keys = {
            "state_path",
            "episode_verification_binding",
            "skill_verification_binding",
            "resume_binding",
            "known_absent_invalidators",
        }
        return (
            "LEARNING_EPISODE"
            if learning_option_keys & set(options)
            else "ADAPTIVE_SOLVER"
        )

    if {"task_id", "goal"} <= keys:
        # Raw intent belongs to R2. The fixed-point R2 controller may acquire a
        # sound decision context, but no routing heuristic is allowed to bypass
        # semantic decision/acceptance authority merely because the caller
        # supplied only natural language.
        return "ADEQUATE_DECISION"

    raise CognitiveFabricError("AUTO_ROUTE_AMBIGUOUS_OR_UNMODELED")


def catalog() -> dict[str, Any]:
    bound = live_brain.load_verified_registry()
    state = self_improvement.load_state()
    closure = closure_census(
        ROOT,
        ["canonical/runtime/unified_cognitive_fabric_v1.py"],
    )
    authority_census = authority_runtime_census(ROOT)
    ownership = live_ownership.evaluate(ENGINE_DESCRIPTORS)
    invocation = live_invoker.coverage(ownership["live_owned_capability_ids"])
    architecture_gate = r1_closure_gate.evaluate(
        ENGINE_DESCRIPTORS,
        ownership=ownership,
        invocation=invocation,
        subruntime_surfaces=live_runtime.SURFACES,
        canonical_public_entrypoint=CANONICAL_PUBLIC_ENTRYPOINT,
        subordinate_runtime_entrypoint=SUBORDINATE_RUNTIME_ENTRYPOINT,
    )
    r1_closed = bool(
        ownership["r1_structural_closure"]
        and invocation["pass"]
        and architecture_gate["pass"]
    )
    r1_residuals = list(architecture_gate["errors"])
    return {
        "schema": SCHEMA,
        "status": "LIVE_FEDERATED_COGNITIVE_FABRIC",
        "engine_count": len(ENGINE_DESCRIPTORS),
        "engines": dict(ENGINE_DESCRIPTORS),
        "verified_bound_capability_count": len(bound),
        "verified_bound_capability_ids": sorted(bound),
        "verified_learned_skill_count": int(state.get("stats", {}).get("verified_skill_count", 0)),
        "active_learned_skill_count": int(state.get("stats", {}).get("active_skill_count", 0)),
        "brain_owned_transitive_file_count": closure["brain_owned_file_count"],
        "brain_owned_transitive_source_bytes": closure["brain_owned_transitive_source_bytes"],
        "brain_owned_transitive_files": [
            row["path"] for row in closure["brain_owned_transitive_files"]
        ],
        "authority_pointer_runtime_reachability_census": authority_census,
        "authority_pointer_runtime_reference_reachability_complete": authority_census["pass"],
        "authority_pointer_runtime_reference_missing_count": authority_census[
            "authority_pointer_reference_missing_count"
        ],
        "authority_pointer_runtime_reference_missing_paths": authority_census[
            "authority_pointer_reference_missing_paths"
        ],
        "live_capability_ownership": ownership,
        "live_owned_capability_count": ownership["live_owned_capability_count"],
        "live_owned_capability_ids": ownership["live_owned_capability_ids"],
        "live_owned_equals_fabric_reachable": ownership["live_owned_equals_fabric_reachable"],
        "current_live_ownership_ontology_complete": ownership["provider_coverage_complete"],
        "live_capability_invocation_coverage": invocation,
        "all_live_owned_capabilities_universally_invocable": invocation["pass"],
        "r1_live_architecture_closure_gate": architecture_gate,
        "r1_drift_locked": architecture_gate["pass"],
        "r1_structural_closure": r1_closed,
        "known_r1_residuals": r1_residuals,
        "known_unified_fabric_residuals": r1_residuals,
        "cross_root_boundaries": list(CROSS_ROOT_BOUNDARIES),
        "canonical_public_entrypoint": CANONICAL_PUBLIC_ENTRYPOINT,
        "subordinate_runtime_entrypoint": SUBORDINATE_RUNTIME_ENTRYPOINT,
        "subordinate_runtime_public_authority": False,
        "single_front_door": True,
        "meta_orchestrators": dict(META_ORCHESTRATORS),
        "all_historical_brain_capabilities_unified": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }



def _run_adequate_decision_engine(
    payload: Mapping[str, Any],
    options: Mapping[str, Any],
    *,
    information_provider=None,
    proposal_provider=None,
    capability_expander=None,
    episode_verification_provider=None,
    skill_verification_provider=None,
) -> dict[str, Any]:
    """Execute the canonical decision engine path used for initial dispatch and replay."""
    wrapped = live_runtime.run(
        {"mode": "decision", "request": deepcopy(dict(payload)), **dict(options)},
        repo_root=ROOT,
        information_provider=information_provider,
        proposal_provider=proposal_provider,
        capability_expander=capability_expander,
        episode_verification_provider=episode_verification_provider,
        skill_verification_provider=skill_verification_provider,
    )
    return _unwrap_live_runtime(wrapped, "decision_output")


def _decision_requires_user_information(out: Mapping[str, Any]) -> bool:
    if out.get("ask_user_required") is True:
        return True
    if str(out.get("action") or "").strip() == "ASK_USER_MINIMUM_CLARIFICATION":
        return True
    request = out.get("next_information_request")
    if isinstance(request, Mapping) and request.get("user_only") is True:
        return True
    return False


def _auto_one_shot_summary(closure: Mapping[str, Any]) -> dict[str, Any]:
    gap = closure.get("gap_contract")
    return {
        "attempted": True,
        "closure_pass": closure.get("pass") is True,
        "closure_status": closure.get("status"),
        "fixed_point": closure.get("fixed_point") is True,
        "gap_class": (
            gap.get("gap_class")
            if isinstance(gap, Mapping)
            else None
        ),
        "proven_external": (
            closure.get("status") == "PASS__PROVEN_INFORMATION_THEORETICALLY_EXTERNAL"
        ),
        "terminal_authority": False,
    }



def run(
    request: Mapping[str, Any],
    *,
    information_provider: Callable[[Mapping[str, Any], int], Mapping[str, Any] | None] | None = None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
    episode_verification_provider=None,
    skill_verification_provider=None,
    success_episode_adapter_provider=None,
    semantic_authority_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    semantic_evidence_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    verification_frontier_acquisition_provider: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    verification_frontier_acquisition_provider_id: str = (
        "HOST_VERIFICATION_FRONTIER_ACQUISITION_PROVIDER"
    ),
    r3_distinguishing_evidence_provider: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    r3_distinguishing_evidence_provider_id: str = (
        "HOST_R3_DISTINGUISHING_EVIDENCE_PROVIDER"
    ),
    one_shot_failure_repair_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    one_shot_externality_certificate_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    one_shot_capability_synthesis_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    one_shot_evidence_acquisition_provider: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(request, Mapping):
            raise CognitiveFabricError("REQUEST_NOT_OBJECT")
        requested_mode = str(request.get("mode") or "").strip().upper()
        if requested_mode == "CATALOG":
            return catalog()
        if requested_mode == "ONE_SHOT_REALITY_CLOSURE":
            options = request.get("options") or {}
            if not isinstance(options, Mapping):
                raise CognitiveFabricError("OPTIONS_NOT_OBJECT")
            out = one_shot_reality_closure.run(
                repo_root=ROOT,
                state_path=options.get("state_path"),
                verification_frontier_acquisition_provider=(
                    verification_frontier_acquisition_provider
                ),
                verification_frontier_acquisition_provider_id=(
                    verification_frontier_acquisition_provider_id
                ),
                failure_repair_provider=one_shot_failure_repair_provider,
                externality_certificate_provider=(
                    one_shot_externality_certificate_provider
                ),
                capability_synthesis_provider=(
                    one_shot_capability_synthesis_provider
                ),
                evidence_acquisition_provider=(
                    one_shot_evidence_acquisition_provider
                ),
                max_repair_rounds=int(options.get("one_shot_max_repair_rounds", 8)),
                v1_max_rounds=int(options.get("one_shot_v1_max_rounds", 64)),
                v1_max_actions_per_round=int(
                    options.get("one_shot_v1_max_actions_per_round", 32)
                ),
            )
            return {
                "schema": SCHEMA,
                "status": "FABRIC_META_ORCHESTRATOR_COMPLETE",
                "mode": requested_mode,
                "requested_mode": requested_mode,
                "auto_routed": False,
                "engine": META_ORCHESTRATORS[requested_mode],
                "inner_pass": out.get("pass") is True,
                "inner_status": out.get("status"),
                "result": deepcopy(dict(out)),
                "single_front_door": True,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }

        payload = request.get("payload")
        if not isinstance(payload, Mapping):
            raise CognitiveFabricError("PAYLOAD_NOT_OBJECT")
        options = request.get("options") or {}
        if not isinstance(options, Mapping):
            raise CognitiveFabricError("OPTIONS_NOT_OBJECT")

        auto_routed = requested_mode in {"", "AUTO"}
        mode = _auto_mode(payload, options) if auto_routed else requested_mode
        if (
            auto_routed
            and mode == "ADAPTIVE_SOLVER"
            and (
                episode_verification_provider is not None
                or skill_verification_provider is not None
            )
        ):
            mode = "LEARNING_EPISODE"
        if mode not in ENGINE_DESCRIPTORS:
            raise CognitiveFabricError("MODE_INVALID:" + mode)

        if mode == "RAW_GOAL":
            wrapped = live_runtime.run(
                {"mode": "raw_bound", "request": deepcopy(dict(payload)), **dict(options)},
                repo_root=ROOT,
                information_provider=information_provider,
                proposal_provider=proposal_provider,
                capability_expander=capability_expander,
                episode_verification_provider=episode_verification_provider,
                skill_verification_provider=skill_verification_provider,
            )
            out = _unwrap_live_runtime(wrapped, "raw_result")
        elif mode == "COMPILED_TASK":
            wrapped = live_runtime.run(
                {"mode": "compiled_bound", "request": deepcopy(dict(payload)), **dict(options)},
                repo_root=ROOT,
                information_provider=information_provider,
                proposal_provider=proposal_provider,
                capability_expander=capability_expander,
                episode_verification_provider=episode_verification_provider,
                skill_verification_provider=skill_verification_provider,
            )
            out = _unwrap_live_runtime(wrapped, "raw_result")
        elif mode == "ADEQUATE_DECISION":
            out = _run_adequate_decision_engine(
                payload,
                options,
                information_provider=information_provider,
                proposal_provider=proposal_provider,
                capability_expander=capability_expander,
                episode_verification_provider=episode_verification_provider,
                skill_verification_provider=skill_verification_provider,
            )
        elif mode == "P3":
            out = p3.evaluate(payload, repo_root=ROOT)
        elif mode == "ADAPTIVE_SOLVER":
            solver_kwargs = {
                "proposal_provider_id": str(options.get("proposal_provider_id") or "HOST_GENERAL_COGNITION_SUBSTRATE"),
                "proposal_provider_max_candidates": int(options.get("proposal_provider_max_candidates", 4)),
                "capability_expander_id": str(options.get("capability_expander_id") or "HOST_CAPABILITY_EXPANDER"),
                "max_capability_expansions": int(options.get("max_capability_expansions", 4)),
            }
            wrapped = live_runtime.run(
                {
                    "mode": "generic",
                    "problem": deepcopy(dict(payload)),
                    **dict(options),
                    "solver_kwargs": solver_kwargs,
                },
                repo_root=ROOT,
                information_provider=information_provider,
                proposal_provider=proposal_provider,
                capability_expander=capability_expander,
                episode_verification_provider=episode_verification_provider,
                skill_verification_provider=skill_verification_provider,
            )
            out = _unwrap_live_runtime(wrapped, "solver_output")
        elif mode == "H100_INFERENCE":
            operation = str(payload.get("operation") or "").strip().upper()
            if operation == "SNAPSHOT":
                snap = h100_inference.registry_snapshot()
                out = {"pass": True, **snap}
            elif operation == "RESOLVE":
                rows = payload.get("rows")
                if not isinstance(rows, list):
                    raise CognitiveFabricError("H100_ROWS_MUST_BE_LIST")
                out = h100_inference.resolve_verified_capability(
                    rows,
                    target=str(payload.get("target") or ""),
                    input_name=payload.get("input_name"),
                    exact_nrmse=float(payload.get("exact_nrmse", 1e-8)),
                )
                out = {
                    "pass": out.get("status") == "LIBRARY_HIT__VERIFY_BEFORE_USE",
                    **out,
                }
            elif operation == "PREDICT":
                resolution = payload.get("resolution")
                point = payload.get("point")
                if not isinstance(resolution, Mapping):
                    raise CognitiveFabricError("H100_RESOLUTION_NOT_OBJECT")
                if not isinstance(point, Mapping):
                    raise CognitiveFabricError("H100_POINT_NOT_OBJECT")
                value = h100_inference.predict(resolution, point)
                out = {
                    "pass": True,
                    "status": "PASS__H100_VERIFIED_CAPABILITY_PREDICTION",
                    "prediction": value,
                    "registry_schema": h100_inference.SCHEMA,
                }
            else:
                raise CognitiveFabricError("H100_OPERATION_INVALID:" + operation)
        elif mode == "MYSTERY_INFERENCE":
            operation = str(payload.get("operation") or "").strip().upper()
            problem = payload.get("problem")
            if not isinstance(problem, Mapping):
                raise CognitiveFabricError("MYSTERY_PROBLEM_NOT_OBJECT")
            if operation == "EXACT_LINEAR_POLYTOPE":
                out = mystery_polytope.solve(problem)
            elif operation == "INTERVAL_INFORMATION_POLICY":
                out = mystery_information.solve(problem)
            else:
                raise CognitiveFabricError("MYSTERY_OPERATION_INVALID:" + operation)
        elif mode == "SEMANTIC_AMBIGUITY":
            out = semantic_ambiguity.decide(payload)
        elif mode == "SEMANTIC_RELATION":
            concept_verifier = semantic_authority_verifier
            concept_claim = payload.get("shared_concept_identity_receipt")
            if (
                concept_verifier is None
                and isinstance(concept_claim, Mapping)
                and concept_claim.get("schema") == finance_concept_verify.CLAIM_SCHEMA
            ):
                concept_verifier = lambda value: finance_concept_verify.verify_claim(
                    value,
                    repo_root=ROOT,
                )
            out = semantic_relation.resolve(
                payload,
                concept_identity_verifier=concept_verifier,
                terminal_signature_verifier=semantic_authority_verifier,
                relation_edge_verifier=semantic_authority_verifier,
            )
        elif mode == "OEWN_DECISION_SENSE":
            out = oewn_decision_sense.resolve(
                sense_universe=payload.get("sense_universe"),
                decision_manifest=payload.get("decision_manifest"),
                authority_receipt=payload.get("authority_receipt"),
                authority_verifier=semantic_authority_verifier,
                evidence_receipts=payload.get("evidence_receipts"),
                evidence_verifier=semantic_evidence_verifier,
                ambiguity_owner=str(payload.get("ambiguity_owner") or "SYSTEM_MODEL"),
            )
        elif mode == "CAPABILITY_SCHEDULER":
            work = payload.get("work")
            if not isinstance(work, list):
                raise CognitiveFabricError("SCHEDULER_WORK_MUST_BE_LIST")
            out = capability_scheduler.rank_work(work)
            out = {"pass": True, **out}
        elif mode == "REPAIR_SYNTHESIS":
            out = live_runtime.synthesize_failure_repair(
                payload,
                state_path=options.get("state_path"),
            )
        elif mode == "REPAIR_CYCLE":
            out = live_runtime.execute_failure_repair_cycle(
                payload,
                repo_root=ROOT,
                state_path=options.get("state_path"),
                information_provider=information_provider,
                proposal_provider=proposal_provider,
                capability_expander=capability_expander,
            )
        elif mode == "UNIVERSAL_ESCAPE":
            out = universal_escape.resolve(**dict(payload))
        elif mode == "CERTIFIED_ROUTE":
            operation = str(payload.get("operation") or "").strip().upper()
            if operation == "PREFLIGHT":
                out = certified_route.preflight()
            elif operation == "DISPATCH":
                context = payload.get("context")
                route_payload = payload.get("route_payload")
                if not isinstance(context, Mapping):
                    raise CognitiveFabricError("CERTIFIED_ROUTE_CONTEXT_NOT_OBJECT")
                if not isinstance(route_payload, Mapping):
                    raise CognitiveFabricError("CERTIFIED_ROUTE_PAYLOAD_NOT_OBJECT")
                out = certified_route.dispatch(context, route_payload)
                out = {"pass": True, **out}
            else:
                raise CognitiveFabricError("CERTIFIED_ROUTE_OPERATION_INVALID:" + operation)
        elif mode == "TERMINAL_AUTOPILOT":
            operation = str(payload.get("operation") or "").strip().upper()
            if operation == "BUILD_MANIFEST":
                out = terminal_autopilot.build_manifest_from_repo(
                    ROOT,
                    max_concurrency=int(payload.get("max_concurrency", 32)),
                )
                out = {"pass": True, "status": "PASS__TERMINAL_AUTOPILOT_MANIFEST_BUILT", **out}
            elif operation == "PLAN":
                manifest = payload.get("manifest")
                if not isinstance(manifest, Mapping):
                    raise CognitiveFabricError("TERMINAL_AUTOPILOT_MANIFEST_NOT_OBJECT")
                out = terminal_autopilot.plan(dict(manifest))
            else:
                raise CognitiveFabricError("TERMINAL_AUTOPILOT_OPERATION_INVALID:" + operation)
        elif mode == "TERMINAL_ROOT":
            out = terminal_root.evaluate(payload, repo_root=ROOT)
        elif mode == "TERMINAL_CLOSURE":
            operation = str(payload.get("operation") or "").strip().upper()
            if operation == "MANIFEST":
                manifest = payload.get("manifest")
                if not isinstance(manifest, Mapping):
                    raise CognitiveFabricError("TERMINAL_CLOSURE_MANIFEST_NOT_OBJECT")
                verdict = terminal_closure.evaluate_manifest(dict(manifest), repo_root=ROOT)
                out = {
                    "pass": verdict.get("achieved") is True,
                    "status": (
                        "PASS__TERMINAL_CLOSURE_ACHIEVED"
                        if verdict.get("achieved") is True
                        else "OPEN__TERMINAL_CLOSURE_NOT_ACHIEVED"
                    ),
                    **verdict,
                }
            elif operation == "FRONTIER":
                active = payload.get("active_hierarchy")
                universe = payload.get("global_universe")
                prequalification = payload.get("prequalification")
                if not all(isinstance(x, Mapping) for x in (active, universe, prequalification)):
                    raise CognitiveFabricError("TERMINAL_FRONTIER_INPUT_NOT_OBJECT")
                verdict = terminal_closure.evaluate_frontier_state(
                    dict(active), dict(universe), dict(prequalification)
                )
                out = {
                    "pass": verdict.get("status") != "FAIL_CLOSED",
                    **verdict,
                }
            else:
                raise CognitiveFabricError("TERMINAL_CLOSURE_OPERATION_INVALID:" + operation)
        elif mode == "OWNERSHIP_CATALOG":
            out = live_ownership.evaluate(ENGINE_DESCRIPTORS)
        elif mode == "LIVE_COMPOSITION":
            depth = int(options.get("__live_capability_depth", 0))
            if depth >= 8:
                raise CognitiveFabricError("LIVE_COMPOSITION_RECURSION_LIMIT")

            def _composition_engine_runner(
                target_mode: str,
                target_payload: Mapping[str, Any],
                target_options: Mapping[str, Any],
            ) -> Mapping[str, Any]:
                nested_options = dict(target_options)
                nested_options["__live_capability_depth"] = depth + 1
                return run(
                    {
                        "mode": target_mode,
                        "payload": dict(target_payload),
                        "options": nested_options,
                    },
                    information_provider=information_provider,
                    proposal_provider=proposal_provider,
                    capability_expander=capability_expander,
                    episode_verification_provider=episode_verification_provider,
                    skill_verification_provider=skill_verification_provider,
                    success_episode_adapter_provider=success_episode_adapter_provider,
                )

            composition_options = dict(options)
            if proposal_provider is not None:
                composition_options["proposal_provider"] = proposal_provider
            if capability_expander is not None:
                composition_options["capability_expander"] = capability_expander

            def _invoke_composed_capability(
                capability_id: str,
                capability_payload: Mapping[str, Any],
                capability_options: Mapping[str, Any],
            ) -> Mapping[str, Any]:
                return live_invoker.invoke(
                    capability_id,
                    capability_payload,
                    engine_runner=_composition_engine_runner,
                    options=capability_options,
                )

            composed = live_composition.execute(
                payload,
                invoke_capability=_invoke_composed_capability,
                options=composition_options,
            )
            out = deepcopy(dict(composed))
            observation = out.get("learning_observation")
            if isinstance(observation, Mapping):
                try:
                    out["learning"] = live_runtime.observe_runtime_outcome(
                        observation,
                        state_path=options.get("state_path"),
                        learn=options.get("learn", True) is not False,
                        surface="LIVE_COMPOSITION",
                        retry_context={
                            "mode": "fabric_direct",
                            "request": {
                                "mode": mode,
                                "payload": deepcopy(dict(payload)),
                                "options": {"learn": False},
                            },
                            "learn": True,
                        },
                    )
                    out["learning_observation_error"] = None
                except Exception as exc:
                    out["learning"] = None
                    out["learning_observation_error"] = (
                        type(exc).__name__ + ":" + str(exc)
                    )
        elif mode == "LIVE_CAPABILITY":
            capability_id = str(payload.get("capability_id") or "").strip()
            capability_payload = payload.get("capability_payload")
            if not capability_id:
                raise CognitiveFabricError("LIVE_CAPABILITY_ID_REQUIRED")
            if not isinstance(capability_payload, Mapping):
                raise CognitiveFabricError("LIVE_CAPABILITY_PAYLOAD_NOT_OBJECT")
            depth = int(options.get("__live_capability_depth", 0))
            if depth >= 8:
                raise CognitiveFabricError("LIVE_CAPABILITY_RECURSION_LIMIT")

            def _engine_runner(
                target_mode: str,
                target_payload: Mapping[str, Any],
                target_options: Mapping[str, Any],
            ) -> Mapping[str, Any]:
                nested_options = dict(target_options)
                nested_options["__live_capability_depth"] = depth + 1
                return run(
                    {
                        "mode": target_mode,
                        "payload": dict(target_payload),
                        "options": nested_options,
                    },
                    information_provider=information_provider,
                    proposal_provider=proposal_provider,
                    capability_expander=capability_expander,
                    episode_verification_provider=episode_verification_provider,
                    skill_verification_provider=skill_verification_provider,
                    success_episode_adapter_provider=success_episode_adapter_provider,
                )

            invoker_options = dict(options)
            if proposal_provider is not None:
                invoker_options["proposal_provider"] = proposal_provider
            if capability_expander is not None:
                invoker_options["capability_expander"] = capability_expander
            out = live_invoker.invoke(
                capability_id,
                capability_payload,
                engine_runner=_engine_runner,
                options=invoker_options,
            )
        elif mode == "IMPROVEMENT_CYCLE":
            def _repair_pending(work: Mapping[str, Any]) -> Mapping[str, Any]:
                payload_row = work.get("payload")
                if not isinstance(payload_row, Mapping):
                    raise CognitiveFabricError("R3_REPAIR_WORK_PAYLOAD_INVALID")
                return live_runtime.execute_failure_repair_cycle(
                    {
                        "failure_fingerprint": payload_row.get("failure_fingerprint"),
                        "retry_capsule_sha256": payload_row.get("retry_capsule_sha256"),
                        "components": list(options.get("repair_components") or []),
                        "solver_kwargs": deepcopy(dict(options.get("repair_solver_kwargs") or {})),
                        "learn": True,
                    },
                    repo_root=ROOT,
                    state_path=options.get("state_path"),
                    information_provider=information_provider,
                    proposal_provider=proposal_provider,
                    capability_expander=capability_expander,
                )

            out = improvement_driver.drain(
                state_path=options.get("state_path", self_improvement.DEFAULT_STATE_PATH),
                repo_root=ROOT,
                episode_verification_provider=episode_verification_provider,
                skill_verification_provider=skill_verification_provider,
                success_episode_adapter_provider=success_episode_adapter_provider,
                failure_repair_provider=_repair_pending,
                verification_frontier_acquisition_provider=(
                    verification_frontier_acquisition_provider
                ),
                verification_frontier_acquisition_provider_id=(
                    verification_frontier_acquisition_provider_id
                ),
                distinguishing_evidence_provider=(
                    r3_distinguishing_evidence_provider
                ),
                distinguishing_evidence_provider_id=(
                    r3_distinguishing_evidence_provider_id
                ),
                max_actions=int(options.get("max_improvement_actions", 4)),
            )
        elif mode == "LEARNING_EPISODE":
            out = self_improvement.run_learning_episode(
                payload,
                repo_root=ROOT,
                state_path=options.get("state_path", self_improvement.DEFAULT_STATE_PATH),
                proposal_packets=options.get("proposal_packets"),
                resolved_semantics_bindings=options.get("resolved_semantics_bindings"),
                effect_root=options.get("effect_root"),
                episode_id=str(options.get("episode_id") or "episode"),
                scope_id=str(options.get("scope_id") or "scope"),
                episode_verification_binding=options.get("episode_verification_binding"),
                skill_verification_binding=options.get("skill_verification_binding"),
                episode_verification_provider=episode_verification_provider,
                skill_verification_provider=skill_verification_provider,
                resume_binding=options.get("resume_binding"),
                known_absent_invalidators=options.get("known_absent_invalidators", ()),
                proposal_provider=proposal_provider,
                capability_expander=capability_expander,
                proposal_provider_id=str(options.get("proposal_provider_id") or "HOST_GENERAL_COGNITION_SUBSTRATE"),
                proposal_provider_max_candidates=int(options.get("proposal_provider_max_candidates", 4)),
                capability_expander_id=str(options.get("capability_expander_id") or "HOST_CAPABILITY_EXPANDER"),
                max_capability_expansions=int(options.get("max_capability_expansions", 4)),
            )
        else:
            capability_id = str(payload.get("capability_id") or "").strip()
            inputs = payload.get("inputs")
            if not capability_id:
                raise CognitiveFabricError("CAPABILITY_ID_REQUIRED")
            if not isinstance(inputs, Mapping):
                raise CognitiveFabricError("BOUND_CAPABILITY_INPUTS_NOT_OBJECT")
            out = execute_bound(capability_id, inputs=dict(inputs))

        auto_one_shot = None
        if (
            auto_routed
            and mode == "ADEQUATE_DECISION"
            and isinstance(out, Mapping)
            and out.get("pass") is not True
            and options.get("auto_one_shot_closure", True) is not False
            and not _decision_requires_user_information(out)
        ):
            closure = one_shot_reality_closure.run(
                repo_root=ROOT,
                state_path=options.get("state_path"),
                verification_frontier_acquisition_provider=(
                    verification_frontier_acquisition_provider
                ),
                verification_frontier_acquisition_provider_id=(
                    verification_frontier_acquisition_provider_id
                ),
                failure_repair_provider=one_shot_failure_repair_provider,
                externality_certificate_provider=(
                    one_shot_externality_certificate_provider
                ),
                capability_synthesis_provider=(
                    one_shot_capability_synthesis_provider
                ),
                evidence_acquisition_provider=(
                    one_shot_evidence_acquisition_provider
                ),
                max_repair_rounds=int(options.get("one_shot_max_repair_rounds", 8)),
                v1_max_rounds=int(options.get("one_shot_v1_max_rounds", 64)),
                v1_max_actions_per_round=int(
                    options.get("one_shot_v1_max_actions_per_round", 32)
                ),
            )
            auto_one_shot = _auto_one_shot_summary(closure)
            if (
                closure.get("pass") is True
                and closure.get("status")
                == "PASS__PROOF_CARRYING_REALITY_CLOSURE_FIXED_POINT"
            ):
                replay = _run_adequate_decision_engine(
                    payload,
                    options,
                    information_provider=information_provider,
                    proposal_provider=proposal_provider,
                    capability_expander=capability_expander,
                    episode_verification_provider=episode_verification_provider,
                    skill_verification_provider=skill_verification_provider,
                )
                auto_one_shot["replay_attempted"] = True
                auto_one_shot["replay_pass"] = replay.get("pass") is True
                auto_one_shot["replay_status"] = replay.get("status")
                out = deepcopy(dict(replay))
            else:
                auto_one_shot["replay_attempted"] = False
                auto_one_shot["replay_pass"] = False
            if isinstance(out, Mapping):
                out = deepcopy(dict(out))
                out["_auto_one_shot_closure"] = deepcopy(auto_one_shot)

        direct_learning = None
        direct_learning_error = None
        if (
            mode in R3_DIRECT_EXPERIENCE_MODES
            and isinstance(out, Mapping)
            and options.get("learn", True) is not False
        ):
            try:
                direct_learning = live_runtime.observe_runtime_outcome(
                    _bounded_r3_direct_observation(mode, out),
                    state_path=options.get("state_path"),
                    learn=True,
                    surface="UNIFIED_FABRIC_DIRECT_" + mode,
                    retry_context={
                        "mode": "fabric_direct",
                        "request": {
                            "mode": mode,
                            "payload": deepcopy(dict(payload)),
                            "options": {"learn": False},
                        },
                        "learn": True,
                    },
                )
            except Exception as exc:
                direct_learning_error = type(exc).__name__ + ":" + str(exc)

        autonomous_failure_repair_provider = None
        if capability_expander is not None or bool(options.get("repair_components")):
            def _autonomous_repair_pending(work: Mapping[str, Any]) -> Mapping[str, Any]:
                payload_row = work.get("payload")
                if not isinstance(payload_row, Mapping):
                    raise CognitiveFabricError("R3_REPAIR_WORK_PAYLOAD_INVALID")
                return live_runtime.execute_failure_repair_cycle(
                    {
                        "failure_fingerprint": payload_row.get("failure_fingerprint"),
                        "retry_capsule_sha256": payload_row.get("retry_capsule_sha256"),
                        "components": list(options.get("repair_components") or []),
                        "solver_kwargs": deepcopy(
                            dict(options.get("repair_solver_kwargs") or {})
                        ),
                        "learn": True,
                        "autonomous": True,
                    },
                    repo_root=ROOT,
                    state_path=options.get("state_path"),
                    information_provider=information_provider,
                    proposal_provider=proposal_provider,
                    capability_expander=capability_expander,
                )

            autonomous_failure_repair_provider = _autonomous_repair_pending

        compounding_tick = None
        if mode != "IMPROVEMENT_CYCLE":
            compounding_tick = improvement_driver.drain(
                state_path=options.get(
                    "state_path",
                    self_improvement.DEFAULT_STATE_PATH,
                ),
                repo_root=ROOT,
                episode_verification_provider=episode_verification_provider,
                skill_verification_provider=skill_verification_provider,
                success_episode_adapter_provider=success_episode_adapter_provider,
                failure_repair_provider=autonomous_failure_repair_provider,
                verification_frontier_acquisition_provider=(
                    verification_frontier_acquisition_provider
                ),
                verification_frontier_acquisition_provider_id=(
                    verification_frontier_acquisition_provider_id
                ),
                distinguishing_evidence_provider=(
                    r3_distinguishing_evidence_provider
                ),
                distinguishing_evidence_provider_id=(
                    r3_distinguishing_evidence_provider_id
                ),
                max_actions=int(options.get("self_improvement_max_actions", 4)),
            )

        episode_compounding_tick = (
            {
                "status": "MERGED_INTO_UNIFIED_COMPOUNDING_TICK",
                "pass": True,
                "terminal_authority": False,
            }
            if compounding_tick is not None
            else None
        )

        return {
            "schema": SCHEMA,
            "status": "FABRIC_DISPATCH_COMPLETE",
            "mode": mode,
            "requested_mode": requested_mode or "AUTO",
            "auto_routed": auto_routed,
            "engine": ENGINE_DESCRIPTORS[mode],
            "inner_pass": bool(isinstance(out, Mapping) and out.get("pass") is True),
            "inner_status": out.get("status") if isinstance(out, Mapping) else None,
            "result": deepcopy(dict(out)) if isinstance(out, Mapping) else out,
            "direct_learning": deepcopy(direct_learning),
            "direct_learning_error": direct_learning_error,
            "direct_experience_observed": (
                direct_learning is not None and direct_learning_error is None
            ),
            "compounding_tick": deepcopy(compounding_tick),
            "episode_compounding_tick": deepcopy(episode_compounding_tick),
            "auto_one_shot_closure": deepcopy(auto_one_shot),
            "single_front_door": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
