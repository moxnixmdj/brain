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


class PointwiseSearchError(ValueError):
    pass


def _score(flags: Sequence[bool]) -> Fraction:
    return structural.exact_score(len(flags), sum(bool(x) for x in flags))


def select_best_postvalidated(
    contracts: Sequence[Mapping[str, Any]],
    evaluated_candidates: Iterable[Mapping[str, Any]],
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
    complete = cert.get("pointwise_optimal") is True

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__POINTWISE_OPTIMAL_CANDIDATE_CERTIFIED"
            if complete
            else "FAIL_CLOSED__BEST_CANDIDATE_OPTIMALITY_NOT_CERTIFIED"
        ),
        "evaluated_candidate_count": evaluated,
        "malformed_candidate_count": malformed,
        "best_candidate": best,
        "certificate": cert,
        "pointwise_optimal": complete,
        "terminal_frequency_used": False,
        "terminal_case_id_used": False,
        "hidden_kwargs_used": False,
        "comparator_response_used": False,
        "acceptance_credit": False,
    }


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

    result = select_best_postvalidated(contracts, evaluated)
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

    result = solve_with_checker(
        contracts,
        checker,
        max_per_subset=max_per_subset,
        max_total=max_total,
    )
    result["exact_checker_callback_required"] = False
    result["exact_checker_binding"] = binding
    return result

def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    """JSON-facing selector over externally exact-postvalidated candidates."""
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
