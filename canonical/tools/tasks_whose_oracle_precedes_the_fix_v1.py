#!/usr/bin/env python3
"""Turn the project's own 89-commit corpus into a real, offline, runnable baseline.

THE DEFECT THIS FIXES
---------------------
`canonical/corpus/real_fix_commits_20261116_V1.json` lists 89 tasks, each with a `parent`, a `sha`, a
`source` file, a `test` file and `failed_nodes`. It has been cited for many rounds as ground truth about
"real fixes". It is not, in the form it is stored: **every one of the sampled commits adds its own tests**, so
the named nodes do not exist at the parent commit.

    pypa/packaging 46167dcd  <-  ecf963ad     src/packaging/ranges.py, tests/test_ranges.py
    fix diff: 426 insertions across source AND tests
    at the parent:  tests/test_ranges.py does not exist
    at the fix:     tests/test_ranges.py::test_copy_and_pickle_preserve_state   288 passed

So a "failed node" recorded against such a commit is a node that was *written together with its fix*, not a
node that failed before it. Any solver "solving" this corpus is completing a task whose own oracle arrived
with the answer.

THE HONEST RECONSTRUCTION, AND WHERE IT LEGITIMATELY STOPS
---------------------------------------------------------
For each task: check out the PARENT, apply ONLY the test-file part of the commit, and run the named nodes.

    FAIL          the test applies and fails on the parent  -> a genuine fail-to-pass task
    COLLECTION    the test file needs the fix to even import -> NOT a valid task; the oracle is unavailable
    PASS          the test applies and passes on the parent -> NOT a task at all
    APPLY_FAILED  the test diff does not apply cleanly      -> excluded, with the reason recorded

Only the FAIL class is usable. Everything else is excluded and counted, because a corpus whose size is
inflated by un-runnable tasks is the same defect as every other number this project has had to retract.

`COLLECTION` is the interesting class: when a commit adds a new module and its tests, no test can fail on the
parent, so no solver can be tested on it. That is not a limitation of this tool; it is a property of the
corpus, and it is the reason a corpus built by mining fix commits overstates what is testable.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
CORPUS = REPO / "canonical" / "corpus" / "real_fix_commits_20261116_V1.json"
SCHEMA = "BRAIN_TASKS_WHOSE_ORACLE_PRECEDES_THE_FIX_V1"


def run(cmd: Sequence[str], cwd: pathlib.Path, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=str(cwd), capture_output=True, text=True,
                          timeout=timeout, check=False)


def prepare(repo: str, workdir: pathlib.Path) -> pathlib.Path | None:
    target = workdir / repo.replace("/", "__")
    if target.exists():
        return target
    result = run(["git", "clone", "-q", f"https://github.com/{repo}.git", str(target)], workdir, timeout=900)
    return target if result.returncode == 0 else None


def classify(task: dict[str, Any], checkout: pathlib.Path, python: str) -> dict[str, Any]:
    parent, sha = task["parent"], task["sha"]
    test_file = task["test"]
    base = {"repo": task["repo"], "sha": sha, "test": test_file,
            "nodes": task["failed_nodes"]}

    reset = run(["git", "checkout", "-q", "-f", parent], checkout)
    if reset.returncode != 0:
        return {**base, "class": "CHECKOUT_FAILED", "detail": reset.stderr[-200:]}
    run(["git", "clean", "-qfd"], checkout)

    diff = run(["git", "diff", parent, sha, "--", test_file], checkout)
    if diff.returncode != 0 or not diff.stdout.strip():
        return {**base, "class": "NO_TEST_DIFF"}
    (checkout / ".brain_test.patch").write_text(diff.stdout)
    applied = run(["git", "apply", "--whitespace=nowarn", ".brain_test.patch"], checkout)
    if applied.returncode != 0:
        return {**base, "class": "APPLY_FAILED", "detail": applied.stderr[-200:]}

    first = task["failed_nodes"][0] if task["failed_nodes"] else test_file
    node = first if first.split("::")[0].endswith(".py") else test_file
    result = run([python, "-m", "pytest", node, "-q", "-x", "--no-header", "-p", "no:cacheprovider"],
                 checkout, timeout=600)
    out = (result.stdout or "") + (result.stderr or "")
    if "error" in out.split("\n")[0].lower() or "ERROR" in out[:400]:
        cls = "COLLECTION"
    elif result.returncode == 0:
        cls = "PASS"
    elif result.returncode in (1, 2):
        cls = "FAIL"
    else:
        cls = f"PYTEST_{result.returncode}"
    tail = [line for line in out.strip().splitlines() if line.strip()][-3:]
    return {**base, "class": cls, "detail": " | ".join(tail)[:300]}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=0, help="0 = all tasks")
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args(argv)
    started = time.time()

    tasks = json.loads(CORPUS.read_text())["tasks"]
    if args.limit:
        tasks = tasks[:args.limit]

    workdir = pathlib.Path(tempfile.mkdtemp(prefix="brain-corpus-"))
    rows: list[dict[str, Any]] = []
    try:
        for index, task in enumerate(tasks, 1):
            checkout = prepare(task["repo"], workdir)
            if checkout is None:
                rows.append({"repo": task["repo"], "sha": task["sha"], "class": "CLONE_FAILED"})
                continue
            try:
                rows.append(classify(task, checkout, args.python))
            except subprocess.TimeoutExpired:
                rows.append({"repo": task["repo"], "sha": task["sha"], "class": "TIMEOUT"})
            print(f"  {index}/{len(tasks)} {task['repo']} {task['sha'][:8]} -> {rows[-1]['class']}",
                  flush=True)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    usable = [row for row in rows if row["class"] == "FAIL"]

    summary = {
        "tasks_in_corpus": len(tasks),
        "by_class": counts,
        "genuine_fail_to_pass_tasks": len(usable),
        "usable_share": round(len(usable) / max(1, len(rows)), 4),
        "verdicts": {
            "the_corpus_as_stored_overstates_the_testable_tasks": counts.get("COLLECTION", 0) > 0,
            "a_majority_are_genuinely_testable": len(usable) > len(rows) / 2,
            "the_recorded_failed_nodes_can_be_failing_nodes":
                counts.get("FAIL", 0) > 0,
        },
        "reading": (
            "Each task is reduced by one question: does the test the commit added still fail when it is "
            "moved back onto the parent? Only those are fail-to-pass tasks. COLLECTION means the test needs "
            "the fix to import, so no solver can be measured on it, and PASS means it was never a bug.")
        ,
        "what_this_does_not_show": (
            "that any solver can solve the genuine tasks. This establishes the task set. The next object is "
            "the same list run against a solver."),
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": str(CORPUS.relative_to(REPO)),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "network_during_build": "git clone of the public repos named in the corpus",
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
        "per_task": rows,
    }, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
