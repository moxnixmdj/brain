#!/usr/bin/env python3
"""Does an action, once learned, chain into a task?

WHY THIS EXISTS
---------------
The claim under test is not "a lesson is remembered". It is: *give the model the most advanced
actions, let it do each once, and it can then do a whole job.* Every prior measurement in this tree
scores a **lesson** -- one edit, in one file, against one demonstration. Nobody had scored a **task**,
which is what a user actually buys.

A task is scored here the way a person scores work: the pull request is done only if every file the
developers changed comes out exactly as they wrote it. One wrong file and a person has to redo it.
That is not a strictness the organ was not told about -- it is what "solved" means.

WHAT IT MEASURES
----------------
For every real pull request in the held-out corpus, and every changed file in it:

  edited    the shipped organ produced something other than the original text
  exact     what it produced is byte-for-byte what the developers wrote
  solved    every changed file in the pull request came out exact

Two numbers come out of that, and the second is the one the claim needs:

  per-file exactness    how often one action lands
  per-task completion   how often a job lands, which is what compounds

THE FIRST-PRINCIPLES POINT
--------------------------
These two are not the same quantity and they are not close. If an action lands with probability `p`
and a job needs `k` of them, the chance the job lands is `p**k` for independent actions and worse once
a growing library starts writing lines nobody asked for (`LEARNING_DOES_NOT_ACCUMULATE_20261112_V1`
measured that: 52 lessons write 39 lines no developer wrote). Learning the action faster cannot change
`p**k`. Only raising `p` or reducing `k` can -- and `k` is set by the job, not by the learner.

Authority: NONE. $0, no model calls, no network.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as taught   # noqa: E402

SCHEMA = "BRAIN_ACTION_CHAIN_TO_TASK_V1"


def measure(pulls: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for pull in pulls:
        changed = [f for f in pull["files"] if f["before"] != f["after"]]
        edited = exact = 0
        for target in changed:
            outcome = None
            for example in changed:
                if example is target:
                    continue
                try:
                    edited_text = taught.edit_by_example(target["before"], example["before"],
                                                         example["after"])
                except Exception:                            # noqa: BLE001 - a refusal
                    continue
                if edited_text is None or edited_text == target["before"]:
                    continue
                if edited_text == target["after"]:
                    outcome = "exact"
                    break
                outcome = "wrong"
            edited += 1 if outcome else 0
            exact += 1 if outcome == "exact" else 0
        rows.append({"pull": pull["name"], "changed_files": len(changed),
                     "files_edited": edited, "files_exact": exact,
                     "solved": bool(changed) and exact == len(changed)})

    changed_total = sum(r["changed_files"] for r in rows)
    exact_total = sum(r["files_exact"] for r in rows)
    solved = sum(1 for r in rows if r["solved"])
    per_file = exact_total / changed_total if changed_total else 0.0
    return {
        "schema": SCHEMA,
        "authority": "NONE",
        "pulls": len(rows),
        "per_pull": rows,
        "per_file_exactness": round(per_file, 4),
        "per_task_completion": round(solved / len(rows), 4) if rows else 0.0,
        "changed_files": changed_total,
        "files_exact": exact_total,
        "tasks_solved": solved,
        "the_compounding": {
            "reading": "with an action that lands p of the time and a job that needs k of them, the "
                       "job lands p**k of the time for independent actions, and less once a growing "
                       "library writes lines nobody asked for",
            "measured_p": round(per_file, 4),
            "at_k_1": round(per_file, 4),
            "at_k_2": round(per_file ** 2, 4),
            "at_k_3": round(per_file ** 3, 4),
            "at_k_10": float(f"{per_file ** 10:.3e}"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pulls", type=pathlib.Path, required=True)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    record = measure(json.loads(args.pulls.read_text()))
    text = json.dumps(record, indent=1)
    if args.json:
        args.json.write_text(text + "\n")
        print("written ->", args.json)
        print(json.dumps({k: v for k, v in record.items()
                          if k not in ("per_pull", "schema")}, indent=1))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
