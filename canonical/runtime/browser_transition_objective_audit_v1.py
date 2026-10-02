"""Objective receipt auditor for browser state transitions.

This is evaluator-side machinery only. It checks two previously uncovered
contract dimensions for BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001:

* undeclared/unobserved side effects, via frozen state-diff keys;
* repeated no-progress action loops, via state hashes and action signatures.

It never selects browser actions and never grants terminal or capability credit.
"""
from __future__ import annotations
from collections import Counter
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_BROWSER_TRANSITION_OBJECTIVE_AUDIT_V1"

def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "reason": reason,
        "terminal_authority": False,
        "capability_credit_delta": 0,
        **extra,
    }

def audit_trace(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("INPUT_NOT_OBJECT")
    writable = payload.get("declared_writable_keys")
    system = payload.get("allowed_system_keys", [])
    steps = payload.get("steps")
    limit = payload.get("no_progress_repeat_limit")
    if (
        not isinstance(writable, list)
        or any(not isinstance(x, str) or not x for x in writable)
        or not isinstance(system, list)
        or any(not isinstance(x, str) or not x for x in system)
        or not isinstance(steps, list)
        or not steps
        or not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < 1
    ):
        return _fail("INPUT_SCHEMA_INVALID")
    if len(set(writable)) != len(writable) or len(set(system)) != len(system):
        return _fail("DUPLICATE_STATE_KEY")

    allowed = set(writable) | set(system)
    seen_no_progress: Counter[tuple[str, str]] = Counter()
    for i, step in enumerate(steps):
        if not isinstance(step, Mapping):
            return _fail("STEP_NOT_OBJECT", step=i)
        action = step.get("action_signature")
        before = step.get("state_hash_before")
        after = step.get("state_hash_after")
        diff = step.get("observed_diff_keys")
        receipt = step.get("receipt_bound")
        if (
            not isinstance(action, str) or not action
            or not isinstance(before, str) or not before
            or not isinstance(after, str) or not after
            or not isinstance(diff, list)
            or any(not isinstance(x, str) or not x for x in diff)
            or type(receipt) is not bool
        ):
            return _fail("STEP_SCHEMA_INVALID", step=i)
        if not receipt:
            return _fail("UNBOUND_ACTION_RECEIPT", step=i)
        undeclared = sorted(set(diff) - allowed)
        if undeclared:
            return _fail("UNDECLARED_SIDE_EFFECT", step=i, keys=undeclared)

        signature = (before, action)
        if after == before:
            seen_no_progress[signature] += 1
            if seen_no_progress[signature] > limit:
                return _fail(
                    "NO_PROGRESS_LOOP",
                    step=i,
                    state_hash=before,
                    action_signature=action,
                    repeats=seen_no_progress[signature],
                )
        else:
            seen_no_progress[signature] = 0

    if payload.get("terminal_success") is not True:
        return _fail("PARENT_TERMINAL_ACCEPTANCE_FAILED")
    return {
        "schema": SCHEMA,
        "pass": True,
        "reason": "PASS",
        "audited_steps": len(steps),
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
