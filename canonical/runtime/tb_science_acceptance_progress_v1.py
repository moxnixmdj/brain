"""Finite acceptance-progress theorem for frozen Terminal-Bench-Science.

This module proves only the score/measure consequence of FINALIZING one previously
unresolved frozen slot. It does not claim that a current slot can always be
started or finalized. Pre-exposure/non-consuming aborts are therefore outside
the finalized-outcome action and receive no progress credit.
"""
from __future__ import annotations

from typing import Any

SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_ACCEPTANCE_PROGRESS_V1"
TOTAL_SLOTS = 210
REQUIRED_SUCCESSES = 124
FAIL_LOCK_FAILURES = 87


class ProgressStateError(ValueError):
    pass


def state(successes: int, finalized_failures: int) -> dict[str, Any]:
    for label, value in (
        ("SUCCESSES", successes),
        ("FINALIZED_FAILURES", finalized_failures),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ProgressStateError(label + "_INVALID")
    if successes + finalized_failures > TOTAL_SLOTS:
        raise ProgressStateError("COUNT_EXCEEDS_FROZEN_SLOT_UNIVERSE")

    unresolved = TOTAL_SLOTS - successes - finalized_failures
    pass_locked = successes >= REQUIRED_SUCCESSES
    fail_locked = successes + unresolved < REQUIRED_SUCCESSES
    status = "PASS_LOCK" if pass_locked else "FAIL_LOCK" if fail_locked else "OPEN"

    if status == "OPEN" and unresolved <= 0:
        raise ProgressStateError("OPEN_STATE_WITHOUT_UNRESOLVED_SLOT")

    return {
        "schema": SCHEMA,
        "status": status,
        "successes": successes,
        "finalized_failures": finalized_failures,
        "unresolved_slots": unresolved,
        "total_slots": TOTAL_SLOTS,
        "required_successes": REQUIRED_SUCCESSES,
        "fail_lock_failures": FAIL_LOCK_FAILURES,
        "pass_locked": pass_locked,
        "fail_locked": fail_locked,
        "well_founded_measure": {
            "kind": "UNRESOLVED_FROZEN_SLOT_COUNT",
            "current_rank": unresolved,
            "minimum_rank": 0,
            "well_founded": True,
        },
        "terminal": status != "OPEN",
        "acceptance_relevant": True,
    }


def finalize_one(
    successes: int,
    finalized_failures: int,
    outcome: str,
) -> dict[str, Any]:
    before = state(successes, finalized_failures)
    if before["status"] != "OPEN":
        raise ProgressStateError("FINALIZATION_REQUIRES_OPEN_PARENT_STATE")
    if before["unresolved_slots"] <= 0:
        raise ProgressStateError("NO_UNRESOLVED_SLOT_TO_FINALIZE")

    if outcome == "SUCCESS":
        after = state(successes + 1, finalized_failures)
    elif outcome == "FINAL_FAILURE":
        after = state(successes, finalized_failures + 1)
    else:
        raise ProgressStateError("FINALIZED_OUTCOME_INVALID")

    terminal = after["terminal"] is True
    strict_decrease = (
        after["status"] == "OPEN"
        and after["unresolved_slots"] == before["unresolved_slots"] - 1
    )
    if terminal == strict_decrease:
        raise ProgressStateError("OUTCOME_NOT_EXACTLY_TERMINAL_OR_DECREASING")

    return {
        "schema": SCHEMA,
        "status": "PASS__FINALIZED_OUTCOME_TERMINAL_OR_STRICTLY_DECREASING",
        "pass": True,
        "action_class": "FINALIZE_ONE_PREVIOUSLY_UNRESOLVED_FROZEN_SLOT",
        "outcome": outcome,
        "before": before,
        "after": after,
        "terminal": terminal,
        "strictly_decreases_measure": strict_decrease,
        "rank_delta": after["unresolved_slots"] - before["unresolved_slots"],
        "current_action_executability_proved": False,
        "nonconsuming_preexposure_abort_counts_as_progress": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def prove_all_count_states() -> dict[str, Any]:
    valid_states = 0
    open_states = 0
    checked_outcomes = 0
    pass_locks = 0
    fail_locks = 0

    for successes in range(TOTAL_SLOTS + 1):
        for failures in range(TOTAL_SLOTS - successes + 1):
            current = state(successes, failures)
            valid_states += 1
            if current["status"] == "PASS_LOCK":
                pass_locks += 1
                continue
            if current["status"] == "FAIL_LOCK":
                fail_locks += 1
                continue

            open_states += 1
            if current["unresolved_slots"] <= 0:
                raise ProgressStateError("OPEN_STATE_RANK_NOT_POSITIVE")
            for outcome in ("SUCCESS", "FINAL_FAILURE"):
                proof = finalize_one(successes, failures, outcome)
                checked_outcomes += 1
                if not proof["pass"]:
                    raise ProgressStateError("FINALIZED_OUTCOME_PROOF_FAILED")

    return {
        "schema": SCHEMA,
        "status": "PASS__EXHAUSTIVE_FINITE_COUNT_STATE_PROOF",
        "pass": True,
        "valid_count_states_checked": valid_states,
        "open_count_states_checked": open_states,
        "finalized_outcomes_checked": checked_outcomes,
        "pass_lock_states": pass_locks,
        "fail_lock_states": fail_locks,
        "all_open_states_have_positive_finite_rank": True,
        "every_finalized_outcome_terminal_or_strictly_decreases": True,
        "rank_decrease_for_nonterminal_finalization": 1,
        "maximum_rank": TOTAL_SLOTS,
        "current_action_executability_proved": False,
        "nonconsuming_preexposure_abort_counts_as_progress": False,
        "global_tb_science_acceptance_proved": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
