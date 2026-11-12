#!/usr/bin/env python3
"""What the tree's repair solver repairs on QuixBugs, and what a lesson adds to it.

`quixbugs_one_fix_transfer_measure_v1` asked what one fix teaches the retention organ by
itself. That left the other half open: the tree also has a SOLVER that searches for a fix and
checks it against the tests. This tool runs that solver, as it is, on the same forty bugs, so
that two numbers stand side by side: what the solver repairs with nothing taught, and what
lessons add to that.

The solver, not edited, called the way the tree's own campaign calls it
(canonical/tests/historical_repair_curriculum_v1.py): a process of its own per bug running
    canonical/runtime/bound_capabilities/python_repair_apply_verified_v1.run
with its default search bounds, on a project that holds the buggy program and its tests, with
the retained-learning store beside the project. It repairs IN PLACE or leaves the source as it
was, and says which.

Three questions, each answered by the program's own tests (asked once more by a fresh oracle
after the solver is done; "repaired" needs the solver's own pass, a written file and that
second pass):
    empty_memory       nothing taught, an empty store               -> repaired by search?
    same_bug_again     the store that run left, a fresh copy of the bug
                                                                     -> repaired from memory, with no search?
    other_fixes        the published fixes of all the OTHER programs taught first
                       (through the organ, as in the earlier measurement)
                                                                     -> does memory propose a repair, and is the
                                                                        bug then repaired? which of those were
                                                                        NOT repaired from an empty memory?
When memory proposes nothing the solver goes on to the same search as with an empty memory;
that is the solver's own code path, and a few such bugs are run in full to see that the
outcome is indeed the same (`check_bugs`).

A solver run that has not finished within the wall limit is stopped and counted as not
repaired, and reported as stopped. No model is called anywhere. Authority: none.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import pathlib
import random
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.tools import quixbugs_one_fix_transfer_measure_v1 as bench  # noqa: E402

SCHEMA = "BRAIN_QUIXBUGS_REPAIR_SOLVER_MEASUREMENT_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
PROJECT = "project"                         # the program and its tests, inside the directory the solver is given
MEMORY = "memory/skills.sqlite"             # the retained-learning store, beside the project
REPORT = "reports/solver.json"
DEFAULT_TIMEOUT_S = 8
DEFAULT_WALL_LIMIT_S = 300
DEFAULT_WORKERS = 2


# --------------------------------------------------------------------------- #
# one bug laid out the way the solver takes it
# --------------------------------------------------------------------------- #
def lay_out(root: pathlib.Path, name: str, where: pathlib.Path) -> pathlib.Path:
    """`where` becomes: project/ (the buggy program and its tests), memory/, reports/."""
    if where.exists():
        shutil.rmtree(where)
    where.mkdir(parents=True)
    bench.build_project(root, name, where / "_")
    (where / "_" / name).rename(where / PROJECT)
    (where / "_").rmdir()
    (where / "memory").mkdir()
    (where / "reports").mkdir()
    return where


def solver_args(name: str, *, timeout_s: int, memory: bool = True) -> dict[str, Any]:
    """The solver's arguments: its default search bounds (none is stated), the program's tests,
    and the store. `memory=False` leaves retained learning switched off altogether."""
    args: dict[str, Any] = {
        "source_root": PROJECT,
        "test_paths": [f"{PROJECT}/python_testcases/test_{name}.py"],
        "output_path": REPORT,
        "timeout_s": int(timeout_s),
    }
    if memory:
        args["retained_learning"] = {
            "enabled": True, "db_path": MEMORY, "target_path": f"{PROJECT}/python_programs/{name}.py",
            "contract": dict(bench.CONTRACT), "context": {k: dict(v) for k, v in bench.CONTEXT.items()},
            # the widest the solver's session can be told to be
            "allow_operator_generalization": True, "allow_cross_scope_transfer": True,
        }
    return args


# --------------------------------------------------------------------------- #
# the solver and its memory, each asked in a process of its own
# --------------------------------------------------------------------------- #
_WORKER = r"""
import json, os, sys, time
from pathlib import Path
mode, where, payload = sys.argv[1:4]
where = Path(where).resolve()
args = json.loads(Path(payload).read_text())
launched = []
sys.addaudithook(lambda event, a: launched.append(1) if event == 'subprocess.Popen' else None)
started = time.monotonic()
if mode == 'solve':
    from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as solver
    result = solver.run(args, where)
else:
    # what the solver itself does first when retained learning is on: ask the session for a proposal
    from canonical.swe_kernel.retained_repair_session_v1 import RetainedRepairSession
    source_root = (where / args['source_root']).resolve()
    tests = [(where / p).resolve() for p in args['test_paths']]
    exec_root = Path(os.path.commonpath([str(source_root), *(str(p) for p in tests)])).resolve()
    session = RetainedRepairSession(args['retained_learning'], where, source_root, exec_root, tests, int(args['timeout_s']))
    patches = session.propose()
    result = {'proposed': bool(patches), 'retained_learning': session.metadata,
              'unified_diffs': [str(p.get('unified_diff') or '') for p in patches]}
print('\n' + json.dumps({'result': result, 'seconds': round(time.monotonic() - started, 2), 'processes_started': len(launched)}, default=str))
"""


def _in_a_process(mode: str, where: pathlib.Path, args: Mapping[str, Any], wall_limit_s: int) -> dict[str, Any]:
    payload = where / "reports" / f"{mode}.args.json"
    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.write_text(json.dumps(args))
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.monotonic()
    process = subprocess.Popen([sys.executable, "-c", _WORKER, mode, str(where), str(payload)], cwd=str(REPO), env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, err = process.communicate(timeout=wall_limit_s)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)          # the search's own children go with it
        except ProcessLookupError:
            pass
        process.communicate()
        return {"finished": False, "stopped_at_the_wall_limit": True, "seconds": round(time.monotonic() - started, 2)}
    last = out.strip().split("\n")[-1] if out.strip() else ""
    try:
        answer = json.loads(last)
    except ValueError:
        return {"finished": False, "stopped_at_the_wall_limit": False, "seconds": round(time.monotonic() - started, 2),
                "worker_returncode": process.returncode, "worker_error": (err or out)[-400:]}
    return {"finished": True, "stopped_at_the_wall_limit": False, "seconds": answer["seconds"],
            "processes_started": answer["processes_started"], "result": answer["result"]}


def solve(where: pathlib.Path, args: Mapping[str, Any], wall_limit_s: int) -> dict[str, Any]:
    return _in_a_process("solve", where, args, wall_limit_s)


def propose(where: pathlib.Path, args: Mapping[str, Any], wall_limit_s: int) -> dict[str, Any]:
    return _in_a_process("propose", where, args, wall_limit_s)


# --------------------------------------------------------------------------- #
# what a run came to
# --------------------------------------------------------------------------- #
def judged(run: Mapping[str, Any], where: pathlib.Path, name: str, buggy: str, fixed: str, *, timeout_s: int) -> dict[str, Any]:
    """The solver's report in a few fields, and the program's tests asked once more about the file
    that is now on disk."""
    result = run.get("result") if run.get("finished") else None
    result = result if isinstance(result, Mapping) else {}
    retained = result.get("retained_learning") if isinstance(result.get("retained_learning"), Mapping) else {}
    teaching = retained.get("teaching") if isinstance(retained.get("teaching"), Mapping) else None
    on_disk = (where / PROJECT / "python_programs" / f"{name}.py").read_text(encoding="utf-8")
    changed = on_disk != buggy
    out: dict[str, Any] = {
        "finished": bool(run.get("finished")), "stopped_at_the_wall_limit": bool(run.get("stopped_at_the_wall_limit")),
        "seconds": run.get("seconds"), "processes_started": run.get("processes_started"),
        "solver_says_pass": bool(result.get("pass")), "solver_says_applied": bool(result.get("applied")),
        "status": result.get("status"), "repair_status": result.get("repair_status"), "repair_mode": result.get("repair_mode"),
        "searches": result.get("repair_search_invocations"),
        "memory_hit": bool(retained.get("hit")), "memory_strategy": retained.get("recall_strategy"),
        "lesson_kept_after": None if teaching is None else bool(teaching.get("crystallized")),
        "lesson_not_kept_because": None if teaching is None else teaching.get("reason"),
        "file_changed": changed,
    }
    if run.get("worker_error"):
        out["worker_error"] = run["worker_error"]
    passes = False
    if changed:
        # a fresh oracle, with nothing of the solver in between: it copies the project and runs the tests on this text
        passes = bool(bench.oracle_for(where / PROJECT, name, timeout_s=timeout_s)(on_disk).passed)
        out["is_the_published_fix"] = bench._same_code(on_disk, fixed)
        out["lines_changed"] = _changed_lines(buggy, on_disk)
    out["second_check_passes"] = passes
    out["repaired"] = bool(out["solver_says_pass"] and out["solver_says_applied"] and changed and passes)
    return out


def _changed_lines(before: str, after: str) -> dict[str, list[str]]:
    import difflib
    a, b = before.split("\n"), after.split("\n")
    removed: list[str] = []
    put_in: list[str] = []
    for tag, a0, a1, b0, b1 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag != "equal":
            removed += [line.strip() for line in a[a0:a1]]
            put_in += [line.strip() for line in b[b0:b1]]
    return {"removed": removed, "put_in": put_in}


# --------------------------------------------------------------------------- #
# the measurement
# --------------------------------------------------------------------------- #
def measure(root: pathlib.Path, names: Sequence[str], work: pathlib.Path, *, timeout_s: int = DEFAULT_TIMEOUT_S,
            wall_limit_s: int = DEFAULT_WALL_LIMIT_S, workers: int = DEFAULT_WORKERS, check_bugs: int = 3, seed: int = 0,
            checked: Mapping[str, Mapping[str, Any]] | None = None,
            solve_with: Callable[..., dict[str, Any]] | None = None, propose_with: Callable[..., dict[str, Any]] | None = None,
            progress: Callable[[str], None] | None = None) -> dict[str, Any]:
    say = progress or (lambda line: None)
    solve_with = solve_with or solve
    propose_with = propose_with or propose
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    if checked is None:
        checked = bench.census(root, names, work / "census", timeout_s=timeout_s, progress=progress)
    targets = [name for name in names if checked[name]["can_be_a_target"]]
    buggy, fixed = {}, {}
    for name in names:
        buggy[name] = (root / "python_programs" / f"{name}.py").read_text(encoding="utf-8")
        correct = (root / "correct_python_programs" / f"{name}.py").read_text(encoding="utf-8")
        fixed[name] = bench.reference_fix(buggy[name], correct)["fixed_source"]

    def in_parallel(job: Callable[[str], dict[str, Any]], over: Sequence[str]) -> dict[str, dict[str, Any]]:
        if workers <= 1 or len(over) <= 1:
            return {name: job(name) for name in over}
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            return dict(zip(over, pool.map(job, over)))

    # ---- 1. nothing taught, an empty store ----------------------------------------------------------------------
    def from_empty(name: str) -> dict[str, Any]:
        where = lay_out(root, name, work / "empty_memory" / name)
        run = solve_with(where, solver_args(name, timeout_s=timeout_s), wall_limit_s)
        outcome = judged(run, where, name, buggy[name], fixed[name], timeout_s=timeout_s)
        say(f"[empty memory] {name:<28} {'REPAIRED' if outcome['repaired'] else 'not repaired':<12} {outcome['seconds']}s "
            f"{outcome['status'] or ('stopped at the wall limit' if outcome['stopped_at_the_wall_limit'] else 'worker failed')}")
        return outcome
    empty = in_parallel(from_empty, targets)

    # ---- 2. the same bug again, with the store that run left ----------------------------------------------------
    def again(name: str) -> dict[str, Any]:
        left = work / "empty_memory" / name / MEMORY
        where = lay_out(root, name, work / "same_bug_again" / name)
        _, tally = bench.store_holding([left], where / MEMORY)
        run = solve_with(where, solver_args(name, timeout_s=timeout_s), wall_limit_s)
        outcome = judged(run, where, name, buggy[name], fixed[name], timeout_s=timeout_s)
        outcome["rules_held"] = tally["rules"]
        say(f"[same bug again] {name:<28} {'REPAIRED' if outcome['repaired'] else 'not repaired':<12} {outcome['seconds']}s "
            f"memory hit={outcome['memory_hit']} searches={outcome['searches']}")
        return outcome
    kept = [name for name in targets if empty[name]["repaired"] and empty[name]["lesson_kept_after"]]
    same = in_parallel(again, kept)

    # ---- 3. the published fixes of all the other programs, taught first -----------------------------------------
    lessons: dict[str, dict[str, Any]] = {}
    stores: dict[str, pathlib.Path] = {}
    for name in targets:
        bench.build_project(root, name, work / "teaching")
        path = work / "lessons" / f"{name}.sqlite"
        path.parent.mkdir(parents=True, exist_ok=True)
        lesson = bench.teach(path, buggy[name], fixed[name], bench.oracle_for(work / "teaching" / name, name, timeout_s=timeout_s))
        lessons[name] = lesson
        if lesson["crystallized"]:
            stores[name] = path
        say(f"taught {name:<28} {'stored' if lesson['crystallized'] else 'REFUSED ' + str(lesson['reason'])}")

    def with_others(name: str, *, full: bool) -> dict[str, Any]:
        others = [stores[t] for t in sorted(stores) if t != name]
        where = lay_out(root, name, work / ("other_fixes_full" if full else "other_fixes") / name)
        _, tally = bench.store_holding(others, where / MEMORY)
        args = solver_args(name, timeout_s=timeout_s)
        if not full:
            asked = propose_with(where, args, wall_limit_s)
            result = asked.get("result") if asked.get("finished") else None
            result = result if isinstance(result, Mapping) else {}
            return {"finished": bool(asked.get("finished")), "memory_proposes": bool(result.get("proposed")),
                    "lessons_given": tally["lessons"], "rules_held": tally["rules"], "rules_refused_on_the_way": tally["refused"],
                    "seconds": asked.get("seconds")}
        run = solve_with(where, args, wall_limit_s)
        outcome = judged(run, where, name, buggy[name], fixed[name], timeout_s=timeout_s)
        outcome.update(lessons_given=tally["lessons"], rules_held=tally["rules"], rules_refused_on_the_way=tally["refused"])
        return outcome

    asked = {name: with_others(name, full=False) for name in targets}
    proposing = [name for name in targets if asked[name]["memory_proposes"]]
    say(f"[other fixes] memory proposes a repair for {len(proposing)} of {len(targets)}: {proposing}")
    repaired_with_lessons = in_parallel(lambda name: with_others(name, full=True), proposing)
    for name, outcome in repaired_with_lessons.items():
        say(f"[other fixes] {name:<28} {'REPAIRED' if outcome['repaired'] else 'not repaired':<12} {outcome['seconds']}s "
            f"memory hit={outcome['memory_hit']} searches={outcome['searches']}")
    silent = [name for name in targets if not asked[name]["memory_proposes"] and asked[name]["finished"]]
    rng = random.Random(seed)
    sample = sorted(rng.sample(silent, min(int(check_bugs), len(silent))))
    checks = in_parallel(lambda name: with_others(name, full=True), sample)
    for name, outcome in checks.items():
        say(f"[check] {name:<28} with lessons that propose nothing: {'REPAIRED' if outcome['repaired'] else 'not repaired'}; "
            f"from an empty memory: {'REPAIRED' if empty[name]['repaired'] else 'not repaired'}")
    return {"programs": list(names), "targets": targets, "census": dict(checked), "lessons": lessons,
            "outcomes": {"empty_memory": empty, "same_bug_again": same,
                         "other_fixes": {"memory_asked": asked, "solver_run_where_memory_proposes": repaired_with_lessons,
                                         "solver_run_where_memory_proposes_nothing": checks}}}


def _middle(values: Sequence[float]) -> float | None:
    ordered = sorted(values)
    return ordered[len(ordered) // 2] if ordered else None


def summarise(measured: Mapping[str, Any]) -> dict[str, Any]:
    targets = list(measured["targets"])
    empty = measured["outcomes"]["empty_memory"]
    same = measured["outcomes"]["same_bug_again"]
    other = measured["outcomes"]["other_fixes"]
    repaired = sorted(name for name in targets if empty[name]["repaired"])
    statuses: dict[str, int] = {}
    for name in targets:
        key = str(empty[name]["status"] or ("STOPPED_AT_THE_WALL_LIMIT" if empty[name]["stopped_at_the_wall_limit"] else "WORKER_FAILED"))
        statuses[key] = statuses.get(key, 0) + 1
    with_lessons = other["solver_run_where_memory_proposes"]
    from_memory = sorted(name for name, o in with_lessons.items() if o["repaired"] and o["memory_hit"])
    checks = other["solver_run_where_memory_proposes_nothing"]
    return {
        "programs": len(measured["programs"]),
        "usable_as_targets": len(targets),
        "empty_memory": {
            "repaired": len(repaired), "of": len(targets), "which": repaired,
            "of_which_with_the_published_fix": sum(1 for name in repaired if empty[name].get("is_the_published_fix")),
            "how_the_runs_ended": dict(sorted(statuses.items())),
            "solver_said_pass_but_the_second_check_did_not": sorted(
                name for name in targets if empty[name]["solver_says_pass"] and empty[name]["file_changed"] and not empty[name]["second_check_passes"]),
            "seconds_in_all": round(sum(float(empty[name]["seconds"] or 0) for name in targets), 1),
            "seconds_of_the_middle_repair": _middle([float(empty[name]["seconds"] or 0) for name in repaired]),
            "lesson_kept_after_the_repair": sorted(name for name in repaired if empty[name]["lesson_kept_after"]),
            "lesson_not_kept_after_the_repair": {name: empty[name]["lesson_not_kept_because"] for name in repaired
                                                 if not empty[name]["lesson_kept_after"]},
        },
        "same_bug_again": {
            "asked": len(same), "repaired": sum(1 for o in same.values() if o["repaired"]),
            "of_which_from_memory_with_no_search": sum(1 for o in same.values() if o["repaired"] and o["memory_hit"] and not o["searches"]),
            "not_from_memory": sorted(name for name, o in same.items() if not (o["repaired"] and o["memory_hit"] and not o["searches"])),
            "seconds_of_the_middle_repair_by_search": _middle([float(empty[name]["seconds"] or 0) for name in same]),
            "seconds_of_the_middle_repair_from_memory": _middle([float(o["seconds"] or 0) for o in same.values()
                                                                 if o["repaired"] and o["memory_hit"] and not o["searches"]]),
        },
        "other_fixes": {
            "published_fixes_stored_as_lessons": sum(1 for lesson in measured["lessons"].values() if lesson["crystallized"]),
            "memory_proposes_a_repair_for": sorted(name for name, o in other["memory_asked"].items() if o["memory_proposes"]),
            "memory_could_not_be_asked": sorted(name for name, o in other["memory_asked"].items() if not o["finished"]),
            "repaired_from_memory": from_memory,
            "of_which_not_repaired_from_an_empty_memory": sorted(set(from_memory) - set(repaired)),
            "of_which_also_repaired_from_an_empty_memory": sorted(set(from_memory) & set(repaired)),
            "proposed_but_not_repaired": sorted(name for name, o in with_lessons.items() if not o["repaired"]),
            "where_memory_proposes_nothing_the_outcome_is_as_from_an_empty_memory": {
                name: {"with_lessons": o["repaired"], "from_an_empty_memory": empty[name]["repaired"],
                       "the_same": o["repaired"] == empty[name]["repaired"]} for name, o in sorted(checks.items())},
        },
        "repaired_with_nothing_taught": len(repaired),
        "repaired_when_all_other_fixes_were_taught_first": len(set(repaired) | set(from_memory)),
        "what_the_lessons_added": sorted(set(from_memory) - set(repaired)),
    }


def code_sha256() -> dict[str, str]:
    files = {"tool": pathlib.Path(__file__),
             "bench_tool": pathlib.Path(bench.__file__),
             "solver": REPO / "canonical/runtime/bound_capabilities/python_repair_apply_verified_v1.py",
             "retained_repair_session": REPO / "canonical/swe_kernel/retained_repair_session_v1.py",
             "organ_store": REPO / "canonical/swe_kernel/verified_skill_crystallizer_v1.py",
             "organ_contract_and_oracle": REPO / "canonical/swe_kernel/skill_verification_contract_v1.py"}
    return {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in files.items() if path.is_file()}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--quixbugs-dir", required=True, help="a checkout of github.com/jkoppel/QuixBugs")
    parser.add_argument("--work-dir", help="where the projects and stores are built (default: a temporary directory)")
    parser.add_argument("--programs", nargs="*", help="program names (default: all)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S, help="seconds one run of a program's tests may take")
    parser.add_argument("--wall-limit", type=int, default=DEFAULT_WALL_LIMIT_S, help="seconds one solver run may take in all")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="solver runs side by side")
    parser.add_argument("--check-bugs", type=int, default=3,
                        help="bugs for which memory proposes nothing that are run in full all the same")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    root = pathlib.Path(args.quixbugs_dir).resolve()
    names = list(args.programs) if args.programs else bench.program_names(root)
    work = pathlib.Path(args.work_dir).resolve() if args.work_dir else pathlib.Path(tempfile.mkdtemp(prefix="quixbugs-solver-"))
    say = lambda line: print(line, flush=True)  # noqa: E731
    measured = measure(root, names, work, timeout_s=args.timeout, wall_limit_s=args.wall_limit, workers=args.workers,
                       check_bugs=args.check_bugs, seed=args.seed, progress=say)
    result: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {"source": "github.com/jkoppel/QuixBugs (MIT), python_programs / correct_python_programs / python_testcases",
                        "benchmark_sha256": bench.benchmark_sha256(root, names), "python": sys.version.split()[0],
                        "code_sha256": code_sha256(), "processors": os.cpu_count()},
        "parameters": {"timeout_s": args.timeout, "wall_limit_s": args.wall_limit, "workers": args.workers,
                       "check_bugs": args.check_bugs, "seed": args.seed,
                       "solver_arguments_for_one_bug": solver_args("NAME", timeout_s=args.timeout)},
        "producer_cognition_model_dependency_count": 0, "incremental_spend_usd": 0,
    }
    result.update(measured)
    result["summary"] = summarise(measured)
    print(json.dumps(result["summary"], indent=1, sort_keys=True))
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(result, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
