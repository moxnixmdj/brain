"""Fail-closed robust lower-bound compiler for FrontierCode-style weighted scoring.

Published FrontierCode semantics:
- a run that fails a blocker can receive score 0;
- a passing run's score is a weighted aggregate of rubric items;
- benchmark score averages runs.

Therefore, under hidden blocker sets / hidden rubric weights, the only sound positive
lower bound is the sum of *independently certified* passed-weight lower bounds for
cells whose blocker pass is also independently certified.

Unknown blocker status => robust lower bound 0 for that cell.
Unknown passed-weight mass => robust lower bound 0 for that cell.

This compiler performs arithmetic only. It does not validate the truth of external
certificates and grants no acceptance or promotion authority.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FRONTIERCODE_ROBUST_SCORE_LOWER_BOUND_V1"


def _plain(d: Decimal) -> str:
    """Canonical non-exponent decimal string with insignificant zeros removed."""
    if d == 0:
        return "0"
    return format(d.normalize(), "f")


def _d(value: Any, label: str, errors: list[str]) -> Decimal | None:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        errors.append(f"{label}_INVALID_DECIMAL")
        return None
    if not d.is_finite():
        errors.append(f"{label}_NONFINITE")
        return None
    return d


def _receipt(obj: Any, label: str, errors: list[str]) -> bool:
    if not isinstance(obj, Mapping):
        errors.append(f"{label}_RECEIPT_NOT_OBJECT")
        return False
    ok = True
    if obj.get("verified") is not True:
        errors.append(f"{label}_RECEIPT_NOT_VERIFIED")
        ok = False
    if obj.get("independent") is not True:
        errors.append(f"{label}_RECEIPT_NOT_INDEPENDENT")
        ok = False
    path = obj.get("source_path")
    sha = obj.get("source_sha")
    if not isinstance(path, str) or not path.strip():
        errors.append(f"{label}_RECEIPT_PATH_MISSING")
        ok = False
    if not isinstance(sha, str) or len(sha.strip()) < 7:
        errors.append(f"{label}_RECEIPT_SHA_MISSING")
        ok = False
    return ok


def evaluate(payload: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "errors": ["INPUT_NOT_OBJECT"],
            "promotion_authority": False,
            "terminal_credit_delta": 0,
        }

    target = _d(payload.get("target_score_fraction"), "TARGET_SCORE", errors)
    task_count = payload.get("task_count")
    trials_per_task = payload.get("trials_per_task")

    if not isinstance(task_count, int) or isinstance(task_count, bool) or task_count <= 0:
        errors.append("TASK_COUNT_INVALID")
        task_count = 0
    if not isinstance(trials_per_task, int) or isinstance(trials_per_task, bool) or trials_per_task <= 0:
        errors.append("TRIALS_PER_TASK_INVALID")
        trials_per_task = 0
    if target is not None and not (Decimal("0") <= target <= Decimal("1")):
        errors.append("TARGET_SCORE_OUT_OF_RANGE")

    expected_cells = task_count * trials_per_task

    groups = payload.get("groups")
    if not isinstance(groups, list) or not groups:
        errors.append("GROUPS_INVALID_OR_EMPTY")
        groups = []

    total_multiplicity = 0
    numerator = Decimal("0")
    normalized_groups = []

    for i, row in enumerate(groups):
        local: list[str] = []
        if not isinstance(row, Mapping):
            errors.append(f"GROUP_NOT_OBJECT:{i}")
            continue

        gid = row.get("group_id")
        if not isinstance(gid, str) or not gid.strip():
            local.append("GROUP_ID_INVALID")
            gid = f"INVALID::{i}"

        multiplicity = row.get("multiplicity")
        if not isinstance(multiplicity, int) or isinstance(multiplicity, bool) or multiplicity <= 0:
            local.append("MULTIPLICITY_INVALID")
            multiplicity = 0

        blockers_proved = row.get("all_blockers_pass_proved") is True
        blocker_receipt_ok = False
        if blockers_proved:
            blocker_receipt_ok = _receipt(
                row.get("blocker_pass_receipt"),
                f"GROUP:{gid}:BLOCKER_PASS",
                local,
            )

        lb = _d(
            row.get("passed_rubric_weight_lower_bound", 0),
            f"GROUP:{gid}:PASSED_WEIGHT_LB",
            local,
        )
        if lb is not None and not (Decimal("0") <= lb <= Decimal("1")):
            local.append("PASSED_WEIGHT_LB_OUT_OF_RANGE")

        weight_receipt_ok = False
        if lb is not None and lb > 0:
            weight_receipt_ok = _receipt(
                row.get("passed_weight_receipt"),
                f"GROUP:{gid}:PASSED_WEIGHT",
                local,
            )

        # Robust worst case:
        # - if blocker pass is not proved, score can be zero;
        # - if passed weight mass is not independently proved, known mass is zero.
        certified_lb = Decimal("0")
        if (
            blockers_proved
            and blocker_receipt_ok
            and lb is not None
            and lb >= 0
            and lb <= 1
            and (lb == 0 or weight_receipt_ok)
        ):
            certified_lb = lb

        total_multiplicity += multiplicity
        numerator += Decimal(multiplicity) * certified_lb

        for e in local:
            errors.append(e)

        normalized_groups.append({
            "group_id": gid,
            "multiplicity": multiplicity,
            "all_blockers_pass_proved": blockers_proved and blocker_receipt_ok,
            "certified_score_lower_bound_fraction": _plain(certified_lb),
        })

    if expected_cells and total_multiplicity != expected_cells:
        errors.append(
            f"GROUP_MULTIPLICITY_SUM_MISMATCH:EXPECTED_{expected_cells}:GOT_{total_multiplicity}"
        )

    lower_bound = (
        numerator / Decimal(expected_cells)
        if expected_cells > 0 and total_multiplicity == expected_cells
        else Decimal("0")
    )

    arithmetic_valid = not errors
    threshold_met = (
        arithmetic_valid
        and target is not None
        and lower_bound >= target
    )

    return {
        "schema": SCHEMA,
        "pass": arithmetic_valid,
        "status": (
            "CERTIFIED_ROBUST_LOWER_BOUND_MEETS_TARGET__EXTERNAL_CERTIFICATE_TRUTH_STILL_SEPARATE"
            if threshold_met
            else (
                "VALID_ROBUST_LOWER_BOUND_BELOW_TARGET"
                if arithmetic_valid
                else "FAIL_CLOSED"
            )
        ),
        "task_count": task_count,
        "trials_per_task": trials_per_task,
        "expected_cell_count": expected_cells,
        "covered_cell_count": total_multiplicity,
        "target_score_fraction": _plain(target) if target is not None else None,
        "robust_score_lower_bound_fraction": _plain(lower_bound),
        "robust_score_lower_bound_percent": _plain(lower_bound * Decimal("100")),
        "target_met_by_robust_lower_bound": threshold_met,
        "groups": normalized_groups,
        "errors": sorted(set(errors)),
        "minimum_missing_information_rule": (
            "TO_RAISE_THE_LOWER_BOUND_ABOVE_ZERO__PROVE_BLOCKER_PASS_AND_A_POSITIVE_"
            "NORMALIZED_PASSED_RUBRIC_WEIGHT_LOWER_BOUND_FOR_SOME_CELLS__"
            "TO_REACH_TARGET__THE_MULTIPLICITY_WEIGHTED_SUM_OF_CERTIFIED_CELL_LOWER_BOUNDS_"
            "MUST_REACH_TARGET_TIMES_TOTAL_CELLS"
        ),
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
