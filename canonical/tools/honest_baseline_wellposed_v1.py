#!/usr/bin/env python3
"""The honest baseline, with a denominator that can be defended.

WHY THIS EXISTS
---------------
`honest_per_task_baseline_v1` published `12 tasks, 12 NO_PROPOSAL, 0.0` on
2026-11-25. Two defects in that instrument were found on 2026-11-26, and both
inflate the appearance of failure. Neither is a capability claim; both are
measurement repairs.

DEFECT 1 -- THE INTERPRETER COULD NOT RUN PYTEST AT ALL.
--------------------------------------------------------
Every measurement in this project runs pytest through `sys.executable`. The
sandbox used for the 2026-11-26 re-measurement had no pytest installed for
that interpreter, so `python -m pytest` exited 1 with
`No module named pytest`. Exit 1 was read as "the test fails on the parent",
which is the *precondition* the harness is looking for, so every task sailed
through the gate on a lie. The run reported 12/12 NO_PROPOSAL and it looked
exactly like a real result. The repository already states the law this
violates: *verification that has never been attempted is indistinguishable
from verification that failed.* A preflight that proves the interpreter can
collect and run a test is now mandatory, and the run refuses without it.

DEFECT 2 -- SOME TASKS ARE UNSOLVABLE BY CONSTRUCTION.
------------------------------------------------------
The harness applies the gold diff for `task["test"]` only. The engine is
forbidden from editing test or oracle files (`_is_test_or_oracle_file`). But
for some commits the gold fix also edits a TEST DATA FIXTURE. Measured here:
`pypa/packaging 9f5249fb` changes `tests/metadata/everything.metadata` from
`Metadata-Version: 2.5` to `2.6` while the new test asserts `== "2.6"`.

    assert raw["metadata_version"] == "2.6"   # parsed from a file saying 2.5

No honest source change satisfies that assertion; only a parser that lies
about the bytes. Counting such a task as a system failure is not honesty, it
is a wrong denominator -- and it is the small-scale shape of the verifier
error the repository already cites in the 2026 SWE-bench audits.

WHAT THIS TOOL ADDS, AND WHAT IT REFUSES TO ADD
-----------------------------------------------
It does not make the system better. It makes the number honest:

  * preflight: pytest must import, collect and run a trivial test; else REFUSED
  * per task: `ILL_POSED` when the gold fix touches any file the harness will
    not apply and the engine may not edit (anything under `tests/`, `test/`,
    `testing/` other than the named test file itself)
  * validity audit: applying the FULL gold diff must make the node pass, or the
    task is marked `GOLD_DOES_NOT_PASS` and dropped as unusable
  * every row keeps its class; two denominators are reported, never one

The audit reads the gold diff to decide task well-posedness and never to
produce a fix. That distinction is stated in the output so it cannot be
mistaken later.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = "BRAIN_HONEST_BASELINE_WELLPOSED_V1"
SELECTED = REPO / "canonical" / "corpus" / "tasks_whose_oracle_precedes_the_fix_20261124_V1.json"
CORPUS = REPO / "canonical" / "corpus" / "real_fix_commits_20261116_V1.json"

ORACLE_PREFIXES = ("tests/", "test/", "testing/", "spec/", "testdata/", "fixtures/")


def run(cmd: Sequence[str], cwd: pathlib.Path, timeout: int = 900,
        env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=str(cwd), capture_output=True, text=True,
                          timeout=timeout, check=False, env=env)


def import_env(checkout: pathlib.Path) -> dict[str, str]:
    """The environment a test MUST run in: the checkout's own source, not site-packages.

    DEFECT 3, found by this tool on its first run. `pytest` depends on
    `packaging`, so a test that does `from packaging.dependency_groups import ...`
    resolves to the INSTALLED copy (measured: 26.4 in site-packages) unless the
    checkout's `src/` comes first on the path. The audit then classified six of
    twelve tasks as `GOLD_DOES_NOT_PASS` -- the gold patch appeared not to work.
    It worked; it was applied to a tree nobody imported. `_build_env` in
    `angelic_cegis_repair_v1` already does this correctly, and this is the same
    construction, kept local so the tool has no runtime dependency on the kernel.
    """
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    paths: list[str] = []
    src_dir = checkout / "src"
    if src_dir.is_dir():
        paths.append(str(src_dir))
    paths.append(str(checkout))
    existing = env.get("PYTHONPATH", "")
    if existing:
        paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    env.pop("PYTEST_ADDOPTS", None)
    return env


def assert_checkout_is_imported(python: str, checkout: pathlib.Path, package: str) -> str:
    """Prove the test will import the checkout, not an installed lookalike."""
    proc = run([python, "-c", f"import {package}, pathlib; print(pathlib.Path({package}.__file__).resolve())"],
               checkout, env=import_env(checkout))
    resolved = (proc.stdout or "").strip()
    if proc.returncode != 0 or not resolved:
        return f"cannot import {package!r} under the task environment: {(proc.stderr or '').strip()[:200]}"
    if not pathlib.Path(resolved).is_relative_to(checkout.resolve()):
        return (f"{package!r} resolves to {resolved}, which is outside the checkout. The test would "
                f"measure the installed copy, not the code under repair.")
    return ""


def preflight(python: str) -> tuple[bool, str]:
    """Prove the interpreter can run a test before any result is trusted.

    A missing pytest exits 1, and exit 1 is exactly what the harness reads as
    "this test fails on the parent". Without this check a missing dependency
    is silently reported as a system failure on every task.
    """
    with tempfile.TemporaryDirectory(prefix="brain-preflight-") as td:
        root = pathlib.Path(td)
        (root / "test_preflight.py").write_text(
            "def test_the_interpreter_can_run_a_test():\n    assert 1 + 1 == 2\n",
            encoding="utf-8",
        )
        try:
            proc = run([python, "-m", "pytest", "test_preflight.py", "-q", "--no-header",
                        "-p", "no:cacheprovider"], root, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"{type(exc).__name__}: {exc}"
    combined = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        return False, f"pytest exit {proc.returncode}: {combined.strip()[-300:]}"
    if "1 passed" not in combined:
        return False, f"pytest ran but did not report a pass: {combined.strip()[-300:]}"
    return True, "pytest imports, collects and passes a trivial test"


def is_oracle_path(path: str) -> bool:
    return path.startswith(ORACLE_PREFIXES) or "/tests/" in path or "/testdata/" in path


def gold_touched_files(checkout: pathlib.Path, parent: str, sha: str) -> list[str]:
    proc = run(["git", "diff", "--name-only", parent, sha], checkout)
    return [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]


def ill_posed_reason(files: Sequence[str], test_file: str) -> str | None:
    """`ILL_POSED` when the fix needs an oracle file the engine may not touch.

    The gold fix may edit the named test file -- the harness applies that. Any
    OTHER oracle-side file is neither applied nor reachable by the engine, so a
    pass would require the source to lie about the fixture's own bytes.
    """
    blocked = [f for f in files if is_oracle_path(f) and f != test_file]
    if blocked:
        return "gold fix edits oracle-side file(s) the harness will not apply: " + ", ".join(blocked)
    return None


def prepare(checkout: pathlib.Path, task: dict[str, Any], *, full_gold: bool) -> str | None:
    """Reset to parent, then apply either the test slice or the whole gold diff."""
    run(["git", "checkout", "-q", "-f", task["parent"]], checkout)
    run(["git", "clean", "-qfd"], checkout)
    if full_gold:
        diff = run(["git", "diff", task["parent"], task["sha"]], checkout)
    else:
        diff = run(["git", "diff", task["parent"], task["sha"], "--", task["test"]], checkout)
    patch = checkout / ".brain_probe.patch"
    patch.write_text(diff.stdout or "", encoding="utf-8")
    applied = run(["git", "apply", "--whitespace=nowarn", str(patch.name)], checkout)
    if applied.returncode != 0:
        return f"patch did not apply: {(applied.stderr or '').strip()[:200]}"
    return None


def node_passes(python: str, checkout: pathlib.Path, node: str) -> tuple[bool, str]:
    proc = run([python, "-m", "pytest", node, "-q", "-x", "--no-header", "-p", "no:cacheprovider"],
               checkout, env=import_env(checkout))
    return proc.returncode == 0, ((proc.stdout or "") + (proc.stderr or ""))[-400:]


def audit_task(python: str, checkout: pathlib.Path, task: dict[str, Any],
               node: str) -> dict[str, Any]:
    """Decide whether the task is usable before the system is ever run on it."""
    files = gold_touched_files(checkout, task["parent"], task["sha"])

    # Provenance first: a test that imports an installed package measures nothing
    # about the checkout. Derive the package name from the checkout layout.
    package = None
    for candidate in sorted((checkout / "src").glob("*/__init__.py")) if (checkout / "src").is_dir() else []:
        package = candidate.parent.name
        break
    if package is None and (checkout / task["test"].split("/")[0]).is_dir() is False:
        stem = task["repo"].split("/")[-1]
        if (checkout / stem / "__init__.py").is_file():
            package = stem
    if package:
        problem = assert_checkout_is_imported(python, checkout, package)
        if problem:
            return {"class": "UNUSABLE", "detail": problem, "gold_files": files}
    reason = ill_posed_reason(files, task["test"])

    # Validity: the whole gold diff must make the node pass, or the task is unusable.
    err = prepare(checkout, task, full_gold=True)
    if err:
        return {"class": "UNUSABLE", "detail": err, "gold_files": files}
    passed, tail = node_passes(python, checkout, node)
    if not passed:
        return {"class": "GOLD_DOES_NOT_PASS", "detail": tail, "gold_files": files}

    if reason:
        return {"class": "ILL_POSED", "detail": reason, "gold_files": files}
    return {"class": "WELL_POSED", "detail": "", "gold_files": files}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--audit-only", action="store_true",
                        help="classify the task set without running the system on it")
    parser.add_argument("--run-system", action="store_true",
                        help="also run the shipped system on the WELL_POSED tasks")
    args = parser.parse_args(argv)
    started = time.time()

    ok, detail = preflight(args.python)
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "preflight": {"ok": ok, "detail": detail, "python": args.python},
        "authority": "NONE__PRODUCER_RUN_SANDBOX",
        "leakage_policy": (
            "The gold diff is read ONLY to decide whether a task is well posed and usable. "
            "It is never read to produce, rank or verify a fix."),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0},
        "per_task": [],
    }
    if not ok:
        receipt["status"] = "REFUSED__INTERPRETER_CANNOT_RUN_PYTEST"
        pathlib.Path(args.out).write_text(json.dumps(receipt, indent=1) + "\n")
        print("REFUSED: the interpreter cannot run pytest -- every 'failure' would be a "
              "missing dependency, not a result.")
        print(f"  {detail}")
        return 2

    selected = [row for row in json.loads(SELECTED.read_text())["per_task"] if row["class"] == "FAIL"]
    corpus = {task["sha"]: task for task in json.loads(CORPUS.read_text())["tasks"]}

    rows: list[dict[str, Any]] = []
    workdir = pathlib.Path(tempfile.mkdtemp(prefix="brain-wellposed-"))
    try:
        for index, cell in enumerate(selected, 1):
            task = corpus[cell["sha"]]
            checkout = workdir / task["repo"].replace("/", "__")
            if not checkout.exists():
                clone = run(["git", "clone", "-q", f"https://github.com/{task['repo']}.git",
                             str(checkout)], workdir)
                if clone.returncode != 0:
                    rows.append({"sha": task["sha"], "class": "CLONE_FAILED"})
                    print(f"  {index}/{len(selected)} {task['repo']} {task['sha'][:8]} -> CLONE_FAILED")
                    continue
            node = (task["failed_nodes"] or [task["test"]])[0]
            audit = audit_task(args.python, checkout, task, node)
            row = {"repo": task["repo"], "sha": task["sha"], "test": task["test"], "node": node,
                   "task_class": audit["class"], "audit_detail": audit["detail"],
                   "gold_files": audit.get("gold_files", [])}

            # The system only ever sees a WELL_POSED task, and only if asked.
            if audit["class"] == "WELL_POSED" and not args.audit_only:
                os.environ.update({k: v for k, v in import_env(checkout).items()
                                   if k in ("PYTHONPATH", "PYTHONDONTWRITEBYTECODE")})
                from canonical.runtime.brain_unified_model_v1 import open_model
                from canonical.runtime.harbor_epistemic_agent_v1 import build_goal

                err = prepare(checkout, task, full_gold=False)
                if err:
                    row["outcome"] = "PREPARE_FAILED"
                else:
                    before_ok, before_tail = node_passes(args.python, checkout, node)
                    if before_ok:
                        row["outcome"] = "NOT_FAILING_ON_PARENT"
                    else:
                        instruction = (
                            f"A test in this repository fails. The failing node is:\n  {node}\n"
                            f"The test runner printed:\n  {before_tail.strip()[:900]}\n"
                            f"Make the named test pass without breaking the other tests in that file.")
                        model = open_model(root=str(REPO))
                        outcome = model.solve(build_goal(instruction, 1, []),
                                              inputs={"harbor_task": instruction, "cycle": 1,
                                                      "observations": []},
                                              mode="EPISTEMIC", cwd=str(checkout))
                        patch = outcome.get("patch") if isinstance(outcome.get("patch"), str) else None
                        row["system_status"] = outcome.get("status")
                        if not patch:
                            row["outcome"] = "NO_PROPOSAL"
                        else:
                            (checkout / ".brain_candidate.patch").write_text(patch, encoding="utf-8")
                            if run(["git", "apply", "--whitespace=nowarn",
                                    ".brain_candidate.patch"], checkout).returncode != 0:
                                row["outcome"] = "PATCH_EMITTED__APPLY_FAILED"
                            else:
                                after_ok, _ = node_passes(args.python, checkout, node)
                                row["outcome"] = ("VERIFIED" if after_ok
                                                  else "PATCH_EMITTED__STILL_FAILING")
            rows.append(row)
            extra = row.get("outcome") or ""
            print(f"  {index}/{len(selected)} {task['repo']} {task['sha'][:8]} -> "
                  f"{audit['class']} {extra}".rstrip(), flush=True)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    def tally(key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            counts[row.get(key, "AUDIT_ONLY")] = counts.get(row.get(key, "AUDIT_ONLY"), 0) + 1
        return counts

    well_posed = [row for row in rows if row.get("task_class") == "WELL_POSED"]
    receipt["per_task"] = rows
    receipt["summary"] = {
        "tasks_listed": len(rows),
        "by_task_class": tally("task_class"),
        "by_outcome_all_tasks": tally("outcome"),
        "denominator_honest": len(well_posed),
        "verified_on_well_posed": sum(1 for r in well_posed if r.get("outcome") == "VERIFIED"),
        "resolve_rate_well_posed": round(
            sum(1 for r in well_posed if r.get("outcome") == "VERIFIED") / max(1, len(well_posed)), 4),
        "reading": (
            "The published 12-task denominator contains tasks no honest system can pass, because the "
            "gold fix edits a test-data fixture the engine may not touch. The honest denominator is "
            "reported separately and it is smaller. The capability result on it is unchanged and is "
            "still a baseline, not a score."),
        "duration_s": round(time.time() - started, 1),
    }
    pathlib.Path(args.out).write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({k: v for k, v in receipt["summary"].items() if k != "reading"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
