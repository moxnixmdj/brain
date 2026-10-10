from __future__ import annotations

from fractions import Fraction
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ZERO_SPEND_PROVIDER_GUARD_V1"

class ZeroSpendBlocked(RuntimeError):
    pass

def _fraction(value: Any, name: str) -> Fraction:
    if isinstance(value, bool):
        raise ZeroSpendBlocked(name.upper() + "_INVALID")
    try:
        return value if isinstance(value, Fraction) else Fraction(str(value))
    except Exception as exc:
        raise ZeroSpendBlocked(name.upper() + "_INVALID") from exc

def _nonneg_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ZeroSpendBlocked(name.upper() + "_INVALID")
    return value

def validate_account_snapshot(snapshot: Mapping[str, Any], *, provider_id: str | None = None) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        raise ZeroSpendBlocked("ACCOUNT_SNAPSHOT_REQUIRED")
    pid = str(snapshot.get("provider_id") or "").strip()
    if not pid:
        raise ZeroSpendBlocked("PROVIDER_ID_REQUIRED")
    if provider_id is not None and pid != str(provider_id):
        raise ZeroSpendBlocked("PROVIDER_ID_MISMATCH")
    required_true = ("receipt_verified", "snapshot_fresh", "free_plan_active")
    for key in required_true:
        if snapshot.get(key) is not True:
            raise ZeroSpendBlocked(key.upper() + "_NOT_PROVEN")
    required_false = ("paid_fallback_enabled", "overage_enabled", "billing_charge_path_enabled")
    for key in required_false:
        if snapshot.get(key) is not False:
            raise ZeroSpendBlocked(key.upper() + "_NOT_DISABLED")
    if _fraction(snapshot.get("incremental_spend_usd", 0), "incremental_spend_usd") != 0:
        raise ZeroSpendBlocked("NONZERO_INCREMENTAL_SPEND")
    for key in ("account_hash", "snapshot_hash"):
        value = str(snapshot.get(key) or "").strip()
        if len(value) < 16:
            raise ZeroSpendBlocked(key.upper() + "_REQUIRED")
    return {
        "schema": SCHEMA,
        "status": "PASS__HARD_ZERO_SPEND_ACCOUNT_STATE",
        "provider_id": pid,
        "account_hash": snapshot["account_hash"],
        "snapshot_hash": snapshot["snapshot_hash"],
        "incremental_spend_usd": 0,
    }

def authorize_call(snapshot: Mapping[str, Any], *, provider_id: str, call_id: str) -> dict[str, Any]:
    state = validate_account_snapshot(snapshot, provider_id=provider_id)
    cid = str(call_id or "").strip()
    if not cid:
        raise ZeroSpendBlocked("CALL_ID_REQUIRED")
    return {
        "schema": SCHEMA,
        "status": "PASS__ZERO_SPEND_CALL_AUTHORIZED",
        "provider_id": state["provider_id"],
        "call_id": cid,
        "account_hash": state["account_hash"],
        "snapshot_hash": state["snapshot_hash"],
        "incremental_spend_usd": 0,
        "paid_fallback_allowed": False,
        "overage_allowed": False,
    }

def observe_call(
    snapshot: Mapping[str, Any],
    *,
    provider_id: str,
    call_id: str,
    outcome: Mapping[str, Any],
) -> dict[str, Any]:
    auth = authorize_call(snapshot, provider_id=provider_id, call_id=call_id)
    if not isinstance(outcome, Mapping):
        raise ZeroSpendBlocked("CALL_OUTCOME_REQUIRED")
    if str(outcome.get("provider_id") or "").strip() != provider_id:
        raise ZeroSpendBlocked("OUTCOME_PROVIDER_MISMATCH")
    if str(outcome.get("call_id") or "").strip() != str(call_id):
        raise ZeroSpendBlocked("OUTCOME_CALL_ID_MISMATCH")
    if outcome.get("paid_charge_observed") is not False:
        raise ZeroSpendBlocked("PAID_CHARGE_OR_UNKNOWN")
    if outcome.get("quota_exhausted") is not False:
        raise ZeroSpendBlocked("QUOTA_EXHAUSTED_OR_UNKNOWN")
    if outcome.get("payment_required") is not False:
        raise ZeroSpendBlocked("PAYMENT_REQUIRED_OR_UNKNOWN")
    if outcome.get("overage_observed") is not False:
        raise ZeroSpendBlocked("OVERAGE_OR_UNKNOWN")
    if _fraction(outcome.get("observed_cost_usd", 0), "observed_cost_usd") != 0:
        raise ZeroSpendBlocked("NONZERO_OBSERVED_COST")
    return {
        "schema": SCHEMA,
        "status": "PASS__ZERO_SPEND_CALL_OBSERVED",
        "provider_id": provider_id,
        "call_id": str(call_id),
        "snapshot_hash": auth["snapshot_hash"],
        "incremental_spend_usd": 0,
        "quota_exhausted": False,
        "payment_required": False,
        "paid_charge_observed": False,
    }

def finalize_run(
    summaries: Sequence[Mapping[str, Any]],
    *,
    required_provider_ids: Iterable[str],
    evaluation_completed: bool,
) -> dict[str, Any]:
    if evaluation_completed is not True:
        raise ZeroSpendBlocked("EVALUATION_NOT_COMPLETED")
    required = {str(x).strip() for x in required_provider_ids if str(x).strip()}
    if not required:
        raise ZeroSpendBlocked("REQUIRED_PROVIDER_IDS_EMPTY")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for raw in summaries:
        if not isinstance(raw, Mapping):
            raise ZeroSpendBlocked("SUMMARY_INVALID")
        pid = str(raw.get("provider_id") or "").strip()
        if not pid or pid in seen:
            raise ZeroSpendBlocked("SUMMARY_PROVIDER_INVALID_OR_DUPLICATE")
        seen.add(pid)
        attempted = _nonneg_int(raw.get("attempted_calls"), "attempted_calls")
        observed = _nonneg_int(raw.get("observed_calls"), "observed_calls")
        if attempted != observed:
            raise ZeroSpendBlocked("UNOBSERVED_PROVIDER_CALLS")
        if raw.get("all_calls_guarded") is not True:
            raise ZeroSpendBlocked("UNGUARDED_PROVIDER_CALL")
        if _nonneg_int(raw.get("guard_trip_count", 0), "guard_trip_count") != 0:
            raise ZeroSpendBlocked("GUARD_TRIP_OBSERVED")
        if _nonneg_int(raw.get("quota_exhaustion_count", 0), "quota_exhaustion_count") != 0:
            raise ZeroSpendBlocked("QUOTA_EXHAUSTION_OBSERVED")
        if _nonneg_int(raw.get("payment_required_count", 0), "payment_required_count") != 0:
            raise ZeroSpendBlocked("PAYMENT_REQUIRED_OBSERVED")
        if _nonneg_int(raw.get("paid_charge_count", 0), "paid_charge_count") != 0:
            raise ZeroSpendBlocked("PAID_CHARGE_OBSERVED")
        if _fraction(raw.get("observed_cost_usd", 0), "observed_cost_usd") != 0:
            raise ZeroSpendBlocked("NONZERO_RUN_COST")
        normalized.append({
            "provider_id": pid,
            "attempted_calls": attempted,
            "observed_calls": observed,
        })
    missing = sorted(required - seen)
    if missing:
        raise ZeroSpendBlocked("REQUIRED_PROVIDER_SUMMARY_MISSING:" + ",".join(missing))
    return {
        "schema": SCHEMA,
        "status": "PASS__FULL_RUN_ZERO_SPEND_AND_ZERO_EXHAUSTION_ATTESTED",
        "required_provider_ids": sorted(required),
        "provider_summaries": sorted(normalized, key=lambda x: x["provider_id"]),
        "evaluation_completed": True,
        "guard_trip_count": 0,
        "incremental_spend_usd": 0,
        "score_eligibility_zero_spend_gate": True,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
    }
