#!/usr/bin/env python3
"""Corrected gap: non-test .py files NOT covered by the unified model (read-only).

The compiler covers a file in two ways: as a source_index row (canonical/runtime
modules that are not capabilities), or as a capability's provenance.source_path.
This script uses both. Writes out/real_gap.csv and out/real_gap_summary.json.
"""
import csv
import collections
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TREE = HERE.parents[2]
MODEL = TREE / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"


def main() -> None:
    model = json.loads(MODEL.read_text())
    src = {e["path"] for e in model["source_index"]}
    cap = {
        (c.get("provenance") or {}).get("source_path")
        for c in model["capabilities"]
    }
    cap.discard(None)

    tracked = subprocess.run(
        ["git", "-C", str(TREE), "ls-files", "*.py"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    nontest = [p for p in tracked if not p.startswith(("canonical/tests/", "tests/"))]
    gap = [p for p in nontest if p not in src and p not in cap]

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "real_gap.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["path", "directory"])
        for p in gap:
            w.writerow([p, "/".join(p.split("/")[:2])])

    summary = {
        "nontest_py": len(nontest),
        "covered_by_index": len([p for p in nontest if p in src]),
        "covered_by_capability_source_path": len([p for p in nontest if p in cap and p not in src]),
        "uncovered": len(gap),
        "uncovered_by_dir": collections.Counter("/".join(p.split("/")[:2]) for p in gap).most_common(),
        "note": "registry ids (.auto.v1) may cover more modules; not counted here, so uncovered may be overstated",
    }
    (OUT / "real_gap_summary.json").write_text(json.dumps(summary, indent=2, default=list) + "\n")
    print(json.dumps(summary, indent=2, default=list))


if __name__ == "__main__":
    main()
