#!/usr/bin/env python3
"""Drive hidden capability surfaces through the repository's own receipt lane.

The census (``harvest_hidden_capabilities_v1``) finds modules the registries
never declared.  This driver does the next thing the project's architecture
requires: it *runs* them and issues the lane's content-addressed execution
receipts, then stages the results in the receipt projection, additively.

It deliberately reimplements none of the evidence machinery:

* invocation goes through ``capability_receipt_lane_v1.execute_and_receipt``,
  so a contract module is called in-process and a CLI module is executed by
  ``bound_capabilities/cli_command.py`` -- the same adapters the creature uses;
* receipt paths, projection entries and tree restoration are the lane's own
  functions, so the evidence is byte-identical to what the lane would issue;
* nothing is promoted.  A producer receipt is self-issued and the loader's
  admission gate requires a *different* identity with signed GitHub OIDC claims
  to re-run it.  What this adds is candidates: the independent verifier can only
  reproduce what a producer receipt already describes, and until now it had no
  way to see a module that owns no registry row.

Projection merge is additive: an existing entry is never replaced or deleted.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CENSUS = "canonical/capabilities/hidden/HIDDEN_CAPABILITY_CENSUS_V1.json"
REPORT = "canonical/capabilities/hidden/HARVEST_REPORT_V1.json"


def _lane(root: Path):
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from canonical.runtime import capability_receipt_lane_v1 as lane
    return lane


def harvest(root: Path, census: dict[str, Any], *, kinds: tuple[str, ...],
            limit: int, domains: tuple[str, ...], ran_by: str) -> dict[str, Any]:
    lane = _lane(root)
    rows = [
        r for r in census.get("hidden") or []
        if r.get("kind") in kinds
        and (not domains or any(r["path"].startswith(d) for d in domains))
    ]
    if limit:
        rows = rows[:limit]

    before = lane._changed_paths(str(root))
    receipts: list[dict[str, Any]] = []
    failures: dict[str, list[str]] = {}

    started = time.perf_counter()
    for row in rows:
        cid, path, kind = row["id"], row["path"], row["kind"]
        entrypoint = row.get("entrypoint") or ("run" if kind == "cli" else "run")
        try:
            receipt = lane.execute_and_receipt(cid, path, entrypoint, str(root), ran_by, kind)
        except BaseException as exc:  # noqa: BLE001 - a failed probe is data
            failures.setdefault(type(exc).__name__, []).append(path)
            continue
        if receipt is None:
            failures.setdefault("DID_NOT_RUN", []).append(path)
            continue
        receipt["receipt_path"] = lane.receipt_path_for(cid)
        out = root / receipt["receipt_path"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(receipt, indent=1, sort_keys=True), encoding="utf-8")
        receipts.append(receipt)
    elapsed = time.perf_counter() - started

    # Probing executes real modules; some write reports or state as a side effect.
    reverted = lane.restore_tree(str(root), before, ("astra_runtime/evidence/CAPABILITY__",
                                                     "astra_runtime/instances/"))

    # Additive projection merge: derived entries only, existing rows untouched.
    projection_path = root / lane.PROJECTION
    try:
        projection = json.loads(projection_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        projection = {"schema": "PROJECT_BRAIN_CAPABILITY_RECEIPT_PROJECTION_V1", "entries": {}}
    entries = projection.setdefault("entries", {})
    added = 0
    for receipt in receipts:
        cid = receipt["capability_id"]
        if cid in entries:
            continue
        entries[cid] = lane.projection_entry(receipt)
        added += 1
    projection["count"] = len(entries)
    projection["harvested_entries"] = sum(
        1 for cid in entries if cid.endswith(".hidden.v1")
    )
    projection_path.write_text(
        json.dumps(projection, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )

    by_domain: dict[str, int] = {}
    for receipt in receipts:
        domain = receipt["module_path"].split("/")[0]
        if receipt["module_path"].startswith("canonical/"):
            parts = receipt["module_path"].split("/")
            domain = "canonical/" + (parts[1] if len(parts) > 1 else "")
        by_domain[domain] = by_domain.get(domain, 0) + 1

    return {
        "schema": "PROJECT_BRAIN_HIDDEN_CAPABILITY_HARVEST_REPORT_V1",
        "candidates": len(rows),
        "kinds": list(kinds),
        "receipts_issued": len(receipts),
        "receipts_by_domain": dict(sorted(by_domain.items())),
        "failures_by_reason": {k: len(v) for k, v in sorted(failures.items())},
        "failure_sample": {k: v[:8] for k, v in sorted(failures.items())},
        "wall_time_s": round(elapsed, 3),
        "throughput_per_s": round(len(rows) / elapsed, 2) if elapsed else None,
        "projection_entries_added": added,
        "projection_total_entries": len(entries),
        "status_flipped": False,
        "registry_written": False,
        "probe_side_effects_reverted": len(reverted),
        "reverted_sample": reverted[:10],
        "ran_by": ran_by,
        "admission": "PENDING_INDEPENDENT_VERIFICATION",
        "note": ("producer receipts only; a different identity with signed GitHub OIDC "
                 "claims must re-run these before the loader admits anything"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--census", default=CENSUS)
    ap.add_argument("--kinds", default="contract,cli")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--domains", default="", help="comma-separated path prefixes")
    ap.add_argument("--ran-by", default=os.environ.get("BRAIN_RUNNER_IDENTITY", "harvest-local-session"))
    ap.add_argument("--report", default=REPORT)
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    census = json.loads((root / args.census).read_text(encoding="utf-8"))
    report = harvest(
        root, census,
        kinds=tuple(k.strip() for k in args.kinds.split(",") if k.strip()),
        limit=args.limit,
        domains=tuple(d.strip() for d in args.domains.split(",") if d.strip()),
        ran_by=args.ran_by,
    )
    out = root / args.report
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "candidates", "receipts_issued", "receipts_by_domain", "failures_by_reason",
        "wall_time_s", "projection_entries_added", "admission")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
