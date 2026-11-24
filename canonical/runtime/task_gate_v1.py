#!/usr/bin/env python3
"""Judge the ARTIFACT, not the plan: does the system do an ordinary thing to a real file?

WHY THIS EXISTS
---------------
Every measurement in this tree so far counts SURFACES: how many capabilities, how many
doors, how many goals compile, how many atoms are proved. None of them runs an ordinary
instruction against a real file and asks whether the file afterwards holds what was asked
for. `goal_compilation_benchmark_v1` comes closest and scores *which capability id was
selected*, so a plan that selects a plausible capability, binds the wrong object and writes
to the wrong directory still counts as a success. It is measured here as three failures:

    goal      "Read data.txt and write the number of lines to count.json."
    compiled  python.source.definition_count.v1        <- counts Python defs, not lines
    inputs    {"source_root": ".", ...}                <- data.txt never appears
    output    canonical/astra_runtime/tmp/...json      <- not count.json, not the workspace

So this gate is deliberately narrow and hard: a fresh directory, an ordinary sentence, a
verifier written against the OS's own tools (gunzip, tar, sqlite3, json) that never looks at
the plan. Either the artifact is right or the task failed.

WHAT EACH TASK MEASURES
-----------------------
COMPILE     the sentence could not be turned into a plan at all
ESCAPED     the plan would touch something outside the workspace -- refused, not executed
EXECUTED    a plan ran; its artifacts are then judged
WRONG       an artifact exists but does not satisfy the request
PASS        the artifact satisfies the request, judged by an independent reader

A task counts as passed only on PASS. Nothing here is hand-solved: the verifier describes
what is wanted and this module never touches the workspace between setup and judging.

Zero model calls. Zero network. No parameters. Authority: NONE (producer-run sandbox).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
import zipfile
from typing import Any, Callable, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA = "PROJECT_BRAIN_TASK_GATE_V1"

TEXT = "alpha\nbeta\ngamma\ndelta\nepsilon\n"
LOG_FILES = {"one.log": "first\n", "two.log": "second\n", "keep.txt": "third\n"}
RECORDS = [
    {"name": "ada", "age": 36}, {"name": "bob", "age": 24},
    {"name": "cy", "age": 41}, {"name": "dee", "age": 30},
    {"name": "eve", "age": 55},
]


# --------------------------------------------------------------------------- #
# tasks: a sentence, a workspace, and a verifier written against the OS
# --------------------------------------------------------------------------- #

def _setup_text(root: pathlib.Path) -> None:
    (root / "data.txt").write_text(TEXT, encoding="utf-8")


def _setup_logs(root: pathlib.Path) -> None:
    for name, body in LOG_FILES.items():
        (root / name).write_text(body, encoding="utf-8")


def _setup_records(root: pathlib.Path) -> None:
    (root / "records.json").write_text(json.dumps(RECORDS), encoding="utf-8")


def _verify_line_count(root: pathlib.Path) -> tuple[bool, str]:
    target = root / "count.json"
    if not target.exists():
        return False, "count.json absent"
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception as error:
        return False, f"count.json unreadable: {type(error).__name__}"
    values = [value for value in data.values()] if isinstance(data, dict) else [data]
    want = len(TEXT.splitlines())
    if want in values:
        return True, f"{want}"
    return False, f"no value equals {want}: {str(data)[:80]}"


def _verify_gzip(root: pathlib.Path) -> tuple[bool, str]:
    for name in ("data.txt.gz", "data.gz"):
        candidate = root / name
        if not candidate.exists():
            continue
        restored = subprocess.run(["gzip", "-dc", str(candidate)], capture_output=True)
        if restored.returncode != 0:
            return False, f"{name} is not a gzip stream"
        if restored.stdout == TEXT.encode():
            return True, name
        return False, f"{name} restores different bytes"
    others = sorted(p.name for p in root.iterdir() if p.suffix == ".gz")
    return False, f"no data.txt.gz (found {others})"


def _verify_tar_gz(root: pathlib.Path) -> tuple[bool, str]:
    wanted = {"data.txt", "one.log", "two.log"}
    for candidate in sorted(root.glob("*.tar.gz")) + sorted(root.glob("*.tgz")):
        try:
            with tarfile.open(candidate, "r:gz") as archive:
                names = {pathlib.PurePosixPath(n).name for n in archive.getnames()}
        except Exception as error:
            return False, f"{candidate.name} unreadable: {type(error).__name__}"
        if wanted <= names:
            return True, candidate.name
        return False, f"{candidate.name} holds {sorted(names)[:6]}"
    return False, "no .tar.gz produced"


def _verify_rename(root: pathlib.Path) -> tuple[bool, str]:
    left = sorted(p.name for p in root.glob("*.log"))
    made = sorted(p.name for p in root.glob("*.txt"))
    if left:
        return False, f"still .log: {left}"
    if {"one.txt", "two.txt"} <= set(made) and (root / "keep.txt").exists():
        bodies = {(root / "one.txt").read_text(), (root / "two.txt").read_text()}
        if bodies == {"first\n", "second\n"}:
            return True, "renamed, bytes intact"
        return False, "renamed but bytes changed"
    return False, f"expected one.txt and two.txt, found {made}"


def _verify_adults(root: pathlib.Path) -> tuple[bool, str]:
    target = root / "adults.txt"
    if not target.exists():
        return False, "adults.txt absent"
    names = [line.strip() for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    want = sorted(r["name"] for r in RECORDS if r["age"] > 30)
    if names == want:
        return True, ",".join(names)
    return False, f"got {names}, want {want}"


def _verify_sqlite(root: pathlib.Path) -> tuple[bool, str]:
    candidate = root / "tasks.db"
    if not candidate.exists():
        return False, "tasks.db absent"
    try:
        connection = sqlite3.connect(str(candidate))
    except Exception as error:
        return False, f"unopenable: {type(error).__name__}"
    try:
        try:
            tables = [row[0] for row in connection.execute(
                "select name from sqlite_master where type='table'")]
            if not tables:
                return False, "no table"
            for table in tables:
                rows = connection.execute(f'select * from "{table}"').fetchall()
                if rows:
                    return True, f"{table} rows={len(rows)}"
            return False, "table exists but holds no row"
        except sqlite3.DatabaseError as error:
            # a file that is not a database is a WRONG artifact, not a crash in the judge
            return False, f"not a database: {str(error)[:60]}"
    finally:
        connection.close()


def _verify_hits(root: pathlib.Path) -> tuple[bool, str]:
    target = root / "hits.txt"
    if not target.exists():
        return False, "hits.txt absent"
    text = target.read_text(encoding="utf-8").strip()
    numbers = re.findall(r"\d+", text)
    want = 0
    for path in root.rglob("*"):
        if path.is_file() and path.name != "hits.txt":
            try:
                if "error" in path.read_text(encoding="utf-8", errors="ignore"):
                    want += 1
            except OSError:
                continue
    if numbers and int(numbers[0]) == want:
        return True, str(want)
    return False, f"got {text[:40]!r}, want {want}"


def _verify_digest(root: pathlib.Path) -> tuple[bool, str]:
    target = root / "digest.json"
    if not target.exists():
        return False, "digest.json absent"
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return False, "digest.json unreadable"
    want_bytes = len(TEXT.encode())
    want_sha = hashlib.sha256(TEXT.encode()).hexdigest()
    # A SUBSTRING TEST ON THE WHOLE DOCUMENT IS NOT A CHECK. The first version asked
    # whether "31" appeared anywhere in the JSON, and a 64-character sha256 contains
    # "31" about one time in three -- so the bytes field could be missing and the task
    # would still pass. Each value is looked for as a value, under any key.
    scalars: list[Any] = []
    def _walk(node: Any, depth: int = 0) -> None:
        if depth > 4:
            return
        if isinstance(node, dict):
            for item in node.values():
                _walk(item, depth + 1)
        elif isinstance(node, (list, tuple)):
            for item in node:
                _walk(item, depth + 1)
        else:
            scalars.append(node)
    _walk(data)
    has_sha = any(isinstance(v, str) and v.lower() == want_sha for v in scalars)
    has_bytes = any(str(v) == str(want_bytes) for v in scalars)
    if has_sha and has_bytes:
        return True, "bytes+sha256"
    return False, f"sha={has_sha} bytes={has_bytes} :: {json.dumps(data)[:90]}"


TASKS: tuple[dict[str, Any], ...] = (
    {"id": "line_count",
     "instruction": "Read data.txt and write the number of lines to count.json.",
     "setup": _setup_text, "verify": _verify_line_count},
    {"id": "gzip_copy",
     "instruction": "Make a compressed copy of data.txt that gunzip can restore exactly.",
     "setup": _setup_text, "verify": _verify_gzip},
    {"id": "tar_gz_bundle",
     "instruction": "Bundle data.txt, one.log and two.log into a single tar.gz archive.",
     "setup": lambda root: (_setup_text(root), _setup_logs(root)),
     "verify": _verify_tar_gz},
    {"id": "rename_logs",
     "instruction": "Rename every .log file in this directory so it ends in .txt instead.",
     "setup": _setup_logs, "verify": _verify_rename},
    {"id": "adults_from_json",
     "instruction": "Write the names of the people in records.json who are older than 30 to "
                    "adults.txt, one name per line, in alphabetical order.",
     "setup": _setup_records, "verify": _verify_adults},
    {"id": "sqlite_row",
     "instruction": "Create tasks.db with a table called tasks and put one row in it.",
     "setup": lambda root: None, "verify": _verify_sqlite},
    {"id": "count_error_files",
     "instruction": "Count the files in this directory that mention error and write the "
                    "number to hits.txt.",
     "setup": lambda root: ((root / "a.txt").write_text("error here\n"),
                            (root / "b.txt").write_text("clean\n"),
                            (root / "c.log").write_text("error also\n")),
     "verify": _verify_hits},
    {"id": "digest_report",
     "instruction": "Write digest.json describing data.txt: how many bytes it has and its "
                    "sha256.",
     "setup": _setup_text, "verify": _verify_digest},
)


# --------------------------------------------------------------------------- #
# running one task
# --------------------------------------------------------------------------- #

def _paths_in(value: Any, into: list[str], depth: int = 0) -> None:
    if depth > 4:
        return
    if isinstance(value, str):
        into.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            _paths_in(item, into, depth + 1)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _paths_in(item, into, depth + 1)


def _escapes(root: pathlib.Path, plan: dict[str, Any]) -> list[str]:
    """Anything the plan would read or write outside the workspace.

    A plan that resolves `.` against the repository instead of the workspace is not a plan
    for this task. It is refused BEFORE execution, because executing it writes into the
    repository -- which is exactly what the compiler proposed for the first task it was
    given here.
    """
    found: list[str] = []
    _paths_in(plan.get("inputs") or {}, found)
    _paths_in(plan.get("compiled_parts") or [], found)
    bad: list[str] = []
    for text in found:
        if not text or len(text) > 400:
            continue
        looks = ("/" in text) or text.endswith((".json", ".txt", ".gz", ".tar", ".db", ".log"))
        if not looks:
            continue
        resolved = (root / text).resolve() if not os.path.isabs(text) else pathlib.Path(text).resolve()
        try:
            resolved.relative_to(root.resolve())
        except ValueError:
            if text in (".", "./"):
                continue   # the workspace itself is legitimate
            bad.append(text)
            continue
        # A PATH CAN BE INSIDE THE WORKSPACE AND STILL NOT BELONG TO IT.
        #
        # `canonical/astra_runtime/tmp/brain_out__x.json` resolved against a fresh
        # workspace is lexically inside it, and the first version of this function called
        # that safe -- while the plan meant the repository. The difference is visible
        # without knowing anything: a workspace-scoped output names a directory that the
        # workspace already has, and a repository path does not. A path needing
        # directories that do not exist here is refused rather than created.
        if os.path.isabs(text):
            continue
        parent = resolved.parent
        if not parent.exists():
            bad.append(text)
    return bad


def run_task(task: dict[str, Any], *, registry: dict[str, Any] | None = None,
             execute: bool = True, lane: str = "registry") -> dict[str, Any]:
    """Set up a fresh workspace, bind the sentence, judge the artifact.

    Two lanes, one judge:

      registry  compile through the 447-capability registry (the system as it stands)
      grounded  bind one of the MACHINE's own doors to the workspace (grounded_binder_v1)

    The verifier is identical and independent in both, so the difference between the two
    numbers is the difference between "which of our capabilities matches these words" and
    "which of this machine's doors does this sentence name".
    """
    from canonical.runtime import goal_compiler as compiler
    from canonical.runtime import live_integrated_brain_v1 as brain

    started = time.perf_counter()
    root = pathlib.Path(tempfile.mkdtemp(prefix=f"gate-{task['id']}-"))
    row: dict[str, Any] = {"id": task["id"], "instruction": task["instruction"], "lane": lane}
    try:
        task["setup"](root)
        if lane == "grounded":
            from canonical.runtime import grounded_binder_v1 as binder
            routed: list[str] = []
            try:
                from canonical.runtime import machine_self_index_v1 as index_module
                routed = [row["program"] for row in
                          index_module.route(task["instruction"], index_module.load(), limit=6)]
            except Exception:
                routed = []
            attempt = binder.run(task["instruction"], root, routed=routed)
            row["binding"] = {"outcome": attempt.get("outcome"),
                              "reason": attempt.get("reason"),
                              "plan": (attempt.get("plan") or {}).get("argv"),
                              "programs": attempt.get("programs"),
                              "named_programs": attempt.get("named_programs"),
                              "routed": routed}
            row["capabilities"] = [(attempt.get("plan") or {}).get("program")]
            ok, detail = task["verify"](root)
            row.update(outcome="PASS" if ok else
                       ("COMPILE" if attempt.get("outcome") != "EXECUTED" else "WRONG"),
                       detail=detail)
            return row
        registry = registry if registry is not None else dict(brain.load_verified_registry())
        try:
            plan = compiler.compile_goal(task["instruction"], registry, str(root))
        except Exception as error:
            row.update(outcome="COMPILE", detail=str(error)[:200])
            return row
        parts = plan.get("compiled_parts") or [plan]
        row["capabilities"] = [p.get("selected_capability") for p in parts]
        escaped = _escapes(root, plan)
        if escaped:
            row.update(outcome="ESCAPED", detail=escaped[:4])
            return row
        if execute:
            executed = []
            for part in parts:
                cid = part.get("selected_capability")
                if not cid:
                    continue
                try:
                    from canonical.runtime import verified_bound_capability_execution_adapter_v1 as adapter
                    outcome = adapter.execute(cid, inputs=dict(part.get("inputs") or {}),
                                              instance_id=f"gate-{task['id']}")
                    executed.append({"capability": cid,
                                     "pass": bool(outcome.get("pass")),
                                     "reason": str(outcome.get("reason") or "")[:120]})
                except Exception as error:
                    executed.append({"capability": cid, "pass": False,
                                     "reason": f"{type(error).__name__}: {str(error)[:100]}"})
            row["executed"] = executed
        ok, detail = task["verify"](root)
        row.update(outcome="PASS" if ok else "WRONG", detail=detail)
        return row
    finally:
        shutil.rmtree(root, ignore_errors=True)
        row["seconds"] = round(time.perf_counter() - started, 3)


def run_gate(*, execute: bool = True) -> dict[str, Any]:
    from canonical.runtime import live_integrated_brain_v1 as brain
    registry = dict(brain.load_verified_registry())
    rows = [run_task(task, registry=registry, execute=execute) for task in TASKS]
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["outcome"]] = counts.get(row["outcome"], 0) + 1
    return {"schema": SCHEMA, "tasks": len(rows), "counts": counts,
            "passed": counts.get("PASS", 0), "rows": rows,
            "model_calls": 0, "parameters": 0,
            "authority": "NONE__PRODUCER_RUN_SANDBOX"}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--no-execute", action="store_true",
                        help="compile and judge only; never run a capability")
    args = parser.parse_args(argv)
    report = run_gate(execute=not args.no_execute)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8")
    for row in report["rows"]:
        print(f"  {row['outcome']:8s} {row['id']:20s} "
              f"{', '.join(c for c in (row.get('capabilities') or []) if c)[:52]:52s} "
              f"{str(row.get('detail'))[:60]}")
    print(json.dumps({"passed": report["passed"], "of": report["tasks"],
                      "counts": report["counts"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
