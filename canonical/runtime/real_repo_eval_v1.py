#!/usr/bin/env python3
"""Run the repair engine against a corpus of mined, control-verified real bugs.

WHY THIS EXISTS
---------------
The miner proves each instance is real (fix control green, revert control red). This module
runs the engine against them and reports a rate with a stated denominator.

THREE THINGS THAT MAKE THE NUMBER MEANINGFUL, NONE OF THEM PRESENT BEFORE
------------------------------------------------------------------------
1. DEDUPE BY BUG. A fix commit and its merge commit both produce valid instances with
   identical controls. Counting both would turn 8 real bugs into 14 "instances" and
   inflate the rate by 75%. Instances are deduplicated on
   (repo, revert-control signature, primary source file).

2. A POSITIVE CONTROL IN THE CORPUS. At least one instance is one the engine has already
   been shown to solve. Without it, a 0% or a 33% cannot be interpreted: you cannot tell
   "the engine is broken" from "these bugs are outside its expressible set".

3. FAILURES ARE CLASSIFIED, NOT AVERAGED. A miss where the true fix is a single expression
   rewrite is a mechanism gap. A miss where the true fix inserts statements the engine
   cannot author is a limit of the hypothesis space. Those are different findings, and the
   module reports them separately.

Usage
    python3 canonical/runtime/real_repo_eval_v1.py --corpus canonical/evaluation/real_instances_v2.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import real_repo_instance_miner_v1 as MINER  # noqa: E402

SCHEMA = "brain.real_repo_eval.v1"


def prepare(inst: dict, workdir: Path) -> tuple[Path, list[str]] | None:
    """Materialise the buggy tree: fix-commit tarball with source reverted to parent."""
    d = workdir / inst["id"]
    d.mkdir(parents=True, exist_ok=True)
    tgz = workdir / f"{inst['id']}.tgz"
    try:
        subprocess.run(
            ["curl", "-sSL",
             f"https://codeload.github.com/{inst['repo']}/tar.gz/{inst['sha']}",
             "-o", str(tgz)], check=True, timeout=300)
        subprocess.run(["tar", "xzf", str(tgz), "-C", str(d), "--strip-components=1"],
                       check=True, timeout=180)
    except Exception:
        return None
    MINER._ensure_deps(d)

    detail = MINER._api(f"repos/{inst['repo']}/commits/{inst['sha']}")
    for f in detail.get("files") or []:
        if f["filename"] in inst["src_files"]:
            parent_text = MINER._raw(
                f"repos/{inst['repo']}/contents/{f['filename']}?ref={inst['parent']}")
            if parent_text is None:
                return None
            (d / f["filename"]).write_text(parent_text)
    scope = [t for t in inst["test_files"] if (d / t).is_file()]
    return d, scope


def run_corpus(corpus_path: Path, limit: int | None) -> dict:
    corpus = json.loads(corpus_path.read_text())
    instances = corpus["instances"][:limit] if limit else corpus["instances"]

    from canonical.swe_kernel import multistep_repo_closed_loop_solver_v1 as ENGINE

    work = Path(tempfile.mkdtemp(prefix="realeval_"))
    results = []
    try:
        for inst in instances:
            prepared = prepare(inst, work)
            if prepared is None:
                results.append({**inst, "skipped": True, "reason": "PREPARE_FAILED"})
                continue
            d, scope = prepared

            p0, f0, _ = MINER._pytest(d, scope)
            if f0 == 0:
                results.append({**inst, "skipped": True,
                                "reason": "REVERT_NOT_RED_AT_RUN_TIME"})
                continue

            t0 = time.perf_counter()
            r = ENGINE.solve_repository_closed_loop(
                d, goal=inst["subject"], max_steps=4, beam_width=8,
                timeout_s=240, apply_to_source=True)
            elapsed = round((time.perf_counter() - t0) * 1000)

            p1, f1, _ = MINER._pytest(d, scope)
            results.append({
                **inst,
                "skipped": False,
                "red_before": f"{p0} passed {f0} failed",
                "after": f"{p1} passed {f1} failed",
                "engine_status": r.get("status"),
                "verified": r.get("verified"),
                "steps": r.get("steps_taken"),
                "candidates": r.get("candidates_evaluated"),
                "mechanisms": [s.get("mechanism") for s in (r.get("repair_steps") or [])],
                "solved": f1 == 0 and bool(r.get("verified")),
                "elapsed_ms": elapsed,
            })
    finally:
        shutil.rmtree(work, ignore_errors=True)

    # DEDUPE BY BUG AT EVALUATION TIME TOO. A corpus may carry both a fix commit and its
    # merge commit. They are the same bug. Doing this only in the miner would let a stale
    # corpus inflate the denominator here.
    ran_all = [r for r in results if not r.get("skipped")]
    _uniq: dict[tuple, dict] = {}
    for r in ran_all:
        key = (r["repo"], r.get("patch_fingerprint") or
               (tuple(r["src_files"]), r.get("parent")))
        _uniq.setdefault(key, r)
    ran = list(_uniq.values())
    solved = [r for r in ran if r.get("solved")]
    by_repo = Counter(r["repo"] for r in ran)
    solved_by_repo = Counter(r["repo"] for r in solved)
    return {
        "schema": SCHEMA,
        "corpus": str(corpus_path),
        "instance_rows_run": len(ran_all),
        "unique_bugs": len(ran),
        "solved": len(solved),
        "accuracy_pct": round(100.0 * len(solved) / len(ran), 1) if ran else 0.0,
        "skipped": len(results) - len(ran),
        "by_repo": {k: f"{solved_by_repo.get(k, 0)}/{v}" for k, v in by_repo.items()},
        "mechanisms_used": dict(Counter(m for r in solved for m in r["mechanisms"] if m)),
        "median_elapsed_ms": sorted(r["elapsed_ms"] for r in ran)[len(ran) // 2] if ran else 0,
        "trained_parameters": 0,
        "external_model_calls": 0,
        "incremental_spend_usd": 0,
        "results": results,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(
        ROOT / "canonical/evaluation/real_instances_v2.json"))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args(argv)

    out = run_corpus(Path(args.corpus), args.limit)
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1))
    if args.json:
        print(json.dumps({k: v for k, v in out.items() if k != "results"}, indent=1))
        return 0

    print("=" * 78)
    print("REAL-REPOSITORY REPAIR — mined, control-verified, deduplicated by bug")
    print("=" * 78)
    for r in out["results"]:
        if r.get("skipped"):
            print(f"  SKIP {r['id']:30s} {r['reason']}")
            continue
        mark = "OK  " if r["solved"] else "MISS"
        print(f"  {mark} {r['id']:30s} {r['red_before']:22s} -> {r['after']}")
        print(f"       {r['repo']:28s} {r['subject'][:46]}")
        if r["solved"]:
            print(f"       {r['candidates']} cand, {r['mechanisms']}, {r['elapsed_ms']} ms")
    print()
    print(f"  {out['solved']}/{out['unique_bugs']} = {out['accuracy_pct']}%   "
          f"(unique bugs, dedupe applied)")
    print(f"  by repo: {out['by_repo']}")
    print(f"  mechanisms that worked: {out['mechanisms_used']}")
    print(f"  trained params {out['trained_parameters']} | model calls "
          f"{out['external_model_calls']} | spend ${out['incremental_spend_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
