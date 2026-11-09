#!/usr/bin/env python3
"""Classify each law in canonical/laws by the status the file itself states (read-only).

Reads the first 25 lines of each law. Looks for SUPERSEDED, HISTORICAL, or CURRENT
in the Status line or the opening blockquote. Writes out/law_status.csv and a summary.
"""
import csv
import collections
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TREE = HERE.parents[2]
LAWS = TREE / "canonical/laws"


def classify(head: str) -> str:
    status_lines = [l for l in head.splitlines() if re.match(r"^\s*(Status:|>)", l)]
    text = " ".join(status_lines).upper()
    if "SUPERSEDED" in text:
        return "SUPERSEDED"
    if "HISTORICAL" in text:
        return "HISTORICAL"
    if re.search(r"\bCURRENT\b", text):
        return "CURRENT"
    return "UNSTATED"


def main() -> None:
    rows = []
    for path in sorted(LAWS.glob("*.md")):
        head = "\n".join(path.read_text(errors="replace").splitlines()[:25])
        rows.append({"file": path.name, "status": classify(head)})

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "law_status.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "status"])
        w.writeheader()
        w.writerows(rows)

    summary = {"laws": len(rows), "by_status": dict(collections.Counter(r["status"] for r in rows))}
    (OUT / "law_status_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
