#!/usr/bin/env python3
"""Join failing test files to the labels of the modules they import (read-only).

Attribution is static and coarse: a failing test file counts against every module
it imports by name (`canonical.x.y` or `from canonical.x import y`). A module can be
hit by many failing files. Reads out/module_labels.csv and a triage_cases.csv
(path to the per-case table is given on the command line, default below).
Writes out/failures_by_label.csv and a summary JSON.
"""
import csv
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TREE = HERE.parents[2]
DEFAULT_CASES = OUT / "triage_full_run_cases.csv"
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+(canonical(?:\.[A-Za-z_]\w*)+)", re.M)


def main() -> None:
    cases_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CASES
    with cases_path.open() as fh:
        failing_files = {r["file"] for r in csv.DictReader(fh) if r["file"] != "(unresolved)"}
    with (OUT / "module_labels.csv").open() as fh:
        labels = {r["path"]: r["label"] for r in csv.DictReader(fh)}

    hits: collections.Counter = collections.Counter()
    failing_by_label: dict[str, set[str]] = collections.defaultdict(set)
    unresolved_imports = 0
    for test in sorted(failing_files):
        text = (TREE / test).read_text(errors="ignore") if (TREE / test).is_file() else ""
        seen = set()
        for mod in IMPORT_RE.findall(text):
            path = mod.replace(".", "/") + ".py"
            if path not in labels:
                path2 = mod.replace(".", "/") + "/__init__.py"
                path = path2 if path2 in labels else None
            if path is None:
                unresolved_imports += 1
                continue
            if path in seen:
                continue
            seen.add(path)
            label = labels[path]
            hits[label] += 1
            failing_by_label[label].add(test)

    OUT.mkdir(parents=True, exist_ok=True)
    rows = [{"label": k, "module_hits_from_failing_tests": v,
             "failing_test_files": len(failing_by_label[k])} for k, v in hits.most_common()]
    with (OUT / "failures_by_label.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = {
        "failing_test_files": len(failing_files),
        "unresolved_imports": unresolved_imports,
        "by_label": rows,
        "caveat": "static import attribution; a failing test marks every module it imports",
    }
    (OUT / "failures_by_label_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
