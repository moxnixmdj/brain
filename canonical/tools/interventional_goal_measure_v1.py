#!/usr/bin/env python3
"""Measure the interventional GOAL on tasks the previous mechanism did NOT solve.

WHY THIS PROTOCOL
-----------------
The owner's standing rule: "We keep testing on bugs we already know work; that's
not progress -- self-congratulation. Avoid."  The previous receipt repaired four
held-out QuixBugs tasks; three of them had already been solved by earlier organs.
Counting them again is not progress.

This tool therefore measures ONLY tasks whose status in the previous receipt is
NOT `REPAIRED__CORPUS_TEST_PASSES`.  The four prior wins are recorded as
`known_wins_not_counted_as_progress`.

The measurement is a FALSIFICATION experiment, not a repair contest:

  F1  quicksort's prior winning diff (`x < pivot` -> `x - 1 < pivot`) is a
      KNOWN FALSE WIN: it passes 13/13 published integer cases and is wrong for
      floats.  The interventional goal must REFUSE it.
  F2  the in-tree deterministic observational program synthesizer is run on
      `is_valid_parenthesization`; its body passes the REAL published suite.
      Whether the interventional goal can refuse it is a measurement of goal
      underdetermination, NOT a capability claim.

PREREGISTERED (written before the run, in this file)
----------------------------------------------------
PASS: F1 refused by >= 1 non-control DO-intervention; zero answer keys; zero
      changed test bytes; zero hidden skips (every previously-unsolved task has
      an executed row); zero permanent rules admitted without identification;
      zero model calls; <= 260 candidates tried per task.
FAIL: any answer key present; any test-byte change; any hidden skip; or F1
      accepted by the interventional contract.
NOT A PASS CONDITION: the number of previously-unsolved tasks repaired.  That
      number is reported as a LIMITING-FACTOR MEASUREMENT.  Requiring a repair
      here would be tuning the experiment to a self-congratulatory outcome.

Integrity: real published QuixBugs programs, tests and JSON cases (pinned
commit), fresh-copy corpus pytest as the only repair verdict, answer key
asserted absent before every task, no synthetic tasks, no model, no network at
run time, $0.  Authority NONE; producer-run; not a leaderboard entry.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.tools import quixbugs_end_to_end_repair_measure_v1 as harness  # noqa: E402
from canonical.tools import quixbugs_one_shot_transfer_measure_v1 as published  # noqa: E402
from canonical.swe_kernel import interventional_goal_v1 as IG  # noqa: E402

SCHEMA = "BRAIN_INTERVENTIONAL_GOAL_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
PRIOR_RECEIPT = REPO / "canonical/verification/CONTRACT_GROUNDED_REPAIR_20261116_V1.json"
CANDIDATE_CAP = 260
REPAIRED = "REPAIRED__CORPUS_TEST_PASSES"


def _head(root: pathlib.Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except (subprocess.OSError, subprocess.SubprocessError):
        return "UNKNOWN"


def previously_unsolved() -> tuple[list[str], list[str]]:
    data = json.loads(PRIOR_RECEIPT.read_text(encoding="utf-8"))
    rows = data["rows"]
    unsolved = [r["task"] for r in rows if r["status"] != REPAIRED]
    known = [r["task"] for r in rows if r["status"] == REPAIRED]
    return unsolved, known


def _apply_single_line_diff(original: str, diff: str) -> str:
    """Apply the prior receipt's verbatim one-line replacement. No guesswork."""
    removed = [ln[1:] for ln in diff.splitlines()
               if ln.startswith("-") and not ln.startswith("---")]
    added = [ln[1:] for ln in diff.splitlines()
             if ln.startswith("+") and not ln.startswith("+++")]
    if len(removed) != 1 or len(added) != 1:
        raise RuntimeError("PRIOR_DIFF_IS_NOT_A_SINGLE_LINE_REPLACEMENT")
    if removed[0] not in original:
        raise RuntimeError("PRIOR_DIFF_DOES_NOT_APPLY_TO_PUBLISHED_SOURCE")
    return original.replace(removed[0], added[0], 1)


def _build_task(root: pathlib.Path, name: str, task_dir: pathlib.Path):
    harness.build_task(root, name, task_dir)
    if (task_dir / IG.ANSWER_KEY).exists():
        raise RuntimeError("ANSWER_KEY_REACHED_THE_SOLVER")
    return IG.CGR.load_task(task_dir, name)


def falsifier_prior_win(root: pathlib.Path) -> dict[str, Any]:
    """F1: a KNOWN false win, reconstructed from the prior receipt's own diff."""
    with tempfile.TemporaryDirectory(prefix="interventional_f1_") as tmp:
        task = _build_task(root, "quicksort", pathlib.Path(tmp) / "task")
        prior = json.loads(PRIOR_RECEIPT.read_text(encoding="utf-8"))
        row = next(r for r in prior["rows"] if r["task"] == "quicksort")
        source = _apply_single_line_diff(task.program_path.read_text(encoding="utf-8"),
                                         row["synthesis"]["winning_diff"])
        result = IG.check_false_win(task, source)
        result["prior_diff"] = row["synthesis"]["winning_diff"]
        result["prior_status"] = row["status"]
        return result


def falsifier_observational_body(root: pathlib.Path) -> dict[str, Any]:
    """F2: what the environment's own I/O pairs induce without interventions."""
    import ast
    from canonical.runtime import swe_observational_program_synthesizer_v1 as synthesizer

    name = "is_valid_parenthesization"
    with tempfile.TemporaryDirectory(prefix="interventional_f2_") as tmp:
        task = _build_task(root, name, pathlib.Path(tmp) / "task")
        exs = [(tuple(a), e) for a, e in task.cases]
        tree = ast.parse(task.program_path.read_text(encoding="utf-8"))
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                  and n.name == task.function_name)
        params = [a.arg for a in fn.args.args]
        # Pin the concept library to an inert object so F2 is reproducible: no
        # memory-derived concepts, only what the published I/O pairs induce.
        body = synthesizer.synthesize_python_function_body(params, exs, [],
                                                          concept_library=object())
        if not body:
            return {"kind": "OBSERVATIONAL_SYNTHESIZER_REFUSED", "body": None,
                    "published_ok": False, "refused": False,
                    "counted_as_progress": False}
        source = f"def {task.function_name}({', '.join(params)}):\n    {body}\n"
        result = IG.check_false_win(task, source)
        interventions, diag = IG.derive_interventions(task)
        result.update({"kind": "OBSERVATIONAL_BODY_UNDER_INTERVENTION", "body": body,
                       "published_cases": len(task.cases),
                       "induced_relations": diag["induced_relations"],
                       "admitted_relations": sorted({r for iv in interventions for r in iv.relations}),
                       "interpretation": ("NO_FALSIFIABLE_RELATION_OVER_THE_ENVIRONMENT"
                                          if not result["refused"] else "REFUSED_BY_COUNTERFACTUAL")})
        return result


def measure(root: pathlib.Path, *, limit: int, candidate_cap: int,
            fresh_cap: int) -> dict[str, Any]:
    unsolved, known = previously_unsolved()
    if limit:
        unsolved = unsolved[:limit]
    rows: list[dict[str, Any]] = []
    started = time.time()
    for name in unsolved:
        with tempfile.TemporaryDirectory(prefix="interventional_task_") as tmp:
            task_dir = pathlib.Path(tmp) / "task"
            try:
                task = _build_task(root, name, task_dir)
                row = IG.solve(task, candidate_cap=candidate_cap, fresh_cap=fresh_cap)
            except Exception as exc:  # a refusal is a row, never a hidden skip
                row = {"schema": IG.SCHEMA, "task": name,
                       "status": "REFUSED__HARNESS_" + type(exc).__name__,
                       "reason": str(exc)[:300], "authority": AUTHORITY,
                       "answer_key_absent": not (task_dir / IG.ANSWER_KEY).exists(),
                       "goal": {}, "identifiability": {},
                       "synthesis": {"candidates": 0, "fresh_verdicts": [],
                                     "passed_published_but_refused_by_intervention": 0,
                                     "calculated_weights": None},
                       "seconds": 0.0}
            rows.append(row)
            print(f"{name:32s} {row['status']:58s} "
                  f"cand={row['synthesis'].get('candidates', 0):4d} "
                  f"refused={row['synthesis'].get('passed_published_but_refused_by_intervention', 0):3d} "
                  f"fresh={len(row['synthesis'].get('fresh_verdicts', []))}", flush=True)

    f1 = falsifier_prior_win(root)
    f2 = falsifier_observational_body(root)

    repaired = [r for r in rows if r["status"] == REPAIRED]
    answer_keys = sum(1 for r in rows if r.get("answer_key_absent") is not True)
    hidden_skips = sum(1 for r in rows if not r.get("status"))
    permanent = sum(1 for r in rows if r.get("identifiability", {}).get("permanent_rule_admitted"))
    candidates = sum(int(r["synthesis"].get("candidates", 0)) for r in rows)
    per_task = round(candidates / len(rows), 1) if rows else None
    regressed = sum(1 for r in repaired for v in r["synthesis"]["fresh_verdicts"]
                    if v.get("returncode") != 0)
    unverified = [r["task"] for r in repaired
                  if not any(v.get("returncode") == 0 and not v.get("timed_out")
                             for v in r["synthesis"]["fresh_verdicts"])]
    reach_total = sum(sum(v for k, v in r.get("goal", {}).get("intervention_reach", {}).items()
                          if k != "IDENTITY") for r in rows)
    underdetermined = []
    discriminating = {}
    unmeasurable = []
    VACUOUS = {"TYPE_MATCH", "BOOLEAN"}
    for r in rows:
        reach = r.get("goal", {}).get("intervention_reach", {})
        relations = set(r.get("goal", {}).get("interventional_relations", []))
        if r["status"].startswith("UNMEASURABLE"):
            unmeasurable.append(r["task"])
        elif not relations or relations <= VACUOUS:
            underdetermined.append(r["task"])
        discriminating[r["task"]] = sorted(k for k, v in reach.items()
                                           if k != "IDENTITY" and v > 0)
    f1_discriminating = sorted(k for k, v in f1["per_intervention"].items()
                               if k != "IDENTITY" and v["violations"] + v["exceptions"] > 0)
    callee_tasks = sum(1 for r in rows if r.get("goal", {}).get("callee_signatures"))
    statuses = collections.Counter(r["status"] for r in rows)

    prereg_pass = (bool(f1["refused"]) and f1["published_ok"]
                   and answer_keys == 0 and hidden_skips == 0 and permanent == 0
                   and not unverified and regressed == 0
                   and (per_task is None or per_task <= CANDIDATE_CAP))
    summary = {
        "schema": SCHEMA, "authority": AUTHORITY,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "upstream": harness.UPSTREAM, "upstream_head": _head(root),
        "protocol": {
            "corpus": "jkoppel/QuixBugs, real published bugs with their own pytest files",
            "pinned_commit": "4257f44b0ff1181dedaedee6a447e133219fcebf",
            "population": "EXACTLY the tasks NOT repaired in CONTRACT_GROUNDED_REPAIR_20261116_V1.json",
            "known_wins_not_counted_as_progress": sorted(known),
            "answer_key": "correct_python_programs asserted absent before every task",
            "verdict": "corpus own pytest on a FRESH copy; candidate self-report is only a filter",
            "test_bytes": "hashed by the existing harness; a changed byte is an error",
            "synthetic_data": "NONE -- programs, cases and tests published verbatim; interventions are DO-maps on real inputs",
            "interventions": list(IG.INTERVENTIONS),
            "model_dependency_count": 0, "network_at_run_time": False, "spend_usd": 0,
        },
        "preregistered": {
            "pass_condition": ("F1_refused_by_a_non_control_DO_intervention AND zero answer keys "
                               "AND zero hidden skips AND zero permanent rules without identification "
                               "AND zero unverified repairs AND <=260 candidates/task"),
            "fail_condition": ("any answer key; any hidden skip; F1 accepted; any unverified repair"),
            "not_a_pass_condition": ("previously_unsolved repairs -- reported as a limiting-factor "
                                     "measurement, explicitly not a repair contest"),
            "verdict": "PASS" if prereg_pass else "FAIL",
        },
        "falsifiers": {"F1_known_false_win": f1, "F2_observational_body": f2},
        "measured": {
            "previously_unsolved_tasks": len(rows),
            "previously_unsolved_repaired": len(repaired),
            "previously_unsolved_repaired_tasks": sorted(r["task"] for r in repaired),
            "known_wins_not_recounted": len(known),
            "status_counts": dict(sorted(statuses.items())),
            "answer_keys_present": answer_keys, "hidden_skips": hidden_skips,
            "regressions": regressed, "unverified_repairs": unverified,
            "permanent_rules_admitted": permanent,
            "candidates_total": candidates,
            "mean_candidates_tried_per_task": per_task,
            "intervention_reach_total_non_control": reach_total,
            "previously_unsolved_remaining": len(rows) - len(repaired),
            "tasks_with_discriminating_intervention": discriminating,
            "f1_discriminating_interventions": f1_discriminating,
            "goal_underdetermined_tasks": underdetermined,
            "unmeasurable_tasks": unmeasurable,
            "tasks_with_callee_signature_vocabulary": callee_tasks,
            "f1_refused": bool(f1["refused"]),
            "f1_non_control_violations": f1["non_control_violations"],
            "f2_refused": bool(f2.get("refused")),
            "f2_interpretation": f2.get("interpretation"),
            "verified_doing_not_admitted_learning": permanent == 0,
            "constructive_inversion_open": len(repaired) < len(rows),
            "wall_seconds": round(time.time() - started, 1),
        },
        "rows": rows,
    }
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quixbugs", required=True, help="pinned jkoppel/QuixBugs checkout")
    parser.add_argument("--out", required=True, help="JSON receipt path")
    parser.add_argument("--limit", type=int, default=0, help="smoke: first N tasks")
    parser.add_argument("--candidate-cap", type=int, default=CANDIDATE_CAP)
    parser.add_argument("--fresh-cap", type=int, default=3)
    args = parser.parse_args(argv)
    root = pathlib.Path(args.quixbugs).resolve()
    if not root.is_dir():
        print("QUIXBUGS_CHECKOUT_MISSING", file=sys.stderr)
        return 2
    summary = measure(root, limit=args.limit, candidate_cap=args.candidate_cap,
                      fresh_cap=args.fresh_cap)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n",
                   encoding="utf-8")
    m = summary["measured"]
    print("\n" + "=" * 78)
    print(f"previously-unsolved {m['previously_unsolved_tasks']}  "
          f"repaired {m['previously_unsolved_repaired']}  "
          f"preregistered {summary['preregistered']['verdict']}")
    print(f"F1 false win refused {m['f1_refused']} "
          f"({m['f1_non_control_violations']} non-control violations)  "
          f"F2 observational body refused {m['f2_refused']} ({m['f2_interpretation']})")
    print(f"goal-underdetermined tasks {len(m['goal_underdetermined_tasks'])}  "
          f"callee-signature tasks {m['tasks_with_callee_signature_vocabulary']}  "
          f"permanent rules {m['permanent_rules_admitted']}")
    print(f"constructive inversion open {m['constructive_inversion_open']}  "
          f"wall {m['wall_seconds']}s")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
