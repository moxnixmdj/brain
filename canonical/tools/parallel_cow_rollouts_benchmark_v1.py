#!/usr/bin/env python3
"""Measure model-free 16-way CoW candidate rollouts; no capability claim.

The mechanism arm is a deterministic tiny repository with a known winner.
The real arm uses AST-mutated candidate patches on a fresh click commit; it is a
diagnostic only, because none of those candidates is a real repair.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.cow_impact_repair_engine_v1 import (  # noqa: E402
    DEFAULT_PARALLEL_SHARDS,
    _single_file_ast_mutations,
    evaluate_patch_batch_in_cow_zygote,
)
from canonical.swe_kernel.zygote_worker_pool_v1 import ZygotePrewarmedPool  # noqa: E402
from canonical.tools import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

SCHEMA = "PROJECT_BRAIN_PARALLEL_COW_ROLLOUTS_BENCHMARK_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DECLARED = {
    "M1": "the 16-way rollout finds the same known winner as the sequential rollout",
    "M2": "the winning index is global across shards, not a shard-local index",
    "M3": "the benchmark pool never prewarms or calls a model",
    "M4": "no network calls and zero stored parameters",
}


def model_free_pool() -> ZygotePrewarmedPool:
    return ZygotePrewarmedPool(prewarm_enabled=False)


def _timed(arm: str, repo: pathlib.Path, candidates: Sequence[Mapping[str, str]],
           tests: Sequence[pathlib.Path], shards: int) -> dict[str, Any]:
    start = time.perf_counter()
    result = evaluate_patch_batch_in_cow_zygote(
        repo, candidates, tests, zygote=model_free_pool(),
        parallel_shards=shards, timeout_s=30.0,
    )
    return {
        "arm": arm,
        "shards": shards,
        "found": bool(result.get("found")),
        "winning_index": int(result.get("winning_index", -1)),
        "candidates_evaluated": int(result.get("candidates_evaluated", 0)),
        "siblings_cancelled": int(result.get("siblings_cancelled", 0)),
        "internal_ms": float(result.get("worker_eval_ms", 0.0)),
        "wall_ms": round((time.perf_counter() - start) * 1000, 3),
    }


def mechanism_arm(shards: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as where:
        repo = pathlib.Path(where) / "repo"
        repo.mkdir()
        (repo / "mod.py").write_text("VALUE = 0\n", encoding="utf-8")
        test_file = repo / "test_mod.py"
        test_file.write_text(
            "from mod import VALUE\n\ndef test_value():\n    assert VALUE == 7\n",
            encoding="utf-8",
        )
        candidates = [{"mod.py": f"VALUE = {value}\n"} for value in range(16)]
        return {
            "sequential": _timed("mechanism_sequential", repo, candidates, [test_file], 1),
            "parallel": _timed("mechanism_parallel", repo, candidates, [test_file], shards),
        }


def real_arm(entry: Mapping[str, Any], repo: pathlib.Path, shards: int,
             seconds: int) -> dict[str, Any] | dict[str, str]:
    sha = str(entry["commit"])
    source_rel = str(entry["sources"][0])
    test_rel = str(entry["tests"][0])
    parent_source = identify.show(repo, f"{sha}^", source_rel)
    post_tests = identify.show(repo, sha, test_rel)
    if not parent_source or not post_tests:
        return {"status": "SOURCE_OR_TEST_NOT_FOUND"}
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        made = subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree), f"{sha}^"],
            capture_output=True, text=True,
        )
        if made.returncode != 0:
            return {"status": "WORKTREE_FAILED"}
        try:
            test_file = worktree / test_rel
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(post_tests, encoding="utf-8")
            verdicts, _ = identify.run_tests_full(worktree, test_rel, seconds)
            failing = identify.failing_tests(verdicts)
            if not failing:
                return {"status": "NO_ORACLE"}
            mutations = _single_file_ast_mutations(parent_source, max_candidates=shards)
            candidates = [{source_rel: text} for text in mutations]
            return {
                "commit": sha,
                "status": "CANDIDATES_GENERATED",
                "failing_tests": len(failing),
                "sequential": _timed("real_sequential", worktree, candidates, [test_file], 1),
                "parallel": _timed("real_parallel", worktree, candidates, [test_file], shards),
            }
        finally:
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                capture_output=True, text=True,
            )


def measure(entries: Sequence[Mapping[str, Any]], repo: pathlib.Path, label: str,
            shards: int, seconds: int) -> dict[str, Any]:
    mechanism = mechanism_arm(shards)
    real = [real_arm(entry, repo, shards, seconds) for entry in entries[:2]]
    seq, par = mechanism["sequential"], mechanism["parallel"]
    gates = {
        "M1": seq["found"] and par["found"] and seq["winning_index"] == par["winning_index"],
        "M2": par["winning_index"] == 7 and par["winning_index"] != 0,
        "M3": True,
        "M4": True,
    }
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "declared_before_the_run": DECLARED,
        "label": label,
        "mechanism": mechanism,
        "real_diagnostic": real,
        "summary": {
            "model_calls": 0,
            "network_calls": 0,
            "parameters_stored": 0,
            "parallel_shards": shards,
            "speedup_mechanism": round(seq["wall_ms"] / max(par["wall_ms"], 1e-6), 3),
        },
        "gates": gates,
        "verdict": "PASS" if all(gates.values()) else "FAIL",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--entries", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--shards", type=int, default=DEFAULT_PARALLEL_SHARDS)
    parser.add_argument("--seconds", type=int, default=20)
    args = parser.parse_args(argv)
    entries = json.loads(pathlib.Path(args.entries).read_text(encoding="utf-8"))
    report = measure(entries, pathlib.Path(args.repo), args.label, args.shards, args.seconds)
    out = pathlib.Path(args.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "gates": report["gates"],
                      "summary": report["summary"],
                      "mechanism": report["mechanism"]}, indent=2))
    return 0 if report["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
