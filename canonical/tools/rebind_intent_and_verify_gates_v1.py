#!/usr/bin/env python3
"""Rebind this branch's action intent to the current merge base and refresh the model.

WHY THIS EXISTS
---------------
Two gates compare `recursive_obs.canonical_base_commit` against the pull request's
*real* base SHA:

  * execution_guard/enforce_load_bearing_primary_pr.py
  * canonical/runtime/enforce_goal_hierarchy.py  (drift immunity)

Every time main moves and this branch merges it, that base changes and the intent goes
stale -- which is correct behaviour, and a manual rebinding is easy to forget. This does
the three steps in the order that works, and fails loudly instead of producing a stale
tree:

  1. rebind `canonical_base_commit` (top level and recursive_obs) to `git merge-base`;
  2. recompile the unified model artifact, because the intent is a knowledge document
     whose hash is inside the model -- editing the intent AFTER compiling leaves the
     tree in a 32/33 state, which is the mistake this script exists to prevent;
  3. run all four gates and report each one's own verdict.

It edits nothing else. A failure is printed, never swallowed.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
INTENT = ROOT / "canonical/action_intents/ONE_DEMONSTRATION_IS_NOT_IDENTIFICATION_20261116_V1.json"
ARTIFACT = "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    done = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if check and done.returncode != 0:
        print("FAILED:", " ".join(args))
        print((done.stdout or "")[-1500:])
        print((done.stderr or "")[-1500:])
        raise SystemExit(done.returncode)
    return done


def merge_base() -> str:
    return run(["git", "merge-base", "HEAD", "origin/main"]).stdout.strip()


def rebind(base: str) -> dict:
    intent = json.loads(INTENT.read_text(encoding="utf-8"))
    if intent.get("canonical_base_commit") != base:
        intent["canonical_base_commit"] = base
        intent["recursive_obs"]["canonical_base_commit"] = base
        INTENT.write_text(json.dumps(intent, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return {"rebound": True, "was": intent.get("canonical_base_commit"), "now": base}
    return {"rebound": False, "now": base}


def main() -> int:
    run(["git", "fetch", "origin", "main", "-q"])
    base = merge_base()
    if len(base) != 40:
        print("MERGE_BASE_UNAVAILABLE")
        return 2
    state = rebind(base)
    print("BASE", base, "(rebound)" if state["rebound"] else "(already bound)")

    print("COMPILE", run([sys.executable, "canonical/runtime/compile_brain_unified_model_v1.py",
                          "--output", ARTIFACT]).stdout.strip().splitlines()[0])

    gates = {
        "unified_model": [sys.executable, "canonical/runtime/verify_brain_unified_model_v1.py"],
        "drift": [sys.executable, "canonical/runtime/enforce_goal_hierarchy.py",
                  "--base", base, "--head", "HEAD"],
        "admission": [sys.executable, "execution_guard/enforce_load_bearing_primary_pr.py",
                      "--base", base, "--head", "HEAD"],
        "integrity": [sys.executable, "execution_guard/repo_integrity_guard_v1.py"],
    }
    failed = []
    for name, argv in gates.items():
        done = run(argv, check=False)
        text = (done.stdout or "") + (done.stderr or "")
        verdict = next((line for line in text.splitlines()
                        if line.startswith(("TOTAL", "DRIFT_GUARD", "LOAD_BEARING", "repo-integrity-guard"))),
                       text.strip().splitlines()[-1] if text.strip() else "NO_OUTPUT")
        ok = done.returncode == 0 and "FAIL" not in verdict
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {verdict[:140]}")
        if not ok:
            failed.append(name)
    print("ALL_GATES_PASS" if not failed else "GATES_FAILED:" + ",".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
