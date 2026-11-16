#!/usr/bin/env python3
"""Re-run another arm's claimed repairs from its own record, with pytest as the only judge.

WHY THIS EXISTS
---------------
`QUIXBUGS_EDIT_KIND_TRANSFER_20261112_V1.json` claims 20 of 40 QuixBugs bugs repaired by edit kinds
learned from 164 HumanEvalFix fixes and no QuixBugs fix. That claim is load-bearing for the union
projection in `THE_SPACE_IS_ASSEMBLED_NOT_LISTED_20261116_V1.md`, and a projection built on an
unverified arm is worth nothing.

The record is unusually generous: for every repaired bug it stores the operator and the exact lines
the repair removed and put in. So the claim can be re-run rather than believed. This tool applies
those recorded line changes to the defective program, and asks the corpus's own pytest.

What it does NOT do: it does not re-learn the kinds, does not consult the lessons, and does not use
the screen. It is a check on a recorded claim, not a reproduction of the mechanism.

Three outcomes per bug:
  CONFIRMED            the recorded lines apply and the corpus's own pytest passes
  NOT_CONFIRMED        the corpus's own pytest fails
  INAPPLICABLE         the recorded line change does not appear in the defective source

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no network at run time.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
import time
from typing import Any, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import grammar_closed_repair_v1 as gen  # noqa: E402


def apply_lines(source: str, lines: dict[str, Any]) -> tuple[str | None, str]:
    """Put the recorded repair lines in and take the recorded removed lines out.

    The record stores line *contents* without their indentation, so this works line-wise and
    re-applies the indentation of the line it replaces. String substitution on the raw text was
    tried first and is wrong: it leaves a dedented body (`expected an indented block`) and would
    have manufactured seventeen false "inapplicable" verdicts against another arm's record.
    """
    removed = [x.strip() for x in (lines or {}).get("removed") or [] if isinstance(x, str)]
    put_in = [x.strip() for x in (lines or {}).get("put_in") or [] if isinstance(x, str)]
    if not removed and not put_in:
        return None, "NO_LINES_RECORDED"
    body = source.splitlines(keepends=True)
    for index, old in enumerate(removed):
        found = next((i for i, line in enumerate(body) if line.strip() == old), None)
        if found is None:
            return None, f"REMOVED_LINE_NOT_IN_SOURCE:{old[:60]}"
        indent = body[found][: len(body[found]) - len(body[found].lstrip())]
        replacement = put_in[index] if index < len(put_in) else None
        if replacement is None:
            body[found] = ""
        else:
            body[found] = f"{indent}{replacement}\n"
    for extra in put_in[len(removed):]:
        body.append(f"{extra}\n")
    patched = "".join(body)
    try:
        compile(patched, "<patched>", "exec")
    except SyntaxError as error:
        return None, f"PATCH_DOES_NOT_COMPILE:{error.msg}"
    return patched, "APPLIED"


def check_one(root: pathlib.Path, name: str, source: str, lines: dict[str, Any],
              verify_timeout: int) -> dict[str, Any]:
    patched, why = apply_lines(source, lines)
    row: dict[str, Any] = {"task": name, "kind": "task", "apply": why}
    if patched is None:
        row["stage"] = "INAPPLICABLE"
        return row
    with tempfile.TemporaryDirectory() as tmp:
        where = pathlib.Path(tmp)
        info = gen.build_task(root, name, where)
        (where / "python_programs" / f"{name}.py").write_text(patched)
        verdict = gen.verify_with_corpus_test(where, info["test_path"], verify_timeout)
    row["corpus_test_returncode"] = verdict["returncode"]
    row["corpus_test_tail"] = verdict["tail"]
    row["stage"] = "CONFIRMED" if verdict["returncode"] == 0 else "NOT_CONFIRMED"
    return row


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--record", required=True,
                        help="the receipt holding per_bug[*].another_benchmark.lines")
    parser.add_argument("--arm", default="another_benchmark")
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--verify-timeout", type=int, default=120)
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs)
    record = json.loads(pathlib.Path(args.record).read_text())
    per_bug = record["per_bug"]
    claimed = sorted(name for name, entry in per_bug.items()
                     if (entry.get(args.arm) or {}).get("repaired"))
    rows: list[dict[str, Any]] = []
    started = time.time()
    for name in claimed:
        source = (root / "python_programs" / f"{name}.py").read_text()
        lines = (per_bug[name][args.arm] or {}).get("lines") or {}
        try:
            row = check_one(root, name, source, lines, args.verify_timeout)
        except Exception as error:  # noqa: BLE001
            row = {"task": name, "kind": "task", "stage": f"INSTRUMENT_ERROR:{type(error).__name__}"}
        rows.append(row)
        print(f"{name:<26} {row.get('stage',''):<18} {row.get('apply','')}", flush=True)
    pathlib.Path(args.out).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    tally: dict[str, int] = {}
    for row in rows:
        tally[row["stage"]] = tally.get(row["stage"], 0) + 1
    receipt = {
        "schema": "BRAIN_RERUN_THE_LEARNED_ARMS_REPAIRS_V1",
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "model_dependency_count": 0,
        "network_calls_at_run_time": 0,
        "arm": args.arm,
        "source_record": args.record,
        "claimed_repaired": len(claimed),
        "tally": dict(sorted(tally.items())),
        "confirmed": sorted(r["task"] for r in rows if r["stage"] == "CONFIRMED"),
        "not_confirmed": sorted(r["task"] for r in rows if r["stage"] == "NOT_CONFIRMED"),
        "inapplicable": sorted(r["task"] for r in rows if r["stage"] == "INAPPLICABLE"),
        "screen_said_pass_runner_said_no_in_the_record": sum(
            int(entry.get("screen_said_pass_runner_said_no") or 0) for entry in per_bug.values()),
        "seconds": round(time.time() - started, 1),
        "rows": rows,
    }
    if args.receipt:
        pathlib.Path(args.receipt).write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({k: receipt[k] for k in ("claimed_repaired", "tally", "seconds")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
