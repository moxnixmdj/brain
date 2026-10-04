#!/usr/bin/env python3
"""Exact pointwise audit over the 192-state legacy15 lexical quotient.

This audit covers the maximal lexical interaction surface:
existence + forbidden words + nth-paragraph first word + fixed ending.

For every reachable collision signature it:
1. constructs visible generator-admitted contracts;
2. checks the sound slot-feasibility UNSAT expectation;
3. runs the bounded relaxed candidate search;
4. postvalidates candidates with the exact pinned strict checker semantics; and
5. requires a machine-checkable pointwise-optimality certificate.

No terminal row content, hidden kwargs, case IDs, comparator responses, scores,
or case frequencies are consumed.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_legacy15_exact_postvalidator_v1 as exact_post
from canonical.runtime import livebench_legacy15_lexical_collision_signatures_v2 as quotient
from canonical.runtime import livebench_legacy15_pointwise_search_v1 as pointwise
from canonical.runtime import livebench_legacy15_slot_feasibility_v1 as feasibility

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_LEXICAL_POINTWISE_AUDIT_V1"


def _contract(iid: str, **slots: Any) -> dict[str, Any]:
    return {
        "instruction_id": iid,
        "slots": slots,
        "parameter_complete": True,
    }


def _contracts(sig: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        _contract(
            "keywords:existence",
            keywords=list(sig["existence_keywords"]),
        ),
        _contract(
            "keywords:forbidden_words",
            forbidden_words=list(sig["forbidden_words"]),
        ),
        _contract(
            "length_constraints:nth_paragraph_first_word",
            num_paragraphs=2,
            nth_paragraph=1,
            first_word=str(sig["nth_word"]),
        ),
        _contract(
            "startend:end_checker",
            end_phrase=str(sig["end_phrase"]),
        ),
    ]


def audit(
    livebench_root: str,
    *,
    max_per_subset: int = 8,
    max_total: int = 256,
) -> dict[str, Any]:
    words = quotient.load_pinned_word_list(livebench_root)
    signatures = quotient.enumerate_signatures(words)

    # These four checkers do not use NLTK word/sentence semantics, so the
    # proof-grade loader correctly requires no NLTK artifact bundle.
    prototype = _contracts(signatures[0])
    registry, binding = exact_post.load_proofgrade_registry(
        livebench_root,
        prototype,
    )

    def checker(
        response: str,
        contracts: Sequence[Mapping[str, Any]],
    ) -> Sequence[bool]:
        return exact_post.evaluate_with_registry(
            response,
            contracts,
            registry,
        )["checker_results"]

    full_score = 0
    partial_optimal = 0
    feasibility_mismatch = 0
    pointwise_failures: list[dict[str, Any]] = []
    true_count_histogram: dict[str, int] = {}

    for index, sig in enumerate(signatures):
        contracts = _contracts(sig)
        expected_unsat = bool(sig["lexical_hard_unsat_expected"])
        slot = feasibility.classify_visible_contracts(contracts)
        observed_unsat = slot.get("status") == "PROVED_UNSAT"
        if observed_unsat != expected_unsat:
            feasibility_mismatch += 1
            if len(pointwise_failures) < 25:
                pointwise_failures.append({
                    "index": index,
                    "stage": "FEASIBILITY_EXPECTATION",
                    "expected_unsat": expected_unsat,
                    "observed": slot,
                })
            continue

        result = pointwise.solve_with_checker(
            contracts,
            checker,
            max_per_subset=max_per_subset,
            max_total=max_total,
        )
        if (
            result.get("status") != "PASS__POINTWISE_OPTIMAL_CANDIDATE_CERTIFIED"
            or result.get("pointwise_optimal") is not True
        ):
            if len(pointwise_failures) < 25:
                pointwise_failures.append({
                    "index": index,
                    "stage": "POINTWISE_CERTIFICATE",
                    "signature": {
                        "nth_category": sig["nth_category"],
                        "nth_in_forbidden": sig["nth_in_forbidden"],
                        "special_forbidden_membership": sig["special_forbidden_membership"],
                        "end_phrase": sig["end_phrase"],
                    },
                    "result": result,
                })
            continue

        best = dict(result.get("best_candidate") or {})
        g = int(best.get("true_checker_count", -1))
        true_count_histogram[str(g)] = true_count_histogram.get(str(g), 0) + 1

        # With these four contracts, every lexical contradiction is mediated by
        # ForbiddenWords. Removing that checker leaves existence+nth+end jointly
        # satisfiable, so hard-UNSAT signatures have exact optimum g=3. All
        # non-collision signatures must achieve all four.
        expected_g = 3 if expected_unsat else 4
        if g != expected_g:
            if len(pointwise_failures) < 25:
                pointwise_failures.append({
                    "index": index,
                    "stage": "OPTIMUM_CARDINALITY",
                    "expected_true_checker_count": expected_g,
                    "observed_true_checker_count": g,
                    "result": result,
                })
            continue

        if g == 4:
            full_score += 1
        else:
            partial_optimal += 1

    resolved = full_score + partial_optimal
    all_pass = (
        feasibility_mismatch == 0
        and not pointwise_failures
        and resolved == len(signatures)
    )
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__ALL_192_LEXICAL_SIGNATURES_POINTWISE_OPTIMAL"
            if all_pass
            else "FAIL_CLOSED__LEXICAL_POINTWISE_RESIDUAL"
        ),
        "signature_count": len(signatures),
        "feasibility_mismatch_count": feasibility_mismatch,
        "pointwise_resolved_count": resolved,
        "full_score_signature_count": full_score,
        "partial_pointwise_optimal_signature_count": partial_optimal,
        "true_checker_count_histogram": true_count_histogram,
        "expected_full_score_signature_count": 37,
        "expected_partial_optimal_signature_count": 155,
        "partial_signature_exact_score": "3/8",
        "proofgrade_binding": binding,
        "failures": pointwise_failures,
        "terminal_data_used": False,
        "terminal_frequency_inferred": False,
        "comparator_response_used": False,
        "acceptance_credit": False,
    }


def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    livebench_root = args.get("livebench_root")
    if not livebench_root:
        raise ValueError("LIVEBENCH_ROOT_REQUIRED")
    return audit(
        str(livebench_root),
        max_per_subset=int(args.get("max_per_subset") or 8),
        max_total=int(args.get("max_total") or 256),
    )


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(run(json.load(sys.stdin)), ensure_ascii=False, indent=2, sort_keys=True))
