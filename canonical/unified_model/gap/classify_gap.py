#!/usr/bin/env python3
"""Fast first-pass classification of unindexed non-test Python files (read-only).

Rules are cheap and deliberately coarse: a file is labelled by its path and by
whether it has a __main__ block, a CLI, or is imported by any other tracked file.
Output: out/gap_classified.csv, out/gap_classified_summary.json.
"""
import csv
import collections
import json
import re
import subprocess
from pathlib import Path

TREE = Path("/tmp/vw2")
MODEL = TREE / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"
OUT = Path(__file__).resolve().parent / "out"

MODULE_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", re.M)


def group_of(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    if path.startswith("canonical/tests/") or path.startswith("tests/"):
        return "TEST"
    if "/_" in path or name.startswith("_"):
        return "INTERNAL_HELPER"
    if name.endswith("__init__.py"):
        return "PACKAGE_INIT"
    if re.search(r"_v\d+\.py$", name):
        return "VERSIONED_MODULE"
    if path.startswith(("swe_probe_", "canonical/experiments/")):
        return "EXPERIMENT_OR_PROBE"
    if path.startswith("execution_guard/"):
        return "GUARD"
    return "RUNTIME_MODULE"


def main() -> None:
    model = json.loads(MODEL.read_text())
    indexed = {e["path"] for e in model["source_index"]}
    tracked = subprocess.run(
        ["git", "-C", str(TREE), "ls-files", "*.py"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    unindexed = [p for p in tracked if p not in indexed and not group_of(p) == "TEST"]

    # Which top-level module names are imported anywhere in the tree (cheap grep-like pass).
    imported_names: collections.Counter = collections.Counter()
    for p in tracked:
        try:
            text = (TREE / p).read_text(errors="ignore")
        except OSError:
            continue
        for m in MODULE_RE.finditer(text):
            imported_names[m.group(1).split(".")[-1]] += 1

    rows = []
    for p in unindexed:
        stem = p.rsplit("/", 1)[-1][:-3]
        text = (TREE / p).read_text(errors="ignore")
        rows.append({
            "path": p,
            "group": group_of(p),
            "has_main": "__main__" in text,
            "imported_by_others": imported_names.get(stem, 0),
            "lines": text.count("\n"),
        })

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "gap_classified.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = {
        "unindexed_non_test_py": len(rows),
        "by_group": collections.Counter(r["group"] for r in rows).most_common(),
        "with_main_block": sum(r["has_main"] for r in rows),
        "imported_by_some_other_file": sum(1 for r in rows if r["imported_by_others"] > 0),
        "imported_by_none": sum(1 for r in rows if r["imported_by_others"] == 0),
    }
    (OUT / "gap_classified_summary.json").write_text(json.dumps(summary, indent=2, default=list) + "\n")
    print(json.dumps(summary, indent=2, default=list))


if __name__ == "__main__":
    main()
