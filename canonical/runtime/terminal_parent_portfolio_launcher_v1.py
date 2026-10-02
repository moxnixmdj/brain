"""Fail-closed route-specific parent launcher for the four terminal portfolios.

This module contains no domain scorer and no success thresholds. It composes the
already-frozen route-specific executors, requires load-bearing parent-portfolio
instrumentation receipts for every multiplex binding, deduplicates shared direct
routes, and refuses to launch if the runtime route algebra drifts.

It does not create a post-freeze beacon. The caller supplies the frozen candidate
package commitment and beacon after PREPARE has closed.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import direct_route_terminal_executors_v1 as direct
from canonical.runtime import cad_t0_route_specific_terminal_executor_v1 as cad
from canonical.runtime import portfolio_multiplex_terminal_instrumentation_v1 as multiplex
from canonical.runtime import terminal_wave_launch_authority_reducer_v1 as launch_authority
from canonical.runtime import terminal_parent_portfolio_runner_v1 as parent_runner
from canonical.runtime import terminal_parent_portfolio_runner_v1 as parent_portfolio_runner

SCHEMA = "PROJECT_BRAIN_TERMINAL_PARENT_PORTFOLIO_LAUNCHER_V1"
PORTFOLIOS = ("T0", "T1", "T2", "T3")

CAD_ID = cad.BEHAVIOR_ID

DIRECT_PORTFOLIOS: dict[str, tuple[str, ...]] = {
    direct.SA_CCR_ID: ("T1",),
    direct.BROWSER_ID: ("T2",),
    direct.DELEGATION_ID: ("T2",),
    direct.TOOL_ID: ("T2", "T3"),
    direct.RESEARCH_ID: ("T3",),
    CAD_ID: ("T0",),
}

EXPECTED_ACTIVE_CONTRACT_COUNT = 12


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(label + "_REQUIRED")
    return value


def static_route_preflight() -> dict[str, Any]:
    """Derive executor coverage from live imported route tables, never stored counters."""
    direct_ids = set(direct.bound_behavior_ids()) | {CAD_ID}
    multiplex_ids = set(multiplex.bound_behavior_ids())
    union = direct_ids | multiplex_ids
    overlap = direct_ids & multiplex_ids
    errors: list[str] = []

    if set(DIRECT_PORTFOLIOS) != direct_ids:
        errors.append("DIRECT_PORTFOLIO_MAP_DRIFT")
    if union != direct_ids | multiplex_ids:
        errors.append("INTERNAL_UNION_ERROR")
    if len(union) != EXPECTED_ACTIVE_CONTRACT_COUNT:
        errors.append("ACTIVE_CONTRACT_COUNT_MISMATCH")
    if overlap != {CAD_ID}:
        errors.append("DIRECT_MULTIPLEX_OVERLAP_MISMATCH")
    if set(PORTFOLIOS) != {
        p for portfolios in DIRECT_PORTFOLIOS.values() for p in portfolios
    }:
        errors.append("DIRECT_PORTFOLIO_COVERAGE_MISMATCH")

    for behavior_id, binding in multiplex.BINDINGS.items():
        portfolios = tuple(binding.get("portfolios") or ())
        if not portfolios or any(p not in PORTFOLIOS for p in portfolios):
            errors.append("MULTIPLEX_PORTFOLIO_BINDING_INVALID:" + behavior_id)

    return {
        "schema": SCHEMA,
        "pass": not errors,
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "direct_behavior_ids": sorted(direct_ids),
        "multiplex_behavior_ids": sorted(multiplex_ids),
        "unique_active_behavior_ids": sorted(union),
        "direct_multiplex_overlap": sorted(overlap),
        "active_contract_count": len(union),
        "errors": sorted(set(errors)),
        "terminal_result": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def build_launch_plan() -> dict[str, Any]:
    preflight = static_route_preflight()
    if not preflight["pass"]:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_PREPARE",
            "pass": False,
            "preflight": preflight,
            "terminal_result": False,
        }

    portfolios: dict[str, dict[str, list[str]]] = {
        p: {"direct": [], "multiplex": []} for p in PORTFOLIOS
    }
    for behavior_id, parents in DIRECT_PORTFOLIOS.items():
        for portfolio in parents:
            portfolios[portfolio]["direct"].append(behavior_id)
    for behavior_id, binding in multiplex.BINDINGS.items():
        for portfolio in binding["portfolios"]:
            portfolios[portfolio]["multiplex"].append(behavior_id)
    for portfolio in portfolios:
        portfolios[portfolio]["direct"].sort()
        portfolios[portfolio]["multiplex"].sort()

    return {
        "schema": SCHEMA,
        "status": "READY",
        "pass": True,
        "preflight": preflight,
        "portfolios": portfolios,
        "unique_direct_routes": sorted(DIRECT_PORTFOLIOS),
        "direct_route_execution_count": len(DIRECT_PORTFOLIOS),
        "shared_direct_routes_deduplicated": [
            behavior_id
            for behavior_id, parents in sorted(DIRECT_PORTFOLIOS.items())
            if len(parents) > 1
        ],
        "post_freeze_beacon_required": True,
        "terminal_result": False,
    }


def validate_parent_receipts(
    parent_receipts: Mapping[str, list[Mapping[str, Any]]],
    *,
    commitment: str,
    beacon: str,
) -> dict[str, Any]:
    _require_text(commitment, "COMMITMENT")
    _require_text(beacon, "BEACON")
    errors: list[str] = []
    by_behavior: dict[str, list[Mapping[str, Any]]] = defaultdict(list)

    if not isinstance(parent_receipts, Mapping):
        raise ValueError("PARENT_RECEIPTS_MAPPING_REQUIRED")

    for portfolio in PORTFOLIOS:
        rows = parent_receipts.get(portfolio)
        if not isinstance(rows, list):
            errors.append("PARENT_PORTFOLIO_RECEIPTS_REQUIRED:" + portfolio)
            continue
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                errors.append(f"PARENT_RECEIPT_NOT_MAPPING:{portfolio}:{index}")
                continue
            behavior_id = row.get("behavior_id")
            binding = multiplex.BINDINGS.get(behavior_id)
            if binding is None:
                errors.append(f"UNBOUND_PARENT_BEHAVIOR:{portfolio}:{index}:{behavior_id}")
                continue
            if portfolio not in binding["portfolios"]:
                errors.append(f"PARENT_BEHAVIOR_WRONG_PORTFOLIO:{portfolio}:{behavior_id}")
            if row.get("candidate_package_commitment") != commitment:
                errors.append(f"PARENT_COMMITMENT_MISMATCH:{portfolio}:{behavior_id}")
            if row.get("post_freeze_beacon") != beacon:
                errors.append(f"PARENT_BEACON_MISMATCH:{portfolio}:{behavior_id}")
            checked = multiplex.validate_parent_observation(behavior_id, row)
            if not checked["valid"]:
                errors.extend(
                    f"PARENT_RECEIPT_INVALID:{portfolio}:{behavior_id}:{err}"
                    for err in checked["errors"]
                )
            by_behavior[str(behavior_id)].append(row)

    reductions: dict[str, dict[str, Any]] = {}
    for behavior_id, binding in sorted(multiplex.BINDINGS.items()):
        rows = by_behavior.get(behavior_id, [])
        for portfolio in binding["portfolios"]:
            load_bearing = [
                row
                for row in rows
                if row.get("portfolio") == portfolio and row.get("load_bearing") is True
            ]
            if not load_bearing:
                errors.append(
                    "MISSING_LOAD_BEARING_PARENT_COVERAGE:"
                    + behavior_id
                    + ":"
                    + portfolio
                )
        if rows:
            reductions[behavior_id] = multiplex.reduce_behavior_receipts(
                behavior_id, list(rows)
            )
            if reductions[behavior_id]["status"] != "PASS_COMPONENT":
                errors.append("MULTIPLEX_REDUCTION_FAIL:" + behavior_id)
        else:
            errors.append("MULTIPLEX_BEHAVIOR_RECEIPTS_MISSING:" + behavior_id)

    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "reductions": reductions,
        "errors": sorted(set(errors)),
        "terminal_result_component": True,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def execute_wave(
    *,
    commitment: str,
    beacon: str,
    root: Path = Path("."),
) -> dict[str, Any]:
    """Execute the canonical V2 terminal wave with no injectable executors.

    The exact verified direct executors are run once first.  Their results cannot
    alter any candidate/runtime path; only the exact CAD result is passed to the
    canonical parent producer because the frozen T0 binding requires deduplicated
    reuse of that same 128-case CAD population.

    All four parent portfolios are then executed regardless of behavioral pass/
    fail so started-wave evidence is not selectively truncated.  Results compile
    only after all direct and parent routes terminate.
    """
    _require_text(commitment, "COMMITMENT")
    _require_text(beacon, "BEACON")

    authority = launch_authority.evaluate(root)
    if authority.get("launch_authority") is not True:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_LAUNCH_NOT_AUTHORIZED",
            "pass": False,
            "launch_authority": authority,
            "parent_runner_invoked": False,
            "direct_runner_invoked": False,
            "terminal_result": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    plan = build_launch_plan()
    if not plan["pass"]:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_PREPARE",
            "pass": False,
            "plan": plan,
            "terminal_result": False,
        }

    # Canonical verified direct executors only.  No caller-supplied replacement
    # can cross this launch boundary.
    direct_results: dict[str, dict[str, Any]] = {}
    for behavior_id in sorted(DIRECT_PORTFOLIOS):
        if behavior_id == CAD_ID:
            result = cad.execute_cad_route(
                commitment=commitment,
                beacon=beacon,
                root=root,
            )
        else:
            result = direct.execute_direct_route(
                behavior_id,
                commitment=commitment,
                beacon=beacon,
            )
        direct_results[behavior_id] = result

    direct_failures = sorted(
        behavior_id
        for behavior_id, result in direct_results.items()
        if result.get("pass") is not True or result.get("terminal_result") is not True
    )

    # The parent producer is allowed to see only the exact CAD direct result,
    # never unrelated terminal outcomes.  That is evidence reuse, not runtime
    # feedback: no candidate path is changed by CAD success/failure.
    cad_context = {CAD_ID: direct_results[CAD_ID]}
    parent_receipts: dict[str, list[Mapping[str, Any]]] = {}
    parent_runner_errors: list[str] = []
    for portfolio in PORTFOLIOS:
        try:
            rows = parent_runner.execute_parent_portfolio(
                portfolio,
                commitment=commitment,
                beacon=beacon,
                direct_results=cad_context,
            )
            parent_receipts[portfolio] = list(rows)
        except Exception as exc:
            parent_receipts[portfolio] = []
            parent_runner_errors.append(
                portfolio + ":" + type(exc).__name__ + ":" + str(exc)
            )

    parent = validate_parent_receipts(
        parent_receipts,
        commitment=commitment,
        beacon=beacon,
    )
    errors = list(parent_runner_errors)
    errors.extend(parent.get("errors") or [])

    ok = not direct_failures and parent["pass"] and not parent_runner_errors
    return {
        "schema": SCHEMA,
        "status": "PASS" if ok else "FAIL_CLOSED",
        "pass": ok,
        "plan": plan,
        "launch_authority": authority,
        "parent_portfolio_receipts": parent_receipts,
        "parent_reduction": parent,
        "parent_runner_errors": parent_runner_errors,
        "direct_results": direct_results,
        "direct_failures": direct_failures,
        "direct_routes_executed_once": sorted(direct_results),
        "shared_direct_route_duplicate_execution_count": 0,
        "canonical_parent_runner_only": True,
        "canonical_direct_runners_only": True,
        "cad_parent_reuses_exact_direct_result": True,
        "no_case_replacement": True,
        "no_tuning_replay": True,
        "result_to_runtime_feedback_during_wave": False,
        "errors": sorted(set(errors)),
        "terminal_result": True,
        "capability_credit_delta": "DEFER_TO_TERMINAL_REDUCER",
        "family_credit_delta": "DEFER_TO_TERMINAL_REDUCER",
    }
