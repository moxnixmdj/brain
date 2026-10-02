"""Route-specific terminal executors for direct frozen populations.

This module binds only routes whose terminal population is self-contained and
already frozen. It does not consume a terminal beacon by itself; callers provide
the candidate-package commitment and the post-freeze beacon.

Bound here:
- SA-CCR: 2000 exact hidden-oracle cases
- Browser: 150 direct-objective cases
- Delegation: 132 cases across the frozen 11-class cycle
- Tool discovery: 180 direct-objective cases
- Research control: 180 direct-objective cases

Portfolio-instrumentation routes and CAD remain intentionally unbound elsewhere
until their exact parent/executable adapter is frozen.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any, Callable

from canonical.runtime import saccr_credit_information_safe_proof as saccr_proof
from canonical.runtime import saccr_credit_information_safe_candidate as saccr_candidate
from canonical.runtime import browser_state_information_safe_proof as browser_proof
from canonical.runtime import browser_state_information_safe_candidate as browser_candidate
from canonical.runtime import delegation_whole_scope_proof_v2 as delegation_v2
from canonical.runtime import delegation_structural_variety_proof_v3 as delegation_v3
from canonical.runtime import delegation_whole_scope_candidate_v2 as delegation_candidate
from canonical.runtime import tool_discovery_information_safe_proof_v2 as tool_proof
from canonical.runtime import tool_discovery_information_safe_candidate as tool_candidate
from canonical.runtime import research_control_information_safe_proof as research_proof
from canonical.runtime import research_control_information_safe_candidate as research_candidate

SCHEMA = "PROJECT_BRAIN_DIRECT_ROUTE_TERMINAL_EXECUTORS_V1"

SA_CCR_ID = "SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001"
BROWSER_ID = "BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001"
DELEGATION_ID = "TASK_TO_DELEGATION_GRAPH_001"
TOOL_ID = "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001"
RESEARCH_ID = "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001"

COUNTS = {
    SA_CCR_ID: 2000,
    BROWSER_ID: 150,
    DELEGATION_ID: 132,
    TOOL_ID: 180,
    RESEARCH_ID: 180,
}

PREFIXES = {
    SA_CCR_ID: b"PROJECT_BRAIN_TERMINAL_V2\0",
    BROWSER_ID: b"PROJECT_BRAIN_BROWSER_TERMINAL_V1\0",
    DELEGATION_ID: b"PROJECT_BRAIN_TERMINAL_V2\0",
    TOOL_ID: b"PROJECT_BRAIN_TOOL_DISCOVERY_TERMINAL_V1\0",
    RESEARCH_ID: b"PROJECT_BRAIN_RESEARCH_TERMINAL_V1\0",
}

VERSIONS = {
    SA_CCR_ID: "SA_CCR_TERMINAL_POPULATION_V1",
    BROWSER_ID: "BROWSER_T2_DIRECT_OBJECTIVE_POOL_V1",
    DELEGATION_ID: "DELEGATION_T2_OBJECTIVE_POOL_V1",
    TOOL_ID: "TOOL_DISCOVERY_T2_T3_OBJECTIVE_POOL_V1",
    RESEARCH_ID: "RESEARCH_T3_DIRECT_OBJECTIVE_POOL_V1",
}


def _require_nonempty(value: str, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(name + "_REQUIRED")
    return value


def case_id(behavior_id: str, slot: int) -> str:
    if behavior_id not in COUNTS:
        raise ValueError("UNBOUND_DIRECT_ROUTE:" + str(behavior_id))
    if not isinstance(slot, int) or isinstance(slot, bool) or not 0 <= slot < COUNTS[behavior_id]:
        raise ValueError("SLOT_OUT_OF_RANGE")
    if behavior_id == SA_CCR_ID:
        return f"{SA_CCR_ID}::SA_CCR_TERMINAL_POPULATION_V1::slot::{slot}"
    return f"{VERSIONS[behavior_id]}::slot::{slot}"


def derive_seed(behavior_id: str, commitment: str, beacon: str, slot: int) -> int:
    _require_nonempty(commitment, "COMMITMENT")
    _require_nonempty(beacon, "BEACON")
    cid = case_id(behavior_id, slot)
    raw = PREFIXES[behavior_id] + commitment.encode() + b"\0" + beacon.encode() + b"\0" + cid.encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big", signed=False)


def _row(slot: int, cid: str, seed: int, passed: bool, reason: Any, case_class: str | None = None) -> dict[str, Any]:
    out = {
        "slot": slot,
        "case_id": cid,
        "seed": seed,
        "pass": bool(passed),
        "reason": "PASS" if passed else str(reason or "UNKNOWN"),
    }
    if case_class is not None:
        out["case_class"] = case_class
    return out


def run_saccr_case(commitment: str, beacon: str, slot: int) -> dict[str, Any]:
    seed = derive_seed(SA_CCR_ID, commitment, beacon, slot)
    cid = case_id(SA_CCR_ID, slot)
    case = saccr_proof.generate_case(seed)
    public = saccr_proof.public_task(case)
    candidate = saccr_candidate.solve(public)
    verdict = saccr_proof.score_case(case, candidate)
    return _row(slot, cid, seed, verdict.get("pass") is True, verdict.get("reason"))


def run_browser_case(commitment: str, beacon: str, slot: int) -> dict[str, Any]:
    seed = derive_seed(BROWSER_ID, commitment, beacon, slot)
    cid = case_id(BROWSER_ID, slot)
    case = browser_proof.generate_case(seed, slot)
    verdict = browser_proof.run_episode(case, browser_candidate.next_action)
    return _row(slot, cid, seed, verdict.get("pass") is True, verdict.get("reason"), case.get("case_class"))


def run_delegation_case(commitment: str, beacon: str, slot: int) -> dict[str, Any]:
    seed = derive_seed(DELEGATION_ID, commitment, beacon, slot)
    cid = case_id(DELEGATION_ID, slot)
    pos = slot % 11
    if pos < 6:
        case = delegation_v2.generate_case(seed, pos)
        try:
            first = delegation_candidate.solve_initial(delegation_v2.public_initial(case))
            second = delegation_candidate.solve_after_receipt(delegation_v2.public_after_receipt(case), first)
            verdict = delegation_v2.score_episode(case, first, second)
        except Exception as exc:
            verdict = {"pass": False, "reason": "EXCEPTION:" + type(exc).__name__ + ":" + str(exc)}
        cls = case.get("case_class")
    else:
        case = delegation_v3.generate_case(seed, pos - 6)
        try:
            candidate = delegation_candidate.solve_initial(delegation_v3.public_case(case))
            verdict = delegation_v3.score_case(case, candidate)
        except Exception as exc:
            verdict = {"pass": False, "reason": "EXCEPTION:" + type(exc).__name__ + ":" + str(exc)}
        cls = case.get("case_class")
    return _row(slot, cid, seed, verdict.get("pass") is True, verdict.get("reason"), cls)


def run_tool_case(commitment: str, beacon: str, slot: int) -> dict[str, Any]:
    seed = derive_seed(TOOL_ID, commitment, beacon, slot)
    cid = case_id(TOOL_ID, slot)
    case = tool_proof.generate_case(seed, slot)
    try:
        verdict = tool_proof.score_episode(case, tool_candidate.next_action)
    except Exception as exc:
        verdict = {"pass": False, "reason": "EXCEPTION:" + type(exc).__name__ + ":" + str(exc)}
    return _row(slot, cid, seed, verdict.get("pass") is True, verdict.get("reason"), case.get("case_class"))


def run_research_case(commitment: str, beacon: str, slot: int) -> dict[str, Any]:
    seed = derive_seed(RESEARCH_ID, commitment, beacon, slot)
    cid = case_id(RESEARCH_ID, slot)
    case = research_proof.generate_case(seed, slot)
    try:
        verdict = research_proof.run_episode(case, research_candidate.next_action)
    except Exception as exc:
        verdict = {"pass": False, "reason": "EXCEPTION:" + type(exc).__name__ + ":" + str(exc)}
    domain = research_proof.DOMAINS[slot % len(research_proof.DOMAINS)]
    return _row(slot, cid, seed, verdict.get("pass") is True, verdict.get("reason"), domain)


_RUN_ONE: dict[str, Callable[[str, str, int], dict[str, Any]]] = {
    SA_CCR_ID: run_saccr_case,
    BROWSER_ID: run_browser_case,
    DELEGATION_ID: run_delegation_case,
    TOOL_ID: run_tool_case,
    RESEARCH_ID: run_research_case,
}


def execute_direct_route(behavior_id: str, *, commitment: str, beacon: str) -> dict[str, Any]:
    if behavior_id not in _RUN_ONE:
        raise ValueError("UNBOUND_DIRECT_ROUTE:" + str(behavior_id))
    _require_nonempty(commitment, "COMMITMENT")
    _require_nonempty(beacon, "BEACON")
    count = COUNTS[behavior_id]
    rows = [_RUN_ONE[behavior_id](commitment, beacon, slot) for slot in range(count)]
    passed = sum(int(row["pass"]) for row in rows)
    class_counts = Counter(str(row.get("case_class")) for row in rows if row.get("case_class") is not None)
    return {
        "schema": SCHEMA,
        "behavior_id": behavior_id,
        "population_version": VERSIONS[behavior_id],
        "case_count": count,
        "pass_count": passed,
        "failed_count": count - passed,
        "pass": passed == count,
        "class_counts": dict(sorted(class_counts.items())),
        "cases": rows,
        "no_case_replacement": True,
        "no_tuning_replay": True,
        "terminal_result": True,
        "capability_credit_delta": "DEFER_TO_TERMINAL_REDUCER",
        "family_credit_delta": "DEFER_TO_TERMINAL_REDUCER",
    }


def bound_behavior_ids() -> tuple[str, ...]:
    return tuple(sorted(_RUN_ONE))
