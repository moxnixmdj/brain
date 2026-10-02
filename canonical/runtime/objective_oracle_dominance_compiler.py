"""Fail-closed compiler for contract-complete objective-oracle dominance.

This compiler never grants terminal, execution, promotion, capability, or family credit.
It answers two narrower questions:

1. Is every declared behavioral success dimension mapped to an objective,
   falsifiable, hidden-evaluator mechanism?
2. If so, which concrete prewave gates still prevent replacing a weaker
   exact-model comparator dependency with that direct behavioral proof route?

A structurally complete objective route may make an external comparator
logically unnecessary, but deletion is authorized only after every frozen-route
gate and independent verification are explicitly true.
"""
from __future__ import annotations

import argparse
import json
from typing import Any, Mapping
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_OBJECTIVE_ORACLE_DOMINANCE_INPUT_V1"
VERDICT_SCHEMA = "PROJECT_BRAIN_OBJECTIVE_ORACLE_DOMINANCE_VERDICT_V1"

REQUIRED_ROUTE_GATES = (
    "candidate_package_frozen",
    "executable_evaluator_bound",
    "population_or_source_pool_frozen",
    "information_boundary_frozen",
    "post_freeze_selector_frozen",
    "terminal_parent_binding_frozen",
    "independent_verification_pass",
)

def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": VERDICT_SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }

def _contract(row: Mapping[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    bid = row.get("behavior_id")
    if not isinstance(bid, str) or not bid:
        return None, ["BEHAVIOR_ID_INVALID"]

    req = row.get("required_dimensions")
    dims = row.get("dimensions")
    gates = row.get("route_gates")
    if not isinstance(req, list) or not req or any(not isinstance(x, str) or not x for x in req):
        errors.append(f"{bid}:REQUIRED_DIMENSIONS_INVALID")
        req = []
    if len(set(req)) != len(req):
        errors.append(f"{bid}:REQUIRED_DIMENSIONS_DUPLICATE")
    if not isinstance(dims, list):
        errors.append(f"{bid}:DIMENSIONS_NOT_LIST")
        dims = []
    if not isinstance(gates, Mapping):
        errors.append(f"{bid}:ROUTE_GATES_INVALID")
        gates = {}

    by_id: dict[str, Mapping[str, Any]] = {}
    for i, d in enumerate(dims):
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

    extra = sorted(set(by_id) - set(req))
    if extra:
        errors.append(f"{bid}:UNDECLARED_DIMENSIONS:" + ",".join(extra))

    missing = sorted(set(req) - set(by_id))
    covered: list[str] = []
    incomplete: list[dict[str, Any]] = []
    for did in req:
        d = by_id.get(did)
        if d is None:
            incomplete.append({"id": did, "reasons": ["NO_OBJECTIVE_MAPPING"]})
            continue
        reasons: list[str] = []
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
            incomplete.append({"id": did, "reasons": sorted(reasons)})
        else:
            covered.append(did)

    hidden_leak = row.get("candidate_receives_hidden_oracle") is not False
    if hidden_leak:
        errors.append(f"{bid}:CANDIDATE_HIDDEN_ORACLE_BOUNDARY_INVALID")

    spec_complete = not missing and not incomplete and not errors

    gate_state: dict[str, bool] = {}
    open_gates: list[str] = []
    for gate in REQUIRED_ROUTE_GATES:
        value = gates.get(gate)
        gate_state[gate] = value is True
        if value is not True:
            open_gates.append(gate)

    comparator = row.get("weaker_comparator_dependency")
    if comparator is not None and (not isinstance(comparator, str) or not comparator):
        errors.append(f"{bid}:COMPARATOR_DEPENDENCY_INVALID")

    stronger_direct_route_exists = spec_complete
    deletion_authorized = spec_complete and not open_gates
    return {
        "behavior_id": bid,
        "objective_spec_complete": spec_complete,
        "covered_dimensions": covered,
        "missing_dimensions": missing,
        "incomplete_dimensions": incomplete,
        "route_gates": gate_state,
        "open_route_gates": open_gates,
        "stronger_direct_behavioral_route_structurally_available": stronger_direct_route_exists,
        "weaker_comparator_dependency": comparator,
        "weaker_comparator_structurally_unnecessary_if_route_verified": bool(
            comparator and stronger_direct_route_exists
        ),
        "weaker_comparator_deletion_authorized_now": bool(
            comparator and deletion_authorized
        ),
        "prewave_route_ready_for_promotion_law": deletion_authorized,
        "terminal_result": False,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }, errors

def compile_dominance(payload: Mapping[str, Any]) -> dict[str, Any]:
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
        row, row_errors = _contract(raw)
        errors.extend(row_errors)
        if row is None:
            continue
        bid = row["behavior_id"]
        if bid in seen:
            errors.append(f"BEHAVIOR_ID_DUPLICATE:{bid}")
        seen.add(bid)
        rows.append(row)

    if errors:
        return {
            **_fail(*errors),
            "contracts": rows,
        }

    all_spec = all(x["objective_spec_complete"] for x in rows)
    all_ready = all(x["prewave_route_ready_for_promotion_law"] for x in rows)
    return {
        "schema": VERDICT_SCHEMA,
        "status": (
            "ALL_OBJECTIVE_ROUTES_VERIFIED_READY_FOR_PROMOTION_LAW"
            if all_ready
            else "OBJECTIVE_ROUTES_STRUCTURALLY_COMPILED__PREWAVE_GATES_OPEN"
            if all_spec
            else "OBJECTIVE_ROUTE_COVERAGE_INCOMPLETE"
        ),
        "pass": True,
        "exact": True,
        "contracts": rows,
        "all_objective_specs_complete": all_spec,
        "all_prewave_routes_ready_for_promotion_law": all_ready,
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "rule": (
            "DIRECT_OBJECTIVE_BEHAVIORAL_PROOF_MAY_DELETE_A_WEAKER_MODEL_COMPARATOR_"
            "ONLY_AFTER_COMPLETE_DIMENSION_COVERAGE_AND_ALL_FROZEN_ROUTE_GATES_PASS__"
            "COMPILER_OUTPUT_ALONE_NEVER_PROMOTES"
        ),
        "errors": [],
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    args = ap.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    out = compile_dominance(payload)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1

if __name__ == "__main__":
    raise SystemExit(main())
