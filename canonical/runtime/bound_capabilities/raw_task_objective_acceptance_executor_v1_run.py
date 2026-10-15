"""Thin adapter wrapper exposing a standard run(args, root) entrypoint.

The underlying implementation lives in the pinned module
canonical/runtime/raw_task_objective_acceptance_executor_v1.py (do not edit it;
its blob sha is recorded by capability receipts). This wrapper only adds the
run(args, root) entrypoint the bound-capability controller expects, delegating
to evaluate_candidate. No model dependency. No spend.
"""
from __future__ import annotations

import pathlib

from canonical.runtime.raw_task_objective_acceptance_executor_v1 import (
    evaluate_candidate,
)


def run(args, root):
    args = dict(args or {})
    raw_task_text = args.get("raw_task_text") or args.get("task_text")
    candidate_response = args.get("candidate_response")
    candidate = {"response_text": candidate_response}
    if args.get("fields") is not None:
        candidate["fields"] = args["fields"]
    if args.get("evidence") is not None:
        candidate["evidence"] = args["evidence"]
    result = evaluate_candidate(
        str(raw_task_text or ""),
        candidate,
        source_id=str(args.get("source_id") or "user"),
    )
    # normalize to the standard adapter result shape
    result.setdefault("adapter", "raw_task_objective_acceptance_executor_v1_run")
    result.setdefault("root", str(pathlib.Path(root).resolve()))
    return result
