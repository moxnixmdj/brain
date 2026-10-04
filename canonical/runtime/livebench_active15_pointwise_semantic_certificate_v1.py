#!/usr/bin/env python3
"""Couple exact checker outcomes to semantic UNSAT and pointwise optimality.

This kernel consumes only visible checker contracts plus exact checker booleans
for one candidate response.  It proves pointwise score optimality when every
required next-cardinality subset is certified jointly UNSAT by the pinned
semantic feasibility kernel.  No terminal rows, frequencies, comparator
responses, or hidden kwargs are used.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility
from canonical.runtime import livebench_pointwise_optimality_certificate_v1 as pointwise

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_ACTIVE15_POINTWISE_SEMANTIC_CERTIFICATE_V1"


def certify(
    contracts: Sequence[Mapping[str, Any]],
    checker_results: Sequence[bool],
) -> dict[str, Any]:
    contracts = tuple(contracts)
    flags = tuple(checker_results)

    if not contracts:
        raise ValueError("CONTRACTS_REQUIRED")
    if len(contracts) != len(flags):
        raise ValueError("CONTRACT_RESULT_LENGTH_MISMATCH")
    if any(type(x) is not bool for x in flags):
        raise ValueError("CHECKER_RESULTS_MUST_BE_BOOL")
    if len(contracts) > pointwise.MAX_FROZEN_LEGACY_CHECKERS_PER_CASE:
        raise ValueError("K_EXCEEDS_FROZEN_GENERATOR_BOUND")

    parent = feasibility.classify_visible_contracts(contracts)
    if str(parent["status"]).startswith("FAIL_CLOSED"):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__INVALID_VISIBLE_CONTRACT_SET",
            "parent_contract_status": parent["status"],
            "terminal_data_used": False,
            "acceptance_credit": False,
        }

    k = len(flags)
    g = sum(flags)
    required = pointwise.required_next_cardinality_subsets(k, g)

    supplied: list[tuple[int, ...]] = []
    semantic_proofs: list[dict[str, Any]] = []
    residual: list[dict[str, Any]] = []

    for subset in required:
        subcontracts = tuple(contracts[i] for i in subset)
        reasons = feasibility.hard_unsat_reasons(subcontracts)
        record = {
            "checker_indices": list(subset),
            "instruction_ids": [
                str(contracts[i]["instruction_id"]) for i in subset
            ],
        }
        if reasons:
            supplied.append(subset)
            semantic_proofs.append({
                **record,
                "status": "PROVED_UNSAT",
                "hard_unsat_reasons": list(reasons),
            })
        else:
            residual.append({
                **record,
                "status": "SEMANTIC_UNSAT_NOT_YET_CERTIFIED",
            })

    structural = pointwise.verify_pointwise_optimality_structure(flags, supplied)
    complete = structural["status"] == "PASS__POINTWISE_OPTIMALITY_STRUCTURE_COMPLETE"

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__POINTWISE_OPTIMALITY_SEMANTICALLY_CERTIFIED"
            if complete
            else "FAIL_CLOSED__SEMANTIC_UNSAT_COVER_INCOMPLETE"
        ),
        "checker_count": k,
        "candidate_true_checker_count": g,
        "candidate_checker_results": list(flags),
        "candidate_exact_score_numerator": structural[
            "candidate_exact_score_numerator"
        ],
        "candidate_exact_score_denominator": structural[
            "candidate_exact_score_denominator"
        ],
        "required_next_cardinality_subset_count": len(required),
        "semantically_proved_unsat_subset_count": len(supplied),
        "semantic_unsat_proofs": semantic_proofs,
        "residual_uncertified_subsets": residual,
        "structural_certificate": structural,
        "pointwise_optimality_proved": complete,
        "terminal_data_used": False,
        "terminal_frequency_used": False,
        "hidden_kwargs_used": False,
        "acceptance_credit": False,
    }


def run(args=None, root=None):
    demo = [
        {
            "instruction_id": feasibility.NTH,
            "slots": {
                "num_paragraphs": 2,
                "nth_paragraph": 1,
                "first_word": "section",
            },
        },
        {
            "instruction_id": feasibility.FORBIDDEN,
            "slots": {"forbidden_words": ["section"]},
        },
    ]
    return certify(demo, [True, False])


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, sort_keys=True))
