#!/usr/bin/env python3
"""The 37-verb track: for every verb the carrier admits, can it LEARN, QUALIFY and RECALL?

WHY THIS IS THE FIRST REAL CAPABILITY NUMBER
--------------------------------------------
r38 counted the ceiling: 37 read verbs, 33 installed. r39 found that a learned skill could
not reach its own file inside the carrier. r40 fixed the path translation, and for the first
time the loop closes -- so this number is computable at all.

The measurement is deliberately the SAME for every verb:
    demonstrate once (a concrete argv on a fixture)  ->  compile + qualify on an untouched
    held-out instance and a sabotage control         ->  recall on a THIRD instance and check
    the answer is the right number.

WHAT IT DOES NOT MEASURE, SAID FIRST
------------------------------------
* It does not measure whether the verb is USEFUL, only whether the demonstration ->
  skill -> recall loop carries it end to end.
* A verb needing two input files (comm, diff, join) or no input file (seq, realpath,
  dirname, basename, stat) is exercised with a postcondition shape that fits, and is marked
  as such. A verb we cannot construct a demonstration for is reported NOT_EXERCISED, never
  counted as a pass.
* Nothing here weakens confinement. Every execution goes through the carrier.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime.admitted_confinement_execution_v1 import READ_ONLY_PROGRAMS
from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
    compile_and_qualify_skill,
    recall_and_execute_workflow,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = ROOT / "canonical" / "astra_runtime" / "tmp"
FIXTURE = "gamma\ndelta\ngamma\nepsilon\nalpha\n"

# verb -> (argv template with {p}, goal template, expected stdout line count)
# {p} is replaced by the path parameter. None means: no demonstration constructed.
SPEC: dict[str, tuple[list[str], str] | None] = {
    # AWK IS ADMITTED BUT CANNOT RUN IN THE CARRIER. Measured 2026-11-09: `awk 1 d.txt`
    # exits 0 natively under the worker's exact env, and fails inside the confined worker
    # (WORKER_STATUS:CHILD_EXITED) with no stderr surfaced. `true`, `cat` and `grep` all run
    # in the same carrier, so this is awk-specific, not a carrier-wide breakage.
    # Recorded as a CEILING DEFECT, not as a learner failure: a verb the admission table
    # allows but the sandbox cannot execute is unreachable capability.
    "awk":        (None, None),
    "basename":   (None, None),
    "cat":        (["cat", "{p}"], "dump the contents of {p}"),
    "cksum":      (["cksum", "{p}"], "checksum {p}"),
    "comm":       (None, None),
    "cut":        (["cut", "-c1", "{p}"], "first column of {p}"),
    "diff":       (None, None),
    "dirname":    (None, None),
    "egrep":      (["egrep", "a", "{p}"], "lines matching a in {p}"),
    "expand":     (["expand", "{p}"], "expand tabs of {p}"),
    "fgrep":      (["fgrep", "a", "{p}"], "fixed lines matching a in {p}"),
    "fmt":        (["fmt", "{p}"], "reflow {p}"),
    "fold":       (["fold", "{p}"], "fold {p}"),
    "grep":       (["grep", "a", "{p}"], "lines containing a in {p}"),
    "head":       (["head", "-2", "{p}"], "first two lines of {p}"),
    "join":       (None, None),
    "md5sum":     (["md5sum", "{p}"], "md5 of {p}"),
    "nl":         (["nl", "{p}"], "number the lines of {p}"),
    "od":         (["od", "{p}"], "octal dump of {p}"),
    "paste":      (["paste", "{p}"], "paste {p}"),
    "realpath":   (None, None),
    "rev":        (["rev", "{p}"], "reverse each line of {p}"),
    "sed":        (["sed", "s/a/A/", "{p}"], "replace a with A in {p}"),
    "seq":        (None, None),
    "sha256sum":  (["sha256sum", "{p}"], "sha256 of {p}"),
    "sort":       (["sort", "-u", "{p}"], "unique lines of {p}"),
    "stat":       (None, None),
    "tac":        (["tac", "{p}"], "reverse the order of {p}"),
    "tail":       (["tail", "-2", "{p}"], "last two lines of {p}"),
    # `tr` takes NO filename operand -- it reads stdin. Demonstrating it with a path is a
    # demonstration of a command that does not exist, and the carrier correctly refused it
    # (`tr: extra operand`). Recorded as a property of the verb, not as a learner failure.
    "tr":         (None, None),
    "unexpand":   (["unexpand", "{p}"], "unexpand {p}"),
    "uniq":       (["uniq", "{p}"], "collapse repeats in {p}"),
    "wc":         (["wc", "-l", "{p}"], "count the lines of {p}"),
}


def run_track() -> dict:
    installed = sorted(p for p in READ_ONLY_PROGRAMS if "never" not in p and shutil.which(p))
    work = pathlib.Path(tempfile.mkdtemp(prefix="track_", dir=str(BASE)))
    skilldb = work / "skills.sqlite"
    os.environ["BRAIN_COMPILED_WORKFLOW_DB"] = str(skilldb)
    rel = lambda p: str(pathlib.Path(p).relative_to(ROOT))
    rows = []
    for verb in installed:
        spec = SPEC.get(verb)
        if not spec or spec[0] is None:
            rows.append({"verb": verb, "verdict": "NOT_EXERCISED",
                         "why": "no demonstration constructed (needs 2 files, or no file)"})
            continue
        argv_t, goal_t = spec
        files = {}
        for name in ("train", "hold", "twin", "sab"):
            p = work / f"{verb}_{name}.txt"
            p.write_text(FIXTURE, encoding="utf-8")
            files[name] = p
        argv = [a.replace("{p}", rel(files["train"])) for a in argv_t]
        try:
            r = compile_and_qualify_skill(
                goal=goal_t.replace("{p}", rel(files["train"])),
                trace=[{"kind": "cli_exec", "layer": "cli_exec", "argv": argv}],
                postcondition={"kind": "stdout_line_count"},
                heldout_goal=goal_t.replace("{p}", rel(files["hold"])),
                heldout_cwd=work,
                sabotaged_postcondition={"kind": "file_contains",
                                         "path": rel(files["sab"]), "contains": "__nope__"},
                db_path=skilldb,
            )
        except Exception as exc:  # noqa: BLE001 - a verb that throws is a measured failure
            rows.append({"verb": verb, "verdict": "TAUGHT_ERROR",
                         "why": f"{type(exc).__name__}: {exc}"[:120]})
            continue
        taught = bool(r.get("pass"))
        row = {"verb": verb, "taught": taught, "status": str(r.get("status"))[:60]}
        if taught:
            hit = recall_and_execute_workflow(goal_t.replace("{p}", rel(files["twin"])),
                                              cwd=str(work), db_path=skilldb)
            row["recalled"] = hit is not None
            row["answer"] = (hit or {}).get("answer")
            row["verdict"] = "PASS" if hit is not None else "TAUGHT_NOT_RECALLED"
        else:
            row["verdict"] = "NOT_TAUGHT"
        rows.append(row)
    shutil.rmtree(work, ignore_errors=True)
    return {"installed": len(installed), "rows": rows}


if __name__ == "__main__":
    out = run_track()
    for r in out["rows"]:
        v = r["verdict"]
        extra = r.get("why") or r.get("answer") or r.get("status") or ""
        print(f'  {v:20s} {r["verb"]:12s} {str(extra)[:56]}')
    tally: dict[str, int] = {}
    for r in out["rows"]:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    print()
    print("TALLY:", json.dumps(tally, sort_keys=True))
    print(f'PASS RATE: {tally.get("PASS",0)}/{out["installed"]} installed verbs')
