#!/usr/bin/env python3
"""Visible-prompt entrypoint for the frozen active15 LiveBench pointwise solver.

Input: only the visible historical LiveBench prompt.
Output: a deterministic candidate response plus its pointwise score certificate
shape. Hidden instruction_id_list, kwargs, terminal rows, comparator responses,
frequencies, and target scores are not accepted by this interface.

Acceptance credit remains false until the public-generator quotient and accepted
scope-equivalence obligations are independently closed.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as pointwise
from canonical.runtime import livebench_legacy15_visible_prompt_compiler_v1 as compiler

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_VISIBLE_POINTWISE_SOLVER_V1"


class VisiblePointwiseSolverError(ValueError):
    pass


def solve_visible_prompt(prompt: str) -> dict[str, Any]:
    if not isinstance(prompt, str) or not prompt:
        raise VisiblePointwiseSolverError("VISIBLE_PROMPT_STRING_REQUIRED")

    compiled = compiler.compile_visible_prompt(prompt)
    contracts = list(compiled["contracts"])
    planned = pointwise.solve_contracts(contracts)

    if planned.get("status") != "CANDIDATE_POINTWISE_OPTIMAL":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__POINTWISE_PLANNER_DID_NOT_PRODUCE_CANDIDATE",
            "compiler": compiled,
            "planner": planned,
            "response": None,
            "terminal_rows_used": False,
            "hidden_kwargs_used": False,
            "target_scores_used": False,
            "acceptance_credit": False,
        }

    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_VISIBLE_POINTWISE_OPTIMAL",
        "response": str(planned["response"]),
        "instruction_ids": list(compiled["instruction_ids"]),
        "sacrificed_instruction_ids": list(
            planned.get("sacrificed_instruction_ids") or []
        ),
        "hard_unsat_reasons": list(planned.get("hard_unsat_reasons") or []),
        "theoretical_max_pass_count": int(
            planned["theoretical_max_pass_count"]
        ),
        "instruction_count": int(planned["instruction_count"]),
        "theoretical_pointwise_optimum_strict_score": float(
            planned["theoretical_pointwise_optimum_strict_score"]
        ),
        "compiler_schema": compiled["schema"],
        "planner_schema": planned["schema"],
        "terminal_rows_used": False,
        "hidden_kwargs_used": False,
        "terminal_frequencies_used": False,
        "target_scores_used": False,
        "model_dependency_count": 0,
        "acceptance_credit": False,
        "hard_nonclaims": [
            "VISIBLE_PROMPT_COMPILER_REQUIRES_INDEPENDENT_PUBLIC_GRAMMAR_COMPLETENESS_BINDING",
            "POINTWISE_OPTIMALITY_REQUIRES_COMPLETE_PUBLIC_GENERATOR_SEMANTIC_QUOTIENT_BINDING",
            "ACCEPTED_TERMINAL_SCOPE_EQUIVALENCE_REMAINS_SEPARATE",
        ],
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    return solve_visible_prompt(args.get("prompt"))


if __name__ == "__main__":
    import json
    import sys

    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), indent=2, sort_keys=True))
