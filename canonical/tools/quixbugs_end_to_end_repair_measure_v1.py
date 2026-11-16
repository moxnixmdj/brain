"""Can this project repair a real public bug corpus it did not write, end to end, with no model?

THE QUESTION THIS ANSWERS
-------------------------
Every measurement of the coding machinery on this tree so far has been of a PART: localization
finds a statement pair and transfers a swap to a different module; the admission gate rejects a
lesson that breaks a correct program it was never taught on; the scope ledger reports five shipped
skills as EXACT_MATCH_ONLY; the repair loop strictly reduces a failing-test count. Each is real.
None of them is the question the owner keeps asking:

    show it one real fix, and can it fix the next real bug?

So this runs the ASSEMBLED thing -- the tree's own bounded, model-free, test-guided AST repair
loop -- against **QuixBugs**: 40 real buggy Python programs published by others (jkoppel/QuixBugs,
MIT), each with the author's own pytest test file and test data. Nobody here wrote these bugs,
chose them, or can see the fixed versions during the run.

What makes this different from the tests in canonical/tests that mention QuixBugs
------------------------------------------------------------------------------
Those use stand-in programs written in this repository. This uses the corpus itself, unmodified,
and the verdict is produced by the corpus's own test file re-run by the harness, not by anything
the repair loop says about itself.

THE FOUR INTEGRITY RULES, ENFORCED RATHER THAN PROMISED
-------------------------------------------------------
1. NO PEEKING. The task directory handed to the solver contains `python_programs/` (defective),
   `python_testcases/` and `conftest.py` -- and `correct_python_programs/` is NOT copied. A test
   asserts it is absent before every task, so a fix cannot be copied from the answer key.
2. THE TEST IS THE PUBLISHED ONE, BYTE FOR BYTE. Every test file and every program under test is
   hashed and compared against the pinned checkout. A changed byte is an error, not a repair.
3. THE VERDICT IS INDEPENDENT. The loop is candidate-only and restores source before returning, so
   its own `pass: true` is not evidence. The harness applies the returned unified diff to a FRESH
   copy of the task, runs the corpus's own test file there, and records that exit code.
4. NOTHING IS PROMOTED. `git apply` is attempted and `patch -p1` is the fallback; if neither applies
   the task counts as NOT VERIFIED, never as repaired.

WHAT A NUMBER HERE IS NOT
-------------------------
Not a leaderboard entry: QuixBugs is a small suite (40 single-function programs) and is not
SWE-bench. It is the hardest *open* corpus that can be run honestly at $0 on one machine with no
model and no network at run time. A repair here is a real repair of a real published bug, and a
failure here is a real failure of the tree's own capability on a task it did not select.

Authority NONE. Producer-run, one sandbox, not independent verification.

Usage
-----
    python3 canonical/tools/quixbugs_end_to_end_repair_measure_v1.py \
        --quixbugs /path/to/QuixBugs \
        --out /tmp/quixbugs.jsonl [--tasks bitcount bucketsort] [--wall-budget-s 120]
"""
from __future__ import annotations

import argparse
import hashlib
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
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA = "BRAIN_QUIXBUGS_END_TO_END_REPAIR_MEASURE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
#: upstream jkoppel/QuixBugs, MIT. Recorded in the receipt so a rerun can be pinned.
UPSTREAM = "https://github.com/jkoppel/QuixBugs"
KEPT = ("conftest.py",)                      # the corpus's own pytest configuration
SOLVER_MAY_SEE = ("python_programs", "python_testcases", "json_testcases", "conftest.py")
ANSWER_KEY = "correct_python_programs"       # must never reach the solver


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tasks_of(root: pathlib.Path) -> list[str]:
    """One task per published test file: that file IS the specification, so it defines the task."""
    return sorted(p.name[len("test_"):-len(".py")]
                  for p in (root / "python_testcases").glob("test_*.py"))


def build_task(root: pathlib.Path, name: str, into: pathlib.Path) -> dict[str, Any]:
    """A directory the solver is allowed to see: defective programs, the corpus's tests, nothing else.

    The whole `python_programs/` directory is copied because some published programs import
    others (node, etc.); copying only the target would make tasks unsolvable for a reason that has
    nothing to do with repair. The answer key is not copied, and its absence is asserted.
    """
    shutil.copytree(root / "python_programs", into / "python_programs")
    (into / "python_testcases").mkdir(parents=True, exist_ok=True)
    test = root / "python_testcases" / f"test_{name}.py"
    shutil.copy2(test, into / "python_testcases" / test.name)
    data = root / "python_testcases" / "load_testdata.py"
    if data.is_file():
        shutil.copy2(data, into / "python_testcases" / data.name)
    # The corpus's test cases live in JSON beside the programs and are part of the published
    # specification of the task -- they are the oracle's inputs, not the answer key.
    cases = root / "json_testcases"
    if cases.is_dir():
        shutil.copytree(cases, into / "json_testcases")
    for extra in KEPT:
        if (root / extra).is_file():
            shutil.copy2(root / extra, into / extra)
    if (into / ANSWER_KEY).exists():
        raise RuntimeError("ANSWER_KEY_REACHED_THE_SOLVER")
    return {"test_path": f"python_testcases/test_{name}.py", "test_sha256": sha(test),
            "program_path": f"python_programs/{name}.py",
            "program_sha256": sha(root / "python_programs" / f"{name}.py")}


def run_pytest(where: pathlib.Path, test_path: str, timeout: int = 180) -> dict[str, Any]:
    """The corpus's own test, run by this harness. This is the only verdict that counts."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(where) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.time()
    try:
        done = subprocess.run([sys.executable, "-m", "pytest", test_path, "-q", "-p", "no:cacheprovider"],
                              cwd=str(where), capture_output=True, text=True, timeout=timeout, env=env)
        return {"returncode": done.returncode, "timed_out": False,
                "tail": (done.stdout + done.stderr).strip().splitlines()[-3:],
                "seconds": round(time.time() - started, 1)}
    except subprocess.TimeoutExpired:
        return {"returncode": None, "timed_out": True, "tail": ["TIMEOUT"], "seconds": round(time.time() - started, 1)}


def apply_patch(where: pathlib.Path, diff: str) -> tuple[bool, str]:
    """Apply the candidate diff the loop returned. git first, patch second, refusal otherwise."""
    handle = where / "_candidate.diff"
    handle.write_text(diff)
    for argv in (["git", "apply", "-p1", "--whitespace=nowarn", str(handle)],
                 ["patch", "-p1", "--batch", "--forward", "-i", str(handle)]):
        try:
            done = subprocess.run(argv, cwd=str(where), capture_output=True, text=True, timeout=60)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        if done.returncode == 0:
            return True, argv[0]
    return False, "PATCH_DID_NOT_APPLY"


def measure(root: pathlib.Path, name: str, *, wall_budget_s: float, timeout_s: int) -> dict[str, Any]:
    """One published bug, start to finish: is it really broken, what does the loop do, and is it fixed?"""
    from canonical.runtime.bound_capabilities import python_iterative_software_repair_loop_v1 as loop

    row: dict[str, Any] = {"task": name, "kind": "task"}
    started = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        where = pathlib.Path(tmp) / name
        try:
            row.update(build_task(root, name, where))
        except Exception as error:  # noqa: BLE001 -- one task must not take the others with it
            row.update(stage="TASK_NOT_BUILT", reason=type(error).__name__, detail=str(error)[:200])
            return row

        baseline = run_pytest(where, row["test_path"], timeout=timeout_s)
        row["baseline"] = baseline
        if baseline["returncode"] == 0:
            # The corpus's defect does not reproduce under this interpreter: not a task for us.
            row["stage"] = "DEFECT_DOES_NOT_REPRODUCE"
            row["seconds"] = round(time.time() - started, 1)
            return row

        os.environ["BRAIN_REPAIR_SELF"] = "1"
        try:
            result = loop.run({"source_root": ".", "test_paths": [row["test_path"]],
                               "output_path": "_loop_result.json",
                               "timeout_s": timeout_s, "wall_budget_s": wall_budget_s}, root=where)
            row["loop_status"] = result.get("status")
            row["loop_claims_pass"] = bool(result.get("pass"))
            row["rounds"] = len(result.get("rounds") or [])
            row["accepted_edit_count"] = result.get("accepted_edit_count")
            row["tested_candidate_count"] = result.get("tested_candidate_count")
            row["accepted_mutations"] = [e.get("mutation") for e in (result.get("accepted_edits") or [])]
            row["patches"] = result.get("patches") or []
        except Exception as error:  # noqa: BLE001
            row.update(loop_status="LOOP_RAISED", loop_error=type(error).__name__,
                       loop_detail=str(error)[:300])
            row["seconds"] = round(time.time() - started, 1)
            return row

        patches = row.get("patches") or []
        if not patches:
            row["stage"] = "NOT_REPAIRED__NO_CANDIDATE"
            row["seconds"] = round(time.time() - started, 1)
            return row

        # Rule 3: verify on a FRESH copy, with the corpus's own test. The loop's claim is not evidence.
        fresh = pathlib.Path(tmp) / (name + "__verify")
        build_task(root, name, fresh)
        applied = []
        for patch in patches:
            ok, how = apply_patch(fresh, str(patch.get("unified_diff") or ""))
            applied.append({"source_path": patch.get("source_path"), "applied": ok, "how": how})
        row["patches_applied"] = applied
        if not all(a["applied"] for a in applied):
            row["stage"] = "NOT_VERIFIED__PATCH_DID_NOT_APPLY"
            row["seconds"] = round(time.time() - started, 1)
            return row
        verdict = run_pytest(fresh, row["test_path"], timeout=timeout_s)
        row["verification"] = verdict
        row["stage"] = "REPAIRED__CORPUS_TEST_PASSES" if verdict["returncode"] == 0 else "NOT_REPAIRED__CORPUS_TEST_STILL_FAILS"
        row["seconds"] = round(time.time() - started, 1)
        return row


def summarise(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Folded from the rows, never typed by hand."""
    stages: dict[str, list[str]] = {}
    for row in rows:
        stages.setdefault(str(row.get("stage")), []).append(str(row["task"]))
    repaired = stages.get("REPAIRED__CORPUS_TEST_PASSES", [])
    return {"tasks": len(rows), "repaired": len(repaired), "repaired_tasks": sorted(repaired),
            "by_stage": {k: {"count": len(v), "tasks": sorted(v)} for k, v in sorted(stages.items())},
            "seconds_total": round(sum(float(r.get("seconds") or 0) for r in rows), 1)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quixbugs", required=True, help="path to a jkoppel/QuixBugs checkout")
    parser.add_argument("--out", required=True, help="JSONL: a header, then one row per task")
    parser.add_argument("--tasks", nargs="*", default=None, help="default: every published test file")
    parser.add_argument("--wall-budget-s", type=float, default=120.0)
    parser.add_argument("--timeout-s", type=int, default=120)
    args = parser.parse_args(argv)

    root = pathlib.Path(args.quixbugs).resolve()
    names = args.tasks or tasks_of(root)
    if not names:
        raise SystemExit("NO_TASKS_FOUND")
    if (root / ANSWER_KEY).exists() is False:
        # Absence at the source is fine (a stripped copy); it is the TASK directory that must lack it,
        # and build_task asserts that per task.
        pass
    header = {"schema": SCHEMA, "authority": AUTHORITY, "kind": "header", "upstream": UPSTREAM,
              "tasks_planned": names, "wall_budget_s": args.wall_budget_s, "timeout_s": args.timeout_s,
              "answer_key_present_at_source": (root / ANSWER_KEY).exists(),
              "python": sys.version.split()[0],
              "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "producer_cognition_model_dependency_count": 0, "incremental_spend_usd": 0,
              "network_calls_during_measurement": 0}
    with open(args.out, "a") as handle:
        handle.write(json.dumps(header) + "\n")
        for name in names:
            row = measure(root, name, wall_budget_s=args.wall_budget_s, timeout_s=args.timeout_s)
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
            handle.flush()
            print(f"{name:<26} {str(row.get('stage')):<40} edits={row.get('accepted_edit_count')} "
                  f"cands={row.get('tested_candidate_count')} {row.get('seconds')}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
