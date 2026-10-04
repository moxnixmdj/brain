from __future__ import annotations
from fractions import Fraction
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_ZERO_SPEND_GUARD_V1"
MODEL_ID = "google/gemini-3.5-flash"
MINIMUM_JUDGE_CALLS = 1000

class ZeroSpendBlocked(RuntimeError):
    pass

def _fraction(value: Any, name: str) -> Fraction:
    if isinstance(value, bool):
        raise ZeroSpendBlocked(name.upper()+"_INVALID")
    try:
        return value if isinstance(value, Fraction) else Fraction(str(value))
    except Exception as exc:
        raise ZeroSpendBlocked(name.upper()+"_INVALID") from exc

def _verified_snapshot(snapshot: Mapping[str, Any]) -> None:
    if not isinstance(snapshot, Mapping):
        raise ZeroSpendBlocked("ACCOUNT_SNAPSHOT_REQUIRED")
    if snapshot.get("receipt_verified") is not True:
        raise ZeroSpendBlocked("ACCOUNT_RECEIPT_NOT_VERIFIED")
    if str(snapshot.get("model_id") or "") != MODEL_ID:
        raise ZeroSpendBlocked("JUDGE_MODEL_MISMATCH")
    if snapshot.get("model_access") is not True:
        raise ZeroSpendBlocked("MODEL_ACCESS_NOT_VERIFIED")
    if snapshot.get("free_tier_active") is not True:
        raise ZeroSpendBlocked("FREE_TIER_NOT_VERIFIED")
    if snapshot.get("paid_fallback_enabled") is not False:
        raise ZeroSpendBlocked("PAID_FALLBACK_NOT_DISABLED")
    if snapshot.get("overage_enabled") is not False:
        raise ZeroSpendBlocked("OVERAGE_NOT_DISABLED")
    if _fraction(snapshot.get("incremental_spend_usd", 0), "incremental_spend_usd") != 0:
        raise ZeroSpendBlocked("NONZERO_INCREMENTAL_SPEND")
    project_hash=str(snapshot.get("project_hash") or "").strip()
    if len(project_hash) < 16:
        raise ZeroSpendBlocked("PROJECT_HASH_REQUIRED")
    cap=snapshot.get("verified_free_call_capacity")
    if isinstance(cap,bool) or not isinstance(cap,int) or cap < 0:
        raise ZeroSpendBlocked("VERIFIED_FREE_CALL_CAPACITY_REQUIRED")

def authorize_plan(snapshot: Mapping[str, Any], *, required_calls: int = MINIMUM_JUDGE_CALLS,
                   retry_reserve: int = 0) -> dict[str, Any]:
    _verified_snapshot(snapshot)
    if isinstance(required_calls,bool) or not isinstance(required_calls,int) or required_calls < MINIMUM_JUDGE_CALLS:
        raise ZeroSpendBlocked("REQUIRED_CALLS_BELOW_FROZEN_MINIMUM")
    if isinstance(retry_reserve,bool) or not isinstance(retry_reserve,int) or retry_reserve < 0:
        raise ZeroSpendBlocked("RETRY_RESERVE_INVALID")
    needed=required_calls+retry_reserve
    capacity=int(snapshot["verified_free_call_capacity"])
    if capacity < needed:
        raise ZeroSpendBlocked("VERIFIED_FREE_CAPACITY_INSUFFICIENT")
    return {
        "schema":SCHEMA,
        "status":"PASS__HARD_ZERO_SPEND_PLAN_AUTHORIZED",
        "model_id":MODEL_ID,
        "required_calls":required_calls,
        "retry_reserve":retry_reserve,
        "verified_free_call_capacity":capacity,
        "project_hash":snapshot["project_hash"],
        "incremental_spend_usd":0,
        "paid_fallback_allowed":False,
        "fresh_reality_authority":False,
        "benchmark_case_execution_authority":False,
    }

def authorize_next_call(snapshot: Mapping[str, Any], *, successful_calls: int,
                        attempted_calls: int, required_calls: int = MINIMUM_JUDGE_CALLS,
                        retry_reserve_remaining: int = 0) -> dict[str, Any]:
    _verified_snapshot(snapshot)
    for name,value in {
        "successful_calls":successful_calls,
        "attempted_calls":attempted_calls,
        "required_calls":required_calls,
        "retry_reserve_remaining":retry_reserve_remaining,
    }.items():
        if isinstance(value,bool) or not isinstance(value,int) or value < 0:
            raise ZeroSpendBlocked(name.upper()+"_INVALID")
    if required_calls < MINIMUM_JUDGE_CALLS:
        raise ZeroSpendBlocked("REQUIRED_CALLS_BELOW_FROZEN_MINIMUM")
    if successful_calls > attempted_calls:
        raise ZeroSpendBlocked("SUCCESS_GT_ATTEMPTS")
    if successful_calls >= required_calls:
        return {
            "schema":SCHEMA,
            "status":"STOP__REQUIRED_JUDGE_CALLS_COMPLETE",
            "authorize_call":False,
            "incremental_spend_usd":0,
        }
    capacity=int(snapshot["verified_free_call_capacity"])
    remaining_capacity=capacity-attempted_calls
    minimum_needed=(required_calls-successful_calls)+retry_reserve_remaining
    if remaining_capacity < minimum_needed:
        raise ZeroSpendBlocked("FREE_CAPACITY_NO_LONGER_SUFFICIENT")
    return {
        "schema":SCHEMA,
        "status":"PASS__NEXT_FREE_TIER_CALL_AUTHORIZED",
        "authorize_call":True,
        "model_id":MODEL_ID,
        "project_hash":snapshot["project_hash"],
        "remaining_verified_free_capacity":remaining_capacity,
        "minimum_remaining_need":minimum_needed,
        "incremental_spend_usd":0,
        "paid_fallback_allowed":False,
    }
