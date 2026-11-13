#!/usr/bin/env python3
"""Where a small passing patch stands among the programs made by writing one line as the task's text writes it.

Why this exists
---------------
canonical/verification/FIX_CONTENT_IN_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json: the issue text
names half of what the small fixes of 80 real tasks bring in, and its rule says to build a list
that takes its content from the task text and to count it as the earlier lists were counted. The
smallest part of such a list is canonical/runtime/quoted_in_the_task_text_v1.py: whole lines the
text writes out, put in place of a line that resembles them or next to a line. This counts it:

  for the 80 tasks, with the function given as before, the place of a small test-passing patch in
  that list; how many tasks that adds to the 16 the earlier lists reach within 200 candidates; and
  the same with another task's issue text.

The budget is the earlier one, 200 candidates, spent as: the first FIRST of this list, then the
two earlier lists in turns for the rest. A task the earlier lists reached at places 181 to 200
falls out by that, and is counted as fallen out.

Definitions of more than 1,000 nodes are not asked, as before. Nothing here runs a program, a
test or a model. What was expected and the rule were written here before any place was counted.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import hashlib
import json
import pathlib
import statistics
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import quoted_in_the_task_text_v1 as quoted  # noqa: E402
from canonical.tools import fix_content_in_task_text_measure_v1 as content  # noqa: E402
from canonical.tools import passing_patch_shape_measure_v1 as passing  # noqa: E402
from canonical.tools import small_passing_patch_place_measure_v1 as place  # noqa: E402

SCHEMA = "BRAIN_QUOTED_LINE_PLACE_V1"
PLACE_RECORD = content.PLACE_RECORD
BUDGET = place.BUDGET
FIRST = 20                       # candidates of this list tried before the earlier lists get the rest of the budget
RANKS = (1, 5, 20, 100)
OTHER_TASK = content.OTHER_TASK

EXPECTED: dict[str, Any] = {
    "written": "2026-11-12 about 22:30 UTC, before any place in this list was counted. Known by then, from the record named above: the issue quotes "
               "the line as a passing patch leaves it for 10 of the 80 tasks, 9 of which no earlier list reaches; and the list was tried on one made-up example.",
    "tasks of 80 with a small passing patch among the first 20 of this list": [4, 10],
    "of them tasks no earlier list reached within 200": [4, 9],
    "tasks of 80 within 200: the first 20 of this list, then the two earlier lists in turns for 180": [19, 25],
    "tasks of 80 with a small passing patch among the first 20 of this list made from another task's text": [0, 1],
    "median number of candidates this list makes for a definition": [20, 400],
    "median number of code lines read from an issue text": [2, 20],
    "rule": "If this list brings at least 5 tasks that no earlier list reached to within its first 20 candidates, it is tried first, for 20 candidates, in "
            "any repair run built here. If fewer than 3, it is kept out of such a run. 3 or 4: undecided. Whatever it brings, it reads whole lines only: "
            "the list still to build is the one that puts a small piece into a line, written with the names the text points to.",
}


def of_definition(before: str, wanted: Sequence[str], text: str) -> dict[str, Any]:
    """The place (from 1) of each wanted text among the candidates made for `before` from `text`; None where it is not among them."""
    made = quoted.candidates(before, text)
    where = {program: at for at, program in enumerate(made, 1)}
    return {"places": [where.get(program) for program in wanted], "candidates": len(made)}


def of_task(patches: Sequence[Mapping[str, Any]], text: str, max_nodes: int = place.MAX_NODES) -> dict[str, Any]:
    rows, definitions = [], {}
    for before in dict.fromkeys(patch["before"] for patch in patches):
        mine = [patch for patch in patches if patch["before"] == before]
        if place.nodes_of(before) > max_nodes:
            definitions[before] = {"places": [None] * len(mine), "candidates": None}
        else:
            definitions[before] = of_definition(before, [patch["wanted"] for patch in mine], text)
        rows.extend({"shape": patch["shape"], "place": at} for patch, at in zip(mine, definitions[before]["places"]))
    found = [row["place"] for row in rows if row["place"] is not None]
    return {"patches": rows, "best": min(found) if found else None, "candidates": [row["candidates"] for row in definitions.values()],
            "code_lines": len(quoted.code_lines(text))}


def within(values: Sequence[int | None]) -> dict[str, int]:
    out = {str(rank): sum(1 for value in values if value is not None and value <= rank) for rank in RANKS}
    out["at any place"] = sum(1 for value in values if value is not None)
    out["in no place"] = sum(1 for value in values if value is None)
    return out


def summarise(per_task: Mapping[str, Mapping[str, Any]], earlier_in_turns: Mapping[str, int | None]) -> dict[str, Any]:
    """The counts. `earlier_in_turns`: the best place of a small passing patch in the two earlier lists taken in turns."""
    tasks = sorted(per_task)
    here = {task: per_task[task]["best"] is not None and per_task[task]["best"] <= FIRST for task in tasks}
    before = {task: earlier_in_turns.get(task) is not None and earlier_in_turns[task] <= BUDGET for task in tasks}
    still = {task: earlier_in_turns.get(task) is not None and earlier_in_turns[task] <= BUDGET - FIRST for task in tasks}
    shapes = collections.Counter(min((row for row in per_task[task]["patches"] if row["place"] is not None), key=lambda row: row["place"])["shape"]
                                 for task in tasks if per_task[task]["best"] is not None)
    made = [count for task in tasks for count in per_task[task]["candidates"] if count is not None]
    return {
        "tasks": len(tasks), "tasks_by_best_place_in_this_list": within([per_task[task]["best"] for task in tasks]),
        "tasks_within_the_first_of_this_list": sum(here.values()),
        "of_them_not_reached_by_the_earlier_lists": sum(1 for task in tasks if here[task] and not before[task]),
        "tasks_the_earlier_lists_reached_within_the_budget": sum(before.values()),
        "of_them_fallen_out_with_less_budget_and_not_reached_here": sum(1 for task in tasks if before[task] and not still[task] and not here[task]),
        "tasks_within_the_budget_with_this_list_first": sum(1 for task in tasks if here[task] or still[task]),
        "by_shape_of_the_patch_found": dict(shapes),
        "median_candidates_for_a_definition": statistics.median(made) if made else None,
        "definitions_asked": len(made), "definitions_not_asked": sum(1 for task in tasks for count in per_task[task]["candidates"] if count is None),
        "definitions_for_which_the_list_is_empty": sum(1 for count in made if count == 0),
        "median_code_lines_read_from_an_issue_text": statistics.median([per_task[task]["code_lines"] for task in tasks]) if tasks else None,
        "tasks_whose_issue_text_has_no_code_line": sum(1 for task in tasks if per_task[task]["code_lines"] == 0),
    }


def rule(new: int) -> dict[str, Any]:
    verdict = ("tried first, for 20 candidates" if new >= 5 else "kept out" if new < 3 else "undecided")
    return {"tasks_no_earlier_list_reached_that_are_within_the_first_20": new, "verdict": verdict}


def code_sha256() -> dict[str, str]:
    names = ("canonical/tools/quoted_line_place_measure_v1.py", "canonical/runtime/quoted_in_the_task_text_v1.py",
             "canonical/tools/fix_content_in_task_text_measure_v1.py", "canonical/tools/small_passing_patch_place_measure_v1.py",
             "canonical/tools/passing_patch_shape_measure_v1.py", "canonical/runtime/fix_shape_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cache-dir", required=True, type=pathlib.Path)
    parser.add_argument("--pull-requests-dir", required=True, type=pathlib.Path)
    parser.add_argument("--statements-dir", required=True, type=pathlib.Path)
    parser.add_argument("--place-record", type=pathlib.Path, default=PLACE_RECORD)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)

    started = time.time()
    say = lambda line: print(line, round(time.time() - started, 1), "s", flush=True)  # noqa: E731
    earlier = json.loads(args.place_record.read_text())["per_task"]
    tasks = sorted(earlier)
    records = {task: json.loads((args.pull_requests_dir / f"{task}.json").read_text()) for task in tasks}
    then = passing.verdicts(args.cache_dir, passing.WITH_PATCHES)
    with_patches = {name: found for name, found in then.items() if (args.cache_dir / passing.WITH_PATCHES[:10] / name / "all_preds.jsonl").exists()}
    found_targets = place.targets(records, tasks, with_patches, lambda name: passing.patches(args.cache_dir, name))
    say(f"{len(tasks)} tasks, {sum(len(rows) for rows in found_targets.values())} small passing patches")
    issues = content.statements(args.statements_dir, tasks)
    other = {task: tasks[(at + OTHER_TASK) % len(tasks)] for at, task in enumerate(tasks)}
    per_task = {task: of_task(found_targets[task], issues[task]) for task in tasks if found_targets[task] and task in issues}
    say("this list counted")
    with_another = {task: of_task(found_targets[task], issues[other[task]]) for task in per_task}
    in_turns = {task: earlier[task][2] for task in tasks}
    summary, control = summarise(per_task, in_turns), summarise(with_another, in_turns)
    record = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expected_before": EXPECTED, "summary": summary, "with_another_tasks_text": control, "rule": rule(summary["of_them_not_reached_by_the_earlier_lists"]),
        "per_task": per_task, "issue_texts_from": list(content.STATEMENTS), "experiments_commit": passing.WITH_PATCHES,
        "submissions_with_patches": len(with_patches), "model_calls": 0, "programs_run": 0, "tests_run": 0, "code_sha256": code_sha256(),
        "seconds": round(time.time() - started, 1),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("WROTE", args.out, record["seconds"], "s", flush=True)
    print(json.dumps({"rule": record["rule"], "summary": summary, "control": control}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
