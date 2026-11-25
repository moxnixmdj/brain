"""The user already wrote the test. Execute it.

Measured: 43/45 rows have no failing test in the parent, and 10/45 issues carry an
executable excerpt. The plan's Idea 1 tries to synthesise a metamorphic test from the
green suite -- measured 0/19, three implementations, because the suite's behaviour is
already correct so the relation fires on intentional mutation.

This tool does not synthesise anything. It takes each fenced code block out of the
issue, asks whether the block is a *reproducer* (it imports the project and calls it),
runs it against the parent tree and against the fix tree with correct module
provenance, and keeps the block only if the verdicts differ:

    parent ERROR / WRONG  and  fix CLEAN   -> FAIL_TO_PASS oracle, derived from prose
    both CLEAN                             -> the reproducer does not reach the bug
    both ERROR                             -> indistinguishable, discard

The oracle is the user's own words, executed. This is the one route in this repo with
a measured non-zero prior behind it (22.2% of issues carry an executable excerpt), and
it has no synthesis step to fail.

    python canonical/tools/run_the_reproducer_the_user_wrote_v1.py \
        --receipt canonical/verification/THE_USER_WROTE_THE_TEST_20261124_V1.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (str(HERE), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

CORPUS = REPO / "canonical" / "corpus" / "single_line_fix_commits_20261123_V1.json"
DEFAULT_REPOS_ROOT = pathlib.Path("/home/user/repos")
FENCE = re.compile(r"```(?:python|py|python3)?[^\n]*\n(.*?)```", re.S)
# A block is a reproducer candidate if it invokes something after importing.
HAS_IMPORT = re.compile(r"^\s*(?:import|from)\s+\w+", re.M)
HAS_CALL = re.compile(r"\w\s*\(")
MAX_BLOCK_LINES = 60


def git(repo_path: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo_path), *args], capture_output=True,
                          text=True, errors="replace")


PROMPT = re.compile(r"^\s*(?:>>>|\.\.\.) ?(.*)$")


def transcript_to_code(block: str) -> str | None:
    """A REPL transcript is the most executable oracle an issue can carry.

    `>>> urllib3.util.parse_url("http://example.com:000001")` followed by the expected
    traceback states the call and the expected outcome in one line. My first version
    discarded every block containing `>>>`, which threw away the single richest source
    in the corpus.
    """
    lines = [m.group(1) for m in (PROMPT.match(ln) for ln in block.splitlines()) if m]
    if not lines:
        return None
    code = "\n".join(lines)
    if not (HAS_IMPORT.search(code) or HAS_CALL.search(code)):
        return None
    return code


def blocks_from(body: str) -> list[str]:
    out: list[str] = []
    for raw in FENCE.findall(body or ""):
        block = raw.strip("\n")
        if not block.strip():
            continue
        if len(block.splitlines()) > MAX_BLOCK_LINES:
            # still allow a short transcript inside a long block
            block = "\n".join(ln for ln in block.splitlines()[:MAX_BLOCK_LINES])
        if ">>>" in block:
            code = transcript_to_code(block)
            if code:
                out.append(code)
            continue
        if HAS_IMPORT.search(block) and HAS_CALL.search(block):
            out.append(block)
    return out


def run_block(worktree: pathlib.Path, block: str, seconds: int) -> dict[str, Any]:
    """Execute the block as a script with the worktree's own source on the path."""
    script = worktree / "_brain_repro.py"
    script.write_text(block + "\n", encoding="utf-8")
    try:
        done = subprocess.run([sys.executable, script.name], cwd=str(worktree),
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=seconds,
                              stdin=subprocess.DEVNULL,
                              env={**__import__("os").environ,
                                   **identify.fresh_bytecode(worktree)})
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "tail": "timeout"}
    finally:
        script.unlink(missing_ok=True)
    error = next((ln for ln in (done.stderr or "").strip().splitlines()
                  if re.match(r"^\w*(Error|Exception|Warning)\b", ln.strip())), "")
    return {"status": "CLEAN" if done.returncode == 0 else "ERROR",
            "returncode": done.returncode,
            "tail": (error or (done.stderr or "").strip().splitlines()[-1:][0]
                     if (done.stderr or "").strip() else "")[:200]}


def one(repo_path: pathlib.Path, entry: dict[str, Any], body: str,
        seconds: int) -> dict[str, Any]:
    row: dict[str, Any] = {"repo": entry["repo"], "commit": entry["commit"][:10]}
    candidates = blocks_from(body)
    row["candidate_blocks"] = len(candidates)
    if not candidates:
        row["verdict"] = "NO_REPRODUCER_IN_ISSUE"
        return row
    with tempfile.TemporaryDirectory() as where:
        parent_tree = pathlib.Path(where) / "parent"
        fix_tree = pathlib.Path(where) / "fix"
        for tree, rev in ((parent_tree, f"{entry['commit']}^"), (fix_tree, entry["commit"])):
            added = git(repo_path, "worktree", "add", "--detach", str(tree), rev)
            if added.returncode != 0:
                return {**row, "verdict": "WORKTREE_FAILED",
                        "note": added.stderr[:160]}
        try:
            results = []
            for index, block in enumerate(candidates, 1):
                parent = run_block(parent_tree, block, seconds)
                fix = run_block(fix_tree, block, seconds)
                results.append({"block": index, "parent": parent, "fix": fix,
                                "fail_to_pass": parent["status"] in ("ERROR", "TIMEOUT")
                                                 and fix["status"] == "CLEAN"})
            row["blocks"] = results
            winning = [r for r in results if r["fail_to_pass"]]
            row["discriminating_blocks"] = len(winning)
            if winning:
                row["verdict"] = "REPRODUCER_DISCRIMINATES"
                row["witness"] = winning[0]["parent"]["tail"]
            elif all(r["parent"]["status"] == "CLEAN" for r in results):
                row["verdict"] = "REPRODUCER_DOES_NOT_REACH"
            else:
                row["verdict"] = "NO_SEPARATION"
            return row
        finally:
            for tree in (parent_tree, fix_tree):
                git(repo_path, "worktree", "remove", "--force", str(tree))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--issues", type=pathlib.Path,
                        help="DOES_THE_ISSUE_CONTAIN_THE_ORACLE receipt; rows with "
                             "ORACLE_IN_ISSUE are attempted first")
    parser.add_argument("--repos-root", type=pathlib.Path, default=DEFAULT_REPOS_ROOT)
    parser.add_argument("--only", default="")
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--all", action="store_true",
                        help="attempt every row, not just ORACLE_IN_ISSUE ones")
    args = parser.parse_args(argv)

    tasks = json.loads(CORPUS.read_text(encoding="utf-8"))["tasks"]
    by_commit = {t["commit"][:10]: t for t in tasks}
    wanted = {p.strip() for p in args.only.split(",") if p.strip()}

    if args.only:
        targets = [by_commit[c] for c in by_commit if c in wanted]
        bodies = {}
        if args.issues and args.issues.exists():
            for row in json.loads(args.issues.read_text(encoding="utf-8"))["rows"]:
                bodies[row["commit"]] = row.get("body_text", "")
    elif args.issues and args.issues.exists():
        issue_rows = json.loads(args.issues.read_text(encoding="utf-8"))["rows"]
        chosen = [r for r in issue_rows
                  if args.all or r["verdict"] == "ORACLE_IN_ISSUE"]
        targets = [by_commit[r["commit"]] for r in chosen if r["commit"] in by_commit]
        bodies = {r["commit"]: r.get("body_text", "") for r in chosen}
    else:
        raise SystemExit("need --issues (with body_text) and/or --only")

    rows = []
    for index, entry in enumerate(targets, 1):
        repo_path = args.repos_root / entry["repo"]
        body = bodies.get(entry["commit"][:10], "")
        if not (repo_path / ".git").exists():
            rows.append({"repo": entry["repo"], "commit": entry["commit"][:10],
                         "verdict": "REPO_MISSING"})
            continue
        row = one(repo_path, entry, body, args.seconds)
        rows.append(row)
        print(f"[{index}/{len(targets)}] {row['repo']:14s} {row['commit']} "
              f"{row['verdict']:26s} blocks={row.get('candidate_blocks', 0)} "
              f"{str(row.get('witness',''))[:60]}", flush=True)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    receipt = {"schema": "THE_USER_WROTE_THE_TEST_V1",
               "method": "execute the issue's own fenced blocks on parent and fix; "
                         "keep blocks whose verdicts differ",
               "counts": dict(sorted(counts.items())), "rows": rows}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1), encoding="utf-8")
    print("\n== counts")
    for name, count in receipt["counts"].items():
        print(f"  {name:26s} {count}")
    print(f"\nreceipt -> {args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
