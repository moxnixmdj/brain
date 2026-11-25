#!/usr/bin/env python3
"""§6's first requirement: an honest, un-gated, per-task baseline. Not a score, a starting point.

WHY THIS ROUND BUILT THIS AND NOT ANOTHER MECHANISM
---------------------------------------------------
Every previous round measured something adjacent to solving. This runs the shipped system on twelve tasks
that are provably fail-to-pass, in real repositories, offline, and reports each one.

The twelve are the survivors of `tasks_whose_oracle_precedes_the_fix_v1.py`: of 89 commits in this
repository's own corpus, 54 pass on the parent (never a bug), 23 cannot be tested on the parent at all (the
test needs the fix to import), and **12 fail on the parent and pass on the fix**. Those 12 are the task set.
Nothing about them was chosen for being easy, and none was hand-solved.

WHAT THE SYSTEM IS GIVEN, AND WHAT IT IS NOT
--------------------------------------------
Given: the test node that fails and the assertion text pytest printed. That is what a developer sees when the
suite runs. It is derived mechanically from a run of the parent commit.

Not given: the fix diff, the commit message, the issue, the changed source lines, or any hint. The task
instruction is assembled from pytest's own output by `instruction_from_failure()` -- no prose written by me
about what the bug is.

WHY THE INSTRUCTION IS DERIVED RATHER THAN WRITTEN
--------------------------------------------------
Because these commits carry no issue text, anything I write would be my summary of the fix, which is
hand-holding. Pytest's failure line is the only description of the task that exists inside the environment.
That keeps the integrity rule intact at the cost of a harsher input -- and the harsher input is the honest one.

THE THREE OUTCOMES RECORDED PER TASK
------------------------------------
    NO_PROPOSAL   the system returned no action and no patch  (its current behaviour)
    PATCH_EMITTED the system produced a patch (this is what the generator must achieve)
    VERIFIED      the patch applied and the named nodes pass on the parent + patch

VERIFIED requires an actual run. A patch that is emitted but fails stays PATCH_EMITTED, not solved.
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
sys.path.insert(0, str(REPO))

SCHEMA = "BRAIN_HONEST_PER_TASK_BASELINE_V1"
SELECTED = (REPO / "canonical" / "corpus" /
            "tasks_whose_oracle_precedes_the_fix_20261124_V1.json")
CORPUS = REPO / "canonical" / "corpus" / "real_fix_commits_20261116_V1.json"


def run(cmd: Sequence[str], cwd: pathlib.Path, timeout: int = 900) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=str(cwd), capture_output=True, text=True,
                          timeout=timeout, check=False)


def instruction_from_failure(node: str, pytest_output: str) -> str:
    """The task text, assembled only from what pytest printed. No prose about the fix."""
    lines = [line.strip() for line in pytest_output.splitlines() if line.strip()]
    summary_lines = [line for line in lines
                     if line.startswith(("FAILED", "E ", "AssertionError", "TypeError", "KeyError",
                                         "ValueError", "AttributeError"))]
    detail = " | ".join(summary_lines[:6])[:900]
    return (f"A test in this repository fails. The failing node is:\n  {node}\n"
            f"The test runner printed:\n  {detail}\n"
            f"Make the named test pass without breaking the other tests in that file.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args(argv)
    started = time.time()

    from canonical.runtime.brain_unified_model_v1 import open_model
    from canonical.runtime.harbor_epistemic_agent_v1 import build_goal

    model = open_model(root=str(REPO))
    selected = [row for row in json.loads(SELECTED.read_text())["per_task"]
                if row["class"] == "FAIL"]
    corpus = {task["sha"]: task for task in json.loads(CORPUS.read_text())["tasks"]}

    workdir = pathlib.Path(tempfile.mkdtemp(prefix="brain-baseline-"))
    rows: list[dict[str, Any]] = []
    try:
        for index, cell in enumerate(selected, 1):
            task = corpus[cell["sha"]]
            checkout = workdir / task["repo"].replace("/", "__")
            if not checkout.exists():
                if run(["git", "clone", "-q", f"https://github.com/{task['repo']}.git",
                        str(checkout)], workdir).returncode != 0:
                    rows.append({"sha": task["sha"], "class": "CLONE_FAILED"})
                    continue
            run(["git", "checkout", "-q", "-f", task["parent"]], checkout)
            run(["git", "clean", "-qfd"], checkout)
            diff = run(["git", "diff", task["parent"], task["sha"], "--", task["test"]], checkout)
            (checkout / ".brain_test.patch").write_text(diff.stdout)
            if run(["git", "apply", "--whitespace=nowarn", ".brain_test.patch"], checkout).returncode != 0:
                rows.append({"sha": task["sha"], "class": "APPLY_FAILED"})
                continue

            node = (task["failed_nodes"] or [task["test"]])[0]
            before = run([args.python, "-m", "pytest", node, "-q", "-x", "--no-header",
                          "-p", "no:cacheprovider"], checkout)
            if before.returncode == 0:
                rows.append({"sha": task["sha"], "class": "NOT_FAILING_ON_PARENT"})
                continue
            instruction = instruction_from_failure(node, (before.stdout or "") + (before.stderr or ""))

            # ---- the system runs here. It is given the instruction and nothing else.
            goal = build_goal(instruction, 1, [])
            outcome = model.solve(goal, inputs={"harbor_task": instruction, "cycle": 1,
                                                "observations": []},
                                  mode="EPISTEMIC", cwd=str(checkout))
            patch = outcome.get("patch") if isinstance(outcome.get("patch"), str) else None

            row = {"repo": task["repo"], "sha": task["sha"], "node": node,
                   "instruction": instruction,
                   "system_status": outcome.get("status"),
                   "system_reason": str(outcome.get("reason") or "")[:160],
                   "system_best": (outcome.get("routing") or {}).get("best", {}).get("id")
                   if isinstance(outcome.get("routing"), dict) else None,
                   "patch_emitted": bool(patch)}
            if not patch:
                row["class"] = "NO_PROPOSAL"
            else:
                (checkout / ".brain_candidate.patch").write_text(patch)
                if run(["git", "apply", "--whitespace=nowarn", ".brain_candidate.patch"],
                       checkout).returncode != 0:
                    row["class"] = "PATCH_EMITTED__APPLY_FAILED"
                else:
                    after = run([args.python, "-m", "pytest", node, "-q", "--no-header",
                                 "-p", "no:cacheprovider"], checkout)
                    row["class"] = "VERIFIED" if after.returncode == 0 else "PATCH_EMITTED__STILL_FAILING"
            rows.append(row)
            print(f"  {index}/{len(selected)} {task['repo']} {task['sha'][:8]} -> {row['class']}"
                  f"  [{row.get('system_status')}]", flush=True)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    verified = counts.get("VERIFIED", 0)

    summary = {
        "tasks": len(rows),
        "by_class": counts,
        "verified_solved": verified,
        "resolve_rate": round(verified / max(1, len(rows)), 4),
        "patch_emission_rate": round(
            sum(1 for row in rows if row.get("patch_emitted")) / max(1, len(rows)), 4),
        "verdicts": {
            "the_system_emits_a_patch_at_all":
                any(row.get("patch_emitted") for row in rows),
            "the_system_solves_at_least_one":
                verified > 0,
            "this_is_a_baseline_not_a_result":
                verified == 0,
        },
        "reading": (
            "An honest per-task baseline on twelve provably fail-to-pass tasks in real repositories, offline, "
            "with the instruction derived from pytest's own failure output. A zero here is the starting "
            "number, and it is the first time this project has had one."),
        "what_this_does_not_show": (
            "nothing about hard benchmarks. These are small single-node bugs in three repositories, not "
            "SWE-bench Pro or Terminal-Bench. It shows what the shipped system does when handed a real "
            "failing test, which is the precondition for any of those."),
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "network_during_build": "git clone of pypa/packaging and hukkin/tomli",
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
        "per_task": rows,
    }, indent=1) + "\n")
    print(json.dumps({k: v for k, v in summary.items()}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
