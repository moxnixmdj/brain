from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_TERMINAL_AUTOPILOT_V1"
TERMINAL_STATES = {"CLOSED", "PROMOTED"}


def _closed_dependencies(dependencies: list[str], closed: set[str]) -> bool:
    return set(dependencies).issubset(closed)


def _lease(kind: str, action_id: str) -> str:
    return f"terminal-autopilot-v1::{kind}::{action_id}"


def plan(manifest: dict[str, Any]) -> dict[str, Any]:
    try:
        if manifest.get("zero_incremental_spend_hard_stop") is not True:
            raise ValueError("ZERO_SPEND_HARD_STOP_REQUIRED")
        max_concurrency = manifest.get("max_concurrency", 16)
        if isinstance(max_concurrency, bool) or not isinstance(max_concurrency, int) or max_concurrency < 1:
            raise ValueError("MAX_CONCURRENCY_INVALID")
        obligations = manifest.get("obligations")
        blockers = manifest.get("blockers", [])
        routes = manifest.get("routes", [])
        active_jobs = manifest.get("active_jobs", [])
        if not isinstance(obligations, list) or not isinstance(blockers, list) or not isinstance(routes, list):
            raise ValueError("MANIFEST_COLLECTION_INVALID")
        if not isinstance(active_jobs, list):
            raise ValueError("ACTIVE_JOBS_INVALID")
    except ValueError as exc:
        return {"schema": SCHEMA, "pass": False, "classification": "INVALID_MANIFEST",
                "reason": str(exc), "terminal_credit": False}

    by_id: dict[str, dict[str, Any]] = {}
    for row in obligations:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            return {"schema": SCHEMA, "pass": False, "classification": "INVALID_OBLIGATION",
                    "terminal_credit": False}
        oid = row["id"]
        if oid in by_id:
            return {"schema": SCHEMA, "pass": False, "classification": "DUPLICATE_OBLIGATION",
                    "reason": oid, "terminal_credit": False}
        by_id[oid] = row

    closed = {oid for oid, row in by_id.items() if row.get("status") in TERMINAL_STATES}
    open_ids = {oid for oid, row in by_id.items() if row.get("status") not in TERMINAL_STATES}

    if manifest.get("terminal") is True:
        return {
            "schema": SCHEMA,
            "pass": True,
            "classification": "TERMINAL_ALREADY_TRUE",
            "dispatch": [],
            "verify": [],
            "promote": [],
            "cancel": sorted(j.get("id") for j in active_jobs if isinstance(j, dict) and isinstance(j.get("id"), str)),
            "terminal_credit": False,
        }

    active_leases = {
        j.get("lease_key") for j in active_jobs
        if isinstance(j, dict) and isinstance(j.get("lease_key"), str)
    }

    verify = []
    promote = []
    candidates = []

    for oid, row in by_id.items():
        status = row.get("status")
        if status == "RESULT_PRESENT":
            verify.append({"kind": "VERIFY", "obligation_ids": [oid], "action_id": f"verify::{oid}"})
        elif status == "VERIFIED":
            promote.append({"kind": "PROMOTE", "obligation_ids": [oid], "action_id": f"promote::{oid}"})

    blocker_for: dict[str, set[str]] = defaultdict(set)
    for blocker in blockers:
        if not isinstance(blocker, dict) or not isinstance(blocker.get("id"), str):
            continue
        unlocks = [x for x in blocker.get("unlocks", []) if x in open_ids]
        if blocker.get("status") == "OPEN" and unlocks:
            for oid in unlocks:
                blocker_for[oid].add(blocker["id"])
            action_id = blocker.get("repair_action") or ("repair::" + blocker["id"])
            lease_key = _lease("REPAIR", action_id)
            if lease_key not in active_leases:
                candidates.append({
                    "kind": "REPAIR",
                    "action_id": action_id,
                    "blocker_id": blocker["id"],
                    "unlocks": sorted(unlocks),
                    "discharge_count": 0,
                    "unlock_count": len(unlocks),
                    "estimated_wall_clock_units": float(blocker.get("estimated_wall_clock_units", 1.0)),
                    "lease_key": lease_key,
                })

    for route in routes:
        if not isinstance(route, dict) or route.get("status") != "OPEN" or not isinstance(route.get("id"), str):
            continue
        deps = route.get("dependencies", [])
        if not isinstance(deps, list) or not _closed_dependencies(deps, closed):
            continue
        discharges = sorted(set(route.get("can_discharge", [])) & open_ids)
        if not discharges:
            continue
        action_id = "route::" + route["id"]
        lease_key = _lease("ROUTE", action_id)
        if lease_key in active_leases:
            continue
        candidates.append({
            "kind": "ROUTE_RACE",
            "action_id": action_id,
            "route_id": route["id"],
            "obligation_ids": discharges,
            "discharge_count": len(discharges),
            "unlock_count": 0,
            "estimated_wall_clock_units": float(route.get("estimated_wall_clock_units", 1.0)),
            "lease_key": lease_key,
        })

    groups: dict[str, list[str]] = defaultdict(list)
    singles: list[str] = []
    for oid in sorted(open_ids):
        row = by_id[oid]
        if row.get("status") not in {"OPEN", "BLOCKED"}:
            continue
        if blocker_for.get(oid):
            continue
        deps = row.get("dependencies", [])
        if not isinstance(deps, list) or not _closed_dependencies(deps, closed):
            continue
        key = row.get("shared_measurement_key")
        if isinstance(key, str) and key:
            groups[key].append(oid)
        else:
            singles.append(oid)

    direct_sets = [[oid] for oid in singles] + [sorted(v) for _, v in sorted(groups.items())]
    for ids in direct_sets:
        action_id = "evidence::" + "+".join(ids)
        lease_key = _lease("EVIDENCE", action_id)
        if lease_key in active_leases:
            continue
        wall = min(float(by_id[oid].get("estimated_wall_clock_units", 1.0)) for oid in ids)
        candidates.append({
            "kind": "EVIDENCE",
            "action_id": action_id,
            "obligation_ids": ids,
            "discharge_count": len(ids),
            "unlock_count": 0,
            "estimated_wall_clock_units": wall,
            "lease_key": lease_key,
        })

    def score(item: dict[str, Any]) -> tuple[float, int, int, float, str]:
        wall = max(float(item["estimated_wall_clock_units"]), 1e-9)
        leverage = (item.get("discharge_count", 0) + item.get("unlock_count", 0)) / wall
        repair_bias = 1 if item["kind"] == "REPAIR" else 0
        return (-leverage, -item.get("discharge_count", 0), -repair_bias, wall, item["action_id"])

    candidates.sort(key=score)
    dispatch = candidates[:max_concurrency]

    cancel = []
    for job in active_jobs:
        if not isinstance(job, dict) or not isinstance(job.get("id"), str):
            continue
        targets = set(job.get("obligation_ids", []))
        if targets and targets.issubset(closed):
            cancel.append(job["id"])

    return {
        "schema": SCHEMA,
        "pass": True,
        "classification": "AUTOPILOT_PLAN",
        "open_obligation_count": len(open_ids),
        "dispatch": dispatch,
        "verify": verify,
        "promote": promote,
        "cancel": sorted(set(cancel)),
        "recompute_trigger": "AFTER_EVERY_RESULT_VERIFICATION_PROMOTION_BLOCKER_CLOSURE_OR_TERMINAL_RECEIPT",
        "terminal_credit": False,
        "rule": "PLAN_ONLY__EXECUTION_VERIFICATION_AND_PROMOTION_REMAIN_SEPARATELY_AUTHORIZED_AND_FAIL_CLOSED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    out = plan(json.loads(args.manifest.read_text(encoding="utf-8")))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
