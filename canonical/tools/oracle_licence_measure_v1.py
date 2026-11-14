#!/usr/bin/env python3
"""Re-run the cross-project licence measurement that `ORACLE_LICENCE_CROSS_PROJECT_20261114_V1.json` records.

Why this exists
---------------
The record it reproduces says a project's own check was blind to 12 of 50 sites across three
repositories. A number like that is worth exactly as much as the ability to re-run it, so the run is
a tool and not a paragraph.

It is the only tool here that needs a network and more than a minute, so it is deliberately separate
from the organ (`canonical/swe_kernel/oracle_licence_v1.py`), which runs offline and in under a
second on its fixtures.

    python3 canonical/tools/oracle_licence_measure_v1.py \
        --out canonical/verification/ORACLE_LICENCE_RERUN.json

It downloads each repository's default branch from codeload.github.com, builds a throwaway venv with
pytest, and measures. Nothing it does is required by any test: no test needs the network, and no test
asserts the numbers below. The numbers are what they are on the day it runs.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import oracle_licence_v1 as L  # noqa: E402

# (label, github repo, default branch, files to measure, extra PYTHONPATH, test arguments)
CORPUS = [
    ("stem term", "torproject/stem", "master", ["stem/util/term.py"], (), ["test/unit/util/term.py"]),
    ("stem connection", "torproject/stem", "master", ["stem/util/connection.py"], (),
     ["test/unit/util/connection.py"]),
    ("stem tor_tools", "torproject/stem", "master", ["stem/util/tor_tools.py"], (),
     ["test/unit/util/tor_tools.py"]),
    ("more-itertools recipes", "more-itertools/more-itertools", "master",
     ["more_itertools/recipes.py"], (), ["tests/test_recipes.py"]),
    ("packaging utils", "pypa/packaging", "main", ["src/packaging/utils.py"], ("src",),
     ["tests/test_utils.py"]),
]


def _fetch(repo: str, branch: str, into: pathlib.Path) -> pathlib.Path:
    target = into / repo.split("/")[-1]
    if target.exists():
        return target
    url = f"https://codeload.github.com/{repo}/tar.gz/refs/heads/{branch}"
    archive = into / (repo.split("/")[-1] + ".tgz")
    print(f"  fetching {url}", flush=True)
    with urllib.request.urlopen(url, timeout=120) as response, open(archive, "wb") as handle:
        shutil.copyfileobj(response, handle)
    target.mkdir(parents=True)
    with tarfile.open(archive) as tar:
        tar.extractall(target)
    inner = [p for p in target.iterdir() if p.is_dir()]
    if len(inner) == 1:
        moved = into / (target.name + ".moved")
        inner[0].rename(moved)
        target.rmdir()
        moved.rename(target)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True)
    parser.add_argument("--work", default=None, help="where to keep the clones (default: temp)")
    parser.add_argument("--max-sites", type=int, default=10)
    parser.add_argument("--max-mutants", type=int, default=24)
    parser.add_argument("--timeout", type=float, default=150.0)
    args = parser.parse_args(argv)

    work = pathlib.Path(args.work) if args.work else pathlib.Path(tempfile.mkdtemp(prefix="licence_corpus_"))
    work.mkdir(parents=True, exist_ok=True)

    venv = work / "venv"
    if not (venv / "bin" / "python").exists():
        print("building a throwaway venv with pytest", flush=True)
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        subprocess.run([str(venv / "bin" / "pip"), "-q", "install", "pytest"], check=True)
    py = str(venv / "bin" / "python")

    results = []
    for label, repo, branch, files, extra, tests in CORPUS:
        project = _fetch(repo, branch, work)
        for rel in files:
            argv_list = [py, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests]
            print(f"[{label}] {rel}", flush=True)
            cache = L.LicenceCache(work / "cache")
            report = L.licence_for_project(project, rel, argv_list, cache=cache, timeout=args.timeout,
                                           max_sites=args.max_sites, max_mutants=args.max_mutants,
                                           extra_paths=extra)
            print("   " + report["text"], flush=True)
            results.append({
                "label": label, "repo": repo, "file": rel, "verdict": report["verdict"],
                "sites_measured": report["sites_measured"], "sites_licensed": report["sites_licensed"],
                "mutants_run": report["mutants_run"], "mutants_caught": report["mutants_caught"],
                "fraction_licensed": report["fraction_licensed"],
                "quantifier": (report.get("measurement") or {}).get("quantifier"),
                "blind_sites": [{"lineno": s["lineno"], "kind": s["node_kind"],
                                 "survivors": s["survivors"]}
                                for s in (report.get("measurement") or {}).get("sites", [])
                                if not s["licensed"]],
            })

    totals = {
        "files": len(results),
        "sites_measured": sum(r["sites_measured"] or 0 for r in results),
        "sites_licensed": sum(r["sites_licensed"] or 0 for r in results),
        "mutants_run": sum(r["mutants_run"] or 0 for r in results),
        "mutants_caught": sum(r["mutants_caught"] or 0 for r in results),
    }
    totals["fraction_of_sites_licensed"] = (
        round(totals["sites_licensed"] / totals["sites_measured"], 4) if totals["sites_measured"] else None)
    payload = {"schema": "BRAIN_ORACLE_LICENCE_CROSS_PROJECT_RERUN_V1", "authority": "NONE",
               "corpus": [c[0] for c in CORPUS], "totals": totals, "results": results}
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps(totals, indent=1))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
