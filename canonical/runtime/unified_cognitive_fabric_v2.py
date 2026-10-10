"""Unified Cognitive Fabric V2.

V2 preserves every V1 route and adds one narrow live surface:
OPEN_WORLD_SEMANTIC_CONTROL. The new route can select only the next
information-acquisition control action. It cannot select semantic identity or a
final domain action.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import unified_cognitive_fabric_v1 as v1
from canonical.runtime import open_world_semantic_control_v1 as open_world_control

SCHEMA = "PROJECT_BRAIN_UNIFIED_COGNITIVE_FABRIC_V2"
ROOT = Path(__file__).resolve().parents[2]
CANONICAL_PUBLIC_ENTRYPOINT = "canonical.runtime.unified_cognitive_fabric_v2.run"
OPEN_WORLD_MODE = "OPEN_WORLD_SEMANTIC_CONTROL"
_REQUIRED_OPEN_WORLD_KEYS = frozenset({
    "environment_id",
    "goal_id",
    "semantic_state",
    "decision_relevant",
    "information_origin",
})


def _is_open_world_control_payload(payload: Mapping[str, Any]) -> bool:
    return _REQUIRED_OPEN_WORLD_KEYS.issubset(set(payload))


def catalog() -> dict[str, Any]:
    out = deepcopy(dict(v1.catalog()))
    out["fabric_schema"] = SCHEMA
    out["canonical_public_entrypoint"] = CANONICAL_PUBLIC_ENTRYPOINT
    engines = deepcopy(dict(out.get("engines") or {}))
    engines[OPEN_WORLD_MODE] = "open_world_semantic_control_v1.resolve"
    out["engines"] = engines
    return out


def run(request: Mapping[str, Any], **providers: Any) -> dict[str, Any]:
    try:
        if not isinstance(request, Mapping):
            raise ValueError("REQUEST_NOT_OBJECT")
        requested = str(request.get("mode") or "").strip().upper()
        if requested == "CATALOG":
            return catalog()

        payload = request.get("payload")
        if not isinstance(payload, Mapping):
            return v1.run(request, **providers)
        options = request.get("options") or {}
        if not isinstance(options, Mapping):
            raise ValueError("OPTIONS_NOT_OBJECT")

        auto = requested in {"", "AUTO"}
        is_new_surface = (
            requested == OPEN_WORLD_MODE
            or (auto and _is_open_world_control_payload(payload))
        )
        if not is_new_surface:
            return v1.run(request, **providers)

        out = open_world_control.resolve(payload, repo_root=ROOT)
        direct_learning = None
        direct_learning_error = None
        if options.get("learn", True) is not False:
            try:
                observation = v1._bounded_r3_direct_observation(OPEN_WORLD_MODE, out)
                direct_learning = v1.live_runtime.observe_runtime_outcome(
                    observation,
                    state_path=options.get("state_path"),
                    learn=True,
                    surface="UNIFIED_FABRIC_DIRECT_" + OPEN_WORLD_MODE,
                    retry_context={
                        "mode": "fabric_direct",
                        "request": {
                            "mode": OPEN_WORLD_MODE,
                            "payload": deepcopy(dict(payload)),
                            "options": {"learn": False},
                        },
                        "learn": True,
                    },
                )
            except Exception as exc:
                direct_learning_error = type(exc).__name__ + ":" + str(exc)

        return {
            "schema": SCHEMA,
            "status": "FABRIC_DISPATCH_COMPLETE",
            "mode": OPEN_WORLD_MODE,
            "requested_mode": requested or "AUTO",
            "auto_routed": auto,
            "engine": "open_world_semantic_control_v1.resolve",
            "inner_pass": out.get("pass") is True,
            "inner_status": out.get("status"),
            "result": deepcopy(dict(out)),
            "direct_learning": deepcopy(direct_learning),
            "direct_learning_error": direct_learning_error,
            "direct_experience_observed": (
                direct_learning is not None and direct_learning_error is None
            ),
            "single_front_door": True,
            "semantic_truth_authority": False,
            "final_domain_action_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "semantic_truth_authority": False,
            "final_domain_action_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
