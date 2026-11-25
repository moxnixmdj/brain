"""Is the oracle handed to us, or do we have to make it?

SWE-bench, Terminal-Bench and OSWorld all present a repository in which the
fail-to-pass test is *absent*: it exists only in the fix commit. Every engine in
this repo is oracle-driven, so the first question about any task is not "can we
generate a patch" but "where does the demand come from".

My 45-commit corpus is mined the same way: each row is a real fix commit, and
`entry["test"]` names the file the fix touched. Every previous tool here
(`the_harness_must_prove_it_can_see_v1.py`, both engines) restores that file from
the fix commit into the parent tree and then runs it. That is a convenience the
real benchmarks do not grant. This script deletes that convenience and asks, per
row, which of three situations the parent is actually in:

    ORACLE_ABSENT      the named test file does not exist at commit^
                       -> the SWE-bench situation: no failing test to hand over
    ORACLE_GREEN       the file exists but the named tests pass at commit^
                       -> the fix *changed* the assertion; no free demand either
    ORACLE_ALREADY_RED the named tests exist and already fail at commit^
                       -> free oracle; the engine's 19/45 is achievable here

The interesting number is how many rows are ORACLE_ALREADY_RED, because those are
the only rows where "solve from an issue alone" is even *testable* with the current
engines. The rest are Wall 1 by construction and must be solved by synthesis (Idea 1
of the plan) or not at all.

    python canonical/tools/the_oracle_was_not_handed_to_us_v1.py \
        --receipt canonical/verification/THE_ORACLE_WAS_NOT_HANDED_TO_US_20261124_V1.json \
        --seconds 180
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import tempfile
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (str(HERE), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

CORPUS = REPO / "canonical" / "corpus" / "single_line_fix_commits_20261123_V1.json"
DEFAULT_REPOS_ROOT = pathlib.Path("/home/user/repos")


def git(repo_path: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo_path), *args],
                          capture_output=True, text=True, errors="replace")


def exists_at(repo_path: pathlib.Path, commit: str, path: str) -> bool:
    return git(repo_path, "cat-file", "-e", f"{commit}:{path}").returncode == 0


def run_nodeids(worktree: pathlib.Path, nodeids: list[str], seconds: int) -> dict[str, Any]:
    """Run the named node ids if they are collectable; report counts and the tail."""
    command = [sys.executable, "-m", "pytest", *nodeids, "-q", "--tb=line",
               "-p", "no:cacheprovider",
               "-o", "asyncio_default_fixture_loop_scope=function"]
    try:
        done = subprocess.run(command, cwd=str(worktree), capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=seconds)
    except subprocess.TimeoutExpired:
        return {"timed_out": True, "passed": 0, "failed": 0, "tail": "TIMEOUT"}
    tail = done.stdout.strip().splitlines()
    text = tail[-1] if tail else ""
    if done.returncode not in (0, 1) or "no tests ran" in done.stdout:
        err = [ln for ln in done.stderr.strip().splitlines() if ln.strip()]
        if err:
            text = (text + " || " + err[-1])[:260]
    passed = failed = errors = 0
    for word, key in (("passed", "passed"), ("failed", "failed"), ("error", "errors")):
        for chunk in text.replace(",", " ").split():
            pass
    # Parse "N passed" / "N failed" robustly without regex surprises.
    tokens = text.replace(",", " ").split()
    for index, token in enumerate(tokens):
        if index == 0:
            continue
        previous = tokens[index - 1]
        if not previous.isdigit():
            continue
        if token.startswith("passed"):
            passed = int(previous)
        elif token.startswith("failed"):
            failed = int(previous)
        elif token.startswith("error"):
            errors = int(previous)
    return {"timed_out": False, "passed": passed, "failed": failed,
            "errors": errors, "tail": text[:200], "returncode": done.returncode}


def one(repo_path: pathlib.Path, entry: dict[str, Any], seconds: int) -> dict[str, Any]:
    commit, test_path = entry["commit"], entry["test"]
    row: dict[str, Any] = {"repo": entry["repo"], "commit": commit[:10],
                           "test": test_path,
                           "failing_named": len(entry.get("failing") or [])}
    parent = f"{commit}^"
    if not exists_at(repo_path, parent, test_path):
        row["verdict"] = "ORACLE_ABSENT"
        row["note"] = "the fix introduced this test file; the parent has no oracle"
        return row
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        added = git(repo_path, "worktree", "add", "--detach", str(worktree), parent)
        if added.returncode != 0:
            return {**row, "verdict": "WORKTREE_FAILED", "note": added.stderr[:200]}
        try:
            nodeids = [n for n in (entry.get("failing") or []) if "::" in n]
            if not nodeids:
                return {**row, "verdict": "NO_NAMED_NODEID",
                        "note": "corpus row names a file but no node id"}
            probe = subprocess.run(
                [sys.executable, "-m", "pytest", *nodeids, "--collect-only", "-q",
                 "-p", "no:cacheprovider",
                 "-o", "asyncio_default_fixture_loop_scope=function"],
                cwd=str(worktree), capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=seconds)
            collected = probe.returncode == 0 and "::" in probe.stdout
            row["collectable_at_parent"] = collected
            if not collected:
                row["verdict"] = "ORACLE_NEW_TEST_CASE"
                row["note"] = ("test file exists at parent but these node ids do not: "
                               "the fix introduced them")
                row["probe_tail"] = (probe.stdout.strip().splitlines() or [""])[-1][:160] \
                    + " || " + (probe.stderr.strip().splitlines() or [""])[-1][:120]
                return row
            result = run_nodeids(worktree, nodeids, seconds)
            row.update(result)
            if result.get("timed_out"):
                row["verdict"] = "TIMEOUT"
            elif result["failed"] > 0:
                row["verdict"] = "ORACLE_ALREADY_RED"
            elif result["passed"] > 0:
                row["verdict"] = "ORACLE_GREEN"
                row["note"] = "named test exists and passes at parent; the fix changed it"
            else:
                row["verdict"] = "COLLECTION_ERROR"
            return row
        finally:
            git(repo_path, "worktree", "remove", "--force", str(worktree))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--repos-root", type=pathlib.Path, default=DEFAULT_REPOS_ROOT)
    parser.add_argument("--only", default="", help="comma-separated commit prefixes")
    parser.add_argument("--seconds", type=int, default=180)
    args = parser.parse_args(argv)

    tasks = json.loads(CORPUS.read_text(encoding="utf-8"))["tasks"]
    wanted = {part.strip() for part in args.only.split(",") if part.strip()}
    if wanted:
        tasks = [t for t in tasks if any(t["commit"].startswith(w) for w in wanted)]

    rows: list[dict[str, Any]] = []
    for index, entry in enumerate(tasks, 1):
        repo_path = args.repos_root / entry["repo"]
        if not (repo_path / ".git").exists():
            rows.append({"repo": entry["repo"], "commit": entry["commit"][:10],
                         "verdict": "REPO_MISSING"})
            print(f"[{index}/{len(tasks)}] {entry['repo']} {entry['commit'][:10]} REPO_MISSING",
                  flush=True)
            continue
        row = one(repo_path, entry, args.seconds)
        rows.append(row)
        print(f"[{index}/{len(tasks)}] {row['repo']:14s} {row['commit']} "
              f"{row['verdict']:18s} {row.get('note', '')[:60]}", flush=True)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    receipt = {
        "schema": "THE_ORACLE_WAS_NOT_HANDED_TO_US_V1",
        "question": "of the 45 real fix commits, on how many does the parent "
                    "already carry a failing test?",
        "counts": dict(sorted(counts.items())),
        "rows": rows,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1), encoding="utf-8")
    print("\n== counts")
    for name, count in receipt["counts"].items():
        print(f"  {name:22s} {count}")
    print(f"\nreceipt -> {args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
