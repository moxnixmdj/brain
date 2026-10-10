from __future__ import annotations

from decimal import Decimal, InvalidOperation, getcontext
from typing import Any, Mapping
import re

getcontext().prec = 40

INPUT_SCHEMA = "PROJECT_BRAIN_ROOT2_CALIBRATED_SETTLEMENT_SCHEDULER_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_ROOT2_CALIBRATED_SETTLEMENT_SCHEDULER_OUTPUT_V1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")


class SettlementSchedulerError(ValueError):
    pass


def _d(v: Any, field: str) -> Decimal:
    if isinstance(v, bool):
        raise SettlementSchedulerError(field + "_INVALID")
    try:
        x = Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise SettlementSchedulerError(field + "_INVALID") from exc
    if not x.is_finite():
        raise SettlementSchedulerError(field + "_NONFINITE")
    return x


def _receipt(v: Any) -> bool:
    return (
        isinstance(v, Mapping)
        and isinstance(v.get("path"), str)
        and bool(v.get("path"))
        and isinstance(v.get("git_blob_sha"), str)
        and bool(HEX40.fullmatch(v["git_blob_sha"].lower()))
    )


def _ids(v: Any, field: str) -> list[str]:
    if not isinstance(v, list) or any(not isinstance(x, str) or not x for x in v):
        raise SettlementSchedulerError(field + "_INVALID")
    if len(v) != len(set(v)):
        raise SettlementSchedulerError(field + "_DUPLICATE")
    return list(v)


def _posterior(action: Mapping[str, Any]) -> tuple[Decimal | None, str]:
    if action.get("deterministic_settlement") is True:
        return Decimal("1"), "DETERMINISTIC"
    hist = action.get("calibration_history")
    if hist is None:
        return None, "UNCALIBRATED"
    if not isinstance(hist, Mapping) or not _receipt(hist.get("receipt")):
        raise SettlementSchedulerError("CALIBRATION_HISTORY_RECEIPT_REQUIRED")
    trials = hist.get("trials")
    success = hist.get("settled")
    if isinstance(trials, bool) or isinstance(success, bool) or not isinstance(trials, int) or not isinstance(success, int):
        raise SettlementSchedulerError("CALIBRATION_COUNTS_INVALID")
    if trials <= 0 or success < 0 or success > trials:
        raise SettlementSchedulerError("CALIBRATION_COUNTS_INVALID")
    # Jeffreys Beta(1/2,1/2) posterior mean. This is used only for scheduling,
    # never as acceptance evidence.
    p = (Decimal(success) + Decimal("0.5")) / (Decimal(trials) + Decimal("1"))
    return p, "JEFFREYS_POSTERIOR_MEAN"


def compile_settlement_schedule(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
            raise SettlementSchedulerError("SCHEMA_MISMATCH")
        actions = doc.get("actions")
        if not isinstance(actions, list):
            raise SettlementSchedulerError("ACTIONS_INVALID")
        allow_fresh = doc.get("allow_fresh_reality", False)
        if not isinstance(allow_fresh, bool):
            raise SettlementSchedulerError("ALLOW_FRESH_REALITY_INVALID")

        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        blocked: list[str] = []

        for i, raw in enumerate(actions):
            if not isinstance(raw, Mapping):
                raise SettlementSchedulerError(f"ACTION_NOT_MAPPING:{i}")
            aid = raw.get("action_id")
            if not isinstance(aid, str) or not aid or aid in seen:
                raise SettlementSchedulerError("ACTION_ID_INVALID_OR_DUPLICATE")
            seen.add(aid)

            zr = raw.get("zero_reality")
            if not isinstance(zr, bool):
                raise SettlementSchedulerError("ACTION_ZERO_REALITY_INVALID:" + aid)
            if not zr and not allow_fresh:
                blocked.append(aid)
                continue

            sec = _d(raw.get("critical_path_seconds"), "CRITICAL_PATH_SECONDS")
            if sec <= 0:
                raise SettlementSchedulerError("CRITICAL_PATH_SECONDS_MUST_BE_POSITIVE:" + aid)

            settles = _ids(raw.get("settles_predicates", []), "SETTLES_PREDICATES")
            deletes = _ids(raw.get("deletes_actions_if_settled", []), "DELETES_ACTIONS_IF_SETTLED")
            if aid in deletes:
                raise SettlementSchedulerError("ACTION_CANNOT_DELETE_ITSELF:" + aid)

            p, method = _posterior(raw)
            direct = Decimal(len(settles))
            deletion = Decimal(len(deletes))
            terminal_delta = direct + deletion

            if p is None:
                expected_delta = None
                rate = None
            else:
                expected_delta = p * terminal_delta
                rate = expected_delta / sec

            rows.append({
                "action_id": aid,
                "critical_path_seconds": str(sec),
                "settles_predicates": settles,
                "deletes_actions_if_settled": deletes,
                "direct_settlement_count": len(settles),
                "downstream_action_deletion_count": len(deletes),
                "calibration_method": method,
                "settlement_probability": None if p is None else str(p),
                "expected_terminal_delta": None if expected_delta is None else str(expected_delta),
                "expected_terminal_delta_per_second": None if rate is None else str(rate),
            })

        calibrated = [r for r in rows if r["expected_terminal_delta_per_second"] is not None]
        uncalibrated = [r for r in rows if r["expected_terminal_delta_per_second"] is None]

        calibrated.sort(
            key=lambda r: (
                -Decimal(r["expected_terminal_delta_per_second"]),
                Decimal(r["critical_path_seconds"]),
                -r["direct_settlement_count"],
                r["action_id"],
            )
        )
        uncalibrated.sort(
            key=lambda r: (
                Decimal(r["critical_path_seconds"]),
                -r["direct_settlement_count"],
                r["action_id"],
            )
        )

        ranked = calibrated + uncalibrated
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "PASS__CALIBRATED_SCHEDULING_ONLY__ZERO_CREDIT",
            "ranked_actions": ranked,
            "blocked_fresh_reality_actions": sorted(blocked),
            "ranking_rule": (
                "CALIBRATED_ACTIONS_DESC_EXPECTED_TERMINAL_DELTA_PER_SECOND__"
                "JEFFREYS_BETA_POSTERIOR_FROM_CONTENT_ADDRESSED_HISTORY_OR_DETERMINISTIC_P1__"
                "UNCALIBRATED_ACTIONS_RECEIVE_NO_PROBABILISTIC_ADVANTAGE_AND_FALL_BACK_TO_CRITICAL_PATH"
            ),
            "hard_nonclaims": [
                "NO_ACCEPTANCE_CREDIT",
                "NO_SCORE_INFERENCE",
                "NO_CAPABILITY_CREDIT",
                "NO_FRESH_REALITY_AUTHORITY",
                "NO_CLAIM_GREEDY_INDEX_IS_GLOBALLY_OPTIMAL_UNDER_ARBITRARY_DEPENDENCIES",
            ],
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "fresh_reality_authority": False,
            "promotion_authority": False,
        }
    except SettlementSchedulerError as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "ranked_actions": [],
            "blocked_fresh_reality_actions": [],
            "acceptance_credit_delta": 0,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
            "execution_authority": False,
            "fresh_reality_authority": False,
            "promotion_authority": False,
        }
