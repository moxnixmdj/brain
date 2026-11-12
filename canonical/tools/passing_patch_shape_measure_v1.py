#!/usr/bin/env python3
"""Is there a smaller repair that also passes? The shapes of other people's test-passing patches.

What is asked
-------------
FIX_SHAPE_CENSUS_20261112_V1.json counted the shape of the EXPERT'S fix for the 500 tasks of
SWE-bench Verified and concluded that a list of single small changes could hold at most 40 of
them. It said what it did not show: another, smaller change may repair the same bug. That limit
decides whether the conclusion stands, and it can be measured without running one test here.

Agents built on language models were run on the same 500 tasks by other people. The benchmark's
harness ran the tests on their patches, and both the patches and the verdicts were published
(github.com/SWE-bench/experiments; the patches stand in its history until 2025-05-21). So for
every task there is a set of patches that PASSED, written by something other than the expert.
Each is given its shape with the same code as the expert's fix (canonical/runtime/fix_shape_v1.py).

  for how many tasks is SOME passing patch one small change that could be listed?
  for how many is some passing patch within one statement?

and, from the verdicts alone (every submission, to this day):

  does the share of agents that resolve a task fall as the expert's fix gets larger in shape?
  If it does not, the shapes do not track what makes a real fix hard.

A patch is given a shape only when it changes exactly one Python file that was there before,
outside the tests, and that file is one the expert changed too (its text is at hand). Files a
patch ADDS are counted beside the shape, never into it: agents leave reproduction scripts behind.
Both readings are reported, with the added files ignored and with any added file ruling the patch
out. Everything else (several files, another file than the expert's, a patch that does not apply)
is not a small change here. So the counts of small passing patches are floors.

No program and no test is run. No model is called: the patches are recordings.

What was expected, and the two rules, were written into EXPECTED before any patch was read.
What was found: canonical/verification/PASSING_PATCH_SHAPE_SWEBENCH_VERIFIED_20261112_V1.json.

Usage
-----
  python3 canonical/tools/passing_patch_shape_measure_v1.py --fetch --cache-dir /tmp/mat/experiments
  python3 canonical/tools/passing_patch_shape_measure_v1.py --cache-dir /tmp/mat/experiments \\
      --pull-requests-dir /tmp/swe/pulls --out /tmp/mat/passing.json
"""
from __future__ import annotations

import argparse
import ast
import collections
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import re
import statistics
import subprocess
import sys
import textwrap
import time
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import fix_shape_v1 as fix_shape  # noqa: E402
from canonical.tools import expert_fix_pull_request_collector_v1 as collector  # noqa: E402
from canonical.tools import expert_fix_repetition_measure_v1 as repetition  # noqa: E402
from canonical.tools import fix_shape_census_measure_v1 as census  # noqa: E402

SCHEMA = "BRAIN_PASSING_PATCH_SHAPE_V1"
EXPERIMENTS = "SWE-bench/experiments"
WITH_PATCHES = "05ad61feb9c9f334dc340baea7c4f31cf7854274"     # 2025-05-21, the commit before "Move predictions to s3 bucket"
TO_THIS_DAY = "40f164d5b8f1d249bf95a6df8b74b577fd8e519d"      # main on 2026-11-12
WHOLE_FILE_AT_MOST_LINES = 1500                                # a larger file is only looked at inside one definition

ELSEWHERE, NOT_APPLIED, NOT_EXAMINED, NO_PYTHON = ("another file than the expert changed", "the patch does not apply to the file",
                                                   "several top-level statements of a large file", "no python file changed that was there before")
CLASSES = ("can be listed", "one statement, not listable", fix_shape.ONE_PLACE, fix_shape.SEVERAL_PLACES, census.SEVERAL_FILES)

EXPECTED: dict[str, Any] = {
    "written": "2026-11-12 about 20:31 UTC, before this tool had read a patch or a verdict. To learn their format one file of patches "
               "(its first patch) and one file of verdicts (its counts) had been looked at by hand.",
    "share of submissions that resolve a task, mean over the tasks of a class of the expert's fix": {
        "can be listed": [0.65, 0.85], "one statement, not listable": [0.55, 0.75], fix_shape.ONE_PLACE: [0.40, 0.60],
        fix_shape.SEVERAL_PLACES: [0.30, 0.50], census.SEVERAL_FILES: [0.15, 0.35]},
    "tasks for which some passing patch can be listed (added files ignored), of 500": [55, 90],
    "tasks for which some passing patch is within one statement (added files ignored), of 500": [200, 260],
    "rules": {
        "do the shapes track difficulty": "The mean share of submissions that resolve a task has to fall by at least 5 points at each step from "
                                          "'at most one statement' to 'several places' to 'several files' of the expert's fix. If it does not, the shapes "
                                          "say nothing about what makes a real fix hard and the census must not be used to argue about it.",
        "was a tenth wrong": "If some passing patch can be listed for at least 100 of the 500 tasks (added files ignored), then 'tops out at "
                             "roughly a tenth' was wrong by a factor of two or more: it is withdrawn, and a repair run on real projects with lists "
                             "of single small changes is back on the table."},
}


# --------------------------------------------------------------------------- #
# the recordings
# --------------------------------------------------------------------------- #
def gh(path: str, ref: str, raw: bool = True, tries: int = 4) -> bytes:
    command = ["gh", "api"] + (["-H", "Accept: application/vnd.github.raw"] if raw else []) + [f"repos/{EXPERIMENTS}/contents/{path}?ref={ref}"]
    last = ""
    for attempt in range(tries):
        done = subprocess.run(command, capture_output=True)
        if done.returncode == 0:
            return done.stdout
        last = (done.stderr or done.stdout).decode("utf-8", "replace")[-200:]
        if "Not Found" in last or "404" in last:
            break
        time.sleep(1 + 2 * attempt)
    raise RuntimeError(last)


def fetch(cache: pathlib.Path, workers: int = 6, ask: Callable[..., bytes] = gh) -> dict[str, int]:
    """Every submission's verdicts to this day, and the patches of those that stood in the tree on 2025-05-21."""
    tally: collections.Counter = collections.Counter()

    def one(job: tuple[str, str, str]) -> str:
        ref, name, what = job
        target = cache / ref[:10] / name / what.split("/")[-1]
        if target.exists():
            return "already there"
        try:
            data = ask(f"evaluation/verified/{name}/{what}", ref)
        except RuntimeError:
            return f"missing {what.split('/')[-1]}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return "fetched " + what.split("/")[-1]

    jobs: list[tuple[str, str, str]] = []
    for ref, files in ((TO_THIS_DAY, ("results/results.json",)), (WITH_PATCHES, ("results/results.json", "all_preds.jsonl"))):
        names = [row["name"] for row in json.loads(ask("evaluation/verified", ref, raw=False)) if row["type"] == "dir"]
        (cache / ref[:10]).mkdir(parents=True, exist_ok=True)
        (cache / ref[:10] / "names.json").write_text(json.dumps(sorted(names)))
        jobs += [(ref, name, what) for name in names for what in files]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for how in pool.map(one, jobs):
            tally[how] += 1
    return dict(tally)


def verdicts(cache: pathlib.Path, ref: str) -> dict[str, set[str]]:
    """{submission: the tasks it resolved}, for the submissions whose verdicts could be read."""
    out: dict[str, set[str]] = {}
    for path in sorted((cache / ref[:10]).glob("*/results.json")):
        try:
            out[path.parent.name] = set(json.loads(path.read_text())["resolved"])
        except (ValueError, KeyError, TypeError):
            continue
    return out


def patches(cache: pathlib.Path, submission: str) -> dict[str, str]:
    """{task: the patch this submission proposed for it}."""
    out: dict[str, str] = {}
    path = cache / WITH_PATCHES[:10] / submission / "all_preds.jsonl"
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row.get("model_patch"), str) and row["model_patch"].strip() and isinstance(row.get("instance_id"), str):
            out[row["instance_id"]] = row["model_patch"]
    return out


# --------------------------------------------------------------------------- #
# one patch
# --------------------------------------------------------------------------- #
_HEAD = re.compile(r"diff --git a/(.*) b/(.*)$")


def files_of(diff: str) -> list[dict[str, Any]]:
    """A patch as its files: the path, whether the file is added, removed, renamed or modified, and its hunks as GitHub writes them."""
    out: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    in_hunk = False
    for line in diff.split("\n"):
        if line.startswith("diff --git "):
            found = _HEAD.match(line.rstrip("\r"))
            current = {"path": found.group(2) if found else None, "status": "modified", "lines": []}
            out.append(current)
            in_hunk = False
            continue
        if current is None:
            continue
        if not in_hunk:
            if line.startswith("new file mode") or line.startswith("--- /dev/null"):
                current["status"] = "added"
            elif line.startswith("deleted file mode") or line.startswith("+++ /dev/null"):
                current["status"] = "removed"
            elif line.startswith("rename from"):
                current["status"] = "renamed"
            elif line.startswith("@@"):
                in_hunk = True
                current["lines"].append(line)
            continue
        current["lines"].append(line)
    for row in out:
        lines = row.pop("lines")
        while lines and lines[-1] == "":
            lines.pop()
        row["patch"] = "\n".join(lines)
    return [row for row in out if row["path"]]


def _spans(tree: ast.Module) -> list[tuple[int, int]]:
    """(first line, last line) of every definition, innermost first, then of every top-level statement."""
    found: list[tuple[int, int, int]] = []

    def go(node: ast.AST, depth: int) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                first = min([child.lineno] + [decorator.lineno for decorator in child.decorator_list])
                found.append((-depth, first, child.end_lineno or child.lineno))
                go(child, depth + 1)
            elif isinstance(child, ast.stmt):
                go(child, depth)

    go(tree, 1)
    found.sort()
    top = [(node.lineno if not getattr(node, "decorator_list", None) else min([node.lineno] + [d.lineno for d in node.decorator_list]),
            node.end_lineno or node.lineno) for node in tree.body]
    return [(first, last) for _, first, last in found] + top


def narrowed(before: str, after: str, spans: Sequence[tuple[int, int]]) -> tuple[str, str] | None:
    """The smallest definition (or top-level statement) of `before` that holds every changed line, and
    what stands in its place in `after`; None when no single one does. Outside it the two files are
    the same line for line, so the shape of the change is the shape of the change between the two parts."""
    a, b = before.split("\n"), after.split("\n")
    most = min(len(a), len(b))
    front = 0
    while front < most and a[front] == b[front]:
        front += 1
    back = 0
    while back < most and a[len(a) - 1 - back] == b[len(b) - 1 - back]:
        back += 1
    # lines that are the same on both sides of what was put in (an empty line, mostly) can be counted to the front or to the back
    ways = {(front, min(back, most - front)), (min(front, most - back), back)}
    delta = len(b) - len(a)
    for first, last in spans:
        if not any(first - 1 <= ahead and len(a) - behind <= last for ahead, behind in ways):
            continue
        part_before = textwrap.dedent("\n".join(a[first - 1:last]))
        part_after = textwrap.dedent("\n".join(b[first - 1:last + delta]))
        try:
            one, other = ast.parse(part_before), ast.parse(part_after)
        except (SyntaxError, ValueError, RecursionError):
            continue
        if len(one.body) == 1 and len(other.body) == 1 and type(one.body[0]) is type(other.body[0]) \
                and getattr(one.body[0], "name", None) == getattr(other.body[0], "name", None):
            return part_before, part_after
    return None


class Files:
    """The expert-changed files of one task as they were, each read once: its spans and what it holds."""

    def __init__(self, record: Mapping[str, Any]):
        self.repo = record.get("repo", "")
        self.before = {row["path"]: row["before"] for row in record.get("files", [])
                       if not row.get("is_test") and row.get("is_python") and row.get("before") is not None}
        self._read: dict[str, tuple[list[tuple[int, int]], set] | None] = {}

    def read(self, path: str) -> tuple[list[tuple[int, int]], set] | None:
        if path not in self._read:
            try:
                tree = ast.parse(self.before[path])
                self._read[path] = (_spans(tree), fix_shape.atoms(tree))
            except (SyntaxError, ValueError, RecursionError):
                self._read[path] = None
        return self._read[path]


def shape_of_patch(files: Files, diff: str, whole_file: bool = False) -> dict[str, Any]:
    """The shape of what a patch does to the Python that was there, outside the tests; the files it
    adds and the other files it changes are counted beside it. With `whole_file` the two whole files
    are compared, the slow way that needs no narrowing: it has to give the same."""
    changed = [row for row in files_of(diff) if not collector.is_test(files.repo, row["path"])]
    there = [row for row in changed if row["path"].endswith(".py") and row["status"] != "added"]
    out: dict[str, Any] = {"kind": None, "needs": None, "nodes": None,
                           "added_files": sum(1 for row in changed if row["status"] == "added"),
                           "other_files": sum(1 for row in changed if not row["path"].endswith(".py") and row["status"] != "added")}
    if not there:
        return {**out, "shape": NO_PYTHON}
    if len(there) > 1:
        return {**out, "shape": census.SEVERAL_FILES}
    row = there[0]
    if row["status"] != "modified":
        return {**out, "shape": census.A_WHOLE_FILE, "kind": row["status"]}
    if row["path"] not in files.before:
        return {**out, "shape": ELSEWHERE}
    before = files.before[row["path"]]
    try:
        after = repetition.apply_patch(before, row["patch"], [])
    except (ValueError, IndexError) as error:
        return {**out, "shape": NOT_APPLIED, "kind": str(error)[:80]}
    read = files.read(row["path"])
    if read is None:
        return {**out, "shape": fix_shape.UNREADABLE}
    spans, held = read
    if not whole_file:
        parts = narrowed(before, after, spans)
        if parts is not None:
            return {**out, **fix_shape.shape(parts[0], parts[1], held=held)}
        if before.count("\n") > WHOLE_FILE_AT_MOST_LINES:
            return {**out, "shape": NOT_EXAMINED}
    return {**out, **fix_shape.shape(before, after, held=held)}


def smallness(found: Mapping[str, Any]) -> dict[str, bool]:
    """Whether a shape is one small change that could be listed, and whether it is within one
    statement; each also in the strict reading, where a patch that adds any file is ruled out."""
    listed = found["shape"] in fix_shape.SHAPES and fix_shape.can_be_listed(found)
    within = found["shape"] in census.AT_MOST_ONE_STATEMENT
    alone = not found.get("added_files")
    return {"listed": listed, "listed_nothing_added": listed and alone, "one_statement": within, "one_statement_nothing_added": within and alone}


def class_of(found: Mapping[str, Any]) -> str:
    """The class of an expert's fix, for the tables."""
    if found["shape"] in fix_shape.SHAPES and fix_shape.can_be_listed(found):
        return "can be listed"
    if found["shape"] in census.AT_MOST_ONE_STATEMENT:
        return "one statement, not listable"
    if found["shape"] in (fix_shape.ONE_PLACE, fix_shape.SEVERAL_PLACES):
        return found["shape"]
    return census.SEVERAL_FILES


# --------------------------------------------------------------------------- #
# the counts
# --------------------------------------------------------------------------- #
def by_verdicts(expert: Mapping[str, str], resolved: Mapping[str, set[str]]) -> dict[str, Any]:
    """From the verdicts alone: how many submissions resolve a task, by the class of the expert's fix."""
    submissions = sorted(resolved)
    share = {task: sum(1 for name in submissions if task in resolved[name]) / len(submissions) for task in expert} if submissions else {}
    best = max(submissions, key=lambda name: len(resolved[name] & set(expert)), default=None)
    counts = sorted(len(resolved[name] & set(expert)) for name in submissions)
    rows: dict[str, Any] = {}
    for name in CLASSES:
        tasks = [task for task, kind in expert.items() if kind == name]
        rows[name] = {"tasks": len(tasks),
                      "mean_share_of_submissions_that_resolve": round(statistics.fmean(share[task] for task in tasks), 4) if tasks and share else None,
                      "resolved_by_none": sum(1 for task in tasks if share and share[task] == 0),
                      "resolved_by_the_best_submission": sum(1 for task in tasks if best and task in resolved[best])}
    one = [task for task, kind in expert.items() if kind in CLASSES[:2]]
    return {"submissions": len(submissions), "best_submission": best, "best_resolves": counts[-1] if counts else None,
            "middle_submission_resolves": counts[len(counts) // 2] if counts else None, "least": counts[0] if counts else None,
            "tasks_resolved_by_none": sum(1 for task in expert if share and share[task] == 0),
            "by_class_of_the_experts_fix": rows,
            "mean_share_at_most_one_statement": round(statistics.fmean(share[task] for task in one), 4) if one and share else None}


def rule_shapes_track_difficulty(told: Mapping[str, Any], step: float = 0.05) -> dict[str, Any]:
    rows = told["by_class_of_the_experts_fix"]
    chain = [told["mean_share_at_most_one_statement"], rows[fix_shape.SEVERAL_PLACES]["mean_share_of_submissions_that_resolve"],
             rows[census.SEVERAL_FILES]["mean_share_of_submissions_that_resolve"]]
    falls = all(a is not None and b is not None and a - b >= step for a, b in zip(chain, chain[1:]))
    return {"at most one statement, several places, several files": chain, "falls_by_at_least_5_points_each_step": falls}


def passing_patches(records: Mapping[str, Mapping[str, Any]], resolved: Mapping[str, set[str]], proposals: Callable[[str], Mapping[str, str]],
                    check_whole_file: int = 0, progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Every (submission, task) whose patch passed, given its shape. Per task: how many passed, and
    whether any of them is small. `check_whole_file` patches are also compared as whole files."""
    files = {task: Files(record) for task, record in records.items()}
    per_task: dict[str, dict[str, Any]] = {task: {"passing": 0, "shapes": collections.Counter(), "listed": False, "listed_nothing_added": False,
                                                  "one_statement": False, "one_statement_nothing_added": False} for task in records}
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    shapes: collections.Counter = collections.Counter()
    checked, apart = 0, []
    for number, name in enumerate(sorted(resolved)):
        offered = proposals(name)
        for task in sorted(resolved[name]):
            if task not in records or task not in offered:
                continue
            key = (task, hashlib.sha256(offered[task].encode("utf-8", "replace")).hexdigest())
            if key not in seen:
                seen[key] = shape_of_patch(files[task], offered[task])
                if checked < check_whole_file and seen[key]["shape"] in fix_shape.SHAPES:
                    checked += 1
                    slow = shape_of_patch(files[task], offered[task], whole_file=True)
                    if [slow.get(k) for k in ("shape", "kind", "needs", "nodes")] != [seen[key].get(k) for k in ("shape", "kind", "needs", "nodes")]:
                        apart.append(f"{name}/{task}")
            found = seen[key]
            row = per_task[task]
            row["passing"] += 1
            row["shapes"][found["shape"]] += 1
            shapes[found["shape"]] += 1
            for flag, value in smallness(found).items():
                row[flag] = row[flag] or value
        if progress:
            progress(f"{number + 1} submissions, {len(seen)} different passing patches")
    return {"per_task": per_task, "different_passing_patches": len(seen), "passing_patches": sum(shapes.values()), "by_shape": dict(shapes.most_common()),
            "checked_as_whole_files": checked, "the_two_ways_apart": apart}


def summarise(expert: Mapping[str, str], per_task: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    flags = ("listed", "listed_nothing_added", "one_statement", "one_statement_nothing_added")
    rows: dict[str, Any] = {}
    for name in CLASSES:
        tasks = [task for task, kind in expert.items() if kind == name]
        rows[name] = {"tasks": len(tasks), "with_a_passing_patch": sum(1 for task in tasks if per_task[task]["passing"]),
                      **{f"some_passing_patch_{flag}": sum(1 for task in tasks if per_task[task][flag]) for flag in flags}}
    return {"tasks": len(expert), "with_a_passing_patch": sum(1 for task in expert if per_task[task]["passing"]),
            **{f"some_passing_patch_{flag}": sum(1 for task in expert if per_task[task][flag]) for flag in flags},
            "by_class_of_the_experts_fix": rows}


def code_sha256() -> dict[str, str]:
    names = ("canonical/tools/passing_patch_shape_measure_v1.py", "canonical/runtime/fix_shape_v1.py", "canonical/runtime/take_out_v1.py",
             "canonical/tools/fix_shape_census_measure_v1.py", "canonical/tools/expert_fix_repetition_measure_v1.py",
             "canonical/tools/expert_fix_pull_request_collector_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--cache-dir", required=True, type=pathlib.Path, help="where the verdicts and patches are kept")
    parser.add_argument("--fetch", action="store_true", help="fetch the verdicts and patches from GitHub and stop")
    parser.add_argument("--pull-requests-dir", type=pathlib.Path, help="one JSON file per task, as the collector wrote them")
    parser.add_argument("--check-whole-file", type=int, default=150, help="how many patches to compare as whole files as well")
    parser.add_argument("--out", type=pathlib.Path)
    args = parser.parse_args(argv)
    if args.fetch:
        print("FETCHED", json.dumps(fetch(args.cache_dir)), flush=True)
        return 0
    if not args.pull_requests_dir or not args.out:
        parser.error("--pull-requests-dir and --out are needed")

    started = time.time()
    records = {path.stem: json.loads(path.read_text()) for path in sorted(args.pull_requests_dir.glob("*.json"))}
    expert = {task: class_of(census.of_pull_request(record)) for task, record in records.items()}
    print("the experts' fixes by class", dict(collections.Counter(expert.values())), round(time.time() - started, 1), "s", flush=True)
    today, then = verdicts(args.cache_dir, TO_THIS_DAY), verdicts(args.cache_dir, WITH_PATCHES)
    told = by_verdicts(expert, today)
    with_patches = {name: tasks for name, tasks in then.items() if (args.cache_dir / WITH_PATCHES[:10] / name / "all_preds.jsonl").exists()}
    found = passing_patches(records, with_patches, lambda name: patches(args.cache_dir, name), args.check_whole_file,
                            lambda line: print(line, round(time.time() - started, 1), "s", flush=True))
    per_task = found.pop("per_task")
    summary = summarise(expert, per_task)
    record = {
        "schema": SCHEMA, "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expected_before": EXPECTED,
        "from_the_verdicts_alone": {**told, "experiments_commit": TO_THIS_DAY, "rule": rule_shapes_track_difficulty(told)},
        "the_passing_patches": {**found, **summary, "experiments_commit": WITH_PATCHES, "submissions_with_patches": len(with_patches),
                                "by_verdicts_of_those_submissions": by_verdicts(expert, with_patches)},
        "per_task_key": "[class of the expert's fix, passing patches, some passing patch can be listed, the same with nothing added, "
                        "some within one statement, the same with nothing added]",
        "per_task": {task: [expert[task], row["passing"], row["listed"], row["listed_nothing_added"], row["one_statement"],
                            row["one_statement_nothing_added"]] for task, row in per_task.items()},
        "model_calls": 0, "programs_run": 0, "tests_run": 0, "code_sha256": code_sha256(), "seconds": round(time.time() - started, 1),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("WROTE", args.out, record["seconds"], "s", flush=True)
    print(json.dumps({key: value for key, value in summary.items() if key != "by_class_of_the_experts_fix"}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
