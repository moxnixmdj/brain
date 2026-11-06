#!/usr/bin/env python3
"""Group *_vN.py modules into families and mark the highest version as current (read-only).

Output: out/version_families.csv and out/version_families_summary.json next to this script.
"""
import csv
import collections
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
TREE = Path(__file__).resolve().parents[3]
OUT = HERE / "out"
VER = re.compile(r"^(?P<stem>.+?)_v(?P<n>\d+)\.py$")


def main() -> None:
    tracked = subprocess.run(
        ["git", "-C", str(TREE), "ls-files", "*.py"],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    families: dict[tuple[str, str], list[tuple[int, str]]] = collections.defaultdict(list)
    for p in tracked:
        if p.startswith(("canonical/tests/", "tests/")):
            continue
        d, name = p.rsplit("/", 1) if "/" in p else ("", p)
        m = VER.match(name)
        if m:
            families[(d, m.group("stem"))].append((int(m.group("n")), p))

    rows = []
    for (d, stem), versions in sorted(families.items()):
        versions.sort()
        latest = versions[-1][1]
        for n, p in versions:
            rows.append({
                "directory": d,
                "family": stem,
                "version": n,
                "path": p,
                "status": "CURRENT" if p == latest else "SUPERSEDED",
                "family_size": len(versions),
            })

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "version_families.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = {
        "versioned_modules": len(rows),
        "families": len(families),
        "current": sum(r["status"] == "CURRENT" for r in rows),
        "superseded": sum(r["status"] == "SUPERSEDED" for r in rows),
        "families_with_one_version": sum(1 for v in families.values() if len(v) == 1),
        "largest_families": sorted(
            [(f"{d}/{s}", len(v)) for (d, s), v in families.items()],
            key=lambda x: -x[1],
        )[:8],
    }
    (OUT / "version_families_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
