#!/usr/bin/env python3
"""What the KIND of a fix, kept from fixes shown once, repairs among bugs it was never shown.

The question
------------
"Let it experience a fix once and it has learned it." Measured on QuixBugs, this tree's memory of
fixes repeats a fix (22 of 22) and repairs a different bug from one in 1 to 3 of 858 pairs. What
it keeps is the fix. `canonical/runtime/edit_kind_learning_v1.py` keeps the kind of change
instead, written from "exactly this" to "this, anywhere". This tool asks how far that goes, on
bugs written by other people that nobody here read before the learner was frozen:

  HumanEvalFix (BigCode, OctoPack 2023): 164 Python functions, each with one bug written in by
  hand, its published fix, and the problem's tests.

For a bug, the learner is shown fixes of OTHER bugs -- never this bug's own -- and proposes
changed programs, best supported first. They are run against the bug's tests one at a time, in
that order, up to a budget. Asked three ways:

  another_benchmark   the 40 QuixBugs fixes only (other authors, other programs)
  all_other_fixes     those and the fixes of the other 163 HumanEvalFix bugs
  learning curve      k of those lessons, drawn at random, for several k

and, as a check on the learner alone (no tests run), where the bug's OWN fix ranks once shown.

What counts
-----------
A candidate counts as a repair when the tests pass twice: in this tree's confined candidate
screen (zygote_worker_pool_v1.screen_python_candidates_cow, unedited) and then in a fresh
interpreter, the way the benchmark's harness runs it. A program that passes its tests is not
therefore right, so every repair is also compared with the published fix: the same program, or
not -- and when not, both are run on inputs the tests do not have (HumanEval+ Mini, written by
other people for these same functions) and their answers compared.

The split is drawn by a seeded draw before anything is run. Bugs in `development` may be read
and the learner changed because of them; bugs in `scored` are the measurement.

Zero model calls. Nothing here gives authority to anything.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import pathlib
import random
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Iterator, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402

SCHEMA = "BRAIN_HUMANEVALFIX_EDIT_KIND_TRANSFER_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

# what the benchmark's harness puts in front of every program (bigcode-evaluation-harness, less numpy)
PRELUDE = ("import math, re, sys, copy, datetime, itertools, collections, heapq, statistics, functools, hashlib, string\n"
           "from typing import *\nfrom collections import *\n")
PROGRAM, TESTS = "prog.py", "test_prog.py"

SPLIT_SEED = 20261111
SCORED = 100                      # bugs drawn for the measurement; the others are for development
READ_BEFORE_THE_DRAW = ("Python/0",)   # looked at while the format was being read: never scored
DEFAULT_BUDGET = 1000             # candidates run against a bug's tests, at most, per question
SCREEN_LIMIT_S = 0.5              # one candidate in the screen
ACCEPT_LIMIT_S = 10               # the harness's own limit, in a fresh interpreter
CHUNK = 40
CURVE_SIZES = (1, 3, 10, 30, 100)
CURVE_SEEDS = 3
RANKS = (1, 10, 100, 1000)


# --------------------------------------------------------------------------- #
# the bugs and the lessons
# --------------------------------------------------------------------------- #
def load_bugs(path: pathlib.Path) -> list[dict[str, Any]]:
    """HumanEvalFix as programs: the declaration and the buggy body; the declaration and the published body."""
    bugs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        last = row["test"].rstrip().split("\n")[-1].strip()
        if last != f"check({row['entry_point']})":
            raise ValueError(f"{row['task_id']}: the tests do not end by calling check on the function")
        bugs.append({"name": row["task_id"], "number": int(row["task_id"].split("/")[1]), "entry": row["entry_point"],
                     "bug_type": row["bug_type"], "buggy": row["declaration"] + row["buggy_solution"],
                     "fixed": row["declaration"] + row["canonical_solution"], "test": row["test"]})
    return bugs


def split(bugs: Sequence[Mapping[str, Any]], *, seed: int = SPLIT_SEED, scored: int = SCORED,
          never_scored: Sequence[str] = READ_BEFORE_THE_DRAW) -> tuple[list[str], list[str]]:
    """(development, scored): the scored names are drawn at random from those nobody read."""
    pool = sorted((b["name"] for b in bugs if b["name"] not in set(never_scored)), key=lambda n: int(n.split("/")[1]))
    drawn = set(random.Random(seed).sample(pool, min(scored, len(pool))))
    order = [b["name"] for b in bugs]
    return [n for n in order if n not in drawn], [n for n in order if n in drawn]


def quixbugs_lessons(root: pathlib.Path) -> dict[str, tuple[str, str]]:
    """The 40 QuixBugs fixes as (buggy program, fixed program), named quixbugs/<program>."""
    from canonical.tools import quixbugs_one_fix_transfer_measure_v1 as bench
    out = {}
    for name in bench.program_names(root):
        buggy = (root / "python_programs" / f"{name}.py").read_text(encoding="utf-8")
        correct = (root / "correct_python_programs" / f"{name}.py").read_text(encoding="utf-8")
        out[f"quixbugs/{name}"] = (buggy, bench.reference_fix(buggy, correct)["fixed_source"])
    return out


def extra_inputs(path: pathlib.Path | None) -> dict[int, dict[str, Any]]:
    """HumanEval+ Mini by problem number: the inputs and the tolerance for numbers."""
    if path is None:
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[int(row["task_id"].split("/")[1])] = {"entry": row["entry_point"], "atol": row.get("atol") or 0,
                                                      "inputs": list(row["base_input"]) + list(row["plus_input"])}
    return out


# --------------------------------------------------------------------------- #
# running a program against its tests
# --------------------------------------------------------------------------- #
def test_file(bug: Mapping[str, Any]) -> str:
    """The bug's tests as a file the screen and pytest both take: the checks, and one test that calls them."""
    lines = bug["test"].rstrip().split("\n")[:-1]
    return PRELUDE + f"from {PROGRAM[:-3]} import *\n" + "\n".join(lines) + f"\n\n\ndef test_check():\n    check({bug['entry']})\n"


def lay_out(bug: Mapping[str, Any], where: pathlib.Path) -> pathlib.Path:
    if where.exists():
        shutil.rmtree(where)
    where.mkdir(parents=True)
    (where / PROGRAM).write_text(PRELUDE + bug["buggy"], encoding="utf-8")
    (where / TESTS).write_text(test_file(bug), encoding="utf-8")
    return where


def screen(where: pathlib.Path, programs: Sequence[str], *, limit_s: float = SCREEN_LIMIT_S) -> int | None:
    """The first of `programs` that passes the tests in this tree's confined candidate screen, or
    None. Raises when the screen does not answer with authority -- nothing is guessed then."""
    from canonical.swe_kernel.zygote_worker_pool_v1 import screen_python_candidates_cow
    if not programs:
        return None
    answer = screen_python_candidates_cow(str(where), PROGRAM, [TESTS], [PRELUDE + p for p in programs], stop_on_first_pass=True,
                                          timeout_s=len(programs) * limit_s + 20.0, per_candidate_timeout_s=limit_s)
    if not (answer.get("ok") and answer.get("screen_authoritative") and answer.get("live_workspace_untouched")):
        raise RuntimeError(f"the candidate screen did not answer with authority: {json.dumps(answer, default=str)[:300]}")
    passing = sorted(int(i) for i in answer.get("passing_indices") or [])
    return passing[0] if passing else None


def accept(bug: Mapping[str, Any], program: str, *, limit_s: float = ACCEPT_LIMIT_S) -> bool:
    """The benchmark's own check: the prelude, the program and the tests in one fresh interpreter;
    it passes when nothing is raised within the limit."""
    with tempfile.TemporaryDirectory(prefix="hef_accept_") as scratch:
        path = pathlib.Path(scratch) / "run.py"
        path.write_text(PRELUDE + program + "\n" + bug["test"] + "\n", encoding="utf-8")
        try:
            done = subprocess.run([sys.executable, "-I", "-B", str(path)], cwd=scratch, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=limit_s)
        except subprocess.TimeoutExpired:
            return False
    return done.returncode == 0


_AGREE = r"""
import copy, json, signal, sys
spec = json.load(open(sys.argv[1]))
class Late(BaseException): pass
def _late(*_): raise Late()
signal.signal(signal.SIGALRM, _late)
def load(text):
    space = {"__name__": "__program__"}
    exec(compile(spec["prelude"] + text, "<program>", "exec"), space)
    return space[spec["entry"]]
def call(function, arguments):
    signal.setitimer(signal.ITIMER_REAL, spec["limit"])
    try:
        return ("value", function(*copy.deepcopy(arguments)))
    except Late:
        return ("late", None)
    except BaseException as error:
        return ("raised", type(error).__name__)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
def same(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b or abs(a - b) <= spec["atol"] or (a != a and b != b)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return type(a) is type(b) and len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b
published, candidate = load(spec["fixed"]), load(spec["candidate"])
used = agree = 0
difference = None
for arguments in spec["inputs"]:
    want = call(published, arguments)
    if want[0] != "value":
        continue
    used += 1
    got = call(candidate, arguments)
    if got[0] == "value" and same(want[1], got[1]):
        agree += 1
    elif difference is None:
        difference = {"input": repr(arguments)[:240], "published": repr(want[1])[:240], "candidate": repr(got)[:240]}
sys.stdout = sys.__stdout__
print("\n@@" + json.dumps({"inputs_used": used, "agree": agree, "first_difference": difference}))
"""


def agreement(bug: Mapping[str, Any], program: str, extra: Mapping[str, Any] | None, *, limit_s: float = 2.0) -> dict[str, Any] | None:
    """The candidate and the published fix on inputs the tests do not have: how many inputs the
    published fix answers, on how many the candidate gives the same answer, and the first on which it does not."""
    if not extra or extra.get("entry") != bug["entry"]:
        return None
    with tempfile.TemporaryDirectory(prefix="hef_agree_") as scratch:
        spec = pathlib.Path(scratch) / "spec.json"
        spec.write_text(json.dumps({"prelude": PRELUDE, "entry": bug["entry"], "fixed": bug["fixed"], "candidate": program,
                                    "inputs": extra["inputs"], "atol": extra["atol"], "limit": limit_s}), encoding="utf-8")
        try:
            done = subprocess.run([sys.executable, "-I", "-B", "-c", _AGREE, str(spec)], cwd=scratch, stdin=subprocess.DEVNULL,
                                  capture_output=True, text=True, timeout=60 + limit_s * 2 * len(extra["inputs"]))
        except subprocess.TimeoutExpired:
            return {"inputs_used": 0, "agree": 0, "first_difference": None, "error": "the comparison did not end"}
    marked = [line for line in done.stdout.splitlines() if line.startswith("@@")]
    if done.returncode != 0 or not marked:
        return {"inputs_used": 0, "agree": 0, "first_difference": None, "error": (done.stderr or done.stdout)[-300:]}
    return json.loads(marked[-1][2:])


# --------------------------------------------------------------------------- #
# one bug, one set of lessons: candidates in order, the tests on each
# --------------------------------------------------------------------------- #
class Bench:
    """One bug with what is already known about its candidates, so that no candidate is run twice."""

    def __init__(self, bug: Mapping[str, Any], check: Callable[[Sequence[str]], int | None],
                 accepted: Callable[[str], bool]) -> None:
        self.bug, self.check, self.accepted = bug, check, accepted
        self.known: dict[str, bool] = {}
        self.compiles: dict[str, bool] = {}
        self.runs = 0
        self.screen_said_pass_fresh_interpreter_said_no = 0

    def in_order(self, ranked: Sequence[tuple[str, float, Any]]) -> Iterator[str]:
        for candidate, _, _ in ranked:
            if candidate not in self.compiles:
                self.compiles[candidate] = kinds.is_a_program(candidate)
            if self.compiles[candidate]:
                yield candidate

    def first_pass(self, ranked: Sequence[tuple[str, float, Any]], budget: int) -> tuple[int | None, str | None, int]:
        """(rank of the first candidate that passes, that candidate, candidates looked at): None when
        none of the first `budget` passes."""
        order = []
        for candidate in self.in_order(ranked):
            order.append(candidate)
            if len(order) >= budget:
                break
        at = 0
        while at < len(order):
            if order[at] in self.known:
                if self.known[order[at]]:
                    return at + 1, order[at], at + 1
                at += 1
                continue
            chunk = []
            for candidate in order[at:]:
                if candidate in self.known:
                    if self.known[candidate]:
                        break
                    continue
                chunk.append(candidate)
                if len(chunk) >= CHUNK:
                    break
            hit = self.check(chunk)
            self.runs += len(chunk) if hit is None else hit + 1
            for index, candidate in enumerate(chunk):
                if hit is None or index < hit:
                    self.known[candidate] = False
            if hit is not None:
                self.known[chunk[hit]] = bool(self.accepted(chunk[hit]))
                if not self.known[chunk[hit]]:
                    self.screen_said_pass_fresh_interpreter_said_no += 1
        return None, None, len(order)


def changed_lines(before: str, after: str) -> dict[str, list[str]]:
    import difflib
    a, b = ast.unparse(ast.parse(before)).split("\n"), after.split("\n")
    removed: list[str] = []
    put_in: list[str] = []
    for tag, a0, a1, b0, b1 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag != "equal":
            removed += [line.strip() for line in a[a0:a1]]
            put_in += [line.strip() for line in b[b0:b1]]
    return {"removed": removed, "put_in": put_in}


def asked(bench: Bench, lessons: kinds.Lessons, votes: Mapping[str, Any], only: Sequence[str], budget: int,
          extra: Mapping[str, Any] | None, *, detail: bool = True) -> dict[str, Any]:
    """One question about one bug: the candidates the lessons in `only` vote for, run in order."""
    bug = bench.bug
    ranked = kinds.ranking(votes, only=only)
    published = ast.unparse(ast.parse(bug["fixed"]))
    place = next((n + 1 for n, candidate in enumerate(bench.in_order(ranked)) if candidate == published), None)
    rank, program, looked_at = bench.first_pass(ranked, budget)
    out: dict[str, Any] = {"lessons": len(only), "candidates": sum(1 for _ in bench.in_order(ranked)),
                           "published_fix_rank": place, "first_pass_rank": rank, "repaired": rank is not None}
    if program is not None:
        out["is_the_published_fix"] = program == published
        if detail:
            row = dict(next(r[2] for r in ranked if r[0] == program))
            strongest = max(row.values(), key=lambda v: v[0])[1]
            out["operator"] = lessons.operators[strongest].shown()
            out["openness"] = lessons.operators[strongest].openness
            out["voted_by"] = sorted(row)[:12]
            out["lines"] = changed_lines(bug["buggy"], program)
            if not out["is_the_published_fix"]:
                out["on_inputs_the_tests_do_not_have"] = agreement(bug, program, extra)
    return out


def one_bug(bug: Mapping[str, Any], lessons: kinds.Lessons, quixbugs_names: Sequence[str], where: pathlib.Path, *,
            budget: int = DEFAULT_BUDGET, extra: Mapping[str, Any] | None = None, curve_sizes: Sequence[int] = CURVE_SIZES,
            curve_seeds: int = CURVE_SEEDS, seed: int = 0,
            check: Callable[[Sequence[str]], int | None] | None = None,
            accepted: Callable[[str], bool] | None = None) -> dict[str, Any]:
    started = time.monotonic()
    lay_out(bug, where)
    check = check or (lambda programs: screen(where, programs))
    accepted = accepted or (lambda program: accept(bug, program))
    out: dict[str, Any] = {"bug_type": bug["bug_type"]}
    # the benchmark has to hold before anything is asked: the bug fails, the published fix passes, both ways
    buggy, fixed = ast.unparse(ast.parse(bug["buggy"])), ast.unparse(ast.parse(bug["fixed"]))
    out["benchmark_holds"] = {"buggy_fails_in_the_screen": check([buggy]) is None, "published_fix_passes_in_the_screen": check([fixed]) == 0,
                              "buggy_fails_in_a_fresh_interpreter": not accepted(bug["buggy"]),
                              "published_fix_passes_in_a_fresh_interpreter": bool(accepted(bug["fixed"]))}
    out["usable"] = all(out["benchmark_holds"].values())
    if not out["usable"]:
        return out
    votes = lessons.votes(bug["buggy"])
    bench = Bench(bug, check, accepted)
    others = [name for name in lessons.lessons if name != bug["name"]]
    # the learner alone: shown this bug's own fix, where does it put it (no test is run for this)
    own = kinds.ranking(votes, only=[bug["name"]])
    everything = kinds.ranking(votes)
    out["own_fix_shown"] = {
        "taught_something": bug["name"] in lessons.lessons,
        "rank_among_its_own_candidates": next((n + 1 for n, c in enumerate(bench.in_order(own)) if c == fixed), None),
        "rank_among_all_candidates": next((n + 1 for n, c in enumerate(bench.in_order(everything)) if c == fixed), None)}
    out["another_benchmark"] = asked(bench, lessons, votes, [n for n in others if n in set(quixbugs_names)], budget, extra)
    out["all_other_fixes"] = asked(bench, lessons, votes, others, budget, extra)
    curve: dict[str, list[dict[str, Any]]] = {}
    for size in curve_sizes:
        if size >= len(others):
            continue
        rows = []
        for draw in range(curve_seeds):
            chosen = random.Random(f"{seed}/{bug['name']}/{size}/{draw}").sample(others, size)
            answer = asked(bench, lessons, votes, chosen, budget, extra, detail=False)
            rows.append({k: answer.get(k) for k in ("candidates", "published_fix_rank", "first_pass_rank", "repaired", "is_the_published_fix")})
        curve[str(size)] = rows
    out["curve"] = curve
    out["candidates_run"] = bench.runs
    out["screen_said_pass_fresh_interpreter_said_no"] = bench.screen_said_pass_fresh_interpreter_said_no
    out["seconds"] = round(time.monotonic() - started, 2)
    return out


# --------------------------------------------------------------------------- #
# the measurement and what it came to
# --------------------------------------------------------------------------- #
def taught(bugs: Sequence[Mapping[str, Any]], quixbugs: Mapping[str, tuple[str, str]]) -> kinds.Lessons:
    lessons = kinds.Lessons()
    for name, (buggy, fixed) in quixbugs.items():
        lessons.learn(name, buggy, fixed)
    for bug in bugs:
        lessons.learn(bug["name"], bug["buggy"], bug["fixed"])
    return lessons


def measure(bugs: Sequence[Mapping[str, Any]], names: Sequence[str], quixbugs: Mapping[str, tuple[str, str]], work: pathlib.Path, *,
            budget: int = DEFAULT_BUDGET, extra: Mapping[int, Mapping[str, Any]] | None = None,
            curve_sizes: Sequence[int] = CURVE_SIZES, curve_seeds: int = CURVE_SEEDS, seed: int = 0,
            check_for: Callable[[Mapping[str, Any], pathlib.Path], Callable[[Sequence[str]], int | None]] | None = None,
            accepted_for: Callable[[Mapping[str, Any]], Callable[[str], bool]] | None = None,
            progress: Callable[[str, Mapping[str, Any], Mapping[str, Any]], None] | None = None) -> dict[str, Any]:
    """Every bug in `names` asked every question. The lessons are the fixes of ALL the bugs given
    and of QuixBugs; a bug's own fix is never among the lessons it is asked with."""
    lessons = taught(bugs, quixbugs)
    by_name = {bug["name"]: bug for bug in bugs}
    per_bug: dict[str, Any] = {}
    for name in names:
        bug = by_name[name]
        where = work / name.replace("/", "_")
        per_bug[name] = one_bug(bug, lessons, list(quixbugs), where, budget=budget, extra=(extra or {}).get(bug["number"]),
                                curve_sizes=curve_sizes, curve_seeds=curve_seeds, seed=seed,
                                check=check_for(bug, where) if check_for else None,
                                accepted=accepted_for(bug) if accepted_for else None)
        shutil.rmtree(where, ignore_errors=True)
        if progress:
            progress(name, per_bug[name], per_bug)
    return {"lessons": {"given": len(lessons.lessons), "from_quixbugs": sum(1 for n in lessons.lessons if n in quixbugs),
                        "taught_nothing": list(lessons.taught_nothing), "operators": len(lessons.operators)},
            "per_bug": per_bug}


def _question(rows: Sequence[Mapping[str, Any]], budget: int) -> dict[str, Any]:
    repaired = [r for r in rows if r.get("repaired")]
    different = [r for r in repaired if not r.get("is_the_published_fix")]
    compared = [r["on_inputs_the_tests_do_not_have"] for r in different if r.get("on_inputs_the_tests_do_not_have")]
    out = {"bugs": len(rows), "repaired": len(repaired),
           "repaired_within": {str(k): sum(1 for r in repaired if r["first_pass_rank"] <= k) for k in RANKS if k <= budget},
           "the_repair_is_the_published_fix": sum(1 for r in repaired if r.get("is_the_published_fix")),
           "the_repair_is_another_program": len(different),
           "of_those_same_answers_on_every_extra_input": sum(1 for c in compared if c.get("inputs_used") and c["agree"] == c["inputs_used"]),
           "of_those_a_different_answer_on_some_extra_input": sum(1 for c in compared if c.get("inputs_used") and c["agree"] < c["inputs_used"]),
           "of_those_not_compared": len(different) - sum(1 for c in compared if c.get("inputs_used")),
           "published_fix_among_the_candidates": sum(1 for r in rows if r.get("published_fix_rank")),
           "published_fix_within": {str(k): sum(1 for r in rows if r.get("published_fix_rank") and r["published_fix_rank"] <= k) for k in RANKS},
           "candidates_median": _median([r.get("candidates", 0) for r in rows])}
    out["repaired_and_right_as_far_as_checked"] = out["the_repair_is_the_published_fix"] + out["of_those_same_answers_on_every_extra_input"]
    return out


def _median(values: Sequence[float]) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def summarise(per_bug: Mapping[str, Mapping[str, Any]], budget: int) -> dict[str, Any]:
    usable = {name: row for name, row in per_bug.items() if row.get("usable")}
    out: dict[str, Any] = {"bugs_asked": len(per_bug), "bugs_usable": len(usable),
                           "not_usable": sorted(name for name, row in per_bug.items() if not row.get("usable"))}
    for question in ("another_benchmark", "all_other_fixes"):
        rows = [row[question] for row in usable.values()]
        out[question] = _question(rows, budget)
        by_type: dict[str, dict[str, int]] = {}
        for row in usable.values():
            cell = by_type.setdefault(row["bug_type"], {"bugs": 0, "repaired": 0, "the_repair_is_the_published_fix": 0,
                                                        "published_fix_among_the_candidates": 0})
            cell["bugs"] += 1
            cell["repaired"] += bool(row[question].get("repaired"))
            cell["the_repair_is_the_published_fix"] += bool(row[question].get("repaired") and row[question].get("is_the_published_fix"))
            cell["published_fix_among_the_candidates"] += bool(row[question].get("published_fix_rank"))
        out[question]["by_bug_type"] = dict(sorted(by_type.items()))
    own = [row["own_fix_shown"] for row in usable.values()]
    out["own_fix_shown"] = {"bugs": len(own), "taught_something": sum(1 for r in own if r["taught_something"]),
                            "first_among_its_own_candidates": sum(1 for r in own if r["rank_among_its_own_candidates"] == 1),
                            "among_all_candidates": sum(1 for r in own if r["rank_among_all_candidates"]),
                            "first_among_all_candidates": sum(1 for r in own if r["rank_among_all_candidates"] == 1),
                            "within_10_among_all_candidates": sum(1 for r in own if r["rank_among_all_candidates"] and r["rank_among_all_candidates"] <= 10)}
    curve: dict[str, Any] = {}
    sizes = sorted({int(size) for row in usable.values() for size in row.get("curve", {})})
    for size in sizes:
        draws = [draw for row in usable.values() for draw in row["curve"].get(str(size), [])]
        if draws:
            curve[str(size)] = {"draws": len(draws), "repaired": sum(1 for d in draws if d["repaired"]),
                                "repaired_share": round(sum(1 for d in draws if d["repaired"]) / len(draws), 4),
                                "the_repair_is_the_published_fix": sum(1 for d in draws if d["repaired"] and d["is_the_published_fix"]),
                                "published_fix_among_the_candidates": sum(1 for d in draws if d["published_fix_rank"])}
    out["curve"] = curve
    out["candidates_run"] = sum(row.get("candidates_run", 0) for row in usable.values())
    out["screen_said_pass_fresh_interpreter_said_no"] = sum(row.get("screen_said_pass_fresh_interpreter_said_no", 0) for row in usable.values())
    out["seconds"] = round(sum(row.get("seconds", 0) for row in usable.values()), 1)
    return out


def code_sha256() -> dict[str, str]:
    files = ("canonical/runtime/edit_kind_learning_v1.py", "canonical/tools/humanevalfix_edit_kind_transfer_measure_v1.py",
             "canonical/swe_kernel/zygote_worker_pool_v1.py", "canonical/runtime/brokered_workspace_execution_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--humanevalfix", required=True, type=pathlib.Path, help="humanevalpack.jsonl, the Python data")
    parser.add_argument("--quixbugs-dir", required=True, type=pathlib.Path)
    parser.add_argument("--extra-inputs", type=pathlib.Path, default=None, help="HumanEvalPlus-Mini.jsonl")
    parser.add_argument("--work-dir", required=True, type=pathlib.Path)
    parser.add_argument("--which", choices=("development", "scored"), default="development")
    parser.add_argument("--bugs", nargs="*", default=None, help="only these, by name")
    parser.add_argument("--shard", default="0/1", help="i/n: every n-th bug of the chosen set, starting at the i-th")
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    parser.add_argument("--curve-seeds", type=int, default=CURVE_SEEDS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--merge", nargs="*", type=pathlib.Path, default=None, help="put shard records together instead of measuring")
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)

    bugs = load_bugs(args.humanevalfix)
    development, scored = split(bugs)
    if args.merge is not None:
        parts = [json.loads(path.read_text()) for path in args.merge]
        per_bug: dict[str, Any] = {}
        for part in parts:
            if any(part[k] != parts[0][k] for k in ("which", "budget", "code_sha256", "benchmark", "lessons", "seed", "curve_seeds")):
                raise SystemExit("the shards were not measured the same way")
            per_bug.update(part["per_bug"])
        record = {k: v for k, v in parts[0].items() if k not in ("per_bug", "summary", "shard", "names")}
        record["names"] = sorted(per_bug, key=lambda n: int(n.split("/")[1]))
        record["per_bug"] = {name: per_bug[name] for name in record["names"]}
        record["summary"] = summarise(record["per_bug"], record["budget"])
        args.out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
        print(json.dumps(record["summary"], indent=1))
        return 0

    chosen = development if args.which == "development" else scored
    index, of = (int(x) for x in args.shard.split("/"))
    names = [name for n, name in enumerate(chosen) if n % of == index]
    if args.bugs is not None:
        names = [name for name in names if name in set(args.bugs)]
    quixbugs = quixbugs_lessons(args.quixbugs_dir)
    extra = extra_inputs(args.extra_inputs)
    record: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "which": args.which, "shard": args.shard, "names": names, "budget": args.budget, "seed": args.seed, "curve_seeds": args.curve_seeds,
        "curve_sizes": list(CURVE_SIZES), "screen_limit_s": SCREEN_LIMIT_S, "accept_limit_s": ACCEPT_LIMIT_S,
        "split": {"seed": SPLIT_SEED, "scored": len(scored), "development": len(development), "never_scored": list(READ_BEFORE_THE_DRAW)},
        "benchmark": {"humanevalfix_sha256": hashlib.sha256(args.humanevalfix.read_bytes()).hexdigest(), "bugs": len(bugs),
                      "extra_inputs_sha256": None if args.extra_inputs is None else hashlib.sha256(args.extra_inputs.read_bytes()).hexdigest(),
                      "quixbugs_fixes": len(quixbugs)},
        "code_sha256": code_sha256(), "model_calls": 0,
    }

    def progress(name: str, row: Mapping[str, Any], so_far: Mapping[str, Any]) -> None:
        a, b = row.get("another_benchmark", {}), row.get("all_other_fixes", {})
        print(f"{name:11s} {row['bug_type']:16s} usable={row.get('usable')} another_benchmark={a.get('first_pass_rank')} "
              f"all_other_fixes={b.get('first_pass_rank')} published={b.get('published_fix_rank')} of {b.get('candidates')} "
              f"runs={row.get('candidates_run')} {row.get('seconds')}s", flush=True)
        record["per_bug"] = dict(so_far)
        args.out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")

    measured = measure(bugs, names, quixbugs, args.work_dir, budget=args.budget, extra=extra, curve_seeds=args.curve_seeds,
                       seed=args.seed, progress=progress)
    record["lessons"] = measured["lessons"]
    record["per_bug"] = measured["per_bug"]
    record["summary"] = summarise(measured["per_bug"], args.budget)
    args.out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print(json.dumps(record["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
