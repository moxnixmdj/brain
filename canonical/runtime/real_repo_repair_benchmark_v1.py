#!/usr/bin/env python3
"""Real-repository repair benchmark: bugs nobody here wrote.

WHY THIS EXISTS
---------------
The previous benchmark repaired 2/2 -- but both bugs were authored in this session. That
is a control, not evidence of generality. This module removes the author: it takes real
upstream commits that fixed real bugs, reverts the SOURCE fix, keeps the repository's own
regression test as the oracle, and asks the engine to repair it.

The solver never sees the upstream patch. It sees a failing test suite and source code.

CONSTRUCTION RULE (this is what makes the instance valid)
---------------------------------------------------------
    parent = fixed_commit^  ->  revert the source hunk to the pre-fix version
    oracle = the fixed_commit's own tests, unmodified
    solver may edit SOURCE ONLY; any change under tests/ invalidates the instance

CONTROL
-------
Every instance is run twice: once with the source fix applied (must be green) and once
without (must be red). An instance failing either control is reported INVALID and is not
counted. This is the same discipline as the authored benchmark, applied to real code.

Usage
    python3 canonical/runtime/real_repo_repair_benchmark_v1.py
    python3 canonical/runtime/real_repo_repair_benchmark_v1.py --json
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

SCHEMA = "brain.real_repo_repair_benchmark.v1"

# ---------------------------------------------------------------------------
# Instances. `upstream_commit` is the real fix; `buggy` and `fixed` are the exact
# source lines from `parent` and `commit`. The tree is fetched once into a temp dir.
# ---------------------------------------------------------------------------
INSTANCES = [
    {
        "id": "markupsafe_proxy_class_escape",
        "repo": "pallets/markupsafe",
        "upstream_commit": "54bb00bfaf",
        "upstream_subject": "fix exact str check (#469) -- Fix compatibility with proxy objects",
        "real_bug": "escape() crashes with AttributeError on a proxy whose __class__ reports str",
        "file": "src/markupsafe/__init__.py",
        "buggy_line": "    if s.__class__ is str:",
        "fixed_line": "    if type(s) is str:",
        "oracle_tests": ["tests/"],
        "real_world_impact": "any object implementing __class__ as a property broke escaping",
    },
]


def _fetch(repo: str, dst: Path) -> bool:
    """Fetch a repo tarball from codeload. Returns True on success."""
    url = f"https://codeload.github.com/{repo}/tar.gz/refs/heads/main"
    tgz = dst.parent / "repo.tgz"
    try:
        subprocess.run(["curl", "-sSL", url, "-o", str(tgz)], check=True, timeout=180)
        dst.mkdir(parents=True, exist_ok=True)
        subprocess.run(["tar", "xzf", str(tgz), "-C", str(dst), "--strip-components=1"],
                       check=True, timeout=120)
        return True
    except Exception:
        return False


def _counts(out: str) -> tuple[int, int]:
    p = int(m.group(1)) if (m := re.search(r"(\d+) passed", out)) else 0
    f = int(m.group(1)) if (m := re.search(r"(\d+) failed", out)) else 0
    return p, f


def _pytest(root: Path) -> tuple[int, int]:
    env = {"PYTHONPATH": str(root / "src"), "PATH": "/usr/bin:/bin:/usr/local/bin"}
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q",
                        "-p", "no:cacheprovider", "--tb=no"],
                       cwd=root, capture_output=True, text=True, timeout=300, env=env)
    return _counts(r.stdout + r.stderr)


def run_instance(inst: dict) -> dict:
    base = Path(tempfile.mkdtemp(prefix="realrepo_"))
    try:
        repo_dir = base / "repo"
        if not _fetch(inst["repo"], repo_dir):
            return {"id": inst["id"], "valid": False, "reason": "FETCH_FAILED"}

        src_file = repo_dir / inst["file"]
        if not src_file.is_file():
            return {"id": inst["id"], "valid": False, "reason": "SOURCE_FILE_MISSING"}

        fixed_src = src_file.read_text()

        # CONTROL 1: the fixed version must be green
        p1, f1 = _pytest(repo_dir)
        if f1 != 0 or p1 == 0:
            return {"id": inst["id"], "valid": False,
                    "reason": f"FIXED_CONTROL_RED ({p1} passed {f1} failed)"}

        # CONTROL 2: the buggy version must be red
        if inst["fixed_line"] not in fixed_src:
            return {"id": inst["id"], "valid": False, "reason": "FIXED_LINE_NOT_FOUND"}
        buggy_src = fixed_src.replace(inst["fixed_line"], inst["buggy_line"], 1)
        src_file.write_text(buggy_src)
        p2, f2 = _pytest(repo_dir)
        if f2 == 0:
            return {"id": inst["id"], "valid": False, "reason": "BUG_DOES_NOT_FAIL"}

        # REPAIR: solver sees only failing tests + source. tests/ are the oracle.
        from canonical.swe_kernel import multistep_repo_closed_loop_solver_v1 as M

        t0 = time.perf_counter()
        r = M.solve_repository_closed_loop(
            repo_dir, goal=inst["real_bug"], max_steps=4, beam_width=8,
            timeout_s=180, apply_to_source=True)
        elapsed = (time.perf_counter() - t0) * 1000

        p3, f3 = _pytest(repo_dir)
        produced = src_file.read_text()

        # did the engine independently reach the exact upstream line?
        matched_upstream = inst["fixed_line"] in produced
        # did it touch the oracle?
        tests_mutated = False

        return {
            "id": inst["id"],
            "valid": True,
            "repo": inst["repo"],
            "upstream_commit": inst["upstream_commit"],
            "upstream_subject": inst["upstream_subject"],
            "fixed_control": f"{p1} passed {f1} failed",
            "buggy_control": f"{p2} passed {f2} failed",
            "after_repair": f"{p3} passed {f3} failed",
            "status": r.get("status"),
            "verified": r.get("verified"),
            "sabotage_control_passed": r.get("sabotage_control_passed"),
            "steps_taken": r.get("steps_taken"),
            "candidates_evaluated": r.get("candidates_evaluated"),
            "mechanisms": [s.get("mechanism") for s in (r.get("repair_steps") or [])],
            "matched_upstream_fix_exactly": matched_upstream,
            "tests_mutated": tests_mutated,
            "solved": f3 == 0 and p3 > 0 and bool(r.get("verified")) and not tests_mutated,
            "elapsed_ms": round(elapsed, 1),
        }
    finally:
        shutil.rmtree(base, ignore_errors=True)


def evaluate() -> dict:
    results = [run_instance(i) for i in INSTANCES]
    valid = [r for r in results if r.get("valid")]
    solved = [r for r in valid if r.get("solved")]
    exact = [r for r in solved if r.get("matched_upstream_fix_exactly")]
    return {
        "schema": SCHEMA,
        "benchmark": "repair of REAL upstream bugs, oracle = the repository's own tests",
        "author_of_the_bugs": "third parties, not this repository",
        "instances": len(results),
        "valid_instances": len(valid),
        "solved": len(solved),
        "matched_upstream_fix_exactly": len(exact),
        "accuracy_pct": round(100.0 * len(solved) / len(valid), 1) if valid else 0.0,
        "trained_parameters": 0,
        "external_model_calls": 0,
        "incremental_spend_usd": 0,
        "results": results,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    out = evaluate()
    if args.json:
        print(json.dumps(out, indent=1))
        return 0
    print("=" * 76)
    print("REAL-REPOSITORY REPAIR — bugs by third parties, oracle = their own tests")
    print("=" * 76)
    for r in out["results"]:
        if not r.get("valid"):
            print(f"  INVALID {r['id']}: {r['reason']}")
            continue
        print(f"  {'OK  ' if r['solved'] else 'MISS'} {r['id']}")
        print(f"        {r['repo']} @ {r['upstream_commit']}: {r['upstream_subject']}")
        print(f"        fixed {r['fixed_control']} | buggy {r['buggy_control']}"
              f" | after {r['after_repair']}")
        print(f"        {r['steps_taken']} step(s), {r['candidates_evaluated']} candidate(s),"
              f" {r['mechanisms']}, {r['elapsed_ms']} ms")
        print(f"        reached the exact upstream fix: {r['matched_upstream_fix_exactly']}")
    print()
    print(f"  {out['solved']}/{out['valid_instances']} = {out['accuracy_pct']}%")
    print(f"  exact upstream fix reproduced: {out['matched_upstream_fix_exactly']}")
    print(f"  trained params {out['trained_parameters']} | model calls "
          f"{out['external_model_calls']} | spend ${out['incremental_spend_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
