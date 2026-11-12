#!/usr/bin/env python3
"""Fetches the expert fixes behind a SWE-bench style benchmark from the merged pull requests themselves.

A task of SWE-bench is one merged pull request: `<owner>__<repo>-<number>`. Its fix is that pull
request's change to the files that are not tests, on top of the commit the pull request was made
against. This tool asks api.github.com (through the `gh` command, already signed in) for exactly
that and writes one JSON file per task:

  instance_id, repo, pull, base_sha, merged, files: [ path, status, previous, patch (the hunks),
  is_test, is_python, and -- for Python files that are not tests and existed before -- `before`:
  the file at base_sha ]

It reads nothing from the benchmark's own dataset, so the tests and the issue texts never pass
through here. Where the task names come from is the caller's business; for SWE-bench Verified the
500 names are the union of the result files under evaluation/verified/*/results/results.json of
github.com/SWE-bench/experiments.

Zero model calls. Nothing here gives authority to anything.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import pathlib
import re
import subprocess
import sys
import time
from typing import Any, Callable, Sequence

SCHEMA = "BRAIN_EXPERT_FIX_PULL_REQUEST_V1"
TEST_WORDS = ("test", "tests", "e2e", "testing")
PAGE = 100


def is_test(repo: str, path: str) -> bool:
    """SWE-bench's split of a pull request into fix and tests: a path with one of these words
    anywhere in it is a test. Taken literally that makes every source file of pytest a test
    (src/_pytest/...); there the tests are the files under testing/."""
    if repo == "pytest-dev/pytest":
        return path.startswith("testing/")
    return any(word in path for word in TEST_WORDS)


def parts(instance_id: str) -> tuple[str, str, int]:
    found = re.match(r"^(.+?)__(.+)-(\d+)$", instance_id)
    if not found:
        raise ValueError(f"not a task name: {instance_id!r}")
    return found.group(1), found.group(2), int(found.group(3))


def gh(path: str, raw: bool = False, tries: int = 4, pause_s: float = 2.0) -> bytes:
    command = ["gh", "api"] + (["-H", "Accept: application/vnd.github.raw"] if raw else []) + [path]
    last = ""
    for attempt in range(tries):
        done = subprocess.run(command, capture_output=True)
        if done.returncode == 0:
            return done.stdout
        last = (done.stderr or done.stdout).decode("utf-8", "replace")[-300:]
        if "Not Found" in last or "404" in last:
            break
        time.sleep(pause_s * (1 + 2 * attempt))
    raise RuntimeError(last)


def changed_files(owner: str, repo: str, number: int, ask: Callable[..., bytes] = gh) -> list[dict[str, Any]]:
    """Every changed file of the pull request, page by page. (Joining pages as text is not safe:
    '][' also stands inside the hunks.)"""
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        got = json.loads(ask(f"repos/{owner}/{repo}/pulls/{number}/files?per_page={PAGE}&page={page}"))
        rows += got
        if len(got) < PAGE:
            return rows
        page += 1


def collect(instance_id: str, ask: Callable[..., bytes] = gh) -> dict[str, Any]:
    owner, repo, number = parts(instance_id)
    record: dict[str, Any] = {"schema": SCHEMA, "instance_id": instance_id, "repo": f"{owner}/{repo}", "pull": number}
    try:
        pull = json.loads(ask(f"repos/{owner}/{repo}/pulls/{number}"))
        base = pull["base"]["sha"]
        record.update(base_sha=base, merged=bool(pull.get("merged")), state=pull.get("state"), merge_commit_sha=pull.get("merge_commit_sha"),
                      title=pull.get("title"), changed_files=pull.get("changed_files"))
        files = []
        for f in changed_files(owner, repo, number, ask):
            path = f["filename"]
            row = {"path": path, "status": f["status"], "previous": f.get("previous_filename"), "patch": f.get("patch"),
                   "additions": f.get("additions"), "deletions": f.get("deletions"),
                   "is_test": is_test(record["repo"], path), "is_python": path.endswith(".py")}
            if not row["is_test"] and row["is_python"] and f["status"] in ("modified", "renamed", "changed", "removed"):
                try:
                    row["before"] = ask(f"repos/{owner}/{repo}/contents/{f.get('previous_filename') or path}?ref={base}", raw=True).decode("utf-8")
                except Exception as error:                       # the file as it was could not be had: said, not guessed
                    row["before"] = None
                    row["fetch_error"] = str(error)[:200]
            files.append(row)
        record["files"] = files
    except Exception as error:
        record["error"] = str(error)[:300]
    return record


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--ids-file", required=True, type=pathlib.Path, help="a JSON list of task names")
    parser.add_argument("--out-dir", required=True, type=pathlib.Path)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    names = json.loads(args.ids_file.read_text())

    def one(name: str) -> str:
        target = args.out_dir / f"{name}.json"
        if target.exists():
            return "already there"
        record = collect(name)
        target.write_text(json.dumps(record))
        return "error" if "error" in record else "ok"

    tally: dict[str, int] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for n, how in enumerate(pool.map(one, names)):
            tally[how] = tally.get(how, 0) + 1
            if (n + 1) % 100 == 0:
                print(n + 1, tally, flush=True)
    print("DONE", tally, flush=True)
    return 0 if not tally.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
