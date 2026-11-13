#!/usr/bin/env python3
"""The candidates the tasks' own tests accept, under the project's WHOLE test suite.

Why this exists
---------------
SWE-bench runs only the test modules a task's test patch touches, and so does
canonical/tools/candidate_under_the_tasks_tests_measure_v1.py. A candidate those modules accept can
still break a test somewhere else in the project; others counted that 7.8% of test-passing patches
do. The count's record names ten candidates that resolve seven tasks. Two of them, read as diffs,
looked as if they break something the task's modules do not test. Reading is not running: this
runs them.

For a candidate the count called resolving, on the task's tree with the task's tests written in:

  1. the candidate is written in alone and Django's whole suite is run;
  2. the test modules holding a test that did not pass in that run are run a second time, twice:
     with the candidate, and with the expert's fix. A test is BROKEN BY THE CANDIDATE only when,
     in that second run, it passes with the expert's fix and does not pass with the candidate. A
     test that fails here with the expert's fix as well says something about this machine, not
     about the candidate, and a test that failed once and passes the second time is left alone.

A candidate KEEPS THE WHOLE SUITE when its whole run got to its summary and no test is broken by
it. Where the whole run did not get to its summary, or too many modules would have to be run again,
nothing is said of the candidate, for or against.

The project's whole suite is not hidden from a solver: it stands in the tree. What this finds
could therefore have been found before a candidate was handed in.

What is expected, and what follows from each outcome, is written below (`EXPECTED`, `rule`) and was
pushed before any whole run was made.

The runs are made on ONE process each. The first whole run, of django__django-11066, was made on two
and ended before its summary after 320 seconds: Django's parallel runner cannot hand an error to
its parent when the error cannot be pickled, and on Python 3.11 one test's error cannot. On one
process the same error is one test's error and the run goes on. That change, and running two
candidates side by side, were made after that first run and before any other; `EXPECTED` and `rule`
are as they were pushed.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import tests_as_the_judge_v1 as judge  # noqa: E402
from canonical.tools import candidate_under_the_tasks_tests_measure_v1 as count  # noqa: E402
from canonical.tools import file_found_from_task_text_measure_v1 as measure  # noqa: E402
from canonical.tools import fix_content_in_task_text_measure_v1 as content  # noqa: E402
from canonical.tools import function_found_from_task_text_measure_v1 as function_measure  # noqa: E402
from canonical.tools import small_passing_patch_place_measure_v1 as place  # noqa: E402

SCHEMA = "BRAIN_RESOLVING_CANDIDATE_UNDER_THE_WHOLE_SUITE_V1"
COUNT_RECORD = ROOT / "canonical" / "verification" / "CANDIDATE_UNDER_THE_TASKS_TESTS_SWEBENCH_VERIFIED_DJANGO_20261113_V1.json"
WHOLE_SECONDS = 3600.0          # one whole run of the suite
AGAIN_SECONDS = 1800.0          # one second run of the modules that held a test that did not pass
MOST_MODULES_AGAIN = 150        # more modules than this are not run again: nothing is then said of the candidate

# Written before any whole run was made. Both ends are counted in. The five are the candidates at
# place 1 that the tasks' own tests accept (one submission each). Read as diffs before this was
# written: the one of django__django-12155 takes `min()` of the lines after the first, which is
# nothing for a docstring of one line; the one of django__django-15814 replaces
# `model = model._meta.concrete_model` instead of the line the expert changed. The other three are
# the expert's own change or the issue's second wording of it.
EXPECTED = {
    "one_submission__whole_runs_that_got_to_their_summary": (4, 5),
    "one_submission__breaking_a_test_elsewhere": (1, 3),
    "one_submission__keeping_the_whole_suite": (2, 4),
}

_NAME = re.compile(r"^(\S+) \(((?:[^\s().]+\.)+)([^\s().]+)\)$")
_DID_NOT_LOAD = re.compile(r"^ImportError: Failed to import test module: (\S+)\s*$", re.MULTILINE)

Runner = Callable[[pathlib.Path, Sequence[str], float], Mapping[str, Any]]


# --------------------------------------------------------------------------- #
# reading two runs against each other
# --------------------------------------------------------------------------- #
def not_passing(found: Mapping[str, str]) -> list[str]:
    """The tests, by name, that failed or ended in an error."""
    return sorted(name for name, how in found.items() if how in (judge.FAILED, judge.ERROR) and _NAME.match(name))


def modules_again(found: Mapping[str, str], printed: str) -> list[str]:
    """The test modules to run a second time: those of the tests that did not pass, and those that did not load."""
    out: dict[str, None] = {}
    for name in not_passing(found):
        dotted = _NAME.match(name).group(2).rstrip(".")
        if not dotted.startswith("unittest."):          # a module that did not load is printed as a test of unittest's own
            out[dotted] = None
    for module in _DID_NOT_LOAD.findall(printed):
        out[module] = None
    return sorted(out)


def broken(with_the_fix: Mapping[str, str], with_the_candidate: Mapping[str, str]) -> list[str]:
    """The tests, by name, that pass with the expert's fix and do not pass with the candidate: failed, ended in an error, or did not run."""
    return sorted(name for name, how in with_the_fix.items()
                  if how == judge.PASSED and _NAME.match(name) and with_the_candidate.get(name) != judge.PASSED)


# --------------------------------------------------------------------------- #
# the runs
# --------------------------------------------------------------------------- #
def run_whole(tree: pathlib.Path, labels: Sequence[str], seconds: float, processes: int = 1) -> dict[str, Any]:
    """Django's own runner on the whole suite (no labels) or on the labels, on one process; what it printed, and whether it was stopped."""
    environment = {**os.environ, "PYTHONPATH": str(tree), "PYTHONDONTWRITEBYTECODE": "1", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"}
    started = time.time()
    process = subprocess.Popen([sys.executable, "tests/runtests.py", "--verbosity", "2", "--settings=test_sqlite", "--parallel", str(processes), *labels],
                               cwd=str(tree), env=environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                               start_new_session=True)
    stopped = False
    try:
        printed, _ = process.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        stopped = True
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        printed, _ = process.communicate()
    return {"output": printed.decode("utf-8", errors="replace"), "seconds": round(time.time() - started, 1), "stopped": stopped, "exit": process.returncode}


def _said(got: Mapping[str, Any], found: Mapping[str, str]) -> dict[str, Any]:
    return {"ran": judge.ran(got["output"]), "finished": judge.finished(got["output"]), "stopped": bool(got["stopped"]), "seconds": got["seconds"],
            "passing": sum(1 for name, how in found.items() if how == judge.PASSED and _NAME.match(name)), "not_passing": len(not_passing(found))}


def of_candidate(tree: pathlib.Path, test_patch: str, fix: str, path: str, text: str, first: Sequence[str],
                 run: Runner = run_whole, keep_output: pathlib.Path | None = None) -> dict[str, Any]:
    """One candidate under the whole suite, and the second run that says which tests it broke."""
    if not count.as_the_task_starts(tree, test_patch):
        raise RuntimeError("the test patch did not go in")
    (tree / path).write_bytes(text.encode("utf-8"))
    got = run(tree, [], WHOLE_SECONDS)
    if keep_output is not None:
        keep_output.write_text(got["output"], encoding="utf-8")
    found = judge.statuses(got["output"])
    row: dict[str, Any] = {"whole_run": {**_said(got, found), "start_passing": len(judge.passing(found, first)), "start_passing_wanted": len(first)},
                           "modules_again": None, "run_again": None, "broken_by_the_candidate": None, "keeps_the_whole_suite": None, "why_nothing_is_said": None}
    if not row["whole_run"]["finished"]:
        row["why_nothing_is_said"] = "the whole run was stopped for time" if got["stopped"] else "the whole run ended before its summary"
        return row
    modules = modules_again(found, got["output"])
    row["modules_again"] = modules
    if len(modules) > MOST_MODULES_AGAIN:
        row["why_nothing_is_said"] = f"{len(modules)} modules hold a test that did not pass: too many to run again"
        return row
    if not modules:
        row.update(broken_by_the_candidate=[], keeps_the_whole_suite=True)
        return row
    second = run(tree, modules, AGAIN_SECONDS)
    with_the_candidate = judge.statuses(second["output"])
    if not count.as_the_task_starts(tree, test_patch) or not count.applied(tree, fix):
        raise RuntimeError("the expert's fix did not go in")
    third = run(tree, modules, AGAIN_SECONDS)
    with_the_fix = judge.statuses(third["output"])
    row["run_again"] = {"with_the_candidate": _said(second, with_the_candidate), "with_the_fix": _said(third, with_the_fix)}
    if not (row["run_again"]["with_the_candidate"]["finished"] and row["run_again"]["with_the_fix"]["finished"]):
        row["why_nothing_is_said"] = "a second run did not get to its summary"
        return row
    names = broken(with_the_fix, with_the_candidate)
    row.update(broken_by_the_candidate=names, keeps_the_whole_suite=not names)
    return row


# --------------------------------------------------------------------------- #
# all of them
# --------------------------------------------------------------------------- #
def resolving(per_task: Mapping[str, Mapping[str, Any]], which: str = "first") -> list[tuple[str, int]]:
    """(task, place) of the candidates the count called resolving.

    "one": those at place 1, one submission each. "first": the first of each task, those at place 1 before the rest. "all": the later ones after them."""
    firsts, later = [], []
    for task, row in per_task.items():
        places = [candidate["place"] for candidate in row.get("candidates") or () if candidate.get("resolves")]
        if places:
            firsts.append((task, places[0]))
            later += [(task, at) for at in places[1:]]
    firsts.sort(key=lambda pair: (pair[1] != 1, int(pair[0].rsplit("-", 1)[1])))
    later.sort(key=lambda pair: (int(pair[0].rsplit("-", 1)[1]), pair[1]))
    if which == "one":
        return [pair for pair in firsts if pair[1] == 1]
    return firsts + (later if which == "all" else [])


def summarise(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    def of(some: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        said = [row for row in some if row["keeps_the_whole_suite"] is not None]
        breaking = [row for row in said if not row["keeps_the_whole_suite"]]
        return {"candidates_run": len(some),
                "whole_runs_that_got_to_their_summary": sum(1 for row in some if row["whole_run"]["finished"]),
                "nothing_said": {f"{row['task']} place {row['place']}": row["why_nothing_is_said"] for row in some if row["keeps_the_whole_suite"] is None},
                "keeping_the_whole_suite": len(said) - len(breaking),
                "keeping_the_whole_suite__tasks": sorted(row["task"] for row in said if row["keeps_the_whole_suite"]),
                "breaking_a_test_elsewhere": len(breaking),
                "breaking_a_test_elsewhere__tests_broken": {f"{row['task']} place {row['place']}": len(row["broken_by_the_candidate"]) for row in breaking}}
    one = [row for row in rows if row["place"] == 1 and row["first_resolving"]]
    first = [row for row in rows if row["first_resolving"]]
    summary: dict[str, Any] = {"candidates_run": len(rows), "seconds_of_test_runs": round(sum(row["seconds"] for row in rows), 1)}
    for name, some in (("one_submission", one), ("first_resolving", first), ("every_resolving_candidate_run", list(rows))):
        for key, value in of(some).items():
            summary[f"{name}__{key}"] = value
    tasks: dict[str, bool] = {}
    for row in rows:
        if row["keeps_the_whole_suite"] is not None:
            tasks[row["task"]] = tasks.get(row["task"], False) or row["keeps_the_whole_suite"]
    summary["tasks_with_a_candidate_run_that_keeps_the_whole_suite"] = sorted(task for task, kept in tasks.items() if kept)
    return summary


def held(summary: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Each expectation with what was found; both ends of a range are counted in."""
    out = {}
    for name, (low, high) in EXPECTED.items():
        found = summary.get(name)
        out[name] = {"expected": [low, high], "found": found, "held": found is not None and low <= found <= high}
    return out


def rule(summary: Mapping[str, Any]) -> dict[str, Any]:
    """What follows; written before any whole run was made."""
    run, breaking, keeping = (summary["one_submission__candidates_run"], summary["one_submission__breaking_a_test_elsewhere"],
                              summary["one_submission__keeping_the_whole_suite"])
    verdict = []
    if run - breaking - keeping:
        verdict.append(f"of {run - breaking - keeping} of the {run} first candidates nothing can be said on this machine; they are counted neither way")
    if breaking:
        verdict.append(f"{breaking} of the {run} first candidates the tasks' own tests accept break a test elsewhere in the project: by the benchmark's count they "
                       f"resolve their task, by the project's own suite they do not; one submission that also keeps the whole suite: {keeping}")
        after = ("the project's whole suite stands in the tree and is not hidden: a candidate that breaks it can be turned down BEFORE it is handed in; "
                 "count next what running the project's suite on each candidate, in order, does to one submission")
    else:
        verdict.append(f"none of the {run} first candidates the tasks' own tests accept breaks a test elsewhere in the project, as far as this machine says: "
                       f"the benchmark's count and the project's own suite agree on {keeping}")
        after = "the count under the tasks' own tests stands as it is; next is WRITING the change"
    return {"verdict": verdict, "next": after}


def code_sha256() -> dict[str, str]:
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (pathlib.Path(__file__).resolve(), pathlib.Path(count.__file__).resolve(), pathlib.Path(judge.__file__).resolve())}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dataset-dir", required=True, type=pathlib.Path, help="holds problems/swe/swebench-verified/<task>.yaml and patches/<task>_tests.patch")
    parser.add_argument("--pull-requests-dir", required=True, type=pathlib.Path)
    parser.add_argument("--trees-dir", required=True, type=pathlib.Path)
    parser.add_argument("--work-dir", required=True, type=pathlib.Path)
    parser.add_argument("--count-record", type=pathlib.Path, default=COUNT_RECORD)
    parser.add_argument("--which", choices=("one", "first", "all"), default="one",
                        help="the resolving candidates at place 1, the first resolving candidate of each task, or every resolving candidate")
    parser.add_argument("--workers", type=int, default=2, help="candidates run side by side, each on its own tree")
    parser.add_argument("--out", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)

    def say(text: str) -> None:
        print(time.strftime("%H:%M:%S", time.gmtime()), text, flush=True)

    started = time.time()
    counted = json.loads(args.count_record.read_text(encoding="utf-8"))
    wanted = resolving(counted["per_task"], args.which)
    firsts = set(resolving(counted["per_task"], "first"))
    tasks = sorted({task for task, _ in wanted}, key=lambda task: int(task.rsplit("-", 1)[1]))
    statements = args.dataset_dir / "problems" / "swe" / "swebench-verified"
    everything = sorted(json.loads(place.PASSING_RECORD.read_text())["per_task"])
    issues = content.statements(statements, everything)
    other = function_measure.other_text_of(sorted(issues))
    commits = measure.base_commits(statements, tasks)
    clone = args.trees_dir / f"{count.PROJECT}.git"
    args.work_dir.mkdir(parents=True, exist_ok=True)
    made = count.candidates_of(clone, measure.repository_of(tasks[0]), [(task, commits[task], issues[task], issues[other[task]]) for task in tasks])
    rows_file = args.work_dir / "rows.jsonl"
    rows: dict[tuple[str, int], dict[str, Any]] = {}
    if rows_file.exists():
        for line in rows_file.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            rows[(row["task"], row["place"])] = row
        say(f"{len(rows)} candidates already run, read from {rows_file}")
    todo = []
    for task, at in wanted:
        if (task, at) in rows:
            continue
        written = counted["per_task"][task]["candidates"][at - 1]
        candidate = made[task]["candidates"][at - 1]
        if written["place"] != at or hashlib.sha256(candidate["text"].encode("utf-8")).hexdigest()[:16] != written["sha256"]:
            say(f"REFUSED: the candidate of {task} at place {at} is not the one the count ran")
            return 2
        tree = args.work_dir / f"{task}__place_{at}"
        count.at_commit(clone, tree, commits[task])                       # one after the other: the trees share one clone
        todo.append((task, at, written, candidate, tree))

    def one(given: tuple) -> dict[str, Any]:
        task, at, written, candidate, tree = given
        test_patch = (args.dataset_dir / "patches" / f"{task}_tests.patch").read_text(encoding="utf-8")
        fix = count.expert_diff(json.loads((args.pull_requests_dir / f"{task}.json").read_text()), test_patch)
        begun = time.time()
        row = {"task": task, "place": at, "first_resolving": (task, at) in firsts, "version": counted["per_task"][task].get("version"),
               "path": candidate["path"], "function": candidate["function"], "sha256": written["sha256"],
               **of_candidate(tree, test_patch, fix, candidate["path"], candidate["text"], count.tests_of(statements / f"{task}.yaml")["fail_to_pass"],
                              keep_output=args.work_dir / f"{task}__place_{at}__whole_run.txt")}
        row["seconds"] = round(time.time() - begun, 1)
        return row

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for row in pool.map(one, todo):
            rows[(row["task"], row["place"])] = row
            with rows_file.open("a", encoding="utf-8") as out:
                out.write(json.dumps(row) + "\n")
            say(f"{len(rows)}/{len(wanted)} {row['task']} place {row['place']}: whole run ran={row['whole_run']['ran']} not passing={row['whole_run']['not_passing']} "
                f"modules again={len(row['modules_again'] or ())} broken by the candidate={row['broken_by_the_candidate']} keeps={row['keeps_the_whole_suite']} "
                f"{row['why_nothing_is_said'] or ''} {row['seconds']}s")
    ordered = [rows[pair] for pair in wanted]
    summary = summarise(ordered)
    record = {
        "schema": SCHEMA,
        "made_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "which": args.which,
        "processes_of_one_run": 1,
        "candidates_side_by_side": max(1, args.workers),
        "expected": {name: list(pair) for name, pair in EXPECTED.items()},
        "expectations": held(summary),
        "summary": summary,
        "rule": rule(summary),
        "seconds": round(time.time() - started, 1),
        "code_sha256": code_sha256(),
        "count_made_at": counted.get("generated_utc") or counted.get("made_at"),
        "candidates": ordered,
    }
    say(json.dumps({"summary": summary, "expectations": record["expectations"], "rule": record["rule"]}, indent=1))
    if args.out is not None:
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        say(f"written {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
