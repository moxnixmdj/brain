#!/usr/bin/env python3
"""Run a capability that leaves its world, without letting it reach this one.

The boundary that had to be satisfied rather than removed
---------------------------------------------------------
48 capabilities in this registry import `subprocess`, `socket` or a browser, and every tool in this
repository refuses to run them. That refusal is a safety property, not a limitation: an adapter
that shells out can edit the tree it is standing in, and one already did during log 12.

But 413 declared claims live behind that boundary and none of them can be settled without running
the code. So the boundary is satisfied instead of moved: the capability runs **inside a throwaway
copy of the repository**, imported **from that copy**, so every path it resolves from `__file__`
points into the copy. Then the copy is destroyed.

Two details that make it real rather than decorative
---------------------------------------------------
1. It must be imported from the copy. Measured 2026-11-04: importing the adapter from the
   repository while handing it a temporary `root` means `ROOT = Path(__file__).parents[2]` still
   resolves to the repository, so the code edits the real tree and reports success about a
   directory nobody looked at.
2. The real tree is checked before and after. A run that changes it is a failure of this file,
   reported as such, not a footnote.

Usage::

    python -m canonical.tools.sandboxed_world_v1            # measure
    python -m canonical.tools.sandboxed_world_v1 --write
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import world_forge_v1 as forge                     # noqa: E402
from canonical.tools.capability_world_v1 import (                      # noqa: E402
    ADAPTERS, declared_inputs, reaches_unsafe, registry)

SCHEMA = "PROJECT_BRAIN_SANDBOXED_WORLD_V1"
ARTIFACT = ROOT / "canonical/verification/SANDBOXED_WORLD_V1.json"


def _git_status() -> str:
    done = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                          capture_output=True, text=True)
    return done.stdout


def make_copy(destination: Path) -> None:
    """An exact copy of the committed tree. Uncommitted work is deliberately excluded: a sandbox
    is a world, not a snapshot of whatever was half-written."""
    done = subprocess.run(["git", "archive", "HEAD"], cwd=ROOT, capture_output=True)
    if done.returncode != 0:
        raise RuntimeError("SANDBOX_COPY_FAILED")
    import io
    with tarfile.open(fileobj=io.BytesIO(done.stdout)) as archive:
        archive.extractall(destination)


def run_in_sandbox(capability_id: str, module: str, goal: str = "OUTPUT") -> dict:
    if not reaches_unsafe((ADAPTERS / f"{module}.py").read_text(encoding="utf-8")):
        return forge.forge(capability_id, module, goal=goal)
    directory = Path(tempfile.mkdtemp(prefix="sandbox_"))
    try:
        make_copy(directory)
        result = forge.forge(capability_id, module, goal=goal, world=directory)
        result["sandboxed"] = True
        return result
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def measure(write: bool = False) -> dict:
    caps = registry()
    before = _git_status()
    targets = []
    for capability_id, entry in sorted(caps.items()):
        module = entry.get("adapter_module") or ""
        path = ADAPTERS / f"{module}.py"
        if not path.is_file():
            continue
        if not reaches_unsafe(path.read_text(encoding="utf-8")):
            continue
        targets.append((capability_id, module, len(entry.get("result_fields") or [])))

    rows = []
    for capability_id, module, claims in targets:
        try:
            result = run_in_sandbox(capability_id, module)
        except Exception as exc:                                        # noqa: BLE001
            result = {"capability": capability_id, "reached": False,
                      "stopped_by": f"ERROR:{type(exc).__name__}", "returned_keys": []}
        rows.append({"capability": capability_id, "claims": claims,
                     "reached": bool(result.get("reached")),
                     "verdict": result.get("verdict"),
                     "keys": len(result.get("returned_keys") or []),
                     "stopped_by": result.get("stopped_by")})
    after = _git_status()

    producing = [r for r in rows if r["reached"]]
    doc = {
        "schema": SCHEMA,
        "question": "Can the capabilities that leave their world be run without letting them "
                    "reach this one?",
        "attempted": len(rows),
        "produced_output": len(producing),
        "claims_behind_the_boundary": sum(r["claims"] for r in rows),
        "claims_now_settleable": sum(r["claims"] for r in producing),
        "real_tree_changed": before != after,
        "real_tree_diff_before_after": {"before": before[:400], "after": after[:400]},
        "rows": rows,
        "how": "a throwaway `git archive HEAD` copy; the adapter is imported FROM the copy, so "
               "every path it derives from __file__ points inside it; the copy is destroyed",
        "non_claims": [
            "RUNNING_IN_A_COPY_DOES_NOT_MAKE_UNTRUSTED_CODE_SAFE_IN_GENERAL",
            "A_CAPABILITY_THAT_REACHES_THE_NETWORK_STILL_REACHES_THE_NETWORK",
            "THE_COPY_EXCLUDES_UNCOMMITTED_WORK_ON_PURPOSE",
        ],
        "authority": "NO_CAPABILITY_CREDIT_SANDBOX_MEASUREMENT_ONLY",
    }
    if write:
        ARTIFACT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    doc = measure(write=args.write)
    print(f"capabilities behind the boundary: {doc['attempted']}")
    print(f"  produced output in a sandbox     : {doc['produced_output']}")
    print(f"  claims behind the boundary       : {doc['claims_behind_the_boundary']}")
    print(f"  claims now settleable            : {doc['claims_now_settleable']}")
    print(f"  real tree changed by any run     : {doc['real_tree_changed']}")
    for row in doc["rows"][:14]:
        print(f"    {row['capability'][:44]:46s} {str(row['verdict']):18s} keys={row['keys']}")
    if args.write:
        print(f"wrote {ARTIFACT.relative_to(ROOT)}")
    return 0 if not doc["real_tree_changed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
