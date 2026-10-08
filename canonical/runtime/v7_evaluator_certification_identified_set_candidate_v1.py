"""Candidate V7 successor adding a partially-identified evaluator route.

The active V7 router is left unchanged.  This wrapper adds exactly one route:

R_PARTIALLY_IDENTIFIED_HIDDEN

R may be used only when a separate proof-carrying semantic receipt establishes
that the supplied finite evaluator-world set is complete for the load-bearing
hidden evaluator semantics in this context.  The identified-set runtime itself
never establishes that semantic premise.

All other modes delegate byte-for-byte in behavior to the active V7 router.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from canonical.runtime.evaluator_identified_set_dominance_v1 import solve as identified_set_solve


_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class V7IdentifiedSetRouteError(ValueError):
    pass


def _receipts(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise V7IdentifiedSetRouteError("IDENTIFIED_SET_SEMANTIC_PROOF_RECEIPTS_REQUIRED")
    out = []
    for row in value:
        if not isinstance(row, Mapping):
            raise V7IdentifiedSetRouteError("IDENTIFIED_SET_SEMANTIC_PROOF_RECEIPT_INVALID")
        path = row.get("path")
        sha = row.get("git_blob_sha")
        if not isinstance(path, str) or not path.strip():
            raise V7IdentifiedSetRouteError("IDENTIFIED_SET_SEMANTIC_PROOF_PATH_INVALID")
        if not isinstance(sha, str) or not _SHA_RE.fullmatch(sha):
            raise V7IdentifiedSetRouteError("IDENTIFIED_SET_SEMANTIC_PROOF_SHA_INVALID")
        out.append({"path": path, "git_blob_sha": sha})
    return out


def certify(task: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(task, Mapping):
        raise V7IdentifiedSetRouteError("TASK_INVALID")

    mode = str(task.get("mode") or "AUTO").upper()
    if mode in {"R", "IDENTIFIED_SET", "PARTIALLY_IDENTIFIED"}:
        receipts = _receipts(task.get("semantic_receipts"))
        identified_task = task.get("identified_set_task")
        if not isinstance(identified_task, Mapping):
            raise V7IdentifiedSetRouteError("IDENTIFIED_SET_TASK_REQUIRED")
        result = identified_set_solve(identified_task)
        return {
            "route": "R_PARTIALLY_IDENTIFIED_HIDDEN",
            "conditional_noninferiority": bool(
                result["universal_noninferiority_over_supplied_world_set"]
            ),
            "identified_set_result": result,
            "proof_receipts": receipts,
            "semantic_premise_verified_by_this_runtime": False,
            "terminal_authority": False,
        }

    # Preserve the already-verified V7 E/M/U semantics exactly outside R.
    from canonical.runtime.v7_evaluator_certification_trichotomy_v1 import certify as v7_certify
    return v7_certify(task)
