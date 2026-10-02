"""Irreversible information-capability firewall for clean evaluation lanes.

The firewall converts post-exposure cleanliness from a behavioral instruction
into a machine-checkable capability state. Once task identity is exposed, broad
discovery capabilities cannot be restored inside the same clean lane.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_EVALUATION_INFORMATION_FIREWALL_V1"

DISCOVERY = {
    "WEB_DISCOVERY",
    "REPO_SEARCH",
    "BROAD_FILESYSTEM_SEARCH",
    "BENCHMARK_HISTORY_LOOKUP",
    "TASK_SPECIFIC_EXTERNAL_SEARCH",
}
POST_EXPOSURE_ALLOWED = {
    "EXACT_FROZEN_BLOB_READ",
    "DECLARED_TOOL",
    "TASK_RUNTIME_IO",
    "WRITE_CANDIDATE_ARTIFACT",
    "TERMINAL_VERIFIER_EXECUTION",
}
ALL_CAPABILITIES = DISCOVERY | POST_EXPOSURE_ALLOWED


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "request_allowed": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def compile_state(state: Mapping[str, Any]) -> dict[str, Any]:
    identity_exposed = state.get("task_identity_exposed")
    clean = state.get("clean_qualification_active")
    if not isinstance(identity_exposed, bool):
        return _fail("TASK_IDENTITY_EXPOSED_INVALID")
    if not isinstance(clean, bool):
        return _fail("CLEAN_QUALIFICATION_ACTIVE_INVALID")

    prior_revoked = state.get("revoked_capabilities", [])
    if not isinstance(prior_revoked, list) or any(x not in ALL_CAPABILITIES for x in prior_revoked):
        return _fail("REVOKED_CAPABILITIES_INVALID")
    revoked = set(prior_revoked)
    if identity_exposed and clean:
        revoked |= DISCOVERY

    allowed = ALL_CAPABILITIES - revoked
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "pass": True,
        "errors": [],
        "task_identity_exposed": identity_exposed,
        "clean_qualification_active": clean,
        "revoked_capabilities": sorted(revoked),
        "allowed_capabilities": sorted(allowed),
        "irreversible_revocation_active": bool(identity_exposed and clean),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def transition(previous: Mapping[str, Any], requested: Mapping[str, Any]) -> dict[str, Any]:
    prev = compile_state(previous)
    nxt = compile_state(requested)
    if not prev.get("pass") or not nxt.get("pass"):
        return _fail("STATE_INVALID")
    if prev["task_identity_exposed"] and not nxt["task_identity_exposed"]:
        return _fail("IDENTITY_EXPOSURE_CANNOT_BE_REVERSED")
    if prev["clean_qualification_active"] and not nxt["clean_qualification_active"]:
        if requested.get("lane_id") == previous.get("lane_id"):
            return _fail("CLEAN_LANE_CANNOT_REENABLE_DISCOVERY_BY_DEACTIVATION")
    if not set(prev["revoked_capabilities"]).issubset(set(nxt["revoked_capabilities"])):
        return _fail("REVOKED_CAPABILITY_RESTORED")
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "pass": True,
        "errors": [],
        "transition_allowed": True,
        "state": nxt,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def evaluate(state: Mapping[str, Any], requested_capability: str) -> dict[str, Any]:
    compiled = compile_state(state)
    if not compiled.get("pass"):
        return compiled
    if requested_capability not in ALL_CAPABILITIES:
        return _fail("UNKNOWN_CAPABILITY")
    allowed = requested_capability in compiled["allowed_capabilities"]
    return {
        "schema": SCHEMA,
        "status": "ALLOWED" if allowed else "DENIED_FAIL_CLOSED",
        "pass": True,
        "errors": [],
        "request_allowed": allowed,
        "requested_capability": requested_capability,
        "revoked_capabilities": compiled["revoked_capabilities"],
        "rule": "POST_IDENTITY_CLEAN_LANE_DISCOVERY_CAPABILITIES_ARE_IRREVOCABLY_REVOKED",
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
