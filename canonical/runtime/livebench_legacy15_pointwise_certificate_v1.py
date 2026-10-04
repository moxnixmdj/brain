#!/usr/bin/env python3
"""Bridge active15 semantic UNSAT proofs into pointwise score certificates.

The caller supplies:
- visible prompt-derived contract records, one per exact checker;
- exact pinned-checker booleans for a candidate response.

This module enumerates only the next-cardinality subsets required by the
pointwise-optimality theorem and asks the current semantic slot-feasibility
kernel for hard UNSAT certificates. It claims pointwise optimality only when
every required subset is semantically certified UNSAT.

No terminal frequency, case id, hidden kwargs, comparator response, or target
score is used.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility
from canonical.runtime import livebench_pointwise_optimality_certificate_v1 as structural

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_POINTWISE_CERTIFICATE_V1"


class PointwiseCertificateError(ValueError):
    pass


def certify(
    contracts: Sequence[Mapping[str, Any]],
    checker_results: Sequence[bool],
) -> dict[str, Any]:
    if len(contracts) != len(checker_results):
        raise PointwiseCertificateError("CONTRACT_RESULT_LENGTH_MISMATCH")
    if not contracts:
        raise PointwiseCertificateError("CONTRACTS_REQUIRED")
    if len(contracts) > structural.MAX_FROZEN_LEGACY_CHECKERS_PER_CASE:
        raise PointwiseCertificateError("CHECKER_COUNT_EXCEEDS_FROZEN_BOUND")

    flags = tuple(bool(x) for x in checker_results)
    g = sum(flags)
    required = structural.required_next_cardinality_subsets(len(flags), g)

    verified: list[tuple[int, ...]] = []
    semantic_evidence: list[dict[str, Any]] = []
    unresolved: list[tuple[int, ...]] = []

    for subset in required:
        subcontracts = [contracts[i] for i in subset]
        reasons = feasibility.hard_unsat_reasons(subcontracts)
        if reasons:
            verified.append(subset)
            semantic_evidence.append({
                "subset_indices": list(subset),
                "instruction_ids": [str(c["instruction_id"]) for c in subcontracts],
                "hard_unsat_reasons": list(reasons),
            })
        else:
            unresolved.append(subset)

    structural_result = structural.verify_pointwise_optimality_structure(
        flags,
        verified,
    )
    complete = (
        not unresolved
        and structural_result["status"] == "PASS__POINTWISE_OPTIMALITY_STRUCTURE_COMPLETE"
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__POINTWISE_SCORE_OPTIMAL_GIVEN_EXACT_CANDIDATE_CHECKER_RESULTS"
            if complete
            else "FAIL_CLOSED__SEMANTIC_UNSAT_COVERAGE_INCOMPLETE"
        ),
        "checker_count": len(flags),
        "candidate_true_checker_count": g,
        "candidate_exact_score_numerator": structural_result[
            "candidate_exact_score_numerator"
        ],
        "candidate_exact_score_denominator": structural_result[
            "candidate_exact_score_denominator"
        ],
        "required_next_cardinality_subset_count": len(required),
        "semantically_verified_unsat_subset_count": len(verified),
        "semantic_unsat_evidence": semantic_evidence,
        "unresolved_subset_indices": [list(x) for x in unresolved],
        "pointwise_optimal": complete,
        "assumption": (
            "checker_results must come from exact pinned checker postvalidation "
            "of the candidate response"
        ),
        "terminal_frequency_used": False,
        "terminal_case_id_used": False,
        "hidden_kwargs_used": False,
        "acceptance_credit": False,
    }


def run(args=None, root=None):
    args = args or {}
    return certify(args.get("contracts") or [], args.get("checker_results") or [])


if __name__ == "__main__":
    import json
    example = [
        {
            "instruction_id": "length_constraints:nth_paragraph_first_word",
            "slots": {"num_paragraphs": 2, "nth_paragraph": 1, "first_word": "alpha"},
        },
        {
            "instruction_id": "keywords:forbidden_words",
            "slots": {"forbidden_words": ["alpha"]},
        },
    ]
    print(json.dumps(certify(example, [True, False]), indent=2, sort_keys=True))
