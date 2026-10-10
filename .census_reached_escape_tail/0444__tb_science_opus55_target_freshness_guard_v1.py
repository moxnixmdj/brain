"""Fail-closed target-freshness guard for Terminal-Bench-Science Opus 5.5 parity."""
from __future__ import annotations
import copy
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "canonical/governance/TB_SCIENCE_OPUS55_TARGET_FRESHNESS_V1.json"
SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_OPUS55_TARGET_FRESHNESS_GUARD_V1"

def evaluate(data: dict[str, Any] | None = None, *, snapshot_identity_proved: bool = False) -> dict[str, Any]:
    d = copy.deepcopy(data) if data is not None else json.loads(DEFAULT.read_text(encoding="utf-8"))
    errors: list[str] = []
    frozen = d.get("frozen_protocol") or {}
    fresh = d.get("fresh_public_observation") or {}
    arithmetic = d.get("arithmetic_if_snapshot_identity_matches") or {}
    slots = int(frozen.get("slots", 0) or 0)
    score = float(fresh.get("resolution_rate_percent", 0) or 0)
    required = math.ceil(slots * score / 100.0) if slots and score else 0
    fail_lock = slots - required + 1 if required else 0
    consumed = int(arithmetic.get("finalized_failures_already_consumed", 0) or 0)

    if slots != 210:
        errors.append("SLOT_COUNT_DRIFT")
    if score != 63.3:
        errors.append("FRESH_OPUS55_SCORE_DRIFT")
    if required != 133:
        errors.append("REQUIRED_SUCCESS_ARITHMETIC_DRIFT")
    if fail_lock != 78:
        errors.append("FAIL_LOCK_ARITHMETIC_DRIFT")
    if arithmetic.get("required_successes") != required:
        errors.append("DECLARED_REQUIRED_SUCCESSES_MISMATCH")
    if arithmetic.get("fail_lock_failures") != fail_lock:
        errors.append("DECLARED_FAIL_LOCK_MISMATCH")
    if arithmetic.get("remaining_failures_before_fail_lock") != fail_lock - consumed:
        errors.append("DECLARED_REMAINING_FAILURES_MISMATCH")
    if d.get("execution_authority") is not False or d.get("promotion_authority") is not False:
        errors.append("PREMATURE_AUTHORITY")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_INVALID_FRESHNESS_INPUT",
            "pass": False,
            "errors": sorted(set(errors)),
            "execution_authority": False,
            "promotion_authority": False,
        }

    if not snapshot_identity_proved:
        return {
            "schema": SCHEMA,
            "status": "PASS__TARGET_FRESHNESS_HOLD_REQUIRED__SNAPSHOT_IDENTITY_UNPROVED",
            "pass": True,
            "effective_execution_authority": False,
            "observed_current_opus55_percent": score,
            "frozen_old_percent": frozen.get("frozen_opus55_bar_percent"),
            "same_snapshot_required_successes_if_proved": required,
            "same_snapshot_fail_lock_if_proved": fail_lock,
            "snapshot_identity_proved": False,
            "promotion_authority": False,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS__SAME_SNAPSHOT_ASSUMPTION_INPUT__EFFECTIVE_TARGET_63_3__SEPARATE_INDEPENDENT_IDENTITY_RECEIPT_STILL_REQUIRED_FOR_CANONICAL_PROMOTION",
        "pass": True,
        "effective_execution_authority": False,
        "observed_current_opus55_percent": score,
        "effective_required_successes": required,
        "effective_fail_lock_failures": fail_lock,
        "snapshot_identity_proved": True,
        "promotion_authority": False,
    }

if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
