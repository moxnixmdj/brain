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
        response = str(item.get("response") or "")
        raw_flags = tuple(bool(x) for x in (item.get("checker_results") or []))
        # Frozen strict evaluation applies response.strip() before every
        # instruction checker. Never allow a raw checker callback to turn an
        # empty/whitespace response into positive benchmark credit.
        flags = raw_flags if response.strip() else tuple(False for _ in raw_flags)
        if len(flags) != len(rows):
            malformed += 1
            continue
        evaluated += 1
        score = _score(flags)
        candidate = {
            "response": response,
            "checker_results": list(flags),
            "strict_nonempty_response_gate_applied": True,
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
    """Conditional selector for externally supplied checker vectors.

    The pointwise theorem can prove maximality given a vector, but this surface
    cannot authenticate that the response actually produced that vector.
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
    nltk_wheel_path: str | None = None,
    nltk_data_root: str | None = None,
    max_per_subset: int = relaxed.DEFAULT_MAX_PER_SUBSET,
    max_total: int = relaxed.DEFAULT_MAX_TOTAL,
) -> dict[str, Any]:
    """Run bounded pointwise search through proof-grade pinned dependencies.

    For word/sentence contracts the exact checker semantics depend on NLTK code
    and Punkt data. Those artifacts must be hermetically bound before this path
    can obtain checker-vector authority.
    """
    registry, binding = exact_postvalidator.load_proofgrade_registry(
        livebench_root,
        contracts,
        nltk_wheel_path=nltk_wheel_path,
        nltk_data_root=nltk_data_root,
    )

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
            "checker_vector_authority": "PROOFGRADE_POSTVALIDATOR_NOT_REACHED",
            "terminal_frequency_used": False,
            "acceptance_credit": False,
        }

    evaluated = []
    for row in pool["candidates"]:
        response = str(row["response"])
        out = exact_postvalidator.evaluate_with_registry(
            response,
            contracts,
            registry,
        )
        flags = tuple(bool(x) for x in out["checker_results"])
        if len(flags) != len(contracts):
            raise PointwiseSearchError("CHECKER_RESULT_LENGTH_MISMATCH")
        evaluated.append({
            "response": response,
            "checker_results": list(flags),
            "source": row.get("provenance"),
        })

    source_binding = dict(binding.get("source") or {})
    evaluation_blob = (
        source_binding.get("evaluation_main_blob")
        or source_binding.get("evaluation_main_git_blob_sha")
    )
    strict_gate_bound = (
        source_binding.get("strict_nonempty_gate_bound") is True
        or bool(source_binding.get("strict_nonempty_guard"))
    )
    runtime_bound = binding.get("proofgrade_runtime_dependencies_bound") is True
    proofgrade_authoritative = (
        evaluation_blob == PINNED_STRICT_EVALUATOR_BLOB
        and strict_gate_bound
        and runtime_bound
    )

    result = _select_best_postvalidated(
        contracts,
        evaluated,
        checker_vector_authoritative=proofgrade_authoritative,
        checker_vector_authority=(
            "EXACT_PINNED_LIVEBENCH_PROOFGRADE_RUNTIME"
            if proofgrade_authoritative
            else "PINNED_SOURCE_WITHOUT_COMPLETE_PROOFGRADE_AUTHORITY"
        ),
    )
    result["candidate_pool_count"] = pool["candidate_count"]
    result["subset_attempt_count"] = pool["subset_attempt_count"]
    result["exact_checker_callback_required"] = False
    result["exact_checker_binding"] = binding
    result["strict_evaluator_binding_required"] = PINNED_STRICT_EVALUATOR_BLOB
    result["proofgrade_runtime_dependencies_required"] = True
    return result

def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    """JSON-facing conditional selector over caller-supplied checker vectors."""
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
