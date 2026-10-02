"""Exact minimum-evidence-cover compiler for Project Brain terminal proof obligations.

This module is intentionally conservative. It never grants capability or family credit.
It answers one question only: given a frozen set of proof obligations and frozen
candidate evidence routes, what is the lexicographically cheapest admissible cover?

A route is eligible only when it has terminal scope authority, zero incremental
spend, and proof-mode-specific admissibility. Partial/public evidence that does not
cover the whole declared obligation remains supporting evidence, not terminal cover.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_PROOF_COVERAGE_COMPILER_V1"
PROOF_MODES = {
    "THEORETICAL_CEILING",
    "FORMAL_PROOF",
    "EXHAUSTIVE_FINITE",
    "PUBLIC_FIXED_BAR",
    "MATCHED_EXACT_OPUS",
    "CANONICAL_ADMITTED_ROUTE",
}
MAX_EXACT_OBLIGATIONS = 20
MAX_ADMISSIBLE_ROUTES = 64


def _fail(errors: list[str], *, details: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "execution_authority": False,
        "promotion_authority": False,
        "errors": sorted(set(errors)),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
    if details:
        out.update(details)
    return out


def _route_admissibility(route: dict[str, Any], required: set[str]) -> tuple[bool, list[str], set[str]]:
    errors: list[str] = []
    rid = route.get("id")
    if not isinstance(rid, str) or not rid:
        return False, ["ROUTE_ID_INVALID"], set()

    mode = route.get("proof_mode")
    if mode not in PROOF_MODES:
        errors.append(f"{rid}:PROOF_MODE_INVALID")

    covered_raw = route.get("covers")
    if not isinstance(covered_raw, list) or not covered_raw:
        errors.append(f"{rid}:COVERS_INVALID")
        covered: set[str] = set()
    else:
        covered = {x for x in covered_raw if isinstance(x, str) and x}
        if len(covered) != len(covered_raw):
            errors.append(f"{rid}:COVERS_DUPLICATE_OR_INVALID")
        unknown = covered - required
        if unknown:
            errors.append(f"{rid}:UNKNOWN_OBLIGATION:" + ",".join(sorted(unknown)))

    if route.get("zero_incremental_spend") is not True:
        errors.append(f"{rid}:NONZERO_OR_UNKNOWN_INCREMENTAL_SPEND")
    if route.get("terminal_scope_authority") is not True:
        errors.append(f"{rid}:NO_TERMINAL_SCOPE_AUTHORITY")
    if route.get("prewave_admissible") is not True:
        errors.append(f"{rid}:NOT_PREWAVE_ADMISSIBLE")
    if route.get("external_blocked") is True:
        errors.append(f"{rid}:EXTERNAL_BLOCKED")

    if mode == "PUBLIC_FIXED_BAR":
        if route.get("harness_scope_equivalent") is not True:
            errors.append(f"{rid}:PUBLIC_BAR_SCOPE_NOT_EQUIVALENT")
        if route.get("zero_cost_executable") is not True:
            errors.append(f"{rid}:PUBLIC_BAR_NOT_ZERO_COST_EXECUTABLE")
        if not isinstance(route.get("public_bar_source"), str) or not route.get("public_bar_source"):
            errors.append(f"{rid}:PUBLIC_BAR_SOURCE_MISSING")
    elif mode == "MATCHED_EXACT_OPUS":
        if route.get("exact_opus_5_5_comparator_bound") is not True:
            errors.append(f"{rid}:EXACT_OPUS_COMPARATOR_NOT_BOUND")
        if route.get("symmetric_harness_frozen") is not True:
            errors.append(f"{rid}:SYMMETRIC_HARNESS_NOT_FROZEN")
    elif mode == "PORTFOLIO_MULTIPLEXED_OPEN_DOMAIN":
        if route.get("portfolio_multiplex_binding_frozen") is not True:
            errors.append(f"{rid}:PORTFOLIO_MULTIPLEX_BINDING_NOT_FROZEN")
        if route.get("independent_preflight_bound") is not True:
            errors.append(f"{rid}:PORTFOLIO_MULTIPLEX_INDEPENDENT_PREFLIGHT_NOT_BOUND")
    elif mode == "CANONICAL_ADMITTED_ROUTE":
        if route.get("canonical_active_basis_admitted") is not True:
            errors.append(f"{rid}:CANONICAL_ADMISSION_NOT_PROVEN")
        if not isinstance(route.get("source_basis_blob_sha"), str) or not route.get("source_basis_blob_sha"):
            errors.append(f"{rid}:SOURCE_BASIS_BLOB_MISSING")

    for key in ("new_reality_units", "clean_case_spend"):
        v = route.get(key, 0)
        if not isinstance(v, int) or isinstance(v, bool) or v < 0:
            errors.append(f"{rid}:{key.upper()}_INVALID")
    evidence_cost = route.get("evidence_cost", 0.0)
    if not isinstance(evidence_cost, (int, float)) or isinstance(evidence_cost, bool) or evidence_cost < 0:
        errors.append(f"{rid}:EVIDENCE_COST_INVALID")

    return not errors, errors, covered


def evaluate(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _fail(["INPUT_NOT_OBJECT"])

    obligations_raw = data.get("required_obligations")
    routes_raw = data.get("routes")
    if not isinstance(obligations_raw, list) or not obligations_raw:
        return _fail(["REQUIRED_OBLIGATIONS_INVALID"])
    if not isinstance(routes_raw, list):
        return _fail(["ROUTES_NOT_LIST"])

    obligations: list[str] = []
    seen: set[str] = set()
    errors: list[str] = []
    for i, row in enumerate(obligations_raw):
        if isinstance(row, str):
            oid = row
        elif isinstance(row, dict):
            oid = row.get("id")
        else:
            oid = None
        if not isinstance(oid, str) or not oid:
            errors.append(f"OBLIGATION_{i}_ID_INVALID")
            continue
        if oid in seen:
            errors.append("DUPLICATE_OBLIGATION:" + oid)
            continue
        seen.add(oid)
        obligations.append(oid)

    if errors:
        return _fail(errors)
    if len(obligations) > MAX_EXACT_OBLIGATIONS:
        return _fail([
            f"EXACT_COVER_LIMIT_EXCEEDED:{len(obligations)}>{MAX_EXACT_OBLIGATIONS}"
        ])

    required = set(obligations)
    index = {oid: i for i, oid in enumerate(obligations)}

    admissible: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    route_ids: set[str] = set()

    for i, route in enumerate(routes_raw):
        if not isinstance(route, dict):
            rejected.append({"route_index": i, "errors": ["ROUTE_NOT_OBJECT"]})
            continue
        rid = route.get("id")
        if isinstance(rid, str) and rid in route_ids:
            rejected.append({"route_id": rid, "errors": ["DUPLICATE_ROUTE_ID"]})
            continue
        if isinstance(rid, str):
            route_ids.add(rid)
        ok, why, covered = _route_admissibility(route, required)
        if not ok:
            rejected.append({"route_id": rid, "errors": why})
            continue
        mask = 0
        for oid in covered:
            mask |= 1 << index[oid]
        if mask == 0:
            rejected.append({"route_id": rid, "errors": ["EMPTY_EFFECTIVE_COVER"]})
            continue
        admissible.append({
            "id": rid,
            "mask": mask,
            "covers": sorted(covered),
            "proof_mode": route["proof_mode"],
            "new_reality_units": int(route.get("new_reality_units", 0)),
            "clean_case_spend": int(route.get("clean_case_spend", 0)),
            "evidence_cost": float(route.get("evidence_cost", 0.0)),
        })

    if len(admissible) > MAX_ADMISSIBLE_ROUTES:
        return _fail([f"ADMISSIBLE_ROUTE_LIMIT_EXCEEDED:{len(admissible)}>{MAX_ADMISSIBLE_ROUTES}"])

    dp: dict[int, tuple[tuple[Any, ...], tuple[str, ...]]] = {
        0: ((0, 0, 0, 0.0, ()), ())
    }
    for route in sorted(admissible, key=lambda r: r["id"]):
        current = list(dp.items())
        for mask, (obj, selected) in current:
            new_mask = mask | route["mask"]
            if new_mask == mask:
                continue
            ids = tuple(sorted(selected + (route["id"],)))
            new_obj = (
                obj[0] + route["new_reality_units"],
                obj[1] + route["clean_case_spend"],
                obj[2] + 1,
                obj[3] + route["evidence_cost"],
                ids,
            )
            prev = dp.get(new_mask)
            if prev is None or new_obj < prev[0]:
                dp[new_mask] = (new_obj, ids)

    full_mask = (1 << len(obligations)) - 1
    best = dp.get(full_mask)

    coverable_mask = 0
    per_obligation: dict[str, list[str]] = {oid: [] for oid in obligations}
    for route in admissible:
        coverable_mask |= route["mask"]
        for oid in route["covers"]:
            per_obligation[oid].append(route["id"])
    uncovered = [
        oid for oid in obligations
        if not (coverable_mask & (1 << index[oid]))
    ]

    if best is None:
        return {
            "schema": SCHEMA,
            "status": "INCOMPLETE_COVER",
            "pass": False,
            "execution_authority": False,
            "promotion_authority": False,
            "required_obligation_count": len(obligations),
            "admissible_route_count": len(admissible),
            "uncovered_obligations": uncovered,
            "candidate_routes_by_obligation": {
                k: sorted(v) for k, v in per_obligation.items()
            },
            "rejected_routes": rejected,
            "errors": [],
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    objective, selected = best
    selected_set = set(selected)
    selected_rows = [r for r in admissible if r["id"] in selected_set]
    return {
        "schema": SCHEMA,
        "status": "EXACT_MINIMUM_COVER_FOUND",
        "pass": True,
        "execution_authority": False,
        "promotion_authority": False,
        "required_obligation_count": len(obligations),
        "admissible_route_count": len(admissible),
        "selected_route_ids": list(selected),
        "selected_routes": selected_rows,
        "objective": {
            "new_reality_units": objective[0],
            "clean_case_spend": objective[1],
            "route_count": objective[2],
            "evidence_cost": objective[3],
        },
        "uncovered_obligations": [],
        "rejected_routes": rejected,
        "rule": (
            "EXACT_LEXICOGRAPHIC_MINIMUM_OVER_FROZEN_ADMISSIBLE_ROUTES__"
            "NO_SCOPE_INHERITANCE__NO_PROXY_COMPARATOR__NO_CAPABILITY_CREDIT"
        ),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    args = ap.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    out = evaluate(data)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"] in {"EXACT_MINIMUM_COVER_FOUND", "INCOMPLETE_COVER"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
