"""Reproducible Zero-Hint Blind Evaluation Harness for `COGS` (`solve_causal_environment`).

Evaluates frozen engine digests (`0` model calls, `0` learned parameters, `0` file/line hints)
on real GitHub bug-fix commits (`single_line_fix_commits_20261123_V1.json` or
`real_fix_commits_20261116_V1.json`) using ephemeral detached git worktrees outside the repo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import tempfile
import time

from canonical.swe_kernel.perfect_algorithm_v1 import solve_causal_environment

ENGINE_FILES = (
    "canonical/swe_kernel/universal_semantic_ir_v1.py",
    "canonical/swe_kernel/causal_cegis_inventor_v1.py",
    "canonical/swe_kernel/perfect_algorithm_v1.py",
)


def compute_engine_digests(repo_root: pathlib.Path) -> dict[str, str]:
    return {
        rel: hashlib.sha256((repo_root / rel).read_bytes()).hexdigest()
        for rel in ENGINE_FILES
    }


def evaluate_corpus_slice(
    *,
    corpus_path: pathlib.Path,
    repos_cache_dir: pathlib.Path,
    start_index: int,
    end_index: int,
    output_json: pathlib.Path,
    sandbox_budget: int = 26,
    timeout_sec: float = 12.0,
) -> dict[str, object]:
    brain_root = pathlib.Path(__file__).resolve().parents[2]
    pre_hashes = compute_engine_digests(brain_root)

    payload = json.loads(corpus_path.read_text(encoding="utf-8"))
    tasks = payload["tasks"]
    selected = tasks[start_index:end_index]

    results: list[dict[str, object]] = []
    solved_count = 0
    t_suite = time.time()

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as shared_td:
        law_path = pathlib.Path(shared_td) / "session_laws.json"
        for offset, row in enumerate(selected):
            idx = start_index + offset
            repo_raw = str(row["repo"])
            repo_short = repo_raw.split("/")[-1]
            sha = str(row.get("commit") or row["sha"])
            parent = str(row.get("parent") or f"{sha}^")
            test_rel = str(row["test"])
            human_sources = (
                list(row["sources"])
                if "sources" in row
                else [str(row["source"])]
            )
            repo_dir = repos_cache_dir / repo_short

            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
                wt = pathlib.Path(td) / "wt"
                subprocess.run(
                    ["git", "-C", str(repo_dir), "worktree", "add", "--detach", str(wt), parent],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                try:
                    test_txt = subprocess.run(
                        ["git", "-C", str(repo_dir), "show", f"{sha}:{test_rel}"],
                        capture_output=True,
                        text=True,
                        check=True,
                    ).stdout
                    (wt / test_rel).parent.mkdir(parents=True, exist_ok=True)
                    (wt / test_rel).write_text(test_txt, encoding="utf-8")

                    t0 = time.time()
                    res = solve_causal_environment(
                        wt,
                        language="python",
                        test_target=test_rel,
                        law_store_path=law_path,
                        sandbox_budget=sandbox_budget,
                        timeout_sec=timeout_sec,
                    )
                    elapsed = round(time.time() - t0, 2)
                finally:
                    subprocess.run(
                        ["git", "-C", str(repo_dir), "worktree", "remove", "--force", str(wt)],
                        capture_output=True,
                        text=True,
                    )

            mod_files = list((res.get("modified_files") or {}).keys())
            if res["solved"]:
                solved_count += 1

            results.append(
                {
                    "task_index": idx,
                    "repo": repo_raw,
                    "commit": sha,
                    "test": test_rel,
                    "solved": res["solved"],
                    "stage": res["stage"],
                    "mechanism": res["mechanism"],
                    "exact_file_match": bool(res["solved"] and set(mod_files) == set(human_sources)),
                    "sabotage_verified": res["sabotage_verified"],
                    "overfit_falsifier_passed": res["overfit_falsifier_passed"],
                    "neighbor_impact_passed": res["neighbor_impact_passed"],
                    "source_tree_unchanged": res["source_tree_unchanged"],
                    "elapsed_sec": elapsed,
                    "unified_diff": res["unified_diff"],
                }
            )

    post_hashes = compute_engine_digests(brain_root)
    if pre_hashes != post_hashes:
        raise RuntimeError("Frozen engine SHA-256 digest changed during blind evaluation!")

    summary: dict[str, object] = {
        "corpus": str(corpus_path.name),
        "slice": [start_index, end_index],
        "solved": solved_count,
        "total": len(results),
        "solve_rate_pct": round(100.0 * solved_count / max(1, len(results)), 2),
        "model_calls": 0,
        "learned_parameters": 0,
        "file_or_line_hints_given": 0,
        "frozen_engine_sha256_pre": pre_hashes,
        "frozen_engine_sha256_post": post_hashes,
        "hashes_identical": True,
        "total_wall_sec": round(time.time() - t_suite, 2),
        "results": results,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=pathlib.Path, required=True)
    parser.add_argument("--repos-dir", type=pathlib.Path, default=pathlib.Path("/tmp/brain_repos"))
    parser.add_argument("--start", type=int, default=15)
    parser.add_argument("--end", type=int, default=45)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--budget", type=int, default=26)
    parser.add_argument("--timeout", type=float, default=12.0)
    args = parser.parse_args()

    summary = evaluate_corpus_slice(
        corpus_path=args.corpus,
        repos_cache_dir=args.repos_dir,
        start_index=args.start,
        end_index=args.end,
        output_json=args.output,
        sandbox_budget=args.budget,
        timeout_sec=args.timeout,
    )
    print(
        f"Evaluated {summary['total']} commits: {summary['solved']}/{summary['total']} "
        f"({summary['solve_rate_pct']}%) solved in {summary['total_wall_sec']}s"
    )


if __name__ == "__main__":
    main()
