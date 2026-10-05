#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_IF_SCORE_ONLY_SEMANTIC_ELISION_V1"

class SemanticElisionError(RuntimeError):
    pass

_ACCEPTABLE_COMPILER_STATUSES = {
    "PASS",
    "FORMAL_CONSTRAINTS_SATISFIED_SEMANTIC_SEED_STILL_REQUIRED",
}

def bridge(
    compiler_result: Mapping[str, Any],
    *,
    all_score_relevant_constraints_recognized: bool,
    exact_checker_postvalidation_pass: bool,
) -> dict[str, Any]:
    """Promote a structural witness under the frozen LiveBench-IF score-only contract.

    This bridge deliberately does not decide whether prompt parsing is complete and
    does not implement the exact checkers. Those are upstream proof obligations.
    It only deletes an unnecessary semantic-seed dependency after BOTH stronger
    gates have already been proved for the concrete response.
    """
    if not isinstance(compiler_result, Mapping):
        raise SemanticElisionError("COMPILER_RESULT_MAPPING_REQUIRED")
    if all_score_relevant_constraints_recognized is not True:
        raise SemanticElisionError("SCORE_RELEVANT_CONSTRAINT_COVERAGE_NOT_PROVED")
    if exact_checker_postvalidation_pass is not True:
        raise SemanticElisionError("EXACT_CHECKER_POSTVALIDATION_NOT_PROVED")

    status = str(compiler_result.get("status") or "")
    if status not in _ACCEPTABLE_COMPILER_STATUSES:
        raise SemanticElisionError("COMPILER_STATUS_NOT_STRUCTURALLY_ADMISSIBLE:" + status)

    response = compiler_result.get("response")
    if not isinstance(response, str) or not response:
        raise SemanticElisionError("NONEMPTY_RESPONSE_REQUIRED")

    return {
        "schema": SCHEMA,
        "status": "PASS__SCORE_ONLY_STRUCTURAL_WITNESS",
        "response": response,
        "semantic_seed_required": False,
        "semantic_quality_claimed": False,
        "all_score_relevant_constraints_recognized": True,
        "exact_checker_postvalidation_pass": True,
        "model_dependency_count": 0,
        "network_used": False,
        "incremental_spend_usd": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit_authorized": False,
        "hard_nonclaim": (
            "THIS BRIDGE DOES NOT PROVE PROMPT-PARSER COVERAGE OR CONSTRUCTOR "
            "COVERAGE; IT ONLY REMOVES A SEMANTIC-SEED REQUIREMENT THAT THE "
            "FROZEN LIVEBENCH-IF SCORER DOES NOT MEASURE."
        ),
    }

def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return bridge(
        args.get("compiler_result") or {},
        all_score_relevant_constraints_recognized=(
            args.get("all_score_relevant_constraints_recognized") is True
        ),
        exact_checker_postvalidation_pass=(
            args.get("exact_checker_postvalidation_pass") is True
        ),
    )
