"""Residual semantic control-invariance candidate builder V1.

This module does not resolve an unknown word sense. It proves a narrower control
fact: when semantics remain open-world and decision-relevant information is
missing, the Brain's next information-acquisition action can be chosen without
consulting the unknown semantic identity.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Mapping

from canonical.runtime.minimum_information_origin_policy_v1 import route as route_origin

SCHEMA = "PROJECT_BRAIN_RESIDUAL_SEMANTIC_CONTROL_INVARIANCE_CANDIDATE_V1"
CONTROL_SCOPE = "NEXT_INFORMATION_ACQUISITION_CONTROL_ONLY"
SEMANTIC_STATE = "UNRESOLVED_OPEN_WORLD"
ALLOWED_ACTIONS = frozenset({
    "ASK_USER_MINIMUM_CLARIFICATION",
    "ASK_USER_SOURCE_OR_SCOPE",
    "OBSERVE_BOUND_SOURCE_ONLY",
    "RESEARCH_MINIMUM_AUTHENTICATED_FACT",
})
FORBIDDEN_KEYS = frozenset({
    "sense_id",
    "synset_id",
    "concept_id",
    "hypothesis_id",
    "semantic_identity",
    "residual_world",
    "intended_sense",
})


class ResidualControlInvariantError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return "sha256:" + sha256(_canon(value)).hexdigest()


def _forbidden_paths(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            name = str(key)
            path = prefix + "." + name if prefix else name
            if name in FORBIDDEN_KEYS:
                found.append(path)
            found.extend(_forbidden_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_paths(child, f"{prefix}[{index}]"))
    return found


def build_candidate(
    *,
    environment_id: str,
    goal_id: str,
    semantic_state: str,
    decision_relevant: bool,
    information_origin: Mapping[str, Any],
) -> dict[str, Any]:
    environment_id = str(environment_id or "").strip()
    goal_id = str(goal_id or "").strip()
    if not environment_id:
        raise ResidualControlInvariantError("ENVIRONMENT_ID_REQUIRED")
    if not goal_id:
        raise ResidualControlInvariantError("GOAL_ID_REQUIRED")
    if semantic_state != SEMANTIC_STATE:
        raise ResidualControlInvariantError("SEMANTIC_STATE_NOT_OPEN_WORLD_UNRESOLVED")
    if decision_relevant is not True:
        raise ResidualControlInvariantError("DECISION_RELEVANT_TRUE_REQUIRED")
    if not isinstance(information_origin, Mapping):
        raise ResidualControlInvariantError("INFORMATION_ORIGIN_MAPPING_REQUIRED")

    origin = deepcopy(dict(information_origin))
    forbidden = _forbidden_paths(origin)
    if forbidden:
        raise ResidualControlInvariantError(
            "SEMANTIC_IDENTITY_MUST_NOT_CONTROL_ORIGIN_ROUTE:" + ",".join(sorted(forbidden))
        )

    origin["decision_relevant"] = True
    if origin.get("context_value_bound") is True:
        raise ResidualControlInvariantError(
            "BOUND_CONTEXT_IS_NOT_RESIDUAL_UNRESOLVED_CONTROL"
        )
    origin.setdefault("context_value_bound", False)

    routed = route_origin(origin)
    if not isinstance(routed, Mapping) or routed.get("pass") is not True:
        reason = routed.get("reason") if isinstance(routed, Mapping) else "NOT_OBJECT"
        raise ResidualControlInvariantError(
            "MINIMUM_INFORMATION_ORIGIN_ROUTE_FAILED:" + str(reason)
        )
    action = str(routed.get("action") or "").strip()
    if action not in ALLOWED_ACTIONS:
        raise ResidualControlInvariantError(
            "ROUTED_ACTION_NOT_INFORMATION_ACQUISITION:" + action
        )

    material = {
        "environment_id": environment_id,
        "goal_id": goal_id,
        "semantic_state": semantic_state,
        "decision_relevant": True,
        "information_origin": origin,
        "action": action,
        "control_scope": CONTROL_SCOPE,
    }
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE__RESIDUAL_SEMANTIC_CONTROL_ACTION_INVARIANT",
        "pass": True,
        **material,
        "information_origin_sha256": _sha(origin),
        "candidate_sha256": _sha(material),
        "origin_policy_result": deepcopy(dict(routed)),
        "semantic_identity_consulted": False,
        "open_world_semantics_closed": False,
        "intended_sense_identified": False,
        "semantic_truth_authority": False,
        "final_domain_action_authority": False,
        "control_action_authority": False,
        "independent_verification_required": True,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
