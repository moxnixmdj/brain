#!/usr/bin/env python3
"""Bugs one after another, from an empty memory: does a repair help with the next bug?

The owner's claim, where it can be true: once the agent has done a thing it has learned it. Here
the things are repairs. The HumanEvalFix bugs the edit-kind learner and the tree's repair solver
were each measured on come one after another, in an order drawn by a seed. The memory is empty at
the first bug. On every bug the learner is asked first -- the candidates that the lessons kept so
far vote for, best first, at most 200 of them run against the bug's tests -- and when none passes,
the solver's search is what is left. (The solver's outcome on a bug is read from its record: it
was taught nothing there, so it does the same whenever it meets the bug.) What is done after the
bug is the arm:

  own        the repair that was made -- the learner's, else the solver's -- is kept as a lesson
             at once, when it changed one line. A repair that rewrites several lines is what the
             solver writes when it restates the constants of the tests; it is not kept.
  backwards  the same, each repair kept the wrong way round (from the repaired program to the
             buggy one): a memory of the same size, read off the same programs, that holds no fix.
  shown      the published fix is shown after the bug, repaired or not: what an expert's answer,
             given once, adds to what the system keeps of its own.

Beside them stand `cold`, the solver alone, and `cache`, a memory that can only give back the
repair of a program it has met: on a bug met for the first time it has nothing to give.

After the last bug every bug comes once more (`on_return`). That is the part of the claim a cache
satisfies as well.

The record ends with the verdict of the tree's own ruler for "it learned"
(canonical/tools/learning_claim_adjudicator_v1.py), which asks for exactly these four arms on the
same tasks, with cost and success kept apart. Success there is the strict one: the repair is the
published fix, or it answers like the published fix on inputs the tests do not have. Neither the
published fix nor those inputs are used by the `own` and `backwards` arms for anything but that
judgement.

Cost is counted in runs of a bug's tests: one to see the bug fail, one per candidate the learner
runs, one more in a fresh interpreter for a candidate that passes, and the processes the solver
starts when it is its turn. A bug on which the solver was stopped at its wall limit has no such
count; it stays in the counts of repairs and is left out of the costs.

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
import statistics
import sys
import time
from typing import Any, Callable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as hef  # noqa: E402
from canonical.tools import humanevalfix_repair_solver_measure_v1 as solver_measure  # noqa: E402
from canonical.tools import learning_claim_adjudicator_v1 as ruler  # noqa: E402

SCHEMA = "BRAIN_HUMANEVALFIX_EXPERIENCE_STREAM_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
ORDER_SEED = 20261112
LEARNER_BUDGET = hef.CURVE_BUDGET      # 200: the budget of the learning-curve draws, fixed before any scored bug was run
ARMS = ("own", "backwards", "shown")
RETURNING = ("own", "shown")           # the arms asked again after the last bug
PARTS = 4
RANKS = (1, 10, 100, 200)
SEE_IT_FAIL = 1                        # one run of the tests to see the bug fail
CONFIRM = 1                            # one run in a fresh interpreter for a candidate that passed the screen


# --------------------------------------------------------------------------- #
# the order, and what counts as one line
# --------------------------------------------------------------------------- #
def stream_order(names: Sequence[str], seed: int = ORDER_SEED) -> list[str]:
    pool = sorted(names, key=lambda n: int(n.split("/")[1]))
    return random.Random(seed).sample(pool, len(pool))


def one_line(lines: Mapping[str, Sequence[str]] | None) -> bool:
    """One line for another, one line put in, or one line taken out -- of the program as written out."""
    if not lines:
        return False
    removed, put_in = list(lines.get("removed") or []), list(lines.get("put_in") or [])
    return len(removed) <= 1 and len(put_in) <= 1 and bool(removed or put_in)


def without_prelude(text: str) -> str | None:
    """A program the solver left on disk, written out without the imports the bench puts before every program."""
    try:
        tree, prelude = ast.parse(text), ast.parse(hef.PRELUDE)
    except (SyntaxError, ValueError):
        return None
    head = len(prelude.body)
    if [ast.dump(n) for n in tree.body[:head]] == [ast.dump(n) for n in prelude.body]:
        tree.body = tree.body[head:]
    return ast.unparse(tree)


# --------------------------------------------------------------------------- #
# the solver: its record, and its program when a lesson is to be made of it
# --------------------------------------------------------------------------- #
class Solver:
    """What the tree's repair solver does on a bug. With a record, the record is what it did; the
    program it left is not in the record, so when a lesson is to be made of it the solver is run on
    the bug once more, and the program is taken only if it changes the lines the record names.
    Without a record the solver is run when the bug comes."""

    def __init__(self, record: Mapping[str, Any] | None, work: pathlib.Path, kept: pathlib.Path, *,
                 extra: Mapping[int, Mapping[str, Any]] | None = None, timeout_s: int = solver_measure.DEFAULT_TIMEOUT_S,
                 wall_limit_s: int = solver_measure.DEFAULT_WALL_LIMIT_S,
                 run: Callable[..., dict[str, Any]] = solver_measure.one_bug) -> None:
        self.rows: dict[str, dict[str, Any]] = {name: dict(row) for name, row in ((record or {}).get("per_bug") or {}).items()}
        self.from_the_record = set(self.rows)
        self.work, self.kept, self.extra = work, kept, dict(extra or {})
        self.timeout_s, self.wall_limit_s, self.run = timeout_s, wall_limit_s, run
        self.runs = 0
        self.not_as_recorded: list[str] = []

    def _saved(self, name: str) -> pathlib.Path:
        return self.kept / (name.replace("/", "_") + ".json")

    def _run(self, bug: Mapping[str, Any]) -> dict[str, Any]:
        name = bug["name"]
        where = self.work / ("solver_" + name.replace("/", "_"))
        row = self.run(bug, where, timeout_s=self.timeout_s, wall_limit_s=self.wall_limit_s, extra=self.extra.get(bug["number"]))
        self.runs += 1
        program = None
        target = where / solver_measure.PROJECT / hef.PROGRAM
        if row.get("repaired") and target.is_file():
            program = without_prelude(target.read_text(encoding="utf-8"))
        shutil.rmtree(where, ignore_errors=True)
        saved = {"name": name, "program": program, "row": row}
        self.kept.mkdir(parents=True, exist_ok=True)
        scratch = self._saved(name).with_suffix(f".{os.getpid()}.tmp")
        scratch.write_text(json.dumps(saved), encoding="utf-8")
        os.replace(scratch, self._saved(name))
        return saved

    def _had(self, bug: Mapping[str, Any]) -> dict[str, Any]:
        path = self._saved(bug["name"])
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
        return self._run(bug)

    def outcome(self, bug: Mapping[str, Any]) -> dict[str, Any]:
        name = bug["name"]
        if name not in self.rows:
            self.rows[name] = dict(self._had(bug)["row"])
        return self.rows[name]

    def program(self, bug: Mapping[str, Any]) -> str | None:
        """The repaired program, without the prelude; None when the solver did not repair the bug, or
        when run once more it did not change the lines its record names."""
        row = self.outcome(bug)
        if not row.get("repaired"):
            return None
        had = self._had(bug)
        if had.get("program") is None or (had["row"].get("lines") != row.get("lines")):
            if bug["name"] not in self.not_as_recorded:
                self.not_as_recorded.append(bug["name"])
            return None
        return had["program"]


def cost_of(row: Mapping[str, Any]) -> int | None:
    """The processes the solver started on a bug: None when it was stopped at its wall limit or failed."""
    started = row.get("processes_started")
    return int(started) if isinstance(started, int) and row.get("finished") else None


# --------------------------------------------------------------------------- #
# one bug, one memory
# --------------------------------------------------------------------------- #
def judged(bench: hef.Bench, program: str, extra: Mapping[str, Any] | None, known: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """For a program that passes the bug's tests: is it the published fix, and if not, does it answer
    like the published fix on inputs the tests do not have. Used for judging only."""
    if program not in known:
        bug = bench.bug
        published = kinds.same_program(program, bug["fixed"])
        compared = None if published else hef.agreement(bug, program, extra)
        right = published or bool(compared and compared.get("inputs_used") and compared["agree"] == compared["inputs_used"])
        known[program] = {"is_the_published_fix": bool(published), "right_as_far_as_checked": bool(right)}
        if compared is not None:
            known[program]["on_inputs_the_tests_do_not_have"] = {k: compared.get(k) for k in ("inputs_used", "agree")}
    return known[program]


def ask_the_learner(bench: hef.Bench, memory: kinds.Lessons, budget: int) -> tuple[dict[str, Any], str | None]:
    """The candidates the lessons vote for, best first, at most `budget` run against the tests."""
    votes = memory.votes(bench.bug["buggy"]) if memory.operators else {}
    ranked = kinds.ranking(votes)
    rank, program, looked_at = bench.first_pass(ranked, budget)
    out = {"candidates": sum(1 for _ in bench.in_order(ranked)), "tried": rank if rank is not None else looked_at,
           "repaired": rank is not None, "rank": rank}
    if program is not None:
        out["lines"] = hef.changed_lines(bench.bug["buggy"], program)
    return out, program


def keep(arm: str, memory: kinds.Lessons, bench: hef.Bench, by: str | None, program: str | None,
         lines: Mapping[str, Sequence[str]] | None, solver: Solver) -> dict[str, Any]:
    """What the arm keeps after a bug. Returns what was kept, or why nothing was."""
    bug = bench.bug
    if arm == "shown":
        gave = memory.learn(bug["name"], bug["buggy"], bug["fixed"])
        return {"kept": gave > 0, "what": "the published fix", "operators": gave}
    if by is None:
        return {"kept": False, "why_not": "nothing was repaired"}
    if not one_line(lines):
        return {"kept": False, "why_not": "the repair changed more than one line"}
    if by == "solver":
        program = solver.program(bug)
        if program is None or not kinds.is_a_program(program) or not bench.accepted(program):
            return {"kept": False, "why_not": "the solver's program could not be had again as recorded"}
    assert program is not None
    before, after = (program, bug["buggy"]) if arm == "backwards" else (bug["buggy"], program)
    gave = memory.learn(bug["name"], before, after)
    if not gave:
        return {"kept": False, "why_not": "the change could not be read as an operator"}
    return {"kept": True, "what": f"the repair made by the {by}" + (", the wrong way round" if arm == "backwards" else ""), "operators": gave}


def meet(arm: str, memory: kinds.Lessons, bench: hef.Bench, solved: Mapping[str, Any], solver: Solver, extra: Mapping[str, Any] | None,
         known: dict[str, dict[str, Any]], budget: int, *, learn: bool = True) -> dict[str, Any]:
    """One bug in one arm: the learner first, the solver's outcome behind it, then what the arm keeps."""
    row: dict[str, Any] = {"lessons_before": len(memory.lessons), "operators_before": len(memory.operators)}
    learner, program = ask_the_learner(bench, memory, budget)
    row["learner"] = learner
    solver_cost = cost_of(solved)
    lines = None
    if program is not None:
        verdict = judged(bench, program, extra, known)
        learner.update(verdict)
        by, right, lines = "learner", verdict["right_as_far_as_checked"], learner["lines"]
        runs: int | None = SEE_IT_FAIL + learner["tried"] + CONFIRM
    else:
        by = "solver" if solved.get("repaired") else None
        right = bool(by and solved.get("right_as_far_as_checked"))
        lines = solved.get("lines") if by else None
        runs = None if solver_cost is None else SEE_IT_FAIL + learner["tried"] + solver_cost
    row.update(repaired=by is not None, repaired_by=by, right_as_far_as_checked=bool(right), test_runs=runs)
    if learn:
        row["kept"] = keep(arm, memory, bench, by, program, lines, solver)
    return row


# --------------------------------------------------------------------------- #
# the stream
# --------------------------------------------------------------------------- #
def run_stream(bugs: Mapping[str, Mapping[str, Any]], order: Sequence[str], solver: Solver, work: pathlib.Path, *,
               arms: Sequence[str] = ARMS, budget: int = LEARNER_BUDGET, extra: Mapping[int, Mapping[str, Any]] | None = None,
               check_for: Callable[[Mapping[str, Any], pathlib.Path], Callable[[Sequence[str]], int | None]] | None = None,
               accepted_for: Callable[[Mapping[str, Any]], Callable[[str], bool]] | None = None,
               progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """Every bug of `order` once, in every arm, each arm with a memory of its own that is empty at
    the first bug; then every bug once more in the returning arms. One bench per bug is shared by
    the arms, so that no candidate is run twice; what an arm is charged is counted, not timed."""
    extra = dict(extra or {})
    memories = {arm: kinds.Lessons() for arm in arms}
    benches: dict[str, hef.Bench] = {}
    known: dict[str, dict[str, dict[str, Any]]] = {}
    met: dict[str, bool] = {}                  # the cache arm: a program met -> did the solver leave a repair of it
    out: dict[str, Any] = {"order": list(order), "arms": {arm: {} for arm in arms}, "cold": {}, "cache": {}, "not_usable": []}

    def bench_of(bug: Mapping[str, Any]) -> hef.Bench:
        name = bug["name"]
        if name not in benches:
            where = work / name.replace("/", "_")
            hef.lay_out(bug, where)
            check = check_for(bug, where) if check_for else (lambda programs, where=where: hef.screen(where, programs))
            accepted = accepted_for(bug) if accepted_for else (lambda program, bug=bug: hef.accept(bug, program))
            benches[name] = hef.Bench(bug, check, accepted)
            known[name] = {}
        return benches[name]

    for position, name in enumerate(order, 1):
        bug = bugs[name]
        bench = bench_of(bug)
        buggy, fixed = ast.unparse(ast.parse(bug["buggy"])), ast.unparse(ast.parse(bug["fixed"]))
        if not (bench.check([buggy]) is None and bench.check([fixed]) == 0):
            out["not_usable"].append(name)
            continue
        solved = solver.outcome(bug)
        cold = {"position": position, "bug_type": bug["bug_type"], "repaired": bool(solved.get("repaired")),
                "right_as_far_as_checked": bool(solved.get("repaired") and solved.get("right_as_far_as_checked")),
                "test_runs": cost_of(solved), "one_line": one_line(solved.get("lines")) if solved.get("repaired") else None}
        out["cold"][name] = cold
        key = kinds.key(bug["buggy"])
        out["cache"][name] = dict(cold, hit=key in met)       # a first meeting: nothing to give back
        met[key] = bool(solved.get("repaired"))
        for arm in arms:
            row = meet(arm, memories[arm], bench, solved, solver, extra.get(bug["number"]), known[name], budget)
            row.update(position=position, bug_type=bug["bug_type"])
            out["arms"][arm][name] = row
        if progress:
            progress({"position": position, "name": name, "cold": cold, "so_far": out, **{arm: out["arms"][arm][name] for arm in arms}})

    # every bug once more, with what the memory holds after the last bug
    for arm in arms:
        if arm not in RETURNING:
            continue
        for name in order:
            if name in out["not_usable"]:
                continue
            bug = bugs[name]
            row = meet(arm, memories[arm], benches[name], solver.outcome(bug), solver, extra.get(bug["number"]), known[name], budget, learn=False)
            out["arms"][arm][name]["on_return"] = {k: row[k] for k in ("repaired", "repaired_by", "right_as_far_as_checked", "test_runs")} | {
                "rank": row["learner"]["rank"], "candidates": row["learner"]["candidates"]}
        if progress:
            progress({"returned": arm, "so_far": out})
    for name in order:
        if name in out["not_usable"]:
            continue
        hit = met.get(kinds.key(bugs[name]["buggy"]), False)
        cold = out["cold"][name]
        out["cache"][name]["on_return"] = {"hit": hit, "repaired": cold["repaired"], "right_as_far_as_checked": cold["right_as_far_as_checked"],
                                           "test_runs": SEE_IT_FAIL + CONFIRM if hit else cold["test_runs"]}
    out["memories"] = {arm: {"lessons": len(m.lessons), "operators": len(m.operators), "taught_nothing": list(m.taught_nothing)} for arm, m in memories.items()}
    out["lessons_evidence_sha256"] = {arm: hashlib.sha256(json.dumps([[n, sorted(t for t, names in m.given_by.items() if n in names)] for n in m.lessons]).encode()).hexdigest()
                                      for arm, m in memories.items()}
    out["solver_runs_made_here"] = solver.runs
    out["solver_program_not_as_recorded"] = list(solver.not_as_recorded)
    out["candidates_run"] = sum(b.runs for b in benches.values())
    out["screen_said_pass_fresh_interpreter_said_no"] = sum(b.screen_said_pass_fresh_interpreter_said_no for b in benches.values())
    return out


# --------------------------------------------------------------------------- #
# what it came to
# --------------------------------------------------------------------------- #
def _mean(values: Sequence[float]) -> float | None:
    return round(statistics.fmean(values), 2) if values else None


def _median(values: Sequence[float]) -> float | None:
    return float(statistics.median(values)) if values else None


def _counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    costs = [row["test_runs"] for row in rows if row.get("test_runs") is not None]
    out = {"bugs": len(rows), "repaired": sum(1 for r in rows if r.get("repaired")),
           "right_as_far_as_checked": sum(1 for r in rows if r.get("right_as_far_as_checked")),
           "bugs_with_a_cost": len(costs), "test_runs_mean": _mean(costs), "test_runs_median": _median(costs), "test_runs_in_all": sum(costs)}
    if rows and "repaired_by" in rows[0]:
        out["by_the_learner"] = sum(1 for r in rows if r.get("repaired_by") == "learner")
        out["by_the_solver"] = sum(1 for r in rows if r.get("repaired_by") == "solver")
        out["by_the_learner_and_right"] = sum(1 for r in rows if r.get("repaired_by") == "learner" and r.get("right_as_far_as_checked"))
        ranks = [rank for rank in ((r["learner"] if "learner" in r else r).get("rank") for r in rows) if rank is not None]
        out["learner_rank_median"] = _median(ranks)
        out["learner_repaired_within"] = {str(k): sum(1 for rank in ranks if rank <= k) for k in RANKS}
    return out


def _parts(rows: Sequence[Mapping[str, Any]], parts: int) -> list[dict[str, Any]]:
    rows = sorted(rows, key=lambda r: r["position"])
    size = max(1, -(-len(rows) // parts))
    out = []
    for at in range(0, len(rows), size):
        part = rows[at:at + size]
        cell = {"positions": [part[0]["position"], part[-1]["position"]], **_counts(part)}
        if "lessons_before" in part[0]:
            cell["lessons_at_its_first_bug"] = part[0]["lessons_before"]
        out.append(cell)
    return out


def summarise(stream: Mapping[str, Any], parts: int = PARTS) -> dict[str, Any]:
    usable = [name for name in stream["order"] if name in stream["cold"]]       # a stream that has not ended: the bugs met so far
    out: dict[str, Any] = {"bugs_in_the_order": len(stream["order"]), "bugs_met": len(usable) + len(stream["not_usable"]), "usable": len(usable),
                           "not_usable": list(stream["not_usable"])}
    for label in ("cold", "cache"):
        rows = [stream[label][name] for name in usable]
        out[label] = {**_counts(rows), "by_part": _parts(rows, parts)}
    again = [dict(r["on_return"], position=r["position"]) for r in (stream["cache"][name] for name in usable) if "on_return" in r]
    if again:
        out["cache"]["on_return"] = {**_counts(again), "hits": sum(1 for r in again if r["hit"])}
    out["cold"]["repairs_that_changed_one_line"] = sum(1 for name in usable if stream["cold"][name].get("one_line"))
    for arm, per_bug in stream["arms"].items():
        rows = [per_bug[name] for name in usable if name in per_bug]
        cell = {**_counts(rows), "by_part": _parts(rows, parts)}
        kept = [r for r in rows if r.get("kept", {}).get("kept")]
        cell["lessons_kept"] = len(kept)
        if arm != "shown":
            cell["lessons_kept_from_a_repair_that_is_not_right_as_far_as_checked"] = sum(1 for r in kept if not r["right_as_far_as_checked"])
            cell["lessons_kept_made_by"] = {who: sum(1 for r in kept if r["repaired_by"] == who) for who in ("learner", "solver")}
        why: dict[str, int] = {}
        for r in rows:
            reason = r.get("kept", {}).get("why_not")
            if reason:
                why[reason] = why.get(reason, 0) + 1
        cell["not_kept_because"] = dict(sorted(why.items()))
        again = [dict(r["on_return"], position=r["position"]) for r in rows if "on_return" in r]
        if again:
            had_a_lesson = [dict(r["on_return"]) for r in rows if "on_return" in r and r.get("kept", {}).get("kept")]
            cell["on_return"] = {**_counts(again),
                                 "bugs_whose_own_lesson_was_kept": len(had_a_lesson),
                                 "of_those_repaired_by_the_first_candidate": sum(1 for r in had_a_lesson if r.get("rank") == 1),
                                 "repaired_on_return_and_not_at_first": sum(1 for r in rows if "on_return" in r and r["on_return"]["repaired"] and not r["repaired"]),
                                 "repaired_at_first_and_not_on_return": sum(1 for r in rows if "on_return" in r and r["repaired"] and not r["on_return"]["repaired"])}
        out[arm] = cell
    return out


def the_rulers_verdict(stream: Mapping[str, Any], *, scorer_sha256: str, warm: str = "own", placebo: str = "backwards") -> dict[str, Any]:
    """The four arms the tree's ruler asks for, on the bugs every arm has a measured cost for, in the
    order they came. Success is `right_as_far_as_checked`. The ruler's thresholds are its own."""
    if warm not in stream["arms"] or placebo not in stream["arms"]:
        return {"verdict": "NOT_ASKED", "reason": f"the ruler needs the arms {warm!r} and {placebo!r}"}
    rows = {"cold": stream["cold"], "cache_only": stream["cache"], "warm": stream["arms"][warm], "random": stream["arms"][placebo]}
    usable = [name for name in stream["order"] if name in stream["cold"]]
    tasks = [name for name in usable if all(rows[arm][name].get("test_runs") is not None for arm in rows)]
    left_out = [name for name in usable if name not in tasks]

    def arm(per_bug: Mapping[str, Mapping[str, Any]]) -> ruler.Arm:
        return ruler.Arm(tuple(float(per_bug[name]["test_runs"]) for name in tasks),
                         tuple(bool(per_bug[name]["right_as_far_as_checked"]) for name in tasks), tuple(tasks))

    again = [name for name in tasks if stream["arms"][warm][name].get("on_return", {}).get("test_runs") is not None]
    experiment = ruler.Experiment(
        held_out_kind="a HumanEvalFix bug met for the first time",
        seen_kinds=("the HumanEvalFix bugs met earlier in the same stream",),
        task_ids=tuple(tasks), cost_unit="runs of the bug's tests", arms={label: arm(per_bug) for label, per_bug in rows.items()},
        demonstration_evidence_hash=stream["lessons_evidence_sha256"][warm], held_out_scorer_hash=scorer_sha256,
        verifier_author="the authors of HumanEvalFix (tests, published fixes) and of HumanEval+ (the inputs the tests do not have)",
        producer_id="this tree: the edit-kind learner in front of its repair solver",
        source_kind_costs_before=tuple(float(stream["arms"][warm][name]["test_runs"]) for name in again),
        source_kind_costs_after=tuple(float(stream["arms"][warm][name]["on_return"]["test_runs"]) for name in again))
    report = ruler.adjudicate(experiment)
    return {"ruler": "canonical/tools/learning_claim_adjudicator_v1.py", "thresholds": dict(ruler.PREREGISTRATION["thresholds"]),
            "arms_given": {"cold": "the solver alone", "warm": f"the arm {warm!r}", "cache_only": "a memory that gives back the repair of a program it has met",
                           "random": f"the arm {placebo!r}"},
            "what_a_kind_is_here": "one bug. The ruler's question is about a new KIND of task; these are new bugs of one benchmark, six bug types among them all. "
                                   "A pass here would be transfer to new bugs of a known kind, not to a new kind.",
            "tasks": len(tasks), "left_out_for_want_of_a_measured_cost": left_out, "report": report}


def code_sha256() -> dict[str, str]:
    files = ("canonical/tools/humanevalfix_experience_stream_measure_v1.py", "canonical/tools/humanevalfix_edit_kind_transfer_measure_v1.py",
             "canonical/tools/humanevalfix_repair_solver_measure_v1.py", "canonical/tools/learning_claim_adjudicator_v1.py",
             "canonical/runtime/edit_kind_learning_v1.py", "canonical/runtime/bound_capabilities/python_repair_apply_verified_v1.py",
             "canonical/swe_kernel/zygote_worker_pool_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--humanevalfix", required=True, type=pathlib.Path)
    parser.add_argument("--extra-inputs", type=pathlib.Path, default=None)
    parser.add_argument("--solver-record", type=pathlib.Path, default=None, help="the solver's record on these bugs; without it the solver is run when a bug comes")
    parser.add_argument("--solver-programs", required=True, type=pathlib.Path, help="where the programs the solver left are kept between runs")
    parser.add_argument("--which", choices=("development", "scored"), default="scored")
    parser.add_argument("--order-seed", type=int, default=ORDER_SEED)
    parser.add_argument("--first", type=int, default=None, help="only the first so many bugs of the order")
    parser.add_argument("--arms", nargs="*", default=list(ARMS), choices=ARMS)
    parser.add_argument("--budget", type=int, default=LEARNER_BUDGET)
    parser.add_argument("--work-dir", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)

    bugs = hef.load_bugs(args.humanevalfix)
    development, scored = hef.split(bugs)
    order = stream_order(development if args.which == "development" else scored, args.order_seed)
    if args.first is not None:
        order = order[:args.first]
    extra = hef.extra_inputs(args.extra_inputs)
    record = json.loads(args.solver_record.read_text()) if args.solver_record else None
    solver = Solver(record, args.work_dir, args.solver_programs, extra=extra,
                    timeout_s=(record or {}).get("timeout_s", solver_measure.DEFAULT_TIMEOUT_S),
                    wall_limit_s=(record or {}).get("wall_limit_s", solver_measure.DEFAULT_WALL_LIMIT_S))
    benchmark = {"humanevalfix_sha256": hashlib.sha256(args.humanevalfix.read_bytes()).hexdigest(),
                 "extra_inputs_sha256": None if args.extra_inputs is None else hashlib.sha256(args.extra_inputs.read_bytes()).hexdigest(),
                 "solver_record_sha256": None if args.solver_record is None else hashlib.sha256(args.solver_record.read_bytes()).hexdigest()}
    head: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "which": args.which, "order_seed": args.order_seed, "first": args.first, "learner_budget": args.budget, "arms": list(args.arms),
        "a_lesson_is_kept_when": "the repair changed one line of the program as written out (arms own and backwards); the published fix always (arm shown)",
        "cost_unit": "runs of a bug's tests: 1 to see it fail, 1 per candidate of the learner, 1 more in a fresh interpreter for one that passes, and the processes the solver starts",
        "benchmark": benchmark, "code_sha256": code_sha256(), "model_calls": 0}
    started = time.monotonic()

    def progress(event: dict[str, Any]) -> None:
        so_far = event.pop("so_far")
        args.out.write_text(json.dumps(dict(head, not_ended=True, seconds=round(time.monotonic() - started, 1), summary=summarise(so_far), stream=so_far), indent=1) + "\n")
        if "returned" in event:
            print(f"every bug once more in the arm {event['returned']}: done at {round(time.monotonic() - started)} s", flush=True)
            return
        cells = []
        for arm in args.arms:
            row = event[arm]
            who = {"learner": f"L{row['learner']['rank']}", "solver": "S", None: "-"}[row["repaired_by"]]
            cells.append(f"{arm}:{who:>4s}{'+' if row.get('kept', {}).get('kept') else ' '}")
        print(f"{event['position']:3d} {event['name']:11s} {event['cold']['bug_type']:16s} cold:{'S' if event['cold']['repaired'] else '-'} "
              + " ".join(cells) + f"  {round(time.monotonic() - started)} s", flush=True)

    if args.work_dir.exists():
        shutil.rmtree(args.work_dir)
    args.work_dir.mkdir(parents=True)
    stream = run_stream({bug["name"]: bug for bug in bugs}, order, solver, args.work_dir, arms=args.arms, budget=args.budget, extra=extra, progress=progress)
    shutil.rmtree(args.work_dir, ignore_errors=True)
    scorer = hashlib.sha256(json.dumps(benchmark, sort_keys=True).encode()).hexdigest()
    record_out = dict(head, seconds=round(time.monotonic() - started, 1), summary=summarise(stream),
                      the_rulers_verdict=the_rulers_verdict(stream, scorer_sha256=scorer), stream=stream)
    args.out.write_text(json.dumps(record_out, indent=1) + "\n")
    print(json.dumps({"summary": record_out["summary"], "the_rulers_verdict": record_out["the_rulers_verdict"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
