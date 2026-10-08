"""Brain-owned grounded candidate policy frontier for R2.

This module converts independently verified plain-goal grounding into policy
*hypotheses* only. It never claims that a grounded capability is adequate for
the user's goal. P3 must authenticate adequacy over the current sound semantic
over-approximation before any policy can be selected.

V1 is deliberately limited to one action-bearing clause. Multi-clause goals
remain with the existing composition path rather than pretending one capability
solves an entire composite request.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.bound_capabilities import plain_goal_bound_grounding as grounding
from canonical.runtime.bound_capabilities import plain_goal_bound_grounding_verify as grounding_verify

SCHEMA = "PROJECT_BRAIN_R2_GROUNDED_CANDIDATE_POLICY_FRONTIER_V1"
POLICY_PREFIX = "BOUND_CAPABILITY_POLICY::"


def _base(status: str, *, passed: bool) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "policy_hypothesis_authority": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def propose(goal: str, *, repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    text = str(goal or "").strip()
    if not text:
        return {**_base("FAIL_CLOSED", passed=False), "reason": "GOAL_REQUIRED"}

    try:
        result = grounding.run({"goal": text}, root)
        registry_doc = json.loads(
            (root / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text(
                encoding="utf-8"
            )
        )
        registry = registry_doc.get("capabilities")
        if not isinstance(registry, Mapping):
            return {
                **_base("FAIL_CLOSED", passed=False),
                "reason": "BOUND_CAPABILITY_REGISTRY_INVALID",
            }
        verified, reason = grounding_verify.verify(text, result, registry)
        if not verified:
            return {
                **_base("FAIL_CLOSED", passed=False),
                "reason": "GROUNDING_INDEPENDENT_VERIFICATION_FAILED:" + str(reason),
            }

        clauses = result.get("clauses")
        if not isinstance(clauses, list) or len(clauses) != 1:
            return {
                **_base("NOT_APPLICABLE__MULTI_CLAUSE_OR_EMPTY", passed=False),
                "grounding": deepcopy(dict(result)),
                "candidate_policy_count": 0,
            }
        clause = clauses[0]
        if not isinstance(clause, Mapping):
            return {
                **_base("FAIL_CLOSED", passed=False),
                "reason": "GROUNDING_CLAUSE_INVALID",
            }
        candidates = clause.get("candidates")
        if not isinstance(candidates, list):
            return {
                **_base("FAIL_CLOSED", passed=False),
                "reason": "GROUNDING_CANDIDATES_INVALID",
            }
        if not candidates:
            return {
                **_base("NOT_APPLICABLE__NO_GROUNDED_BOUND_CAPABILITY", passed=False),
                "grounding": deepcopy(dict(result)),
                "candidate_policy_count": 0,
            }

        policy_conditions: dict[str, dict[str, str]] = {}
        capability_by_policy: dict[str, str] = {}
        for row in candidates:
            if not isinstance(row, Mapping):
                return {
                    **_base("FAIL_CLOSED", passed=False),
                    "reason": "GROUNDING_CANDIDATE_NOT_OBJECT",
                }
            capability_id = str(row.get("capability_id") or "").strip()
            if not capability_id or capability_id not in registry:
                return {
                    **_base("FAIL_CLOSED", passed=False),
                    "reason": "GROUNDING_CANDIDATE_ID_INVALID",
                }
            policy_id = POLICY_PREFIX + capability_id
            policy_conditions[policy_id] = {"op": "TRUE"}
            capability_by_policy[policy_id] = capability_id

        return {
            **_base(
                "PASS__VERIFIED_GROUNDING_EXPOSED_AS_UNTRUSTED_POLICY_FRONTIER",
                passed=True,
            ),
            "grounding_verified": True,
            "grounding_model_dependency_count": result.get("model_dependency_count"),
            "candidate_policy_count": len(policy_conditions),
            "policy_conditions": policy_conditions,
            "capability_by_policy": capability_by_policy,
            "grounding": deepcopy(dict(result)),
            "robustness_semantics": (
                "TRUE_MEANS_EACH_CANDIDATE_MUST_BE_PROVED_ADEQUATE_OVER_THE_ENTIRE_"
                "CURRENT_SOUND_SEMANTIC_OVERAPPROXIMATION_BEFORE_SELECTION"
            ),
            "ambiguity_preserved": len(policy_conditions) > 1,
            "candidate_only": True,
        }
    except Exception as exc:
        return {
            **_base("FAIL_CLOSED", passed=False),
            "reason": type(exc).__name__ + ":" + str(exc),
        }
