#!/usr/bin/env python3
"""A bug is searchable when the observable exists — and for nine of the forty it did not.

WHAT WAS BROKEN
---------------
The grammar-closed repairer reads the corpus's `json_testcases/<name>.json` to decide whether a
candidate is improving. Nine of the forty QuixBugs bugs ship no JSON: their cases are built as
objects inside `python_testcases/test_<name>.py` (`Node("Westminster", …)`, graph edges, assertions
of a printed sentence). For those nine the repairer reported `NO_EXAMPLES` and never searched at all.

That is not a search failure and not a budget failure. It is the vocabulary wall the user names as
mechanic 2: **the causal observable was missing from the representation**, so repetition could not
separate success from failure — there was nothing to separate.

WHAT THIS DOES
--------------
For exactly those tasks, the corpus's own test file becomes the observable. Candidates from the same
five rewrite families are screened against the untouched test file through the tree's existing
confined screen (`quixbugs_edit_kind_transfer_measure_v1.screen`, copy-on-write workers, one case
per candidate), and any survivor is then put through the corpus's real `pytest` on a fresh copy —
the same judge every other measurement in this tree uses.

Nothing here is new vocabulary: the edit families are the ones already merged. What is new is that
the families can finally *see* these nine bugs. That is the whole claim, and it is deliberately a
small one: a mechanism that could not run now runs.

Authority: NONE. Producer-run sandbox measurement. No model, no weights, no network at run time.
"""
from __future__ import annotations

import argparse
import ast
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
import quixbugs_edit_kind_transfer_measure_v1 as screen_mod  # noqa: E402

MAX_CANDIDATES = 6000


def searchable_only_by_the_suite(root: pathlib.Path, names: Sequence[str]) -> list[str]:
    """The tasks whose cases live in the test file and nowhere else."""
    have_json = {p.stem for p in (root / "json_testcases").glob("*.json")}
    tests = {p.name[5:-3] for p in (root / "python_testcases").glob("test_*.py")}
    return [n for n in names if n in tests and n not in have_json]


def candidates_for(root: pathlib.Path, name: str) -> tuple[list[str], str | None]:
    source = (root / "python_programs" / f"{name}.py").read_text()
    tree = ast.parse(source)
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef)), None)
    if function is None:
        return [], None
    seen: set[str] = set()
    out: list[str] = []
    for candidate in gen._enumerate(tree, gen.atoms_of(function)):
        text = candidate["source"]
        if text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= MAX_CANDIDATES:
            break
    return out, function.name


def measure_task(root: pathlib.Path, name: str, *, verify_timeout: int) -> dict[str, Any]:
    started = time.time()
    row: dict[str, Any] = {"task": name, "kind": "task"}
    programs, function_name = candidates_for(root, name)
    row["candidates"] = len(programs)
    if not programs:
        row["stage"] = "NO_CANDIDATES"
        return row
    try:
        with tempfile.TemporaryDirectory() as tmp:
            project = screen_mod.screen_project(root, name, pathlib.Path(tmp))
            index = screen_mod.screen(project, name, programs)
    except Exception as error:  # noqa: BLE001
        row["stage"] = f"SCREEN_UNAVAILABLE:{type(error).__name__}"
        row["seconds"] = round(time.time() - started, 1)
        return row
    if index is None:
        row["stage"] = "NOT_REPAIRED__NO_SURVIVOR_AT_THE_SCREEN"
        row["seconds"] = round(time.time() - started, 1)
        return row

    winner = programs[index]
    row["accepted_at_screen_rank"] = index
    row["accepted_source_sha256"] = hashlib.sha256(winner.encode()).hexdigest()
    # The screen is a filter, never the verdict. The corpus's own pytest decides.
    with tempfile.TemporaryDirectory() as tmp:
        where = pathlib.Path(tmp)
        info = gen.build_task(root, name, where)
        (where / "python_programs" / f"{name}.py").write_text(winner)
        verdict = gen.verify_with_corpus_test(where, info["test_path"], verify_timeout)
    row["corpus_test_returncode"] = verdict["returncode"]
    row["corpus_test_tail"] = verdict["tail"]
    row["stage"] = ("REPAIRED__CORPUS_TEST_PASSES" if verdict["returncode"] == 0
                    else "SCREEN_ACCEPTED__CORPUS_TEST_FAILS")
    row["seconds"] = round(time.time() - started, 1)
    return row


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", required=True)
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt", default=None)
    parser.add_argument("--verify-timeout", type=int, default=120)
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs)
    all_tests = sorted(p.name[5:-3] for p in (root / "python_testcases").glob("test_*.py"))
    names = args.tasks or searchable_only_by_the_suite(root, all_tests)
    rows: list[dict[str, Any]] = []
    with pathlib.Path(args.out).open("w") as handle:
        for name in names:
            try:
                row = measure_task(root, name, verify_timeout=args.verify_timeout)
            except Exception as error:  # noqa: BLE001
                row = {"task": name, "kind": "task", "stage": f"INSTRUMENT_ERROR:{type(error).__name__}"}
            rows.append(row)
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            print(f"{name:<26} {row.get('stage',''):<44} cands={row.get('candidates','?'):<6} "
                  f"{row.get('seconds','?')}s", flush=True)
    if args.receipt:
        repaired = [r["task"] for r in rows if r.get("stage") == "REPAIRED__CORPUS_TEST_PASSES"]
        receipt = {
            "schema": "BRAIN_REPAIR_WHERE_THE_SUITE_IS_THE_OBSERVABLE_V1",
            "authority": "NONE__PRODUCER_RUN_SANDBOX",
            "model_dependency_count": 0,
            "external_capability_provider_count": 0,
            "network_calls_at_run_time": 0,
            "why": ("nine of the forty QuixBugs bugs ship no json_testcases, so the examples-based "
                    "search reported NO_EXAMPLES and never ran; their cases are objects and "
                    "assertions inside their own test file"),
            "tasks_with_no_json": all_tests and [n for n in all_tests
                                                 if n not in {p.stem for p in (root / "json_testcases").glob("*.json")}],
            "tasks_measured": len(rows),
            "repaired": len(repaired),
            "repaired_tasks": sorted(repaired),
            "stages": _tally(r.get("stage") for r in rows),
            "rows": list(rows),
        }
        pathlib.Path(args.receipt).write_text(json.dumps(receipt, indent=1) + "\n")
    return 0


def _tally(values) -> dict[str, int]:
    out: dict[str, int] = {}
    for value in values:
        out[str(value)] = out.get(str(value), 0) + 1
    return dict(sorted(out.items()))


if __name__ == "__main__":
    raise SystemExit(main())
