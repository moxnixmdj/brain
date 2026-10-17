#!/usr/bin/env python3
"""Classify adapter modules present on disk but not referenced by the registry.

The earlier "25 missing capabilities" claim was wrong because it compared file
names without checking whether a bound capability already covered the same
ground.  This sorts them mechanically instead:

  SUPERSEDED     -- a bound capability already covers this (name overlap)
  BINDABLE       -- has run(args, root), network-free, nothing else does it
  NEEDS_WRAPPER  -- real implementation, but no run(args, root) entrypoint
  NEEDS_NETWORK  -- does network I/O, so it cannot be bound or tested here

Measurement only.  This edits nothing.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "canonical" / "runtime" / "BOUND_CAPABILITY_REGISTRY_V1.json"
BC = ROOT / "canonical" / "runtime" / "bound_capabilities"

REGISTRY = json.loads(REG.read_text(encoding="utf-8"))["capabilities"]
BOUND = {e.get("adapter_module") for e in REGISTRY.values()}

NETWORK = re.compile(r"\b(urllib|requests|http\.client|socket|urlopen|aiohttp|httpx)\b")
SUBPROC = re.compile(r"\b(subprocess|Popen|check_output|os\.system)\b")


def toks(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) > 2}


def analyse(path: Path) -> dict:
    src = path.read_text(encoding="utf-8", errors="replace")
    try:
        fns = [n.name for n in ast.parse(src).body if isinstance(n, ast.FunctionDef)]
    except SyntaxError:
        fns = []
    return {
        "functions": fns,
        "has_run": "run" in fns,
        "network": bool(NETWORK.search(src)),
        "subprocess": bool(SUBPROC.search(src)),
    }


def bucket(v: dict) -> str:
    if v["overlap"] >= 2:
        return "SUPERSEDED"
    if not v["has_run"]:
        return "NEEDS_WRAPPER"
    if v["network"]:
        return "NEEDS_NETWORK"
    return "BINDABLE"


def main() -> int:
    report: dict[str, dict] = {}
    for path in sorted(BC.glob("*.py")):
        if path.stem in BOUND or path.stem.startswith("_"):
            continue
        info = analyse(path)
        mine = toks(path.stem)
        best, score = None, 0
        for cid in REGISTRY:
            s = len(mine & toks(cid))
            if s > score:
                best, score = cid, s
        report[path.stem] = {**info, "closest_bound": best, "overlap": score}

    order = {"BINDABLE": 0, "NEEDS_WRAPPER": 1, "NEEDS_NETWORK": 2, "SUPERSEDED": 3}
    rows = sorted(report.items(), key=lambda kv: (order[bucket(kv[1])], kv[0]))

    print(f"unbound adapter modules: {len(report)}")
    print()
    counts: dict[str, int] = {}
    for name, v in rows:
        b = bucket(v)
        counts[b] = counts.get(b, 0) + 1
        print(f"{b:14s} {name}")
        print(f"{'':14s}   run={v['has_run']}  net={v['network']}  subprocess={v['subprocess']}")
        print(f"{'':14s}   closest bound: {v['closest_bound']}  (overlap {v['overlap']})")
    print()
    print("counts:", counts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
