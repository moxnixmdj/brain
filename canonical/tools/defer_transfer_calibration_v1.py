#!/usr/bin/env python3
"""Does the DEFER form transfer, or does it fire only on the task that suggested it?

THE RULE THIS FILE ENFORCES
---------------------------
V38's failure was adding a sixth form to rescue a calibration it had already
failed. A form is only worth having if it fires on tasks that are NOT the one
that suggested it. So the calibration is stated BEFORE the result is measured,
and the result is reported against it either way.

WHAT A TASK LOOKS LIKE HERE
---------------------------
For each mined task: check out the parent commit, apply ONLY the added test files
from the fix commit, and leave every source file untouched. That is the corpus's
own rule (`fail_to_pass_tasks_20261124_V1.json`). The fix commit is never read for
its source diff -- the form sees only the traceback.

THE PROCEDURE, IDENTICAL FOR EVERY TASK
---------------------------------------
1. Run the failing node. If it passes, discard the task (not fail-to-pass).
2. Feed the traceback and the source file the traceback names to the DEFER form.
3. Apply each candidate, run the target node AND the whole test module.
4. A task is solved only when the target flips AND the module stays green.

Zero model calls, no stored parameters, no network at run time. The checkout is
cloned once and reset per task; the repository's own tests are the oracle and are
never modified beyond the added-test application the corpus defines.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
from typing import Any, Sequence

SCHEMA = "BRAIN_DEFER_TRANSFER_CALIBRATION_V1"
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.tools import deferred_definition_form_v1 as FORM  # noqa: E402


def git(cwd: pathlib.Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def pytest(cwd: pathlib.Path, env: dict[str, str], args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", *args, "-q", "-o", "addopts=", "--tb=short"],
        cwd=str(cwd), env=env, capture_output=True, text=True, timeout=600,
    )


def prepare(checkout: pathlib.Path, task: dict[str, Any]) -> bool:
    """Parent commit + only the added test files. Source stays at the parent."""
    if git(checkout, "checkout", "-q", "--force", task["parent"]).returncode != 0:
        return False
    git(checkout, "clean", "-qfd")
    applied = git(checkout, "checkout", task["sha"], "--", task["test"])
    return applied.returncode == 0


def attempt(checkout: pathlib.Path, task: dict[str, Any], src_root: str) -> dict[str, Any]:
    env = {**os.environ, "PYTHONPATH": f"{checkout / src_root}:{checkout}",
           "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    node = task["failed_nodes"][0]
    base = pytest(checkout, env, [node])
    if base.returncode == 0:
        return {"task": task["parent"][:8], "outcome": "SKIPPED_NOT_FAIL_TO_PASS"}

    tb = base.stdout + base.stderr
    # The source file the traceback names, restricted to files the task declares.
    named: list[str] = []
    for line in tb.splitlines():
        for src in task["source_files"]:
            if line.startswith(src + ":") and src not in named:
                named.append(src)
    target = named[0] if named else task["source_files"][0]
    path = checkout / target
    if not path.is_file():
        return {"task": task["parent"][:8], "outcome": "NO_SOURCE_FILE", "target": target}

    original = path.read_text(encoding="utf-8", errors="replace")
    emitted = FORM.emit_for_traceback(tb, original)
    tried = 0
    solved_by = None
    for cand in emitted.get("candidates", []):
        patched = FORM.apply_candidate(original, cand)
        if not patched or patched == original:
            continue
        tried += 1
        path.write_text(patched, encoding="utf-8")
        target_rc = pytest(checkout, env, [node]).returncode
        module_rc = pytest(checkout, env, [task["test"]]).returncode
        path.write_text(original, encoding="utf-8")
        if target_rc == 0 and module_rc == 0:
            solved_by = cand["spelling"]
            break
    return {
        "task": task["parent"][:8],
        "target": target,
        "applies": emitted.get("applies"),
        "reason": emitted.get("reason"),
        "candidates_tried": tried,
        "outcome": "SOLVED" if solved_by else ("NOT_SOLVED" if tried else "NO_CANDIDATE_EMITTED"),
        "solved_by": solved_by,
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--checkout", required=True, help="a clone of the target repository")
    ap.add_argument("--tasks", default="canonical/corpus/fail_to_pass_tasks_20261124_V1.json")
    ap.add_argument("--repo-filter", default=None, help="only tasks whose repo contains this")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--json", default=None)
    ns = ap.parse_args(argv)

    tasks_doc = json.loads((REPO_ROOT / ns.tasks).read_text(encoding="utf-8"))
    tasks = [t for t in tasks_doc["tasks"]
             if not ns.repo_filter or ns.repo_filter in t["repo"]]
    if ns.limit:
        tasks = tasks[: ns.limit]

    checkout = pathlib.Path(ns.checkout).resolve()
    src_root = "src" if (checkout / "src").is_dir() else "."
    rows: list[dict[str, Any]] = []
    for task in tasks:
        if not prepare(checkout, task):
            rows.append({"task": task["parent"][:8], "outcome": "PREPARE_FAILED"})
            continue
        rows.append(attempt(checkout, task, src_root))

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["outcome"]] = counts.get(row["outcome"], 0) + 1
    solved = counts.get("SOLVED", 0)
    eligible = sum(v for k, v in counts.items() if k not in ("SKIPPED_NOT_FAIL_TO_PASS", "PREPARE_FAILED"))
    result = {
        "schema": SCHEMA,
        "authority": "NONE -- sandbox measurement, not independent verification",
        "tasks_considered": len(tasks),
        "eligible": eligible,
        "solved": solved,
        "outcomes": counts,
        "rows": rows,
        "model_calls": 0,
        "parameters_stored": 0,
        "network_at_run_time": 0,
    }
    text = json.dumps(result, indent=1)
    if ns.json:
        pathlib.Path(ns.json).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
