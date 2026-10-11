#!/usr/bin/env python3
"""Fail-closed Finance Agent v2 exact-harness model-boundary certificate.

This certificate proves a narrow structural statement only:
if the pinned Vals Finance Agent v2 harness is left byte-identical at its
load-bearing files and only the LLM implementation supplied to get_agent() is
substituted, the benchmark harness layer is unchanged.

It does NOT prove that a candidate LLM/Brain adapter exists, is protocol
compatible, receives private-suite access, runs at zero cost, or scores 58.59.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_FINANCE_AGENT_V2_EXACT_HARNESS_MODEL_BOUNDARY_V1"

PINNED = {
    "finance_repo_commit": "502aab6fdaa3fb9294905c7453f89882baa8d39b",
    "readme_blob": "6e18ea1e7149ba696e59c80e52890878aca8f096",
    "get_agent_blob": "22c012241a430975266fb7f8d2fe7af8e9f1b8d4",
    "run_agent_blob": "49d08c50990ef1ca296f4d690216fc4cc4c53c85",
    "prompt_blob": "bfbd6577a60a14dacfa1fed12c88d6d9e1f8dded",
    "tools_blob": "19b85ce4e110e39f410c52b2efa0e33f651fa6d1",
    "pyproject_blob": "6c8c5520fa560f99eb01a6ec8888480fbf529150",
}

OFFICIAL_HARNESS_FILES = (
    "README.md",
    "finance_agent/get_agent.py",
    "finance_agent/run_agent.py",
    "finance_agent/prompt.py",
    "finance_agent/tools.py",
    "pyproject.toml",
)

ALLOWED_MODEL_BOUNDARY_ROUTES = frozenset({
    "GET_AGENT_LLM_ARGUMENT",
    "CUSTOM_ENDPOINT_CREATE_LLM",
})


def verify(evidence: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    for key, expected in PINNED.items():
        if str(evidence.get(key) or "") != expected:
            errors.append(f"PIN_MISMATCH:{key}")

    route = str(evidence.get("route") or "").strip()
    if route not in ALLOWED_MODEL_BOUNDARY_ROUTES:
        errors.append("ROUTE_NOT_MODEL_BOUNDARY_ONLY")

    modified = evidence.get("modified_official_harness_files", [])
    if not isinstance(modified, Sequence) or isinstance(modified, (str, bytes)):
        errors.append("MODIFIED_FILE_LIST_INVALID")
        modified = []
    else:
        forbidden = sorted(set(str(x) for x in modified) & set(OFFICIAL_HARNESS_FILES))
        if forbidden:
            errors.extend(f"OFFICIAL_HARNESS_FILE_MODIFIED:{x}" for x in forbidden)

    if evidence.get("get_agent_accepts_llm_argument") is not True:
        errors.append("GET_AGENT_LLM_INJECTION_NOT_BOUND")
    if evidence.get("custom_endpoint_supported") is not True:
        errors.append("CUSTOM_ENDPOINT_SUPPORT_NOT_BOUND")
    if evidence.get("official_prompt_preserved") is not True:
        errors.append("OFFICIAL_PROMPT_NOT_PRESERVED")
    if evidence.get("official_tool_construction_preserved") is not True:
        errors.append("OFFICIAL_TOOL_CONSTRUCTION_NOT_PRESERVED")
    if evidence.get("official_time_limit_preserved") is not True:
        errors.append("OFFICIAL_TIME_LIMIT_NOT_PRESERVED")
    if evidence.get("official_agent_hooks_preserved") is not True:
        errors.append("OFFICIAL_AGENT_HOOKS_NOT_PRESERVED")
    if evidence.get("official_answer_extraction_preserved") is not True:
        errors.append("OFFICIAL_ANSWER_EXTRACTION_NOT_PRESERVED")
    if evidence.get("llm_is_only_substituted_component") is not True:
        errors.append("NON_LLM_COMPONENT_SUBSTITUTION_PRESENT")

    passed = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__EXACT_OFFICIAL_HARNESS_PRESERVED__MODEL_BOUNDARY_ONLY"
            if passed else
            "FAIL_CLOSED"
        ),
        "pass": passed,
        "errors": errors,
        "harness_layer_comparability": passed,
        "candidate_model_protocol_compatibility_proved": False,
        "candidate_model_capability_proved": False,
        "vals_private_access_proved": False,
        "zero_spend_full_run_proved": False,
        "score_ge_58_59_proved": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
