#!/usr/bin/env python3
"""The edit-kind learner on the 40 QuixBugs bugs: the same bugs the tree's own repair solver was measured on.

Like for like
-------------
canonical/verification/QUIXBUGS_REPAIR_SOLVER_20261111_V1.json: the tree's repair solver, not
edited, repairs 5 of the 40 QuixBugs bugs with nothing taught and 6 with every other published fix
taught first. This tool asks the learner of canonical/runtime/edit_kind_learning_v1.py about the
same 40 bugs, with the same tests deciding, and a budget of candidates of the size the solver
spends (about a thousand test runs per bug):

  another_benchmark   lessons: the 164 HumanEvalFix fixes only -- no QuixBugs fix is shown at all
  all_other_fixes     those and the fixes of the other 39 QuixBugs bugs (never the bug's own)

A candidate counts as a repair when the program's tests pass twice: in the tree's confined
candidate screen, and then in the benchmark's own runner (pytest, the same oracle the solver
measurement used). The screen cannot run pytest, so it gets the benchmark's test file untouched
together with a stand-in for the five things that file asks of pytest (use_correct, run_slow,
mark.parametrize, skip, approx) and one test without arguments that runs every case. Whether the
stand-in tells the buggy program from the published fix is checked for every bug before anything
is asked; where it does not, the benchmark's own runner is asked about every candidate instead.

All 40 QuixBugs fixes were read earlier in this work and the learner's limits were chosen with
them in view: this is a comparison on the same bugs, not a score on unseen ones.

Zero model calls. Nothing here gives authority to anything.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import shutil
import sys
import time
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as hef  # noqa: E402
from canonical.tools import quixbugs_one_fix_transfer_measure_v1 as bench  # noqa: E402

SCHEMA = "BRAIN_QUIXBUGS_EDIT_KIND_TRANSFER_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
DEFAULT_BUDGET = 1000
SCREEN_LIMIT_S = 1.5              # one wave of candidates in the screen
ORACLE_LIMIT_S = 8                # the benchmark's own runner, as in the solver measurement
BUDGET_WITHOUT_THE_SCREEN = 150   # where every candidate has to go through the benchmark's own runner
RANKS = (1, 10, 100, 1000)
SCREEN_TEST = "test_screen.py"

# what the benchmark's test files ask of pytest, and nothing more
PYTEST_STAND_IN = '''"""A stand-in for the five things the QuixBugs test files ask of pytest."""
use_correct = False
run_slow = False


class Skipped(Exception):
    pass


def skip(reason=""):
    raise Skipped(reason)


class _Approx:
    def __init__(self, expected, rel=None, abs=None):
        self.expected, self.rel, self.abs = expected, rel, abs

    def __eq__(self, other):
        gap = other - self.expected
        gap = -gap if gap < 0 else gap
        size = -self.expected if self.expected < 0 else self.expected
        if self.abs is not None and self.rel is None:
            return gap <= self.abs
        relative = (1e-6 if self.rel is None else self.rel) * size
        absolute = 1e-12 if self.abs is None else self.abs
        return gap <= (relative if relative > absolute else absolute)

    def __ne__(self, other):
        return not self.__eq__(other)


def approx(expected, rel=None, abs=None):
    return _Approx(expected, rel, abs)


class _Mark:
    def parametrize(self, names, values):
        names = [n.strip() for n in names.split(",")] if isinstance(names, str) else list(names)

        def keep(function):
            function._cases = (names, list(values))
            return function
        return keep


mark = _Mark()
'''

SCREEN_TEST_TEXT = '''"""Every case of the benchmark's own test file, run from one test without arguments."""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for extra in (os.path.join(HERE, "python_testcases"), HERE):
    if extra not in sys.path:
        sys.path.insert(0, extra)
import pytest  # the stand-in beside this file


def _the_benchmarks_tests():
    spec = importlib.util.spec_from_file_location("quixbugs_tests", os.path.join(HERE, "python_testcases", "test_NAME.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_case():
    module = _the_benchmarks_tests()
    ran = 0
    for name, function in sorted(vars(module).items()):
        if not name.startswith("test") or not callable(function):
            continue
        cases = getattr(function, "_cases", None)
        if cases is None:
            runs = [()]
        else:
            names, values = cases
            runs = [tuple(value) if len(names) > 1 else (value,) for value in values]
        for arguments in runs:
            try:
                function(*arguments)
            except pytest.Skipped:
                continue
            ran += 1
    assert ran > 0
'''


# --------------------------------------------------------------------------- #
# one program laid out twice: for the benchmark's own runner, and for the screen
# --------------------------------------------------------------------------- #
def screen_project(root: pathlib.Path, name: str, where: pathlib.Path) -> pathlib.Path:
    """The program with the benchmark's test file untouched, the stand-in, and the one test."""
    made = bench.build_project(root, name, where)
    (made / "conftest.py").unlink()
    (made / "pytest.py").write_text(PYTEST_STAND_IN, encoding="utf-8")
    (made / SCREEN_TEST).write_text(SCREEN_TEST_TEXT.replace("test_NAME.py", f"test_{name}.py"), encoding="utf-8")
    return made


def screen(project: pathlib.Path, name: str, programs: Sequence[str], *, limit_s: float = SCREEN_LIMIT_S) -> int | None:
    """The first of `programs` that passes in the tree's confined candidate screen, or None.
    Raises when the screen does not answer with authority."""
    from canonical.swe_kernel.zygote_worker_pool_v1 import screen_python_candidates_cow
    if not programs:
        return None
    answer = screen_python_candidates_cow(str(project), f"python_programs/{name}.py", [SCREEN_TEST], list(programs), stop_on_first_pass=True,
                                          timeout_s=len(programs) * limit_s + 20.0, per_candidate_timeout_s=limit_s)
    if not (answer.get("ok") and answer.get("screen_authoritative") and answer.get("live_workspace_untouched")):
        raise RuntimeError(f"the candidate screen did not answer with authority: {json.dumps(answer, default=str)[:300]}")
    passing = sorted(int(i) for i in answer.get("passing_indices") or [])
    return passing[0] if passing else None


def one_at_a_time(accepted: Callable[[str], bool]) -> Callable[[Sequence[str]], int | None]:
    """A check for where the screen cannot be used: the benchmark's own runner on each candidate in turn."""
    def check(programs: Sequence[str]) -> int | None:
        for index, program in enumerate(programs):
            if accepted(program):
                return index
        return None
    return check


# --------------------------------------------------------------------------- #
# the lessons, the bugs
# --------------------------------------------------------------------------- #
def bugs_of(root: pathlib.Path, names: Sequence[str] | None = None) -> list[dict[str, Any]]:
    out = []
    for name in names or bench.program_names(root):
        buggy = (root / "python_programs" / f"{name}.py").read_text(encoding="utf-8")
        correct = (root / "correct_python_programs" / f"{name}.py").read_text(encoding="utf-8")
        out.append({"name": f"quixbugs/{name}", "program": name, "entry": name, "buggy": buggy,
                    "fixed": bench.reference_fix(buggy, correct)["fixed_source"], "bug_type": "quixbugs"})
    return out


def taught(root: pathlib.Path, humanevalfix: Sequence[Mapping[str, Any]]) -> kinds.Lessons:
    """Every HumanEvalFix fix and every QuixBugs fix shown once."""
    lessons = kinds.Lessons()
    for bug in humanevalfix:
        lessons.learn(bug["name"], bug["buggy"], bug["fixed"])
    for bug in bugs_of(root):
        lessons.learn(bug["name"], bug["buggy"], bug["fixed"])
    return lessons


# --------------------------------------------------------------------------- #
# one bug
# --------------------------------------------------------------------------- #
def one_bug(root: pathlib.Path, bug: Mapping[str, Any], lessons: kinds.Lessons, work: pathlib.Path, *, budget: int = DEFAULT_BUDGET,
            check: Callable[[Sequence[str]], int | None] | None = None, accepted: Callable[[str], bool] | None = None) -> dict[str, Any]:
    started = time.monotonic()
    name = bug["program"]
    out: dict[str, Any] = {}
    if accepted is None:
        oracle = bench.oracle_for(bench.build_project(root, name, work / "runner"), name, timeout_s=ORACLE_LIMIT_S)
        accepted = lambda program: bool(oracle(program).passed)                   # noqa: E731
    buggy, fixed = ast.unparse(ast.parse(bug["buggy"])), ast.unparse(ast.parse(bug["fixed"]))
    holds = {"buggy_fails_in_the_benchmarks_runner": not accepted(bug["buggy"]), "published_fix_passes_in_the_benchmarks_runner": bool(accepted(bug["fixed"]))}
    usable = all(holds.values())
    through_the_screen = False
    if check is None and usable:
        project = screen_project(root, name, work / "screen")
        try:
            holds["buggy_fails_in_the_screen"] = screen(project, name, [buggy]) is None
            holds["published_fix_passes_in_the_screen"] = screen(project, name, [fixed]) == 0
        except RuntimeError as error:
            holds["buggy_fails_in_the_screen"] = holds["published_fix_passes_in_the_screen"] = False
            holds["screen_error"] = str(error)[:200]
        through_the_screen = bool(holds["buggy_fails_in_the_screen"] and holds["published_fix_passes_in_the_screen"])
        check = (lambda programs: screen(project, name, programs)) if through_the_screen else one_at_a_time(accepted)
    out.update(benchmark_holds=holds, usable=usable, asked_through="the_screen_then_the_benchmarks_runner" if through_the_screen else "the_benchmarks_runner_alone")
    if not usable:
        return out
    if not through_the_screen and check is not None and budget > BUDGET_WITHOUT_THE_SCREEN and "buggy_fails_in_the_screen" in holds:
        budget = BUDGET_WITHOUT_THE_SCREEN
    out["budget"] = budget
    votes = lessons.votes(bug["buggy"])
    asking = hef.Bench(bug, check, accepted)
    others = [lesson for lesson in lessons.lessons if lesson != bug["name"]]
    out["another_benchmark"] = hef.asked(asking, lessons, votes, [lesson for lesson in others if not lesson.startswith("quixbugs/")], budget, None)
    out["all_other_fixes"] = hef.asked(asking, lessons, votes, others, budget, None)
    own = kinds.ranking(votes, only=[bug["name"]])
    out["own_fix_shown"] = {"rank_among_its_own_candidates": next((n + 1 for n, c in enumerate(asking.in_order(own)) if c == fixed), None)}
    out["candidates_run"] = asking.runs
    out["screen_said_pass_runner_said_no"] = asking.screen_said_pass_fresh_interpreter_said_no
    out["seconds"] = round(time.monotonic() - started, 2)
    return out


# --------------------------------------------------------------------------- #
# what it came to, beside the solver
# --------------------------------------------------------------------------- #
def _question(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    repaired = [r for r in rows if r.get("repaired")]
    return {"bugs": len(rows), "repaired": len(repaired),
            "repaired_within": {str(k): sum(1 for r in repaired if r["first_pass_rank"] <= k) for k in RANKS},
            "the_repair_is_the_published_fix": sum(1 for r in repaired if r.get("is_the_published_fix")),
            "the_repair_is_another_program": sum(1 for r in repaired if not r.get("is_the_published_fix")),
            "published_fix_among_the_candidates": sum(1 for r in rows if r.get("published_fix_rank"))}


def summarise(per_bug: Mapping[str, Mapping[str, Any]], solver: Mapping[str, Sequence[str]] | None = None) -> dict[str, Any]:
    usable = {name: row for name, row in per_bug.items() if row.get("usable")}
    out: dict[str, Any] = {"bugs_asked": len(per_bug), "bugs_usable": len(usable), "not_usable": sorted(name for name, row in per_bug.items() if not row.get("usable")),
                           "asked_through_the_benchmarks_runner_alone": sorted(name for name, row in usable.items() if row["asked_through"] != "the_screen_then_the_benchmarks_runner")}
    for question in ("another_benchmark", "all_other_fixes"):
        out[question] = _question([row[question] for row in usable.values()])
        out[question]["which"] = sorted(name for name, row in usable.items() if row[question].get("repaired"))
    out["candidates_run"] = sum(row.get("candidates_run", 0) for row in usable.values())
    out["seconds"] = round(sum(row.get("seconds", 0) for row in usable.values()), 1)
    out["screen_said_pass_runner_said_no"] = sum(row.get("screen_said_pass_runner_said_no", 0) for row in usable.values())
    if solver:
        beside: dict[str, Any] = {}
        for label, names in solver.items():
            theirs = set(names)
            for question in ("another_benchmark", "all_other_fixes"):
                mine = set(out[question]["which"])
                beside[f"{question}__beside__{label}"] = {
                    "the_learner": len(mine), "the_solver": len(theirs), "both": sorted(mine & theirs),
                    "the_learner_alone": sorted(mine - theirs), "the_solver_alone": sorted(theirs - mine),
                    "neither": len(per_bug) - len(mine | theirs)}
        out["beside_the_trees_repair_solver"] = beside
    return out


def solver_record(path: pathlib.Path) -> dict[str, list[str]]:
    """What the tree's repair solver repaired on the same bugs, from its record."""
    summary = json.loads(path.read_text())["summary"]
    nothing = sorted(summary["empty_memory"]["which"])
    taught_first = sorted(set(nothing) | set(summary["other_fixes"]["repaired_from_memory"]))
    return {"the_solver_with_nothing_taught": nothing, "the_solver_with_all_other_fixes_taught_first": taught_first}


def code_sha256() -> dict[str, str]:
    files = ("canonical/runtime/edit_kind_learning_v1.py", "canonical/tools/quixbugs_edit_kind_transfer_measure_v1.py",
             "canonical/tools/humanevalfix_edit_kind_transfer_measure_v1.py", "canonical/tools/quixbugs_one_fix_transfer_measure_v1.py",
             "canonical/swe_kernel/zygote_worker_pool_v1.py", "canonical/runtime/brokered_workspace_execution_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--quixbugs-dir", required=True, type=pathlib.Path)
    parser.add_argument("--humanevalfix", required=True, type=pathlib.Path, help="humanevalpack.jsonl: its fixes are the lessons from another benchmark")
    parser.add_argument("--solver-record", type=pathlib.Path, default=ROOT / "canonical/verification/QUIXBUGS_REPAIR_SOLVER_20261111_V1.json")
    parser.add_argument("--work-dir", required=True, type=pathlib.Path)
    parser.add_argument("--programs", nargs="*", default=None)
    parser.add_argument("--shard", default="0/1")
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    parser.add_argument("--merge", nargs="*", type=pathlib.Path, default=None)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    solver = solver_record(args.solver_record) if args.solver_record and args.solver_record.is_file() else None

    if args.merge is not None:
        parts = [json.loads(path.read_text()) for path in args.merge]
        if any(part[k] != parts[0][k] for part in parts for k in ("budget", "code_sha256", "benchmark", "lessons")):
            raise SystemExit("the shards were not measured the same way")
        per_bug: dict[str, Any] = {}
        for part in parts:
            per_bug.update(part["per_bug"])
        record = {k: v for k, v in parts[0].items() if k not in ("per_bug", "summary", "shard", "names")}
        record["per_bug"] = dict(sorted(per_bug.items()))
        record["summary"] = summarise(record["per_bug"], solver)
        args.out.write_text(json.dumps(record, indent=1) + "\n")
        print(json.dumps(record["summary"], indent=1))
        return 0

    humanevalfix = hef.load_bugs(args.humanevalfix)
    lessons = taught(args.quixbugs_dir, humanevalfix)
    index, of = (int(x) for x in args.shard.split("/"))
    every = bugs_of(args.quixbugs_dir, args.programs)
    chosen = [bug for n, bug in enumerate(every) if n % of == index]
    record: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "shard": args.shard, "names": [bug["program"] for bug in chosen], "budget": args.budget,
        "budget_where_the_screen_cannot_be_used": BUDGET_WITHOUT_THE_SCREEN, "screen_limit_s": SCREEN_LIMIT_S, "oracle_limit_s": ORACLE_LIMIT_S,
        "benchmark": {"quixbugs_sha256": bench.benchmark_sha256(args.quixbugs_dir, bench.program_names(args.quixbugs_dir)), "humanevalfix_sha256": hashlib.sha256(args.humanevalfix.read_bytes()).hexdigest()},
        "lessons": {"given": len(lessons.lessons), "from_humanevalfix": sum(1 for n in lessons.lessons if not n.startswith("quixbugs/")),
                    "from_quixbugs": sum(1 for n in lessons.lessons if n.startswith("quixbugs/")), "taught_nothing": list(lessons.taught_nothing),
                    "operators": len(lessons.operators)},
        "code_sha256": code_sha256(), "model_calls": 0, "per_bug": {},
    }
    for bug in chosen:
        row = one_bug(args.quixbugs_dir, bug, lessons, args.work_dir / bug["program"], budget=args.budget)
        shutil.rmtree(args.work_dir / bug["program"], ignore_errors=True)
        record["per_bug"][bug["program"]] = row
        a, b = row.get("another_benchmark", {}), row.get("all_other_fixes", {})
        print(f"{bug['program']:28s} usable={row['usable']} through={row['asked_through'][:10]} another_benchmark={a.get('first_pass_rank')} "
              f"all_other_fixes={b.get('first_pass_rank')} published={b.get('published_fix_rank')} of {b.get('candidates')} runs={row.get('candidates_run')} {row.get('seconds')}s", flush=True)
        args.out.write_text(json.dumps(record, indent=1) + "\n")
    record["summary"] = summarise(record["per_bug"], solver)
    args.out.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
