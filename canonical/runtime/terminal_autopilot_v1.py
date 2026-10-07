from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

SCHEMA = "PROJECT_BRAIN_TERMINAL_AUTOPILOT_V1"
TERMINAL_STATES = {"CLOSED", "PROMOTED"}
DEFAULT_QUOTIENT = "canonical/governance/FROZEN_19_ACCEPTANCE_PROOF_SHAPE_QUOTIENT_20261007_V1.json"
ACTION_INTENT_DIR = "canonical/action_intents"
CURRENT_AUTHORITY = "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
SCIENCE_OBLIGATION = "TB_SCIENCE_GE_58_7"


def _closed_dependencies(dependencies: list[str], closed: set[str]) -> bool:
    return set(dependencies).issubset(closed)


def _lease(kind: str, action_id: str) -> str:
    return f"terminal-autopilot-v1::{kind}::{action_id}"


def _intent_targets(intent: dict[str, Any], path: Path, open_ids: set[str]) -> list[str]:
    targets: set[str] = set()
    pred = intent.get("predicate")
    if isinstance(pred, str) and pred in open_ids:
        targets.add(pred)
    listed = intent.get("obligation_ids")
    if isinstance(listed, list):
        targets.update(x for x in listed if isinstance(x, str) and x in open_ids)
    if "TB_SCIENCE" in path.name and "TB_SCIENCE_GE_58_7" in open_ids:
        targets.add("TB_SCIENCE_GE_58_7")
    return sorted(targets)


def _live_authority_truth(root: Path) -> dict[str, Any]:
    path = root / CURRENT_AUTHORITY
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    live = value.get("live_truth") if isinstance(value, dict) else None
    return dict(live) if isinstance(live, dict) else {}


def _science_execution_authority_active(live_truth: dict[str, Any]) -> bool | None:
    if not live_truth:
        return None
    return any(
        key.startswith("tb_science_rank")
        and key.endswith("_authority_active")
        and value is True
        for key, value in live_truth.items()
    )


def _science_repair_action(live_truth: dict[str, Any]) -> str:
    if (
        live_truth.get("tb_science_planner_grammar_repair_candidate_bound") is True
        and live_truth.get("tb_science_planner_grammar_repair_live_transport_verified") is not True
    ):
        return "repair::TB_SCIENCE_PLANNER_TRANSPORT_PREFLIGHT"
    return "repair::TB_SCIENCE_CURRENT_AUTHORITY_PREFLIGHT"


def build_manifest_from_repo(repo_root: str | Path, *, max_concurrency: int = 16) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    quotient_path = root / DEFAULT_QUOTIENT
    quotient = json.loads(quotient_path.read_text(encoding="utf-8"))
    open_rows = quotient.get("independent_open_obligations")
    if not isinstance(open_rows, list) or not all(isinstance(x, str) and x for x in open_rows):
        raise ValueError("CURRENT_QUOTIENT_OPEN_OBLIGATIONS_INVALID")

    open_ids = set(open_rows)
    statuses = {oid: "OPEN" for oid in open_rows}
    active_jobs: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    live_truth = _live_authority_truth(root)
    science_authority_active = _science_execution_authority_active(live_truth)

    intent_dir = root / ACTION_INTENT_DIR
    if intent_dir.is_dir():
        for path in sorted(intent_dir.glob("*.json")):
            try:
                intent = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            status = str(intent.get("status") or "").upper()
            if not any(token in status for token in ("ACTIVE", "READY", "STARTED", "PREEXPOSURE")):
                continue
            targets = _intent_targets(intent, path, open_ids)
            if science_authority_active is False and SCIENCE_OBLIGATION in targets:
                targets = [x for x in targets if x != SCIENCE_OBLIGATION]
            if not targets:
                continue
            for oid in targets:
                statuses[oid] = "RUNNING"
            action_id = str(intent.get("action_id") or path.stem)
            active_jobs.append({
                "id": action_id,
                "lease_key": str(intent.get("blocker_lease_key") or f"existing-intent::{action_id}"),
                "obligation_ids": targets,
                "source_path": str(path.relative_to(root)).replace("\\", "/"),
            })

    if (
        SCIENCE_OBLIGATION in open_ids
        and live_truth
        and science_authority_active is False
        and statuses[SCIENCE_OBLIGATION] != "RUNNING"
    ):
        statuses[SCIENCE_OBLIGATION] = "BLOCKED"
        blockers.append({
            "id": "TB_SCIENCE_CURRENT_EXECUTION_GATE",
            "status": "OPEN",
            "unlocks": [SCIENCE_OBLIGATION],
            "repair_action": _science_repair_action(live_truth),
            "estimated_wall_clock_units": 1.0,
            "reason": (
                "CURRENT_ONE_USE_AUTHORITY_INACTIVE_OR_CONSUMED__"
                "REPAIR_AND_VERIFY_TRANSPORT_BEFORE_NEXT_SLOT"
            ),
        })

    obligations = [{"id": oid, "status": statuses[oid]} for oid in open_rows]
    return {
        "terminal": len(open_rows) == 0,
        "zero_incremental_spend_hard_stop": True,
        "max_concurrency": max_concurrency,
        "obligations": obligations,
        "blockers": blockers,
        "routes": [{
            "id": "SCOPE_COMPLETE_UNIVERSAL_COVER",
            "status": "OPEN" if open_rows else "CLOSED",
            "can_discharge": list(open_rows),
        }],
        "active_jobs": active_jobs,
        "source_quotient": DEFAULT_QUOTIENT,
    }


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
            "schema": SCHEMA, "pass": True, "classification": "TERMINAL_ALREADY_TRUE",
            "dispatch": [], "verify": [], "promote": [],
            "cancel": sorted(j.get("id") for j in active_jobs if isinstance(j, dict) and isinstance(j.get("id"), str)),
            "terminal_credit": False,
        }

    active_leases = {
        j.get("lease_key") for j in active_jobs
        if isinstance(j, dict) and isinstance(j.get("lease_key"), str)
    }
    active_targets: set[str] = set()
    for job in active_jobs:
        if isinstance(job, dict):
            active_targets.update(x for x in job.get("obligation_ids", []) if isinstance(x, str))

    verify: list[dict[str, Any]] = []
    promote: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

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
                    "kind": "REPAIR", "action_id": action_id, "blocker_id": blocker["id"],
                    "unlocks": sorted(unlocks), "discharge_count": 0, "unlock_count": len(unlocks),
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
            "kind": "ROUTE_RACE", "action_id": action_id, "route_id": route["id"],
            "obligation_ids": discharges, "discharge_count": len(discharges), "unlock_count": 0,
            "estimated_wall_clock_units": float(route.get("estimated_wall_clock_units", 1.0)),
            "lease_key": lease_key,
        })

    groups: dict[str, list[str]] = defaultdict(list)
    singles: list[str] = []
    for oid in sorted(open_ids):
        row = by_id[oid]
        if row.get("status") not in {"OPEN", "BLOCKED"}:
            continue
        if oid in active_targets or blocker_for.get(oid):
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
            "kind": "EVIDENCE", "action_id": action_id, "obligation_ids": ids,
            "discharge_count": len(ids), "unlock_count": 0,
            "estimated_wall_clock_units": wall, "lease_key": lease_key,
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
        "schema": SCHEMA, "pass": True, "classification": "AUTOPILOT_PLAN",
        "open_obligation_count": len(open_ids), "active_target_count": len(active_targets),
        "dispatch": dispatch, "verify": verify, "promote": promote, "cancel": sorted(set(cancel)),
        "recompute_trigger": "AFTER_EVERY_RESULT_VERIFICATION_PROMOTION_BLOCKER_CLOSURE_ACTION_INTENT_OR_TERMINAL_RECEIPT",
        "terminal_credit": False,
        "rule": "PLAN_ONLY__EXECUTION_VERIFICATION_AND_PROMOTION_REMAIN_SEPARATELY_AUTHORIZED_AND_FAIL_CLOSED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", nargs="?", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--max-concurrency", type=int, default=16)
    args = parser.parse_args()
    if (args.manifest is None) == (args.repo_root is None):
        parser.error("provide exactly one of manifest or --repo-root")
    if args.repo_root is not None:
        manifest = build_manifest_from_repo(args.repo_root, max_concurrency=args.max_concurrency)
    else:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    out = plan(manifest)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
