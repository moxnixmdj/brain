#!/usr/bin/env python3
"""Give every uncovered (real gap) non-test .py file one label (read-only).

Reads out/real_gap.csv. Rules, first match wins:
  VERSIONED   -> CURRENT or SUPERSEDED, from out/version_families.csv
  EXPERIMENT  -> swe_probe_* or canonical/experiments/
  GUARD       -> execution_guard/
  HELPER      -> file name starts with _
  USED        -> canonical/runtime module with __main__ or an importer
  RETIRE_CANDIDATE -> canonical/runtime module with neither
  UNUSED_SCOPE -> any other uncovered file (capabilities, research, ...), needs review
Writes out/real_gap_labels.csv and out/real_gap_labels_summary.json.
"""
import csv
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


def load(name):
    with (OUT / name).open() as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    version = {r["path"]: r["status"] for r in load("version_families.csv")}
    runtime = {r["path"]: r for r in load("gap_classified.csv")}
    triage = {r["path"]: r["label"] for r in load("runtime_triage.csv")}
    gap = load("real_gap.csv")

    rows = []
    for g in gap:
        p = g["path"]
        name = p.rsplit("/", 1)[-1]
        if p.startswith("canonical/unified_model/gap/"):
            label, basis = "ANALYSIS_TOOL", "path"
        elif p in version:
            label, basis = version[p], "version_family"
        elif p.startswith(("swe_probe_", "canonical/experiments/")):
            label, basis = "EXPERIMENT_OR_PROBE", "path"
        elif p.startswith("execution_guard/"):
            label, basis = "GUARD", "path"
        elif name.startswith("_"):
            label, basis = "HELPER", "name"
        elif p.startswith("canonical/runtime/") and p in triage:
            label, basis = triage[p], "runtime_triage"
        else:
            label, basis = "OUTSIDE_RUNTIME_REVIEW", "outside_runtime_rules"
        rows.append({"path": p, "label": label, "basis": basis})

    with (OUT / "real_gap_labels.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["path", "label", "basis"])
        w.writeheader()
        w.writerows(rows)

    summary = {
        "uncovered_files": len(rows),
        "labelled_exactly_once": len({r["path"] for r in rows}),
        "labels": dict(collections.Counter(r["label"] for r in rows).most_common()),
        "unused_scope_by_dir": collections.Counter(
            "/".join(r["path"].split("/")[:2]) for r in rows if r["label"] == "UNUSED_SCOPE"
        ).most_common(),
    }
    (OUT / "real_gap_labels_summary.json").write_text(json.dumps(summary, indent=2, default=list) + "\n")
    print(json.dumps(summary, indent=2, default=list))


if __name__ == "__main__":
    main()
