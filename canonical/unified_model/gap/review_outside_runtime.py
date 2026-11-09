#!/usr/bin/env python3
"""Sort OUTSIDE_RUNTIME_REVIEW files by whether any tracked file mentions them (read-only).

For each such file, count tracked non-.py files (JSON, MD, YAML, ...) that contain its
repo path, and tracked .py files that contain its path or stem as text (not an import).
Writes out/outside_runtime_review.csv and a summary JSON.
"""
import csv
import collections
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TREE = HERE.parents[2]


def main() -> None:
    with (OUT / "real_gap_labels.csv").open() as fh:
        targets = [r["path"] for r in csv.DictReader(fh) if r["label"] == "OUTSIDE_RUNTIME_REVIEW"]

    tracked = subprocess.run(
        ["git", "-C", str(TREE), "ls-files"], capture_output=True, text=True, check=True
    ).stdout.split()
    # Exclude this session's own gap outputs: they list every path and would match all of them.
    own = "canonical/unified_model/gap/"
    data_files = [p for p in tracked if not p.endswith(".py") and not p.startswith(".git") and not p.startswith(own)]
    py_files = [p for p in tracked if p.endswith(".py") and not p.startswith(own)]

    blobs = {}
    for p in data_files + py_files:
        try:
            blobs[p] = (TREE / p).read_text(errors="ignore")
        except OSError:
            pass

    rows = []
    for t in targets:
        stem = Path(t).stem
        data_refs = [p for p in data_files if p in blobs and t in blobs[p]]
        py_refs = [p for p in py_files if p != t and p in blobs and (t in blobs[p] or stem in blobs[p])]
        if data_refs:
            label = "REFERENCED_BY_RECORD"
        elif py_refs:
            label = "REFERENCED_BY_CODE_ONLY"
        else:
            label = "UNREFERENCED"
        rows.append({"path": t, "label": label, "data_refs": len(data_refs), "code_refs": len(py_refs),
                     "example_data_ref": data_refs[0] if data_refs else ""})

    with (OUT / "outside_runtime_review.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = {
        "files": len(rows),
        "labels": dict(collections.Counter(r["label"] for r in rows)),
        "by_dir_unreferenced": collections.Counter(
            "/".join(r["path"].split("/")[:2]) for r in rows if r["label"] == "UNREFERENCED"
        ).most_common(),
    }
    (OUT / "outside_runtime_review_summary.json").write_text(json.dumps(summary, indent=2, default=list) + "\n")
    print(json.dumps(summary, indent=2, default=list))


if __name__ == "__main__":
    main()
