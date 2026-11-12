#!/usr/bin/env python3
"""How many tries, with the place given? Where a small test-passing repair stands in the lists built here.

What is asked
-------------
PASSING_PATCH_SHAPE_SWEBENCH_VERIFIED_20261112_V1.json found that for 80 of the 500 real tasks of
SWE-bench Verified some patch that passed the benchmark's tests is one small change that "could be
listed". It did not ask whether the lists built in this tree hold that change, nor how far down.
That decides whether a repair run on real projects is worth building, and it can be counted with
no test run: the passing patch is known, so its place in a list is a matter of looking.

For each of those tasks and each of its small passing patches:

  the place GIVEN   the smallest definition that holds the whole change, as it was. This is the
                    best case. Nothing here finds the file or the function.
  the lists         (1) the learner (canonical/runtime/edit_kind_learning_v1.py) shown every
                    HumanEvalFix fix and 1,000 ConDefects fixes, each once: its candidates for the
                    definition, best supported first; (2) every single piece taken out of it
                    (canonical/runtime/take_out_v1.py), the smallest first; and the two taken in
                    turns, the learner's turn first.
  the place         of the passing patch in each list, counted over candidates that compile.
                    A definition of more than 1,000 nodes, or one the learner has not finished in
                    150 seconds, is not asked and counts as not reached (said in the record).

A task counts by the best place any of its small passing patches has. In a repair run every
candidate before that place costs one run of the project's tests.

Beside it: whether the patch is made from what its own definition holds (the learner sees only
the definition), how many functions the changed file holds (the place is given here, not found),
and a control that the instrument can say yes: the same question for the 64 HumanEvalFix
development bugs, each bug's own fix left out of the lessons.

No program and no test is run; no model is called. The patches are other people's recordings.

What was expected and the rule were written into EXPECTED before any place was counted.
What was found: canonical/verification/SMALL_PASSING_PATCH_PLACE_SWEBENCH_VERIFIED_20261112_V1.json.

Usage
-----
  python3 canonical/tools/passing_patch_shape_measure_v1.py --fetch --cache-dir /tmp/rank/experiments
  python3 canonical/tools/small_passing_patch_place_measure_v1.py --cache-dir /tmp/rank/experiments \\
      --pull-requests-dir /tmp/swe/pulls --humanevalfix /tmp/hef/humanevalpack.jsonl \\
      --condefects /tmp/cd/ConDefects --out /tmp/rank/places.json
"""
from __future__ import annotations

import argparse
import ast
import collections
import datetime
import hashlib
import json
import multiprocessing
import pathlib
import signal
import statistics
import sys
import time
import warnings
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_choice_v1 as choice  # noqa: E402
from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
from canonical.runtime import fix_shape_v1 as fix_shape  # noqa: E402
from canonical.runtime import take_out_v1 as take_out  # noqa: E402
from canonical.tools import edit_kind_choice_measure_v1 as choice_measure  # noqa: E402
from canonical.tools import expert_fix_pull_request_collector_v1 as collector  # noqa: E402
from canonical.tools import expert_fix_repetition_measure_v1 as repetition  # noqa: E402
from canonical.tools import expert_fixes_dose_response_measure_v1 as dose  # noqa: E402
from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as hef  # noqa: E402
from canonical.tools import passing_patch_shape_measure_v1 as passing  # noqa: E402

SCHEMA = "BRAIN_SMALL_PASSING_PATCH_PLACE_V1"
PASSING_RECORD = ROOT / "canonical" / "verification" / "PASSING_PATCH_SHAPE_SWEBENCH_VERIFIED_20261112_V1.json"
CONDEFECTS_LESSONS = 1000            # the dose record: what the learner repairs is flat from 1,000 of these lessons on
ORDER_SEED = dose.ORDER_SEEDS[0]     # the first order of the dose record
BUDGET = 200                         # candidates a repair run here has been allowed per bug
RANKS = (1, 10, 100, 200, 1000)
LIMIT_SECONDS = 150                  # the learner on one definition; past this the definition counts as not reached
MAX_NODES = 1000                     # a larger definition (or a whole file) is not asked at all, and counts as not reached
LEARNER, TAKEN_OUT, IN_TURNS = "learner", "taken_out", "in_turns"
LISTS = (IN_TURNS, LEARNER, TAKEN_OUT)
ONE_DEFINITION, WHOLE_FILE = "one definition", "the whole file"

EXPECTED: dict[str, Any] = {
    "written": "2026-11-12 about 21:00 UTC, before any place was counted. Seen by then: how long the learner takes and how many candidates it makes "
               "(2,308 to 60,617) on four definitions of tasks OUTSIDE the 80, with three sets of lessons. No place of any patch.",
    "tasks of 80 with a small passing patch within the first 200 of the two lists in turns": [10, 32],
    "tasks of 80 with a small passing patch within the first 1,000 of the two lists in turns": [14, 40],
    "tasks of 80 with no small passing patch in either list at any place": [30, 60],
    "share of the tasks with a taken-out passing patch that have one within the first 200 of the pieces taken out": [0.7, 1.0],
    "tasks of 80 with a small passing patch made from what its own definition holds": [45, 72],
    "control: HumanEvalFix development bugs of 64 whose published fix is within the first 200 in turns, own fix left out": [15, 35],
    "rule": "With the place given, if a small passing patch stands within the first 200 candidates (the two lists in turns) for at least 40 of the 80 "
            "tasks, a repair run on real projects with the lists built here is worth building; the next thing would be a harness for the projects' "
            "tests. If for fewer than 20, the lists built here do not reach real projects even with the place given: no run is built, and the next "
            "thing to ask is what puts the right name first, not more list. From 20 to 39: undecided; no run is built on this count alone.",
}


# --------------------------------------------------------------------------- #
# the lessons
# --------------------------------------------------------------------------- #
def lessons_of(humanevalfix: pathlib.Path, condefects: pathlib.Path | None, n: int = CONDEFECTS_LESSONS, seed: int = ORDER_SEED) -> tuple[kinds.Lessons, dict[str, Any]]:
    """The learner shown every HumanEvalFix fix and the first `n` ConDefects fixes of the seeded order, each once."""
    lessons = kinds.Lessons()
    bugs = hef.load_bugs(humanevalfix)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for bug in bugs:
            lessons.learn(bug["name"], bug["buggy"], bug["fixed"])
        shown = 0
        if condefects is not None and n:
            pairs, _ = dose.condefects_pairs(condefects)
            for name in dose.order_of(list(pairs), seed)[:n]:
                lessons.learn(name, *pairs[name])
                shown += 1
    return lessons, {"humanevalfix_fixes_shown": len(bugs), "condefects_fixes_shown": shown, "order_seed": seed,
                     "lessons_that_taught_something": len(lessons.lessons), "operators": len(lessons.operators),
                     "condefects_commit": dose.checkout_commit(condefects) if condefects is not None else None}


# --------------------------------------------------------------------------- #
# the small passing patches of a task, each as the definition before and after
# --------------------------------------------------------------------------- #
def normal(text: str) -> str:
    """The text every list here writes its candidates in."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return ast.unparse(ast.parse(text))


def nodes_of(text: str) -> int:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return sum(1 for _ in ast.walk(ast.parse(text)))


def parts_of(files: passing.Files, diff: str) -> tuple[str, str, str] | None:
    """(the definition as it was, as the patch leaves it, what the scope is) for a patch that changes
    exactly one Python file the expert changed too; None otherwise. The steps are those of
    passing.shape_of_patch, so what was given a shape there is cut the same way here."""
    changed = [row for row in passing.files_of(diff) if not collector.is_test(files.repo, row["path"])]
    there = [row for row in changed if row["path"].endswith(".py") and row["status"] != "added"]
    if len(there) != 1 or there[0]["status"] != "modified" or there[0]["path"] not in files.before:
        return None
    before = files.before[there[0]["path"]]
    try:
        after = repetition.apply_patch(before, there[0]["patch"], [])
    except (ValueError, IndexError):
        return None
    read = files.read(there[0]["path"])
    if read is None:
        return None
    parts = passing.narrowed(before, after, read[0])
    return (parts[0], parts[1], ONE_DEFINITION) if parts is not None else (before, after, WHOLE_FILE)


def functions_in(text: str) -> int | None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return sum(1 for node in ast.walk(ast.parse(text)) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
    except (SyntaxError, ValueError, RecursionError):
        return None


def small_passing_patches(record: Mapping[str, Any], offered: Sequence[str]) -> list[dict[str, Any]]:
    """The different small passing patches among `offered` (patches that passed this task's tests):
    each with its definition before and after, its shape, and whether it is made from what the
    definition itself holds."""
    files = passing.Files(record)
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for diff in offered:
        found = passing.shape_of_patch(files, diff)
        if not passing.smallness(found)["listed"]:
            continue
        parts = parts_of(files, diff)
        if parts is None:
            continue
        before, after, scope = parts
        try:
            wanted = normal(after)
            alone = fix_shape.shape(before, after)
        except (SyntaxError, ValueError, RecursionError):
            continue
        row = out.setdefault((before, wanted), {"before": before, "wanted": wanted, "scope": scope, "shape": found["shape"], "kind": found["kind"],
                                                "needs": found["needs"], "nodes": found["nodes"], "times": 0,
                                                "from_its_definition_alone": alone["shape"] in fix_shape.SHAPES and fix_shape.can_be_listed(alone)})
        row["times"] += 1
    return list(out.values())


def targets(records: Mapping[str, Mapping[str, Any]], tasks: Sequence[str], resolved: Mapping[str, set[str]],
            proposals: Callable[[str], Mapping[str, str]]) -> dict[str, list[dict[str, Any]]]:
    """{task: its small passing patches}, read from the submissions' patches that passed."""
    wanted = set(tasks)
    passed: dict[str, list[str]] = {task: [] for task in tasks}
    for name in sorted(resolved):
        mine = wanted & resolved[name]
        if not mine:
            continue
        offered = proposals(name)
        for task in sorted(mine):
            if task in offered and offered[task] not in passed[task]:
                passed[task].append(offered[task])
    return {task: small_passing_patches(records[task], passed[task]) for task in tasks}


# --------------------------------------------------------------------------- #
# the place of a wanted text in the lists
# --------------------------------------------------------------------------- #
class TooLong(Exception):
    pass


def _late(*_: Any) -> None:
    raise TooLong()


def places(lessons: kinds.Lessons, before: str, wanted: Sequence[str], without: Sequence[str] = ()) -> dict[str, Any]:
    """For each wanted text: its place among the learner's candidates for `before`, among the pieces
    taken out of it, and in the two taken in turns (the learner's turn first), each counted from 1
    over candidates that compile; None where it is not in the list."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        votes = lessons.votes(before, without)
        pieces = [(text, -float(fewer), {"kind": kind}) for text, fewer, kind in take_out.candidates(before)]
    piece_texts = [text for text, _, _ in pieces]
    order: list | None = None
    compiles: dict[str, bool] = {}
    rows = []
    for text in wanted:
        row: dict[str, int | None] = {LEARNER: None, TAKEN_OUT: None, IN_TURNS: None}
        if text in piece_texts:
            row[TAKEN_OUT] = piece_texts.index(text) + 1
        if text in votes or row[TAKEN_OUT] is not None:
            if order is None:
                order = kinds.ranking(votes)
            if text in votes:
                row[LEARNER] = choice_measure.place_of(order, text, compiles)
            if row[LEARNER] is not None or row[TAKEN_OUT] is not None:
                for number, item in enumerate(choice.in_turns(choice_measure.programs_only(order, compiles), pieces), 1):
                    if item[0] == text:
                        row[IN_TURNS] = number
                        break
        rows.append(row)
    return {"candidates": len(votes), "pieces": len(pieces), "places": rows}


_LESSONS: kinds.Lessons | None = None
_LIMIT = LIMIT_SECONDS


def _one(job: tuple[str, str, list[str], list[str]]) -> tuple[str, str, dict[str, Any]]:
    """One definition and what is wanted in it, in a worker; the learner is cut off past the limit."""
    key, before, wanted, without = job
    started = time.time()
    nothing = {"candidates": None, "pieces": None, "places": [{LEARNER: None, TAKEN_OUT: None, IN_TURNS: None} for _ in wanted], "too_long": True}
    if nodes_of(before) > MAX_NODES:
        return key, before, {**nothing, "seconds": 0.0}
    signal.signal(signal.SIGALRM, _late)
    signal.alarm(_LIMIT)
    try:
        found = places(_LESSONS, before, wanted, without)
    except TooLong:
        found = nothing
    finally:
        signal.alarm(0)
    found["seconds"] = round(time.time() - started, 1)
    return key, before, found


def asked(lessons: kinds.Lessons, jobs: Sequence[tuple[str, str, list[str], list[str]]], workers: int = 2, limit: int = LIMIT_SECONDS,
          say: Callable[[str], None] | None = None) -> dict[tuple[str, str], dict[str, Any]]:
    """Every job's places, {(key, the definition): ...}; the largest definitions first so that the workers end together."""
    global _LESSONS, _LIMIT
    _LESSONS, _LIMIT = lessons, limit
    ordered = sorted(jobs, key=lambda job: -len(job[1]))
    out: dict[tuple[str, str], dict[str, Any]] = {}
    if workers <= 1:
        results: Any = map(_one, ordered)
        pool = None
    else:
        pool = multiprocessing.get_context("fork").Pool(workers)
        results = pool.imap_unordered(_one, ordered)
    try:
        for number, (key, before, found) in enumerate(results, 1):
            out[(key, before)] = found
            if say:
                say(f"{number} of {len(ordered)}: {key}, {found['candidates']} candidates, {found['seconds']} s")
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    return out


# --------------------------------------------------------------------------- #
# the counts
# --------------------------------------------------------------------------- #
def best(rows: Sequence[Mapping[str, int | None]], which: str) -> int | None:
    found = [row[which] for row in rows if row[which] is not None]
    return min(found) if found else None


def within(values: Sequence[int | None], ranks: Sequence[int] = RANKS) -> dict[str, int]:
    return {**{str(rank): sum(1 for value in values if value is not None and value <= rank) for rank in ranks},
            "at any place": sum(1 for value in values if value is not None), "in no place": sum(1 for value in values if value is None)}


def _median(values: Sequence[float]) -> float | None:
    return statistics.median(values) if values else None


def summarise(per_task: Mapping[str, Mapping[str, Any]], budget: int = BUDGET) -> dict[str, Any]:
    """Tasks by the best place any of their small passing patches has, in each list; the same by the
    kind of patch; how long the lists are; where the material is."""
    tasks = list(per_task)
    out: dict[str, Any] = {"tasks": len(tasks), "small_passing_patches": sum(len(per_task[task]["patches"]) for task in tasks),
                           "tasks_by_best_place": {which: within([best(per_task[task]["places"], which) for task in tasks]) for which in LISTS}}
    by_shape: dict[str, Any] = {}
    for shape in (fix_shape.TAKEN_OUT, fix_shape.PUT_IN, fix_shape.LEAF):
        rows = {task: [place for patch, place in zip(per_task[task]["patches"], per_task[task]["places"]) if patch["shape"] == shape] for task in tasks}
        having = [task for task in tasks if rows[task]]
        by_shape[shape] = {"tasks_with_such_a_passing_patch": len(having),
                           **{f"within_{budget}_{which}": sum(1 for task in having if (best(rows[task], which) or budget + 1) <= budget) for which in LISTS},
                           "in_either_list_at_any_place": sum(1 for task in having if best(rows[task], IN_TURNS) is not None)}
    out["by_shape_of_the_passing_patch"] = by_shape
    found = [best(per_task[task]["places"], IN_TURNS) for task in tasks]
    out["median_place_in_turns_where_there_is_one"] = _median([value for value in found if value is not None])
    out["median_learner_candidates_for_the_definition"] = _median([row["candidates"] for task in tasks for row in per_task[task]["definitions"] if row["candidates"] is not None])
    out["median_pieces_taken_out_of_the_definition"] = _median([row["pieces"] for task in tasks for row in per_task[task]["definitions"] if row["pieces"] is not None])
    out["median_nodes_of_the_definition"] = _median([row["nodes"] for task in tasks for row in per_task[task]["definitions"]])
    out["definitions"] = sum(len(per_task[task]["definitions"]) for task in tasks)
    out["definitions_the_learner_did_not_finish"] = sum(1 for task in tasks for row in per_task[task]["definitions"] if row.get("too_long"))
    out["patches_whose_scope_is_the_whole_file"] = sum(1 for task in tasks for patch in per_task[task]["patches"] if patch["scope"] == WHOLE_FILE)
    out["tasks_with_a_small_passing_patch_from_its_definition_alone"] = sum(1 for task in tasks if any(patch["from_its_definition_alone"] for patch in per_task[task]["patches"]))
    out["tasks_within_budget_whose_patch_there_is_from_its_definition_alone"] = sum(
        1 for task in tasks if any(patch["from_its_definition_alone"] and (place[IN_TURNS] or budget + 1) <= budget
                                   for patch, place in zip(per_task[task]["patches"], per_task[task]["places"])))
    functions = [per_task[task]["functions_in_the_file"] for task in tasks if per_task[task].get("functions_in_the_file")]
    out["median_functions_in_the_changed_file"] = _median(functions)
    return out


def rule(summary: Mapping[str, Any], budget: int = BUDGET) -> dict[str, Any]:
    came = summary["tasks_by_best_place"][IN_TURNS][str(budget)]
    verdict = "worth building" if came >= 40 else "not reached: no run" if came < 20 else "undecided: no run on this count alone"
    return {"tasks_within_the_first_200_in_turns": came, "of": summary["tasks"], "verdict": verdict}


def code_sha256() -> dict[str, str]:
    names = ("canonical/tools/small_passing_patch_place_measure_v1.py", "canonical/tools/passing_patch_shape_measure_v1.py",
             "canonical/runtime/edit_kind_learning_v1.py", "canonical/runtime/take_out_v1.py", "canonical/runtime/edit_kind_choice_v1.py",
             "canonical/runtime/fix_shape_v1.py", "canonical/tools/edit_kind_choice_measure_v1.py", "canonical/tools/expert_fix_repetition_measure_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def put_together(found_targets: Mapping[str, Sequence[Mapping[str, Any]]], answers: Mapping[tuple[str, str], Mapping[str, Any]],
                 functions: Mapping[str, int | None]) -> dict[str, dict[str, Any]]:
    """Per task: its patches, the place of each, and its definitions with how long their lists are."""
    per_task: dict[str, dict[str, Any]] = {}
    for task, patches in found_targets.items():
        rows, definitions, seen = [], [], []
        for patch in patches:
            answer = answers[(task, patch["before"])]
            wanted = [other["wanted"] for other in patches if other["before"] == patch["before"]]
            rows.append(answer["places"][wanted.index(patch["wanted"])])
            if patch["before"] not in seen:
                seen.append(patch["before"])
                definitions.append({"nodes": nodes_of(patch["before"]), "lines": patch["before"].count("\n") + 1, "candidates": answer["candidates"],
                                    "pieces": answer["pieces"], "seconds": answer["seconds"], **({"too_long": True} if answer.get("too_long") else {})})
        per_task[task] = {"patches": [{key: value for key, value in patch.items() if key not in ("before", "wanted")} for patch in patches],
                          "places": rows, "definitions": definitions, "functions_in_the_file": functions.get(task)}
    return per_task


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cache-dir", required=True, type=pathlib.Path, help="the verdicts and patches, as passing_patch_shape_measure_v1.py --fetch kept them")
    parser.add_argument("--pull-requests-dir", required=True, type=pathlib.Path)
    parser.add_argument("--humanevalfix", required=True, type=pathlib.Path)
    parser.add_argument("--condefects", type=pathlib.Path)
    parser.add_argument("--condefects-lessons", type=int, default=CONDEFECTS_LESSONS)
    parser.add_argument("--passing-record", type=pathlib.Path, default=PASSING_RECORD)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--limit-seconds", type=int, default=LIMIT_SECONDS)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)

    started = time.time()
    say = lambda line: print(line, round(time.time() - started, 1), "s", flush=True)  # noqa: E731
    tasks = sorted(task for task, row in json.loads(args.passing_record.read_text())["per_task"].items() if row[2])
    records = {task: json.loads((args.pull_requests_dir / f"{task}.json").read_text()) for task in tasks}
    then = passing.verdicts(args.cache_dir, passing.WITH_PATCHES)
    with_patches = {name: found for name, found in then.items() if (args.cache_dir / passing.WITH_PATCHES[:10] / name / "all_preds.jsonl").exists()}
    found_targets = targets(records, tasks, with_patches, lambda name: passing.patches(args.cache_dir, name))
    say(f"{len(tasks)} tasks, {sum(1 for task in tasks if found_targets[task])} with a small passing patch, {sum(len(rows) for rows in found_targets.values())} different ones")
    lessons, shown = lessons_of(args.humanevalfix, args.condefects, args.condefects_lessons)
    say(f"lessons {shown}")

    jobs: list[tuple[str, str, list[str], list[str]]] = []
    for task in tasks:
        for before in dict.fromkeys(patch["before"] for patch in found_targets[task]):
            jobs.append((task, before, [patch["wanted"] for patch in found_targets[task] if patch["before"] == before], []))
    development, _ = hef.split(hef.load_bugs(args.humanevalfix))
    bugs = {bug["name"]: bug for bug in hef.load_bugs(args.humanevalfix)}
    control_jobs = [("control " + name, bugs[name]["buggy"], [normal(bugs[name]["fixed"])], [name]) for name in development]
    answers = asked(lessons, jobs + control_jobs, args.workers, args.limit_seconds, say)

    functions = {}
    for task in tasks:
        rows = [row for row in records[task].get("files", []) if not row.get("is_test") and row.get("is_python") and row.get("before") is not None]
        functions[task] = functions_in(rows[0]["before"]) if len(rows) == 1 else None
    per_task = put_together({task: rows for task, rows in found_targets.items() if rows}, answers, functions)
    summary = summarise(per_task)
    control = [answers[(key, before)]["places"][0] for key, before, _, _ in control_jobs]
    record = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expected_before": EXPECTED, "lessons": shown, "tasks_asked": len(tasks), "tasks_with_a_small_passing_patch": len(per_task),
        "summary": summary, "rule": rule(summary),
        "control_humanevalfix_development": {"bugs": len(control), **{which: within([row[which] for row in control]) for which in LISTS}},
        "per_task": per_task, "experiments_commit": passing.WITH_PATCHES, "submissions_with_patches": len(with_patches),
        "model_calls": 0, "programs_run": 0, "tests_run": 0, "code_sha256": code_sha256(), "seconds": round(time.time() - started, 1),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("WROTE", args.out, record["seconds"], "s", flush=True)
    print(json.dumps({"rule": record["rule"], "tasks_by_best_place": summary["tasks_by_best_place"], "control": record["control_humanevalfix_development"]}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
