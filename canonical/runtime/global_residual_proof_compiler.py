"""Global residual proof compiler for Project Brain.

This layer sits above terminal_proof_supercompiler. It does three things that the
base compiler intentionally does not:

1. Keep internally solvable proof work moving even when other obligations are
   externally blocked or have no admissible route in the frozen universe.
2. Deduplicate blockers only through explicit semantic-equivalence assertions,
   never by string similarity or heuristic inference.
3. Return one fail-closed global residual partition: exact internal unblock cut
   plus the obligations that still require a stronger route or external fact.

It never grants execution, promotion, capability, or family credit.
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.terminal_proof_supercompiler import (
    SCHEMA as SUPERCOMPILER_SCHEMA,
    compile_superproof,
)

SCHEMA = "PROJECT_BRAIN_GLOBAL_RESIDUAL_PROOF_COMPILER_INPUT_V1"
VERDICT_SCHEMA = "PROJECT_BRAIN_GLOBAL_RESIDUAL_PROOF_COMPILER_VERDICT_V1"


def _fail(*errors: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema": VERDICT_SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "exact": False,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "errors": sorted(set(errors)),
    }
    if details:
        out.update(details)
    return out


def _normalize_equivalence(
    blockers_raw: Any,
    routes_raw: Any,
    classes_raw: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    if not isinstance(blockers_raw, list):
        return [], [], [], ["BLOCKERS_NOT_LIST"]
    if not isinstance(routes_raw, list):
        return [], [], [], ["ROUTES_NOT_LIST"]
    if classes_raw is None:
        classes_raw = []
    if not isinstance(classes_raw, list):
        return [], [], [], ["SEMANTIC_EQUIVALENCE_NOT_LIST"]

    errors: list[str] = []
    blockers: dict[str, dict[str, Any]] = {}
    for i, row in enumerate(blockers_raw):
        if not isinstance(row, Mapping):
            errors.append(f"BLOCKER_NOT_OBJECT:{i}")
            continue
        bid = row.get("id")
        if not isinstance(bid, str) or not bid:
            errors.append(f"BLOCKER_ID_INVALID:{i}")
            continue
        if bid in blockers:
            errors.append(f"BLOCKER_ID_DUPLICATE:{bid}")
            continue
        blockers[bid] = dict(row)

    member_to_canonical: dict[str, str] = {}
    class_receipts: list[dict[str, Any]] = []
    canonical_defs: dict[str, dict[str, Any]] = {}

    for i, row in enumerate(classes_raw):
        if not isinstance(row, Mapping):
            errors.append(f"SEMANTIC_CLASS_NOT_OBJECT:{i}")
            continue
        cid = row.get("id")
        members = row.get("members")
        if not isinstance(cid, str) or not cid:
            errors.append(f"SEMANTIC_CLASS_ID_INVALID:{i}")
            continue
        if cid in blockers and cid not in (members or []):
            errors.append(f"SEMANTIC_CLASS_ID_COLLIDES_WITH_RAW_BLOCKER:{cid}")
        if (
            not isinstance(members, list)
            or len(members) < 2
            or any(not isinstance(x, str) or not x for x in members)
        ):
            errors.append(f"SEMANTIC_CLASS_MEMBERS_INVALID:{cid}")
            continue
        if len(set(members)) != len(members):
            errors.append(f"SEMANTIC_CLASS_MEMBER_DUPLICATE:{cid}")
            continue
        unknown = sorted(set(members) - set(blockers))
        if unknown:
            errors.append(f"SEMANTIC_CLASS_UNKNOWN_MEMBER:{cid}:" + ",".join(unknown))
            continue
        overlap = sorted(x for x in members if x in member_to_canonical)
        if overlap:
            errors.append(f"SEMANTIC_CLASS_OVERLAP:{cid}:" + ",".join(overlap))
            continue
        if row.get("equivalence_asserted") is not True:
            errors.append(f"SEMANTIC_CLASS_NOT_EXPLICITLY_ASSERTED:{cid}")
            continue

        rows = [blockers[x] for x in members]
        statuses = {x.get("status") for x in rows}
        if not statuses <= {"OPEN", "CLOSED"}:
            errors.append(f"SEMANTIC_CLASS_STATUS_INVALID:{cid}")
            continue

        merged = {
            "id": cid,
            "status": "OPEN" if "OPEN" in statuses else "CLOSED",
            "closable": all(x.get("closable") is True for x in rows),
            "external_blocked": any(x.get("external_blocked") is True for x in rows),
            "dependency_depth": max(int(x.get("dependency_depth", 0)) for x in rows),
            "critical_path_wall_clock_units": max(
                float(x.get("critical_path_wall_clock_units", 0.0)) for x in rows
            ),
            "new_reality_units": max(float(x.get("new_reality_units", 0.0)) for x in rows),
        }
        canonical_defs[cid] = merged
        for member in members:
            member_to_canonical[member] = cid
        class_receipts.append(
            {
                "id": cid,
                "members": sorted(members),
                "merge_rule": (
                    "EXPLICIT_SEMANTIC_EQUIVALENCE_ONLY__OPEN_IF_ANY_OPEN__"
                    "CLOSABLE_IF_ALL_CLOSABLE__EXTERNAL_IF_ANY_EXTERNAL__"
                    "MAX_COST_NOT_SUM"
                ),
            }
        )

    if errors:
        return [], [], class_receipts, errors

    normalized_blockers: list[dict[str, Any]] = []
    emitted: set[str] = set()
    for bid, row in blockers.items():
        cid = member_to_canonical.get(bid, bid)
        if cid in emitted:
            continue
        emitted.add(cid)
        normalized_blockers.append(deepcopy(canonical_defs.get(cid, row)))

    normalized_routes: list[dict[str, Any]] = []
    for i, raw in enumerate(routes_raw):
        if not isinstance(raw, Mapping):
            errors.append(f"ROUTE_NOT_OBJECT:{i}")
            continue
        route = deepcopy(dict(raw))
        rb = route.get("blockers", [])
        if not isinstance(rb, list) or any(not isinstance(x, str) or not x for x in rb):
            errors.append(f"ROUTE_BLOCKERS_INVALID:{route.get('id', i)}")
            continue
        unknown = sorted(set(rb) - set(blockers))
        if unknown:
            errors.append(
                f"ROUTE_UNKNOWN_BLOCKER:{route.get('id', i)}:" + ",".join(unknown)
            )
            continue
        route["blockers"] = sorted(
            {member_to_canonical.get(x, x) for x in rb}
        )
        sab = route.get("scope_authority_blocker")
        if isinstance(sab, str) and sab:
            if sab not in blockers:
                errors.append(
                    f"ROUTE_UNKNOWN_SCOPE_AUTHORITY_BLOCKER:{route.get('id', i)}:{sab}"
                )
                continue
            route["scope_authority_blocker"] = member_to_canonical.get(sab, sab)
        normalized_routes.append(route)

    return normalized_blockers, normalized_routes, class_receipts, errors


def _super_payload(
    payload: Mapping[str, Any],
    obligations: list[str],
    blockers: list[dict[str, Any]],
    routes: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": SUPERCOMPILER_SCHEMA,
        "obligations": obligations,
        "blockers": blockers,
        "routes": routes,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def compile_global_residual(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("INPUT_NOT_OBJECT")
    if payload.get("schema") != SCHEMA:
        return _fail("SCHEMA_INVALID")

    obligations_raw = payload.get("obligations")
    if (
        not isinstance(obligations_raw, list)
        or not obligations_raw
        or any(not isinstance(x, str) or not x for x in obligations_raw)
    ):
        return _fail("OBLIGATIONS_INVALID")
    if len(set(obligations_raw)) != len(obligations_raw):
        return _fail("OBLIGATIONS_DUPLICATE")
    obligations = list(obligations_raw)

    blockers, routes, equivalence_receipts, errors = _normalize_equivalence(
        payload.get("blockers"),
        payload.get("routes"),
        payload.get("semantic_blocker_equivalence"),
    )
    if errors:
        return _fail(*errors, details={"semantic_equivalence": equivalence_receipts})

    full = compile_superproof(
        _super_payload(payload, obligations, blockers, routes)
    )
    full_status = full.get("status")

    if full_status == "FAIL_CLOSED":
        return _fail(
            "BASE_SUPERCOMPILER_FAIL_CLOSED",
            details={
                "base_supercompiler": full,
                "semantic_equivalence": equivalence_receipts,
            },
        )

    if full_status == "EXACT_MINIMUM_UNBLOCK_CUT_FOUND":
        return {
            "schema": VERDICT_SCHEMA,
            "status": "GLOBAL_EXACT_INTERNAL_COVER_FOUND",
            "pass": True,
            "exact": True,
            "global_terminal_complete": False,
            "execution_authority": False,
            "promotion_authority": False,
            "all_obligations": sorted(obligations),
            "internally_coverable_obligations": sorted(obligations),
            "residual_obligations": [],
            "minimum_internal_unblock_cut": full.get("minimum_unblock_cut"),
            "proof_mode_transmutation": full.get("proof_mode_transmutation"),
            "semantic_equivalence": equivalence_receipts,
            "base_supercompiler_status": full_status,
            "rule": (
                "SCHEDULING_ONLY__CLOSE_EXACT_INTERNAL_CUT_THEN_RECOMPUTE__"
                "NO_TERMINAL_OR_CAPABILITY_CREDIT"
            ),
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "errors": [],
        }

    if full_status != "EXTERNAL_IRREDUCIBLE_OR_FROZEN_UNIVERSE_INCOMPLETE":
        return _fail(
            "BASE_SUPERCOMPILER_STATUS_UNEXPECTED:" + str(full_status),
            details={
                "base_supercompiler": full,
                "semantic_equivalence": equivalence_receipts,
            },
        )

    uncovered = full.get("internally_uncovered_obligations")
    if (
        not isinstance(uncovered, list)
        or any(not isinstance(x, str) or x not in obligations for x in uncovered)
    ):
        return _fail(
            "BASE_UNCOVERED_OBLIGATIONS_INVALID",
            details={"base_supercompiler": full},
        )
    residual = sorted(set(uncovered))
    internal = sorted(set(obligations) - set(residual))

    projected_routes: list[dict[str, Any]] = []
    projection_rejected: list[str] = []
    internal_set = set(internal)
    for route in routes:
        covers = route.get("covers")
        if not isinstance(covers, list):
            continue
        cset = set(covers)
        intersection = sorted(cset & internal_set)
        if not intersection:
            continue
        if cset <= internal_set:
            projected_routes.append(deepcopy(route))
            continue
        if route.get("coverage_projection_safe") is True:
            projected = deepcopy(route)
            projected["covers"] = intersection
            projected_routes.append(projected)
        else:
            projection_rejected.append(str(route.get("id")))

    internal_result: dict[str, Any] | None = None
    if internal:
        internal_result = compile_superproof(
            _super_payload(payload, internal, blockers, projected_routes)
        )
        if internal_result.get("status") != "EXACT_MINIMUM_UNBLOCK_CUT_FOUND":
            return _fail(
                "INTERNAL_PARTITION_NOT_EXACTLY_COVERABLE_AFTER_PROJECTION",
                details={
                    "base_supercompiler": full,
                    "internal_partition_supercompiler": internal_result,
                    "projection_rejected_route_ids": sorted(projection_rejected),
                    "semantic_equivalence": equivalence_receipts,
                },
            )

    transmutation = full.get("proof_mode_transmutation")
    if not isinstance(transmutation, dict):
        transmutation = {}
    residual_rows = []
    for oid in residual:
        t = transmutation.get(oid) if isinstance(transmutation.get(oid), dict) else {}
        residual_rows.append(
            {
                "obligation_id": oid,
                "classification": (
                    "MATCHED_EXACT_OPUS_IRREDUCIBLE_UNDER_FROZEN_UNIVERSE"
                    if t.get("matched_exact_opus_irreducible_under_frozen_universe") is True
                    else "NO_INTERNALLY_REACHABLE_ADMISSIBLE_ROUTE__STRONGER_ROUTE_OR_EXTERNAL_FACT_REQUIRED"
                ),
                "strongest_declared_mode": t.get("strongest_declared_mode"),
                "candidate_route_ids": t.get("candidate_route_ids") or [],
            }
        )

    return {
        "schema": VERDICT_SCHEMA,
        "status": "GLOBAL_RESIDUAL_PARTITION_FOUND",
        "pass": True,
        "exact": True,
        "global_terminal_complete": False,
        "execution_authority": False,
        "promotion_authority": False,
        "all_obligations": sorted(obligations),
        "internally_coverable_obligations": internal,
        "residual_obligations": residual_rows,
        "minimum_internal_unblock_cut": (
            internal_result.get("minimum_unblock_cut") if internal_result else None
        ),
        "proof_mode_transmutation": transmutation,
        "semantic_equivalence": equivalence_receipts,
        "projection_rejected_route_ids": sorted(projection_rejected),
        "base_supercompiler_status": full_status,
        "rule": (
            "EXTERNAL_OR_UNPROVEN_RESIDUALS_MUST_NOT_STALL_INDEPENDENT_INTERNAL_CLOSURE__"
            "CLOSE_ONLY_EXACT_INTERNAL_CUT__RECOMPUTE_AFTER_EACH_CLOSURE__"
            "NO_HEURISTIC_SEMANTIC_DEDUP__NO_PROXY_SUBSTITUTION"
        ),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "errors": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    args = ap.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    out = compile_global_residual(payload)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
