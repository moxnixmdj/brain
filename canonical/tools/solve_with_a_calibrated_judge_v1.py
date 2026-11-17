#!/usr/bin/env python3
"""Turn last session's audit into solved bugs: judge the way the corpus's own test judges.

WHAT WAS WRONG, AND WHY THIS IS THE REPAIR
------------------------------------------
`judge_the_judge_v1` measured that the cheap in-process judge is **inadmissible on 5 of 31** published
bugs and that the naive comparison rejects the corpus's own corrected program on **7**. And the tree's
own refusal audit (`WHERE_THE_REFUSALS_ACTUALLY_WERE_20261116_V1`) had classified **6** refusals as
`A_SEARCH_TOO_WEAK` -- the answer was inside the space and the search did not reach it. Five of those
six are the same tasks the judge cannot see. So the refusals were attributed to the search when the
instrument was blind.

This runs the space against a judge repaired **only with things a solver actually has at solve time**:

    the test file            the corpus's test is the judge, so the judge reads the test. Where it
                             transforms its data (`testdata = [[inp, [tuple(x) for x in out]] ...]`, as
                             `hanoi` does) the same one-level transform is applied -- not a recursive
                             one, which is a different assertion. Where the test says what *equal*
                             means (`== pytest.approx(expected, abs=input_data[-1])`, as `sqrt` does)
                             the same tolerance is applied. Nothing is read from the answer key.
    the return value         a generator or other iterator is compared by its values, taken bounded by
                             one more than the expected answer could need
    the clock                per case, sized from what the DEFECTIVE program costs on that case -- and
                             where the defective program never returns, its cost says nothing, so the
                             clock falls back to the base instead of to the cap
    isolation                a case that runs out of time is a rejected case; a candidate that cannot
                             run is `None`, never accepted; chunks run in children with memory and CPU
                             ceilings, bisection on a killed child, and no child outlives the judge

Then the corpus's own `pytest` decides, on a fresh copy, with the answer key absent from the task
directory. A task counts as solved only if the corpus's suite says so.

THE INSTRUMENT IS CERTIFIED BEFORE ANY COUNT IS MADE
----------------------------------------------------
Every task opens the corpus's corrected and defective programs once, runs both through this judge, and
runs no search unless the corrected one passes on every case and the defective one is rejected. That is
the only use of the answer key, and it is a gate on the judge, never an input to the search. It earned
its place immediately: with a recursive data transform the judge rejected the corpus's own `hanoi`, and
the run reported the whole 17,395-candidate space as `SPACE_EXHAUSTED` -- a claim about the space that
belonged to the instrument.

A CORRECT JUDGE IS NOT A SEARCH
-------------------------------
Calibrating the judge alone solved one of five tasks in 461.9 s: with the space in natural order,
12,600 candidates went by and four tasks ended `BUDGET_EXHAUSTED`. The judge was not the remaining
limit; the order was. So the space is ordered by the lines the failure actually executes --
`grammar_closed_repair_v1.executed_lines()` on a case the defective program fails. Still knowledge-free:
it reads the defective program's own behaviour on an input it gets wrong, never the answer.

WHAT IS NOT CLAIMED
-------------------
Not that this reaches every refusal. A task is reported `SPACE_EXHAUSTED` only when every candidate in
the space was judged and none passed, `BUDGET_EXHAUSTED` only when the wall or the cap stopped it, and
`JUDGE_NOT_CALIBRATED` when the judge could not see the corpus's own answer -- in which case no verdict
is counted at all. Not any capability credit. Authority NONE, producer-run, zero model, zero network at
run time.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import shutil
import sys
import tempfile
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import grammar_closed_repair_v1 as gen  # noqa: E402

SCHEMA = "BRAIN_SOLVE_WITH_A_CALIBRATED_JUDGE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
UPSTREAM = "https://github.com/jkoppel/QuixBugs"
CHUNK = 50
CHILD_MEMORY_CAP_BYTES = 256_000_000
BASE_CLOCK = 0.05
CLOCK_FACTOR = 20.0
CLOCK_CAP = 2.0


# -------------------------------------------------------------------------------------------------- #
# what the test file says the answer must look like
# -------------------------------------------------------------------------------------------------- #
NORMALISATIONS = (
    (re.compile(r"tuple\(\s*(\w+)\s*\)\s+for\s+\1\s+in\s+out"), "nested_lists_to_tuples"),
    (re.compile(r"list\(\s*(\w+)\s*\)\s+for\s+\1\s+in\s+out"), "nested_tuples_to_lists"),
    # The test file also says what "equal" means. `sqrt` asserts
    # `sqrt(*input_data) == pytest.approx(expected, abs=input_data[-1])`: equality with a
    # tolerance the test takes from its own input. Comparing exactly rejected the corpus's own
    # answer, which is not a fact about the answer.
    (re.compile(r"pytest\.approx\([^)]*abs\s*=\s*input_data\s*\[\s*-\s*1\s*\]"), "approx_last_argument"),
)


def test_file_normalisation(root: pathlib.Path, name: str) -> str | None:
    """The data transform the corpus's own test applies, if it applies one. Read, not guessed."""
    path = root / "python_testcases" / f"test_{name}.py"
    if not path.is_file():
        return None
    text = path.read_text()
    for pattern, kind in NORMALISATIONS:
        if pattern.search(text):
            return kind
    return None


def apply_normalisation(value: Any, kind: str | None) -> Any:
    """Do exactly what the test file does: `[tuple(x) for x in out]`, one level, not all the way.

    Recursing instead of mapping was a real defect and it made `hanoi` unjudgeable: the corpus
    wants `[(1, 3)]`, the corrected program returns `[(1, 3)]`, and recursing turned the expected
    data into `((1, 3),)`. Every candidate was then rejected for a reason that belonged to the
    judge, and the run reported it as `SPACE_EXHAUSTED` -- a claim about the space.
    """
    if not kind or not isinstance(value, (list, tuple)):
        return value
    if kind == "nested_lists_to_tuples":
        return [tuple(item) if isinstance(item, (list, tuple)) else item for item in value]
    if kind == "nested_tuples_to_lists":
        return [list(item) if isinstance(item, (list, tuple)) else item for item in value]
    return value


def approximately_equal(value: Any, expected: Any, tolerance: float) -> bool:
    try:
        return abs(float(value) - float(expected)) <= tolerance
    except (TypeError, ValueError):
        return False


def materialise(value: Any, cap: int) -> Any:
    """Take the values out of a generator, bounded by what the answer could need."""
    import itertools

    if isinstance(value, (str, bytes, list, tuple, dict, set, int, float, bool, type(None))):
        return value
    if hasattr(value, "__iter__"):
        try:
            return list(itertools.islice(iter(value), cap))
        except Exception:  # noqa: BLE001
            return value
    return value


# -------------------------------------------------------------------------------------------------- #
# the judge, in one call, with the clock sized from the defective program
# -------------------------------------------------------------------------------------------------- #
class _CaseTimeout(Exception):
    pass


def _on_alarm(signum, frame):  # noqa: ARG001
    raise _CaseTimeout("case")


def clocks_for(source: str, function_name: str,
               cases: Sequence[tuple[list[Any], Any]]) -> list[float]:
    """Per-case budgets derived from what the defective program costs on each case.

    One global clock is one number too few: `sqrt`'s defective program is slow on one case and
    instant on the rest, so a global 2 s makes every looping candidate cost 2 s -- 307 candidates
    cost 2 s each and the space never finished. A case gets the reference's own cost, times 20.
    """
    import copy
    import signal

    signal.signal(signal.SIGALRM, _on_alarm)
    namespace: dict[str, Any] = {}
    try:
        exec(compile(source, "<clock>", "exec"), namespace)  # noqa: S102
    except Exception:  # noqa: BLE001
        return [BASE_CLOCK for _ in cases]
    function = namespace.get(function_name)
    if function is None:
        return [BASE_CLOCK for _ in cases]
    clocks: list[float] = []
    for args, _expected in cases:
        started = time.time()
        try:
            signal.setitimer(signal.ITIMER_REAL, CLOCK_CAP)
            function(*copy.deepcopy(args))
            signal.setitimer(signal.ITIMER_REAL, 0)
        except Exception:  # noqa: BLE001
            signal.setitimer(signal.ITIMER_REAL, 0)
        took = time.time() - started
        # A defective program that never returned does not say how long the answer may take.
        # `sqrt`'s defective program hangs on six of seven cases; charging the cap to all of them
        # made every looping candidate cost 2 s and the space never finished.
        clocks.append(BASE_CLOCK if took >= CLOCK_CAP
                      else min(CLOCK_CAP, max(BASE_CLOCK, took * CLOCK_FACTOR)))
    return clocks


def clock_for(source: str, function_name: str, cases: Sequence[tuple[list[Any], Any]]) -> float:
    """The slowest case's clock: the one number a chunk budget needs."""
    return max(clocks_for(source, function_name, cases))


def satisfied_cases(source: str, function_name: str, cases: Sequence[tuple[list[Any], Any]],
                    clock: float | Sequence[float],
                    normalisation: str | None) -> list[bool] | None:
    """None when the candidate cannot be run at all; otherwise one flag per case."""
    import copy
    import signal

    signal.signal(signal.SIGALRM, _on_alarm)
    namespace: dict[str, Any] = {}
    try:
        exec(compile(source, "<candidate>", "exec"), namespace)  # noqa: S102
    except Exception:  # noqa: BLE001
        return None
    function = namespace.get(function_name)
    if function is None:
        return None
    clocks = ([clock] * len(cases) if isinstance(clock, (int, float))
              else list(clock) + [BASE_CLOCK] * max(0, len(cases) - len(clock)))
    flags: list[bool] = []
    for (args, expected), case_clock in zip(cases, clocks):
        try:
            signal.setitimer(signal.ITIMER_REAL, case_clock)
            got = function(*copy.deepcopy(args))
            signal.setitimer(signal.ITIMER_REAL, 0)
        except _CaseTimeout:
            signal.setitimer(signal.ITIMER_REAL, 0)
            # The candidate cannot answer this case inside twenty times the reference's own cost.
            # That is a rejected case, not an unknown -- and one is enough: acceptance needs them
            # all, so the remaining cases are not paid for.
            return flags + [False] * (len(cases) - len(flags))
        except Exception:  # noqa: BLE001
            signal.setitimer(signal.ITIMER_REAL, 0)
            return flags + [False] * (len(cases) - len(flags))
        cap = (len(expected) + 1) if isinstance(expected, (list, tuple, str)) else 1024
        value = materialise(got, cap)
        wanted = apply_normalisation(expected, normalisation)
        if normalisation == "approx_last_argument":
            same = approximately_equal(value, expected, abs(float(args[-1])))
        else:
            try:
                same = bool(value == wanted) or bool(value == expected)
            except Exception:  # noqa: BLE001
                same = False
        flags.append(same)
        if not same:
            return flags + [False] * (len(cases) - len(flags))
    return flags


def _child(payload: dict[str, Any], out_path: str, seconds: float) -> None:
    """A child gets a wall, a CPU budget and a memory ceiling, so a hostile candidate fails here."""
    import ctypes
    import resource

    try:  # never outlive the judge: a killed parent used to leave a child spinning for 14 minutes
        ctypes.CDLL("libc.so.6", use_errno=True).prctl(1, 9, 0, 0, 0)  # PR_SET_PDEATHSIG, SIGKILL
    except Exception:  # noqa: BLE001
        pass
    for limit, value in ((resource.RLIMIT_AS, CHILD_MEMORY_CAP_BYTES),
                         (resource.RLIMIT_CPU, int(seconds) + 2)):
        try:
            resource.setrlimit(limit, (value, value))
        except (ValueError, OSError):  # noqa: BLE001
            pass
    clock = payload.get("clocks", payload["clock"])
    rows = [satisfied_cases(src, payload["function"], payload["cases"], clock,
                            payload["normalisation"]) for src in payload["sources"]]
    pathlib.Path(out_path).write_text(json.dumps(rows))


def evaluate_chunk(sources: Sequence[str], payload_core: dict[str, Any],
                   budget_s: float) -> list[Any] | None:
    import multiprocessing

    context = multiprocessing.get_context("spawn")
    with tempfile.TemporaryDirectory() as tmp:
        target = pathlib.Path(tmp) / "chunk.json"
        payload = dict(payload_core, sources=list(sources))
        process = context.Process(target=_child, args=(payload, str(target), budget_s))
        process.start()
        process.join(budget_s)
        if process.is_alive():
            process.terminate()
            process.join(5)
            if process.is_alive():
                process.kill()
                process.join(5)
            return None
        if not target.is_file():
            return None
        return json.loads(target.read_text())


def chunk_budget(per_candidate: float | None, chunk_size: int, clock: float) -> float:
    """What a chunk may cost: measured cost per candidate if there is one, else the clock as a bound.

    The price of judging is measured, not assumed. Before anything is measured the bound is the
    corpus's own clock -- the defective program's own cost on its own cases -- not a constant.
    """
    if per_candidate is None:
        return max(10.0, 40.0 * clock)
    # A half must be cheap enough that bisecting to the one candidate that hung costs seconds
    # after `kheapsort`, not tens of seconds per hang.
    return max(0.35, 3.0 * per_candidate * chunk_size)


def judge(sources: Sequence[str], payload_core: dict[str, Any], *,
          budget_s: float, per_candidate: float | None = None) -> list[Any]:
    """Grade a chunk; if it takes too long, bisect until the expensive candidate is alone.

    A chunk that times out used to cost every candidate in it its verdict, which is how 750
    candidates were reported as hung. Bisection charges the hang to the candidate that hung, and
    a candidate that gets no verdict is `None` — neither accepted nor rejected.
    """
    graded = evaluate_chunk(sources, payload_core, budget_s)
    if graded is not None:
        return graded
    if len(sources) == 1:
        return [None]
    half = len(sources) // 2
    narrow = chunk_budget(per_candidate, half, payload_core["clock"])
    return (judge(sources[:half], payload_core, budget_s=narrow, per_candidate=per_candidate)
            + judge(sources[half:], payload_core, budget_s=narrow, per_candidate=per_candidate))


def self_calibration(root: pathlib.Path, name: str, function_name: str,
                     cases: Sequence[tuple[list[Any], Any]], clocks: Sequence[float],
                     normalisation: str | None) -> dict[str, Any]:
    """Can this judge see the corpus's own corrected program, and does it reject the bug?

    This is the only place the answer key is opened, and it is opened to certify the instrument,
    never to search: the space is enumerated from the defective program alone. Without the gate a
    `SPACE_EXHAUSTED` would be a claim about a judge nobody checked.
    """
    corrected_path = root / "correct_python_programs" / f"{name}.py"
    defective_path = root / "python_programs" / f"{name}.py"
    if not corrected_path.is_file():
        return {"status": "NO_CORRECTED_PROGRAM"}
    corrected = satisfied_cases(corrected_path.read_text(), function_name, cases, clocks,
                                normalisation)
    defective = satisfied_cases(defective_path.read_text(), function_name, cases, clocks,
                                normalisation)
    return {"status": "CALIBRATED",
            "corrected_passes": bool(corrected) and all(corrected),
            "defective_is_rejected": not (bool(defective) and all(defective))}


def exhaustion_stage(evaluated: int, space_size: int, candidate_cap: int) -> str:
    """Running out of candidates in the space is not the same fact as running out of budget."""
    if space_size <= candidate_cap and evaluated >= space_size:
        return "SPACE_EXHAUSTED"
    return "BUDGET_EXHAUSTED"


def solve_task(root: pathlib.Path, name: str, *, candidate_cap: int, wall_budget: float,
               verify_timeout: int, workdir: pathlib.Path,
               space_builder: "Callable[[ast.AST, Sequence[str]], list[dict[str, Any]]] | None" = None,
               ) -> dict[str, Any]:
    row: dict[str, Any] = {"task": name, "kind": "task"}
    cases = gen.examples_of(root, name)
    row["cases"] = len(cases)
    if not cases:
        row["stage"] = "NO_PUBLISHED_CASES"
        return row
    source = (root / "python_programs" / f"{name}.py").read_text()
    row["program_sha256"] = gen.sha256(root / "python_programs" / f"{name}.py")
    tree = ast.parse(source)
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef)), None)
    if function is None:
        row["stage"] = "NO_FUNCTION"
        return row
    row["function"] = function.name
    normalisation = test_file_normalisation(root, name)
    row["normalisation_from_the_test_file"] = normalisation
    clocks = clocks_for(source, function.name, cases)
    clock = max(clocks)
    row["clock_seconds"] = round(clock, 3)
    row["clock_seconds_per_case"] = [round(c, 4) for c in clocks]
    row["calibration"] = self_calibration(root, name, function.name, cases, clocks, normalisation)
    if not (row["calibration"].get("corrected_passes")
            and row["calibration"].get("defective_is_rejected")):
        row["stage"] = "JUDGE_NOT_CALIBRATED"
        return row

    atoms = gen.atoms_of(function)
    if space_builder is None:
        space = gen._enumerate(tree, atoms)  # noqa: SLF001
    else:
        # The space is supplied; the judge, the certification and the verdict are not.
        space = space_builder(tree, atoms)
    row["space_size"] = len(space)
    # Order by the lines the failure actually executes. Knowledge-free: it reads the defective
    # program's own behaviour on a case it fails, never the answer.
    failing = next((args for args, expected in cases
                    if not all(satisfied_cases(source, function.name, [(args, expected)], clock,
                                               normalisation) or [False])), None)
    warm = set()
    if failing is not None:
        try:
            warm = set(gen.executed_lines(source, function.name, failing, clock))
        except Exception:  # noqa: BLE001
            warm = set()
    row["warm_lines"] = sorted(warm)
    if warm:
        space = ([c for c in space if c.get("lineno") in warm]
                 + [c for c in space if c.get("lineno") not in warm])
        row["space_reordered_by_the_failure"] = True
    core = {"function": function.name, "cases": list(cases), "clock": clock,
            "clocks": list(clocks), "normalisation": normalisation}
    started = time.time()
    evaluated = 0
    hung = 0
    per_candidate: float | None = None
    survivors: list[dict[str, Any]] = []
    stage = "BUDGET_EXHAUSTED"
    for start in range(0, min(len(space), candidate_cap), CHUNK):
        chunk = space[start:start + CHUNK]
        budget = chunk_budget(per_candidate, len(chunk), clock)
        budget = min(budget, max(1.0, wall_budget - (time.time() - started)))
        began = time.time()
        graded = judge([c["source"] for c in chunk], core, budget_s=budget,
                       per_candidate=per_candidate)
        took = time.time() - began
        if took < budget and any(flags is not None for flags in graded):
            share = took / len(chunk)
            per_candidate = share if per_candidate is None else 0.7 * per_candidate + 0.3 * share
        evaluated += len(chunk)
        hung += sum(1 for flags in graded if flags is None)
        for candidate, flags in zip(chunk, graded):
            if flags is not None and all(flags):
                survivors.append(candidate)
        if survivors:
            stage = "CANDIDATE_FOUND"
            break
        if time.time() - started > wall_budget:
            stage = "BUDGET_EXHAUSTED"
            break
    if stage == "BUDGET_EXHAUSTED":
        # Every candidate in the space was judged and none passed. That is a fact about the space,
        # not about the budget, and it is not a verdict on the task either.
        stage = exhaustion_stage(evaluated, len(space), candidate_cap)
    row["stage"] = stage
    row["candidates_evaluated"] = evaluated
    row["candidates_hung_or_crashed"] = hung
    row["seconds_per_candidate"] = (round(per_candidate, 6) if per_candidate is not None else None)
    row["seconds_searching"] = round(time.time() - started, 1)
    row["survivors"] = len(survivors)

    row["verdicts"] = []
    for candidate in survivors[:3]:
        where = workdir / f"{name}__calibrated"
        if where.exists():
            shutil.rmtree(where)
        where.mkdir(parents=True)
        built = gen.build_task(root, name, where)
        (where / "python_programs" / f"{name}.py").write_text(candidate["source"], encoding="utf-8")
        result = gen.verify_with_corpus_test(where, built["test_path"], verify_timeout)
        shutil.rmtree(where, ignore_errors=True)
        verdict = {"corpus_test_passes": bool(result.get("returncode") == 0
                                              and not result.get("timed_out")),
                   "returncode": result.get("returncode"),
                   "edit_kind": candidate["kind"],
                   "replacement": candidate.get("replacement"),
                   "lineno": candidate.get("lineno")}
        row["verdicts"].append(verdict)
    row["solved"] = any(v["corpus_test_passes"] for v in row["verdicts"])
    return row


def corpus_commit(root: pathlib.Path) -> str | None:
    """The commit the corpus was read at, so a result is reproducible and not a memory."""
    import subprocess

    try:
        done = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=20)
        return done.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def summarise(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    attempted = [r for r in rows if r.get("stage") in
                 {"CANDIDATE_FOUND", "BUDGET_EXHAUSTED", "SPACE_EXHAUSTED",
                  "NO_PUBLISHED_CASES", "JUDGE_NOT_CALIBRATED"}]
    return {
        "tasks_attempted": len(rows),
        "solved": sorted(r["task"] for r in rows if r.get("solved")),
        "solved_count": sum(1 for r in rows if r.get("solved")),
        "not_solved": sorted(r["task"] for r in rows if not r.get("solved")),
        "budget_exhausted": sorted(r["task"] for r in attempted if r.get("stage")
                                   == "BUDGET_EXHAUSTED"),
        "space_exhausted": sorted(r["task"] for r in attempted if r.get("stage")
                                  == "SPACE_EXHAUSTED"),
        "judge_not_calibrated": sorted(r["task"] for r in rows if r.get("stage")
                                       == "JUDGE_NOT_CALIBRATED"),
        "normalisation_taken_from_the_test_file": sorted(
            r["task"] for r in rows if r.get("normalisation_from_the_test_file")),
        "candidates_evaluated_total": sum(r.get("candidates_evaluated") or 0 for r in rows),
        "candidates_hung_or_crashed_total": sum(r.get("candidates_hung_or_crashed") or 0
                                                for r in rows),
        "seconds_total": round(sum(r.get("seconds_searching") or 0 for r in rows), 1),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--tasks", nargs="+", required=True)
    parser.add_argument("--out", default=None)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--candidate-cap", type=int, default=6000)
    parser.add_argument("--wall-budget", type=float, default=240.0)
    parser.add_argument("--verify-timeout", type=int, default=120)
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs)
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        workdir = pathlib.Path(tmp)
        for name in args.tasks:
            try:
                row = solve_task(root, name, candidate_cap=args.candidate_cap,
                                 wall_budget=args.wall_budget,
                                 verify_timeout=args.verify_timeout, workdir=workdir)
            except Exception as error:  # noqa: BLE001
                row = {"task": name, "kind": "task", "stage": "RAISED", "error": repr(error)[:300]}
            rows.append(row)
            print(f"{name:24s} {str(row.get('stage')):18s} evaluated={row.get('candidates_evaluated')} "
                  f"clock={row.get('clock_seconds')} solved={'Y' if row.get('solved') else 'n'} "
                  f"norm={row.get('normalisation_from_the_test_file')}", flush=True)

    summary = summarise(rows)
    receipt = {"schema": SCHEMA, "authority": AUTHORITY, "upstream": UPSTREAM,
               "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "corpus_commit": corpus_commit(root),
               "tool": "canonical/tools/solve_with_a_calibrated_judge_v1.py",
               "tests": "canonical/tests/test_solve_with_a_calibrated_judge_v1.py",
               "parameters": {"candidate_cap": args.candidate_cap,
                              "wall_budget_seconds": args.wall_budget,
                              "verify_timeout_seconds": args.verify_timeout,
                              "chunk": CHUNK, "child_memory_cap_bytes": CHILD_MEMORY_CAP_BYTES},
               "model_dependency_count": 0, "external_capability_provider_count": 0,
               "network_calls_at_run_time": 0, "summary": summary, "rows": rows}
    if args.out:
        pathlib.Path(args.out).write_text(
            "\n".join(json.dumps(r, default=str) for r in rows) + "\n")
    if args.receipt:
        pathlib.Path(args.receipt).write_text(json.dumps(receipt, indent=2, default=str) + "\n")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
