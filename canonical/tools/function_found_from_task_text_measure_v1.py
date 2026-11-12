#!/usr/bin/env python3
"""Whether the task's text finds the function, and whether the list of quoted lines reaches tasks it was not shaped on.

Why this exists
---------------
Two things were open after canonical/verification/QUOTED_LINE_PLACE_SWEBENCH_VERIFIED_20261112_V1.json:

  the list was shaped on the 80   canonical/runtime/quoted_in_the_task_text_v1.py was written while
                                  looking at the 80 tasks that have a small test-passing patch, and
                                  reaches 7 of them within 5 candidates. Whether it reaches a task
                                  it was not shaped on has not been counted.
  the function was given          every count so far handed over the function to change. A run has
                                  a file at best.

So, for every task of SWE-bench Verified that has a test-passing patch which changes ONE FUNCTION
of one file the expert changed too (any size of change, not only the small ones):

  function given   the place of such a patch among the first FIRST candidates of the quoted-line
                   list for that function -- for the 80, and for the tasks outside the 80
  the function     where such a function stands among the functions of its file when
                   canonical/runtime/function_the_task_text_points_at_v1.py orders them by the
                   task text; and where it stands counted from the top of the file
  file given       the place of such a patch in that module's list for the file: the first 5
                   quoted-line candidates of each of the first 4 functions, 20 in all

each also with ANOTHER task's issue text: the next task of the same project in the sorted list.

For the 80, the earlier lists (the learner, pieces taken out) were counted with the function given
and reach 16 tasks within 200. With the file given they are spent on the first function only, for
the 180 that the quoted lines leave: a task stays reached if its function is the first. Where a
task's small passing patches stand in more than one function, that is a range.

The patches are the recorded ones; no program, test or model is run. What was expected and the
rule were written here before anything was counted: EXPECTED below.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import multiprocessing
import pathlib
import statistics
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import function_the_task_text_points_at_v1 as pointer  # noqa: E402
from canonical.runtime import quoted_in_the_task_text_v1 as quoted  # noqa: E402
from canonical.tools import expert_fix_pull_request_collector_v1 as collector  # noqa: E402
from canonical.tools import expert_fix_repetition_measure_v1 as repetition  # noqa: E402
from canonical.tools import fix_content_in_task_text_measure_v1 as content  # noqa: E402
from canonical.tools import passing_patch_shape_measure_v1 as passing  # noqa: E402
from canonical.tools import small_passing_patch_place_measure_v1 as place  # noqa: E402

SCHEMA = "BRAIN_FUNCTION_FOUND_FROM_TASK_TEXT_V1"
PASSING_RECORD = place.PASSING_RECORD
PLACE_RECORD = content.PLACE_RECORD
BUDGET = place.BUDGET
FIRST = 20                       # candidates of the quoted-line list looked at: the share the earlier rule gives that list
RANKS = (1, 4, 10)
THE_80, THE_REST, ALL = "the 80 it was shaped on", "tasks outside the 80", "all"

EXPECTED: dict[str, Any] = {
    "written": "2026-11-12 22:55 UTC, before anything was counted. Known by then: the earlier records (the list reaches 7 of the 80 within 5 "
               "candidates, function given, definitions of at most 1,000 nodes; the changed file of the 80 holds a median of 41 functions; 276 of 500 "
               "tasks have a passing patch within one statement), and a published figure for finding the FILE by BM25 (first: about 40%). Nothing of "
               "the tasks outside the 80, and no rank of any function.",
    "tasks of 500 with a passing patch that changes one function of a file the expert changed": [280, 430],
    "tasks outside the 80 with such a patch within the first 20 quoted-line candidates, function given": [3, 30],
    "tasks of the 80 with such a patch within the first 20 quoted-line candidates, function given, definitions of any size": [7, 12],
    "all tasks, the same with another task's text": [0, 2],
    "share of the tasks for which such a function is the first of its file in the order the task text gives": [0.30, 0.60],
    "share for which it is among the first 4": [0.55, 0.85],
    "share for which it is the first with another task's text": [0.03, 0.20],
    "all tasks with such a patch within the 20 candidates made for the file": [5, 35],
    "of the tasks reached with the function given, the share still reached with the file given": [0.6, 1.0],
    "median number of functions in the file": [15, 60],
    "rule": "If, with only the file given, the quoted-line list still reaches at least two thirds of the tasks it reaches with the function given "
            "(within 20 candidates both ways), a repair run built here starts from the file and the task text, not from a function handed to it, and "
            "the next thing to count is finding the file, which needs the projects' trees. If it keeps fewer than one third, finding the function is "
            "the limiting step and nothing else is built before it. In between: undecided. Separately, and whatever the first part says: if the "
            "list reaches no task outside the 80 within 20 candidates, what it showed on the 80 does not carry to tasks it was not shaped on.",
}


# --------------------------------------------------------------------------- #
# one patch: the function it changes
# --------------------------------------------------------------------------- #
def cut(files: passing.Files, diff: str) -> tuple[str, tuple[int, int], str, str] | None:
    """(the path, the lines of the smallest definition that holds every change, that definition
    before, and after) for a patch that changes exactly one Python file the expert changed too;
    None otherwise. The cut is passing.narrowed's; here the lines are kept as well."""
    changed = [row for row in passing.files_of(diff) if not collector.is_test(files.repo, row["path"])]
    there = [row for row in changed if row["path"].endswith(".py") and row["status"] != "added"]
    if len(there) != 1 or there[0]["status"] != "modified" or there[0]["path"] not in files.before:
        return None
    path = there[0]["path"]
    before = files.before[path]
    try:
        after = repetition.apply_patch(before, there[0]["patch"], [])
    except (ValueError, IndexError):
        return None
    read = files.read(path)
    if read is None or before == after:
        return None
    a, b = before.split("\n"), after.split("\n")
    most = min(len(a), len(b))
    front = 0
    while front < most and a[front] == b[front]:
        front += 1
    back = 0
    while back < most and a[len(a) - 1 - back] == b[len(b) - 1 - back]:
        back += 1
    ways = {(front, min(back, most - front)), (min(front, most - back), back)}
    for span in read[0]:
        if not any(span[0] - 1 <= ahead and len(a) - behind <= span[1] for ahead, behind in ways):
            continue
        parts = passing.narrowed(before, after, [span])
        if parts is not None:
            return path, (span[0], span[1]), parts[0], parts[1]
    return None


def place_in(made: Sequence[str], wanted: set[str]) -> int | None:
    """The place, from 1, of the first candidate that is one of the wanted programs."""
    for at, program in enumerate(made, 1):
        if program in wanted:
            return at
    return None


# --------------------------------------------------------------------------- #
# one task
# --------------------------------------------------------------------------- #
def of_task(job: tuple[str, Mapping[str, Any], Sequence[str], str, str, bool]) -> tuple[str, dict[str, Any]]:
    """Everything counted for one task: its functions with a passing patch, where the text ranks them, and the places."""
    task, record, diffs, text, other_text, shaped_on = job
    files = passing.Files(record)
    functions: dict[str, list[pointer.Function]] = {}
    targets: dict[tuple[str, tuple[int, int]], dict[str, Any]] = {}
    not_one_function = 0
    for diff in diffs:
        found = cut(files, diff)
        if found is None:
            not_one_function += 1
            continue
        path, span, before, after = found
        if path not in functions:
            functions[path] = pointer.functions_of(files.before[path])
        if not any((function.first, function.last) == span for function in functions[path]):
            not_one_function += 1                                     # a class, or a statement at the top of the file
            continue
        try:
            wanted = place.normal(after)
        except (SyntaxError, ValueError, RecursionError, MemoryError):
            not_one_function += 1
            continue
        target = targets.setdefault((path, span), {"before": before, "wanted": set(), "small": False})
        target["wanted"].add(wanted)
        if shaped_on and not target["small"]:
            target["small"] = bool(passing.smallness(passing.shape_of_patch(files, diff))["listed"])

    orders = {path: (pointer.order(files.before[path], text, functions[path]), pointer.order(files.before[path], other_text, functions[path]))
              for path in {path for path, _ in targets}}
    rows = []
    for (path, span), target in sorted(targets.items()):
        own, other = orders[path]
        spans_own, spans_other = [(f.first, f.last) for f in own], [(f.first, f.last) for f in other]
        rows.append({
            "path": path, "first": span[0], "last": span[1], "functions_in_the_file": len(functions[path]),
            "rank": spans_own.index(span) + 1, "rank_other_text": spans_other.index(span) + 1,
            "from_the_top": [(f.first, f.last) for f in functions[path]].index(span) + 1,
            "place": place_in(quoted.candidates(target["before"], text, at_most=FIRST), target["wanted"]),
            "place_other_text": place_in(quoted.candidates(target["before"], other_text, at_most=FIRST), target["wanted"]),
            "small": target["small"],
        })

    def in_the_file(which: str) -> int | None:
        best = None
        for path in sorted({path for path, _ in targets}):
            made = pointer.candidates(files.before[path], which)
            for at, (function, program) in enumerate(made, 1):
                target = targets.get((path, (function.first, function.last)))
                if target is not None and program in target["wanted"]:
                    best = at if best is None else min(best, at)
                    break
        return best

    return task, {"passing_patches": len(diffs), "not_one_function": not_one_function, "functions": rows,
                  "file_given": in_the_file(text) if rows else None, "file_given_other_text": in_the_file(other_text) if rows else None,
                  "code_lines": len(quoted.code_lines(text))}


def other_text_of(tasks: Sequence[str]) -> dict[str, str]:
    """For each task the next task of the same project in the sorted list (the first after the last); of any project where it is the only one."""
    ordered = sorted(tasks)
    by_project: dict[str, list[str]] = {}
    for task in ordered:
        by_project.setdefault(task.rsplit("-", 1)[0], []).append(task)
    out = {}
    for at, task in enumerate(ordered):
        mine = by_project[task.rsplit("-", 1)[0]]
        out[task] = mine[(mine.index(task) + 1) % len(mine)] if len(mine) > 1 else ordered[(at + 1) % len(ordered)]
    return out


# --------------------------------------------------------------------------- #
# all of them
# --------------------------------------------------------------------------- #
def _best(rows: Sequence[Mapping[str, Any]], key: str) -> int | None:
    values = [row[key] for row in rows if row[key] is not None]
    return min(values) if values else None


def _share(count: int, of: int) -> float | None:
    return round(count / of, 3) if of else None


def part(per_task: Mapping[str, Mapping[str, Any]], tasks: Sequence[str]) -> dict[str, Any]:
    """The counts over some of the tasks that have a passing patch within one function."""
    mine = [task for task in tasks if per_task[task]["functions"]]
    rows = {task: per_task[task]["functions"] for task in mine}
    given = {task: _best(rows[task], "place") for task in mine}
    given_other = {task: _best(rows[task], "place_other_text") for task in mine}
    rank = {task: _best(rows[task], "rank") for task in mine}
    rank_other = {task: _best(rows[task], "rank_other_text") for task in mine}
    top = {task: _best(rows[task], "from_the_top") for task in mine}
    in_file = {task: per_task[task]["file_given"] for task in mine}
    in_file_other = {task: per_task[task]["file_given_other_text"] for task in mine}
    reached = [task for task in mine if given[task] is not None]
    kept = [task for task in reached if in_file[task] is not None]

    def within(values: Mapping[str, int | None], ranks: Sequence[int]) -> dict[str, int]:
        return {str(n): sum(1 for value in values.values() if value is not None and value <= n) for n in ranks}

    return {
        "tasks": len(mine),
        "function_given__tasks_with_a_passing_patch_among_the_first": within(given, (1, 5, FIRST)),
        "function_given__with_another_tasks_text": within(given_other, (1, 5, FIRST)),
        "the_function_is_among_the_first_of_its_file": within(rank, RANKS),
        "the_function_is_among_the_first_of_its_file__share": {str(n): _share(sum(1 for value in rank.values() if value <= n), len(mine)) for n in RANKS},
        "with_another_tasks_text": within(rank_other, RANKS),
        "with_another_tasks_text__share": {str(n): _share(sum(1 for value in rank_other.values() if value <= n), len(mine)) for n in RANKS},
        "counted_from_the_top_of_the_file": within(top, RANKS),
        "file_given__tasks_with_a_passing_patch_among_the_20": sum(1 for value in in_file.values() if value is not None),
        "file_given__with_another_tasks_text": sum(1 for value in in_file_other.values() if value is not None),
        "reached_with_the_function_given": len(reached), "of_them_still_reached_with_the_file_given": len(kept),
        "share_kept": _share(len(kept), len(reached)),
        "reached_with_the_file_given_only": sum(1 for task in mine if in_file[task] is not None and given[task] is None),
        "median_functions_in_the_file": statistics.median([min(row["functions_in_the_file"] for row in rows[task]) for task in mine]) if mine else None,
        "tasks_whose_file_has_one_function": sum(1 for task in mine if min(row["functions_in_the_file"] for row in rows[task]) == 1),
    }


def earlier_lists(per_task: Mapping[str, Mapping[str, Any]], earlier_in_turns: Mapping[str, int | None]) -> dict[str, Any]:
    """For the 80: what the lists counted before reach when they are spent on the first function of the file only."""
    before = [task for task, at in earlier_in_turns.items() if at is not None and at <= BUDGET]
    still = [task for task in before if earlier_in_turns[task] <= BUDGET - FIRST]
    surely, perhaps = [], []
    for task in still:
        ranks = [row["rank"] for row in per_task.get(task, {}).get("functions", []) if row["small"]]
        if ranks and all(rank == 1 for rank in ranks):
            surely.append(task)
        if any(rank == 1 for rank in ranks):
            perhaps.append(task)
    quoted_in_file = {task for task in earlier_in_turns if per_task.get(task, {}).get("file_given") is not None}
    quoted_given = {task for task in earlier_in_turns if _best(per_task.get(task, {}).get("functions", []), "place") is not None}
    return {
        "reached_by_the_earlier_lists_within_200__function_given": len(before), "of_them_within_180": len(still),
        "of_them_with_the_function_first_of_its_file__at_least": len(surely), "at_most": len(perhaps),
        "tasks_of_the_80_within_200__function_given__quoted_lines_first": len(quoted_given | set(still)),
        "tasks_of_the_80_within_200__file_given__at_least": len(quoted_in_file | set(surely)), "file_given__at_most": len(quoted_in_file | set(perhaps)),
    }


def summarise(per_task: Mapping[str, Mapping[str, Any]], the_80: Sequence[str], earlier_in_turns: Mapping[str, int | None]) -> dict[str, Any]:
    tasks = sorted(per_task)
    inside = [task for task in tasks if task in set(the_80)]
    outside = [task for task in tasks if task not in set(the_80)]
    return {
        "tasks_with_a_passing_patch": len(tasks),
        "tasks_with_a_passing_patch_within_one_function": sum(1 for task in tasks if per_task[task]["functions"]),
        ALL: part(per_task, tasks), THE_80: part(per_task, inside), THE_REST: part(per_task, outside),
        "the_earlier_lists_on_the_80": earlier_lists(per_task, earlier_in_turns),
        "tasks_whose_issue_text_has_no_code_line": sum(1 for task in tasks if per_task[task]["functions"] and per_task[task]["code_lines"] == 0),
    }


def rule(summary: Mapping[str, Any]) -> dict[str, Any]:
    kept = summary[ALL]["share_kept"]
    outside = summary[THE_REST]["function_given__tasks_with_a_passing_patch_among_the_first"][str(FIRST)]
    verdict = ("undecided: nothing reached with the function given" if kept is None
               else "start from the file and the task text; next, count finding the file" if kept >= 2 / 3
               else "finding the function is the limiting step" if kept < 1 / 3 else "undecided")
    return {"share_of_the_reached_tasks_kept_with_the_file_given": kept, "verdict": verdict,
            "tasks_outside_the_80_reached_within_20": outside,
            "carries_to_tasks_it_was_not_shaped_on": outside > 0}


def code_sha256() -> dict[str, str]:
    names = ("canonical/tools/function_found_from_task_text_measure_v1.py", "canonical/runtime/function_the_task_text_points_at_v1.py",
             "canonical/runtime/quoted_in_the_task_text_v1.py", "canonical/runtime/bound_capabilities/objective_relevance_bm25.py",
             "canonical/tools/passing_patch_shape_measure_v1.py", "canonical/tools/small_passing_patch_place_measure_v1.py",
             "canonical/tools/fix_content_in_task_text_measure_v1.py", "canonical/runtime/fix_shape_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cache-dir", required=True, type=pathlib.Path)
    parser.add_argument("--pull-requests-dir", required=True, type=pathlib.Path)
    parser.add_argument("--statements-dir", required=True, type=pathlib.Path)
    parser.add_argument("--passing-record", type=pathlib.Path, default=PASSING_RECORD)
    parser.add_argument("--place-record", type=pathlib.Path, default=PLACE_RECORD)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)

    started = time.time()
    say = lambda line: print(line, round(time.time() - started, 1), "s", flush=True)  # noqa: E731
    tasks = sorted(json.loads(args.passing_record.read_text())["per_task"])
    earlier = {task: row[2] for task, row in json.loads(args.place_record.read_text())["per_task"].items()}
    then = passing.verdicts(args.cache_dir, passing.WITH_PATCHES)
    with_patches = {name: found for name, found in then.items() if (args.cache_dir / passing.WITH_PATCHES[:10] / name / "all_preds.jsonl").exists()}
    passed: dict[str, list[str]] = {task: [] for task in tasks}
    for name in sorted(with_patches):
        offered = passing.patches(args.cache_dir, name)
        for task in sorted(with_patches[name]):
            if task in passed and task in offered and offered[task] not in passed[task]:
                passed[task].append(offered[task])
    issues = content.statements(args.statements_dir, tasks)
    other = other_text_of(sorted(issues))
    jobs = [(task, json.loads((args.pull_requests_dir / f"{task}.json").read_text()), passed[task], issues[task], issues[other[task]], task in earlier)
            for task in tasks if passed[task] and task in issues]
    jobs.sort(key=lambda job: -len(job[2]))
    say(f"{len(tasks)} tasks, {len(jobs)} with a passing patch and an issue text, {sum(len(job[2]) for job in jobs)} different passing patches")

    per_task: dict[str, dict[str, Any]] = {}
    with multiprocessing.Pool(args.workers) as pool:
        for done, (task, found) in enumerate(pool.imap_unordered(of_task, jobs, chunksize=1), 1):
            per_task[task] = found
            if done % 50 == 0:
                say(f"{done} tasks")
    summary = summarise(per_task, sorted(earlier), earlier)
    record = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expected_before": EXPECTED, "summary": summary, "rule": rule(summary),
        "per_task": {task: per_task[task] for task in sorted(per_task)}, "shaped_on": sorted(earlier),
        "issue_texts_from": list(content.STATEMENTS), "experiments_commit": passing.WITH_PATCHES, "submissions_with_patches": len(with_patches),
        "model_calls": 0, "programs_run": 0, "tests_run": 0, "code_sha256": code_sha256(), "seconds": round(time.time() - started, 1),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("WROTE", args.out, record["seconds"], "s", flush=True)
    print(json.dumps({"rule": record["rule"], "summary": summary}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
