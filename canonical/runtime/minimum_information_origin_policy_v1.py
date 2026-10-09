"""Minimum-information origin routing policy V1.

This policy prevents a missing user specification from being misclassified as an
external-world research problem. It routes only the minimum decision-relevant
missing information and grants no semantic-truth or acceptance authority.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_MINIMUM_INFORMATION_ORIGIN_POLICY_V1"

USER_SPECIFICATION = "USER_SPECIFICATION"
EXTERNAL_WORLD = "EXTERNAL_WORLD"
UNKNOWN = "UNKNOWN"

BOUND_SOURCE = "BOUND_SOURCE"
UNBOUND_SOURCE = "UNBOUND_SOURCE"


def _base(action: str, reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": True,
        "action": action,
        "reason": reason,
        "external_research_authorized": False,
        "ask_user_required": False,
        "bound_source_only": False,
        "semantic_truth_authority": False,
        "policy_adequacy_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def route(problem: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "PROBLEM_MAPPING_REQUIRED",
            "external_research_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    decision_relevant = problem.get("decision_relevant")
    context_value_bound = problem.get("context_value_bound")
    if not isinstance(decision_relevant, bool):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "DECISION_RELEVANCE_BOOLEAN_REQUIRED",
            "external_research_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    if not isinstance(context_value_bound, bool):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "CONTEXT_VALUE_BOUND_BOOLEAN_REQUIRED",
            "external_research_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    if not decision_relevant:
        return _base("IGNORE_NO_INFORMATION_NEEDED", "MISSING_VALUE_CANNOT_CHANGE_ACTION")

    if context_value_bound:
        out = _base("REUSE_BOUND_CONTEXT", "DECISION_RELEVANT_VALUE_ALREADY_BOUND")
        out["context_binding_id"] = problem.get("context_binding_id")
        return out

    owner = problem.get("information_owner", UNKNOWN)
    if owner not in {USER_SPECIFICATION, EXTERNAL_WORLD, UNKNOWN}:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "INFORMATION_OWNER_INVALID",
            "external_research_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    source = problem.get("source_scope")
    if source is None:
        source = {"kind": UNBOUND_SOURCE}
    if not isinstance(source, Mapping):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "SOURCE_SCOPE_INVALID",
            "external_research_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    source_kind = source.get("kind", UNBOUND_SOURCE)
    if source_kind not in {BOUND_SOURCE, UNBOUND_SOURCE}:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "SOURCE_SCOPE_KIND_INVALID",
            "external_research_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    source_id = source.get("source_id")
    if source_kind == BOUND_SOURCE and (not isinstance(source_id, str) or not source_id.strip()):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "BOUND_SOURCE_ID_REQUIRED",
            "external_research_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    delegated = problem.get("discovery_delegated", False)
    if not isinstance(delegated, bool):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "DISCOVERY_DELEGATED_BOOLEAN_REQUIRED",
            "external_research_authorized": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    if owner == USER_SPECIFICATION:
        out = _base(
            "ASK_USER_MINIMUM_CLARIFICATION",
            "MISSING_VALUE_IS_USER_CONTROLLED_SPECIFICATION_NOT_WORLD_FACT",
        )
        out["ask_user_required"] = True
        out["clarification_key"] = problem.get("clarification_key")
        return out

    if owner == EXTERNAL_WORLD and source_kind == BOUND_SOURCE:
        out = _base(
            "OBSERVE_BOUND_SOURCE_ONLY",
            "EXTERNAL_FACT_SOURCE_ALREADY_FIXED_BY_USER_OR_AUTHENTICATED_CONTEXT",
        )
        out["bound_source_only"] = True
        out["source_id"] = source_id.strip()
        return out

    if owner == EXTERNAL_WORLD and delegated:
        out = _base(
            "RESEARCH_MINIMUM_AUTHENTICATED_FACT",
            "USER_DELEGATED_DISCOVERY_OF_DECISION_RELEVANT_EXTERNAL_FACT",
        )
        out["external_research_authorized"] = True
        return out

    if owner == EXTERNAL_WORLD:
        out = _base(
            "ASK_USER_SOURCE_OR_SCOPE",
            "EXTERNAL_FACT_NEEDED_BUT_SOURCE_DISCOVERY_NOT_DELEGATED",
        )
        out["ask_user_required"] = True
        return out

    out = _base(
        "ASK_USER_MINIMUM_CLARIFICATION",
        "INFORMATION_ORIGIN_UNPROVED__DO_NOT_INVENT_SOURCE_OR_RESEARCH_SCOPE",
    )
    out["ask_user_required"] = True
    out["clarification_key"] = problem.get("clarification_key")
    return out
