"""Fail-closed lower-bound reducer for frozen Terminal-Bench-Science 0.1."""
from __future__ import annotations
from typing import Iterable, Mapping, Any

FINAL_FAILURE_STATES = {
    "FAILURE", "TIMEOUT", "INFRA_FAILURE", "RESOURCE_FAILURE", "INVALID", "CANCELLED"
}

def adjudicate(
    expected_slot_ids: Iterable[str],
    records: Iterable[Mapping[str, Any]],
    *,
    required_successes: int = 124,
    final: bool = False,
) -> dict[str, Any]:
    expected = [str(x) for x in expected_slot_ids]
    if len(expected) != 210 or len(set(expected)) != 210:
        raise ValueError("TB_SCIENCE_EXPECTED_SLOT_UNIVERSE_MUST_BE_EXACTLY_210_UNIQUE")
    if not (1 <= int(required_successes) <= 210):
        raise ValueError("TB_SCIENCE_REQUIRED_SUCCESS_COUNT_INVALID")

    expected_set = set(expected)
    seen: set[str] = set()
    successes = 0
    finalized_failures = 0

    for rec in records:
        sid = str(rec.get("slot_id") or "")
        state = str(rec.get("state") or "")
        if sid not in expected_set:
            raise ValueError("TB_SCIENCE_RECORD_OUTSIDE_FROZEN_SLOT_UNIVERSE")
        if sid in seen:
            raise ValueError("TB_SCIENCE_DUPLICATE_SLOT_RECORD")
        seen.add(sid)
        if state == "SUCCESS":
            successes += 1
        elif state in FINAL_FAILURE_STATES:
            finalized_failures += 1
        else:
            raise ValueError("TB_SCIENCE_RECORD_STATE_INVALID")

    missing = 210 - len(seen)
    pending = 0 if final else missing
    conservative_failures = finalized_failures + (missing if final else 0)
    pass_locked = successes >= int(required_successes)
    fail_locked = (successes + pending) < int(required_successes)
    status = "PASS_LOCK" if pass_locked else "FAIL_LOCK" if fail_locked else "OPEN"
    if final and status == "OPEN":
        status = "FAIL_LOCK"
        fail_locked = True

    return {
        "schema": "PROJECT_BRAIN_TB_SCIENCE_CONSERVATIVE_CENSORING_REDUCER_V1",
        "status": status,
        "successes": successes,
        "finalized_failures": finalized_failures,
        "conservative_failures": conservative_failures,
        "pending": pending,
        "total_slots": 210,
        "required_successes": int(required_successes),
        "lower_bound_rate": successes / 210.0,
        "pass_locked": pass_locked,
        "fail_locked": fail_locked,
        "unobserved_slots_count_as_zero_on_finalization": True,
    }
