#!/usr/bin/env python3
"""Closed-loop trace-abduction repair, measured on HumanEvalFix scored bugs.

The system under test is `canonical/swe_kernel/closed_loop_trace_abduction_repair_v1.py`:
trace-sliced fault localization (Ochiai over executed lines) + edit-kind
operators from DEV fixes only + take_out deletions + observational synthesis
at executed fault lines, ranked by trace evidence, with a counterfactual
falsifier (degeneracy scan + perturbation probes + locality) gating every
test-passing candidate before it counts as a repair.

Protocol (identical to the edit-kind transfer measure, so the numbers are
comparable):
  * split by SPLIT_SEED=20261111: 64 development / 100 scored bugs;
  * lessons are the fixes of the 64 dev bugs + the 40 QuixBugs fixes --
    a scored bug's own fix is NEVER among its lessons;
  * a candidate counts as a repair only when it passes the confined screen
    AND a fresh interpreter AND survives the falsifier;
  * every repair is compared with the published fix on HumanEval+ Mini
    extra inputs (agreement) to expose test overfitting.

Zero model calls. Authority: NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_learning_v1 as kinds  # noqa: E402
from canonical.swe_kernel import closed_loop_trace_abduction_repair_v1 as closed_loop  # noqa: E402
from canonical.tools import humanevalfix_edit_kind_transfer_measure_v1 as hef  # noqa: E402

SCHEMA = "BRAIN_CLOSED_LOOP_TRACE_ABDUCTION_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
DEFAULT_BUDGET = 200


def taught_lessons(bugs: Sequence[Mapping[str, Any]], dev_names: Sequence[str],
                   quixbugs: Mapping[str, tuple[str, str]]) -> kinds.Lessons:
    """Dev fixes + QuixBugs fixes only. Scored bugs' own fixes are excluded."""
    lessons = kinds.Lessons()
    for name, (buggy, fixed) in quixbugs.items():
        lessons.learn(name, buggy, fixed)
    by_name = {b["name"]: b for b in bugs}
    for name in dev_names:
        bug = by_name[name]
        lessons.learn(bug["name"], bug["buggy"], bug["fixed"])
    return lessons


def one_bug(bug: Mapping[str, Any], lessons: kinds.Lessons, where: pathlib.Path, *,
            budget: int = DEFAULT_BUDGET,
            extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    started = time.monotonic()
    hef.lay_out(bug, where)
    check = lambda programs: hef.screen(where, programs)  # noqa: E731
    accepted = lambda program: hef.accept(bug, program)  # noqa: E731
    out: dict[str, Any] = {"bug_type": bug["bug_type"]}
    buggy, fixed = (hef.ast.unparse(hef.ast.parse(bug["buggy"])),
                    hef.ast.unparse(hef.ast.parse(bug["fixed"])))
    out["benchmark_holds"] = {
        "buggy_fails_in_the_screen": check([buggy]) is None,
        "published_fix_passes_in_the_screen": check([fixed]) == 0,
        "buggy_fails_in_a_fresh_interpreter": not accepted(bug["buggy"]),
        "published_fix_passes_in_a_fresh_interpreter": bool(accepted(bug["fixed"])),
    }
    out["usable"] = all(out["benchmark_holds"].values())
    if not out["usable"]:
        return out

    # closed-loop proposals: trace-sliced, dev lessons only
    proposals = closed_loop.proposals_for(bug["buggy"], bug["entry"], bug["test"], lessons,
                                          prelude=hef.PRELUDE, budget=budget)
    ranked = [(p["source"], p["score"], p) for p in proposals]
    bench = hef.Bench(bug, check, accepted)
    rank, program, looked_at = bench.first_pass(ranked, budget)
    out["candidates"] = len(proposals)
    out["first_pass_rank"] = rank
    out["repaired_raw"] = rank is not None
    out["candidates_run"] = bench.runs

    if program is not None:
        # falsifier gate: a test-passing candidate is a repair only if it survives
        try:
            buggy_unparsed = hef.ast.unparse(hef.ast.parse(bug["buggy"]))
            fn = closed_loop.load_function(buggy_unparsed, bug["entry"], hef.PRELUDE)
            cases = closed_loop.extract_assert_cases(bug["test"], bug["entry"], fn)
            failing = [c for c in cases if not c.passed]
            passing = [c for c in cases if c.passed]
            f_traces = [closed_loop.run_with_trace(fn, c.args) for c in failing if c.args]
            executed: set[int] = set()
            for t in f_traces:
                executed |= t.executed_lines
            fals = closed_loop.falsify(program, bug["buggy"], bug["entry"], bug["test"],
                                       failing, executed, prelude=hef.PRELUDE)
        except Exception as exc:  # noqa: BLE001
            fals = {"survives": False, "error": str(exc)[:200]}
        out["falsifier"] = fals
        out["repaired"] = bool(fals.get("survives"))
        out["is_the_published_fix"] = program == fixed
        out["origin"] = next((p["origin"] for p in proposals if p["source"] == program), None)
        if not out["is_the_published_fix"]:
            out["on_inputs_the_tests_do_not_have"] = hef.agreement(bug, program, extra)
    else:
        out["repaired"] = False
        out["falsifier"] = None
    out["seconds"] = round(time.monotonic() - started, 2)
    return out


def summarise(per_bug: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    usable = {n: r for n, r in per_bug.items() if r.get("usable")}
    rows = list(usable.values())
    repaired = [r for r in rows if r.get("repaired")]
    raw = [r for r in rows if r.get("repaired_raw")]
    different = [r for r in repaired if not r.get("is_the_published_fix")]
    compared = [r["on_inputs_the_tests_do_not_have"] for r in different
                if r.get("on_inputs_the_tests_do_not_have")]
    by_type: dict[str, dict[str, int]] = {}
    for r in rows:
        cell = by_type.setdefault(r["bug_type"], {"bugs": 0, "repaired": 0, "repaired_raw": 0})
        cell["bugs"] += 1
        cell["repaired"] += bool(r.get("repaired"))
        cell["repaired_raw"] += bool(r.get("repaired_raw"))
    return {
        "bugs_asked": len(per_bug),
        "bugs_usable": len(usable),
        "not_usable": sorted(n for n, r in per_bug.items() if not r.get("usable")),
        "repaired_raw_test_passing": len(raw),
        "repaired_falsifier_surviving": len(repaired),
        "falsifier_killed": len(raw) - len(repaired),
        "the_repair_is_the_published_fix": sum(1 for r in repaired if r.get("is_the_published_fix")),
        "of_those_same_answers_on_every_extra_input": sum(
            1 for c in compared if c.get("inputs_used") and c["agree"] == c["inputs_used"]),
        "of_those_a_different_answer_on_some_extra_input": sum(
            1 for c in compared if c.get("inputs_used") and c["agree"] < c["inputs_used"]),
        "by_bug_type": dict(sorted(by_type.items())),
        "candidates_run": sum(r.get("candidates_run", 0) for r in rows),
        "seconds": round(sum(r.get("seconds", 0) for r in rows), 1),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--humanevalfix", required=True, type=pathlib.Path)
    parser.add_argument("--quixbugs-dir", required=True, type=pathlib.Path)
    parser.add_argument("--extra-inputs", type=pathlib.Path, default=None)
    parser.add_argument("--work-dir", required=True, type=pathlib.Path)
    parser.add_argument("--which", choices=("development", "scored"), default="scored")
    parser.add_argument("--bugs", nargs="*", default=None)
    parser.add_argument("--shard", default="0/1")
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)

    bugs = hef.load_bugs(args.humanevalfix)
    development, scored = hef.split(bugs)
    chosen = development if args.which == "development" else scored
    index, of = (int(x) for x in args.shard.split("/"))
    names = [n for i, n in enumerate(chosen) if i % of == index]
    if args.bugs is not None:
        names = [n for n in names if n in set(args.bugs)]
    quixbugs = hef.quixbugs_lessons(args.quixbugs_dir)
    extra = hef.extra_inputs(args.extra_inputs)
    lessons = taught_lessons(bugs, development, quixbugs)
    record: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "which": args.which, "shard": args.shard, "names": names, "budget": args.budget,
        "lessons": {"given": len(lessons.lessons), "from_quixbugs": sum(1 for n in lessons.lessons if n in quixbugs),
                    "operators": len(lessons.operators)},
        "split": {"seed": hef.SPLIT_SEED, "scored": len(scored), "development": len(development)},
        "benchmark": {"humanevalfix_sha256": hashlib.sha256(args.humanevalfix.read_bytes()).hexdigest(),
                      "bugs": len(bugs)},
        "code_sha256": {
            "canonical/swe_kernel/closed_loop_trace_abduction_repair_v1.py":
                hashlib.sha256((ROOT / "canonical/swe_kernel/closed_loop_trace_abduction_repair_v1.py").read_bytes()).hexdigest(),
            "canonical/tools/closed_loop_trace_abduction_measure_v1.py":
                hashlib.sha256((ROOT / "canonical/tools/closed_loop_trace_abduction_measure_v1.py").read_bytes()).hexdigest(),
        },
        "model_calls": 0,
    }
    by_name = {b["name"]: b for b in bugs}
    per_bug: dict[str, Any] = {}
    for name in names:
        bug = by_name[name]
        where = args.work_dir / name.replace("/", "_")
        per_bug[name] = one_bug(bug, lessons, where, budget=args.budget,
                                extra=extra.get(bug["number"]))
        shutil.rmtree(where, ignore_errors=True)
        r = per_bug[name]
        print(f"{name:11s} {r['bug_type']:16s} usable={r.get('usable')} "
              f"raw={r.get('repaired_raw')} falsifier_survives={r.get('repaired')} "
              f"rank={r.get('first_pass_rank')} of {r.get('candidates')} {r.get('seconds')}s", flush=True)
        record["per_bug"] = dict(per_bug)
        args.out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    record["per_bug"] = per_bug
    record["summary"] = summarise(per_bug)
    args.out.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
    print(json.dumps(record["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
