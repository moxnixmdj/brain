#!/usr/bin/env python3
"""Composed active15 joint route: exact special branches plus parameter-aware general branch.

This router is intentionally zero-terminal-data. It selects solely from visible
constraints parsed by compiler V4, delegates the three special structural
families to the existing exact special witness, and delegates all remaining
compatible families to the parameter-aware general composer.
"""
from __future__ import annotations

from typing import Any

from canonical.runtime import livebench_legacy_visible_constraint_compiler_v4 as compiler
from canonical.runtime import livebench_legacy15_joint_witness_v1 as special_witness
from canonical.runtime import livebench_legacy15_general_composer_v1 as general_composer

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_JOINT_ROUTER_V2"
_SPECIAL = {
    "detectable_format:json_format",
    "combination:repeat_prompt",
    "combination:two_responses",
}


def solve(prompt: str) -> dict[str, Any]:
    text = str(prompt or "")
    parsed = compiler.compile_visible_constraints(text)
    constraints = list(parsed.get("constraints") or [])
    if parsed.get("status") != "PASS" or not constraints:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "VISIBLE_COMPILER_NOT_PASS",
            "response": None,
        }

    if list(parsed.get("parameter_incomplete") or []):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "VISIBLE_COMPILER_PARAMETER_INCOMPLETE",
            "response": None,
        }

    ids = {str(c.get("instruction_id") or "") for c in constraints}
    if ids & _SPECIAL:
        out = dict(special_witness.solve(text))
        out["schema"] = SCHEMA
        out["implementation_route"] = "SPECIAL_WITNESS_V1"
        return out

    out = general_composer.compose_visible_prompt(text)
    if out.get("status") != "PASS_CANDIDATE_GENERAL_BRANCH":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "error": "GENERAL_COMPOSER:" + str(out.get("error") or out.get("status")),
            "response": None,
            "instruction_ids": sorted(ids),
        }

    return {
        "schema": SCHEMA,
        "status": "PASS_CANDIDATE_JOINT_LEGACY15_WITNESS",
        "response": str(out.get("response") or ""),
        "route": "GENERAL",
        "implementation_route": "GENERAL_COMPOSER_V1",
        "instruction_ids": sorted(ids),
        "constraint_count": len(constraints),
        "hidden_instruction_ids_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_metadata_used": False,
        "terminal_case_content_used": False,
        "model_dependency_count": 0,
        "network_used": False,
        "acceptance_credit": False,
        "semantic_capability_credit": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    return solve(str((args or {}).get("prompt") or ""))
