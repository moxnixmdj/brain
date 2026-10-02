"""Fail-closed authority guard for the live global residual frontier.

The residual scheduler is derived state. ACTIVE_TERMINAL_PROOF_BASIS_V1 is the
authority. This guard prevents admitted contracts from remaining in the live
work queue and prevents currently blocked contracts from silently disappearing.

It performs no promotion, execution, capability, or family credit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

BASIS_SCHEMA = "PROJECT_BRAIN_ACTIVE_TERMINAL_PROOF_BASIS_V1"
RESIDUAL_SCHEMA = "PROJECT_BRAIN_GLOBAL_RESIDUAL_PROOF_COMPILER_INPUT_V1"
VERDICT_SCHEMA = "PROJECT_BRAIN_RESIDUAL_FRONTIER_AUTHORITY_GUARD_VERDICT_V1"


def _fail(*errors: str, **extra: Any) -> dict[str, Any]:
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
    out.update(extra)
    return out


def validate_frontier(
    basis: Mapping[str, Any], residual: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(basis, Mapping):
        return _fail("BASIS_NOT_OBJECT")
    if not isinstance(residual, Mapping):
        return _fail("RESIDUAL_NOT_OBJECT")
    if basis.get("schema") != BASIS_SCHEMA:
        return _fail("BASIS_SCHEMA_INVALID")
    if residual.get("schema") != RESIDUAL_SCHEMA:
        return _fail("RESIDUAL_SCHEMA_INVALID")

    contracts = basis.get("contracts")
    if not isinstance(contracts, list) or not contracts:
        return _fail("BASIS_CONTRACTS_INVALID")

    errors: list[str] = []
    blocked: set[str] = set()
    admitted: set[str] = set()
    seen: set[str] = set()

    for i, raw in enumerate(contracts):
        if not isinstance(raw, Mapping):
            errors.append(f"CONTRACT_NOT_OBJECT:{i}")
            continue
        bid = raw.get("behavior_id")
        if not isinstance(bid, str) or not bid:
            errors.append(f"BEHAVIOR_ID_INVALID:{i}")
            continue
        if bid in seen:
            errors.append(f"BEHAVIOR_ID_DUPLICATE:{bid}")
            continue
        seen.add(bid)
        blockers = raw.get("blockers")
        if not isinstance(blockers, list) or any(
            not isinstance(x, str) or not x for x in blockers
        ):
            errors.append(f"CONTRACT_BLOCKERS_INVALID:{bid}")
            continue
        if blockers:
            blocked.add(bid)
        else:
            admitted.add(bid)

    obligations = residual.get("obligations")
    if (
        not isinstance(obligations, list)
        or any(not isinstance(x, str) or not x for x in obligations)
    ):
        errors.append("RESIDUAL_OBLIGATIONS_INVALID")
        obligations = []
    if len(set(obligations)) != len(obligations):
        errors.append("RESIDUAL_OBLIGATIONS_DUPLICATE")

    live = set(obligations)
    missing = sorted(blocked - live)
    stale = sorted(live - blocked)
    stale_admitted = sorted(live & admitted)
    unknown = sorted(live - seen)

    if missing:
        errors.append("MISSING_BLOCKED_OBLIGATIONS:" + ",".join(missing))
    if stale_admitted:
        errors.append("STALE_ADMITTED_OBLIGATIONS:" + ",".join(stale_admitted))
    if unknown:
        errors.append("UNKNOWN_RESIDUAL_OBLIGATIONS:" + ",".join(unknown))
    stale_other = sorted(set(stale) - set(stale_admitted) - set(unknown))
    if stale_other:
        errors.append("STALE_NONBLOCKED_OBLIGATIONS:" + ",".join(stale_other))

    routes = residual.get("routes")
    if not isinstance(routes, list):
        errors.append("RESIDUAL_ROUTES_INVALID")
        routes = []
    for i, route in enumerate(routes):
        if not isinstance(route, Mapping):
            errors.append(f"ROUTE_NOT_OBJECT:{i}")
            continue
        rid = route.get("id", str(i))
        covers = route.get("covers")
        if not isinstance(covers, list) or any(
            not isinstance(x, str) or not x for x in covers
        ):
            errors.append(f"ROUTE_COVERS_INVALID:{rid}")
            continue
        off_frontier = sorted(set(covers) - live)
        if off_frontier:
            errors.append(
                f"ROUTE_COVERS_OFF_FRONTIER:{rid}:" + ",".join(off_frontier)
            )

    if errors:
        return _fail(
            *errors,
            authoritative_blocked_obligations=sorted(blocked),
            live_residual_obligations=sorted(live),
            admitted_contracts=sorted(admitted),
        )

    return {
        "schema": VERDICT_SCHEMA,
        "status": "PASS__LIVE_RESIDUAL_FRONTIER_EXACTLY_MATCHES_ACTIVE_BLOCKED_CONTRACTS",
        "pass": True,
        "exact": True,
        "authoritative_blocked_obligations": sorted(blocked),
        "live_residual_obligations": sorted(live),
        "admitted_contracts": sorted(admitted),
        "blocked_obligation_count": len(blocked),
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "errors": [],
        "rule": (
            "ACTIVE_TERMINAL_PROOF_BASIS_IS_AUTHORITY__RESIDUAL_FRONTIER_MUST_"
            "EQUAL_EXACTLY_THE_SET_OF_CONTRACTS_WITH_NONEMPTY_BLOCKERS"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("basis", type=Path)
    ap.add_argument("residual", type=Path)
    args = ap.parse_args()
    basis = json.loads(args.basis.read_text(encoding="utf-8"))
    residual = json.loads(args.residual.read_text(encoding="utf-8"))
    out = validate_frontier(basis, residual)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
