#!/usr/bin/env python3
"""Fail-closed prompt-to-pointwise-optimal solver for frozen LiveBench legacy15.

Pipeline:
1. compile only the visible historical prompt suffix into active15 contracts;
2. bind the exact pinned public LiveBench checker source by Git blob SHA;
3. generate the bounded subset-relaxation candidate pool;
4. exact-postvalidate every candidate against every recovered contract;
5. select the highest exact score;
6. emit a response only if semantic next-cardinality UNSAT certificates prove
   that the selected score is pointwise maximal for this case.

The solver does not consume comparator responses, terminal scores, hidden
instruction_id_list values, hidden kwargs, case frequencies, or case ids.
A caller-supplied visible prompt is necessarily read because it is the input.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from canonical.runtime import livebench_legacy15_exact_postvalidator_v1 as exact_checker
from canonical.runtime import livebench_legacy15_pointwise_search_v1 as pointwise
from canonical.runtime import livebench_legacy_visible_constraint_compiler_v4 as compiler
from canonical.runtime.livebench_frozen_active_legacy15_v1 import ACTIVE_IDS

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_POINTWISE_SOLVER_V1"


def _fail(error: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "error": str(error),
        "response": None,
        "pointwise_optimal": False,
        "visible_prompt_used": True,
        "hidden_instruction_ids_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_id_used": False,
        "terminal_score_used": False,
        "comparator_response_used": False,
        "case_frequency_used": False,
        "acceptance_credit": False,
        **extra,
    }


def solve_prompt(
    prompt: str,
    livebench_root: str | Path,
    *,
    max_per_subset: int = 16,
    max_total: int = 512,
) -> dict[str, Any]:
    compiled = compiler.compile_visible_constraints(str(prompt or ""))
    if compiled.get("status") != "PASS":
        return _fail(
            "VISIBLE_CONSTRAINT_COMPILER_NOT_COMPLETE",
            compiler_status=compiled.get("status"),
            compiler_error=compiled.get("error"),
        )

    contracts = list(compiled.get("constraints") or [])
    if not contracts:
        return _fail("NO_VISIBLE_ACTIVE15_CONTRACTS")

    if any(c.get("parameter_complete") is not True for c in contracts):
        return _fail("VISIBLE_CONTRACT_PARAMETER_INCOMPLETE")

    ids = [str(c.get("instruction_id") or "") for c in contracts]
    if len(ids) != len(set(ids)):
        return _fail("DUPLICATE_VISIBLE_INSTRUCTION_ID")
    outside = sorted(set(ids) - set(ACTIVE_IDS))
    if outside:
        return _fail("OUTSIDE_FROZEN_ACTIVE15:" + ",".join(outside))

    try:
        search = pointwise.solve_with_pinned_livebench(
            contracts,
            str(livebench_root),
            max_per_subset=max_per_subset,
            max_total=max_total,
        )
        source_binding = dict(search.get("exact_checker_binding") or {})
    except (
        exact_checker.ExactPostvalidationError,
        pointwise.PointwiseSearchError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        return _fail("EXECUTION_ERROR:" + type(exc).__name__ + ":" + str(exc))

    if (
        search.get("status") != "PASS__POINTWISE_OPTIMAL_CANDIDATE_CERTIFIED"
        or search.get("pointwise_optimal") is not True
    ):
        return _fail(
            "POINTWISE_OPTIMALITY_NOT_CERTIFIED",
            search=search,
            pinned_source_binding=source_binding,
        )

    best = dict(search.get("best_candidate") or {})
    response = best.get("response")
    if not isinstance(response, str):
        return _fail(
            "CERTIFIED_RESULT_MISSING_RESPONSE",
            search=search,
            pinned_source_binding=source_binding,
        )

    return {
        "schema": SCHEMA,
        "status": "PASS__POINTWISE_OPTIMAL_RESPONSE_CERTIFIED",
        "response": response,
        "instruction_ids": ids,
        "contract_count": len(contracts),
        "compiler_schema": compiled.get("schema"),
        "pinned_source_binding": source_binding,
        "search": search,
        "pointwise_optimal": True,
        "visible_prompt_used": True,
        "hidden_instruction_ids_used": False,
        "hidden_kwargs_used": False,
        "terminal_case_id_used": False,
        "terminal_score_used": False,
        "comparator_response_used": False,
        "case_frequency_used": False,
        "model_dependency_count": 0,
        "network_used_by_solver": False,
        "acceptance_credit": False,
    }


def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    livebench_root = args.get("livebench_root")
    if not livebench_root:
        return _fail("LIVEBENCH_ROOT_REQUIRED")
    return solve_prompt(
        str(args.get("prompt") or ""),
        livebench_root,
        max_per_subset=int(args.get("max_per_subset") or 16),
        max_total=int(args.get("max_total") or 512),
    )


if __name__ == "__main__":
    import json
    import sys

    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), ensure_ascii=False, indent=2, sort_keys=True))
