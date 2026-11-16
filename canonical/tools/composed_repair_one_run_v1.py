#!/usr/bin/env python3
"""Three vocabularies, one run, one judge.

WHY THIS EXISTS
---------------
Every number this project has quoted for repair came from a *different* run of a *different*
mechanism, and the best number it ever published was a projection: take the 18 bugs one arm repairs,
take the 16 another arm's record confirms, union them, and call it 24 of 40. A projection is not a
capability. Nothing has ever run the arms together and let one command decide.

That is what this is. For each bug, the arms are tried in order of measured cost, and the first
candidate that the corpus's own pytest accepts wins:

  1. SYNTHESIZED_FROM_THE_FAILURE  build the expression the failure implies from the live scope at
                                   return (~2,000 evaluations, ~0.2 s). No vocabulary at all.
  2. REWRITE_FAMILIES              the grammar-closed families, seeded from the program's own atoms,
                                   under a per-task budget.
  3. RECORDED_LEARNED_REPAIR       an edit kind learned from another corpus, replayed from its own
                                   record's removed/put-in lines. The lesson corpus is not in this
                                   repository, so this arm is *replayed*, never re-learned -- and it
                                   is labelled that way in every row.

The judge is always the corpus's own `pytest` on a fresh copy with the answer key absent. An arm that
proposes nothing loses nothing; an arm that proposes something the judge refuses loses to the next.

What this can and cannot claim: it measures what *this* composition achieves here. It does not show
the arms are independent in principle, and the recorded arm is a replay, so this is the strongest
number available in this sandbox and not the strongest number available in principle.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no network at run time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import tempfile
import time
from typing import Any, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import grammar_closed_repair_v1 as gen  # noqa: E402
import rerun_the_learned_arms_repairs_v1 as replay  # noqa: E402
import synthesized_expression_from_the_failure_v1 as synth  # noqa: E402

ARMS = ("SYNTHESIZED_FROM_THE_FAILURE", "REWRITE_FAMILIES", "RECORDED_LEARNED_REPAIR")


def judged(root: pathlib.Path, name: str, patched: str, verify_timeout: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        where = pathlib.Path(tmp)
        info = gen.build_task(root, name, where)
        (where / "python_programs" / f"{name}.py").write_text(patched)
        return gen.verify_with_corpus_test(where, info["test_path"], verify_timeout)


def measures_one(root: pathlib.Path, name: str, *, budget_s: float, per_example_timeout: float,
                 verify_timeout: int, recorded: dict[str, Any]) -> dict[str, Any]:
    started = time.time()
    row: dict[str, Any] = {"task": name, "kind": "task", "arms_tried": [], "arms_rejected": 0}
    source = (root / "python_programs" / f"{name}.py").read_text()
    examples = gen.examples_of(root, name)
    row["examples"] = len(examples)
    if not gen._install_alarm():
        row["stage"] = "UNMEASURABLE__NO_TIMER"
        return row

    # ---- arm 1: synthesized from the failure (cheapest, no vocabulary)
    if examples:
        try:
            found = synth.synthesize_return(source, _function_name(source), examples,
                                            per_example_timeout, depth=3)
        except Exception:  # noqa: BLE001
            found = {"status": "ARM_ERROR"}
        row["arms_tried"].append("SYNTHESIZED_FROM_THE_FAILURE")
        if found.get("status") == "FOUND":
            for expression in found.get("expressions", []):
                patched = synth.install_return(source, _function_name(source), expression)
                if patched is None:
                    continue
                if gen.score(patched, _function_name(source), examples, per_example_timeout) != len(examples):
                    continue
                verdict = judged(root, name, patched, verify_timeout)
                if verdict["returncode"] == 0:
                    row.update(stage="REPAIRED", winner="SYNTHESIZED_FROM_THE_FAILURE",
                               expression=expression, seconds=round(time.time() - started, 1))
                    return row
                row["arms_rejected"] += 1

    # ---- arm 2: the grammar-closed rewrite families
    row["arms_tried"].append("REWRITE_FAMILIES")
    families = gen.repair_task(root, name, budget_s=budget_s,
                               per_example_timeout=per_example_timeout,
                               verify_timeout=verify_timeout)
    if families.get("stage") == "REPAIRED__CORPUS_TEST_PASSES":
        row.update(stage="REPAIRED", winner="REWRITE_FAMILIES",
                   candidates_tested=families.get("candidates_tested"),
                   edit=families.get("edit"), seconds=round(time.time() - started, 1))
        return row

    # ---- arm 3: the learned kind, replayed from its own record
    if recorded.get("repaired") and recorded.get("lines"):
        row["arms_tried"].append("RECORDED_LEARNED_REPAIR")
        patched, why = replay.apply_lines(source, recorded["lines"])
        if patched is not None:
            verdict = judged(root, name, patched, verify_timeout)
            if verdict["returncode"] == 0:
                row.update(stage="REPAIRED", winner="RECORDED_LEARNED_REPAIR",
                           replay=why, seconds=round(time.time() - started, 1))
                return row
            row["arms_rejected"] += 1
        else:
            row["recorded_arm"] = why

    row["stage"] = families.get("stage", "NOT_REPAIRED")
    row["seconds"] = round(time.time() - started, 1)
    return row


def _function_name(source: str) -> str:
    import ast
    tree = ast.parse(source)
    return next(n.name for n in tree.body if isinstance(n, ast.FunctionDef))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--record", required=True,
                        help="QUIXBUGS_EDIT_KIND_TRANSFER record holding per_bug[*].another_benchmark")
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--budget-s", type=float, default=45.0)
    parser.add_argument("--per-example-timeout", type=float, default=0.05)
    parser.add_argument("--verify-timeout", type=int, default=120)
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs)
    record = json.loads(pathlib.Path(args.record).read_text())["per_bug"]
    names = args.tasks or sorted(p.stem for p in (root / "python_programs").glob("*.py")
                                 if not p.stem.endswith("_test"))
    rows: list[dict[str, Any]] = []
    started = time.time()
    with pathlib.Path(args.out).open("w") as handle:
        for name in names:
            rec = (record.get(name) or {}).get("another_benchmark") or {}
            try:
                row = measures_one(root, name, budget_s=args.budget_s,
                                   per_example_timeout=args.per_example_timeout,
                                   verify_timeout=args.verify_timeout, recorded=rec)
            except Exception as error:  # noqa: BLE001
                row = {"task": name, "kind": "task", "stage": f"INSTRUMENT_ERROR:{type(error).__name__}"}
            rows.append(row)
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            print(f"{name:<26}{row.get('stage',''):<46}{row.get('winner','') or '':<30}"
                  f"{row.get('seconds','?')}s", flush=True)
    repaired = [r for r in rows if r.get("stage") == "REPAIRED"]
    by_arm: dict[str, list[str]] = {}
    for r in repaired:
        by_arm.setdefault(r["winner"], []).append(r["task"])
    receipt = {
        "schema": "BRAIN_COMPOSED_REPAIR_ONE_RUN_V1",
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_dependency_count": 0,
        "external_capability_provider_count": 0,
        "network_calls_at_run_time": 0,
        "arms_in_order": list(ARMS),
        "recorded_arm_is_a_replay": True,
        "recorded_arm_note": ("the lesson corpus is not in this repository, so the learned kinds are "
                              "replayed from their own record's removed/put-in lines and never re-learned"),
        "tasks": len(rows),
        "repaired": len(repaired),
        "by_arm": {k: sorted(v) for k, v in sorted(by_arm.items())},
        "stages": _tally(r.get("stage") for r in rows),
        "seconds": round(time.time() - started, 1),
        "rows": rows,
    }
    if args.receipt:
        pathlib.Path(args.receipt).write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({k: receipt[k] for k in ("tasks", "repaired", "by_arm", "stages", "seconds")}, indent=1))
    return 0


def _tally(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[str(value)] = out.get(str(value), 0) + 1
    return dict(sorted(out.items()))


if __name__ == "__main__":
    raise SystemExit(main())
