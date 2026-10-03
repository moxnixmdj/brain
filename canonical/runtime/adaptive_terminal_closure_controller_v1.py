"""Adaptive zero-credit terminal closure controller.

Scheduling only. This module never creates evidence, executes gated reality,
promotes acceptance, or grants ownership. It converts the independently
verified live frontier into concurrent work lanes and optionally uses empirical
success/latency observations for resource ordering.

Unknown probabilities stay unknown. Structural leverage is always available;
Bayesian expected-value ordering is enabled only when explicit observations
are supplied.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ADAPTIVE_TERMINAL_CLOSURE_CONTROLLER_V1"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _accepted_unowned_families(matrix: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    rows = matrix.get("rows")
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        family = row.get("family")
        acceptance = str(row.get("postwave_opus55_acceptance_status") or "")
        ownership = str(row.get("postwave_ownership_credit") or "")
        status = str(row.get("status") or "")
        accepted = acceptance.startswith("PASS") or status == "VERIFIED_OWNED_EQUAL_OR_BETTER"
        owned = (
            ownership == "VERIFIED_OWNED_EQUAL_OR_BETTER"
            or status == "VERIFIED_OWNED_EQUAL_OR_BETTER"
        )
        if isinstance(family, str) and family and accepted and not owned:
            out.append(family)
    return sorted(set(out))


def _empirical_posterior(
    action_id: str,
    observations: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not observations or action_id not in observations:
        return {
            "probability_status": "UNKNOWN_NOT_INVENTED",
            "posterior_mean": None,
            "expected_latency_s": None,
        }
    raw = observations[action_id]
    if not isinstance(raw, Mapping):
        raise ValueError(f"EMPIRICAL_OBSERVATION_NOT_OBJECT:{action_id}")
    successes = raw.get("successes")
    failures = raw.get("failures")
    latency = raw.get("expected_latency_s")
    if (
        isinstance(successes, bool)
        or isinstance(failures, bool)
        or not isinstance(successes, int)
        or not isinstance(failures, int)
        or successes < 0
        or failures < 0
    ):
        raise ValueError(f"EMPIRICAL_COUNTS_INVALID:{action_id}")
    if (
        isinstance(latency, bool)
        or not isinstance(latency, (int, float))
        or not isfinite(float(latency))
        or float(latency) <= 0
    ):
        raise ValueError(f"EMPIRICAL_LATENCY_INVALID:{action_id}")
    # Beta(1,1) prior. This is scheduling only and never acceptance evidence.
    posterior = (successes + 1.0) / (successes + failures + 2.0)
    return {
        "probability_status": "EMPIRICAL_BETA_POSTERIOR_SCHEDULING_ONLY",
        "posterior_mean": posterior,
        "expected_latency_s": float(latency),
    }


def compile_controller(
    dominance: Mapping[str, Any],
    matched_scope: Mapping[str, Any],
    ownership_matrix: Mapping[str, Any],
    empirical_observations: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    live = dominance.get("live_world")
    if not isinstance(live, Mapping):
        return _fail("DOMINANCE_LIVE_WORLD_MISSING")

    if live.get("unresolved_predicates") != 27:
        errors.append("UNRESOLVED_PREDICATE_COUNT_NOT_27")
    if live.get("nondominated_certificate_count") != 16:
        errors.append("NONDOMINATED_CERTIFICATE_COUNT_NOT_16")
    if live.get("unique_zero_reality_requirements") != 19:
        errors.append("ZERO_REALITY_REQUIREMENT_COUNT_NOT_19")

    cert_ids = dominance.get("nondominated_certificate_ids")
    reqs = dominance.get("required_propositions")
    if not isinstance(cert_ids, list) or len(cert_ids) != 16:
        errors.append("NONDOMINATED_CERTIFICATE_IDS_INVALID")
        cert_ids = []
    if not isinstance(reqs, list) or len(reqs) != 19:
        errors.append("REQUIRED_PROPOSITIONS_INVALID")
        reqs = []

    expected = matched_scope.get("expected")
    targets = matched_scope.get("targets")
    implications = matched_scope.get("implications")
    if not isinstance(expected, Mapping):
        errors.append("MATCHED_EXPECTED_MISSING")
        expected = {}
    if expected.get("target_count") != 8:
        errors.append("MATCHED_TARGET_COUNT_NOT_8")
    if expected.get("primitive_residual_fact_count") != 16:
        errors.append("MATCHED_PRIMITIVE_FACT_COUNT_NOT_16")
    if expected.get("shared_residual_group_count") != 0:
        errors.append("MATCHED_SHARED_RESIDUAL_GROUP_COUNT_NOT_ZERO")
    if not isinstance(targets, list) or len(targets) != 8:
        errors.append("MATCHED_TARGETS_INVALID")
        targets = []
    if not isinstance(implications, list) or len(implications) != 8:
        errors.append("MATCHED_IMPLICATIONS_INVALID")
        implications = []

    if errors:
        return _fail(*errors)

    child_facts: list[dict[str, str]] = []
    for edge in implications:
        if not isinstance(edge, Mapping):
            return _fail("MATCHED_IMPLICATION_INVALID")
        target_list = edge.get("then")
        requirements = edge.get("if_all")
        if (
            not isinstance(target_list, list)
            or len(target_list) != 1
            or not isinstance(requirements, list)
            or len(requirements) != 2
        ):
            return _fail("MATCHED_CHILD_FACT_SHAPE_INVALID")
        target = str(target_list[0])
        for requirement in requirements:
            child_facts.append(
                {
                    "target_predicate": target,
                    "required_fact": str(requirement),
                }
            )

    highest = dominance.get("highest_direct_leverage")
    matched_certificate = (
        highest.get("certificate_id")
        if isinstance(highest, Mapping)
        else "MATCHED_SCOPE_BINDING_CERTIFICATE"
    )

    certificate_rows: list[dict[str, Any]] = []
    for cid in sorted(str(x) for x in cert_ids):
        posterior = _empirical_posterior(cid, empirical_observations)
        direct_coverage = 8 if cid == matched_certificate else 1
        if cid == "SHARED_PUBLIC_BENCHMARK_ABI_ROUTE_CERTIFICATE":
            direct_coverage = 3
        structural_value = float(direct_coverage)
        score = None
        if posterior["posterior_mean"] is not None:
            score = (
                posterior["posterior_mean"]
                * structural_value
                / posterior["expected_latency_s"]
            )
        certificate_rows.append(
            {
                "certificate_id": cid,
                "structural_direct_coverage": direct_coverage,
                "structural_value": structural_value,
                **posterior,
                "empirical_expected_value_per_second": score,
                "parallel": True,
            }
        )

    # Resource priority is not serialization. Unknown empirical probabilities
    # cannot be invented, so structural leverage provides the deterministic
    # fallback order.
    certificate_rows.sort(
        key=lambda row: (
            row["empirical_expected_value_per_second"] is None,
            -(row["empirical_expected_value_per_second"] or 0.0),
            -row["structural_value"],
            row["certificate_id"],
        )
    )

    ownership_ready = _accepted_unowned_families(ownership_matrix)

    return {
        "schema": SCHEMA,
        "status": "PASS__ADAPTIVE_PARALLEL_ZERO_REALITY_POLICY_COMPILED__ZERO_CREDIT",
        "live_world": {
            "unresolved_predicates": 27,
            "nondominated_certificates": 16,
            "unique_zero_reality_requirements": 19,
            "matched_targets": 8,
            "matched_primitive_child_facts": 16,
        },
        "parallel_lanes": {
            "matched_scope_child_fact_race": {
                "priority": "HIGHEST_STRUCTURAL_RESOURCE_PRIORITY",
                "serializes_other_lanes": False,
                "child_facts": child_facts,
                "stop_rule": "STOP_EACH_TARGET_AS_SOON_AS_ITS_TWO_REQUIRED_FACTS_ARE_INDEPENDENTLY_VERIFIED",
            },
            "nondominated_zero_reality_certificates": certificate_rows,
            "ownership_reconciliation": {
                "accepted_but_not_verified_owned_families": ownership_ready,
                "run_in_parallel_with_acceptance": True,
                "credit_rule": "NO_OWNERSHIP_CREDIT_WITHOUT_EXISTING_INDEPENDENT_OWNERSHIP_PROMOTION_AUTHORITY",
            },
        },
        "required_propositions": sorted(str(x) for x in reqs),
        "adaptive_policy": {
            "recompute_after_every_independently_verified_delta": True,
            "recompute_fixed_point": True,
            "recompute_information_dominance": True,
            "cancel_newly_dominated_branches": True,
            "probability_rule": "USE_EMPIRICAL_POSTERIORS_FOR_SCHEDULING_ONLY__NEVER_INVENT_MISSING_PROBABILITIES",
            "resource_rule": "PARALLELIZE_ALL_NONDOMINATED_ZERO_REALITY_BRANCHES__PRIORITIZE_RESOURCES_WITH_EMPIRICAL_VALUE_PER_SECOND_WHEN_AVAILABLE__OTHERWISE_STRUCTURAL_LEVERAGE",
            "fresh_reality_rule": "FORBIDDEN_UNTIL_CURRENT_AUTHORITY_EXPLICITLY_GRANTS_FRESH_REALITY_AFTER_ZERO_REALITY_FIXED_POINT",
        },
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
