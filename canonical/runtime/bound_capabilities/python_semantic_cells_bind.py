#!/usr/bin/env python3
"""Thin live binding for the pinned semantic-cells kernel (byte unchanged).

Capability ``python.software.request.semantic_cells.v1``: evaluate bounded,
source-grounded semantic acceptance cells (The file "X" must contain/not
contain Y; must exist; must not exist) against one source tree and write the
verdict JSON. The task spec is read from a file (sentence-quoted binding
cannot carry the inner quotes the cell grammar requires). Baseline defaults
to the candidate tree (acceptance of the tree as it stands); differential
baseline-vs-candidate measurement stays available through the kernel's direct
API.

Strictness (fail-closed, enforced HERE because the pinned kernel's
``pass: not failed`` verdict does not block on unbound obligations despite its
own hard nonclaim): the binding raises unless every obligation is bound and
passing. Fails closed (raises) on: non-object args, missing/unreadable task
file, missing source tree, output outside the repository, cell compilation
failure, or any unbound or failed obligation. Never guesses, never a model,
never a spend.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

from canonical.runtime.bound_capabilities import python_request_semantic_acceptance_cells_v1 as cells

SCHEMA = "PROJECT_BRAIN_PYTHON_SEMANTIC_CELLS_BIND_V1"
CAPABILITY_ID = "python.software.request.semantic_cells.v1"


def run(args, root):
    if not isinstance(args, dict):
        raise RuntimeError("ARGS_NOT_OBJECT")
    repo = pathlib.Path(root).resolve()
    task_file = (repo / str(args.get("task_path") or "")).resolve()
    if task_file == repo or repo not in task_file.parents or not task_file.is_file():
        raise RuntimeError("TASK_PATH_INVALID")
    spec = task_file.read_text(encoding="utf-8")
    if not spec.strip():
        raise RuntimeError("TASK_SPEC_REQUIRED")
    if len(spec) > 20000:
        raise RuntimeError("TASK_SPEC_TOO_LONG")
    tree = (repo / str(args.get("source_root") or "")).resolve()
    if tree == repo or repo not in tree.parents or not tree.is_dir():
        raise RuntimeError("SOURCE_ROOT_INVALID")
    out = (repo / str(args.get("output_path") or "")).resolve()
    if out == repo or repo not in out.parents:
        raise RuntimeError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    if out.suffix.lower() != ".json":
        raise RuntimeError("OUTPUT_PATH_MUST_BE_JSON")
    result = cells.evaluate_cells(
        spec,
        baseline_root=tree,
        candidate_root=tree,
    )
    blocking = list(result.get("failed_obligation_ids") or []) + list(result.get("unbound_obligation_ids") or [])
    if result.get("pass") is not True or blocking:
        raise RuntimeError(
            "SEMANTIC_CELLS_NOT_SATISFIED:" + ",".join(blocking or ["KERNEL_REPORTED_FAILURE"])[:400]
        )
    payload = {**result, "capability_id": CAPABILITY_ID, "output_verified": True}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raw = out.read_bytes()
    return {
        **payload,
        "bound_source_root": str(tree.relative_to(repo)).replace("\\", "/"),
        "task_path": str(task_file.relative_to(repo)).replace("\\", "/"),
        "output_path": str(out.relative_to(repo)).replace("\\", "/"),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "incremental_spend_usd": 0,
    }
