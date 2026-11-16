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

  1. rebind `canonical_base_commit` (top level and recursive_obs) to the base CI will use;
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
ARTIFACT = "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json"


def intent_added_by_this_branch(base: str) -> pathlib.Path:
    """The ONE intent this branch adds, found from the diff rather than named here.

    Hardcoding the path was a real defect: the tool kept rewriting an intent that had already
    merged, which put a second `canonical/action_intents/*.json` into the diff. Both referees
    count every intent file in the diff -- `DRIFT` fails MULTIPLE_ACTION_INTENTS_IN_ONE_PR and
    `admission` fails EXACTLY_ONE_ACTION_INTENT_REQUIRED -- so a rebind of a merged intent is
    indistinguishable from adding a second one, and the gates correctly refuse.

    A merged intent is history: its recorded base is the base it was measured against, and
    rewriting it destroys provenance for no benefit. Only the added intent is ours to bind.
    """
    done = subprocess.run(["git", "diff", "--name-status", f"{base}...HEAD", "--",
                           "canonical/action_intents/"],
                          cwd=ROOT, capture_output=True, text=True, check=True)
    added = [line.split("\t")[-1] for line in done.stdout.splitlines()
             if line.startswith("A\t") and line.rstrip().endswith(".json")]
    if len(added) != 1:
        raise SystemExit(
            f"NEED_EXACTLY_ONE_ADDED_INTENT (found {len(added)}): {added}. If this branch adds "
            "none, there is nothing to rebind; if it adds two, the gates will refuse the PR.")
    return ROOT / added[0]


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    done = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    if check and done.returncode != 0:
        print("FAILED:", " ".join(args))
        print((done.stdout or "")[-1500:])
        print((done.stderr or "")[-1500:])
        raise SystemExit(done.returncode)
    return done


def merge_base() -> str:
    """The base the CI guard will actually compare against -- NOT `git merge-base`.

    `drift-immunity-guard.yml` runs on `pull_request_target` and takes its base from
    `github.event.pull_request.base.sha`, which is the CURRENT TIP OF MAIN, not the merge base.
    The guard then requires `recursive_obs.canonical_base_commit` to equal that value exactly, so
    a rebind to the merge base passes locally and fails in CI every time main has moved -- which
    is every time. The local gate is only useful if it agrees with the referee, so this uses
    `origin/main`'s tip.
    """
    return run(["git", "rev-parse", "origin/main"]).stdout.strip()


def rebind(base: str) -> dict:
    intent_path = intent_added_by_this_branch(base)
    intent = json.loads(intent_path.read_text(encoding="utf-8"))
    was = intent.get("canonical_base_commit")
    if was != base:
        intent["canonical_base_commit"] = base
        intent["recursive_obs"]["canonical_base_commit"] = base
        intent_path.write_text(json.dumps(intent, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        return {"rebound": True, "was": was, "now": base, "intent": intent_path.name}
    return {"rebound": False, "now": base, "intent": intent_path.name}


def main() -> int:
    run(["git", "fetch", "origin", "main", "-q"])
    base = merge_base()
    if len(base) != 40:
        print("MERGE_BASE_UNAVAILABLE")
        return 2
    state = rebind(base)
    print("BASE", base, "(rebound)" if state["rebound"] else "(already bound)", "|", state["intent"])

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
