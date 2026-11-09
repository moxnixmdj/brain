#!/usr/bin/env python3
"""Does the front door find each verified capability from its own declared triggers? (read-only)

For each VERIFIED_BOUND_CAPABILITY in the compiled model, take its declared triggers
and route them through UnifiedModel.route(). Record whether the best match is the
capability itself and whether the router reports it as confident. Nothing is executed.
Writes out/route_self_check.csv and a summary JSON.
"""
import csv
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TREE = HERE.parents[2]
sys.path.insert(0, str(TREE))

from canonical.runtime import brain_unified_model_v1 as bum  # noqa: E402


def main() -> None:
    model = bum.open_model()
    raw = json.loads((TREE / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json").read_text())
    verified = [c for c in raw["capabilities"] if c.get("registry_status") == "VERIFIED_BOUND_CAPABILITY"]

    rows = []
    for cap in verified:
        triggers = cap.get("triggers") or []
        goal = " ".join(str(t) for t in triggers) if isinstance(triggers, list) else str(triggers)
        if not goal.strip():
            rows.append({"capability_id": cap["id"], "trigger_text": "", "result": "NO_TRIGGERS",
                         "best_id": "", "confident": False})
            continue
        r = model.route(goal, top_k=3)
        best = r.get("best") or {}
        if best.get("id") == cap["id"]:
            result = "FOUND_SELF_CONFIDENT" if r.get("confident") else "FOUND_SELF_NOT_CONFIDENT"
        else:
            result = "MISROUTED_OR_NOT_FOUND"
        rows.append({"capability_id": cap["id"], "trigger_text": goal[:160], "result": result,
                     "best_id": best.get("id", ""), "confident": bool(r.get("confident"))})

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "route_self_check.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = {
        "verified_bound_capabilities": len(verified),
        "results": dict(collections.Counter(r["result"] for r in rows)),
        "caveat": "routes each capability's declared triggers; does not execute anything",
    }
    (OUT / "route_self_check_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
