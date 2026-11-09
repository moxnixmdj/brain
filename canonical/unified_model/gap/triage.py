#!/usr/bin/env python3
"""Triage the failing and erroring cases of the honest-suite run (read-only).

Groups each failure by a coarse error bucket and by test file. Reads the
junit XML and the scratch tree only; writes CSV/JSON under out/.
"""
from __future__ import annotations

import collections
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

TREE = Path("/tmp/vw2")
JUNIT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/an/honest/junit.xml")
OUT = Path(__file__).resolve().parent / "out"


def resolve(dotted: str, tree: Path) -> str | None:
    """Longest dotted prefix that is a real .py file in the tree, as a repo path."""
    parts = dotted.split(".")
    for i in range(len(parts), 0, -1):
        cand = "/".join(parts[:i]) + ".py"
        if (tree / cand).is_file():
            return cand
    return None

BUCKET_RULES = [
    ("ENV_MISSING_MODULE", r"ModuleNotFoundError|No module named"),
    ("IMPORT_ERROR", r"ImportError|cannot import name"),
    ("GUARD_REGISTRY_STALE", r"LEGACY_VERIFIED_SITE_DISAPPEARED|EffectClassRegistryV2Error"),
    ("NETWORK_OR_TIMEOUT", r"Network|urlopen|Name or service not known|Temporary failure in name resolution|ConnectionError|timed out|Timeout"),
    ("MISSING_FILE", r"FileNotFoundError|No such file or directory|MISSING_FILE"),
    ("DRIFT_OR_HASH", r"DRIFT|BLOB|sha256|hash mismatch|CURRENTNESS"),
    ("ASSERTION", r"AssertionError"),
    ("OTHER_EXCEPTION", r"Error"),
]


def bucket(text: str) -> str:
    for name, pat in BUCKET_RULES:
        if re.search(pat, text, re.I if name == "NETWORK_OR_TIMEOUT" else 0):
            return name
    return "UNKNOWN"


def main() -> None:
    root = ET.parse(JUNIT).getroot()
    rows = []
    for tc in root.iter("testcase"):
        node = tc.find("failure")
        outcome = "fail"
        if node is None:
            node = tc.find("error")
            outcome = "error"
        if node is None:
            continue
        msg = node.get("message", "") or ""
        body = node.text or ""
        f = resolve(tc.get("classname", "") or tc.get("name", ""), TREE) or "(unresolved)"
        rows.append({
            "file": f,
            "test": tc.get("name", ""),
            "outcome": outcome,
            "bucket": bucket(msg + "\n" + body),
            "message_head": msg[:200].replace("\n", " "),
        })

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "triage_cases.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    by_bucket = collections.Counter(r["bucket"] for r in rows)
    by_file: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for r in rows:
        by_file[r["file"]][r["bucket"]] += 1
    file_rows = [
        {"file": f, "failing_cases": sum(c.values()), **dict(c)}
        for f, c in sorted(by_file.items(), key=lambda kv: -sum(kv[1].values()))
    ]
    summary = {
        "failing_or_erroring_cases": len(rows),
        "by_outcome": dict(collections.Counter(r["outcome"] for r in rows)),
        "by_bucket": dict(by_bucket.most_common()),
        "files": len(by_file),
        "files_with_one_failure": sum(1 for c in by_file.values() if sum(c.values()) == 1),
        "top_files": [(r["file"], r["failing_cases"]) for r in file_rows[:15]],
    }
    (OUT / "triage_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
