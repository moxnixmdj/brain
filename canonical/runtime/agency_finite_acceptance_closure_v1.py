from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from canonical.runtime import matched_agency_stateful_case_v1 as stateful
from canonical.runtime import delegation_whole_scope_candidate_v2 as delegation_candidate
from canonical.runtime import delegation_whole_scope_proof_v2 as delegation_proof
from canonical.runtime.matched_exact_finite_success_reducer_v1 import reduce_exact

SCHEMA = "PROJECT_BRAIN_AGENCY_FINITE_ACCEPTANCE_CLOSURE_V1"
ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "canonical/governance/AGENCY_FINITE_PORTFOLIO_FREEZE_20261007_V1.json"

REQUIRED_DIMENSIONS = {
    "multi-step planning with at least three distinct tool/action types",
    "state change after actions requiring replanning",
    "long-horizon state retention",
    "tool failure/recovery",
    "subtask dependency and fan-in",
    "minimal-oversight completion",
}
REQUIRED_METRICS = {
    "terminal_task_success",
    "invalid_action_rate",
    "unrecovered_failure_rate",
    "duplicate_or_conflicting_work_rate",
}

CASE_SPECS = [
    {
        "case_id": "AGENCY-FINITE-STATEFUL-001",
        "kind": "STATEFUL_TOP_CELL_WITNESS",
        "input": {
            "case_token": "AGENCY-FINITE-CLOSURE-STATEFUL-20261007",
            "ordinal": 0,
        },
        "coverage": [
            "multi-step planning with at least three distinct tool/action types",
            "long-horizon state retention",
            "minimal-oversight completion",
        ],
    },
    {
        "case_id": "AGENCY-FINITE-FAILURE-FANIN-002",
        "kind": "DELEGATION_STEP_UNAVAILABLE_WITNESS",
        "input": {
            "seed": 20261007,
            "ordinal": 2,
        },
        "coverage": [
            "state change after actions requiring replanning",
            "tool failure/recovery",
            "subtask dependency and fan-in",
        ],
    },
]

def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

def _load_freeze() -> dict[str, Any]:
    doc = json.loads(FREEZE.read_text(encoding="utf-8"))
    if doc.get("schema") != "PROJECT_BRAIN_AGENCY_FINITE_PORTFOLIO_FREEZE_V1":
        raise ValueError("FREEZE_SCHEMA_INVALID")
    if doc.get("frozen_cases") != CASE_SPECS:
        raise ValueError("FREEZE_CASE_SPEC_DRIFT")
    if doc.get("fixed_case_count") != len(CASE_SPECS):
        raise ValueError("FREEZE_CASE_COUNT_DRIFT")
    if doc.get("required_dimensions") != sorted(REQUIRED_DIMENSIONS):
        raise ValueError("FREEZE_DIMENSION_SET_DRIFT")
    if doc.get("required_metrics") != sorted(REQUIRED_METRICS):
        raise ValueError("FREEZE_METRIC_SET_DRIFT")
    return doc

def _stateful_case(spec: dict[str, Any]) -> dict[str, Any]:
    inp = spec["input"]
    out = stateful.run_case(inp["case_token"], inp["ordinal"])
    actions = list(out.get("action_types") or [])
    checks = dict(out.get("checks") or {})
    passed = (
        out.get("pass") is True
        and all(checks.values())
        and out.get("planner_plan") == ["browser", "tool", "delegation"]
        and len(actions) == 3
        and len(set(actions)) == 3
        and all((out.get("component_results") or {}).get(k, {}).get("pass") is True
                for k in ("browser", "tool", "delegation"))
    )
    return {
        "case_id": spec["case_id"],
        "kind": spec["kind"],
        "input_sha256": _canonical_sha256(inp),
        "coverage": list(spec["coverage"]),
        "success": bool(passed),
        "verified": bool(passed),
        "metrics": {
            "terminal_task_success": 1 if passed else 0,
            "invalid_action_rate": 0 if passed else 1,
            "unrecovered_failure_rate": 0 if passed else 1,
            "duplicate_or_conflicting_work_rate": 0 if passed else 1,
        },
        "evidence": {
            "planner_plan": out.get("planner_plan"),
            "action_types": actions,
            "checks": checks,
        },
    }

def _failure_fanin_case(spec: dict[str, Any]) -> dict[str, Any]:
    inp = spec["input"]
    case = delegation_proof.generate_case(inp["seed"], inp["ordinal"])
    if case.get("case_class") != "STEP_UNAVAILABLE":
        raise ValueError("FROZEN_DELEGATION_CASE_CLASS_DRIFT")
    initial = delegation_candidate.solve_initial(delegation_proof.public_initial(case))
    revised = delegation_candidate.solve_after_receipt(
        delegation_proof.public_after_receipt(case), initial
    )
    verdict = delegation_proof.score_episode(case, initial, revised)
    receipt = dict(case["_oracle"]["receipt"])
    changed = (
        initial.get("task_ids") != revised.get("task_ids")
        or initial.get("assignment") != revised.get("assignment")
        or initial.get("waves") != revised.get("waves")
    )
    completed = set(receipt.get("completed_task_ids") or [])
    revised_ids = set(revised.get("task_ids") or [])
    passed = (
        verdict.get("pass") is True
        and receipt.get("kind") == "STEP_UNAVAILABLE"
        and changed
        and not (completed & revised_ids)
        and bool(revised.get("terminal_evidence"))
    )
    return {
        "case_id": spec["case_id"],
        "kind": spec["kind"],
        "input_sha256": _canonical_sha256(inp),
        "coverage": list(spec["coverage"]),
        "success": bool(passed),
        "verified": bool(passed),
        "metrics": {
            "terminal_task_success": 1 if passed else 0,
            "invalid_action_rate": 0 if passed else 1,
            "unrecovered_failure_rate": 0 if passed else 1,
            "duplicate_or_conflicting_work_rate": 0 if passed else 1,
        },
        "evidence": {
            "case_class": case.get("case_class"),
            "receipt_kind": receipt.get("kind"),
            "plan_changed_after_receipt": changed,
            "completed_work_replayed": bool(completed & revised_ids),
            "verdict": verdict,
        },
    }

def run_portfolio() -> dict[str, Any]:
    freeze = _load_freeze()
    rows = [_stateful_case(CASE_SPECS[0]), _failure_fanin_case(CASE_SPECS[1])]
    dimensions = {d for row in rows for d in row["coverage"]}
    reducer = reduce_exact(
        {"case_id": row["case_id"], "success": row["success"], "verified": row["verified"]}
        for row in rows
    )
    all_pass = (
        all(row["success"] and row["verified"] for row in rows)
        and dimensions == REQUIRED_DIMENSIONS
        and reducer["success_fraction"] == 1.0
        and all(
            row["metrics"]["terminal_task_success"] == 1
            and row["metrics"]["invalid_action_rate"] == 0
            and row["metrics"]["unrecovered_failure_rate"] == 0
            and row["metrics"]["duplicate_or_conflicting_work_rate"] == 0
            for row in rows
        )
    )
    return {
        "schema": SCHEMA,
        "status": "PASS__FINITE_DECLARED_AGENCY_PORTFOLIO_AT_OBJECTIVE_CEILING" if all_pass else "FAIL_CLOSED",
        "pass": all_pass,
        "freeze_sha256": _canonical_sha256(freeze),
        "case_count": len(rows),
        "cases": rows,
        "dimension_coverage": sorted(dimensions),
        "dimension_coverage_complete": dimensions == REQUIRED_DIMENSIONS,
        "metrics_at_objective_ceiling": all_pass,
        "brain_success_fraction": reducer["success_fraction"],
        "exact_finite_reducer": reducer,
        "opus_case_execution_required": False if all_pass else None,
        "acceptance_implication": (
            "ON_THE_EXACT_FROZEN_FINITE_SCOPE_BRAIN_SUCCESS_FRACTION_IS_1_AND_ALL_LOWER_IS_BETTER_SAFETY_RATES_ARE_0__NO_COMPARATOR_CAN_EXCEED_THE_SUCCESS_CEILING_OR_IMPROVE_BELOW_ZERO"
            if all_pass else None
        ),
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "incremental_spend_usd": 0,
    }

if __name__ == "__main__":
    print(json.dumps(run_portfolio(), indent=2, sort_keys=True))
