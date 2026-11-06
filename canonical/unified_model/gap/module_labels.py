#!/usr/bin/env python3
"""One label per tracked .py file, merged from the existing gap outputs (read-only).

Precedence: TEST > INDEXED (in the unified model's source index) > VERSIONED > RUNTIME > other.
Writes out/module_labels.csv and out/module_labels_summary.json, and checks coverage:
every tracked .py file appears exactly once.
"""
import csv
import collections
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TREE = HERE.parents[2]  # repo root


def load_csv(name):
    with (OUT / name).open() as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    tracked = subprocess.run(
        ["git", "-C", str(TREE), "ls-files", "*.py"],
        capture_output=True, text=True, check=True,
    ).stdout.split()

    model_index = json.loads((TREE / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json").read_text())["source_index"]
    indexed = {e["path"]: e.get("classification", "") for e in model_index}
    versions = {r["path"]: r["status"] for r in load_csv("version_families.csv")}
    runtime = {r["path"]: r["label"] for r in load_csv("runtime_triage.csv")}
    gap_group = {r["path"]: r["group"] for r in load_csv("gap_classified.csv")}

    rows = []
    for p in tracked:
        if p.startswith(("canonical/tests/", "tests/")):
            label, basis = "TEST", "path"
        elif p.startswith("canonical/unified_model/gap/"):
            label, basis = "ANALYSIS_TOOL", "path"
        elif p in indexed:
            label, basis = "INDEXED", indexed[p]
        elif p in versions:
            label, basis = versions[p], "version_family"
        elif p.startswith("canonical/runtime/") and p in runtime:
            label, basis = runtime[p], "runtime_triage"
        else:
            label, basis = gap_group.get(p, "UNCLASSIFIED"), "gap_group"
            if not p.startswith("canonical/runtime/") and label == "RUNTIME_MODULE":
                label = "OUTSIDE_RUNTIME_REVIEW"
        rows.append({"path": p, "label": label, "basis": basis})

    paths = [r["path"] for r in rows]
    assert len(paths) == len(set(paths)) == len(tracked), "coverage check failed"

    with (OUT / "module_labels.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["path", "label", "basis"])
        w.writeheader()
        w.writerows(rows)

    summary = {
        "tracked_py_files": len(tracked),
        "labelled_exactly_once": len(paths),
        "unclassified": sum(1 for r in rows if r["label"] == "UNCLASSIFIED"),
        "labels": dict(collections.Counter(r["label"] for r in rows).most_common()),
    }
    (OUT / "module_labels_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
