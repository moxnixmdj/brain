#!/usr/bin/env python3
"""Label the unindexed runtime modules by whether anything uses them (read-only).

Reads out/gap_classified.csv. A RUNTIME_MODULE is USED if it has a __main__ block
or is imported by another tracked file (name match, coarse). Otherwise it is a
RETIRE_CANDIDATE, which still needs a human check before any change.
Output: out/runtime_triage.csv and out/runtime_triage_summary.json.
"""
import csv
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def main() -> None:
    with (OUT / "gap_classified.csv").open() as fh:
        rows = [r for r in csv.DictReader(fh) if r["group"] == "RUNTIME_MODULE"]
    for r in rows:
        used = r["has_main"] == "True" or int(r["imported_by_others"]) > 0
        r["label"] = "USED" if used else "RETIRE_CANDIDATE"

    with (OUT / "runtime_triage.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = {
        "runtime_modules": len(rows),
        "labels": dict(collections.Counter(r["label"] for r in rows)),
        "used_by_main_only": sum(1 for r in rows if r["has_main"] == "True" and int(r["imported_by_others"]) == 0),
        "used_by_import_only": sum(1 for r in rows if r["has_main"] != "True" and int(r["imported_by_others"]) > 0),
        "retire_candidate_lines": sum(int(r["lines"]) for r in rows if r["label"] == "RETIRE_CANDIDATE"),
    }
    (OUT / "runtime_triage_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
