#!/usr/bin/env python3
"""Index every mechanism module by whether anything else in the tree names it.

WHY THIS EXISTS
---------------
The owner said, repeatedly and correctly, that the solutions exist but their names are hard to
find.  Response-shaped wrongness: re-reading filenames, or re-asserting that something is missing
because its name did not suggest it.  Both are slow and both were wrong.

This is the fast version.  One pass tokenizes every Python file, then answers "who names this
module?" by set lookup instead of by re-reading the tree per module: ~2 seconds for 5k files.
The output is a map, not a claim -- a module with no reference is a mechanism that exists and is
not reached by any other code, which is a fact about wiring, not about capability.

    python3 scripts/solution_census_v1.py            # human summary
    python3 scripts/solution_census_v1.py --json     # machine copy

Authority: NONE.  This grants no credit and proves no capability.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP = {".git", "node_modules", "__pycache__", ".guard_trusted", ".venv", "dist", "build",
        ".mypy_cache", ".pytest_cache", ".ruff_cache"}
TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# Names that are language or library furniture, not mechanisms.
NOISE = {"main", "setup", "conftest", "__init__", "test", "tests", "utils", "helpers", "config"}


def python_files(include_tests=False):
    for path in ROOT.rglob("*.py"):
        if set(path.parts) & SKIP:
            continue
        if not include_tests and ("tests" in path.parts or path.stem.startswith("test_")):
            continue  # a test is never imported by name; counting it as an orphan is noise
        yield path


def census():
    files = list(python_files())
    tokens: dict[pathlib.Path, set[str]] = {}
    by_stem: dict[str, list[pathlib.Path]] = defaultdict(list)
    for path in files:
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        tokens[path] = set(TOKEN.findall(text))
        by_stem[path.stem].append(path)

    # Workflows, shells and docs call modules by name too; counting only .py referrers
    # reported CLI entry points (guards, probes) as orphans, which is misleading.
    extra_text = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or set(path.parts) & SKIP:
            continue
        if path.suffix not in {".yml", ".yaml", ".sh", ".ps1", ".md", ".json"}:
            continue
        try:
            if path.stat().st_size > 500_000:
                continue
            extra_text.append((path, set(TOKEN.findall(path.read_text(errors="ignore")))))
        except OSError:
            continue

    referrers: dict[str, set[pathlib.Path]] = {}
    for stem in by_stem:
        if stem in NOISE or stem.startswith("__"):
            continue
        hits = {p for p, toks in tokens.items() if stem in toks and p.stem != stem}
        hits |= {p for p, toks in extra_text if stem in toks}
        referrers[stem] = hits

    orphan = sorted(
        (stem for stem, hits in referrers.items() if not hits),
        key=lambda s: max(p.stat().st_size for p in by_stem[s]),
        reverse=True,
    )
    return {
        "python_files": len(files),
        "modules": len(referrers),
        "orphan_modules": len(orphan),
        "orphans": [
            {
                "module": stem,
                "path": str(min(by_stem[stem], key=lambda p: len(str(p))).relative_to(ROOT)),
                "bytes": max(p.stat().st_size for p in by_stem[stem]),
            }
            for stem in orphan
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--top", type=int, default=15)
    ns = ap.parse_args()
    result = census()
    if ns.json:
        print(json.dumps(result, indent=1))
        return 0
    print(f"python_files {result['python_files']}  modules {result['modules']}  "
          f"orphans {result['orphan_modules']}")
    for row in result["orphans"][: ns.top]:
        print(f"  {row['bytes'] // 1024:5d}KB  {row['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
