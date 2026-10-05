#!/usr/bin/env python3
"""Pointwise optimality certificate bridge for frozen LiveBench union25.

Given exact pinned-checker booleans for one candidate response, enumerate only
next-cardinality subsets. Each such subset is passed to the sound union25
semantic UNSAT kernel. If every next-cardinality subset is proved UNSAT, no
response can satisfy more checkers than the candidate, so the candidate is
pointwise score-optimal under the frozen scorer.

This is distribution-free and consumes no terminal frequencies or comparator
responses.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_pointwise_optimality_certificate_v1 as structural
from canonical.runtime import livebench_union25_semantic_unsat_kernel_v1 as semantic

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_POINTWISE_CERTIFICATE_V1"


class Union25PointwiseCertificateError(ValueError):
    pass


def certify(
    contracts: Sequence[Mapping[str, Any]],
    checker_results: Sequence[bool],
) -> dict[str, Any]:
    rows = [dict(c) for c in contracts]
    flags = tuple(bool(x) for x in checker_results)

    if not rows:
        raise Union25PointwiseCertificateError("CONTRACTS_REQUIRED")
    if len(rows) != len(flags):
        raise Union25PointwiseCertificateError("CONTRACT_RESULT_LENGTH_MISMATCH")
    if len(rows) > structural.MAX_FROZEN_LEGACY_CHECKERS_PER_CASE:
        raise Union25PointwiseCertificateError("CHECKER_COUNT_EXCEEDS_FROZEN_BOUND")

    ids = [str(c.get("instruction_id") or "") for c in rows]
    if any(not iid for iid in ids):
        raise Union25PointwiseCertificateError("INSTRUCTION_ID_REQUIRED")
    if len(ids) != len(set(ids)):
        raise Union25PointwiseCertificateError("DUPLICATE_INSTRUCTION_ID")

    g = sum(flags)
    required = structural.required_next_cardinality_subsets(len(flags), g)

    verified: list[tuple[int, ...]] = []
    evidence: list[dict[str, Any]] = []
    unresolved: list[tuple[int, ...]] = []

    for subset in required:
        subcontracts = [rows[i] for i in subset]
        proof = semantic.prove_unsat(subcontracts)
        if proof.get("jointly_unsatisfiable") is True:
            verified.append(subset)
            evidence.append({
                "subset_indices": list(subset),
                "instruction_ids": [
                    str(c["instruction_id"]) for c in subcontracts
                ],
                "semantic_unsat_evidence": proof["hard_unsat_evidence"],
            })
        else:
            unresolved.append(subset)

    structural_result = structural.verify_pointwise_optimality_structure(
        flags,
        verified,
    )
    complete = (
        not unresolved
        and structural_result["status"]
        == "PASS__POINTWISE_OPTIMALITY_STRUCTURE_COMPLETE"
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__UNION25_POINTWISE_SCORE_OPTIMAL_GIVEN_EXACT_CHECKER_RESULTS"
            if complete
            else "FAIL_CLOSED__UNION25_SEMANTIC_UNSAT_COVERAGE_INCOMPLETE"
        ),
        "instruction_ids": ids,
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
        "semantic_unsat_evidence": evidence,
        "unresolved_subset_indices": [list(x) for x in unresolved],
        "pointwise_optimal": complete,
        "assumption": (
            "checker_results are exact results from the frozen pinned checker "
            "bytes for the candidate response"
        ),
        "terminal_rows_read": 0,
        "hidden_kwargs_read": 0,
        "terminal_case_ids_read": 0,
        "case_frequencies_read": 0,
        "comparator_responses_read": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = dict(args or {})
    return certify(
        list(args.get("contracts") or []),
        list(args.get("checker_results") or []),
    )
