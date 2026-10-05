#!/usr/bin/env python3
"""Candidate pointwise solver for the exact frozen-schema19 LiveBench envelope.

The frozen parquet schema reduces the ambiguity-free terminal surface to:
  * all already-closed Active15 structures, plus
  * exactly six extra signatures:
      constrained
      english_capital
      english_lowercase
      no_comma
      english_capital + no_comma
      english_lowercase + no_comma

The first four extra signatures are handled by the existing Active15+1 solver.
This module closes the two remaining compositions by observing that ASCII case
normalization preserves comma identity. Therefore adding no_comma on top of a
case-extra witness creates exactly one possible new mandatory-loss coordinate:
a retained repeat_prompt whose required visible prefix itself contains a comma.

If the composed response contains any other comma, this solver fails closed.
Independent exact pinned-checker postvalidation remains required for promotion.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import livebench_active15_plus_one_noarg_pointwise_v1 as plus1
from canonical.runtime import livebench_frozen_schema19_envelope_v1 as env
from canonical.runtime import livebench_legacy15_contract_composer_v2 as composer
from canonical.runtime import livebench_legacy15_pointwise_optimal_v1 as active
from canonical.runtime import livebench_union25_archetypes_v1 as u

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_SCHEMA19_POINTWISE_CANDIDATE_V1"

CASE_EXTRAS = frozenset({u.ENGLISH_CAPITAL, u.ENGLISH_LOWERCASE})
NO_COMMA = u.NO_COMMA
CONSTRAINED = u.CONSTRAINED


def _slots(c: Mapping[str, Any]) -> dict[str, Any]:
    return dict(c.get("slots") or {})


def _ids(contracts: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(str(c.get("instruction_id") or "") for c in contracts)


def _fail(error: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "error": error,
        "acceptance_credit": False,
        **extra,
    }


def _strict_score(total: int, passed: int) -> float:
    return active.strict_score_from_pass_count(total, passed)


def _retained_contracts(
    contracts: Sequence[Mapping[str, Any]],
    sacrificed: set[str],
) -> list[dict[str, Any]]:
    return [
        dict(c)
        for c in contracts
        if str(c.get("instruction_id")) not in sacrificed
    ]


def _forced_repeat_comma(
    retained: Sequence[Mapping[str, Any]],
) -> bool:
    repeat = next(
        (c for c in retained if str(c.get("instruction_id")) == composer.REPEAT),
        None,
    )
    if repeat is None:
        return False
    return "," in str(_slots(repeat).get("prompt_to_repeat") or "")


def solve_contracts(contracts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    contracts = [dict(c) for c in contracts]
    ids = _ids(contracts)
    if not contracts:
        return _fail("NO_CONTRACTS")
    if any(not x for x in ids):
        return _fail("MISSING_INSTRUCTION_ID")
    if len(ids) != len(set(ids)):
        return _fail("DUPLICATE_ID")
    if len(ids) > u.MAX_GENERATED_INSTRUCTIONS:
        return _fail("OUTSIDE_PINNED_MAX_5")
    if not set(ids) <= set(env.SCHEMA19):
        return _fail("OUTSIDE_FROZEN_SCHEMA19_ENVELOPE")
    if not u.compatible(ids):
        return _fail("OUTSIDE_PINNED_COMPATIBILITY_GRAPH")

    extras = tuple(iid for iid in ids if iid not in u.ACTIVE15)

    # Embedded Active15 is already independently closed.
    if not extras:
        out = active.solve_contracts(contracts)
        return {
            "schema": SCHEMA,
            "status": (
                "CANDIDATE_POINTWISE_OPTIMAL_SCHEMA19"
                if out.get("status") == "CANDIDATE_POINTWISE_OPTIMAL"
                else "FAIL_CLOSED"
            ),
            "route": "ACTIVE15",
            "delegated": out,
            "response": out.get("response"),
            "sacrificed_instruction_ids": out.get("sacrificed_instruction_ids"),
            "instruction_count": len(contracts),
            "theoretical_max_pass_count": out.get("theoretical_max_pass_count"),
            "theoretical_pointwise_optimum_strict_score": out.get(
                "theoretical_pointwise_optimum_strict_score"
            ),
            "acceptance_credit": False,
        }

    extra_set = frozenset(extras)
    allowed_extra_signatures = {
        frozenset({CONSTRAINED}),
        frozenset({u.ENGLISH_CAPITAL}),
        frozenset({u.ENGLISH_LOWERCASE}),
        frozenset({NO_COMMA}),
        frozenset({u.ENGLISH_CAPITAL, NO_COMMA}),
        frozenset({u.ENGLISH_LOWERCASE, NO_COMMA}),
    }
    if extra_set not in allowed_extra_signatures:
        return _fail(
            "SCHEMA19_EXTRA_SIGNATURE_DRIFT",
            observed_extras=sorted(extra_set),
        )

    # Four signatures are exactly the already-built Active15+1 theorem.
    if len(extra_set) == 1:
        out = plus1.solve_contracts(contracts)
        return {
            "schema": SCHEMA,
            "status": (
                "CANDIDATE_POINTWISE_OPTIMAL_SCHEMA19"
                if out.get("status") == "CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE"
                else "FAIL_CLOSED"
            ),
            "route": "ACTIVE15_PLUS_ONE",
            "delegated": out,
            "response": out.get("response"),
            "sacrificed_instruction_ids": out.get("sacrificed_instruction_ids"),
            "instruction_count": len(contracts),
            "theoretical_max_pass_count": out.get("theoretical_max_pass_count"),
            "theoretical_pointwise_optimum_strict_score": out.get(
                "theoretical_pointwise_optimum_strict_score"
            ),
            "acceptance_credit": False,
        }

    # The only two two-extra signatures are CASE + NO_COMMA.
    case_extra = next((x for x in extra_set if x in CASE_EXTRAS), None)
    if case_extra is None or NO_COMMA not in extra_set:
        return _fail("UNREACHABLE_TWO_EXTRA_SIGNATURE")

    without_no_comma = [
        c for c in contracts if str(c.get("instruction_id")) != NO_COMMA
    ]
    base = plus1.solve_contracts(without_no_comma)
    if base.get("status") != "CANDIDATE_POINTWISE_OPTIMAL_ACTIVE15_PLUS_ONE":
        return _fail("CASE_SUBPROBLEM_NOT_SOLVED", case_result=base)

    response = str(base.get("response") or "")
    sacrificed = set(map(str, base.get("sacrificed_instruction_ids") or []))
    retained = _retained_contracts(without_no_comma, sacrificed)
    forced_comma = _forced_repeat_comma(retained)

    if "," in response:
        if not forced_comma:
            return _fail(
                "UNEXPLAINED_COMMA_IN_CASE_WITNESS",
                case_extra=case_extra,
                case_result=base,
            )
        # Repeat-prefix comma and no_comma form a sound unavoidable pair.
        # Dropping NO_COMMA adds one failure and attains that lower bound.
        sacrificed.add(NO_COMMA)
        comma_proof = (
            "RETAINED_REPEAT_PREFIX_CONTAINS_COMMA__REPEAT_AND_NO_COMMA_CANNOT_"
            "BOTH_PASS__CASE_NORMALIZATION_PRESERVES_COMMA__DROP_NO_COMMA"
        )
    else:
        if forced_comma:
            return _fail(
                "CASE_WITNESS_LOST_REQUIRED_REPEAT_PREFIX_COMMA",
                case_extra=case_extra,
                case_result=base,
            )
        comma_proof = (
            "CASE_WITNESS_IS_COMMA_FREE__ASCII_CASE_NORMALIZATION_CANNOT_CREATE_"
            "COMMAS__NO_COMMA_PASSES_WITH_ZERO_ADDITIONAL_LOSS"
        )

    total = len(contracts)
    max_pass = total - len(sacrificed)
    return {
        "schema": SCHEMA,
        "status": "CANDIDATE_POINTWISE_OPTIMAL_SCHEMA19",
        "route": "ACTIVE15_PLUS_CASE_PLUS_NO_COMMA",
        "case_extra": case_extra,
        "response": response,
        "instruction_ids": sorted(ids),
        "sacrificed_instruction_ids": sorted(sacrificed),
        "instruction_count": total,
        "theoretical_max_pass_count": max_pass,
        "theoretical_pointwise_optimum_strict_score": _strict_score(total, max_pass),
        "new_composition_proof": comma_proof,
        "case_subproblem": base,
        "case_normalization_comma_invariant": True,
        "terminal_rows_used": False,
        "terminal_instruction_ids_used": False,
        "hidden_kwargs_used": False,
        "target_responses_used": False,
        "target_scores_used": False,
        "acceptance_credit": False,
        "hard_nonclaims": [
            "NO_PROMOTION_BEFORE_EXACT_PINNED_CHECKER_POSTVALIDATION",
            "NO_TERMINAL_GOAL_COMPLETION_CLAIM",
        ],
    }


def verify_scope_closure() -> dict[str, Any]:
    upstream = env.verify()
    observed = {frozenset(x) for x in upstream["remaining_extra_signatures"]}
    expected = {
        frozenset({CONSTRAINED}),
        frozenset({u.ENGLISH_CAPITAL}),
        frozenset({u.ENGLISH_LOWERCASE}),
        frozenset({NO_COMMA}),
        frozenset({u.ENGLISH_CAPITAL, NO_COMMA}),
        frozenset({u.ENGLISH_LOWERCASE, NO_COMMA}),
    }
    if observed != expected:
        raise AssertionError("SCHEMA19_EXTRA_SIGNATURE_SET_DRIFT")

    # Source-level algebraic fact used by the two new compositions.
    probes = [
        "Alpha beta",
        "Alpha, beta",
        "P.P.S alpha",
        '"Alpha, beta?"',
        "Section 1 alpha",
    ]
    for text in probes:
        if ("," in text.upper()) != ("," in text):
            raise AssertionError("UPPERCASE_CHANGED_COMMA_IDENTITY")
        if ("," in text.lower()) != ("," in text):
            raise AssertionError("LOWERCASE_CHANGED_COMMA_IDENTITY")

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__SCHEMA19_EXTRA_SURFACE_REDUCED_TO_FOUR_PLUS_ONE_DELEGATIONS_"
            "AND_TWO_CASE_X_NO_COMMA_COMPOSITIONS"
        ),
        "schema19_compatible_total": upstream["compatible_total"],
        "schema19_extra_bearing_total": upstream["extra_bearing_total"],
        "schema19_extra_signature_count": len(observed),
        "extra_signatures": [sorted(x) for x in sorted(observed, key=lambda s: (len(s), sorted(s)))],
        "new_two_extra_signatures_closed_by_composition_rule": [
            sorted([u.ENGLISH_CAPITAL, NO_COMMA]),
            sorted([u.ENGLISH_LOWERCASE, NO_COMMA]),
        ],
        "remaining_new_constructor_shapes_beyond_active15_plus_one": 2,
        "complete_incompatibility_map_required": False,
        "independent_exact_checker_verification_required": True,
        "terminal_rows_used": False,
        "acceptance_credit": False,
    }


def run(args: Mapping[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = dict(args or {})
    if "contracts" not in args:
        return verify_scope_closure()
    return solve_contracts(list(args.get("contracts") or []))


if __name__ == "__main__":
    import json
    print(json.dumps(verify_scope_closure(), indent=2, sort_keys=True))
