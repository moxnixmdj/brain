"""Unified Cognitive Fabric V1.

One typed live front door over the Brain's current verified execution,
adequate-decision, adaptive-solving, P3, and self-improvement systems.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import live_integrated_brain_v1 as live_brain
from canonical.runtime import general_adequate_decision_controller_v1 as adequate_decision
from canonical.runtime import p3_real_context_v3_admission_v12 as p3
from canonical.runtime import universal_verified_adaptive_solver_v12 as adaptive_solver
from canonical.runtime import autonomous_verified_self_improvement_v1 as self_improvement
from canonical.runtime.verified_bound_capability_execution_adapter_v1 import execute as execute_bound

SCHEMA = "PROJECT_BRAIN_UNIFIED_COGNITIVE_FABRIC_V1"
ROOT = Path(__file__).resolve().parents[2]

ENGINE_DESCRIPTORS = {
    "RAW_GOAL": "live_integrated_brain_v1.run_raw_goal",
    "COMPILED_TASK": "live_integrated_brain_v1.run",
    "ADEQUATE_DECISION": "general_adequate_decision_controller_v1.run",
    "P3": "p3_real_context_v3_admission_v12.evaluate",
    "ADAPTIVE_SOLVER": "universal_verified_adaptive_solver_v12.run",
    "LEARNING_EPISODE": "autonomous_verified_self_improvement_v1.run_learning_episode",
    "BOUND_CAPABILITY": "verified_bound_capability_execution_adapter_v1.execute",
}

KNOWN_RESIDUALS = (
    "H100_SPECIALIZED_INFERENCE_REGISTRIES_NOT_YET_EXPOSED_AS_FABRIC_CAPABILITIES",
    "MYSTERYMECHANISM_SPECIALIZED_INFERENCE_KERNELS_NOT_YET_EXPOSED_AS_FABRIC_CAPABILITIES",
    "VERIFIED_SKILL_MACRO_PLANNER_NOT_YET_FIRST_CLASS_LIVE_FABRIC_ROUTE",
    "CAPABILITY_FIRST_SCHEDULER_NOT_YET_MANDATORY_FOR_EVERY_FABRIC_CALL",
)


class CognitiveFabricError(ValueError):
    pass


def catalog() -> dict[str, Any]:
    bound = live_brain.load_verified_registry()
    return {
        "schema": SCHEMA,
        "status": "LIVE_FEDERATED_COGNITIVE_FABRIC",
        "engine_count": len(ENGINE_DESCRIPTORS),
        "engines": dict(ENGINE_DESCRIPTORS),
        "verified_bound_capability_count": len(bound),
        "verified_bound_capability_ids": sorted(bound),
        "known_unified_fabric_residuals": list(KNOWN_RESIDUALS),
        "single_front_door": True,
        "all_historical_brain_capabilities_unified": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def run(
    request: Mapping[str, Any],
    *,
    information_provider: Callable[[Mapping[str, Any], int], Mapping[str, Any] | None] | None = None,
    proposal_provider: Callable[..., Mapping[str, Any] | None] | None = None,
    capability_expander: Callable[..., Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(request, Mapping):
            raise CognitiveFabricError("REQUEST_NOT_OBJECT")
        mode = str(request.get("mode") or "").strip().upper()
        if mode == "CATALOG":
            return catalog()
        if mode not in ENGINE_DESCRIPTORS:
            raise CognitiveFabricError("MODE_INVALID:" + mode)
        payload = request.get("payload")
        if not isinstance(payload, Mapping):
            raise CognitiveFabricError("PAYLOAD_NOT_OBJECT")
        options = request.get("options") or {}
        if not isinstance(options, Mapping):
            raise CognitiveFabricError("OPTIONS_NOT_OBJECT")

        if mode == "RAW_GOAL":
            out = live_brain.run_raw_goal(payload)
        elif mode == "COMPILED_TASK":
            out = live_brain.run(payload)
        elif mode == "ADEQUATE_DECISION":
            out = adequate_decision.run(
                payload,
                repo_root=ROOT,
                information_provider=information_provider,
                proposal_provider=proposal_provider,
                capability_expander=capability_expander,
            )
        elif mode == "P3":
            out = p3.evaluate(payload, repo_root=ROOT)
        elif mode == "ADAPTIVE_SOLVER":
            out = adaptive_solver.run(
                payload,
                repo_root=ROOT,
                proposal_provider=proposal_provider,
                capability_expander=capability_expander,
                proposal_provider_id=str(options.get("proposal_provider_id") or "HOST_GENERAL_COGNITION_SUBSTRATE"),
                proposal_provider_max_candidates=int(options.get("proposal_provider_max_candidates", 4)),
                capability_expander_id=str(options.get("capability_expander_id") or "HOST_CAPABILITY_EXPANDER"),
                max_capability_expansions=int(options.get("max_capability_expansions", 4)),
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
                resume_binding=options.get("resume_binding"),
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

        return {
            "schema": SCHEMA,
            "status": "FABRIC_DISPATCH_COMPLETE",
            "mode": mode,
            "engine": ENGINE_DESCRIPTORS[mode],
            "inner_pass": bool(isinstance(out, Mapping) and out.get("pass") is True),
            "inner_status": out.get("status") if isinstance(out, Mapping) else None,
            "result": deepcopy(dict(out)) if isinstance(out, Mapping) else out,
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
