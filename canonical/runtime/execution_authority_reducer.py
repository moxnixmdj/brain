"""Deterministic execution-authority reducer over immutable task receipts.

No writable boolean is authoritative. CAN_EXECUTE and CAN_VERIFY are pure
functions of a validated hash-chained event history.

V3 hardening:
- authorization includes every current irreversible Stage-C prerequisite;
- execution/verifier consumption must be authorized at the exact transition;
- exact carrier identity is bound into state;
- explicit task taint is irreversible;
- semantic builder success and frozen output are required before verification.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

SCHEMA = "BRAIN_AUTHORITY_EVENT_V1"
EVENT_TYPES = {
    "STAGE_A_PASS",
    "STAGE_B_PASS",
    "SOURCE_BOUNDARY_PASS",
    "SOURCE_BOUNDARY_FAIL",
    "EXECUTION_SURFACE_PASS",
    "EXECUTION_SURFACE_FAIL",
    "ACCEPTANCE_FROZEN",
    "ACCEPTANCE_INVALIDATED",
    "MINIMUM_REALITY_CUT_PASS",
    "MINIMUM_REALITY_CUT_FAIL",
    "RUNTIME_API_PREFLIGHT_PASS",
    "RUNTIME_API_PREFLIGHT_FAIL",
    "LEASE_ISSUED",
    "LEASE_REVOKED",
    "CARRIER_OPEN",
    "CARRIER_CLOSED",
    "EXECUTION_CONSUMED",
    "BUILDER_SEMANTIC_SUCCESS",
    "BUILDER_SEMANTIC_FAILURE",
    "OUTPUT_FROZEN",
    "OUTPUT_INVALIDATED",
    "VERIFIER_CONSUMED",
    "TASK_TAINTED",
}
PASS_OR_GRANT_EVENTS = {
    "STAGE_A_PASS",
    "STAGE_B_PASS",
    "SOURCE_BOUNDARY_PASS",
    "EXECUTION_SURFACE_PASS",
    "ACCEPTANCE_FROZEN",
    "MINIMUM_REALITY_CUT_PASS",
    "RUNTIME_API_PREFLIGHT_PASS",
    "LEASE_ISSUED",
    "CARRIER_OPEN",
    "BUILDER_SEMANTIC_SUCCESS",
    "OUTPUT_FROZEN",
}
REVOCATION_EVENTS = {
    "SOURCE_BOUNDARY_FAIL",
    "EXECUTION_SURFACE_FAIL",
    "ACCEPTANCE_INVALIDATED",
    "MINIMUM_REALITY_CUT_FAIL",
    "RUNTIME_API_PREFLIGHT_FAIL",
    "LEASE_REVOKED",
    "CARRIER_CLOSED",
    "BUILDER_SEMANTIC_FAILURE",
    "OUTPUT_INVALIDATED",
    "TASK_TAINTED",
}


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_event_hash(event: Mapping[str, Any]) -> str:
    clean = dict(event)
    clean.pop("event_sha256", None)
    return hashlib.sha256(_canonical_json(clean)).hexdigest()


def carrier_binding_hash(evidence: Any) -> str:
    return hashlib.sha256(_canonical_json(evidence)).hexdigest()


def _new_state() -> dict[str, Any]:
    return {
        "stage_a_pass": False,
        "stage_b_pass": False,
        "source_boundary_pass": False,
        "execution_surface_pass": False,
        "acceptance_frozen": False,
        "minimum_reality_cut_pass": False,
        "runtime_api_preflight_pass": False,
        "lease_active": False,
        "carrier_open": False,
        "active_carrier_binding_sha256": None,
        "active_carrier_event_id": None,
        "last_carrier_binding_sha256": None,
        "execution_used": 0,
        "builder_semantic_success": False,
        "output_frozen": False,
        "verifier_used": 0,
        "tainted": False,
        "latest_revocation_seq": -1,
        "latest_grant_seq": -1,
    }


def _budget_valid(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _base_execution_prereqs(state: Mapping[str, Any]) -> bool:
    no_newer_revocation = state["latest_revocation_seq"] < state["latest_grant_seq"]
    carrier_bound = (
        state["carrier_open"]
        and isinstance(state["active_carrier_binding_sha256"], str)
        and bool(state["active_carrier_binding_sha256"])
    )
    return bool(
        state["stage_a_pass"]
        and state["stage_b_pass"]
        and state["source_boundary_pass"]
        and state["execution_surface_pass"]
        and state["acceptance_frozen"]
        and state["minimum_reality_cut_pass"]
        and state["runtime_api_preflight_pass"]
        and state["lease_active"]
        and carrier_bound
        and not state["tainted"]
        and no_newer_revocation
    )


def _can_execute_now(state: Mapping[str, Any], execution_budget: Any) -> bool:
    return (
        _base_execution_prereqs(state)
        and _budget_valid(execution_budget)
        and state["execution_used"] < execution_budget
    )


def _can_verify_now(state: Mapping[str, Any], verifier_budget: Any) -> bool:
    return (
        _base_execution_prereqs(state)
        and state["execution_used"] > 0
        and state["builder_semantic_success"]
        and state["output_frozen"]
        and _budget_valid(verifier_budget)
        and state["verifier_used"] < verifier_budget
    )


def validate_event_chain(events: Iterable[Mapping[str, Any]], task: str) -> list[str]:
    errors: list[str] = []
    ordered = list(events)
    last_seq = -1
    prev_hash = None
    seen_ids: set[str] = set()
    carrier_open = False

    for i, e in enumerate(ordered):
        if e.get("schema") != SCHEMA:
            errors.append(f"EVENT_SCHEMA_INVALID:{i}")
        if e.get("task") != task:
            errors.append(f"EVENT_TASK_MISMATCH:{i}")
        et = e.get("type")
        if et not in EVENT_TYPES:
            errors.append(f"EVENT_TYPE_INVALID:{i}:{et}")
        eid = e.get("event_id")
        if not isinstance(eid, str) or not eid:
            errors.append(f"EVENT_ID_MISSING:{i}")
        elif eid in seen_ids:
            errors.append(f"EVENT_ID_DUPLICATE:{eid}")
        else:
            seen_ids.add(eid)

        seq = e.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool) or seq < 0:
            errors.append(f"EVENT_SEQ_INVALID:{i}")
        elif seq <= last_seq:
            errors.append(f"EVENT_SEQ_NOT_STRICTLY_INCREASING:{i}")
        else:
            last_seq = seq

        expected_prev = e.get("prev_event_sha256")
        if i == 0:
            if expected_prev not in (None, ""):
                errors.append("FIRST_EVENT_PREV_HASH_NOT_EMPTY")
        elif expected_prev != prev_hash:
            errors.append(f"EVENT_CHAIN_BROKEN:{i}")

        actual_hash = canonical_event_hash(e)
        declared = e.get("event_sha256")
        if declared is not None and declared != actual_hash:
            errors.append(f"EVENT_HASH_MISMATCH:{i}")
        prev_hash = actual_hash

        if et in PASS_OR_GRANT_EVENTS and e.get("evidence") in (None, "", {}):
            errors.append(f"GRANT_EVIDENCE_MISSING:{i}:{et}")

        if et == "CARRIER_OPEN":
            if carrier_open:
                errors.append(f"SECOND_CARRIER_OPEN_WITHOUT_CLOSE:{i}")
            carrier_open = True
        elif et == "CARRIER_CLOSED":
            if not carrier_open:
                errors.append(f"CARRIER_CLOSED_WITHOUT_OPEN:{i}")
            carrier_open = False
        elif et in {
            "EXECUTION_CONSUMED",
            "BUILDER_SEMANTIC_SUCCESS",
            "BUILDER_SEMANTIC_FAILURE",
            "OUTPUT_FROZEN",
            "OUTPUT_INVALIDATED",
            "VERIFIER_CONSUMED",
        } and not carrier_open:
            errors.append(f"{et}_WITHOUT_OPEN_CARRIER:{i}")

    return sorted(set(errors))


def derive_authority(
    events: Iterable[Mapping[str, Any]],
    *,
    task: str,
    execution_budget: int,
    verifier_budget: int,
) -> dict[str, Any]:
    ordered = list(events)
    errors = validate_event_chain(ordered, task)
    if not _budget_valid(execution_budget):
        errors.append("EXECUTION_BUDGET_INVALID")
    if not _budget_valid(verifier_budget):
        errors.append("VERIFIER_BUDGET_INVALID")
    if errors:
        return {
            "task": task,
            "valid": False,
            "errors": sorted(set(errors)),
            "can_execute": False,
            "can_verify": False,
        }

    state = _new_state()
    transition_errors: list[str] = []

    for i, e in enumerate(ordered):
        et = e["type"]
        seq = e["seq"]

        if et == "STAGE_A_PASS":
            state["stage_a_pass"] = True
        elif et == "STAGE_B_PASS":
            if not state["stage_a_pass"]:
                transition_errors.append(f"STAGE_B_PASS_BEFORE_STAGE_A:{i}")
            state["stage_b_pass"] = True
        elif et == "SOURCE_BOUNDARY_PASS":
            if not state["stage_b_pass"]:
                transition_errors.append(f"SOURCE_BOUNDARY_PASS_BEFORE_STAGE_B:{i}")
            state["source_boundary_pass"] = True
        elif et == "SOURCE_BOUNDARY_FAIL":
            state["source_boundary_pass"] = False
            state["lease_active"] = False
        elif et == "EXECUTION_SURFACE_PASS":
            if not state["stage_a_pass"]:
                transition_errors.append(f"EXECUTION_SURFACE_PASS_BEFORE_STAGE_A:{i}")
            state["execution_surface_pass"] = True
        elif et == "EXECUTION_SURFACE_FAIL":
            state["execution_surface_pass"] = False
            state["lease_active"] = False
        elif et == "ACCEPTANCE_FROZEN":
            if not state["stage_b_pass"]:
                transition_errors.append(f"ACCEPTANCE_FROZEN_BEFORE_STAGE_B:{i}")
            state["acceptance_frozen"] = True
        elif et == "ACCEPTANCE_INVALIDATED":
            state["acceptance_frozen"] = False
            state["lease_active"] = False
        elif et == "MINIMUM_REALITY_CUT_PASS":
            state["minimum_reality_cut_pass"] = True
        elif et == "MINIMUM_REALITY_CUT_FAIL":
            state["minimum_reality_cut_pass"] = False
            state["lease_active"] = False
        elif et == "RUNTIME_API_PREFLIGHT_PASS":
            if not state["stage_b_pass"]:
                transition_errors.append(f"RUNTIME_API_PREFLIGHT_PASS_BEFORE_STAGE_B:{i}")
            state["runtime_api_preflight_pass"] = True
        elif et == "RUNTIME_API_PREFLIGHT_FAIL":
            state["runtime_api_preflight_pass"] = False
            state["lease_active"] = False
        elif et == "LEASE_ISSUED":
            lease_prereqs = (
                state["stage_a_pass"]
                and state["stage_b_pass"]
                and state["source_boundary_pass"]
                and state["execution_surface_pass"]
                and state["acceptance_frozen"]
                and state["minimum_reality_cut_pass"]
                and state["runtime_api_preflight_pass"]
                and not state["tainted"]
            )
            if not lease_prereqs:
                transition_errors.append(f"LEASE_ISSUED_BEFORE_ALL_PREREQS:{i}")
            state["lease_active"] = True
        elif et == "LEASE_REVOKED":
            state["lease_active"] = False
        elif et == "CARRIER_OPEN":
            if not state["lease_active"] or state["tainted"]:
                transition_errors.append(f"CARRIER_OPEN_WITHOUT_LIVE_LEASE:{i}")
            binding = carrier_binding_hash(e.get("evidence"))
            state["carrier_open"] = True
            state["active_carrier_binding_sha256"] = binding
            state["active_carrier_event_id"] = e.get("event_id")
            state["last_carrier_binding_sha256"] = binding
        elif et == "CARRIER_CLOSED":
            state["carrier_open"] = False
            state["active_carrier_binding_sha256"] = None
            state["active_carrier_event_id"] = None
        elif et == "EXECUTION_CONSUMED":
            if not _can_execute_now(state, execution_budget):
                transition_errors.append(f"EXECUTION_CONSUMED_WITHOUT_DERIVED_AUTHORITY:{i}")
            else:
                state["execution_used"] += 1
                state["builder_semantic_success"] = False
                state["output_frozen"] = False
        elif et == "BUILDER_SEMANTIC_SUCCESS":
            if state["execution_used"] <= 0:
                transition_errors.append(f"BUILDER_SUCCESS_WITHOUT_EXECUTION:{i}")
            state["builder_semantic_success"] = True
        elif et == "BUILDER_SEMANTIC_FAILURE":
            state["builder_semantic_success"] = False
            state["output_frozen"] = False
            state["lease_active"] = False
        elif et == "OUTPUT_FROZEN":
            if state["execution_used"] <= 0 or not state["builder_semantic_success"]:
                transition_errors.append(f"OUTPUT_FROZEN_BEFORE_SEMANTIC_SUCCESS:{i}")
            state["output_frozen"] = True
        elif et == "OUTPUT_INVALIDATED":
            state["output_frozen"] = False
            state["lease_active"] = False
        elif et == "VERIFIER_CONSUMED":
            if not _can_verify_now(state, verifier_budget):
                transition_errors.append(f"VERIFIER_CONSUMED_WITHOUT_DERIVED_AUTHORITY:{i}")
            else:
                state["verifier_used"] += 1
        elif et == "TASK_TAINTED":
            state["tainted"] = True
            state["source_boundary_pass"] = False
            state["lease_active"] = False
            state["output_frozen"] = False

        if et in PASS_OR_GRANT_EVENTS:
            state["latest_grant_seq"] = max(state["latest_grant_seq"], seq)
        if et in REVOCATION_EVENTS:
            state["latest_revocation_seq"] = max(state["latest_revocation_seq"], seq)

    if transition_errors:
        return {
            "task": task,
            "valid": False,
            "errors": sorted(set(transition_errors)),
            "state": state,
            "can_execute": False,
            "can_verify": False,
        }

    can_execute = _can_execute_now(state, execution_budget)
    can_verify = _can_verify_now(state, verifier_budget)

    digest_payload = {
        "task": task,
        "state": state,
        "execution_budget": execution_budget,
        "verifier_budget": verifier_budget,
        "can_execute": can_execute,
        "can_verify": can_verify,
    }
    digest = hashlib.sha256(_canonical_json(digest_payload)).hexdigest()

    return {
        "task": task,
        "valid": True,
        "errors": [],
        "state": state,
        "execution_budget": execution_budget,
        "verifier_budget": verifier_budget,
        "can_execute": can_execute,
        "can_verify": can_verify,
        "active_carrier_binding_sha256": state["active_carrier_binding_sha256"],
        "state_sha256": digest,
    }
