#!/usr/bin/env python3
"""The counterfactual interior-specification repairer on the 40 QuixBugs bugs.

Like for like
------------
canonical/verification/QUIXBUGS_REPAIR_SOLVER_20261111_V1.json: the tree's
repair solver, not edited, repairs 5 of the 40 with nothing taught.
canonical/verification/QUIXBUGS_EDIT_KIND_TRANSFER_20261112_V1.json: the
edit-kind learner from HumanEvalFix lessons repairs 20 (21 with all other
fixes), union with the solver 21; neither arm repairs 19.

This tool gives the same 40 bugs, with the same tests deciding, to
canonical/runtime/bound_capabilities/python_counterfactual_spec_repair_v1.py --
the missing channel: force a value at an interior site, re-execute, synthesize
the expression that produces it, verify on the corpus's own pytest.

Integrity (the four rules of quixbugs_end_to_end_repair_measure_v1, unchanged):
  1. No answer key in the task directory (build_task asserts).
  2. Tests byte-for-byte hashed against the pinned checkout.
  3. Independent verdict: the candidate diff is applied to a FRESH copy and the
     corpus's own pytest runs there.  The search's claim is not evidence.
  4. Nothing is promoted; authority NONE; zero model calls; $0 spend.

Headline for this receipt is the overlap with the 19 bugs neither prior arm
repairs -- new coverage, not a re-test of known-working bugs.

Zero model calls. Nothing here gives authority to anything.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime.bound_capabilities import (  # noqa: E402
    python_counterfactual_spec_repair_v1 as cf,
)
from canonical.tools import quixbugs_end_to_end_repair_measure_v1 as base  # noqa: E402

SCHEMA = "BRAIN_COUNTERFACTUAL_REPAIR_QUIXBUGS_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

# The 19 bugs neither prior arm repaired (derived from
# QUIXBUGS_EDIT_KIND_TRANSFER_20261112_V1.json summary beside_the_trees /
# another_benchmark__beside__the_solver_with_nothing_taught).
NEITHER_19 = (
    "bitcount", "breadth_first_search", "detect_cycle", "flatten", "kheapsort",
    "kth", "lis", "max_sublist_sum", "mergesort", "possible_change",
    "powerset", "reverse_linked_list", "shortest_path_length", "shortest_paths",
    "shunting_yard", "sqrt", "subsequences", "topological_ordering", "wrap",
)


def pytest_argv(where: pathlib.Path, test_path: str) -> list[str]:
    """Direct pytest argv -- the same oracle the prior arms used, with node ids."""
    import sys as _sys
    return [_sys.executable, "-m", "pytest", test_path, "-q", "-p", "no:cacheprovider"]


def run_pytest(where: pathlib.Path, test_path: str, timeout: int = 180) -> dict[str, Any]:
    """Corpus pytest with QuixBugs' two import roots on PYTHONPATH.

    The inherited base.run_pytest only puts ``where`` on PYTHONPATH; tests
    do ``from node import Node`` / ``from load_testdata import ...`` which
    live under ``python_programs/`` and ``python_testcases/``.  Without
    those roots the suite dies at collection (rc 2) and a correct patch is
    misreported as NOT_REPAIRED.
    """
    import os as _os
    import subprocess as _sp
    env = dict(_os.environ)
    roots = [str(where), str(where / "python_programs"), str(where / "python_testcases")]
    prior = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = _os.pathsep.join(roots + ([prior] if prior else []))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.time()
    try:
        done = _sp.run(pytest_argv(where, test_path),
                       cwd=str(where), capture_output=True, text=True,
                       timeout=timeout, env=env)
        return {"returncode": done.returncode, "timed_out": False,
                "tail": (done.stdout + done.stderr).strip().splitlines()[-3:],
                "seconds": round(time.time() - started, 1)}
    except _sp.TimeoutExpired:
        return {"returncode": None, "timed_out": True, "tail": ["TIMEOUT"],
                "seconds": round(time.time() - started, 1)}


def measure(root: pathlib.Path, name: str, *, wall_budget_s: float,
            timeout_s: int) -> dict[str, Any]:
    """One published bug, start to finish, with independent fresh-copy verdict."""
    import os
    import tempfile

    row: dict[str, Any] = {"task": name, "kind": "task"}
    started = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        where = pathlib.Path(tmp) / name
        try:
            row.update(base.build_task(root, name, where))
        except Exception as error:  # noqa: BLE001 -- one task must not take the others
            row.update(stage="TASK_NOT_BUILT", reason=type(error).__name__,
                       detail=str(error)[:200])
            return row

        test_path = row["test_path"]
        baseline = run_pytest(where, test_path, timeout=timeout_s)
        row["baseline"] = baseline
        if baseline["returncode"] == 0:
            row["stage"] = "DEFECT_DOES_NOT_REPRODUCE"
            row["seconds"] = round(time.time() - started, 1)
            return row

        os.environ["BRAIN_REPAIR_SELF"] = "1"
        argv = pytest_argv(where, test_path)
        try:
            result = cf.run({
                "source_path": row["program_path"],
                "test_paths": [test_path],
                "test_argv": argv,
                "output_path": "_cf_result.json",
                "timeout_s": timeout_s,
                "wall_budget_s": wall_budget_s,
                "max_sites": 24,
                "max_terms": 50,
            }, root=where)
        except cf.CounterfactualSpecError as error:
            row.update(stage="ENGINE__" + str(error),
                       seconds=round(time.time() - started, 1))
            return row
        except Exception as error:  # noqa: BLE001
            row.update(stage="ENGINE_RAISED__" + type(error).__name__,
                       detail=str(error)[:300],
                       seconds=round(time.time() - started, 1))
            return row

        row["engine_status"] = result.get("status")
        row["engine_pass"] = bool(result.get("pass"))
        row["winning_site"] = result.get("winning_site")
        row["winning_kind"] = result.get("winning_kind")
        row["winning_term"] = result.get("winning_term")
        row["winning_mode"] = result.get("winning_mode")
        row["sabotage_discriminates"] = result.get("sabotage_discriminates")
        row["tested_candidate_count"] = result.get("tested_candidate_count")
        row["engine_seconds"] = result.get("seconds")
        patches = result.get("patches") or []
        row["patch_count"] = len(patches)

        if not patches:
            row["stage"] = "NOT_REPAIRED__" + str(result.get("status"))
            row["seconds"] = round(time.time() - started, 1)
            return row

        # Rule 3: verify on a FRESH copy with the corpus's own test.
        fresh = pathlib.Path(tmp) / (name + "__verify")
        base.build_task(root, name, fresh)
        applied = []
        for patch in patches:
            ok, how = base.apply_patch(fresh, str(patch.get("unified_diff") or ""))
            applied.append({"source_path": patch.get("source_path"),
                            "applied": ok, "how": how})
        row["patches_applied"] = applied
        if not all(a["applied"] for a in applied):
            row["stage"] = "NOT_VERIFIED__PATCH_DID_NOT_APPLY"
            row["seconds"] = round(time.time() - started, 1)
            return row
        verdict = run_pytest(fresh, test_path, timeout=timeout_s)
        row["verification"] = verdict
        if verdict["returncode"] == 0 and not verdict.get("timed_out"):
            row["stage"] = "REPAIRED__CORPUS_TEST_PASSES"
        else:
            row["stage"] = "NOT_REPAIRED__CORPUS_TEST_STILL_FAILS"
        row["seconds"] = round(time.time() - started, 1)
        return row


def summarise(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    stages: dict[str, list[str]] = {}
    for row in rows:
        stages.setdefault(str(row.get("stage")), []).append(str(row.get("task")))
    repaired = stages.get("REPAIRED__CORPUS_TEST_PASSES", [])
    neither_repaired = sorted(set(repaired) & set(NEITHER_19))
    return {
        "tasks": len(rows),
        "repaired": len(repaired),
        "repaired_tasks": sorted(repaired),
        "neither_19_repaired": neither_repaired,
        "neither_19_repaired_count": len(neither_repaired),
        "by_stage": {k: {"count": len(v), "tasks": sorted(v)}
                     for k, v in sorted(stages.items())},
        "seconds_total": round(sum(float(r.get("seconds") or 0) for r in rows), 1),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", required=True,
                        help="path to a jkoppel/QuixBugs checkout")
    parser.add_argument("--out", required=True,
                        help="JSONL: a header, then one row per task")
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--wall-budget-s", type=float, default=90.0)
    parser.add_argument("--timeout-s", type=int, default=30)
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs).resolve()
    names = args.tasks or base.tasks_of(root)
    if not names:
        raise SystemExit("NO_TASKS_FOUND")
    header = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "kind": "header",
        "upstream": base.UPSTREAM,
        "tasks_planned": names,
        "wall_budget_s": args.wall_budget_s,
        "timeout_s": args.timeout_s,
        "neither_19": list(NEITHER_19),
        "answer_key_present_at_source": (root / base.ANSWER_KEY).exists(),
        "python": sys.version.split()[0],
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "producer_cognition_model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "network_calls_during_measurement": 0,
    }
    with open(args.out, "a") as handle:
        handle.write(json.dumps(header) + "\n")
        for name in names:
            row = measure(root, name, wall_budget_s=args.wall_budget_s,
                          timeout_s=args.timeout_s)
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
            handle.flush()
            print(f"{name:<26} {str(row.get('stage')):<48} "
                  f"cands={row.get('tested_candidate_count')} "
                  f"{row.get('seconds')}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
