#!/usr/bin/env python3
"""Pointwise-optimal search bridge for frozen LiveBench legacy15.

This composes three already-bounded pieces:
1. visible-only subset-relaxation candidate generation;
2. exact full-case checker postvalidation supplied by an independent runner;
3. semantic next-cardinality UNSAT certification.

The core selector can also consume pre-postvalidated candidate rows. It never
uses terminal frequencies, comparator responses, case ids, hidden kwargs, or
target scores.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Callable, Iterable, Mapping, Sequence

from canonical.runtime import livebench_legacy15_pointwise_certificate_v1 as certificate
from canonical.runtime import livebench_legacy15_exact_postvalidator_v1 as exact_postvalidator
from canonical.runtime import livebench_legacy15_relaxed_candidate_search_v1 as relaxed
from canonical.runtime import livebench_pointwise_optimality_certificate_v1 as structural

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_POINTWISE_SEARCH_V1"
MAX_CHECKERS = structural.MAX_FROZEN_LEGACY_CHECKERS_PER_CASE
PINNED_STRICT_EVALUATOR_BLOB = "4a341984936c4d609644a3b77f8c030ac5aa7269"


class PointwiseSearchError(ValueError):
    pass


def _score(flags: Sequence[bool]) -> Fraction:
    return structural.exact_score(len(flags), sum(bool(x) for x in flags))


def _select_best_postvalidated(
    contracts: Sequence[Mapping[str, Any]],
    evaluated_candidates: Iterable[Mapping[str, Any]],
    *,
    checker_vector_authoritative: bool,
    checker_vector_authority: str,
) -> dict[str, Any]:
    rows = [dict(c) for c in contracts]
    if not rows:
        raise PointwiseSearchError("CONTRACTS_REQUIRED")
    if len(rows) > MAX_CHECKERS:
        raise PointwiseSearchError("CHECKER_COUNT_EXCEEDS_FROZEN_BOUND")

    best: dict[str, Any] | None = None
    evaluated = 0
    malformed = 0

    for raw in evaluated_candidates:
        item = dict(raw)
        flags = tuple(bool(x) for x in (item.get("checker_results") or []))
        if len(flags) != len(rows):
            malformed += 1
            continue
        evaluated += 1
        score = _score(flags)
        candidate = {
            "response": str(item.get("response") or ""),
            "checker_results": list(flags),
            "true_checker_count": sum(flags),
            "score_numerator": score.numerator,
            "score_denominator": score.denominator,
            "source": item.get("source"),
        }
        if best is None:
            best = candidate
            continue
        best_score = Fraction(best["score_numerator"], best["score_denominator"])
        if score > best_score:
            best = candidate
        elif score == best_score and candidate["true_checker_count"] > best["true_checker_count"]:
            best = candidate

    if best is None:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_NO_VALID_POSTVALIDATED_CANDIDATES",
            "evaluated_candidate_count": evaluated,
            "malformed_candidate_count": malformed,
            "pointwise_optimal": False,
            "terminal_frequency_used": False,
            "terminal_case_id_used": False,
            "hidden_kwargs_used": False,
            "acceptance_credit": False,
        }

    cert = certificate.certify(rows, best["checker_results"])
    structurally_complete = cert.get("pointwise_optimal") is True
    authoritative_complete = structurally_complete and checker_vector_authoritative

    if authoritative_complete:
        status = "PASS__POINTWISE_OPTIMAL_CANDIDATE_CERTIFIED"
    elif structurally_complete:
        status = "CONDITIONAL__POINTWISE_OPTIMAL_GIVEN_UNVERIFIED_CHECKER_VECTOR"
    else:
        status = "FAIL_CLOSED__BEST_CANDIDATE_OPTIMALITY_NOT_CERTIFIED"

    return {
        "schema": SCHEMA,
        "status": status,
        "evaluated_candidate_count": evaluated,
        "malformed_candidate_count": malformed,
        "best_candidate": best,
        "certificate": cert,
        "pointwise_optimal_given_checker_vector": structurally_complete,
        "checker_vector_authoritative": checker_vector_authoritative,
        "checker_vector_authority": checker_vector_authority,
        "pointwise_optimal": authoritative_complete,
        "terminal_frequency_used": False,
        "terminal_case_id_used": False,
        "hidden_kwargs_used": False,
        "comparator_response_used": False,
        "acceptance_credit": False,
    }


def select_best_postvalidated(
    contracts: Sequence[Mapping[str, Any]],
    evaluated_candidates: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Select over caller-supplied vectors without granting vector authority.

    A semantic UNSAT certificate can prove maximality *given* a checker vector,
    but it cannot prove that the supplied vector is truthful. This public path
    therefore never emits an authoritative pointwise PASS from external booleans.
    """
    return _select_best_postvalidated(
        contracts,
        evaluated_candidates,
        checker_vector_authoritative=False,
        checker_vector_authority="CALLER_SUPPLIED_UNVERIFIED",
    )


def solve_with_checker(
    contracts: Sequence[Mapping[str, Any]],
    checker: Callable[[str, Sequence[Mapping[str, Any]]], Sequence[bool]],
    *,
    max_per_subset: int = relaxed.DEFAULT_MAX_PER_SUBSET,
    max_total: int = relaxed.DEFAULT_MAX_TOTAL,
) -> dict[str, Any]:
    """Generate bounded candidates, exact-postvalidate, then certify maximality.

    The checker callable must evaluate the candidate response against every
    supplied contract in order using the exact pinned public checker semantics.
    """
    pool = relaxed.generate_relaxed(
        [dict(c) for c in contracts],
        max_per_subset=max_per_subset,
        max_total=max_total,
    )
    if pool.get("status") != "PASS_CANDIDATE_POOL":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_CANDIDATE_POOL",
            "candidate_pool": pool,
            "pointwise_optimal": False,
            "terminal_frequency_used": False,
            "acceptance_credit": False,
        }

    evaluated = []
    for row in pool["candidates"]:
        response = str(row["response"])
        flags = tuple(bool(x) for x in checker(response, contracts))
        if len(flags) != len(contracts):
            raise PointwiseSearchError("CHECKER_RESULT_LENGTH_MISMATCH")
        evaluated.append({
            "response": response,
            "checker_results": list(flags),
            "source": row.get("provenance"),
        })

    result = _select_best_postvalidated(
        contracts,
        evaluated,
        checker_vector_authoritative=False,
        checker_vector_authority="CALLBACK_UNVERIFIED",
    )
    result["candidate_pool_count"] = pool["candidate_count"]
    result["subset_attempt_count"] = pool["subset_attempt_count"]
    result["exact_checker_callback_required"] = True
    return result



def solve_with_pinned_livebench(
    contracts: Sequence[Mapping[str, Any]],
    livebench_root: str,
    *,
    max_per_subset: int = relaxed.DEFAULT_MAX_PER_SUBSET,
    max_total: int = relaxed.DEFAULT_MAX_TOTAL,
) -> dict[str, Any]:
    """Run the bounded pointwise search against exact pinned legacy checker bytes."""
    registry, binding = exact_postvalidator.load_pinned_registry(livebench_root)

    def checker(
        response: str,
        rows: Sequence[Mapping[str, Any]],
    ) -> Sequence[bool]:
        out = exact_postvalidator.evaluate_with_registry(response, rows, registry)
        return out["checker_results"]

    pool = relaxed.generate_relaxed(
        [dict(c) for c in contracts],
        max_per_subset=max_per_subset,
        max_total=max_total,
    )
    if pool.get("status") != "PASS_CANDIDATE_POOL":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED_CANDIDATE_POOL",
            "candidate_pool": pool,
            "pointwise_optimal": False,
            "checker_vector_authoritative": False,
            "checker_vector_authority": "PINNED_POSTVALIDATOR_NOT_REACHED",
            "terminal_frequency_used": False,
            "acceptance_credit": False,
        }

    evaluated = []
    for row in pool["candidates"]:
        response = str(row["response"])
        flags = tuple(bool(x) for x in checker(response, contracts))
        if len(flags) != len(contracts):
            raise PointwiseSearchError("CHECKER_RESULT_LENGTH_MISMATCH")
        evaluated.append({
            "response": response,
            "checker_results": list(flags),
            "source": row.get("provenance"),
        })

    evaluation_blob = (
        binding.get("evaluation_main_blob")
        or binding.get("evaluation_main_git_blob_sha")
    )
    strict_gate_bound = (
        binding.get("strict_nonempty_gate_bound") is True
        or bool(binding.get("strict_nonempty_guard"))
    )
    postvalidator_authoritative = (
        evaluation_blob == PINNED_STRICT_EVALUATOR_BLOB
        and strict_gate_bound
    )
    result = _select_best_postvalidated(
        contracts,
        evaluated,
        checker_vector_authoritative=postvalidator_authoritative,
        checker_vector_authority=(
            "EXACT_PINNED_LIVEBENCH_STRICT_POSTVALIDATOR"
            if postvalidator_authoritative
            else "PINNED_CHECKERS_WITHOUT_BOUND_STRICT_WRAPPER"
        ),
    )
    result["candidate_pool_count"] = pool["candidate_count"]
    result["subset_attempt_count"] = pool["subset_attempt_count"]
    result["exact_checker_callback_required"] = False
    result["exact_checker_binding"] = binding
    result["strict_evaluator_binding_required"] = PINNED_STRICT_EVALUATOR_BLOB
    return result

def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    """JSON-facing conditional selector over caller-supplied checker vectors.

    This surface cannot authenticate external checker booleans and therefore
    cannot emit an authoritative pointwise PASS. Use solve_with_pinned_livebench
    for the exact source-bound authority path.
    """
    args = args or {}
    return select_best_postvalidated(
        args.get("contracts") or [],
        args.get("evaluated_candidates") or [],
    )


if __name__ == "__main__":
    import json
    import sys

    payload = json.load(sys.stdin)
    print(json.dumps(run(payload), ensure_ascii=False, indent=2, sort_keys=True))
