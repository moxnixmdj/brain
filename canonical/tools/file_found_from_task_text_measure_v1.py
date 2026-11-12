#!/usr/bin/env python3
"""Whether the task's text finds the file in the project's tree, and what is left of the chain when nothing is handed over.

Why this exists
---------------
canonical/verification/FUNCTION_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json was counted
with the file handed over, and its rule, written before counting, said what comes next: count
finding the file, on the projects' trees. A repair run has the tree and the text of the task and
nothing else.

So, for the 500 tasks of SWE-bench Verified, with each project's tree as it stood at the task's
base commit (its Python files outside the tests):

  the file         where a file the expert changed stands when
                   canonical/runtime/file_the_task_text_points_at_v1.py orders the files by the
                   task text; the same by score alone (plain BM25, which others have published
                   counts for); and with ANOTHER task's text, the next task of the same project
  the chain        for the tasks that have a test-passing patch inside one function: the place of
                   such a patch among the 20 candidates made from the tree and the text alone --
                   the first file, its first 4 functions, 5 quoted-line candidates each -- and the
                   same with the functions of the first 3 files ranked together
  the earlier      the lists counted earlier (the learner, pieces taken out) reach a task from the
  lists            tree only where its function is the first of the first file

The patches are the recorded ones; none of the tasks' programs or tests is run and no model is
called. What was expected and the rule were written here before anything was counted: EXPECTED.

  --fetch      clone the 12 projects without their file contents, list each task's tree, and
               fetch the contents of the Python files outside the tests (about 0.5 GB)
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import multiprocessing
import pathlib
import re
import statistics
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import file_the_task_text_points_at_v1 as finder  # noqa: E402
from canonical.runtime import function_the_task_text_points_at_v1 as pointer  # noqa: E402
from canonical.tools import expert_fix_pull_request_collector_v1 as collector  # noqa: E402
from canonical.tools import fix_content_in_task_text_measure_v1 as content  # noqa: E402
from canonical.tools import function_found_from_task_text_measure_v1 as function_measure  # noqa: E402
from canonical.tools import passing_patch_shape_measure_v1 as passing  # noqa: E402
from canonical.tools import small_passing_patch_place_measure_v1 as place  # noqa: E402

SCHEMA = "BRAIN_FILE_FOUND_FROM_TASK_TEXT_V1"
FUNCTION_RECORD = ROOT / "canonical" / "verification" / "FUNCTION_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json"
PLACE_RECORD = content.PLACE_RECORD
BUDGET, FIRST = function_measure.BUDGET, function_measure.FIRST
RANKS = (1, 3, 10)
THREE_FILES = 3
CHUNK = 40                       # tasks handled by one worker at a time, neighbours in the project's history
FETCH_AT_ONCE = 4000             # file contents asked for in one request

EXPECTED: dict[str, Any] = {
    "written": "2026-11-12 23:50 UTC, before anything was counted. Known by then: counts others published for plain BM25 over a project's files "
               "(500 SWE-bench Verified issues: a fixing file first 26.6%, among the first 3 47.0%, among the first 10 70.2%, synaptixs/spine pull "
               "request 593; SWE-bench Lite: first 30% to 39% in three other counts); that 27% of the Verified issues write a file path out "
               "(arXiv 2506.12286); and the last record here (10 tasks reached with the file given, 3 more by the earlier lists). No rank of any file.",
    "share of the 500 tasks with a file the expert changed first, by score alone": [0.22, 0.50],
    "the same in the order of the organ, which puts the files the text names first": [0.27, 0.58],
    "share with such a file among the first 3, organ": [0.45, 0.78],
    "share with such a file among the first 10, organ": [0.62, 0.90],
    "share with such a file first, another task's text, organ": [0.00, 0.08],
    "share of the tasks whose text names a file the expert changed": [0.15, 0.50],
    "median number of Python files outside the tests": [100, 900],
    "of the 10 tasks reached with the file given, those reached from the tree, all 20 candidates in the first file": [4, 9],
    "the same with the functions of the first 3 files ranked together": [4, 10],
    "tasks reached from the tree with another task's text": [0, 1],
    "rule": "If, from the tree and the text alone with all 20 candidates in the first file, at least 7 of the 10 tasks reached with the file given are "
            "still reached, the chain stands as it is and the next step is to run the tasks' own tests on what it reaches. If 3 or fewer are, finding "
            "the file is the limiting step of the chain and a better order of the files comes before anything else. In between: undecided, and the "
            "second design counted here (the functions of the first 3 files ranked together) says whether spreading the candidates over files is the "
            "thing to do. Separately: if score alone puts an expert-changed file first for a share outside its range above, the files read or the "
            "scorer differ from what others measured, and no number of this record is quoted before that is explained.",
}


# --------------------------------------------------------------------------- #
# the projects' trees
# --------------------------------------------------------------------------- #
_BASE = re.compile(r"^base_commit:\s*['\"]?([0-9a-f]{40})", re.MULTILINE)


def project_of(task: str) -> str:
    return task.rsplit("-", 1)[0]


def repository_of(task: str) -> str:
    owner, name, _ = collector.parts(task)
    return f"{owner}/{name}"


def base_commits(directory: pathlib.Path, tasks: Sequence[str]) -> dict[str, str]:
    out = {}
    for task in tasks:
        path = directory / f"{task}.yaml"
        found = _BASE.search(path.read_text(encoding="utf-8")) if path.exists() else None
        if found:
            out[task] = found.group(1)
    return out


def _git(directory: pathlib.Path, *args: str, text_in: str | None = None, check: bool = True) -> str:
    done = subprocess.run(["git", "-C", str(directory), *args], input=text_in, capture_output=True, text=True)
    if check and done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:3])}: {done.stderr.strip()[:300]}")
    return done.stdout


def listing(directory: pathlib.Path, repository: str, commit: str) -> list[tuple[str, str]]:
    """(path, the name of its contents) of every Python file outside the tests in the tree of a commit."""
    out = []
    for entry in _git(directory, "ls-tree", "-r", "-z", commit).split("\0"):
        if not entry:
            continue
        head, path = entry.split("\t", 1)
        mode, kind, name = head.split(" ")
        if kind == "blob" and mode in ("100644", "100755") and path.endswith(".py") and not collector.is_test(repository, path):
            out.append((path, name))
    return out


def fetch(trees: pathlib.Path, tasks: Sequence[str], commits: Mapping[str, str]) -> dict[str, Any]:
    """Clone each project without file contents, then fetch the contents of the listed files of every task's tree."""
    report: dict[str, Any] = {}
    for project in sorted({project_of(task) for task in tasks}):
        mine = [task for task in tasks if project_of(task) == project and task in commits]
        repository = repository_of(mine[0])
        directory = trees / f"{project}.git"
        started = time.time()
        if not directory.exists():
            subprocess.run(["git", "clone", "-q", "--bare", "--filter=blob:none", f"https://github.com/{repository}", str(directory)], check=True)
        missing = [commits[task] for task in mine if subprocess.run(["git", "-C", str(directory), "cat-file", "-e", commits[task] + "^{commit}"],
                                                                    capture_output=True).returncode != 0]
        for commit in missing:
            _git(directory, "fetch", "-q", "--filter=blob:none", "origin", commit, check=False)
        wanted: dict[str, None] = {}
        for task in mine:
            for _, name in listing(directory, repository, commits[task]):
                wanted[name] = None
        names = list(wanted)
        for at in range(0, len(names), FETCH_AT_ONCE):
            _git(directory, "-c", "fetch.negotiationAlgorithm=noop", "fetch", "origin", "--no-tags", "--no-write-fetch-head", "--recurse-submodules=no",
                 "--filter=blob:none", "--stdin", text_in="\n".join(names[at:at + FETCH_AT_ONCE]) + "\n")
        report[project] = {"tasks": len(mine), "commits_fetched_by_name": len(missing), "file_contents": len(names), "seconds": round(time.time() - started, 1)}
        print("FETCHED", project, report[project], flush=True)
    return report


class Contents:
    """The contents of files by name, read from one project's clone through one `git cat-file --batch`."""

    def __init__(self, directory: pathlib.Path):
        self._process = subprocess.Popen(["git", "-C", str(directory), "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def read(self, name: str) -> str:
        self._process.stdin.write(name.encode() + b"\n")
        self._process.stdin.flush()
        head = self._process.stdout.readline().split()
        if len(head) != 3:
            return ""
        data = self._process.stdout.read(int(head[2]))
        self._process.stdout.read(1)
        return data.decode("utf-8", errors="replace")

    def close(self) -> None:
        self._process.stdin.close()
        self._process.wait()


# --------------------------------------------------------------------------- #
# one task
# --------------------------------------------------------------------------- #
def targets_of(record: Mapping[str, Any], diffs: Sequence[str]) -> dict[tuple[str, tuple[int, int]], set[str]]:
    """{(path, the lines of a function): the texts of that function after a passing patch}, as the function count cut them."""
    files = passing.Files(record)
    functions: dict[str, list[pointer.Function]] = {}
    out: dict[tuple[str, tuple[int, int]], set[str]] = {}
    for diff in diffs:
        found = function_measure.cut(files, diff)
        if found is None:
            continue
        path, span, _, after = found
        if path not in functions:
            functions[path] = pointer.functions_of(files.before[path])
        if not any((function.first, function.last) == span for function in functions[path]):
            continue
        try:
            out.setdefault((path, span), set()).add(place.normal(after))
        except (SyntaxError, ValueError, RecursionError, MemoryError):
            continue
    return out


def rank_of(order: Sequence[str], wanted: set[str]) -> int | None:
    """The place, from 1, of the first of the wanted files in an order."""
    for at, path in enumerate(order, 1):
        if path in wanted:
            return at
    return None


def place_of(made: Sequence[tuple[str, pointer.Function, str]], targets: Mapping[tuple[str, tuple[int, int]], set[str]]) -> int | None:
    """The place, from 1, of the first candidate that is a function's text after a passing patch."""
    for at, (path, function, program) in enumerate(made, 1):
        if program in targets.get((path, (function.first, function.last)), ()):
            return at
    return None


def of_task(documents: Mapping[str, Mapping[str, int]], source_of, record: Mapping[str, Any], diffs: Sequence[str], text: str, other_text: str) -> dict[str, Any]:
    """Everything counted for one task, from the documents of its tree."""
    expert = set(passing.Files(record).before)
    in_order = finder.order(documents, text)
    by_score = finder.order(documents, text, use_names=False)
    with_other = finder.order(documents, other_text)
    targets = targets_of(record, diffs)
    holding = {path for path, _ in targets}
    row: dict[str, Any] = {
        "files": len(documents),
        "expert": rank_of(in_order, expert), "expert_by_score": rank_of(by_score, expert), "expert_other_text": rank_of(with_other, expert),
        "expert_named": max([finder.named(path, text) for path in expert if path in documents], default=None),
        "passing": rank_of(in_order, holding) if holding else None,
        "place": None, "place_three": None, "place_other_text": None,
    }
    if targets:
        row["place"] = place_of(finder.candidates(documents, source_of, text, in_order=in_order), targets)
        row["place_three"] = place_of(finder.candidates(documents, source_of, text, files_tried=THREE_FILES, in_order=in_order), targets)
        row["place_other_text"] = place_of(finder.candidates(documents, source_of, other_text, in_order=with_other), targets)
    before = passing.Files(record).before
    row["same_text"] = all(source_of(path) == before[path] for path in expert if path in documents)
    return row


def of_chunk(job: tuple[str, str, list[tuple[str, str, Mapping[str, Any], list[str], str, str]]]) -> dict[str, dict[str, Any]]:
    """The tasks of one stretch of a project's history: each file's words are counted once for as long as the file stays the same."""
    directory, repository, tasks = job
    contents = Contents(pathlib.Path(directory))
    kept: dict[tuple[str, str], Any] = {}
    out = {}
    try:
        for task, commit, record, diffs, text, other_text in tasks:
            files = listing(pathlib.Path(directory), repository, commit)
            here = {}
            for path, name in files:
                key = (name, path)
                if key not in kept:
                    kept[key] = finder.document(path, contents.read(name))
                here[key] = kept[key]
            kept = here                                                # what the next task does not hold again is let go
            names = dict(files)
            documents = {path: kept[(name, path)] for path, name in files}
            out[task] = of_task(documents, lambda path: contents.read(names[path]), record, diffs, text, other_text)
    finally:
        contents.close()
    return out


# --------------------------------------------------------------------------- #
# all of them
# --------------------------------------------------------------------------- #
def _share(count: int, of: int) -> float | None:
    return round(count / of, 3) if of else None


def _within(values: Sequence[int | None], ranks: Sequence[int] = RANKS) -> dict[str, int]:
    return {str(n): sum(1 for value in values if value is not None and value <= n) for n in ranks}


def summarise(per_task: Mapping[str, Mapping[str, Any]], reached_with_the_file: Sequence[str], earlier_kept_with_the_file: Sequence[str]) -> dict[str, Any]:
    tasks = sorted(per_task)
    rows = [per_task[task] for task in tasks]
    total = len(rows)

    def shares(found: Mapping[str, int], of: int) -> dict[str, float | None]:
        return {key: _share(value, of) for key, value in found.items()}

    organ, by_score, other = (_within([row[key] for row in rows]) for key in ("expert", "expert_by_score", "expert_other_text"))
    named = [row for row in rows if row["expert_named"]]
    by_naming = {}
    for label, level in (("written out with a directory or a module path", finder.WRITTEN_OUT), ("the file name alone", finder.FILE_NAME_ONLY), ("not named", finder.NOT_NAMED)):
        mine = [row for row in rows if row["expert_named"] == level]
        by_naming[label] = {"tasks": len(mine), "first_in_the_order_of_the_organ": sum(1 for row in mine if row["expert"] == 1),
                            "first_by_score_alone": sum(1 for row in mine if row["expert_by_score"] == 1)}
    by_project: dict[str, dict[str, int]] = {}
    for task in tasks:
        found = by_project.setdefault(project_of(task), {"tasks": 0, "first": 0, "among_the_first_3": 0, "among_the_first_10": 0})
        found["tasks"] += 1
        rank = per_task[task]["expert"]
        found["first"] += rank is not None and rank <= 1
        found["among_the_first_3"] += rank is not None and rank <= 3
        found["among_the_first_10"] += rank is not None and rank <= 10
    with_patch = [row for row in rows if row["passing"] is not None]
    reached = [task for task in tasks if per_task[task]["place"] is not None]
    reached_three = [task for task in tasks if per_task[task]["place_three"] is not None]
    given = [task for task in reached_with_the_file if task in per_task]
    earlier = [task for task in earlier_kept_with_the_file if task in per_task and per_task[task]["passing"] == 1]
    return {
        "tasks": total,
        "tasks_with_an_expert_file_in_the_tree": sum(1 for row in rows if row["expert"] is not None),
        "median_python_files_outside_the_tests": statistics.median([row["files"] for row in rows]) if rows else None,
        "expert_file_among_the_first__organ": organ, "expert_file_among_the_first__organ__share": shares(organ, total),
        "expert_file_among_the_first__score_alone": by_score, "expert_file_among_the_first__score_alone__share": shares(by_score, total),
        "expert_file_among_the_first__another_tasks_text": other, "expert_file_among_the_first__another_tasks_text__share": shares(other, total),
        "tasks_whose_text_names_an_expert_file": len(named), "tasks_whose_text_names_an_expert_file__share": _share(len(named), total),
        "by_how_the_text_names_the_file": by_naming,
        "by_project": by_project,
        "tasks_with_a_passing_patch_inside_one_function": len(with_patch),
        "file_holding_such_a_patch_among_the_first__organ": _within([row["passing"] for row in with_patch]),
        "chain__tasks_reached_from_the_tree__all_20_in_the_first_file": len(reached), "chain__which": reached,
        "chain__tasks_reached__functions_of_the_first_3_files_together": len(reached_three), "chain__which_three": reached_three,
        "chain__tasks_reached_with_another_tasks_text": sum(1 for row in rows if row["place_other_text"] is not None),
        "reached_with_the_file_given": len(given),
        "of_them_reached_from_the_tree": sum(1 for task in given if per_task[task]["place"] is not None),
        "of_them_reached_from_the_tree__three_files": sum(1 for task in given if per_task[task]["place_three"] is not None),
        "reached_from_the_tree_only": sum(1 for task in reached if task not in set(given)),
        "earlier_lists__tasks_kept_with_the_file_given": len([task for task in earlier_kept_with_the_file if task in per_task]),
        "earlier_lists__of_them_with_their_file_first": len(earlier), "earlier_lists__which": earlier,
        "of_the_500_from_the_tree_and_the_text_alone": len(set(reached) | set(earlier)),
        "expert_files_whose_text_in_the_tree_is_not_what_the_collector_read__tasks": sum(1 for row in rows if not row["same_text"]),
    }


def rule(summary: Mapping[str, Any]) -> dict[str, Any]:
    kept, of = summary["of_them_reached_from_the_tree"], summary["reached_with_the_file_given"]
    low, high = EXPECTED["share of the 500 tasks with a file the expert changed first, by score alone"]
    share = summary["expert_file_among_the_first__score_alone__share"]["1"]
    verdict = ("the chain stands as it is; next, run the tasks' own tests on what it reaches" if kept >= 7
               else "finding the file is the limiting step of the chain" if kept <= 3 else "undecided")
    return {"reached_with_the_file_given": of, "of_them_reached_from_the_tree": kept, "verdict": verdict,
            "three_files_together_reach": summary["of_them_reached_from_the_tree__three_files"],
            "score_alone_agrees_with_what_others_measured": share is not None and low <= share <= high}


def earlier_kept(function_record: Mapping[str, Any], place_record: Mapping[str, Any]) -> list[str]:
    """The tasks the earlier lists still reach with the file given: within 180 with the function given, and every function that holds a small passing patch first of its file."""
    out = []
    for task, found in place_record["per_task"].items():
        at = found[2]
        if at is None or at > BUDGET - FIRST:
            continue
        ranks = [row["rank"] for row in function_record["per_task"].get(task, {}).get("functions", []) if row["small"]]
        if ranks and all(rank == 1 for rank in ranks):
            out.append(task)
    return sorted(out)


def code_sha256() -> dict[str, str]:
    names = ("canonical/tools/file_found_from_task_text_measure_v1.py", "canonical/runtime/file_the_task_text_points_at_v1.py",
             "canonical/runtime/function_the_task_text_points_at_v1.py", "canonical/runtime/quoted_in_the_task_text_v1.py",
             "canonical/runtime/bound_capabilities/objective_relevance_bm25.py", "canonical/tools/function_found_from_task_text_measure_v1.py",
             "canonical/tools/passing_patch_shape_measure_v1.py", "canonical/tools/expert_fix_pull_request_collector_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--trees-dir", required=True, type=pathlib.Path)
    parser.add_argument("--statements-dir", required=True, type=pathlib.Path)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--cache-dir", type=pathlib.Path)
    parser.add_argument("--pull-requests-dir", type=pathlib.Path)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args(argv)

    started = time.time()
    say = lambda line: print(line, round(time.time() - started, 1), "s", flush=True)  # noqa: E731
    function_record = json.loads(FUNCTION_RECORD.read_text())
    tasks = sorted(json.loads(place.PASSING_RECORD.read_text())["per_task"])
    commits = base_commits(args.statements_dir, tasks)
    if args.fetch:
        report = fetch(args.trees_dir, tasks, commits)
        say(f"FETCHED {sum(found['file_contents'] for found in report.values())} file contents of {len(report)} projects")
        return 0

    then = passing.verdicts(args.cache_dir, passing.WITH_PATCHES)
    with_patches = {name: found for name, found in then.items() if (args.cache_dir / passing.WITH_PATCHES[:10] / name / "all_preds.jsonl").exists()}
    passed: dict[str, list[str]] = {task: [] for task in tasks}
    for name in sorted(with_patches):
        offered = passing.patches(args.cache_dir, name)
        for task in sorted(with_patches[name]):
            if task in passed and task in offered and offered[task] not in passed[task]:
                passed[task].append(offered[task])
    issues = content.statements(args.statements_dir, tasks)
    other = function_measure.other_text_of(sorted(issues))
    jobs = []
    for project in sorted({project_of(task) for task in tasks}):
        directory = args.trees_dir / f"{project}.git"
        mine = [task for task in tasks if project_of(task) == project and task in commits and task in issues]
        when = {task: int(_git(directory, "log", "-1", "--format=%ct", commits[task]).strip() or 0) for task in mine}
        mine.sort(key=lambda task: (when[task], task))
        rows = [(task, commits[task], json.loads((args.pull_requests_dir / f"{task}.json").read_text()), passed[task], issues[task], issues[other[task]]) for task in mine]
        for at in range(0, len(rows), CHUNK):
            jobs.append((str(directory), repository_of(mine[0]), rows[at:at + CHUNK]))
    jobs.sort(key=lambda job: -len(job[2]))
    say(f"{len(tasks)} tasks, {sum(len(job[2]) for job in jobs)} with a base commit and an issue text, in {len(jobs)} stretches")

    per_task: dict[str, dict[str, Any]] = {}
    with multiprocessing.Pool(args.workers) as pool:
        for found in pool.imap_unordered(of_chunk, jobs, chunksize=1):
            per_task.update(found)
            say(f"{len(per_task)} tasks")
    reached_with_the_file = sorted(task for task, found in function_record["per_task"].items() if found["file_given"] is not None)
    summary = summarise(per_task, reached_with_the_file, earlier_kept(function_record, json.loads(PLACE_RECORD.read_text())))
    record = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expected_before": EXPECTED, "summary": summary, "rule": rule(summary),
        "per_task": {task: per_task[task] for task in sorted(per_task)},
        "base_commits_from": list(content.STATEMENTS), "experiments_commit": passing.WITH_PATCHES, "submissions_with_patches": len(with_patches),
        "model_calls": 0, "task_programs_run": 0, "task_tests_run": 0, "code_sha256": code_sha256(), "seconds": round(time.time() - started, 1),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("WROTE", args.out, record["seconds"], "s", flush=True)
    print(json.dumps({"rule": record["rule"], "summary": {key: value for key, value in summary.items() if key != "by_project"}}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
