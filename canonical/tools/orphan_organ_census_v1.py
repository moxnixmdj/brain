#!/usr/bin/env python3
"""Orphan-organ census: rank repository modules that no goal can reach.

The unified model knows about 2,857 modules but only routes a minority of
them. A module with no capability, no engine, and no harvested surface is
not "in the model" in any useful sense -- it is inventory. This tool ranks
that inventory so the next wiring decision is a measurement instead of a
guess.

Ranking is influence-first, not size-first. A 7,000-line module nobody
imports and nothing routes is usually historical; a 1,500-line module with
eight importers is load-bearing and unreachable, which is worse. The score
is deliberately simple and explainable:

    score = symbols * (1 + importers) * log2(1 + lines)

Usage:
    python3 canonical/tools/orphan_organ_census_v1.py
    python3 canonical/tools/orphan_organ_census_v1.py --min-lines 1000 --top 30
    python3 canonical/tools/orphan_organ_census_v1.py --json out.json

Reads the compiled artifact only. Runs no module it reports on, imports
nothing it ranks, writes nothing except the optional --json path. It grants
no capability and changes no authority: this is a report, not a receipt.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"

# Vendored third-party trees are dependencies, not hidden capabilities. They
# are counted separately so the headline is not inflated by code nobody in
# this repository wrote. Measured 2026-11-26: vendored is 21,441 lines, 3.2%
# of the unrouted total -- small enough that the headline survives the check,
# which is worth knowing rather than assuming.
VENDOR_PREFIXES = (
    "canonical/capabilities/internalized/",
    "vendor/",
    "third_party/",
    "node_modules/",
)

# The finishable target. 2,301 unrouted modules is not a plan, it is a mood.
# A module is load-bearing-and-unreachable if something imports it, or if it
# is large enough that nobody believes it is dead by accident. That set is
# small enough to name every member, and it is where "unified" has to start.
TARGET_MIN_IMPORTERS = 3
TARGET_MIN_LINES = 1000


def is_vendored(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in VENDOR_PREFIXES)


def _line_count(root: Path, rel: str) -> int:
    path = root / rel
    if not path.is_file():
        return 0
    try:
        return len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
    except OSError:
        return 0


def census(
    *,
    root: Path = ROOT,
    artifact: Path = ARTIFACT,
    min_lines: int = 0,
    min_symbols: int = 0,
    top: int = 40,
) -> dict[str, Any]:
    model = json.loads(artifact.read_text(encoding="utf-8"))
    routed_paths: set[str] = set()
    for row in model.get("capabilities") or []:
        p = str(row.get("path") or "")
        if p:
            routed_paths.add(p)
    for row in model.get("engines") or []:
        p = str(row.get("source_path") or "")
        if p:
            routed_paths.add(p)
    for row in model.get("harvested_capabilities") or []:
        p = str(row.get("path") or "")
        if p:
            routed_paths.add(p)

    index: dict[str, dict[str, Any]] = {}
    for section in ("source_index", "extended_source_index"):
        for row in model.get(section) or []:
            p = str(row.get("path") or "")
            if p and p not in index:
                index[p] = row

    total_lines = 0
    unrouted_lines = 0
    vendored_lines = vendored_unrouted = 0
    target_lines = 0
    orphans: list[dict[str, Any]] = []
    target_set: list[dict[str, Any]] = []
    for rel, row in index.items():
        lines = _line_count(root, rel)
        vendored = is_vendored(rel)
        total_lines += lines
        if vendored:
            vendored_lines += lines
        if rel in routed_paths:
            continue
        unrouted_lines += lines
        if vendored:
            vendored_unrouted += lines
        symbols = int(row.get("symbol_count") or 0)
        importers = int(row.get("imported_by_count") or 0)
        record = {
            "path": rel,
            "lines": lines,
            "symbols": symbols,
            "importers": importers,
            "vendored": vendored,
            "classification": str(row.get("classification") or ""),
        }
        if importers >= TARGET_MIN_IMPORTERS or lines >= TARGET_MIN_LINES:
            target_lines += lines
            target_set.append(record)
        if vendored:
            continue
        if lines < min_lines or symbols < min_symbols:
            continue
        score = symbols * (1 + importers) * math.log2(1 + lines)
        orphans.append({**record, "score": round(score, 2)})
    orphans.sort(key=lambda r: (-r["score"], -r["importers"], -r["lines"], r["path"]))
    target_set.sort(key=lambda r: (-r["importers"], -r["lines"], r["path"]))

    return {
        "schema": "BRAIN_ORPHAN_ORGAN_CENSUS_V1",
        "artifact_digest": (model.get("digest") or {}).get("value"),
        "indexed_modules": len(index),
        "routed_modules": len(routed_paths & set(index)),
        "unrouted_modules": sum(1 for p in index if p not in routed_paths),
        "indexed_lines": total_lines,
        "unrouted_lines": unrouted_lines,
        "routed_line_ratio": round(1 - (unrouted_lines / total_lines), 4) if total_lines else 0.0,
        "vendored_lines": vendored_lines,
        "vendored_unrouted_lines": vendored_unrouted,
        "vendored_share_of_unrouted": (
            round(vendored_unrouted / unrouted_lines, 4) if unrouted_lines else 0.0
        ),
        "first_party_unrouted_lines": unrouted_lines - vendored_unrouted,
        "target_set_modules": len(target_set),
        "target_set_lines": target_lines,
        "target_set_share_of_unrouted": (
            round(target_lines / unrouted_lines, 4) if unrouted_lines else 0.0
        ),
        "target_set": target_set[: max(1, top)],
        "ranked": orphans[: max(1, top)],
        "ranked_total": len(orphans),
        "authority": "NONE",
    }


def render(report: dict[str, Any]) -> str:
    out: list[str] = []
    out.append("ORPHAN ORGAN CENSUS")
    out.append(
        f"  indexed {report['indexed_modules']} modules / {report['indexed_lines']:,} lines"
    )
    out.append(
        f"  unrouted {report['unrouted_modules']} modules / {report['unrouted_lines']:,} lines"
        f"  ({100 * (1 - report['routed_line_ratio']):.1f}%)"
    )
    out.append(f"  routed line ratio {report['routed_line_ratio']:.4f}")
    out.append(
        f"  vendored {report['vendored_unrouted_lines']:,} lines"
        f"  ({100 * report['vendored_share_of_unrouted']:.1f}% of unrouted -- excluded below)"
    )
    out.append(
        f"  TARGET SET (importers>={TARGET_MIN_IMPORTERS} or lines>={TARGET_MIN_LINES}):"
        f" {report['target_set_modules']} modules / {report['target_set_lines']:,} lines"
        f"  ({100 * report['target_set_share_of_unrouted']:.1f}% of unrouted lines)"
    )
    out.append("")
    out.append("  -- target set, by importers --")
    out.append(f"  {'imp':>4} {'lines':>6} {'sym':>4}  module")
    for row in report["target_set"]:
        out.append(
            f"  {row['importers']:>4} {row['lines']:>6} {row['symbols']:>4}  {row['path']}"
        )
    out.append("")
    out.append("  -- first-party ranking, by influence score --")
    out.append(f"  {'score':>10} {'lines':>6} {'sym':>4} {'imp':>4}  module")
    for row in report["ranked"]:
        out.append(
            f"  {row['score']:>10.1f} {row['lines']:>6} {row['symbols']:>4} "
            f"{row['importers']:>4}  {row['path']}"
        )
    out.append("")
    out.append("  AUTHORITY NONE -- sandbox measurement, not a receipt")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-lines", type=int, default=0)
    ap.add_argument("--min-symbols", type=int, default=0)
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--json", type=str, default="")
    ns = ap.parse_args(argv)

    report = census(min_lines=ns.min_lines, min_symbols=ns.min_symbols, top=ns.top)
    print(render(report))
    if ns.json:
        Path(ns.json).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"\n  wrote {ns.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
