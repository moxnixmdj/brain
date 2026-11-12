#!/usr/bin/env python3
"""The tree's own repair solver on the HumanEvalFix bugs the edit-kind learner was scored on.

Like for like, on bugs nobody here had read: the learner repaired 62 of these 100 bugs from the
fixes of other bugs (canonical/verification/HUMANEVALFIX_EDIT_KIND_TRANSFER_20261111_V1.json).
This tool gives the same bugs, with the same tests, to the repair solver the tree already has
(canonical/runtime/bound_capabilities/python_repair_apply_verified_v1.py) -- not edited, nothing
taught, its default search bounds, one process per bug with a wall limit -- and judges what it
leaves on disk the way the learner's repairs were judged: the bug's tests once more in a fresh
interpreter, then the published fix or the same answers on inputs the tests do not have.

The question it answers is what the solver's hand-written changes repair that the learned kinds
of change do not, and the other way round, before one is put in front of the other.

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
from canonical.tools import quixbugs_repair_solver_measure_v1 as solver_tool  # noqa: E402

SCHEMA = "BRAIN_HUMANEVALFIX_REPAIR_SOLVER_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
PROJECT = "project"
REPORT = "reports/solver.json"
DEFAULT_TIMEOUT_S = 8             # one run of the tests inside the solver, as in its QuixBugs measurement
DEFAULT_WALL_LIMIT_S = 300        # one bug, as in its QuixBugs measurement


def lay_out(bug: Mapping[str, Any], where: pathlib.Path) -> pathlib.Path:
    """`where` becomes: project/ (the buggy program and its tests), memory/, reports/ -- what the solver takes."""
    if where.exists():
        shutil.rmtree(where)
    (where / PROJECT).mkdir(parents=True)
    (where / PROJECT / hef.PROGRAM).write_text(hef.PRELUDE + bug["buggy"], encoding="utf-8")
    (where / PROJECT / hef.TESTS).write_text(hef.test_file(bug), encoding="utf-8")
    (where / "memory").mkdir()
    (where / "reports").mkdir()
    return where


def solver_args(timeout_s: int = DEFAULT_TIMEOUT_S) -> dict[str, Any]:
    """The solver's arguments: its default search bounds (none is stated), the bug's tests, no memory."""
    return {"source_root": PROJECT, "test_paths": [f"{PROJECT}/{hef.TESTS}"], "output_path": REPORT, "timeout_s": int(timeout_s)}


def one_bug(bug: Mapping[str, Any], where: pathlib.Path, *, timeout_s: int = DEFAULT_TIMEOUT_S, wall_limit_s: int = DEFAULT_WALL_LIMIT_S,
            extra: Mapping[str, Any] | None = None, solve: Callable[..., dict[str, Any]] = solver_tool.solve,
            accepted: Callable[[str], bool] | None = None, agreement: Callable[..., dict[str, Any] | None] = hef.agreement) -> dict[str, Any]:
    accepted = accepted or (lambda program: hef.accept(bug, program))
    before = hef.PRELUDE + bug["buggy"]
    out: dict[str, Any] = {"bug_type": bug["bug_type"]}
    out["benchmark_holds"] = {"buggy_fails": not accepted(before), "published_fix_passes": bool(accepted(hef.PRELUDE + bug["fixed"]))}
    out["usable"] = all(out["benchmark_holds"].values())
    if not out["usable"]:
        return out
    lay_out(bug, where)
    run = solve(where, solver_args(timeout_s), wall_limit_s)
    result = run.get("result") if run.get("finished") else None
    result = result if isinstance(result, Mapping) else {}
    on_disk = (where / PROJECT / hef.PROGRAM).read_text(encoding="utf-8")
    changed = on_disk != before
    out.update(finished=bool(run.get("finished")), stopped_at_the_wall_limit=bool(run.get("stopped_at_the_wall_limit")), seconds=run.get("seconds"),
               processes_started=run.get("processes_started"), solver_says_pass=bool(result.get("pass")), solver_says_applied=bool(result.get("applied")),
               status=result.get("status"), searches=result.get("repair_search_invocations"), file_changed=changed)
    if run.get("worker_error"):
        out["worker_error"] = str(run["worker_error"])[-300:]
    passes = bool(changed and accepted(on_disk))
    out["second_check_passes"] = passes
    out["repaired"] = bool(out["solver_says_pass"] and out["solver_says_applied"] and passes)
    if out["repaired"]:
        out["is_the_published_fix"] = kinds.same_program(on_disk, hef.PRELUDE + bug["fixed"])
        right = out["is_the_published_fix"]
        if not right:
            compared = agreement(bug, on_disk, extra)
            out["on_inputs_the_tests_do_not_have"] = compared
            right = bool(compared and compared.get("inputs_used") and compared["agree"] == compared["inputs_used"])
        out["right_as_far_as_checked"] = bool(right)
        try:
            out["lines"] = hef.changed_lines(before, ast.unparse(ast.parse(on_disk)))
        except (SyntaxError, ValueError):
            out["lines"] = None
    return out


def learner_outcomes(record: Mapping[str, Any]) -> dict[str, dict[str, dict[str, bool]]]:
    """What the edit-kind learner did on each bug, from its record, for both sets of lessons."""
    out: dict[str, dict[str, dict[str, bool]]] = {}
    for question in ("all_other_fixes", "another_benchmark"):
        rows = {}
        for name, row in record["per_bug"].items():
            if not row.get("usable"):
                continue
            answer = row[question]
            compared = answer.get("on_inputs_the_tests_do_not_have")
            right = bool(answer.get("repaired") and (answer.get("is_the_published_fix")
                                                     or (compared and compared.get("inputs_used") and compared["agree"] == compared["inputs_used"])))
            rows[name] = {"repaired": bool(answer.get("repaired")), "right_as_far_as_checked": right}
        out[question] = rows
    return out


def summarise(per_bug: Mapping[str, Mapping[str, Any]], learner: Mapping[str, Mapping[str, Mapping[str, bool]]] | None = None) -> dict[str, Any]:
    usable = {name: row for name, row in per_bug.items() if row.get("usable")}
    repaired = {name for name, row in usable.items() if row.get("repaired")}
    ends: dict[str, int] = {}
    for row in usable.values():
        how = row.get("status") or ("STOPPED_AT_THE_WALL_LIMIT" if row.get("stopped_at_the_wall_limit") else "WORKER_FAILED")
        ends[how] = ends.get(how, 0) + 1
    out: dict[str, Any] = {
        "bugs_asked": len(per_bug), "bugs_usable": len(usable), "not_usable": sorted(name for name, row in per_bug.items() if not row.get("usable")),
        "repaired": len(repaired), "the_repair_is_the_published_fix": sum(1 for n in repaired if usable[n].get("is_the_published_fix")),
        "right_as_far_as_checked": sum(1 for n in repaired if usable[n].get("right_as_far_as_checked")),
        "passes_and_is_wrong_on_an_extra_input": sum(1 for n in repaired if not usable[n].get("right_as_far_as_checked")),
        "solver_said_pass_but_the_second_check_did_not": sorted(n for n, row in usable.items() if row.get("solver_says_pass") and row.get("solver_says_applied")
                                                                and not row.get("second_check_passes")),
        "how_the_runs_ended": dict(sorted(ends.items())),
        "seconds_in_all": round(sum(row.get("seconds") or 0 for row in usable.values()), 1),
        "which": sorted(repaired, key=lambda n: int(n.split("/")[1])),
    }
    by_type: dict[str, dict[str, int]] = {}
    for name, row in usable.items():
        cell = by_type.setdefault(row["bug_type"], {"bugs": 0, "repaired": 0})
        cell["bugs"] += 1
        cell["repaired"] += name in repaired
    out["by_bug_type"] = dict(sorted(by_type.items()))
    if learner:
        beside = {}
        for question, rows in learner.items():
            names = [name for name in usable if name in rows]
            theirs = {name for name in names if rows[name]["repaired"]}
            mine = repaired & set(names)
            beside[question] = {"bugs": len(names), "the_solver": len(mine), "the_learner": len(theirs), "both": len(mine & theirs),
                                "the_solver_alone": sorted(mine - theirs, key=lambda n: int(n.split("/")[1])), "the_learner_alone": len(theirs - mine),
                                "neither": len(names) - len(mine | theirs), "either": len(mine | theirs),
                                "either_right_as_far_as_checked": sum(1 for name in names if (rows[name]["right_as_far_as_checked"] if rows[name]["repaired"]
                                                                                           else bool(usable[name].get("right_as_far_as_checked"))))}
        out["beside_the_edit_kind_learner"] = beside
    return out


def code_sha256() -> dict[str, str]:
    files = ("canonical/tools/humanevalfix_repair_solver_measure_v1.py", "canonical/tools/quixbugs_repair_solver_measure_v1.py",
             "canonical/tools/humanevalfix_edit_kind_transfer_measure_v1.py", "canonical/runtime/bound_capabilities/python_repair_apply_verified_v1.py",
             "canonical/runtime/bound_capabilities/python_test_guided_patch_search_v1.py")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--humanevalfix", required=True, type=pathlib.Path)
    parser.add_argument("--extra-inputs", type=pathlib.Path, default=None)
    parser.add_argument("--learner-record", type=pathlib.Path, default=ROOT / "canonical/verification/HUMANEVALFIX_EDIT_KIND_TRANSFER_20261111_V1.json")
    parser.add_argument("--which", choices=("development", "scored"), default="scored")
    parser.add_argument("--bugs", nargs="*", default=None)
    parser.add_argument("--shard", default="0/1")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--wall-limit", type=int, default=DEFAULT_WALL_LIMIT_S)
    parser.add_argument("--work-dir", required=True, type=pathlib.Path)
    parser.add_argument("--merge", nargs="*", type=pathlib.Path, default=None)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    learner = learner_outcomes(json.loads(args.learner_record.read_text())) if args.learner_record and args.learner_record.is_file() else None

    if args.merge is not None:
        parts = [json.loads(path.read_text()) for path in args.merge]
        if any(part[k] != parts[0][k] for part in parts for k in ("which", "timeout_s", "wall_limit_s", "code_sha256", "benchmark")):
            raise SystemExit("the shards were not measured the same way")
        per_bug: dict[str, Any] = {}
        for part in parts:
            per_bug.update(part["per_bug"])
        record = {k: v for k, v in parts[0].items() if k not in ("per_bug", "summary", "shard", "names")}
        record["per_bug"] = dict(sorted(per_bug.items(), key=lambda kv: int(kv[0].split("/")[1])))
        record["summary"] = summarise(record["per_bug"], learner)
        args.out.write_text(json.dumps(record, indent=1) + "\n")
        print(json.dumps(record["summary"], indent=1))
        return 0

    bugs = hef.load_bugs(args.humanevalfix)
    development, scored = hef.split(bugs)
    chosen = development if args.which == "development" else scored
    index, of = (int(x) for x in args.shard.split("/"))
    names = [name for n, name in enumerate(chosen) if n % of == index]
    if args.bugs is not None:
        names = [name for name in names if name in set(args.bugs)]
    extra = hef.extra_inputs(args.extra_inputs)
    by_name = {bug["name"]: bug for bug in bugs}
    record: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "which": args.which, "shard": args.shard, "names": names, "timeout_s": args.timeout, "wall_limit_s": args.wall_limit,
        "solver_arguments_for_one_bug": solver_args(args.timeout), "nothing_taught": True,
        "benchmark": {"humanevalfix_sha256": hashlib.sha256(args.humanevalfix.read_bytes()).hexdigest(),
                      "extra_inputs_sha256": None if args.extra_inputs is None else hashlib.sha256(args.extra_inputs.read_bytes()).hexdigest()},
        "code_sha256": code_sha256(), "model_calls": 0, "per_bug": {},
    }
    for name in names:
        bug = by_name[name]
        where = args.work_dir / name.replace("/", "_")
        row = one_bug(bug, where, timeout_s=args.timeout, wall_limit_s=args.wall_limit, extra=extra.get(bug["number"]))
        shutil.rmtree(where, ignore_errors=True)
        record["per_bug"][name] = row
        print(f"{name:11s} {row['bug_type']:16s} {'REPAIRED' if row.get('repaired') else 'not repaired'} {row.get('seconds')} s "
              f"{row.get('processes_started')} {row.get('status') or ('wall limit' if row.get('stopped_at_the_wall_limit') else 'worker failed')} {row.get('lines') or ''}", flush=True)
        args.out.write_text(json.dumps(record, indent=1) + "\n")
    record["summary"] = summarise(record["per_bug"], learner)
    args.out.write_text(json.dumps(record, indent=1) + "\n")
    print(json.dumps(record["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
