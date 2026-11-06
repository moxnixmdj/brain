#!/usr/bin/env python3
"""For multi-version families, check which version is actually imported (read-only).

A version counts as IMPORTED if some other tracked .py file imports its module name
(coarse name match). Output: out/current_vs_imported.csv and a summary JSON.
"""
import csv
import collections
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TREE = HERE.parents[2]
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", re.M)


def main() -> None:
    with (OUT / "version_families.csv").open() as fh:
        fam = [r for r in csv.DictReader(fh) if int(r["family_size"]) > 1]

    tracked = subprocess.run(
        ["git", "-C", str(TREE), "ls-files", "*.py"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    imported = collections.Counter()
    for p in tracked:
        try:
            text = (TREE / p).read_text(errors="ignore")
        except OSError:
            continue
        for m in IMPORT_RE.finditer(text):
            for part in m.group(1).split("."):
                imported[part] += 1

    rows = []
    for r in fam:
        stem = Path(r["path"]).stem
        rows.append({
            "family": f'{r["directory"]}/{r["family"]}',
            "path": r["path"],
            "status": r["status"],
            "imported_refs": imported.get(stem, 0),
        })

    with (OUT / "current_vs_imported.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    by_family = collections.defaultdict(list)
    for r in rows:
        by_family[r["family"]].append(r)
    cur_used = sum(1 for v in by_family.values() for r in v if r["status"] == "CURRENT" and r["imported_refs"] > 0)
    sup_used = sum(1 for v in by_family.values() for r in v if r["status"] == "SUPERSEDED" and r["imported_refs"] > 0)
    summary = {
        "multi_version_families": len(by_family),
        "current_versions": sum(1 for r in rows if r["status"] == "CURRENT"),
        "current_imported_somewhere": cur_used,
        "superseded_versions": sum(1 for r in rows if r["status"] == "SUPERSEDED"),
        "superseded_imported_somewhere": sup_used,
        "families_where_current_is_not_imported_but_an_old_one_is":
            sum(1 for v in by_family.values()
                if not any(r["status"] == "CURRENT" and r["imported_refs"] > 0 for r in v)
                and any(r["status"] == "SUPERSEDED" and r["imported_refs"] > 0 for r in v)),
    }
    (OUT / "current_vs_imported_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
