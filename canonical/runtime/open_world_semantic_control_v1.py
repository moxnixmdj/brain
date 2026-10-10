"""Open-world semantic control closure V1.

Semantic identity may remain unresolved. This wrapper certifies only the next
information-acquisition control action when that action is invariant to the
unknown semantic identity under the Brain's minimum-information origin policy.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import residual_semantic_control_invariance_v1 as builder
from canonical.runtime import residual_semantic_control_invariance_verify_v1 as verifier

SCHEMA = "PROJECT_BRAIN_OPEN_WORLD_SEMANTIC_CONTROL_V1"
ROOT = Path(__file__).resolve().parents[2]


def resolve(
    problem: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(problem, Mapping):
            raise ValueError("PROBLEM_MAPPING_REQUIRED")
        candidate = builder.build_candidate(
            environment_id=str(problem.get("environment_id") or ""),
            goal_id=str(problem.get("goal_id") or ""),
            semantic_state=str(problem.get("semantic_state") or ""),
            decision_relevant=problem.get("decision_relevant") is True,
            information_origin=deepcopy(problem.get("information_origin")),
        )
        receipt = verifier.verify(
            candidate,
            repo_root=(Path(repo_root).resolve() if repo_root is not None else ROOT),
        )
        if receipt.get("pass") is not True:
            return {
                "schema": SCHEMA,
                "status": "FAIL_CLOSED__CONTROL_INVARIANCE_NOT_VERIFIED",
                "pass": False,
                "reason": receipt.get("reason"),
                "control_sufficient": False,
                "semantic_decision_sufficient": False,
                "open_world_semantics_closed": False,
                "intended_sense_identified": False,
                "semantic_truth_authority": False,
                "final_domain_action_authority": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
            }
        return {
            "schema": SCHEMA,
            "status": "PASS__OPEN_WORLD_SEMANTIC_CONTROL_CLOSED",
            "pass": True,
            "control_sufficient": True,
            "action": receipt["action"],
            "action_scope": receipt["control_scope"],
            "residual_control_invariance_receipt": deepcopy(dict(receipt)),
            "semantic_decision_sufficient": False,
            "open_world_semantics_closed": False,
            "intended_sense_identified": False,
            "semantic_truth_authority": False,
            "final_domain_action_authority": False,
            "control_action_authority": True,
            "requires_downstream_reverification_after_information": True,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "control_sufficient": False,
            "semantic_decision_sufficient": False,
            "open_world_semantics_closed": False,
            "intended_sense_identified": False,
            "semantic_truth_authority": False,
            "final_domain_action_authority": False,
            "control_action_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
