#!/usr/bin/env python3
"""Adaptive terminal-closure scheduler for the current V13 / Retrieval V5 world.

Scheduling only. This module cannot grant acceptance, family, ownership,
execution, promotion, or fresh-reality authority.

The controller derives the executable zero-reality work units from independently
verified authority. Unknown success probabilities are never invented. Optional
empirical attempt history may affect scheduling order only.
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ADAPTIVE_TERMINAL_CLOSURE_CONTROLLER_V1"

MATCHED_PARENT_REQUIREMENTS = {
    "MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS",
    "MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS",
}
DISCHARGED_SOURCE_REQUIREMENTS = {
    "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_FINANCE_JUDGMENT_SOURCE_GATE_PASS",
    "BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_UNKNOWN_DOMAIN_JUDGMENT_SOURCE_GATE_PASS",
}
DIRECT_REALITY_BLOCKED = {
    "FINANCE_UNCOVERED_SCOPE_AUDIT",
    "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
}
TOOL_DISCOVERY_TARGET = "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
TB4_REQUIREMENT = "MACHINE_VERIFIED_TB4_ROUTE_UPPER_BOUND_GE_220"


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
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "incremental_spend_usd": 0,
        "new_reality_units_consumed": 0,
    }


def _empirical_posterior(history: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(history, Mapping):
        return None
    s = history.get("verified_successes")
    f = history.get("verified_failures")
    total = history.get("total_wall_seconds")
    if (
        isinstance(s, bool)
        or isinstance(f, bool)
        or not isinstance(s, int)
        or not isinstance(f, int)
        or s < 0
        or f < 0
        or s + f <= 0
    ):
        return None
    n = s + f
    alpha = 1 + s
    beta = 1 + f
    mean_wall = None
    if isinstance(total, (int, float)) and not isinstance(total, bool) and total > 0:
        mean_wall = float(total) / n
    return {
        "model": "BETA_BINOMIAL_UNIFORM_PRIOR_WITH_EMPIRICAL_HISTORY",
        "alpha": alpha,
        "beta": beta,
        "posterior_mean_verified_discharge_probability": alpha / (alpha + beta),
        "observations": n,
        "mean_wall_seconds": mean_wall,
        "promotion_use_forbidden": True,
    }


def _classify_requirement(req: str, targets: set[str]) -> str:
    if req == TB4_REQUIREMENT:
        return "ATTAINABILITY_SEARCH_ONLY"
    if TOOL_DISCOVERY_TARGET in targets:
        return "TOOL_DISCOVERY_SCOPE_PROOF"
    if "STRONGER_PROOF" in req or "STRONGER_WITNESS" in req:
        return "STRONGER_PROOF"
    if "ROUTE_BOUND" in req or "CANONICAL_ROUTE" in req or "DATASET_SCORER_ROUTE" in req:
        return "PUBLIC_ROUTE_BINDING"
    if "COMPARABLE_SCORE_PRODUCING_ROUTE" in req:
        return "PUBLIC_ROUTE_BINDING"
    if "INTERFACES_BOUND_TO_INDEPENDENT" in req:
        return "COMPOSITION_RECEIPT_BINDING"
    return "ZERO_REALITY_PROOF"


def _source_hints(lane: str, tool_discovery: bool) -> list[str]:
    if tool_discovery:
        return [
            "MANDATORY_TOOL_DISCOVERY_V5_OVER_VERIFIED_V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_RETRIEVAL_GATE",
            "DIVERSITY_PRESERVING_14_SOURCE_FEDERATION",
            "ONE_ROUTER_ATTEMPT_RECEIPT_PER_SELECTED_CELL",
            "NO_CONSUMED_SOURCE_EPOCH_REPLAY",
        ]
    if lane == "PUBLIC_ROUTE_BINDING":
        return [
            "OFFICIAL_BENCHMARK_REPOSITORY_OR_SITE",
            "CANONICAL_GITHUB",
            "DATASET_AND_PACKAGE_REGISTRIES",
            "ARCHIVED_RELEASE_HISTORY_IF_NEEDED",
        ]
    if lane == "STRONGER_PROOF":
        return [
            "CANONICAL_CONTENT_ADDRESSED_RECEIPTS",
            "CODE_CONTENT_AND_HISTORY",
            "SOFTWARE_ARCHIVE",
            "SCHOLARLY_PRIMARY",
            "OPEN_WEB_PRIMARY",
            "SOCIAL_TECHNICAL_DISCUSSION_CANDIDATE_ONLY",
        ]
    if lane == "ATTAINABILITY_SEARCH_ONLY":
        return [
            "CANONICAL_ROUTE_AND_CARRIER_RECEIPTS",
            "OFFICIAL_BENCHMARK_PROTOCOL",
            "ALTERNATIVE_ADMISSIBLE_CARRIER_OR_PROTOCOL_EQUIVALENCE_EVIDENCE",
        ]
    return [
        "CANONICAL_CONTENT_ADDRESSED_RECEIPTS",
        "GOOGLE_DRIVE_EVIDENCE_MIRROR_CANDIDATES",
        "OFFICIAL_PRIMARY_EVIDENCE",
        "CODE_CONTENT_AND_HISTORY",
    ]


def _matched_children(matched: Mapping[str, Any]) -> list[tuple[str, str]]:
    targets = matched.get("targets")
    edges = matched.get("implications")
    if not isinstance(targets, list) or not isinstance(edges, list):
        return []
    live = {x for x in targets if isinstance(x, str)}
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for edge in edges:
        if (
            not isinstance(edge, Mapping)
            or edge.get("verified") is not True
            or edge.get("independent") is not True
        ):
            continue
        then = edge.get("then")
        reqs = edge.get("if_all")
        if not isinstance(then, list) or len(then) != 1 or then[0] not in live:
            continue
        if not isinstance(reqs, list):
            continue
        target = str(then[0])
        for req in reqs:
            if not isinstance(req, str) or req in seen:
                continue
            if not req.startswith(target + "::WITNESS_TARGET_"):
                continue
            seen.add(req)
            out.append((req, target))
    return sorted(out)


def evaluate(
    registry: Mapping[str, Any],
    evidence: Mapping[str, Any],
    frontier: Mapping[str, Any],
    prior_dominance: Mapping[str, Any],
    matched_residual: Mapping[str, Any],
    matched_verification: Mapping[str, Any],
    post_dual_verification: Mapping[str, Any],
    ownership_matrix: Mapping[str, Any],
    terminal_authority: Mapping[str, Any],
    scheduling_authority: Mapping[str, Any],
    *,
    attempt_history: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    predicates = registry.get("predicates")
    claims = evidence.get("claims")
    certificates = frontier.get("certificates")
    if not isinstance(predicates, list) or not isinstance(claims, list):
        return _fail("REGISTRY_OR_EVIDENCE_INVALID")
    if not isinstance(certificates, list):
        return _fail("CERTIFICATE_FRONTIER_INVALID")

    by_predicate: dict[str, Mapping[str, Any]] = {}
    for row in predicates:
        if isinstance(row, Mapping) and isinstance(row.get("id"), str):
            by_predicate[str(row["id"])] = row
    proved = {
        str(row["predicate_id"])
        for row in claims
        if isinstance(row, Mapping)
        and isinstance(row.get("predicate_id"), str)
        and row.get("state") == "PROVED"
        and row.get("scope_complete") is True
    }
    unresolved = set(by_predicate) - proved
    if (len(by_predicate), len(proved), len(unresolved)) != (38, 11, 27):
        errors.append("LIVE_PREDICATE_COUNTS_NOT_38_11_27")

    truth = terminal_authority.get("truth") or {}
    if truth.get("opus55_acceptance") != "4/19_PASS__15/19_OPEN":
        errors.append("ACCEPTANCE_NOT_CURRENT_4_OF_19")
    if truth.get("achieved") is not False:
        errors.append("TERMINAL_MUST_REMAIN_FALSE")

    sched_status = str(scheduling_authority.get("status") or "")
    if not sched_status.startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V13_CURRENT"):
        errors.append("SCHEDULING_AUTHORITY_NOT_CURRENT_V13_INDEPENDENT_PASS")
    live = scheduling_authority.get("live_world") or {}
    expected_live = (
        live.get("registry_predicates"),
        live.get("proved_predicates"),
        live.get("unresolved_predicates"),
        live.get("active_zero_reality_requirements"),
        live.get("active_nondominated_certificates"),
        live.get("zero_reality_covered_predicates"),
        live.get("primitive_zero_reality_work_units"),
        live.get("matched_priority_child_facts"),
    )
    if expected_live != (38, 11, 27, 17, 14, 25, 31, 16):
        errors.append("SCHEDULING_V13_LIVE_WORLD_DRIFT")
    if set(live.get("direct_reality_blocked_predicates") or []) != DIRECT_REALITY_BLOCKED:
        errors.append("SCHEDULING_DIRECT_REALITY_BLOCKED_SET_DRIFT")
    if scheduling_authority.get("fresh_reality_authority") is not False:
        errors.append("SCHEDULING_FRESH_REALITY_LEAK")

    retrieval = scheduling_authority.get("mandatory_tool_discovery_retrieval") or {}
    if retrieval.get("authority") != "V5_OVER_VERIFIED_V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE":
        errors.append("TOOL_DISCOVERY_RETRIEVAL_NOT_V5")
    for key in (
        "mandatory",
        "strict_success_only_source_cell_consumption_required",
        "transient_failures_retryable_and_unconsumed",
        "all_selected_cells_required_before_epoch_consumption",
    ):
        if retrieval.get(key) is not True:
            errors.append("RETRIEVAL_REQUIRED_FLAG_FALSE:" + key)
    for key in (
        "partial_batch_epoch_consumption_allowed",
        "off_domain_result_may_satisfy_source_cell",
        "consumed_cell_replay_allowed",
        "empty_or_failed_attempt_proves_nonexistence",
    ):
        if retrieval.get(key) is not False:
            errors.append("RETRIEVAL_FAIL_CLOSED_FLAG_NOT_FALSE:" + key)

    post_status = str(post_dual_verification.get("status") or "")
    pv = post_dual_verification.get("verified") or {}
    if not post_status.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("POST_DUAL_FRONTIER_NOT_INDEPENDENT_PASS")
    expected_post = {
        "current_zero_reality_requirements": 17,
        "current_nondominated_zero_reality_certificates": 14,
        "zero_reality_covered_predicates": 25,
        "primitive_zero_reality_work_units": 31,
        "matched_priority_child_facts": 16,
    }
    for key, value in expected_post.items():
        if pv.get(key) != value:
            errors.append("POST_DUAL_VERIFIED_DRIFT:" + key)
    if set(pv.get("direct_reality_blocked_predicates") or []) != DIRECT_REALITY_BLOCKED:
        errors.append("POST_DUAL_DIRECT_REALITY_SET_DRIFT")
    if pv.get("current_global_fresh_reality_authority") is not False:
        errors.append("POST_DUAL_FRESH_REALITY_LEAK")

    mv = matched_verification.get("result") or {}
    if not str(matched_verification.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("MATCHED_RESIDUAL_NOT_INDEPENDENT_PASS")
    children = _matched_children(matched_residual)
    if (
        mv.get("target_count"),
        mv.get("primitive_residual_fact_count"),
        mv.get("shared_residual_group_count"),
    ) != (8, 16, 0):
        errors.append("MATCHED_VERIFIED_COUNTS_DRIFT")
    if len(children) != 16:
        errors.append("MATCHED_CHILD_COUNT_NOT_16")

    required = prior_dominance.get("required_propositions")
    nondominated = prior_dominance.get("nondominated_certificate_ids")
    if not isinstance(required, list) or len(set(required)) != 19:
        errors.append("PRIOR_REQUIREMENT_BASIS_NOT_19")
        required = []
    if not isinstance(nondominated, list) or len(set(nondominated)) != 16:
        errors.append("PRIOR_CERTIFICATE_BASIS_NOT_16")

    req_targets: dict[str, set[str]] = defaultdict(set)
    req_certificates: dict[str, set[str]] = defaultdict(set)
    for cert in certificates:
        if not isinstance(cert, Mapping):
            continue
        cid = cert.get("id")
        targets = {str(x) for x in (cert.get("target_predicates") or []) if x in unresolved}
        for req in cert.get("requires") or []:
            if isinstance(req, str):
                req_targets[req].update(targets)
                if isinstance(cid, str):
                    req_certificates[req].add(cid)

    active_direct = (
        set(str(x) for x in required)
        - MATCHED_PARENT_REQUIREMENTS
        - DISCHARGED_SOURCE_REQUIREMENTS
    )
    if len(active_direct) != 15:
        errors.append("ACTIVE_DIRECT_ZERO_REALITY_REQUIREMENTS_NOT_15")

    history = attempt_history if isinstance(attempt_history, Mapping) else {}
    work_units: list[dict[str, Any]] = []
    family_open: dict[str, int] = defaultdict(int)
    for pid in unresolved:
        family_open[str(by_predicate[pid].get("family") or "UNKNOWN")] += 1

    for req, target in children:
        family = str(by_predicate[target].get("family") or "UNKNOWN")
        work_units.append({
            "work_unit_id": req,
            "kind": "ZERO_REALITY_ACCEPTANCE_REQUIREMENT",
            "lane": "MATCHED_TARGET_PROOF",
            "requirement": req,
            "target_predicates": [target],
            "target_families": [family],
            "priority_tier": 0,
            "first_resource_priority": True,
            "parallelizable": True,
            "source_hints": [
                "CANONICAL_CONTENT_ADDRESSED_RECEIPTS",
                "GOOGLE_DRIVE_EVIDENCE_MIRROR_CANDIDATES",
                "FROZEN_TARGET_PROTOCOL_AND_METRIC_SOURCES",
                "OFFICIAL_PRIMARY_EVIDENCE",
            ],
            "empirical_posterior": _empirical_posterior(history.get(req)),
            "fresh_reality_authority": False,
            "promotion_authority": False,
        })

    for req in sorted(active_direct):
        targets = req_targets.get(req, set()) - DIRECT_REALITY_BLOCKED
        lane = _classify_requirement(req, targets)
        tool_discovery = TOOL_DISCOVERY_TARGET in targets
        mode = "ZERO_REALITY_DISCHARGE"
        if req == TB4_REQUIREMENT:
            mode = "ROUTE_SEARCH_ONLY__CURRENT_DIRECT_EXECUTION_FORBIDDEN"
        work_units.append({
            "work_unit_id": req,
            "kind": "ZERO_REALITY_ACCEPTANCE_REQUIREMENT",
            "lane": lane,
            "requirement": req,
            "target_predicates": sorted(targets),
            "target_families": sorted({
                str(by_predicate[p].get("family") or "UNKNOWN") for p in targets
            }),
            "certificate_ids": sorted(req_certificates.get(req, set())),
            "priority_tier": 1 if tool_discovery else 2,
            "first_resource_priority": False,
            "parallelizable": True,
            "execution_mode": mode,
            "source_hints": _source_hints(lane, tool_discovery),
            "mandatory_tool_discovery_v5_gate": tool_discovery,
            "empirical_posterior": _empirical_posterior(history.get(req)),
            "fresh_reality_authority": False,
            "promotion_authority": False,
        })

    target_union = {
        pid for row in work_units for pid in row.get("target_predicates", [])
    }
    if len(work_units) != 31:
        errors.append("PRIMITIVE_WORK_UNIT_COUNT_NOT_31")
    if len(target_union) != 25:
        errors.append("ZERO_REALITY_TARGET_UNION_NOT_25")
    if target_union & DIRECT_REALITY_BLOCKED:
        errors.append("DIRECT_REALITY_BLOCKED_PREDICATE_LEAKED_INTO_ZERO_REALITY_WORK")

    ownership_rows = ownership_matrix.get("rows")
    if not isinstance(ownership_rows, list):
        errors.append("OWNERSHIP_ROWS_INVALID")
        ownership_rows = []
    reconcile: list[dict[str, Any]] = []
    prework: list[dict[str, Any]] = []
    for row in ownership_rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("family"), str):
            continue
        family = str(row["family"])
        acceptance = str(row.get("postwave_opus55_acceptance_status") or "")
        owned = (
            row.get("status") == "VERIFIED_OWNED_EQUAL_OR_BETTER"
            or row.get("postwave_ownership_credit") == "VERIFIED_OWNED_EQUAL_OR_BETTER"
        )
        accepted = acceptance.startswith("PASS") or row.get("status") == "VERIFIED_OWNED_EQUAL_OR_BETTER"
        if accepted and not owned:
            reconcile.append({
                "work_unit_id": "OWNERSHIP_RECONCILE::" + family,
                "family": family,
                "parallelizable": True,
                "acceptance_already_closed": True,
                "promotion_authority": False,
            })
        elif not accepted and row.get("internalization_required") is True:
            prework.append({
                "work_unit_id": "OWNERSHIP_PREWORK::" + family,
                "family": family,
                "parallelizable": True,
                "acceptance_already_closed": False,
                "candidate_internalization_routes": row.get("candidate_internalization_routes") or [],
                "promotion_authority": False,
            })
    reconcile.sort(key=lambda x: x["family"])
    prework.sort(key=lambda x: x["family"])

    if errors:
        return _fail(*errors)

    empirical_count = sum(
        1 for row in work_units if row.get("empirical_posterior") is not None
    )
    return {
        "schema": SCHEMA,
        "status": "PASS__V13_V5_ADAPTIVE_ZERO_REALITY_AND_OWNERSHIP_FRONTIER_COMPILED__ZERO_CREDIT",
        "pass": True,
        "live_world": {
            "frozen_predicates": 38,
            "proved_predicates": 11,
            "unresolved_predicates": 27,
            "opus55_acceptance": "4/19_PASS__15/19_OPEN",
            "active_zero_reality_requirements": 17,
            "active_nondominated_certificates": 14,
            "zero_reality_covered_predicates": 25,
            "primitive_zero_reality_work_units": 31,
            "matched_live_targets": 8,
            "matched_primitive_child_facts": 16,
            "matched_shared_residual_groups": 0,
            "direct_reality_blocked_predicates": sorted(DIRECT_REALITY_BLOCKED),
        },
        "acceptance_work_units": sorted(
            work_units,
            key=lambda x: (
                int(x["priority_tier"]),
                -(x.get("empirical_posterior") or {}).get(
                    "posterior_mean_verified_discharge_probability", -1
                ),
                str(x["work_unit_id"]),
            ),
        ),
        "first_resource_priority_work_unit_ids": sorted(
            row["work_unit_id"] for row in work_units if row["first_resource_priority"]
        ),
        "ownership_reconciliation_work_units": reconcile,
        "ownership_prework_units": prework,
        "probability_policy": {
            "unknown_success_probability_may_be_invented": False,
            "empirically_scored_work_unit_count": empirical_count,
            "posterior_model_when_history_exists": "Beta(1+s,1+f)",
            "posterior_may_grant_acceptance_or_promotion": False,
        },
        "execution_policy": {
            "run_all_31_zero_reality_work_units_concurrently": True,
            "matched_16_child_facts_first_resource_priority_without_serializing_siblings": True,
            "ownership_reconciliation_runs_in_parallel": True,
            "fixed_point_after_every_independently_verified_delta": True,
            "recompute_frontier_after_every_verified_delta": True,
            "cancel_newly_dominated_branches": True,
            "fresh_reality_before_zero_reality_fixed_point": False,
            "tool_discovery_v5_gate_mandatory": True,
            "direct_reality_blocked_predicates_not_in_zero_reality_batch": True,
        },
        "hard_rules": [
            "SCHEDULING_ONLY_ZERO_CREDIT",
            "NO_INVENTED_SUCCESS_PROBABILITY_OR_PROOF_COST",
            "NO_MATCHED_PARENT_FLAG_SUBSTITUTION_FOR_TARGET_SPECIFIC_CHILD_FACTS",
            "NO_CROSS_TARGET_MATCHED_SCOPE_INHERITANCE",
            "NO_REPEAT_OF_CONSUMED_TOOL_DISCOVERY_SOURCE_EPOCH",
            "NO_RESULT_IS_NOT_NONEXISTENCE",
            "TB4_CURRENT_EXECUTION_ROUTE_REMAINS_FORBIDDEN_UNTIL_ATTAINABILITY_UPPER_BOUND_GE_220",
            "FINANCE_AND_UNKNOWN_DIRECT_PREDICATES_REQUIRE_SEPARATE_REALITY_AUTHORITY_AFTER_ZERO_REALITY_FIXED_POINT",
            "ACCEPTANCE_AND_OWNERSHIP_ACCOUNTING_REMAIN_SEPARATE",
        ],
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "ownership_credit_delta": 0,
        "incremental_spend_usd": 0,
        "new_reality_units_consumed": 0,
    }


def evaluate_repository(root: Path) -> dict[str, Any]:
    def load(rel: str) -> dict[str, Any]:
        value = json.loads((root / rel).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(rel + ":NOT_OBJECT")
        return value

    return evaluate(
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
        load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
        load("canonical/governance/CURRENT_27_INFORMATION_DOMINANCE_V1.json"),
        load("canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"),
        load("canonical/verification/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json"),
        load("canonical/verification/POST_DUAL_JUDGMENT_ZERO_REALITY_FRONTIER_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
        load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"),
        load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
        load("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"),
    )


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    out = evaluate_repository(root)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
