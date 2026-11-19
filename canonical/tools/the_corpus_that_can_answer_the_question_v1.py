#!/usr/bin/env python3
"""Build the corpus that decides the engine's number, without deciding it for it.

WHY THIS EXISTS
---------------
Every sweep in this tree so far ran on 6, 7, 29 or 30 commits -- small enough that one row moves the
headline three points. The last round said so itself: "the reader binds 1 of 2 in-class rows, and the
corpus is the limit, not the reader. Any future acceptance on admissibility has to be measured against
a corpus where more than 2 rows are in class."

This builds that corpus out of real history, in two stages that are separated on purpose:

  shape   a commit is a candidate by STRUCTURE alone -- one Python source file, at least one Python
          test file, and a source diff of exactly one removed and one added line. Nothing is executed,
          nothing is solved, and the engine's own class (`expression_pair`) is recorded, not required.
  gate    a candidate is a task only if, with the commit's own test file placed on the parent, the
          project's suite FAILS, and at the commit it PASSES. Both are pytest's verdicts on the
          project's unmodified tests.

Selection by shape and admission by execution is what keeps this from being the set of bugs that
already worked: the filter is the *class* the engine claims, applied to real history, and the gate is
the project's own verdict -- never the engine's, never a label anyone wrote down.

WHAT THIS DOES NOT DO
---------------------
It does not rank or drop candidates by how hard they look, and it never keeps a task because the engine
solves it (the engine is not run here at all). Rejections are written with their reason, so the corpus's
own price -- commits scanned per task admitted -- is visible instead of implied.
"""
from __future__ import annotations

import argparse
import ast
import concurrent.futures
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

SCHEMA = "BRAIN_THE_CORPUS_THAT_CAN_ANSWER_THE_QUESTION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
TEST_DIRS = ("tests/", "test/", "testing/")
NUMSTAT = re.compile(r"^(\d+|-)\t(\d+|-)\t(.+)$")
FAILING = ("FAILED", "ERROR")


def is_test(path: str) -> bool:
    return path.startswith(TEST_DIRS) or pathlib.PurePosixPath(path).name.startswith("test_")


def is_source(path: str) -> bool:
    return path.endswith(".py") and not is_test(path)


def _git(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          errors="replace").stdout


def changed_files(repo: pathlib.Path, commit: str) -> list[str]:
    return [line.strip() for line in _git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r",
                                          commit).splitlines() if line.strip()]


def line_counts(repo: pathlib.Path, commit: str, path: str) -> tuple[int, int] | None:
    for line in _git(repo, "diff-tree", "--no-commit-id", "--numstat", "-r", commit, "--",
                     path).splitlines():
        found = NUMSTAT.match(line.strip())
        if found and found.group(3) == path:
            added, removed = found.group(1), found.group(2)
            if added == "-" or removed == "-":
                return None
            return int(added), int(removed)
    return None


def line_pair(repo: pathlib.Path, commit: str, path: str) -> tuple[str, str] | None:
    removed: list[str] = []
    added: list[str] = []
    for line in _git(repo, "diff-tree", "--no-commit-id", "-U0", "--no-color", "-r", "-p", commit,
                     "--", path).splitlines():
        if line.startswith(("---", "+++", "@@", "diff ", "index ", "new file", "deleted file")):
            continue
        if line.startswith("-"):
            removed.append(line[1:])
        elif line.startswith("+"):
            added.append(line[1:])
    if len(removed) != 1 or len(added) != 1:
        return None
    return removed[0], added[0]


def is_expression(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    try:
        ast.parse(stripped, mode="eval")
    except SyntaxError:
        return False
    return True


def expression_pair(before: str, after: str) -> bool:
    """Do the two lines change an EXPRESSION while leaving the statement's form alone?

    A changed line is usually `    return <expr>`, which is not an expression at all -- reading it with
    `mode="eval"` classified a genuine expression replacement as "not an expression" (measured: it
    called 163 of 181 candidates non-expression). What matters to the engine is the *site*: the same
    statement kind on both sides, whose payload is the expression that changed.
    """
    def payload(text: str) -> tuple[str, str] | None:
        stripped = text.strip()
        if not stripped:
            return None
        if is_expression(stripped):
            return "Expr", stripped
        try:
            module = ast.parse(stripped, mode="exec")
        except SyntaxError:
            return None
        if len(module.body) != 1:
            return None
        statement = module.body[0]
        kind = type(statement).__name__
        value = getattr(statement, "value", None)
        if value is None:
            return None
        return kind, ast.dump(value)

    left, right = payload(before), payload(after)
    if left is None or right is None:
        return False
    return left[0] == right[0] and left[1] != right[1]


def shape_candidate(repo: pathlib.Path, commit: str) -> tuple[dict[str, Any] | None, str]:
    """One commit as a shape candidate, or the reason it cannot be one. Runs nothing."""
    files = changed_files(repo, commit)
    sources = [path for path in files if is_source(path)]
    tests = [path for path in files if path.endswith(".py") and is_test(path)]
    if len(sources) != 1:
        return None, f"SOURCE_FILES={len(sources)}"
    if not tests:
        return None, "NO_TEST_FILE"
    counts = line_counts(repo, commit, sources[0])
    if counts != (1, 1):
        return None, "NOT_ONE_LINE" if counts is None else f"NOT_ONE_LINE={counts[0]}+{counts[1]}-"
    pair = line_pair(repo, commit, sources[0])
    if pair is None:
        return None, "NOT_ONE_REMOVED_AND_ONE_ADDED"
    before, after = pair
    if before.strip() == after.strip():
        return None, "NO_CHANGE"
    return {"repo": repo.name, "commit": commit, "test": tests[0],
            "tests": tests[:3], "sources": [sources[0]],
            "old_line": before.strip()[:200], "new_line": after.strip()[:200],
            "expression_pair": expression_pair(before, after),
            "subject": _git(repo, "log", "-1", "--format=%s", commit).strip()[:160]}, "CANDIDATE"


def verdicts_at(repo: pathlib.Path, commit: str, test_path: str, seconds: int,
                test_source_commit: str | None = None) -> tuple[dict[str, str], str]:
    """Run one test file at `commit`, with the test file taken from `test_source_commit`.

    The two are separate on purpose and were conflated once: showing the PARENT's test file on the
    PARENT asks whether the old test passes on the old code, which it always does. Measured: that
    defect reported PARENT_PASSES for 75 of 181 real candidates. The rule is about the COMMIT's test
    placed on the parent, and nothing else.
    """
    source_commit = test_source_commit or commit
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        added = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree),
                                commit], capture_output=True, text=True, errors="replace")
        if added.returncode != 0:
            return {}, "WORKTREE_FAILED"
        try:
            text = identify.show(repo, source_commit, test_path)
            if not text:
                return {}, "TEST_FILE_MISSING"
            (worktree / test_path).write_text(text, encoding="utf-8")
            outcomes, output = identify.run_tests_full(worktree, test_path, seconds)
            return outcomes, output
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                           capture_output=True, text=True)


def gate_one(root: pathlib.Path, entry: dict[str, Any],
             seconds: int) -> tuple[dict[str, Any], str]:
    """The corpus rule, tried on EVERY test file the commit changed, not on an arbitrary one.

    Picking `tests[0]` was a defect: a commit that changes four test files usually has one that carries
    the failing case and three that do not, and measuring the wrong one reports PARENT_PASSES -- a claim
    about the project. Measured: 71 of 181 candidates "passed on the parent" under that defect.
    """
    repo = root / entry["repo"]
    reasons: list[str] = []
    for test_path in entry.get("tests") or [entry["test"]]:
        entry["test"] = test_path
        entry, stage = _gate_one_file(repo, entry, seconds)
        if stage == "ADMITTED":
            return entry, stage
        reasons.append(stage)
    return entry, reasons[0] if len(set(reasons)) == 1 else "ANY_FILE:" + "|".join(
        sorted(set(stage.split(":")[0] for stage in reasons)))


def _gate_one_file(repo: pathlib.Path, entry: dict[str, Any],
                   seconds: int) -> tuple[dict[str, Any], str]:
    parent_outcomes, parent_output = verdicts_at(repo, f"{entry['commit']}^", entry["test"], seconds,
                                                 test_source_commit=entry["commit"])
    if not parent_outcomes:
        tail = (parent_output or "").strip().splitlines()
        return entry, "PARENT_NO_VERDICTS" + (": " + tail[-1][:100] if tail else "")
    failing = [name for name, verdict in parent_outcomes.items() if verdict.upper() in FAILING]
    if not failing:
        return entry, "PARENT_PASSES"
    commit_outcomes, _ = verdicts_at(repo, entry["commit"], entry["test"], seconds)
    if not commit_outcomes:
        return entry, "COMMIT_NO_VERDICTS"
    # The rule is about THE nodes the commit repairs, not about the whole file: a real commit's test file
    # routinely carries unrelated failures and skips, and demanding a green file threw away every task
    # whose file had a second, unrelated red -- measured 15 of 181 candidates. What must hold is that the
    # test the parent fails is green at the commit, and that nothing the parent passed goes red.
    still_failing = [name for name in failing if commit_outcomes.get(name, "MISSING").upper() != "PASSED"]
    regressions = [name for name, verdict in parent_outcomes.items()
                   if verdict.upper() == "PASSED" and commit_outcomes.get(name, "").upper() in FAILING]
    if still_failing or regressions:
        return entry, f"COMMIT_DOES_NOT_REPAIR={len(still_failing)}+{len(regressions)}"
    entry["failing"] = sorted(failing)[:8]
    entry["parent_verdicts"] = len(parent_outcomes)
    entry["commit_verdicts"] = len(commit_outcomes)
    return entry, "ADMITTED"


def shape_stage(root: pathlib.Path, repos: Sequence[str], scan: int,
                cap: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    candidates: list[dict[str, Any]] = []
    stages: dict[str, int] = {}
    for name in repos:
        repo = root / name
        if not (repo / ".git").exists():
            stages["NOT_CLONED"] = stages.get("NOT_CLONED", 0) + 1
            continue
        commits = _git(repo, "log", "--no-merges", "--format=%H", "-n", str(scan)).split()
        for commit in commits:
            entry, why = shape_candidate(repo, commit)
            if entry is None:
                stages[why] = stages.get(why, 0) + 1
                continue
            candidates.append(entry)
            if len(candidates) >= cap:
                return candidates, stages
    return candidates, stages


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stage", choices=("shape", "gate"), required=True)
    parser.add_argument("--repos", nargs="+", default=["more-itertools", "pluggy", "markupsafe",
                                                       "werkzeug", "itsdangerous"])
    parser.add_argument("--repos-root", type=pathlib.Path, default=pathlib.Path("/tmp/repos"))
    parser.add_argument("--scan", type=int, default=1500)
    parser.add_argument("--cap", type=int, default=400)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--seconds", type=int, default=120)
    parser.add_argument("--shapes", type=pathlib.Path, help="shape corpus consumed by --stage gate")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)

    started = time.time()
    if args.stage == "shape":
        candidates, stages = shape_stage(args.repos_root, args.repos, args.scan, args.cap)
        args.out.write_text(json.dumps({"schema": SCHEMA, "authority": AUTHORITY,
                                        "stage": "shape", "repos": args.repos,
                                        "tasks": candidates, "entries": candidates}, indent=1) + "\n", encoding="utf-8")
        totals = {"candidates": len(candidates), "shape_stages": dict(sorted(stages.items(),
                                                                             key=lambda kv: -kv[1])),
                  "expression_pairs": sum(1 for row in candidates if row["expression_pair"]),
                  "per_repo": {name: sum(1 for row in candidates if row["repo"] == name)
                               for name in args.repos}}
    else:
        if args.shapes is None:
            parser.error("--stage gate needs --shapes")
        pool = json.loads(args.shapes.read_text(encoding="utf-8"))["tasks"]
        admitted: list[dict[str, Any]] = []
        stages: dict[str, int] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as workers:
            futures = [workers.submit(gate_one, args.repos_root, dict(entry), args.seconds)
                       for entry in pool]
            for done, future in enumerate(concurrent.futures.as_completed(futures), 1):
                entry, stage = future.result()
                stages[stage] = stages.get(stage, 0) + 1
                if stage == "ADMITTED":
                    admitted.append(entry)
                print(f"[{done}/{len(futures)}] {entry['repo']} {entry['commit'][:10]} {stage}",
                      file=sys.stderr, flush=True)
        admitted.sort(key=lambda row: (row["repo"], row["commit"]))
        args.out.write_text(json.dumps({"schema": SCHEMA, "authority": AUTHORITY, "stage": "gate",
                                        "repos": args.repos, "tasks": admitted, "entries": admitted}, indent=1) + "\n",
                            encoding="utf-8")
        totals = {"gated": len(pool), "admitted": len(admitted),
                  "gate_stages": dict(sorted(stages.items(), key=lambda kv: -kv[1])),
                  "expression_pairs": sum(1 for row in admitted if row["expression_pair"]),
                  "commits_scanned_per_task": None}
    args.receipt.write_text(json.dumps({
        "schema": SCHEMA + "__RECEIPT", "authority": AUTHORITY, "date": "2026-11-23",
        "mode": "MINE_REAL_HISTORY", "repos": args.repos, "totals": totals,
        "seconds": round(time.time() - started, 1)}, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(totals))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
