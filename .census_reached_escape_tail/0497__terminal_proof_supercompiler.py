"""Terminal proof supercompiler for Project Brain.

This controller adds two exact, fail-closed transformations above the existing
proof coverage and global proof-cut compilers:

1. Proof-mode transmutation: for each terminal obligation, identify the
   strongest currently admissible proof mode before accepting an expensive or
   externally blocked matched comparator route.
2. Minimum unblock cut: over a frozen finite route/blocker universe, compute
   the exact smallest internally closable blocker set whose closure enables a
   complete terminal proof cover.

It never grants capability, family, execution, or promotion authority. It is a
pre-proof scheduling compiler only.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_PROOF_SUPERCOMPILER_INPUT_V1"
VERDICT_SCHEMA = "PROJECT_BRAIN_TERMINAL_PROOF_SUPERCOMPILER_VERDICT_V1"

PROOF_MODE_ORDER = (
    "EXISTING_RECEIPT",
    "EXACT_DEDUCTION",
    "FORMAL_PROOF",
    "EXHAUSTIVE_FINITE",
    "DETERMINISTIC_HIDDEN_ORACLE",
    "PUBLIC_FIXED_BAR",
    "PUBLIC_SAME_CASE_OPUS",
    "MATCHED_EXACT_OPUS",
)
PROOF_MODE_RANK = {mode: i for i, mode in enumerate(PROOF_MODE_ORDER)}

MAX_OBLIGATIONS = 32
MAX_ROUTES = 96
MAX_BLOCKERS = 64
MAX_STATES_PER_COVERAGE_MASK = 512


def _finite_nonnegative(v: Any) -> bool:
    return (
        isinstance(v, (int, float))
        and not isinstance(v, bool)
        and math.isfinite(float(v))
        and float(v) >= 0
    )


def _fail(*errors: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema": VERDICT_SCHEMA,
        "status": "FAIL_CLOSED",
        "exact": False,
        "pass": False,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "errors": sorted(set(errors)),
    }
    if details:
        out.update(details)
    return out


def _normalize_obligations(rows: Any) -> tuple[list[str], list[str]]:
    if not isinstance(rows, list) or not rows:
        return [], ["OBLIGATIONS_INVALID"]
    out: list[str] = []
    seen: set[str] = set()
    errors: list[str] = []
    for i, row in enumerate(rows):
        oid = row if isinstance(row, str) else row.get("id") if isinstance(row, Mapping) else None
        if not isinstance(oid, str) or not oid:
            errors.append(f"OBLIGATION_ID_INVALID:{i}")
            continue
        if oid in seen:
            errors.append(f"OBLIGATION_ID_DUPLICATE:{oid}")
            continue
        seen.add(oid)
        out.append(oid)
    if len(out) > MAX_OBLIGATIONS:
        errors.append(f"OBLIGATION_LIMIT_EXCEEDED:{len(out)}>{MAX_OBLIGATIONS}")
    return out, errors


def _normalize_blockers(rows: Any) -> tuple[dict[str, dict[str, Any]], list[str]]:
    if not isinstance(rows, list):
        return {}, ["BLOCKERS_NOT_LIST"]
    errors: list[str] = []
    out: dict[str, dict[str, Any]] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"BLOCKER_INVALID:{i}")
            continue
        bid = row.get("id")
        if not isinstance(bid, str) or not bid:
            errors.append(f"BLOCKER_ID_INVALID:{i}")
            continue
        if bid in out:
            errors.append(f"BLOCKER_ID_DUPLICATE:{bid}")
            continue
        status = row.get("status")
        if status not in {"OPEN", "CLOSED"}:
            errors.append(f"BLOCKER_STATUS_INVALID:{bid}")
        closable = row.get("closable")
        external = row.get("external_blocked")
        if closable is not True and closable is not False:
            errors.append(f"BLOCKER_CLOSABLE_INVALID:{bid}")
        if external is not True and external is not False:
            errors.append(f"BLOCKER_EXTERNAL_FLAG_INVALID:{bid}")
        depth = row.get("dependency_depth", 0)
        wall = row.get("critical_path_wall_clock_units", 0.0)
        reality = row.get("new_reality_units", 0.0)
        if not isinstance(depth, int) or isinstance(depth, bool) or depth < 0:
            errors.append(f"BLOCKER_DEPENDENCY_DEPTH_INVALID:{bid}")
            depth = 0
        if not _finite_nonnegative(wall):
            errors.append(f"BLOCKER_WALL_CLOCK_INVALID:{bid}")
            wall = 0.0
        if not _finite_nonnegative(reality):
            errors.append(f"BLOCKER_REALITY_UNITS_INVALID:{bid}")
            reality = 0.0
        out[bid] = {
            "id": bid,
            "status": status,
            "closable": closable is True,
            "external_blocked": external is True,
            "dependency_depth": int(depth),
            "critical_path_wall_clock_units": float(wall),
            "new_reality_units": float(reality),
        }
    if len(out) > MAX_BLOCKERS:
        errors.append(f"BLOCKER_LIMIT_EXCEEDED:{len(out)}>{MAX_BLOCKERS}")
    return out, errors


def _proof_mode_checks(route: Mapping[str, Any]) -> list[str]:
    rid = route.get("id", "<unknown>")
    mode = route.get("proof_mode")
    errors: list[str] = []
    if mode not in PROOF_MODE_RANK:
        return [f"{rid}:PROOF_MODE_INVALID"]
    if mode in {"EXACT_DEDUCTION", "FORMAL_PROOF"} and route.get("machine_checkable") is not True:
        errors.append(f"{rid}:MACHINE_CHECKABLE_PROOF_REQUIRED")
    elif mode == "EXISTING_RECEIPT":
        if route.get("scope_equivalent_receipt") is not True:
            errors.append(f"{rid}:SCOPE_EQUIVALENT_RECEIPT_REQUIRED")
        if route.get("receipt_valid") is not True:
            errors.append(f"{rid}:VALID_RECEIPT_REQUIRED")
    elif mode == "EXHAUSTIVE_FINITE":
        if route.get("finite_domain_frozen") is not True:
            errors.append(f"{rid}:FINITE_DOMAIN_NOT_FROZEN")
        if route.get("exhaustive") is not True:
            errors.append(f"{rid}:EXHAUSTIVE_PROOF_REQUIRED")
    elif mode == "DETERMINISTIC_HIDDEN_ORACLE":
        if route.get("oracle_independent") is not True:
            errors.append(f"{rid}:INDEPENDENT_ORACLE_REQUIRED")
        if route.get("candidate_oracle_hidden") is not True:
            errors.append(f"{rid}:ORACLE_INFORMATION_BOUNDARY_REQUIRED")
    elif mode == "PUBLIC_FIXED_BAR":
        if route.get("scope_equivalent") is not True:
            errors.append(f"{rid}:PUBLIC_BAR_SCOPE_EQUIVALENCE_REQUIRED")
        if route.get("zero_cost_executable") is not True:
            errors.append(f"{rid}:PUBLIC_BAR_ZERO_COST_EXECUTION_REQUIRED")
    elif mode == "PUBLIC_SAME_CASE_OPUS":
        if route.get("same_case_provenance_bound") is not True:
            errors.append(f"{rid}:SAME_CASE_PROVENANCE_REQUIRED")
        if route.get("harness_equivalent") is not True:
            errors.append(f"{rid}:HARNESS_EQUIVALENCE_REQUIRED")
    elif mode == "MATCHED_EXACT_OPUS":
        if route.get("exact_opus_5_5_comparator_bound") is not True:
            errors.append(f"{rid}:EXACT_OPUS_COMPARATOR_REQUIRED")
        if route.get("symmetric_harness_frozen") is not True:
            errors.append(f"{rid}:SYMMETRIC_HARNESS_REQUIRED")
    return errors


def _normalize_routes(
    rows: Any,
    obligations: set[str],
    blockers: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    if not isinstance(rows, list):
        return [], [], ["ROUTES_NOT_LIST"]
    errors: list[str] = []
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            rejected.append({"route_index": i, "errors": ["ROUTE_NOT_OBJECT"]})
            continue
        rid = row.get("id")
        why: list[str] = []
        if not isinstance(rid, str) or not rid:
            rejected.append({"route_index": i, "errors": ["ROUTE_ID_INVALID"]})
            continue
        if rid in seen:
            rejected.append({"route_id": rid, "errors": ["ROUTE_ID_DUPLICATE"]})
            continue
        seen.add(rid)
        covers = row.get("covers")
        if not isinstance(covers, list) or not covers or any(not isinstance(x, str) or not x for x in covers):
            why.append(f"{rid}:COVERS_INVALID")
            cover_set: set[str] = set()
        else:
            cover_set = set(covers)
            if len(cover_set) != len(covers):
                why.append(f"{rid}:COVERS_DUPLICATE")
            unknown = cover_set - obligations
            if unknown:
                why.append(f"{rid}:COVERS_UNKNOWN:" + ",".join(sorted(unknown)))
        braw = row.get("blockers", [])
        if not isinstance(braw, list) or any(not isinstance(x, str) or not x for x in braw):
            why.append(f"{rid}:BLOCKERS_INVALID")
            bset: set[str] = set()
        else:
            bset = set(braw)
            if len(bset) != len(braw):
                why.append(f"{rid}:BLOCKERS_DUPLICATE")
            unknown_b = bset - blockers.keys()
            if unknown_b:
                why.append(f"{rid}:UNKNOWN_BLOCKER:" + ",".join(sorted(unknown_b)))
        if row.get("base_admissible") is not True:
            why.append(f"{rid}:BASE_NOT_ADMISSIBLE")
        current_scope_authority = row.get("terminal_scope_authority") is True
        conditional_scope_authority = row.get("terminal_scope_authority_after_blockers") is True
        scope_authority_blocker = row.get("scope_authority_blocker")
        if not current_scope_authority:
            if not conditional_scope_authority:
                why.append(f"{rid}:NO_CURRENT_OR_CONDITIONAL_TERMINAL_SCOPE_AUTHORITY")
            elif (
                not isinstance(scope_authority_blocker, str)
                or not scope_authority_blocker
                or scope_authority_blocker not in bset
            ):
                why.append(f"{rid}:CONDITIONAL_SCOPE_AUTHORITY_BLOCKER_NOT_BOUND")
        if row.get("zero_incremental_spend") is not True:
            why.append(f"{rid}:NONZERO_OR_UNKNOWN_INCREMENTAL_SPEND")
        if row.get("opaque_target_capability_provider") is True:
            why.append(f"{rid}:OPAQUE_TARGET_CAPABILITY_PROVIDER")
        why.extend(_proof_mode_checks(row))
        if why:
            rejected.append({"route_id": rid, "errors": sorted(set(why))})
            continue
        open_blockers = sorted(
            bid for bid in bset if blockers[bid]["status"] == "OPEN"
        )
        unclosable = sorted(
            bid for bid in open_blockers
            if not blockers[bid]["closable"] or blockers[bid]["external_blocked"]
        )
        accepted.append(
            {
                "id": rid,
                "covers": sorted(cover_set),
                "proof_mode": row["proof_mode"],
                "proof_mode_rank": PROOF_MODE_RANK[row["proof_mode"]],
                "open_blockers": open_blockers,
                "unclosable_blockers": unclosable,
                "current_terminal_scope_authority": current_scope_authority,
                "conditional_terminal_scope_authority": conditional_scope_authority,
                "scope_authority_blocker": scope_authority_blocker if conditional_scope_authority else None,
            }
        )
    if len(accepted) > MAX_ROUTES:
        errors.append(f"ROUTE_LIMIT_EXCEEDED:{len(accepted)}>{MAX_ROUTES}")
    return sorted(accepted, key=lambda r: r["id"]), rejected, errors


def _blocker_union_objective(
    blocker_ids: frozenset[str], blockers: dict[str, dict[str, Any]]
) -> tuple[int, float, float, int, tuple[str, ...]]:
    rows = [blockers[x] for x in blocker_ids]
    max_depth = max((r["dependency_depth"] for r in rows), default=0)
    wall = max((r["critical_path_wall_clock_units"] for r in rows), default=0.0)
    reality = sum(r["new_reality_units"] for r in rows)
    return max_depth, wall, reality, len(blocker_ids), tuple(sorted(blocker_ids))


def _state_objective(
    blocker_ids: frozenset[str],
    blockers: dict[str, dict[str, Any]],
    max_mode_rank: int,
    route_ids: tuple[str, ...],
) -> tuple[Any, ...]:
    bobj = _blocker_union_objective(blocker_ids, blockers)
    return (
        bobj[0],
        bobj[1],
        bobj[2],
        max_mode_rank,
        bobj[3],
        len(route_ids),
        bobj[4],
        route_ids,
    )


def _prune_states(
    states: list[tuple[frozenset[str], int, tuple[str, ...]]],
    blockers: dict[str, dict[str, Any]],
) -> list[tuple[frozenset[str], int, tuple[str, ...]]]:
    kept: list[tuple[frozenset[str], int, tuple[str, ...]]] = []
    for cand in sorted(
        states,
        key=lambda s: _state_objective(s[0], blockers, s[1], s[2]),
    ):
        dominated = False
        for prior in kept:
            if (
                prior[0] <= cand[0]
                and prior[1] <= cand[1]
                and len(prior[2]) <= len(cand[2])
            ):
                dominated = True
                break
        if not dominated:
            kept.append(cand)
        if len(kept) > MAX_STATES_PER_COVERAGE_MASK:
            raise ValueError("PARETO_FRONTIER_LIMIT_EXCEEDED__DECOMPOSE_REQUIRED")
    return kept


def compile_superproof(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("INPUT_NOT_OBJECT")
    if payload.get("schema") != SCHEMA:
        return _fail("SCHEMA_INVALID")

    obligations, oerr = _normalize_obligations(payload.get("obligations"))
    blockers, berr = _normalize_blockers(payload.get("blockers"))
    routes, rejected, rerr = _normalize_routes(
        payload.get("routes"), set(obligations), blockers
    )
    errors = oerr + berr + rerr
    if errors:
        return _fail(*errors, details={"rejected_routes": rejected})

    index = {oid: i for i, oid in enumerate(obligations)}
    target = (1 << len(obligations)) - 1

    transmutation: dict[str, Any] = {}
    for oid in obligations:
        candidates = [r for r in routes if oid in r["covers"]]
        candidates.sort(key=lambda r: (r["proof_mode_rank"], r["id"]))
        internal = [r for r in candidates if not r["unclosable_blockers"]]
        transmutation[oid] = {
            "strongest_declared_mode": candidates[0]["proof_mode"] if candidates else None,
            "strongest_internally_reachable_mode": internal[0]["proof_mode"] if internal else None,
            "matched_exact_opus_irreducible_under_frozen_universe": (
                bool(candidates)
                and all(r["proof_mode"] == "MATCHED_EXACT_OPUS" for r in candidates)
                and not internal
            ),
            "candidate_route_ids": [r["id"] for r in candidates],
        }

    internal_routes = [r for r in routes if not r["unclosable_blockers"]]
    coverable = set()
    for r in internal_routes:
        coverable.update(r["covers"])
    internally_uncovered = sorted(set(obligations) - coverable)

    if internally_uncovered:
        ext: set[str] = set()
        for r in routes:
            if set(r["covers"]) & set(internally_uncovered):
                ext.update(r["unclosable_blockers"])
        return {
            "schema": VERDICT_SCHEMA,
            "status": "EXTERNAL_IRREDUCIBLE_OR_FROZEN_UNIVERSE_INCOMPLETE",
            "exact": True,
            "pass": False,
            "execution_authority": False,
            "promotion_authority": False,
            "proof_mode_transmutation": transmutation,
            "internally_uncovered_obligations": internally_uncovered,
            "unclosable_blockers": sorted(ext),
            "rejected_routes": rejected,
            "minimum_unblock_cut": None,
            "rule": (
                "NO_PROXY_SUBSTITUTION__EITHER_ADD_ADMISSIBLE_STRONGER_ROUTE_OR_"
                "ESTABLISH_THE_EXTERNAL_INFORMATION__DO_NOT_SPEND_CLEAN_CASES"
            ),
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    dp: dict[int, list[tuple[frozenset[str], int, tuple[str, ...]]]] = {
        0: [(frozenset(), 0, ())]
    }
    try:
        for route in internal_routes:
            rmask = 0
            for oid in route["covers"]:
                rmask |= 1 << index[oid]
            rblockers = frozenset(route["open_blockers"])
            snapshot = [(mask, list(states)) for mask, states in dp.items()]
            for mask, states in snapshot:
                nmask = mask | rmask
                if nmask == mask:
                    continue
                bucket = list(dp.get(nmask, []))
                for bset, max_rank, rids in states:
                    ids = tuple(sorted(rids + (route["id"],)))
                    bucket.append(
                        (
                            bset | rblockers,
                            max(max_rank, route["proof_mode_rank"]),
                            ids,
                        )
                    )
                dp[nmask] = _prune_states(bucket, blockers)
    except ValueError as exc:
        return _fail(str(exc), details={
            "proof_mode_transmutation": transmutation,
            "rejected_routes": rejected,
        })

    solutions = dp.get(target, [])
    if not solutions:
        return _fail(
            "NO_COMPLETE_INTERNAL_COVER_AFTER_DP",
            details={
                "proof_mode_transmutation": transmutation,
                "rejected_routes": rejected,
            },
        )

    best = min(
        solutions,
        key=lambda s: _state_objective(s[0], blockers, s[1], s[2]),
    )
    bset, max_rank, route_ids = best
    max_depth, wall, reality, blocker_count, blocker_tuple = _blocker_union_objective(
        bset, blockers
    )
    selected = [r for r in internal_routes if r["id"] in set(route_ids)]

    return {
        "schema": VERDICT_SCHEMA,
        "status": "EXACT_MINIMUM_UNBLOCK_CUT_FOUND",
        "exact": True,
        "pass": True,
        "execution_authority": False,
        "promotion_authority": False,
        "proof_mode_transmutation": transmutation,
        "minimum_unblock_cut": {
            "blocker_ids": list(blocker_tuple),
            "blocker_count": blocker_count,
            "max_dependency_depth": max_depth,
            "parallel_critical_path_wall_clock_units": wall,
            "new_reality_units": reality,
            "selected_route_ids": list(route_ids),
            "selected_routes": selected,
            "weakest_selected_proof_mode": PROOF_MODE_ORDER[max_rank],
        },
        "objective_order": [
            "MINIMIZE_LONGEST_BLOCKER_DEPENDENCY_DEPTH",
            "MINIMIZE_PARALLEL_CRITICAL_PATH_WALL_CLOCK",
            "MINIMIZE_NEW_REALITY_INFORMATION",
            "MINIMIZE_WEAKEST_SELECTED_PROOF_MODE_RANK",
            "MINIMIZE_UNIQUE_BLOCKER_COUNT",
            "MINIMIZE_ROUTE_COUNT",
            "DETERMINISTIC_LEXICAL_TIEBREAK",
        ],
        "rejected_routes": rejected,
        "rule": (
            "CLOSE_ONLY_THIS_INTERNAL_UNBLOCK_CUT__THEN_RECOMPUTE__"
            "MATCHED_EXACT_OPUS_IS_LAST_RESORT_NOT_DEFAULT"
        ),
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    args = ap.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    out = compile_superproof(payload)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"] in {
        "EXACT_MINIMUM_UNBLOCK_CUT_FOUND",
        "EXTERNAL_IRREDUCIBLE_OR_FROZEN_UNIVERSE_INCOMPLETE",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
