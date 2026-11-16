"""Does one demonstration buy a repair on a bug it never saw? Measured on a public corpus.

THE EXPERIMENT
--------------
Split QuixBugs' 40 published bugs by a hash of their names (so the split cannot be chosen to suit a
result). Show the system the TRAIN half as demonstrations -- defective source and repaired source --
and nothing else. Then hand it each HELD-OUT bug as a task: defective source plus the corpus's own
test file. No answer key is present in a task directory, and `build_task` asserts that per task.

A held-out repair therefore has exactly two possible sources of power:
  1. an edit template induced from a DIFFERENT program, applied because the demonstration's
     precondition (same node type, same role, same context, same old value) literally holds there;
  2. the corpus's own tests, used only to accept an edit that strictly reduces failures.
There is no model, no network, no spend, and no copying.

WHY THE SPLIT IS THE POINT
--------------------------
Any system can repair a bug whose fix it was just shown. The owner's question is whether showing a
fix ONCE buys capability that outlives the example. That is a transfer question, so it must be
measured across programs, with the teacher's answers physically absent from the task.

WHAT A REPAIR MEANS HERE
------------------------
The harness -- not the candidate generator -- applies the accepted edit to a fresh copy of the task
and runs the corpus's own published test file there. `REPAIRED` means that exit code was 0. The
generator's own bookkeeping is never the verdict.

Authority NONE. Producer-run, one sandbox, not independent verification. Not a SWE-bench score.

Usage
-----
    python3 canonical/tools/quixbugs_one_shot_transfer_measure_v1.py \
        --quixbugs /path/to/QuixBugs --out /tmp/transfer.json [--context-depth 1] [--rounds 4]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
import tempfile
import time
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.swe_kernel import induced_edit_basis_v1 as basis  # noqa: E402
from canonical.tools import quixbugs_end_to_end_repair_measure_v1 as harness  # noqa: E402

SCHEMA = "BRAIN_QUIXBUGS_ONE_SHOT_TRANSFER_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
HALF = 20


def split(names: Sequence[str], train_size: int = HALF) -> tuple[list[str], list[str]]:
    """Deterministic, result-blind split: order by the hash of the name, not by anything about the bug."""
    ordered = sorted(names, key=lambda name: hashlib.sha256(name.encode()).hexdigest())
    if not 10 <= train_size < len(ordered):
        raise ValueError("SPLIT_SIZE_OUT_OF_RANGE")
    return ordered[:train_size], ordered[train_size:]


def demonstrate(root: pathlib.Path, names: Sequence[str]) -> dict[str, list]:
    """The teacher: for each demonstration bug, the defective program and the repaired one.

    Two rungs are induced from the same demonstrations. The leaf rung swaps one operator, name or
    literal; the node rung replaces one node with a generalized pattern. They are kept apart in the
    receipt so a repair can be attributed to the rung that produced it.
    """
    pairs = [(name, (root / "python_programs" / f"{name}.py").read_text(),
              (root / "correct_python_programs" / f"{name}.py").read_text()) for name in names]
    return {"leaf": basis.induce_templates(pairs), "node": basis.induce_node_templates(pairs)}


def repair(root: pathlib.Path, name: str, templates: dict[str, list], *,
           rounds: int, max_candidates: int, timeout_s: int, wall_budget_s: float = 180.0) -> dict[str, Any]:
    """Search the induced basis against one held-out bug, accepting only oracle-confirmed progress."""
    from canonical.runtime.bound_capabilities import python_iterative_software_repair_loop_v1 as loop
    patch_module = loop._PATCH

    row: dict[str, Any] = {"task": name, "kind": "task", "rounds_used": 0, "candidates_tested": 0,
                          "accepted": []}
    started = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        where = pathlib.Path(tmp) / name
        row.update(harness.build_task(root, name, where))
        target = where / row["program_path"]
        original = target.read_text()

        argv = [sys.executable, "-m", "pytest", row["test_path"], "-q", "-p", "no:cacheprovider"]
        env = patch_module._source_env(where)
        baseline = patch_module._run_tests(where, argv, timeout_s, env)
        row["baseline"] = {"returncode": baseline.get("returncode"), "timed_out": baseline.get("timed_out")}
        score = loop._score(baseline)
        if baseline.get("returncode") == 0:
            row["stage"] = "DEFECT_DOES_NOT_REPRODUCE"
            return row
        if score is None:
            row["stage"] = "BASELINE_METRIC_UNPARSEABLE"
            return row
        row["baseline_failure_score"] = score

        current = original
        deadline = time.monotonic() + wall_budget_s
        for round_index in range(1, rounds + 1):
            if score == 0:
                break
            candidates = (basis.candidates_from_templates(current, templates["leaf"], max_candidates=max_candidates)
                          + basis.candidates_from_node_templates(current, templates["node"],
                                                                 max_candidates=max_candidates))
            row["rounds_used"] = round_index
            row["candidates_offered"] = row.get("candidates_offered", 0) + len(candidates)
            improved = None
            for candidate in candidates:
                if time.monotonic() > deadline:
                    row["wall_exhausted"] = True
                    break
                row["candidates_tested"] += 1
                target.write_text(candidate["source"])
                loop._purge({target})
                result = patch_module._run_tests(where, argv, timeout_s, env)
                new_score = loop._score(result)
                if new_score is not None and new_score < score:
                    improved = {"candidate": candidate, "score_before": score, "score_after": new_score}
                    current = candidate["source"]
                    score = new_score
                    break
            target.write_text(current)
            loop._purge({target})
            if improved is None:
                row["stage"] = ("WALL_DEADLINE_EXHAUSTED" if row.get("wall_exhausted")
                                else "NO_STRICTLY_IMPROVING_CANDIDATE_IN_BASIS")
                break
            template = improved["candidate"]["template"]
            row["accepted"].append({
                "round": round_index, "mutation": improved["candidate"]["mutation"],
                "template_id": improved["candidate"]["template_id"],
                "rung": template.get("rung", "LEAF_SUBSTITUTION"),
                "template_kind": template["kind"], "template_context": template["context"],
                "taught_by": template["taught_by"], "template_support": template.get("support"),
                "taught_by_self": name in template["taught_by"],
                "score_before": improved["score_before"], "score_after": improved["score_after"],
                "final_source_sha256": hashlib.sha256(current.encode()).hexdigest()})
        if score == 0:
            row["stage"] = "REPAIRED__CORPUS_TEST_PASSES"
        elif "stage" not in row:
            row["stage"] = "OPEN__ROUND_BUDGET_EXHAUSTED"

        # Independent verdict: fresh task copy, the accepted source written in, the corpus's own test.
        if row["stage"] == "REPAIRED__CORPUS_TEST_PASSES":
            fresh = pathlib.Path(tmp) / (name + "__verify")
            harness.build_task(root, name, fresh)
            (fresh / row["program_path"]).write_text(current)
            verdict = harness.run_pytest(fresh, row["test_path"], timeout=timeout_s)
            row["verification"] = verdict
            if verdict["returncode"] != 0:
                row["stage"] = "NOT_VERIFIED__INDEPENDENT_RERUN_FAILED"
        row["seconds"] = round(time.time() - started, 1)
        return row


def summarise(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    repaired = [r for r in rows if r.get("stage") == "REPAIRED__CORPUS_TEST_PASSES"]
    # Transfer is DERIVED from who taught the accepted edit, never read from a flag the row set
    # about itself: a repair accepted from a template that names its own task is self-teaching, and
    # a repair accepted from a template taught elsewhere is the only thing this measurement counts.
    transferred = [r for r in repaired
                   if any(str(r["task"]) not in (a.get("taught_by") or [])
                          for a in (r.get("accepted") or []))]
    by_stage: dict[str, list[str]] = {}
    for row in rows:
        by_stage.setdefault(str(row.get("stage")), []).append(str(row["task"]))
    return {
        "held_out_tasks": len(rows),
        "repaired": len(repaired),
        "repaired_by_transferred_edit": len(transferred),
        "repaired_tasks": sorted(r["task"] for r in repaired),
        "by_stage": {k: {"count": len(v), "tasks": sorted(v)} for k, v in sorted(by_stage.items())},
        "by_rung": {rung: sorted({r["task"] for r in repaired
                                  if any(a.get("rung") == rung for a in (r.get("accepted") or []))})
                    for rung in ("LEAF_SUBSTITUTION", "NODE_SUBSTITUTION")},
        "transfers": [{"task": r["task"],
                       "mutation": (r.get("accepted") or [{}])[0].get("mutation"),
                       "taught_by": (r.get("accepted") or [{}])[0].get("taught_by")} for r in repaired],
        "seconds_total": round(sum(float(r.get("seconds") or 0) for r in rows), 1),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--train-size", type=int, default=HALF)
    parser.add_argument("--context-depth", type=int, default=1)
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--max-candidates", type=int, default=200)
    parser.add_argument("--timeout-s", type=int, default=120)
    parser.add_argument("--limit", type=int, default=0, help="smoke: only the first N held-out tasks")
    parser.add_argument("--wall-budget-s", type=float, default=180.0)
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs).resolve()
    names = harness.tasks_of(root)
    train, held_out = split(names, args.train_size)
    templates = demonstrate(root, train)
    ladder = {name: basis.classify_fix_shape((root / "python_programs" / f"{name}.py").read_text(),
                                             (root / "correct_python_programs" / f"{name}.py").read_text())
              for name in names}
    ladder_counts = {rung: sorted(n for n, v in ladder.items() if v["rung"] == rung) for rung in basis.RUNGS}
    payload: dict[str, Any] = {
        "schema": SCHEMA, "authority": AUTHORITY, "upstream": harness.UPSTREAM,
        "train": train, "held_out": held_out, "context_depth": args.context_depth,
        "executable_leaf_template_count": sum(1 for t in templates["leaf"] if t.executable),
        "leaf_templates": [t.as_dict() for t in templates["leaf"]],
        "node_templates": [t.as_dict() for t in templates["node"]],
        "expressibility_ladder_all_40": {k: {"count": len(v), "tasks": v} for k, v in ladder_counts.items()},
        "expressibility_one_node_or_leaf": len(ladder_counts["RUNG_LEAF"]) + len(ladder_counts["RUNG_NODE"]),
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "producer_cognition_model_dependency_count": 0, "incremental_spend_usd": 0,
        "network_calls_during_measurement": 0,
        "rows": [],
    }
    print(f"trained on {len(train)} demonstrations -> {payload['executable_leaf_template_count']} leaf "
          f"+ {len(templates['node'])} node templates; held out {len(held_out)}", flush=True)
    print(f"ladder over all 40: { {k: len(v) for k, v in ladder_counts.items()} }", flush=True)
    for name in (held_out[:args.limit] if args.limit else held_out):
        row = repair(root, name, templates, rounds=args.rounds, max_candidates=args.max_candidates,
                     timeout_s=args.timeout_s, wall_budget_s=args.wall_budget_s)
        payload["rows"].append(row)
        print(f"{name:<28} {str(row.get('stage')):<46} cands={row.get('candidates_tested')} "
              f"{row.get('seconds')}s", flush=True)
    payload["summary"] = summarise(payload["rows"])
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps(payload["summary"], indent=2)[:2000], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
