#!/usr/bin/env python3
"""Sound lower-bound / exact-witness theorem for LiveBench Union25 pointwise optimality.

A complete incompatibility map is unnecessary.

Let C be any collection of sound unavoidable-loss clauses. A clause is a
non-empty set of checker IDs that cannot all pass simultaneously for the
current visible contract. Therefore every exact failure set must hit every
clause. The minimum hitting-set size tau(C) is a rigorous lower bound on the
number of checker failures of every possible response.

If an independently exact-postvalidated candidate response fails exactly
tau(C) checkers, then the lower bound is attained and that response is
pointwise optimal. Unknown or unmodeled incompatibilities do not invalidate
this theorem: if they matter, exact postvalidation produces extra failures and
the equality gate fails closed.

This replaces the stronger and unnecessary requirement to enumerate every
possible incompatibility with:
  1. sound lower-bound clauses;
  2. exact minimum hitting-set computation (trivial for <=5 active checkers);
  3. exact pinned-checker postvalidation of one constructed witness.

No terminal row, hidden kwarg, target response, target score, or comparator
response is consumed by this module.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_SOUND_LOWER_BOUND_HITTING_SET_V1"
MAX_FROZEN_INSTRUCTIONS_PER_CASE = 5


class CertificateError(ValueError):
    pass


def _ids(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(x) for x in values if str(x)}))


def normalize_clauses(
    active_ids: Iterable[str],
    clauses: Iterable[Iterable[str]],
) -> tuple[frozenset[str], ...]:
    """Normalize non-empty unavoidable-loss clauses over the active checker set."""
    active = frozenset(_ids(active_ids))
    if len(active) > MAX_FROZEN_INSTRUCTIONS_PER_CASE:
        raise CertificateError("ACTIVE_SET_EXCEEDS_FROZEN_MAX_5")

    normalized: set[frozenset[str]] = set()
    for raw in clauses:
        clause = frozenset(_ids(raw))
        if not clause:
            raise CertificateError("EMPTY_UNAVOIDABLE_LOSS_CLAUSE")
        if not clause <= active:
            raise CertificateError(
                "CLAUSE_REFERENCES_INACTIVE_CHECKER:" + repr(sorted(clause - active))
            )
        normalized.add(clause)

    return tuple(sorted(normalized, key=lambda s: (len(s), tuple(sorted(s)))))


def is_hitting_set(
    failed_ids: Iterable[str],
    clauses: Iterable[Iterable[str]],
) -> bool:
    failed = frozenset(_ids(failed_ids))
    return all(bool(failed & frozenset(c)) for c in clauses)


def minimum_hitting_sets(
    active_ids: Iterable[str],
    clauses: Iterable[Iterable[str]],
) -> tuple[tuple[str, ...], ...]:
    """Enumerate every exact minimum hitting set."""
    active = _ids(active_ids)
    normalized = normalize_clauses(active, clauses)

    if not normalized:
        return ((),)

    for size in range(len(active) + 1):
        hits = tuple(
            subset
            for subset in combinations(active, size)
            if is_hitting_set(subset, normalized)
        )
        if hits:
            return hits

    raise AssertionError("FINITE_HITTING_SET_SEARCH_FAILED")


def certify_exact_witness_optimality(
    active_ids: Iterable[str],
    unavoidable_loss_clauses: Iterable[Iterable[str]],
    exact_failed_ids: Iterable[str],
    *,
    exact_postvalidation: bool,
    clause_soundness_bound: bool,
) -> dict[str, Any]:
    """Certify pointwise optimality from a sound lower bound plus exact witness.

    clause_soundness_bound means an external/content-addressed proof binds every
    supplied clause as genuinely unavoidable for this visible contract.
    exact_postvalidation means exact_failed_ids is the complete failure set
    returned by the frozen checker runtime for the candidate response.

    This module deliberately does not self-certify either premise.
    """
    active = _ids(active_ids)
    clauses = normalize_clauses(active, unavoidable_loss_clauses)
    failed = _ids(exact_failed_ids)

    if not set(failed) <= set(active):
        raise CertificateError("POSTVALIDATION_FAILURE_REFERENCES_INACTIVE_CHECKER")

    minima = minimum_hitting_sets(active, clauses)
    tau = len(minima[0])
    failure_count = len(failed)
    hits_all_sound_clauses = is_hitting_set(failed, clauses)

    premise_complete = bool(exact_postvalidation and clause_soundness_bound)
    lower_bound_attained = (
        premise_complete
        and hits_all_sound_clauses
        and failure_count == tau
    )
    pointwise_optimal = lower_bound_attained

    return {
        "schema": SCHEMA,
        "status": (
            "PROVED_POINTWISE_MAXIMUM_PASS_COUNT"
            if pointwise_optimal
            else "FAIL_CLOSED__POINTWISE_OPTIMALITY_NOT_PROVED"
        ),
        "active_ids": list(active),
        "active_count": len(active),
        "sound_unavoidable_loss_clauses": [sorted(c) for c in clauses],
        "minimum_unavoidable_failure_count": tau,
        "minimum_hitting_sets": [list(x) for x in minima],
        "exact_postvalidated_failed_ids": list(failed),
        "exact_postvalidated_failure_count": failure_count,
        "hits_all_sound_clauses": hits_all_sound_clauses,
        "clause_soundness_bound": bool(clause_soundness_bound),
        "exact_postvalidation": bool(exact_postvalidation),
        "lower_bound_attained": lower_bound_attained,
        "pointwise_maximum_pass_count_proved": pointwise_optimal,
        "maximum_pass_count_if_proved": (
            len(active) - tau if pointwise_optimal else None
        ),
        "complete_incompatibility_map_required": False,
        "reason": (
            "ANY_RESPONSE_MUST_FAIL_AT_LEAST_TAU_BY_SOUND_HITTING_SET_LOWER_BOUND__"
            "EXACT_WITNESS_FAILS_EXACTLY_TAU__THEREFORE_TAU_IS_THE_GLOBAL_MINIMUM"
            if pointwise_optimal
            else
            "EQUALITY_GATE_NOT_MET__UNKNOWN_INCOMPATIBILITIES_OR_UNBOUND_PREMISES_REMAIN_FAIL_CLOSED"
        ),
        "terminal_rows_read": 0,
        "hidden_terminal_kwargs_read": 0,
        "target_responses_read": 0,
        "target_scores_read": 0,
        "acceptance_credit": False,
        "family_credit": False,
        "capability_credit": False,
        "ownership_credit": False,
    }


def verify_theorem() -> dict[str, Any]:
    """Small deterministic regressions for the generic theorem."""
    active = ("SENTENCE", "FORBIDDEN", "NTH", "END", "SECTIONS")
    clauses = (
        ("SENTENCE",),
        ("FORBIDDEN", "NTH"),
        ("FORBIDDEN", "END"),
    )
    minima = minimum_hitting_sets(active, clauses)
    if minima != (("FORBIDDEN", "SENTENCE"),):
        raise AssertionError("OVERLAPPING_CLAUSE_MINIMUM_DRIFT:" + repr(minima))

    proved = certify_exact_witness_optimality(
        active,
        clauses,
        ("FORBIDDEN", "SENTENCE"),
        exact_postvalidation=True,
        clause_soundness_bound=True,
    )
    if not proved["pointwise_maximum_pass_count_proved"]:
        raise AssertionError("ATTAINED_LOWER_BOUND_NOT_PROMOTED")

    extra_failure = certify_exact_witness_optimality(
        active,
        clauses,
        ("FORBIDDEN", "SENTENCE", "SECTIONS"),
        exact_postvalidation=True,
        clause_soundness_bound=True,
    )
    if extra_failure["pointwise_maximum_pass_count_proved"]:
        raise AssertionError("EXTRA_FAILURE_FALSE_CREDIT")

    unbound = certify_exact_witness_optimality(
        active,
        clauses,
        ("FORBIDDEN", "SENTENCE"),
        exact_postvalidation=False,
        clause_soundness_bound=True,
    )
    if unbound["pointwise_maximum_pass_count_proved"]:
        raise AssertionError("UNBOUND_POSTVALIDATION_FALSE_CREDIT")

    return {
        "schema": SCHEMA,
        "status": "PASS__SOUND_LOWER_BOUND_PLUS_EXACT_WITNESS_THEOREM",
        "frozen_max_active_checkers": MAX_FROZEN_INSTRUCTIONS_PER_CASE,
        "maximum_subset_candidates": 2 ** MAX_FROZEN_INSTRUCTIONS_PER_CASE,
        "deleted_proof_requirement": "COMPLETE_INCOMPATIBILITY_MAP",
        "replacement": (
            "SOUND_UNAVOIDABLE_LOSS_CLAUSES_PLUS_EXACT_MINIMUM_HITTING_SET_"
            "PLUS_EXACT_POSTVALIDATED_WITNESS_ATTAINING_THE_LOWER_BOUND"
        ),
        "acceptance_credit": False,
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = dict(args or {})
    return certify_exact_witness_optimality(
        args.get("active_ids") or (),
        args.get("unavoidable_loss_clauses") or (),
        args.get("exact_failed_ids") or (),
        exact_postvalidation=bool(args.get("exact_postvalidation", False)),
        clause_soundness_bound=bool(args.get("clause_soundness_bound", False)),
    )


if __name__ == "__main__":
    import json
    print(json.dumps(verify_theorem(), indent=2, sort_keys=True))
