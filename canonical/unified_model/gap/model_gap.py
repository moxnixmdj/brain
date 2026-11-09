#!/usr/bin/env python3
"""Compare the unified model's source index with every tracked .py file (read-only).

Writes out/model_gap.json and out/model_gap_by_dir.csv next to this script.
"""
import csv
import json
import collections
import subprocess
from pathlib import Path

TREE = Path("/tmp/vw2")
MODEL = TREE / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"
OUT = Path(__file__).resolve().parent / "out"


def main() -> None:
    model = json.loads(MODEL.read_text())
    indexed = {e["path"] for e in model["source_index"]}
    classes = collections.Counter(e.get("classification") for e in model["source_index"])

    tracked = subprocess.run(
        ["git", "-C", str(TREE), "ls-files", "*.py"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    tree_py = set(tracked)

    missing = sorted(tree_py - indexed)
    stale = sorted(indexed - tree_py)

    by_dir: collections.Counter = collections.Counter()
    for p in missing:
        parts = p.split("/")
        by_dir["/".join(parts[:2]) if len(parts) > 2 else parts[0]] += 1

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "model_gap_by_dir.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["directory", "unindexed_py_files"])
        for d, n in by_dir.most_common():
            w.writerow([d, n])

    summary = {
        "tracked_py_files": len(tree_py),
        "model_source_index_entries": len(indexed),
        "indexed_and_in_tree": len(indexed & tree_py),
        "unindexed_py_files": len(missing),
        "indexed_but_not_in_tree": len(stale),
        "model_classifications": dict(classes),
        "top_unindexed_directories": by_dir.most_common(15),
        "stale_examples": stale[:10],
    }
    (OUT / "model_gap.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
