"""Measure the goal compiler on real held-out published bugs.

THE QUESTION
------------
"Show the agent the most advanced coding actions once and it learns them
permanently -- so we solve software engineering."  The tree already measured
that this is false (2/20 and 1/20 held-out QuixBugs repairs).  This tool asks
the sharper question: what happens when the missing level -- the GOAL -- is
derived at use time from the environment's own executable contract?

PROTOCOL (integrity enforced, not promised)
------------------------------------------
1. Corpus: jkoppel/QuixBugs (MIT), pinned by commit, 40 real published bugs.
2. Split by sha256(name), reusing the PUBLISHED split function so the result
   is comparable to the two measured baselines (2/20 hand-listed, 1/20
   induced).  The training half is never used to design the mechanism.
3. ``build_task`` copies only what the solver may see.  ``correct_python_programs``
   is asserted absent before every task.  The answer key was never read in
   this session.
4. The verdict is the corpus's OWN pytest, re-run by the harness on a FRESH
   copy of the task.  A candidate's own in-process pass is only a filter.
5. Every test byte and program byte is hashed.  A changed test byte is an
   error, not a repair.
6. No model, no network at run time, no synthetic tasks, $0.

PREREGISTERED (written before the run, in this file)
----------------------------------------------------
PASS: held-out repairs >= 4 (beating the union of both published baselines,
3/20), zero regressions, every repaired task backed by a fresh-copy pytest
rc=0, answer key absent everywhere, and <= 260 candidates TRIED PER TASK
(i.e. the gain is not brute-force enumeration).
FAIL: any repaired task without a fresh-copy rc=0; any answer key present;
any test-file byte change; or a gain that required unbounded enumeration.

Authority NONE. Producer-run. Not a leaderboard entry.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.tools import quixbugs_end_to_end_repair_measure_v1 as harness
from canonical.tools import quixbugs_one_shot_transfer_measure_v1 as published
from canonical.swe_kernel import contract_grounded_repair_v1 as cgr

SCHEMA = "BRAIN_CONTRACT_GROUNDED_REPAIR_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
CANDIDATE_CAP = 260
PASS_REPAIRS = 4


def _head(root: pathlib.Path) -> str:
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return "UNKNOWN"


def measure(root: pathlib.Path, *, train_size: int, limit: int,
            candidate_cap: int, fresh_cap: int) -> dict[str, Any]:
    names = harness.tasks_of(root)
    train, held_out = published.split(names, train_size)
    if limit:
        held_out = held_out[:limit]
    rows: list[dict[str, Any]] = []
    started = time.time()
    for name in held_out:
        with tempfile.TemporaryDirectory(prefix="contract_task_") as tmp:
            task_dir = pathlib.Path(tmp) / "task"
            try:
                harness.build_task(root, name, task_dir)
                task = cgr.load_task(task_dir, name)
                row = cgr.solve(task, candidate_cap=candidate_cap, fresh_cap=fresh_cap)
            except Exception as exc:  # a refusal is a row, never a hidden skip
                row = {"schema": cgr.SCHEMA, "task": name,
                       "status": "REFUSED__HARNESS_" + type(exc).__name__,
                       "reason": str(exc)[:300], "authority": AUTHORITY,
                       "answer_key_absent": not (task_dir / cgr.ANSWER_KEY).exists(),
                       "goal": {}, "identifiability": {},
                       "synthesis": {"candidates": 0, "screened": 0,
                                     "fresh_verdicts": [], "prior": None,
                                     "passed_published_but_refused_by_contract": 0},
                       "seconds": 0.0}
            rows.append(row)
            print(f"{name:32s} {row['status']:56s} "
                  f"candidates={row['synthesis'].get('candidates', 0):4d} "
                  f"fresh={len(row['synthesis'].get('fresh_verdicts', []))}", flush=True)

    repaired = [r for r in rows if r["status"] == "REPAIRED__CORPUS_TEST_PASSES"]
    repairs = len(repaired)
    regressions = sum(1 for r in repaired
                      for v in r["synthesis"]["fresh_verdicts"]
                      if v["family"] == r["synthesis"]["winning_family"] and v["returncode"] != 0)
    answer_keys = sum(1 for r in rows if r.get("answer_key_absent") is not True)
    unverified_repairs = [r["task"] for r in repaired
                          if not any(v["returncode"] == 0 and not v["timed_out"]
                                     for v in r["synthesis"]["fresh_verdicts"])]
    statuses = collections.Counter(r["status"] for r in rows)
    closures = sum(1 for r in rows
                   if r.get("identifiability", {}).get("closure", "").startswith("STATIC_INSUFFICIENT"))
    static_insufficient = sum(1 for r in rows
                              if (r.get("identifiability", {}).get("static_certificate") or {}).get("unrepairable_by_repetition"))
    traced_insufficient = sum(1 for r in rows
                              if (r.get("identifiability", {}).get("traced_certificate") or {}).get("unrepairable_by_repetition"))
    contract_relations = sum(int(r.get("goal", {}).get("contract_reach", 0)) for r in rows)
    refused_by_contract = sum(int(r["synthesis"].get("passed_published_but_refused_by_contract", 0))
                              for r in rows)
    candidates = sum(int(r["synthesis"].get("candidates", 0)) for r in rows)
    fresh_verdicts = sum(len(r["synthesis"].get("fresh_verdicts", [])) for r in rows)
    per_task = round(candidates / len(rows), 1) if rows else None
    first_indices = [r["synthesis"].get("winning_index") for r in repaired
                     if r["synthesis"].get("winning_index") is not None]
    mean_to_first = round(sum(i + 1 for i in first_indices) / len(first_indices), 1) if first_indices else None
    permanent_rules = sum(1 for r in rows
                          if r.get("identifiability", {}).get("permanent_rule_admitted"))

    prereg_pass = (repairs >= PASS_REPAIRS and regressions == 0 and answer_keys == 0
                   and not unverified_repairs and (per_task is None or per_task <= CANDIDATE_CAP))
    summary = {
        "schema": SCHEMA, "authority": AUTHORITY,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "upstream": harness.UPSTREAM, "upstream_head": _head(root),
        "protocol": {
            "corpus": "jkoppel/QuixBugs, 40 real published bugs with their own pytest files",
            "split": "sha256(name), reused from quixbugs_one_shot_transfer_measure_v1.split",
            "train": train, "held_out": held_out, "train_size": train_size,
            "answer_key": "correct_python_programs asserted absent before every task",
            "verdict": "corpus own pytest on a FRESH copy; candidate self-report is only a filter",
            "test_bytes": "hashed; a changed byte is an error, not a repair",
            "synthetic_data": "NONE -- all programs, cases and tests are published verbatim",
            "model_dependency_count": 0, "network_at_run_time": False, "spend_usd": 0,
        },
        "preregistered": {
            "pass_condition": ("held_out_repairs >= 4 AND regressions == 0 AND "
                               "every repaired task has fresh pytest rc=0 AND answer_key_absent "
                               "AND mean_candidates_tried_per_task <= 260"),
            "fail_condition": ("any repaired task without a fresh rc=0; any answer key present; "
                               "any test-byte change; any gain requiring brute-force enumeration"),
            "published_baselines": {"hand_listed_basis": "2/20, 5021 candidates",
                                    "induced_basis": "1/20, 224 candidates",
                                    "union": "3/20 (successes disjoint)"},
            "verdict": "PASS" if prereg_pass else "FAIL",
        },
        "measured": {
            "held_out_tasks": len(rows), "repaired": repairs,
            "repaired_tasks": sorted(r["task"] for r in repaired),
            "status_counts": dict(sorted(statuses.items())),
            "unverified_repairs": unverified_repairs,
            "regressions": regressions, "answer_keys_present": answer_keys,
            "candidates_total": candidates, "fresh_verdicts_total": fresh_verdicts,
            "mean_candidates_tried_per_task": per_task,
            "mean_candidates_to_first_repair": mean_to_first,
            "permanent_rules_admitted": permanent_rules,
            "certificate_closures": closures,
            "static_vocabulary_insufficient_tasks": static_insufficient,
            "traced_vocabulary_insufficient_tasks": traced_insufficient,
            "assertion_derived_relations_with_teeth": contract_relations,
            "candidates_that_passed_published_cases_but_were_refused_by_the_contract": refused_by_contract,
            "wall_seconds": round(time.time() - started, 1),
        },
        "rows": rows,
    }
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quixbugs", required=True, help="pinned jkoppel/QuixBugs checkout")
    parser.add_argument("--out", required=True, help="JSON receipt path")
    parser.add_argument("--train-size", type=int, default=20)
    parser.add_argument("--limit", type=int, default=0, help="smoke: first N held-out tasks")
    parser.add_argument("--candidate-cap", type=int, default=CANDIDATE_CAP)
    parser.add_argument("--fresh-cap", type=int, default=3)
    args = parser.parse_args(argv)
    root = pathlib.Path(args.quixbugs).resolve()
    if not root.is_dir():
        print("QUIXBUGS_CHECKOUT_MISSING", file=sys.stderr)
        return 2
    summary = measure(root, train_size=args.train_size, limit=args.limit,
                      candidate_cap=args.candidate_cap, fresh_cap=args.fresh_cap)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n",
                   encoding="utf-8")
    m = summary["measured"]
    print("\n" + "=" * 78)
    print(f"held-out {m['held_out_tasks']}  repaired {m['repaired']}  "
          f"preregistered {summary['preregistered']['verdict']}")
    print(f"certificate closures {m['certificate_closures']}  "
          f"static insufficient {m['static_vocabulary_insufficient_tasks']}  "
          f"traced insufficient {m['traced_vocabulary_insufficient_tasks']}")
    print(f"assertion-derived relations with teeth {m['assertion_derived_relations_with_teeth']}  "
          f"refused by contract {m['candidates_that_passed_published_cases_but_were_refused_by_the_contract']}")
    print(f"candidates {m['candidates_total']}  fresh verdicts {m['fresh_verdicts_total']}  "
          f"per task {m['mean_candidates_tried_per_task']}  "
          f"to first repair {m['mean_candidates_to_first_repair']}  wall {m['wall_seconds']}s")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
