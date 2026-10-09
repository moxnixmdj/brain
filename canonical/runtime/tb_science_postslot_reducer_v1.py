"""Deterministic post-slot reducer for the frozen Terminal-Bench-Science 210-slot ledger."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

TOTAL_SLOTS = 210
PASS_LOCK = 124
FAIL_LOCK = 87


class TBSciencePostSlotError(ValueError):
    pass


def _as_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TBSciencePostSlotError(label + "_INVALID")
    return value


def _slot_by_order(manifest: Mapping[str, Any], order: int) -> dict[str, Any]:
    slots = manifest.get("slots")
    if not isinstance(slots, list) or len(slots) != TOTAL_SLOTS:
        raise TBSciencePostSlotError("FROZEN_MANIFEST_SLOT_UNIVERSE_INVALID")
    matches = [x for x in slots if isinstance(x, dict) and x.get("schedule_order") == order]
    if len(matches) != 1:
        raise TBSciencePostSlotError("FROZEN_MANIFEST_SCHEDULE_ORDER_INVALID")
    row = dict(matches[0])
    required = ("slot_id", "task_digest", "schedule_order", "task_rank")
    if any(not row.get(k) and row.get(k) != 0 for k in required):
        raise TBSciencePostSlotError("FROZEN_MANIFEST_SLOT_ROW_INVALID")
    return row


def _normalized_next(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "ledger_schedule_rank": int(row["schedule_order"]) + 1,
        "frozen_manifest_schedule_order": int(row["schedule_order"]),
        "task_rank": int(row["task_rank"]),
        "slot_id": str(row["slot_id"]),
        "task_digest": str(row["task_digest"]),
    }


def reduce_postslot(
    predecessor_ledger: Mapping[str, Any],
    receipt: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    counts = predecessor_ledger.get("current_counts")
    if not isinstance(counts, dict):
        raise TBSciencePostSlotError("PREDECESSOR_COUNTS_MISSING")

    consumed = _as_int(counts.get("consumed_slots"), "CONSUMED_SLOTS")
    successes = _as_int(counts.get("consumed_successes"), "CONSUMED_SUCCESSES")
    failures = _as_int(counts.get("consumed_final_failures"), "CONSUMED_FINAL_FAILURES")
    if consumed != successes + failures:
        raise TBSciencePostSlotError("PREDECESSOR_ACCOUNTING_INCONSISTENT")

    expected = counts.get("next_unconsumed_slot")
    if not isinstance(expected, dict):
        raise TBSciencePostSlotError("NEXT_UNCONSUMED_SLOT_MISSING")

    if receipt.get("slot_id") != expected.get("slot_id"):
        raise TBSciencePostSlotError("RECEIPT_SLOT_OUT_OF_ORDER")
    if receipt.get("task_digest") != expected.get("task_digest"):
        raise TBSciencePostSlotError("RECEIPT_TASK_DIGEST_MISMATCH")
    if receipt.get("rerun_credit") is not False:
        raise TBSciencePostSlotError("RERUN_CREDIT_MUST_BE_FALSE")
    if receipt.get("start_cas_replay_authority") not in (False, None):
        raise TBSciencePostSlotError("REPLAY_AUTHORITY_MUST_BE_FALSE")
    if receipt.get("start_cas_replacement_carrier_authority") not in (False, None):
        raise TBSciencePostSlotError("REPLACEMENT_AUTHORITY_MUST_BE_FALSE")

    started = receipt.get("task_started") is True
    trials = _as_int(receipt.get("benchmark_trials_consumed"), "BENCHMARK_TRIALS_CONSUMED")
    status = str(receipt.get("status") or "")

    current_order = _as_int(expected.get("frozen_manifest_schedule_order"), "CURRENT_SCHEDULE_ORDER")
    current_manifest_slot = _slot_by_order(manifest, current_order)
    if current_manifest_slot["slot_id"] != expected["slot_id"] or current_manifest_slot["task_digest"] != expected["task_digest"]:
        raise TBSciencePostSlotError("PREDECESSOR_NEXT_SLOT_NOT_IN_FROZEN_MANIFEST")

    if not started:
        if trials != 0 or status != "PREEXPOSURE_ABORT_NONCONSUMING":
            raise TBSciencePostSlotError("NONCONSUMING_RECEIPT_INVALID")
        return {
            "schema": "PROJECT_BRAIN_TB_SCIENCE_POSTSLOT_REDUCER_V1",
            "status": "PREEXPOSURE_ABORT_NONCONSUMING",
            "consumed_delta": 0,
            "success_delta": 0,
            "failure_delta": 0,
            "current_counts": dict(counts),
            "next_unconsumed_slot": dict(expected),
            "terminal_result": "UNCONSUMED",
        }

    if trials != 1:
        raise TBSciencePostSlotError("STARTED_SLOT_MUST_CONSUME_EXACTLY_ONE_TRIAL")
    if receipt.get("execution_authority_consumed") is not True:
        raise TBSciencePostSlotError("STARTED_SLOT_MUST_CONSUME_AUTHORITY")

    reward = receipt.get("reward")
    success = status == "SUCCESS" and isinstance(reward, (int, float)) and not isinstance(reward, bool) and float(reward) >= 1.0
    failure = status == "FINAL_ZERO"
    if success == failure:
        raise TBSciencePostSlotError("TERMINAL_RECEIPT_STATUS_INVALID")
    if success and receipt.get("consumed_successes_delta") != 1:
        raise TBSciencePostSlotError("SUCCESS_DELTA_INVALID")
    if success and receipt.get("consumed_final_failures_delta") != 0:
        raise TBSciencePostSlotError("SUCCESS_FAILURE_DELTA_INVALID")
    if failure and receipt.get("consumed_successes_delta") != 0:
        raise TBSciencePostSlotError("FAILURE_SUCCESS_DELTA_INVALID")
    if failure and receipt.get("consumed_final_failures_delta") != 1:
        raise TBSciencePostSlotError("FAILURE_DELTA_INVALID")

    new_consumed = consumed + 1
    new_successes = successes + (1 if success else 0)
    new_failures = failures + (1 if failure else 0)
    if new_consumed != new_successes + new_failures:
        raise TBSciencePostSlotError("POSTSLOT_ACCOUNTING_INCONSISTENT")

    remaining = TOTAL_SLOTS - new_consumed
    successes_needed = max(0, PASS_LOCK - new_successes)
    next_row = _slot_by_order(manifest, current_order + 1) if remaining > 0 else None
    next_slot = _normalized_next(next_row) if next_row is not None else None
    pass_reachable = new_successes + remaining >= PASS_LOCK

    new_counts = {
        "consumed_slots": new_consumed,
        "consumed_successes": new_successes,
        "consumed_final_failures": new_failures,
        "successes_remaining_for_pass_lock": successes_needed,
        "additional_failures_before_fail_lock": max(0, FAIL_LOCK - new_failures),
        "maximum_possible_successes_remaining": remaining,
        "minimum_required_success_rate_over_remaining_slots": (
            successes_needed / remaining if remaining else (0.0 if successes_needed == 0 else None)
        ),
        "pass_still_mathematically_reachable": pass_reachable,
        "next_unconsumed_slot": next_slot,
    }

    return {
        "schema": "PROJECT_BRAIN_TB_SCIENCE_POSTSLOT_REDUCER_V1",
        "status": "SUCCESS" if success else "FINAL_ZERO",
        "consumed_delta": 1,
        "success_delta": 1 if success else 0,
        "failure_delta": 1 if failure else 0,
        "current_counts": new_counts,
        "next_unconsumed_slot": next_slot,
        "terminal_result": "SUCCESS" if success else "FINAL_ZERO",
        "reward": float(reward) if isinstance(reward, (int, float)) and not isinstance(reward, bool) else None,
    }


def main() -> int:
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--ledger", required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--manifest", required=True)
    args = p.parse_args()
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
    receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    print(json.dumps(reduce_postslot(ledger, receipt, manifest), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
