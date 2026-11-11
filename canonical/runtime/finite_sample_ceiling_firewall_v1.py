"""Fail-closed firewall for finite-sample -> absolute-ceiling acceptance claims.

A finite terminal sample can establish an empirical pass on that frozen sample. It
cannot establish a protocol-wide theoretical ceiling unless the source evidence
also proves one of the following:
  * the source case universe is exactly the complete target case universe;
  * an exhaustive finite superset contains the entire target universe; or
  * a universal/formally complete proof covers every admissible target input.

This compiler grants no acceptance, family, capability, execution, or promotion
credit. It exists to stop sample success from being silently upgraded into a
scope-complete absolute-dominance witness.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_FINITE_SAMPLE_CEILING_FIREWALL_V1"


def _fail(*errors: str, facts: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "facts": dict(facts or {}),
        "absolute_ceiling_established": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def evaluate(
    *,
    witness: Mapping[str, Any],
    relation: Mapping[str, Any],
    target_superportfolio: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    if witness.get("mode") != "ABSOLUTE_DOMINANCE":
        errors.append("WITNESS_NOT_ABSOLUTE_DOMINANCE")

    source_case_count = witness.get("source_case_count")
    if isinstance(source_case_count, bool) or not isinstance(source_case_count, int) or source_case_count <= 0:
        errors.append("FINITE_SOURCE_CASE_COUNT_REQUIRED")

    result = witness.get("result")
    if not isinstance(result, Mapping):
        errors.append("WITNESS_RESULT_MISSING")
    else:
        if result.get("direction") != "higher":
            errors.append("EXPECTED_HIGHER_IS_BETTER")
        if result.get("brain_lower_bound") != 1.0:
            errors.append("CLAIMED_BRAIN_CEILING_BOUND_MISSING")
        if result.get("theoretical_upper_bound") != 1.0:
            errors.append("THEORETICAL_UPPER_BOUND_MISSING")

    case_generation = target_superportfolio.get("case_generation")
    target_generated = isinstance(case_generation, Mapping) and case_generation.get("generated_now") is True
    target_exposed = isinstance(case_generation, Mapping) and case_generation.get("exposed_now") is True

    target_case_identity = relation.get("target_case_universe_identity")
    exact_target_universe = (
        isinstance(target_case_identity, Mapping)
        and target_case_identity.get("verified") is True
        and target_case_identity.get("independent") is True
        and target_case_identity.get("relation") == "EXACT"
        and target_case_identity.get("complete_target_case_set") is True
        and isinstance(target_case_identity.get("receipt"), str)
        and bool(target_case_identity.get("receipt"))
    )

    exhaustive = relation.get("exhaustive_finite_scope")
    exhaustive_superset = (
        isinstance(exhaustive, Mapping)
        and exhaustive.get("verified") is True
        and exhaustive.get("independent") is True
        and exhaustive.get("exhaustive") is True
        and exhaustive.get("target_subset_proved") is True
        and isinstance(exhaustive.get("receipt"), str)
        and bool(exhaustive.get("receipt"))
    )

    universal = relation.get("universal_scope_proof")
    universal_complete = (
        isinstance(universal, Mapping)
        and universal.get("verified") is True
        and universal.get("independent") is True
        and universal.get("all_admissible_target_inputs_proved") is True
        and universal.get("formal_completeness") is True
        and isinstance(universal.get("receipt"), str)
        and bool(universal.get("receipt"))
    )

    admissible_basis = exact_target_universe or exhaustive_superset or universal_complete

    facts = {
        "source_case_count": source_case_count,
        "target_case_generation_generated_now": target_generated,
        "target_case_generation_exposed_now": target_exposed,
        "exact_complete_target_case_universe_verified": exact_target_universe,
        "exhaustive_finite_superset_verified": exhaustive_superset,
        "universal_scope_complete_verified": universal_complete,
    }

    # A claim that a finite sample is the complete target universe cannot be
    # accepted while the canonical target superportfolio explicitly says its
    # target cases have not even been generated.
    if exact_target_universe and not target_generated:
        errors.append("EXACT_TARGET_UNIVERSE_CONTRADICTS_UNGENERATED_TARGET_PORTFOLIO")

    if relation.get("relation") in {"PROVEN_STRONGER", "PROVEN_STRONGER_CANDIDATE"} and not admissible_basis:
        errors.append("SCOPE_RELATION_LACKS_COMPLETE_COVERAGE_PROOF")

    if not admissible_basis:
        errors.append("FINITE_SAMPLE_CANNOT_ESTABLISH_PROTOCOL_WIDE_CEILING")

    if errors:
        return _fail(*errors, facts=facts)

    return {
        "schema": SCHEMA,
        "status": "PASS__ABSOLUTE_CEILING_HAS_SCOPE_COMPLETE_BASIS__ZERO_CREDIT",
        "pass": True,
        "errors": [],
        "facts": facts,
        "absolute_ceiling_established": True,
        "basis": (
            "EXACT_COMPLETE_TARGET_CASE_UNIVERSE"
            if exact_target_universe
            else "EXHAUSTIVE_FINITE_SUPERSET"
            if exhaustive_superset
            else "UNIVERSAL_FORMAL_SCOPE_PROOF"
        ),
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
