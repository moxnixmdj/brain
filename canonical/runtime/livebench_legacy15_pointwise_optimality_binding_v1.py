#!/usr/bin/env python3
"""Bind slot-level UNSAT semantics to the finite LiveBench pointwise-optimality theorem.

The frozen legacy scorer gives a case with k checkers score 1 when all k pass,
otherwise g/(2k), where g is the number of passing checkers. For k <= 5, a
candidate with g passing checkers is pointwise optimal if every checker subset
of cardinality g+1 is jointly UNSAT.

This module does not invent UNSAT facts. It asks the independently auditable
slot-feasibility kernel for a checker-semantics certificate on each required
(g+1)-subset, then feeds only certified subsets to the structural optimality
kernel. Missing semantic certificates fail closed.

No terminal rows, prompts, hidden kwargs, responses, frequencies, or scores are
read by this module.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility
from canonical.runtime import livebench_pointwise_optimality_certificate_v1 as optimality

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_POINTWISE_OPTIMALITY_BINDING_V1"


def certify_pointwise_optimality(
    contracts: Sequence[Mapping[str, Any]],
    checker_results: Sequence[bool],
) -> dict[str, Any]:
    rows = [dict(x) for x in contracts]
    flags = tuple(bool(x) for x in checker_results)

    if not rows:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__CONTRACTS_REQUIRED",
            "terminal_data_used": False,
            "acceptance_credit": False,
        }
    if len(rows) != len(flags):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__CHECKER_RESULT_ARITY_MISMATCH",
            "contract_count": len(rows),
            "checker_result_count": len(flags),
            "terminal_data_used": False,
            "acceptance_credit": False,
        }
    if len(rows) > optimality.MAX_FROZEN_LEGACY_CHECKERS_PER_CASE:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__FROZEN_GENERATOR_BOUND_EXCEEDED",
            "contract_count": len(rows),
            "terminal_data_used": False,
            "acceptance_credit": False,
        }

    # Fail closed if the full identity set is not on the frozen compatible
    # active-15 surface. This also rejects unknown and duplicate IDs.
    full_classification = feasibility.classify_visible_contracts(rows)
    if str(full_classification.get("status", "")).startswith("FAIL_CLOSED"):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__FULL_CONTRACT_SET_OUTSIDE_ADMITTED_SURFACE",
            "full_classification": full_classification,
            "terminal_data_used": False,
            "acceptance_credit": False,
        }

    g = sum(flags)
    required = optimality.required_next_cardinality_subsets(len(rows), g)
    verified_unsat: list[tuple[int, ...]] = []
    semantic_receipts: list[dict[str, Any]] = []

    for subset in required:
        subrows = [rows[i] for i in subset]
        classification = feasibility.classify_visible_contracts(subrows)
        if classification.get("status") == "PROVED_UNSAT":
            verified_unsat.append(tuple(subset))
            semantic_receipts.append({
                "subset_indices": list(subset),
                "instruction_ids": [
                    str(rows[i].get("instruction_id")) for i in subset
                ],
                "hard_unsat_reasons": list(
                    classification.get("hard_unsat_reasons") or []
                ),
            })

    structural = optimality.verify_pointwise_optimality_structure(
        flags,
        verified_unsat,
    )
    complete = (
        structural.get("status")
        == "PASS__POINTWISE_OPTIMALITY_STRUCTURE_COMPLETE"
    )
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__POINTWISE_OPTIMALITY_CERTIFIED_BY_SLOT_SEMANTICS"
            if complete
            else "FAIL_CLOSED__SEMANTIC_UNSAT_COVERAGE_INCOMPLETE"
        ),
        "contract_count": len(rows),
        "candidate_true_checker_count": g,
        "candidate_checker_results": list(flags),
        "candidate_exact_score_numerator": structural[
            "candidate_exact_score_numerator"
        ],
        "candidate_exact_score_denominator": structural[
            "candidate_exact_score_denominator"
        ],
        "required_next_cardinality_unsat_subset_count": len(required),
        "semantically_verified_unsat_subset_count": len(verified_unsat),
        "semantic_unsat_receipts": semantic_receipts,
        "missing_unsat_subsets": structural["missing_unsat_subsets"],
        "pointwise_optimal": complete,
        "full_contract_hard_unsat_reasons": list(
            full_classification.get("hard_unsat_reasons") or []
        ),
        "terminal_data_used": False,
        "hidden_kwargs_used": False,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def run(args=None, root=None):
    args = args or {}
    return certify_pointwise_optimality(
        args.get("contracts") or [],
        args.get("checker_results") or [],
    )


if __name__ == "__main__":
    import json
    import sys

    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), indent=2, sort_keys=True))
