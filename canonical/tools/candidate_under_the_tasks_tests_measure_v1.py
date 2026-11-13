#!/usr/bin/env python3
"""The candidates made from a task's text, run under the task's own tests.

Why this exists
---------------
Three records of this line of work say a task is "reached" when the text of a candidate is the text
of a patch that passed in somebody's recorded run. Nothing was run here, and the last record's rule
says what comes next: "run the tasks' own tests on what it reaches". This does that for the Django
tasks of SWE-bench Verified (231 of the 500), which need nothing compiled.

For every task, on this machine, with no model call:

  1. the tree at the task's commit, with the task's tests written in (the dataset's test patch);
  2. the tests are run as they stand: the tests that should start passing must not all pass;
  3. the expert's fix is written in and the tests are run again: every test that should start
     passing must pass. Where 2 and 3 do not both hold THIS MACHINE CANNOT JUDGE THE TASK and no
     candidate of it is counted, for or against;
  4. each candidate the chain makes from the tree and the task's text (the first file, its first
     four functions, five of each: at most twenty, in order) is written in alone and run. It
     resolves the task when every test that should start passing passes and so does every test
     that should keep passing and passes with the expert's fix here;
  5. for a task that has a candidate of its own, the first candidate made from ANOTHER task's
     text is run the same way: what passes with nothing of this task in it.

A candidate is first run on just the tests that should start passing (shown, with the expert's fix,
to pass when run alone) and on the whole test modules only when all of those pass: a candidate that
fails one of them cannot resolve the task, so nothing is lost but time.

Two counts are kept apart, because they are different things. ONE SUBMISSION is the first candidate:
what the chain would hand in, having seen no test. WITHIN TWENTY is the first candidate in order that
resolves the task: it needs somebody to say which one that is, and here the task's hidden tests say
it, which a submission may not use.

What is expected, and what follows from each outcome, is written below (`EXPECTED`, `rule`) and was
pushed before any candidate was run.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import queue
import re
import signal
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import file_the_task_text_points_at_v1 as finder  # noqa: E402
from canonical.runtime import function_the_task_text_points_at_v1 as pointer  # noqa: E402
from canonical.runtime import tests_as_the_judge_v1 as judge  # noqa: E402
from canonical.tools import file_found_from_task_text_measure_v1 as measure  # noqa: E402
from canonical.tools import fix_content_in_task_text_measure_v1 as content  # noqa: E402
from canonical.tools import function_found_from_task_text_measure_v1 as function_measure  # noqa: E402
from canonical.tools import small_passing_patch_place_measure_v1 as place  # noqa: E402

SCHEMA = "BRAIN_CANDIDATE_UNDER_THE_TASKS_TESTS_V1"
PROJECT = "django__django"
FILE_RECORD = ROOT / "canonical" / "verification" / "FILE_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json"
WHOLE_SECONDS = 900              # one run of the test modules the task's test patch touches
FEW_SECONDS = 300                # one run of just the tests that should start passing
RANKS = (1, 5, 10, 20)
FETCH_AT_ONCE = 4000

# Written and pushed before any candidate was run. A range is [least, most], both counted in.
EXPECTED: dict[str, Any] = {
    # the fix passes and the unfixed program fails, here: Python 3.11 for every Django from 1.11 to 5.0, no image of the task
    "judged__share_of_the_django_tasks": [0.70, 0.98],
    # the seven Django tasks the last record says the chain reaches (places 1, 6, 1, 1, 2, 4, 1)
    "recorded_places__tasks_judged_of_the_seven": [6, 7],
    "recorded_places__judged_and_not_resolving_at_the_recorded_place": [0, 0],
    # the first candidate alone; four of them are recorded as the text of a passing patch
    "one_submission__tasks_resolved": [4, 10],
    # the first resolving candidate among at most twenty
    "within_twenty__tasks_resolved": [7, 20],
    "within_twenty__resolved_and_not_in_the_earlier_record": [0, 10],
    # the first candidate made from another task's text
    "another_tasks_text__tasks_resolved": [0, 0],
}


# --------------------------------------------------------------------------- #
# the task as it is published
# --------------------------------------------------------------------------- #
_TOUCHED = re.compile(r"^diff --git a/(\S+) b/(\S+)$", re.MULTILINE)


def touched(diff: str) -> list[str]:
    """The paths a diff touches, in its order."""
    out: list[str] = []
    for _, path in _TOUCHED.findall(diff):
        if path not in out:
            out.append(path)
    return out


def labels_of(test_patch: str) -> list[str]:
    """What Django's test runner is handed: the test modules the task's test patch touches, dotted, as SWE-bench's harness does."""
    out: list[str] = []
    for path in touched(test_patch):
        if path.startswith("tests/") and path.endswith(".py"):
            label = path[len("tests/"):-len(".py")].replace("/", ".")
            if label not in out:
                out.append(label)
    return out


_IN_CLASS = re.compile(r"\(((?:[^\s().]+\.)+[^\s().]+)\)$")


def modules_named(names: Sequence[str]) -> list[str]:
    """The test modules the tests' own names give: `test_x (pkg.mod.Class)` is of `pkg.mod`. For a task whose test patch touches no test module."""
    out: list[str] = []
    for name in names:
        found = _IN_CLASS.search(judge.normal(name))
        if found and "." in found.group(1):
            module = found.group(1).rsplit(".", 1)[0]
            if module not in out:
                out.append(module)
    return out


def tests_of(statement_file: pathlib.Path) -> dict[str, Any]:
    """The task's lists of tests and its Django version, from the file the dataset is kept in."""
    import yaml                                                   # only here: nothing else of this tool needs it
    held = yaml.safe_load(statement_file.read_text(encoding="utf-8"))
    return {"fail_to_pass": [str(name) for name in held.get("fail_to_pass") or []],
            "pass_to_pass": [str(name) for name in held.get("pass_to_pass") or []],
            "version": str(held.get("version")), "base_commit": str(held.get("base_commit"))}


def expert_diff(record: Mapping[str, Any], test_patch: str) -> str:
    """The expert's fix as one diff: every file of the merged pull request that the task's test patch does not touch."""
    tests = set(touched(test_patch))
    out = []
    for file in record.get("files") or ():
        path = file.get("path")
        if not path or path in tests or not file.get("patch"):
            continue
        status, old = file.get("status"), file.get("previous") or path
        head = [f"diff --git a/{old} b/{path}"]
        if status == "added":
            head += ["new file mode 100644", "--- /dev/null", f"+++ b/{path}"]
        elif status == "removed":
            head += ["deleted file mode 100644", f"--- a/{path}", "+++ /dev/null"]
        else:
            if old != path:
                head += [f"rename from {old}", f"rename to {path}"]
            head += [f"--- a/{old}", f"+++ b/{path}"]
        out.append("\n".join(head) + "\n" + file["patch"].rstrip("\n") + "\n")
    return "".join(out)


def few_of(output_with_the_fix: str, names: Sequence[str]) -> list[str] | None:
    """The labels that run just these tests, read from a run that printed them; nothing when one of them cannot be named."""
    known = judge.identifiers(output_with_the_fix)
    out: list[str] = []
    for name in names:
        labels = known.get(judge.normal(name)) or known.get(name)
        if not labels:
            return None
        for label in labels:
            if label not in out:
                out.append(label)
    return out or None


# --------------------------------------------------------------------------- #
# the tree and the runs
# --------------------------------------------------------------------------- #
def _git(directory: pathlib.Path, *args: str, text_in: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    done = subprocess.run(["git", "-C", str(directory), *args], input=text_in, capture_output=True, text=True)
    if check and done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:3])}: {done.stderr.strip()[:300]}")
    return done


def fetch_everything(clone: pathlib.Path, commits: Sequence[str]) -> dict[str, Any]:
    """Every file of every listed commit's tree into a clone made without file contents, asked for together."""
    started = time.time()
    wanted: dict[str, None] = {}
    for commit in commits:
        for entry in _git(clone, "ls-tree", "-r", "-z", commit).stdout.split("\0"):
            if entry:
                mode, kind, name = entry.split("\t", 1)[0].split(" ")
                if kind == "blob":
                    wanted[name] = None
    have = set(_git(clone, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)").stdout.split())
    names = [name for name in wanted if name not in have]
    for at in range(0, len(names), FETCH_AT_ONCE):
        _git(clone, "-c", "fetch.negotiationAlgorithm=noop", "fetch", "origin", "--no-tags", "--no-write-fetch-head", "--recurse-submodules=no",
             "--filter=blob:none", "--stdin", text_in="\n".join(names[at:at + FETCH_AT_ONCE]) + "\n")
    have = set(_git(clone, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)").stdout.split())
    return {"commits": len(commits), "files": len(wanted), "fetched": len(names), "still_missing": sum(1 for name in wanted if name not in have),
            "seconds": round(time.time() - started, 1)}


def at_commit(clone: pathlib.Path, tree: pathlib.Path, commit: str) -> None:
    """The tree of the commit, and nothing else, in `tree`."""
    if not (tree / ".git").exists():
        _git(clone, "worktree", "prune")
        _git(clone, "worktree", "add", "-f", "--detach", str(tree), commit)
    else:
        _git(tree, "checkout", "-q", "-f", "--detach", commit)
    _git(tree, "clean", "-fdxq")


def applied(tree: pathlib.Path, diff: str) -> bool:
    """Whether the diff went in whole."""
    if not diff.strip():
        return False
    return _git(tree, "apply", "--whitespace=nowarn", "-", text_in=diff, check=False).returncode == 0


def as_the_task_starts(tree: pathlib.Path, test_patch: str) -> bool:
    """Back to the commit's tree with the task's tests written in."""
    _git(tree, "reset", "-q", "--hard")
    _git(tree, "clean", "-fdxq")
    return applied(tree, test_patch)


def run_tests(tree: pathlib.Path, labels: Sequence[str], seconds: float) -> dict[str, Any]:
    """One run of Django's own runner on the labels, as SWE-bench's harness calls it; what it printed, and whether it was stopped."""
    environment = {**os.environ, "PYTHONPATH": str(tree), "PYTHONDONTWRITEBYTECODE": "1", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8"}
    started = time.time()
    process = subprocess.Popen([sys.executable, "tests/runtests.py", "--verbosity", "2", "--settings=test_sqlite", "--parallel", "1", *labels],
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


def parses(text: str) -> bool:
    try:
        compile(text, "candidate", "exec", dont_inherit=True)
    except (SyntaxError, ValueError):
        return False
    return True


# --------------------------------------------------------------------------- #
# one task
# --------------------------------------------------------------------------- #
Runner = Callable[[pathlib.Path, Sequence[str], float], Mapping[str, Any]]


def _read(got: Mapping[str, Any], first: Sequence[str], keep: Sequence[str]) -> tuple[dict[str, str], dict[str, Any]]:
    found = judge.statuses(got["output"])
    return found, {"ran": judge.ran(got["output"]), "finished": judge.finished(got["output"]), "stopped": bool(got["stopped"]), "seconds": got["seconds"],
                   "start_passing": len(judge.passing(found, first)), "keep_passing": len(judge.passing(found, keep))}


def of_candidate(tree: pathlib.Path, test_patch: str, path: str, text: str, labels: Sequence[str], few: Sequence[str] | None,
                 fixed: Mapping[str, str], first: Sequence[str], keep: Sequence[str], run: Runner = run_tests) -> dict[str, Any]:
    """One candidate, written in alone on the task's tree with the task's tests, and what the tests say of it."""
    row: dict[str, Any] = {"resolves": False, "start_passing": None, "whole_run": False, "seconds": 0.0}
    if not parses(text):
        row["does_not_parse"] = True
        return row
    if not as_the_task_starts(tree, test_patch):
        raise RuntimeError("the test patch did not go in a second time")
    (tree / path).write_bytes(text.encode("utf-8"))
    if few:
        got = run(tree, few, FEW_SECONDS)
        found = judge.statuses(got["output"])
        row.update(start_passing=len(judge.passing(found, first)), seconds=got["seconds"], stopped=bool(got["stopped"]))
        if row["start_passing"] < len(first):
            return row
    got = run(tree, labels, WHOLE_SECONDS)
    found, read = _read(got, first, keep)
    kept = judge.passing(fixed, keep)
    row.update(whole_run=True, start_passing=read["start_passing"], keep_passing=len(judge.passing(found, kept)), keep_wanted=len(kept),
               stopped=read["stopped"], seconds=round(row["seconds"] + got["seconds"], 1), resolves=judge.resolves(found, fixed, first, keep))
    return row


def of_task(tree: pathlib.Path, clone: pathlib.Path, commit: str, test_patch: str, fix: str, tests: Mapping[str, Any],
            candidates: Sequence[Mapping[str, Any]], other: Mapping[str, Any] | None, run: Runner = run_tests) -> dict[str, Any]:
    """Whether this machine can judge the task, and what its tests say of each candidate."""
    started = time.time()
    first, keep = list(tests["fail_to_pass"]), list(tests["pass_to_pass"])
    labels = labels_of(test_patch) or modules_named(first + keep)
    row: dict[str, Any] = {"version": tests.get("version"), "labels": labels, "start_passing": len(first), "keep_passing": len(keep),
                           "judged": False, "why_not": None, "candidates_made": len(candidates), "candidates": [], "another_tasks_text": None}

    def ended(why: str | None) -> dict[str, Any]:
        row["why_not"] = why
        row["seconds"] = round(time.time() - started, 1)
        return row

    if not first:
        return ended("the task names no test that should start passing")
    if not labels:
        return ended("neither the test patch nor the tests' names give a test module")
    at_commit(clone, tree, commit)
    if not applied(tree, test_patch):
        return ended("the test patch did not go in")
    got = run(tree, labels, WHOLE_SECONDS)
    base, row["as_it_stands"] = _read(got, first, keep)
    if not applied(tree, fix):
        return ended("the expert's fix did not go in")
    got = run(tree, labels, WHOLE_SECONDS)
    fixed, row["with_the_fix"] = _read(got, first, keep)
    row["left_out"] = len(judge.left_out(fixed, keep))
    if not row["with_the_fix"]["finished"]:
        return ended("the tests do not run here: with the expert's fix the run " + ("was stopped for time" if got["stopped"] else "ended before its summary"))
    if row["with_the_fix"]["start_passing"] < len(first):
        return ended("with the expert's fix a test that should start passing does not pass here")
    if not judge.tells_apart(base, fixed, first):
        return ended("without the fix every test that should start passing passes here")
    row["judged"] = True
    if not candidates and other is None:
        return ended(None)
    few = few_of(got["output"], first)
    if few:
        alone = run(tree, few, FEW_SECONDS)
        stands = len(judge.passing(judge.statuses(alone["output"]), first)) == len(first)
        row["few"] = {"labels": len(few), "stands": stands, "seconds": alone["seconds"]}
        if not stands:
            few = None
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for at, candidate in enumerate(list(candidates) + ([other] if other is not None else []), 1):
        key = (candidate["path"], hashlib.sha256(candidate["text"].encode("utf-8")).hexdigest())
        if key not in seen:
            seen[key] = of_candidate(tree, test_patch, candidate["path"], candidate["text"], labels, few, fixed, first, keep, run)
        said = {"path": candidate["path"], "function": candidate["function"], "sha256": key[1][:16], **seen[key]}
        if other is not None and at == len(candidates) + 1:
            row["another_tasks_text"] = said
        else:
            row["candidates"].append({"place": at, **said})
    return ended(None)


# --------------------------------------------------------------------------- #
# the candidates of every task
# --------------------------------------------------------------------------- #
def candidates_of(clone: pathlib.Path, repository: str, tasks: Sequence[tuple[str, str, str, str]]) -> dict[str, dict[str, Any]]:
    """{task: its candidates in order, and the first one made from another task's text}; (task, commit, text, another task's text) in the project's order."""
    contents = measure.Contents(clone)
    kept: dict[tuple[str, str], Any] = {}
    out: dict[str, dict[str, Any]] = {}
    try:
        for task, commit, text, other_text in tasks:
            files = measure.listing(clone, repository, commit)
            here = {}
            for path, name in files:
                key = (name, path)
                if key not in kept:
                    kept[key] = finder.document(path, contents.read(name))
                here[key] = kept[key]
            kept = here
            names = dict(files)
            documents = {path: kept[(name, path)] for path, name in files}

            def source_of(path: str) -> str:
                return contents.read(names[path])

            def written(made: Sequence[tuple[str, pointer.Function, str]]) -> list[dict[str, Any]]:
                return [{"path": path, "function": function.name, "text": pointer.written_into(source_of(path), function, program)}
                        for path, function, program in made]

            mine = written(finder.candidates(documents, source_of, text, in_order=finder.order(documents, text)))
            others = written(finder.candidates(documents, source_of, other_text, in_order=finder.order(documents, other_text))[:1])
            out[task] = {"candidates": mine, "another_tasks_text": others[0] if others else None}
    finally:
        contents.close()
    return out


# --------------------------------------------------------------------------- #
# all of them
# --------------------------------------------------------------------------- #
def _share(count: int, of: int) -> float | None:
    return round(count / of, 4) if of else None


def first_resolving(row: Mapping[str, Any]) -> int | None:
    """The place, from 1, of the first candidate the task's tests accept."""
    return next((candidate["place"] for candidate in row.get("candidates") or () if candidate.get("resolves")), None)


def summarise(per_task: Mapping[str, Mapping[str, Any]], recorded: Mapping[str, int]) -> dict[str, Any]:
    """The counts. `recorded` is {task: the place the earlier record gives its first candidate that is the text of a passing patch}."""
    rows = dict(per_task)
    judged = {task: row for task, row in rows.items() if row.get("judged")}
    with_candidates = {task: row for task, row in rows.items() if row.get("candidates_made")}
    counted = {task: row for task, row in judged.items() if row.get("candidates_made")}
    places = {task: first_resolving(row) for task, row in counted.items()}
    why: dict[str, int] = {}
    for row in rows.values():
        if not row.get("judged"):
            why[str(row.get("why_not"))] = why.get(str(row.get("why_not")), 0) + 1
    run = [candidate for row in counted.values() for candidate in row["candidates"]]
    one = sorted(task for task, at in places.items() if at == 1)
    within = sorted(task for task, at in places.items() if at is not None)
    standing, failing, unjudged = [], [], []
    for task, at in sorted(recorded.items()):
        if task not in rows:
            continue
        if task not in judged:
            unjudged.append(task)
            continue
        there = next((candidate for candidate in rows[task]["candidates"] if candidate["place"] == at), None)
        (standing if there is not None and there.get("resolves") else failing).append(task)
    others = [row["another_tasks_text"] for row in judged.values() if row.get("another_tasks_text")]
    versions: dict[str, dict[str, int]] = {}
    for task, row in rows.items():
        mine = versions.setdefault(str(row.get("version")), {"tasks": 0, "judged": 0, "with_a_candidate_and_judged": 0, "one_submission": 0, "within_twenty": 0})
        mine["tasks"] += 1
        mine["judged"] += 1 if task in judged else 0
        mine["with_a_candidate_and_judged"] += 1 if task in counted else 0
        mine["one_submission"] += 1 if task in one else 0
        mine["within_twenty"] += 1 if task in within else 0
    return {
        "tasks": len(rows),
        "judged": len(judged),
        "judged__share_of_the_django_tasks": _share(len(judged), len(rows)),
        "not_judged__why": dict(sorted(why.items(), key=lambda item: -item[1])),
        "tests_left_out__that_fail_here_even_with_the_fix": sum(row.get("left_out") or 0 for row in judged.values()),
        "tests_that_should_keep_passing__in_the_judged_tasks": sum(row.get("keep_passing") or 0 for row in judged.values()),
        "tasks_with_a_test_left_out": sum(1 for row in judged.values() if row.get("left_out")),
        "with_a_candidate": len(with_candidates),
        "with_a_candidate_and_judged": len(counted),
        "candidates_run": len(run),
        "candidates_that_do_not_parse": sum(1 for candidate in run if candidate.get("does_not_parse")),
        "candidates_resolving": sum(1 for candidate in run if candidate.get("resolves")),
        "candidates_passing_what_should_start_passing_and_breaking_what_should_keep_passing":
            sum(1 for candidate in run if candidate.get("whole_run") and not candidate.get("resolves")),
        "candidates_stopped_for_time": sum(1 for candidate in run if candidate.get("stopped")),
        "one_submission__tasks_resolved": len(one),
        "one_submission__tasks": one,
        "one_submission__share_of_the_judged_with_a_candidate": _share(len(one), len(counted)),
        "one_submission__share_of_the_django_tasks": _share(len(one), len(rows)),
        "within__tasks_resolved": {str(rank): sum(1 for at in places.values() if at is not None and at <= rank) for rank in RANKS},
        "within_twenty__tasks_resolved": len(within),
        "within_twenty__tasks": {task: places[task] for task in within},
        "within_twenty__resolved_and_not_in_the_earlier_record": sum(1 for task in within if task not in recorded),
        "within_twenty__tasks_not_in_the_earlier_record": [task for task in within if task not in recorded],
        "recorded_places": {task: at for task, at in sorted(recorded.items()) if task in rows},
        "recorded_places__tasks_judged_of_the_seven": len(standing) + len(failing),
        "recorded_places__standing": standing,
        "recorded_places__judged_and_not_resolving_at_the_recorded_place": len(failing),
        "recorded_places__not_resolving": failing,
        "recorded_places__not_judged": unjudged,
        "another_tasks_text__tasks_run": len(others),
        "another_tasks_text__tasks_resolved": sum(1 for other in others if other.get("resolves")),
        "by_version": dict(sorted(versions.items())),
        "seconds_of_test_runs": round(sum(row.get("seconds") or 0 for row in rows.values()), 1),
    }


def held(summary: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Each expectation with what was found and whether it held."""
    out = {}
    for key, (least, most) in EXPECTED.items():
        found = summary.get(key)
        out[key] = {"expected": [least, most], "found": found, "held": found is not None and least <= found <= most}
    return out


def rule(summary: Mapping[str, Any]) -> dict[str, Any]:
    """What follows from the counts; written before they were made."""
    judged_share = summary.get("judged__share_of_the_django_tasks") or 0.0
    failing = summary.get("recorded_places__judged_and_not_resolving_at_the_recorded_place") or 0
    one, within = summary.get("one_submission__tasks_resolved") or 0, summary.get("within_twenty__tasks_resolved") or 0
    other = summary.get("another_tasks_text__tasks_resolved") or 0
    said = []
    if judged_share < 0.5:
        said.append("this machine judges fewer than half of the tasks: the counts below say little, and the next step is a machine that holds the tasks' own images")
    if other:
        said.append("a candidate made from another task's text passes: the tests accept what has nothing of the task in it, and every count here is to be read against that")
    if failing:
        said.append(f"the earlier record counted {failing} task(s) too many: a candidate whose text is a recorded passing patch does not pass here; from now on the tests are the judge, not the text")
    else:
        said.append("the earlier record's places stand under the tasks' own tests, as far as this machine judges them")
    if within > one:
        said.append(f"one submission resolves {one} and the first twenty hold a resolving candidate for {within}: choosing among candidates WITHOUT the hidden tests is worth at most {within - one} task(s) here; "
                    "the rest of the tasks have no resolving candidate at all, and that is writing, not choosing")
    else:
        said.append(f"one submission resolves {one} and the first twenty resolve no more: choosing is not what limits this chain; writing the change is")
    return {"verdict": said,
            "next": "with the tests as the judge on this machine, work on WRITING the change, counted by the tests and not by the text of somebody's patch"}


def recorded_places(file_record: Mapping[str, Any]) -> dict[str, int]:
    """{Django task: the place of its first candidate that is the text of a passing patch}, as the earlier record has it."""
    return {task: row["place"] for task, row in file_record["per_task"].items() if task.startswith(PROJECT + "-") and row.get("place") is not None}


def code_sha256() -> dict[str, str]:
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (pathlib.Path(__file__).resolve(), pathlib.Path(judge.__file__).resolve(), pathlib.Path(finder.__file__).resolve(),
                         pathlib.Path(pointer.__file__).resolve())}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--dataset-dir", required=True, type=pathlib.Path, help="holds problems/swe/swebench-verified/<task>.yaml and patches/<task>_tests.patch")
    parser.add_argument("--pull-requests-dir", required=True, type=pathlib.Path)
    parser.add_argument("--trees-dir", required=True, type=pathlib.Path)
    parser.add_argument("--work-dir", required=True, type=pathlib.Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--only", nargs="*", default=None, help="just these tasks")
    parser.add_argument("--no-candidates", action="store_true", help="only whether this machine can judge each task")
    parser.add_argument("--out", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)

    def say(text: str) -> None:
        print(time.strftime("%H:%M:%S", time.gmtime()), text, flush=True)

    started = time.time()
    statements = args.dataset_dir / "problems" / "swe" / "swebench-verified"
    everything = sorted(json.loads(place.PASSING_RECORD.read_text())["per_task"])
    issues = content.statements(statements, everything)
    other = function_measure.other_text_of(sorted(issues))
    tasks = [task for task in everything if task.startswith(PROJECT + "-") and task in issues]
    if args.only is not None:
        tasks = [task for task in tasks if task in set(args.only)]
    commits = measure.base_commits(statements, tasks)
    tasks.sort(key=lambda task: int(task.rsplit("-", 1)[1]))
    clone = args.trees_dir / f"{PROJECT}.git"
    args.work_dir.mkdir(parents=True, exist_ok=True)
    say(f"{len(tasks)} tasks; fetching every file of their trees")
    fetched = fetch_everything(clone, [commits[task] for task in tasks])
    say(f"fetched {fetched}")
    if fetched["still_missing"]:
        say("REFUSED: files of the trees are missing after the fetch")
        return 2
    records, patches, tests = {}, {}, {}
    for task in tasks:
        records[task] = json.loads((args.pull_requests_dir / f"{task}.json").read_text())
        patches[task] = (args.dataset_dir / "patches" / f"{task}_tests.patch").read_text(encoding="utf-8")
        tests[task] = tests_of(statements / f"{task}.yaml")
    broken = [task for task in tasks if records[task].get("error") or any(file.get("fetch_error") for file in records[task].get("files") or ())]
    if broken:
        say(f"REFUSED: {len(broken)} pull request records are not whole")
        return 2
    made: dict[str, dict[str, Any]] = {task: {"candidates": [], "another_tasks_text": None} for task in tasks}
    if not args.no_candidates:
        made = candidates_of(clone, measure.repository_of(tasks[0]), [(task, commits[task], issues[task], issues[other[task]]) for task in tasks])
        say(f"candidates made: {sum(len(row['candidates']) for row in made.values())} for {sum(1 for row in made.values() if row['candidates'])} tasks")

    rows_file = args.work_dir / "rows.jsonl"
    per_task: dict[str, dict[str, Any]] = {}
    if rows_file.exists():
        for line in rows_file.read_text().splitlines():
            row = json.loads(line)
            if row["task"] in tasks:
                per_task[row["task"]] = row["row"]
        say(f"{len(per_task)} tasks already judged, read from {rows_file}")
    waiting: queue.Queue = queue.Queue()
    for task in sorted(tasks, key=lambda task: (not made[task]["candidates"], int(task.rsplit("-", 1)[1]))):
        if task not in per_task:
            waiting.put(task)
    lock = threading.Lock()

    def work(number: int) -> None:
        tree = args.work_dir / f"tree{number}"
        while True:
            try:
                task = waiting.get_nowait()
            except queue.Empty:
                return
            try:
                row = of_task(tree, clone, commits[task], patches[task], expert_diff(records[task], patches[task]), tests[task],
                              made[task]["candidates"], made[task]["another_tasks_text"] if made[task]["candidates"] else None)
            except Exception as error:  # noqa: BLE001 - one task that cannot be set up must not end the count
                row = {"version": tests[task].get("version"), "judged": False, "why_not": f"could not be set up: {type(error).__name__}: {str(error)[:200]}",
                       "candidates_made": len(made[task]["candidates"]), "candidates": [], "another_tasks_text": None}
            with lock:
                per_task[task] = row
                with rows_file.open("a") as out:
                    out.write(json.dumps({"task": task, "row": row}, ensure_ascii=False) + "\n")
                resolving = first_resolving(row)
                say(f"{len(per_task)}/{len(tasks)} {task} v{row.get('version')} judged={row.get('judged')} candidates={len(row.get('candidates') or ())} "
                    f"first resolving={resolving} {row.get('seconds')}s{'' if row.get('judged') else ' WHY ' + str(row.get('why_not'))}")

    threads = [threading.Thread(target=work, args=(number,), daemon=True) for number in range(max(1, args.workers))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    recorded = recorded_places(json.loads(FILE_RECORD.read_text()))
    summary = summarise({task: per_task[task] for task in tasks}, recorded)
    record = {
        "schema": SCHEMA,
        "made_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "python": sys.version.split()[0],
        "expected": {key: list(value) for key, value in EXPECTED.items()},
        "expectations": held(summary),
        "summary": summary,
        "rule": rule(summary),
        "fetched": fetched,
        "seconds": round(time.time() - started, 1),
        "code_sha256": code_sha256(),
        "per_task": {task: per_task[task] for task in tasks},
    }
    say(json.dumps({key: value for key, value in summary.items() if not isinstance(value, (dict, list))}, indent=1))
    if args.out is not None:
        args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        say(f"written {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
