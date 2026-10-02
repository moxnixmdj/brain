"""Fail-closed autocompiler for objective terminal proof-route materialization.

The compiler converts a complete objective-oracle contract into the smallest
zero-terminal-evidence materialization plan justified by the current route-gate
state. It never invents semantics, never executes terminal cases, and never
grants execution, promotion, capability, or family credit.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_OBJECTIVE_ORACLE_DOMINANCE_INPUT_V1"
OUT_SCHEMA = "PROJECT_BRAIN_TERMINAL_PROOF_ROUTE_AUTOCOMPILE_V1"

GATE_ORDER = (
    "candidate_package_frozen",
    "executable_evaluator_bound",
    "population_or_source_pool_frozen",
    "information_boundary_frozen",
    "post_freeze_selector_frozen",
    "terminal_parent_binding_frozen",
    "independent_verification_pass",
)

ACTION_BY_GATE = {
    "candidate_package_frozen": "FREEZE_CANDIDATE_PACKAGE",
    "executable_evaluator_bound": "BIND_EXECUTABLE_EVALUATOR",
    "population_or_source_pool_frozen": "FREEZE_HIDDEN_POPULATION_OR_SOURCE_POOL",
    "information_boundary_frozen": "FREEZE_INFORMATION_BOUNDARY",
    "post_freeze_selector_frozen": "FREEZE_POST_FREEZE_SELECTOR",
    "terminal_parent_binding_frozen": "BIND_TERMINAL_PARENT_PORTFOLIO",
    "independent_verification_pass": "RUN_INDEPENDENT_EXACT_BLOB_VERIFICATION",
}


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": OUT_SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def _is_real_evidence_ref(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value != "NEW_TERMINAL_OBJECTIVE_ORACLE_COMPONENT_REQUIRED"
    )


def _compile_contract(row: Mapping[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    bid = row.get("behavior_id")
    if not isinstance(bid, str) or not bid:
        return None, ["BEHAVIOR_ID_INVALID"]

    required = row.get("required_dimensions")
    dimensions = row.get("dimensions")
    gates = row.get("route_gates")
    if not isinstance(required, list) or not required:
        errors.append(f"{bid}:REQUIRED_DIMENSIONS_INVALID")
        required = []
    if any(not isinstance(x, str) or not x for x in required):
        errors.append(f"{bid}:REQUIRED_DIMENSION_ID_INVALID")
    if len(set(required)) != len(required):
        errors.append(f"{bid}:REQUIRED_DIMENSIONS_DUPLICATE")
    if not isinstance(dimensions, list):
        errors.append(f"{bid}:DIMENSIONS_INVALID")
        dimensions = []
    if not isinstance(gates, Mapping):
        errors.append(f"{bid}:ROUTE_GATES_INVALID")
        gates = {}

    by_id: dict[str, Mapping[str, Any]] = {}
    for i, d in enumerate(dimensions):
        if not isinstance(d, Mapping):
            errors.append(f"{bid}:DIMENSION_NOT_OBJECT:{i}")
            continue
        did = d.get("id")
        if not isinstance(did, str) or not did:
            errors.append(f"{bid}:DIMENSION_ID_INVALID:{i}")
            continue
        if did in by_id:
            errors.append(f"{bid}:DIMENSION_DUPLICATE:{did}")
            continue
        by_id[did] = d

    missing = sorted(set(required) - set(by_id))
    extra = sorted(set(by_id) - set(required))
    if extra:
        errors.append(f"{bid}:UNDECLARED_DIMENSIONS:" + ",".join(extra))

    semantic_gaps: list[dict[str, Any]] = []
    evaluator_gaps: list[str] = []
    evidence_refs: list[dict[str, str]] = []
    for did in required:
        d = by_id.get(did)
        if d is None:
            semantic_gaps.append({"dimension": did, "reasons": ["MISSING_DIMENSION"]})
            continue
        reasons = []
        if d.get("objective") is not True:
            reasons.append("NOT_OBJECTIVE")
        if d.get("falsifiable") is not True:
            reasons.append("NOT_FALSIFIABLE")
        if d.get("hidden_from_candidate") is not True:
            reasons.append("ORACLE_NOT_HIDDEN")
        if d.get("terminal_load_bearing") is not True:
            reasons.append("NOT_TERMINAL_LOAD_BEARING")
        mechanism = d.get("mechanism")
        if not isinstance(mechanism, str) or not mechanism:
            reasons.append("MECHANISM_UNDEFINED")
        if reasons:
            semantic_gaps.append({"dimension": did, "reasons": sorted(reasons)})
        ev = d.get("existing_evidence")
        if _is_real_evidence_ref(ev):
            evidence_refs.append({"dimension": did, "evidence": ev})
        else:
            evaluator_gaps.append(did)

    if row.get("candidate_receives_hidden_oracle") is not False:
        errors.append(f"{bid}:HIDDEN_ORACLE_BOUNDARY_INVALID")

    gate_state: dict[str, bool] = {}
    open_gates: list[str] = []
    for gate in GATE_ORDER:
        gate_state[gate] = gates.get(gate) is True
        if not gate_state[gate]:
            open_gates.append(gate)

    semantic_complete = not missing and not semantic_gaps and not errors
    evaluator_coverage_complete = semantic_complete and not evaluator_gaps
    actions = []
    if semantic_complete:
        for gate in open_gates:
            if gate == "executable_evaluator_bound" and not evaluator_coverage_complete:
                continue
            actions.append(
                {
                    "behavior_id": bid,
                    "gate": gate,
                    "action": ACTION_BY_GATE[gate],
                    "new_terminal_reality_units": 0,
                    "terminal_case_execution_required": False,
                }
            )

    return {
        "behavior_id": bid,
        "semantic_contract_complete": semantic_complete,
        "missing_dimensions": missing,
        "semantic_gaps": semantic_gaps,
        "evaluator_coverage_complete": evaluator_coverage_complete,
        "evaluator_gaps": sorted(evaluator_gaps),
        "evidence_refs": evidence_refs,
        "route_gates": gate_state,
        "open_route_gates": open_gates,
        "zero_reality_materialization_actions": actions,
        "route_ready_for_existing_promotion_law": semantic_complete
        and evaluator_coverage_complete
        and not open_gates,
        "weaker_comparator_dependency": row.get("weaker_comparator_dependency"),
    }, errors


def compile_routes(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("INPUT_NOT_OBJECT")
    if payload.get("schema") != SCHEMA:
        return _fail("SCHEMA_INVALID")
    contracts = payload.get("contracts")
    if not isinstance(contracts, list) or not contracts:
        return _fail("CONTRACTS_INVALID")

    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for i, raw in enumerate(contracts):
        if not isinstance(raw, Mapping):
            errors.append(f"CONTRACT_NOT_OBJECT:{i}")
            continue
        row, row_errors = _compile_contract(raw)
        errors.extend(row_errors)
        if row is None:
            continue
        bid = row["behavior_id"]
        if bid in seen:
            errors.append(f"BEHAVIOR_ID_DUPLICATE:{bid}")
        seen.add(bid)
        rows.append(row)

    if errors:
        return {**_fail(*errors), "contracts": rows}

    shared: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        for ref in row["evidence_refs"]:
            shared[ref["evidence"]].append(
                {"behavior_id": row["behavior_id"], "dimension": ref["dimension"]}
            )
    shared_basis = [
        {
            "evidence": evidence,
            "uses": uses,
            "reuse_count": len(uses),
            "reuse_authority": "EXACT_EVIDENCE_REFERENCE_ONLY__NO_SEMANTIC_PROJECTION",
        }
        for evidence, uses in sorted(shared.items())
        if len(uses) > 1
    ]

    actions = [
        action
        for row in rows
        for action in row["zero_reality_materialization_actions"]
    ]
    evaluator_gap_count = sum(len(row["evaluator_gaps"]) for row in rows)
    semantic_gap_count = sum(
        len(row["semantic_gaps"]) + len(row["missing_dimensions"]) for row in rows
    )
    ready = [
        row["behavior_id"] for row in rows if row["route_ready_for_existing_promotion_law"]
    ]

    return {
        "schema": OUT_SCHEMA,
        "status": (
            "ALL_ROUTES_MATERIALIZED_PENDING_EXISTING_PROMOTION_LAW"
            if len(ready) == len(rows)
            else "ZERO_REALITY_ROUTE_MATERIALIZATION_PLAN_COMPILED"
            if semantic_gap_count == 0
            else "SEMANTIC_GAPS_BLOCK_AUTOCOMPILE"
        ),
        "pass": True,
        "exact": True,
        "contracts": rows,
        "shared_evaluator_basis": shared_basis,
        "semantic_gap_count": semantic_gap_count,
        "evaluator_gap_count": evaluator_gap_count,
        "zero_reality_materialization_action_count": len(actions),
        "zero_reality_materialization_actions": actions,
        "route_ready_behavior_ids": sorted(ready),
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "rule": (
            "AUTOCOMPILE_ONLY_FROM_FROZEN_OBJECTIVE_SEMANTICS_AND_EXISTING_EVIDENCE__"
            "NEVER_INVENT_SEMANTIC_TRUTH__NEVER_EXECUTE_TERMINAL_CASES__"
            "NEVER_PROMOTE_FROM_COMPILER_OUTPUT_ALONE"
        ),
        "errors": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    args = ap.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    out = compile_routes(payload)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
