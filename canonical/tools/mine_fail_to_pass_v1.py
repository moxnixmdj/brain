#!/usr/bin/env python3
"""Mine fail-to-pass tasks from a repository's own history, with the same rules as the hand-built corpus.

WHY THIS EXISTS
---------------
Every conclusion this project has drawn for four rounds rested on 8 tasks in 2 repositories. Choosing what to
build next from 8 tasks is guessing. This mines the same two repositories for every commit that adds a test
next to source, then keeps only the ones where the added test genuinely FAILS on the parent.

THE RULES, ALL LEARNED BY BEING WRONG FIRST
-------------------------------------------
1. A test file and a source file must both change. A commit that only adds a test measures nothing.
2. The added test must fail on the parent as a TEST FAILURE (pytest rc=1). rc=2 is a collection error and
   measures importability; rc=0 means the test already passed and the commit is not a reproduction.
3. pytest must run with the checkout on PYTHONPATH, or the installed wheel shadows the source and the failure
   is fake. This is the V34 defect and it is the reason this file imports env_for rather than reimplementing it.
4. The interpreter that runs pytest is the one that has pytest installed, not `sys.executable`. Getting this
   wrong produces "No module named pytest" and silently rejects every task. That happened on the first run.

Deterministic, no model calls, no network at run time beyond the clone.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.tools.behavioural_emission_v2 import env_for, run  # noqa: E402

SCHEMA = "BRAIN_MINED_FAIL_TO_PASS_V1"
FORMAT = "BRAIN_FAIL_TO_PASS_TASKS_V1"


def added_tests(diff: str) -> list[str]:
    names: list[str] = []
    for line in diff.splitlines():
        if not line.startswith("+"):
            continue
        match = re.match(r"\+\s*def (test_\w+)", line)
        if match:
            names.append(match.group(1))
    return names


def mine(repo: str, checkout: pathlib.Path, python: str, limit: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    rejected: dict[str, int] = {}
    # anchor to the branch tip: a checkout left detached on an old parent has a truncated history, and the
    # first version of this miner silently mined 7 tasks instead of 15 because of exactly that
    run(["git", "checkout", "-q", "-f", "origin/HEAD"], checkout)
    run(["git", "clean", "-qfd"], checkout)
    log = run(["git", "log", "--no-merges", "--format=%H %P", "-n", str(limit)], checkout).stdout
    for line in log.strip().splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        sha, parent = parts
        files = run(["git", "diff", "--name-only", parent, sha], checkout).stdout.split()
        tests = [f for f in files if f.startswith("tests/") and f.endswith(".py")
                 and not re.search(r"conftest|__init__|__main__", f)]
        sources = [f for f in files if f.endswith(".py") and not f.startswith("tests/")
                   and "docs" not in f and "benchmark" not in f]
        if not tests or not sources:
            rejected["NO_TEST_AND_SOURCE_PAIR"] = rejected.get("NO_TEST_AND_SOURCE_PAIR", 0) + 1
            continue
        diff = run(["git", "diff", parent, sha, "--"] + tests, checkout).stdout
        names = added_tests(diff)
        if not names:
            rejected["NO_ADDED_TEST_FUNCTION"] = rejected.get("NO_ADDED_TEST_FUNCTION", 0) + 1
            continue
        run(["git", "checkout", "-q", "-f", parent], checkout)
        run(["git", "clean", "-qfd"], checkout)
        (checkout / ".mined.patch").write_text(diff)
        if run(["git", "apply", "--whitespace=nowarn", ".mined.patch"], checkout).returncode != 0:
            rejected["PATCH_DID_NOT_APPLY"] = rejected.get("PATCH_DID_NOT_APPLY", 0) + 1
            continue
        probe = run([python, "-m", "pytest", tests[0], "-q", "--no-header", "-p", "no:cacheprovider"],
                    checkout, env_for(checkout))
        if probe.returncode != 1:
            key = f"RC_{probe.returncode}"
            rejected[key] = rejected.get(key, 0) + 1
            continue
        output = (probe.stdout or "") + (probe.stderr or "")
        # the node id runs to the ' - ' pytest appends before the error summary; splitting on spaces
        # truncates class-based nodes to the class name and silently loses the test
        failing = [line[len("FAILED "):].split(" - ")[0].strip() for line in output.splitlines()
                   if line.startswith("FAILED ") and "::" in line]
        if not failing:
            rejected["NO_NAMED_FAILING_NODE"] = rejected.get("NO_NAMED_FAILING_NODE", 0) + 1
            continue
        rows.append({"repo": repo, "sha": sha, "parent": parent, "test": tests[0],
                     "failed_nodes": [failing[0]],
                     "added_test_functions": names,
                     "source_files": sources[:4]})
    return {"repo": repo, "mined": len(rows), "rejected": rejected, "tasks": rows}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--clone", nargs=2, action="append", required=True,
                        metavar=("REPO", "PATH"), help="repo slug and existing checkout")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--limit", type=int, default=120)
    args = parser.parse_args(argv)
    blocks = [mine(repo, pathlib.Path(path), args.python, args.limit) for repo, path in args.clone]
    tasks = [task for block in blocks for task in block["tasks"]]
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"schema": FORMAT, "blocks": blocks, "tasks": tasks,
                               "cost": {"model_calls": 0, "network_at_run_time": 0}}, indent=1) + "\n")
    print(json.dumps({"mined": len(tasks), "blocks": [
        {"repo": block["repo"], "mined": block["mined"], "rejected": block["rejected"]}
        for block in blocks]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
