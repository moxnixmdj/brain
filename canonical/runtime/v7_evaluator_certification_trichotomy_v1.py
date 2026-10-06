"""Fail-closed V7 capability evaluator certification router.

This router does not discover evaluator semantics. It only applies a sound
conditional route after the relevant semantic premise has been independently proved.
Unknown or unproved hidden semantics fall back to exact trajectory-law equality.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from canonical.runtime.hidden_evaluator_dominance_boundary_v1 import (
    hidden_evaluator_universal_noninferiority,
)
from canonical.runtime.hidden_evaluator_monotone_coupling_v1 import solve as monotone_coupling_solve
from canonical.runtime.v7_layered_distributional_order_v1 import capability_noninferior


_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class EvaluatorCertificationError(ValueError):
    pass


def _proof_receipts(value: Any, label: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise EvaluatorCertificationError(f"{label}_PROOF_RECEIPTS_REQUIRED")
    out: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, Mapping):
            raise EvaluatorCertificationError(f"{label}_PROOF_RECEIPT_INVALID")
        path = row.get("path")
        sha = row.get("git_blob_sha")
        if not isinstance(path, str) or not path.strip():
            raise EvaluatorCertificationError(f"{label}_PROOF_PATH_INVALID")
        if not isinstance(sha, str) or not _SHA_RE.fullmatch(sha):
            raise EvaluatorCertificationError(f"{label}_PROOF_SHA_INVALID")
        out.append({"path": path, "git_blob_sha": sha})
    return out


def certify(task: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(task, Mapping):
        raise EvaluatorCertificationError("TASK_INVALID")

    mode = str(task.get("mode") or "AUTO").upper()

    # E is permitted only when complete explicit L1 semantics are proof-carrying.
    if mode in {"E", "EXPLICIT"}:
        receipts = _proof_receipts(task.get("semantic_receipts"), "EXPLICIT")
        brain = task.get("brain_law")
        target = task.get("target_law")
        evaluators = task.get("evaluators")
        constraints = task.get("capability_hard_constraints", ())
        if not isinstance(brain, Mapping) or not isinstance(target, Mapping):
            raise EvaluatorCertificationError("EXPLICIT_LAWS_REQUIRED")
        if not isinstance(evaluators, Sequence) or isinstance(evaluators, (str, bytes)) or not evaluators:
            raise EvaluatorCertificationError("EXPLICIT_EVALUATORS_REQUIRED")
        passed = capability_noninferior(
            brain,
            target,
            evaluators=evaluators,
            capability_hard_constraints=constraints,
        )
        return {
            "route": "E_EXPLICIT_COMPLETE",
            "conditional_noninferiority": bool(passed),
            "proof_receipts": receipts,
            "semantic_premise_verified_by_this_runtime": False,
            "terminal_authority": False,
        }

    # M is permitted only when the hidden class restriction/material order is proved.
    if mode in {"M", "MONOTONE"}:
        receipts = _proof_receipts(task.get("semantic_receipts"), "MONOTONE")
        coupling_task = task.get("coupling_task")
        if not isinstance(coupling_task, Mapping):
            raise EvaluatorCertificationError("MONOTONE_COUPLING_TASK_REQUIRED")
        bound = dict(coupling_task)
        bound["material_order_certificate"] = "CONTENT_ADDRESSED:" + receipts[0]["git_blob_sha"]
        result = monotone_coupling_solve(bound)
        return {
            "route": "M_HIDDEN_RESTRICTED_MONOTONE",
            "conditional_noninferiority": bool(result["universal_monotone_utility_noninferiority"]),
            "proof_receipts": receipts,
            "semantic_premise_verified_by_this_runtime": False,
            "coupling_result": result,
            "terminal_authority": False,
        }

    # U is the conservative fallback. No semantic restriction is assumed.
    if mode in {"U", "ARBITRARY_HIDDEN", "AUTO"}:
        target = task.get("target_distribution_exact")
        brain = task.get("brain_distribution_exact")
        if not isinstance(target, Mapping) or not isinstance(brain, Mapping):
            raise EvaluatorCertificationError("EXACT_DISTRIBUTIONS_REQUIRED_FOR_U")
        passed = hidden_evaluator_universal_noninferiority(target, brain)
        return {
            "route": "U_ARBITRARY_OR_UNCLASSIFIED_HIDDEN",
            "conditional_noninferiority": bool(passed),
            "proof_receipts": [],
            "semantic_premise_verified_by_this_runtime": True,
            "terminal_authority": False,
        }

    raise EvaluatorCertificationError("UNKNOWN_CERTIFICATION_MODE")
