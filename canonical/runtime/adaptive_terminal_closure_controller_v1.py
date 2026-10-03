#!/usr/bin/env python3
"""Adaptive zero-credit terminal-closure controller.

This controller schedules already-declared Project Brain proof obligations. It
never grants acceptance, ownership, execution, promotion, or fresh-reality
authority.

Design:
- preserve the independently verified 19-requirement zero-reality frontier;
- expand the matched-scope parent certificate into its exact 16 verified
  target-specific child facts for execution planning;
- run all independent zero-reality branches concurrently;
- give matched-scope child facts first resource priority without serializing
  other work;
- run ownership reconciliation for already-accepted but not-yet-owned
  families in parallel;
- never invent probabilities. Bayesian/posterior ranking is enabled only when
  empirical counts and an explicit prior are supplied by a caller;
- recompute after every independently verified delta and stop newly dominated
  work immediately.
"""
from __future__ import annotations

import json
from math import isfinite
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ADAPTIVE_TERMINAL_CLOSURE_CONTROLLER_V1"

MATCHED_PARENT_REQUIREMENTS = {
    "MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS",
    "MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS",
}
TB4_REQUIREMENT = "MACHINE_VERIFIED_TB4_ROUTE_UPPER_BOUND_GE_220"
TOOL_DISCOVERY_REQUIREMENT = (
    "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_"
    "OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL"
)


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
        "family_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _posterior(
    empirical: Mapping[str, Any] | None,
    item_id: str,
    *,
    structural_value: float,
) -> dict[str, Any]:
    """Return a probability record without manufacturing a prior.

    A posterior is computed only when the caller supplied all four values:
    prior_alpha, prior_beta, successes, failures. Latency is optional and is
    used only to compute expected utility per second.
    """
    row = empirical.get(item_id) if isinstance(empirical, Mapping) else None
    if not isinstance(row, Mapping):
        return {
            "status": "UNKNOWN_NOT_INVENTED",
            "posterior_mean": None,
            "mean_latency_seconds": None,
            "expected_structural_utility_per_second": None,
        }

    needed = ("prior_alpha", "prior_beta", "successes", "failures")
    if any(k not in row for k in needed):
        return {
            "status": "UNKNOWN_INCOMPLETE_EMPIRICAL_INPUT",
            "posterior_mean": None,
            "mean_latency_seconds": None,
            "expected_structural_utility_per_second": None,
        }

    try:
        prior_a = float(row["prior_alpha"])
        prior_b = float(row["prior_beta"])
        successes = int(row["successes"])
        failures = int(row["failures"])
    except (TypeError, ValueError):
        return {
            "status": "INVALID_EMPIRICAL_INPUT",
            "posterior_mean": None,
            "mean_latency_seconds": None,
            "expected_structural_utility_per_second": None,
        }

    if (
        not isfinite(prior_a)
        or not isfinite(prior_b)
        or prior_a <= 0
        or prior_b <= 0
        or successes < 0
        or failures < 0
    ):
        return {
            "status": "INVALID_EMPIRICAL_INPUT",
            "posterior_mean": None,
            "mean_latency_seconds": None,
            "expected_structural_utility_per_second": None,
        }

    post_a = prior_a + successes
    post_b = prior_b + failures
    mean = post_a / (post_a + post_b)

    latency = row.get("mean_latency_seconds")
    latency_value = None
    utility = None
    if latency is not None:
        try:
            latency_value = float(latency)
        except (TypeError, ValueError):
            latency_value = None
        if latency_value is not None and (
            not isfinite(latency_value) or latency_value <= 0
        ):
            latency_value = None
        if latency_value is not None:
            utility = mean * float(structural_value) / latency_value

    return {
        "status": "EMPIRICAL_BETA_POSTERIOR",
        "prior_alpha": prior_a,
        "prior_beta": prior_b,
        "successes": successes,
        "failures": failures,
        "posterior_alpha": post_a,
        "posterior_beta": post_b,
        "posterior_mean": mean,
        "mean_latency_seconds": latency_value,
        "expected_structural_utility_per_second": utility,
    }


def _live_predicate_states(evidence: Mapping[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in evidence.get("claims") or []:
        if not isinstance(row, Mapping):
            continue
        pid = row.get("predicate_id")
        state = row.get("state")
        if isinstance(pid, str) and isinstance(state, str):
            out[pid] = state
    return out


def _matched_child_facts(matched: Mapping[str, Any]) -> list[dict[str, Any]]:
    targets = matched.get("targets")
    implications = matched.get("implications")
    if not isinstance(targets, list) or not isinstance(implications, list):
        return []

    target_set = {x for x in targets if isinstance(x, str)}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for edge in implications:
        if not isinstance(edge, Mapping):
            continue
        then = edge.get("then")
        if_all = edge.get("if_all")
        if (
            edge.get("verified") is not True
            or edge.get("independent") is not True
            or not isinstance(then, list)
            or len(then) != 1
            or then[0] not in target_set
            or not isinstance(if_all, list)
        ):
            continue
        target = then[0]
        for fact in if_all:
            if not isinstance(fact, str) or not fact or fact in seen:
                continue
            seen.add(fact)
            rows.append(
                {
                    "fact_id": fact,
                    "target_predicate": target,
                    "source_edge_id": edge.get("edge_id"),
                    "resource_priority": "FIRST",
                    "execution_mode": "ZERO_REALITY_TARGET_SPECIFIC_PROOF_OR_BINDING",
                }
            )
    rows.sort(key=lambda x: (x["target_predicate"], x["fact_id"]))
    return rows


def evaluate(
    dominance: Mapping[str, Any],
    matched: Mapping[str, Any],
    matrix: Mapping[str, Any],
    frontier: Mapping[str, Any],
    evidence: Mapping[str, Any],
    empirical_stats: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    live = dominance.get("live_world")
    if not isinstance(live, Mapping):
        return _fail("DOMINANCE_LIVE_WORLD_MISSING")

    unresolved_count = live.get("unresolved_predicates")
    cert_count = live.get("nondominated_certificate_count")
    requirement_count = live.get("unique_zero_reality_requirements")
    requirements = dominance.get("required_propositions")
    nondominated_ids = dominance.get("nondominated_certificate_ids")

    if not isinstance(requirements, list) or any(
        not isinstance(x, str) or not x for x in requirements
    ):
        errors.append("REQUIREMENTS_INVALID")
        requirements = []
    if len(set(requirements)) != len(requirements):
        errors.append("REQUIREMENTS_DUPLICATE")
    if not isinstance(nondominated_ids, list) or any(
        not isinstance(x, str) or not x for x in nondominated_ids
    ):
        errors.append("NONDOMINATED_CERTIFICATE_IDS_INVALID")
        nondominated_ids = []

    if requirement_count != len(requirements):
        errors.append("DOMINANCE_REQUIREMENT_COUNT_MISMATCH")
    if cert_count != len(nondominated_ids):
        errors.append("DOMINANCE_CERTIFICATE_COUNT_MISMATCH")

    states = _live_predicate_states(evidence)
    terminal_states = {"PROVED", "REFUTED"}

    cert_rows = {
        row.get("id"): row
        for row in (frontier.get("certificates") or [])
        if isinstance(row, Mapping) and isinstance(row.get("id"), str)
    }

    req_targets: dict[str, set[str]] = {req: set() for req in requirements}
    req_certificates: dict[str, set[str]] = {req: set() for req in requirements}
    for cid in nondominated_ids:
        row = cert_rows.get(cid)
        if not isinstance(row, Mapping):
            errors.append("NONDOMINATED_CERTIFICATE_MISSING_FROM_FRONTIER:" + cid)
            continue
        targets = [
            x
            for x in (row.get("target_predicates") or [])
            if isinstance(x, str) and states.get(x) not in terminal_states
        ]
        for req in row.get("requires") or []:
            if req not in req_targets:
                continue
            req_targets[req].update(targets)
            req_certificates[req].add(cid)

    matched_children = _matched_child_facts(matched)
    expected = matched.get("expected") if isinstance(matched.get("expected"), Mapping) else {}
    expected_child_count = expected.get("primitive_residual_fact_count")
    if expected_child_count != len(matched_children):
        errors.append("MATCHED_CHILD_FACT_COUNT_MISMATCH")

    matched_parent_requirements = sorted(
        req for req in requirements if req in MATCHED_PARENT_REQUIREMENTS
    )
    if set(matched_parent_requirements) != MATCHED_PARENT_REQUIREMENTS:
        errors.append("MATCHED_PARENT_REQUIREMENTS_NOT_EXACT")

    other_requirements = sorted(
        req for req in requirements if req not in MATCHED_PARENT_REQUIREMENTS
    )

    work_items: list[dict[str, Any]] = []
    denom = float(unresolved_count) if isinstance(unresolved_count, int) and unresolved_count > 0 else 1.0
    for req in other_requirements:
        targets = sorted(req_targets.get(req, set()))
        structural_value = len(targets) / denom
        mode = "ZERO_REALITY_DISCHARGE"
        hard_rule = None
        if req == TB4_REQUIREMENT:
            mode = "ROUTE_SEARCH_ONLY"
            hard_rule = "CURRENT_TB4_EXECUTION_ROUTE_ATTAINABILITY_180_LT_220__NO_BENCHMARK_EXECUTION"
        elif req == TOOL_DISCOVERY_REQUIREMENT:
            mode = "NEW_SOURCE_EPOCH_OR_SCOPE_PROOF_ONLY"
            hard_rule = "CONSUMED_TOOL_DISCOVERY_GITHUB_SOURCE_EPOCH_REPLAY_FORBIDDEN"

        probability = _posterior(empirical_stats, req, structural_value=structural_value)
        work_items.append(
            {
                "requirement_id": req,
                "target_predicates": targets,
                "certificate_ids": sorted(req_certificates.get(req, set())),
                "structural_coverage_upper_bound_count": len(targets),
                "structural_coverage_upper_bound_fraction": structural_value,
                "resource_priority": "PARALLEL",
                "execution_mode": mode,
                "hard_rule": hard_rule,
                "probability": probability,
            }
        )

    def _rank_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
        p = row.get("probability") if isinstance(row.get("probability"), Mapping) else {}
        utility = p.get("expected_structural_utility_per_second")
        known = isinstance(utility, (int, float))
        return (
            0 if known else 1,
            -float(utility) if known else 0.0,
            -int(row.get("structural_coverage_upper_bound_count") or 0),
            str(row.get("requirement_id") or ""),
        )

    work_items.sort(key=_rank_key)

    accepted_unowned: list[dict[str, Any]] = []
    for row in matrix.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        family = row.get("family")
        acceptance = str(row.get("postwave_opus55_acceptance_status") or "")
        ownership = str(row.get("postwave_ownership_credit") or "")
        status = str(row.get("status") or "")
        accepted = acceptance.startswith("PASS")
        owned = (
            ownership == "VERIFIED_OWNED_EQUAL_OR_BETTER"
            or status == "VERIFIED_OWNED_EQUAL_OR_BETTER"
        )
        if isinstance(family, str) and accepted and not owned:
            accepted_unowned.append(
                {
                    "family": family,
                    "acceptance_status": acceptance,
                    "ownership_status": ownership or status,
                    "execution_mode": "OWNERSHIP_RECONCILIATION_ONLY",
                    "resource_priority": "PARALLEL_WITH_ACCEPTANCE_FRONTIER",
                }
            )
    accepted_unowned.sort(key=lambda x: x["family"])

    if errors:
        return _fail(*errors)

    return {
        "schema": SCHEMA,
        "status": "PASS__ADAPTIVE_ZERO_REALITY_AND_OWNERSHIP_FRONTIER_COMPILED__ZERO_CREDIT",
        "pass": True,
        "live_world": {
            "unresolved_predicates": unresolved_count,
            "nondominated_certificates": cert_count,
            "unique_zero_reality_requirements": requirement_count,
            "matched_live_targets": len(matched.get("targets") or []),
            "matched_primitive_child_facts": len(matched_children),
            "other_zero_reality_requirements": len(other_requirements),
            "accepted_but_not_verified_owned_families": len(accepted_unowned),
        },
        "launch_policy": {
            "all_independent_zero_reality_branches_parallel": True,
            "matched_child_facts_first_resource_priority": True,
            "other_zero_reality_requirements_not_serialized": True,
            "ownership_reconciliation_parallel_with_acceptance": True,
            "fixed_point_after_every_independently_verified_delta": True,
            "cancel_branch_when_newly_dominated": True,
            "fresh_reality_before_zero_reality_fixed_point": False,
        },
        "matched_parent_requirements": matched_parent_requirements,
        "matched_child_fact_batch": matched_children,
        "other_zero_reality_batch": work_items,
        "ownership_reconciliation_batch": accepted_unowned,
        "probability_policy": {
            "invented_priors_forbidden": True,
            "posterior_allowed_only_with_explicit_prior_and_empirical_counts": True,
            "unknown_probability_state": "UNKNOWN_NOT_INVENTED",
            "probability_is_scheduling_only_never_proof": True,
        },
        "source_discovery_policy": {
            "single_best_search_engine_claim": False,
            "route_by_evidence_surface": True,
            "exact_residual_drives_queries": True,
            "unicode_native_language_queries_preserved": True,
            "descriptionless_code_observables_allowed": True,
            "consumed_source_epoch_replay_forbidden": True,
            "new_orthogonal_source_epoch_is_material_wake": True,
            "no_result_is_not_nonexistence": True,
        },
        "replan_triggers": [
            "ANY_INDEPENDENTLY_VERIFIED_PREDICATE_DELTA",
            "ANY_INDEPENDENTLY_VERIFIED_SCOPE_OR_SEMANTIC_BINDING_DELTA",
            "ANY_NEW_MATERIAL_SOURCE_EPOCH",
            "ANY_OWNERSHIP_STATUS_DELTA",
            "ANY_ROUTE_ATTAINABILITY_DELTA",
            "ANY_CERTIFICATE_DOMINANCE_DELTA",
        ],
        "hard_rules": [
            "SCHEDULING_OUTPUT_GRANTS_ZERO_ACCEPTANCE_OR_OWNERSHIP_CREDIT",
            "MATCHED_CHILD_FACTS_ARE_TARGET_SPECIFIC__NO_CROSS_TARGET_INHERITANCE",
            "TB4_CURRENT_EXECUTION_ROUTE_REMAINS_DOMINATED_UNTIL_UPPER_BOUND_GE_220",
            "TOOL_DISCOVERY_CONSUMED_GITHUB_SOURCE_EPOCH_MUST_NOT_BE_REPLAYED",
            "PROBABILITY_NEVER_SUBSTITUTES_FOR_FROZEN_ACCEPTANCE_EVIDENCE",
            "OWNERSHIP_CANNOT_BE_CLAIMED_FROM_ACCEPTANCE_ALONE",
        ],
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "ownership_credit_delta": 0,
        "family_credit_delta": 0,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]

    def load(rel: str) -> dict[str, Any]:
        return json.loads((root / rel).read_text(encoding="utf-8"))

    empirical_path = root / "canonical/governance/ADAPTIVE_TERMINAL_EMPIRICAL_STATS_V1.json"
    empirical = (
        json.loads(empirical_path.read_text(encoding="utf-8"))
        if empirical_path.exists()
        else None
    )
    out = evaluate(
        load("canonical/governance/CURRENT_27_INFORMATION_DOMINANCE_V1.json"),
        load("canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"),
        load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"),
        load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
        empirical,
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
