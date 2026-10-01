"""Deterministic execution-authority reducer over immutable task receipts.

No writable boolean is authoritative. CAN_EXECUTE and CAN_VERIFY are pure
functions of validated events. Revocation dominates older grants.

V2 hardening: authority binds the exact active carrier identity. A second
CARRIER_OPEN while one carrier is already open invalidates the event chain.
This prevents two different PRs from sharing an otherwise identical boolean
authority state.
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
    "LEASE_ISSUED",
    "LEASE_REVOKED",
    "CARRIER_OPEN",
    "CARRIER_CLOSED",
    "EXECUTION_CONSUMED",
    "VERIFIER_CONSUMED",
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
    """Bind authorization to the exact carrier evidence, not carrier_open=True."""
    return hashlib.sha256(_canonical_json(evidence)).hexdigest()


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

        if et == "CARRIER_OPEN":
            if e.get("evidence") in (None, "", {}):
                errors.append(f"CARRIER_BINDING_MISSING:{i}")
            if carrier_open:
                errors.append(f"SECOND_CARRIER_OPEN_WITHOUT_CLOSE:{i}")
            carrier_open = True
        elif et == "CARRIER_CLOSED":
            if not carrier_open:
                errors.append(f"CARRIER_CLOSED_WITHOUT_OPEN:{i}")
            carrier_open = False
        elif et in {"EXECUTION_CONSUMED", "VERIFIER_CONSUMED"} and not carrier_open:
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
    if errors:
        return {
            "task": task,
            "valid": False,
            "errors": errors,
            "can_execute": False,
            "can_verify": False,
        }

    state = {
        "stage_a_pass": False,
        "stage_b_pass": False,
        "source_boundary_pass": False,
        "execution_surface_pass": False,
        "lease_active": False,
        "carrier_open": False,
        "active_carrier_binding_sha256": None,
        "active_carrier_event_id": None,
        "last_carrier_binding_sha256": None,
        "execution_used": 0,
        "verifier_used": 0,
        "latest_revocation_seq": -1,
        "latest_grant_seq": -1,
    }

    for e in ordered:
        et = e["type"]
        seq = e["seq"]
        if et == "STAGE_A_PASS":
            state["stage_a_pass"] = True
        elif et == "STAGE_B_PASS":
            state["stage_b_pass"] = True
        elif et == "SOURCE_BOUNDARY_PASS":
            state["source_boundary_pass"] = True
            state["latest_grant_seq"] = max(state["latest_grant_seq"], seq)
        elif et == "SOURCE_BOUNDARY_FAIL":
            state["source_boundary_pass"] = False
            state["lease_active"] = False
            state["latest_revocation_seq"] = max(state["latest_revocation_seq"], seq)
        elif et == "EXECUTION_SURFACE_PASS":
            state["execution_surface_pass"] = True
            state["latest_grant_seq"] = max(state["latest_grant_seq"], seq)
        elif et == "EXECUTION_SURFACE_FAIL":
            state["execution_surface_pass"] = False
            state["lease_active"] = False
            state["latest_revocation_seq"] = max(state["latest_revocation_seq"], seq)
        elif et == "LEASE_ISSUED":
            state["lease_active"] = True
            state["latest_grant_seq"] = max(state["latest_grant_seq"], seq)
        elif et == "LEASE_REVOKED":
            state["lease_active"] = False
            state["latest_revocation_seq"] = max(state["latest_revocation_seq"], seq)
        elif et == "CARRIER_OPEN":
            binding = carrier_binding_hash(e.get("evidence"))
            state["carrier_open"] = True
            state["active_carrier_binding_sha256"] = binding
            state["active_carrier_event_id"] = e.get("event_id")
            state["last_carrier_binding_sha256"] = binding
            state["latest_grant_seq"] = max(state["latest_grant_seq"], seq)
        elif et == "CARRIER_CLOSED":
            state["carrier_open"] = False
            state["active_carrier_binding_sha256"] = None
            state["active_carrier_event_id"] = None
            state["latest_revocation_seq"] = max(state["latest_revocation_seq"], seq)
        elif et == "EXECUTION_CONSUMED":
            state["execution_used"] += 1
        elif et == "VERIFIER_CONSUMED":
            state["verifier_used"] += 1

    no_newer_revocation = state["latest_revocation_seq"] < state["latest_grant_seq"]
    carrier_bound = (
        state["carrier_open"]
        and isinstance(state["active_carrier_binding_sha256"], str)
        and bool(state["active_carrier_binding_sha256"])
    )
    prereqs = (
        state["stage_a_pass"]
        and state["stage_b_pass"]
        and state["source_boundary_pass"]
        and state["execution_surface_pass"]
        and state["lease_active"]
        and carrier_bound
        and no_newer_revocation
    )
    can_execute = (
        prereqs
        and isinstance(execution_budget, int)
        and not isinstance(execution_budget, bool)
        and execution_budget >= 0
        and state["execution_used"] < execution_budget
    )
    can_verify = (
        prereqs
        and state["execution_used"] > 0
        and isinstance(verifier_budget, int)
        and not isinstance(verifier_budget, bool)
        and verifier_budget >= 0
        and state["verifier_used"] < verifier_budget
    )

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
