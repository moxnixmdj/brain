"""Adaptive zero-reality terminal-closure scheduler V2.

Scheduling only. Derives the current 31 primitive zero-reality work units from
the independently verified post-dual 17-requirement frontier. It cannot grant
acceptance, ownership, execution, promotion, or fresh-reality authority.
"""
from __future__ import annotations

from collections import defaultdict
import json
import re
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_ADAPTIVE_TERMINAL_CLOSURE_CONTROLLER_V2"
MATCHED_PARENT_REQUIREMENTS = {
    "MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS",
    "MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS",
}
TOOL_DISCOVERY_TARGET = "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
DIRECT_REALITY_BLOCKED = [
    "FINANCE_UNCOVERED_SCOPE_AUDIT",
    "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT",
]


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


def _classify(req: str) -> str:
    if "::WITNESS_TARGET_" in req:
        return "MATCHED_TARGET_PROOF"
    if req.startswith("INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE"):
        return "TOOL_DISCOVERY_SCOPE_PROOF"
    if "STRONGER_PROOF" in req or "STRONGER_WITNESS" in req:
        return "STRONGER_PROOF"
    if req == "MACHINE_VERIFIED_TB4_ROUTE_UPPER_BOUND_GE_220":
        return "ATTAINABILITY"
    if req.startswith("TWELVE_LITERAL_INTERFACES_BOUND_"):
        return "COMPOSITION_RECEIPT_BINDING"
    if any(x in req for x in (
        "ROUTE_BOUND", "DATASET_SCORER_ROUTE", "COMPARABLE_SCORE_PRODUCING_ROUTE",
        "CANONICAL_ROUTE",
    )):
        return "PUBLIC_ROUTE_BINDING"
    return "ZERO_REALITY_PROOF"


def _source_hints(lane: str, *, tool_discovery: bool = False) -> list[str]:
    if tool_discovery:
        return [
            "MANDATORY_TOOL_DISCOVERY_V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE_RETRIEVAL_GATE",
            "NEW_CONTENT_ADDRESSED_SOURCE_EPOCH_ONLY",
            "DIVERSITY_PRESERVING_FEDERATION_WITH_ROUTER_RECEIPTS",
        ]
    if lane == "MATCHED_TARGET_PROOF":
        return [
            "CANONICAL_CONTENT_ADDRESSED_RECEIPTS",
            "GOOGLE_DRIVE_EVIDENCE_MIRROR_CANDIDATES",
            "FROZEN_TARGET_PROTOCOL_AND_METRIC_SOURCES",
            "OFFICIAL_PRIMARY_EVIDENCE",
        ]
    if lane == "PUBLIC_ROUTE_BINDING":
        return [
            "OFFICIAL_BENCHMARK_REPOSITORY_OR_SITE",
            "CANONICAL_GITHUB",
            "DATASET_REGISTRY",
            "PACKAGE_REGISTRY",
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
    if lane == "ATTAINABILITY":
        return [
            "CANONICAL_ROUTE_AND_CARRIER_RECEIPTS",
            "OFFICIAL_BENCHMARK_PROTOCOL",
            "CODE_HISTORY_RELEASES_ISSUES",
            "ALTERNATIVE_ADMISSIBLE_CARRIER_EVIDENCE",
        ]
    if lane == "COMPOSITION_RECEIPT_BINDING":
        return [
            "CANONICAL_ACCEPTANCE_SCOPED_RECEIPTS",
            "FROZEN_COMPONENT_INTERFACE_MANIFEST",
        ]
    return [
        "CANONICAL_CONTENT_ADDRESSED_RECEIPTS",
        "OFFICIAL_PRIMARY_EVIDENCE",
        "CODE_CONTENT_AND_HISTORY",
        "SCHOLARLY_PRIMARY",
        "OPEN_WEB_PRIMARY",
    ]


def _posterior(history: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(history, Mapping):
        return None
    s, f = history.get("verified_successes"), history.get("verified_failures")
    t = history.get("total_wall_seconds")
    if (
        isinstance(s, bool) or isinstance(f, bool)
        or not isinstance(s, int) or not isinstance(f, int)
        or s < 0 or f < 0 or s + f <= 0
    ):
        return None
    n = s + f
    a, b = 1 + s, 1 + f
    mean_seconds = (
        float(t) / n
        if isinstance(t, (int, float)) and not isinstance(t, bool) and t > 0
        else None
    )
    return {
        "model": "BETA_BINOMIAL_UNIFORM_PRIOR_WITH_EMPIRICAL_HISTORY",
        "alpha": a,
        "beta": b,
        "posterior_mean_verified_discharge_probability": a / (a + b),
        "observations": n,
        "mean_wall_seconds": mean_seconds,
        "promotion_use_forbidden": True,
    }


def evaluate(
    registry: Mapping[str, Any],
    evidence: Mapping[str, Any],
    certificate_frontier: Mapping[str, Any],
    zero_frontier: Mapping[str, Any],
    zero_frontier_verification: Mapping[str, Any],
    post_dual: Mapping[str, Any],
    post_dual_verification: Mapping[str, Any],
    matched: Mapping[str, Any],
    matched_verification: Mapping[str, Any],
    ownership: Mapping[str, Any],
    terminal_authority: Mapping[str, Any],
    scheduling_authority: Mapping[str, Any],
    *,
    attempt_history: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    predicates = registry.get("predicates")
    claims = evidence.get("claims")
    certs = certificate_frontier.get("certificates")
    if not isinstance(predicates, list):
        return _fail("PREDICATE_REGISTRY_NOT_LIST")
    if not isinstance(claims, list):
        return _fail("EVIDENCE_CLAIMS_NOT_LIST")
    if not isinstance(certs, list):
        return _fail("CERTIFICATE_FRONTIER_NOT_LIST")

    by_pred = {
        str(x["id"]): x
        for x in predicates
        if isinstance(x, Mapping) and isinstance(x.get("id"), str)
    }
    if len(by_pred) != len(predicates):
        errors.append("PREDICATE_REGISTRY_INVALID_OR_DUPLICATE")

    proved = {
        str(x.get("predicate_id"))
        for x in claims
        if isinstance(x, Mapping)
        and x.get("state") == "PROVED"
        and x.get("scope_complete") is True
        and isinstance(x.get("predicate_id"), str)
    }
    unresolved = [pid for pid in by_pred if pid not in proved]
    unresolved_set = set(unresolved)
    if (len(by_pred), len(proved), len(unresolved)) != (38, 11, 27):
        errors.append("LIVE_PREDICATE_COUNTS_NOT_38_11_27")

    truth = terminal_authority.get("truth") or {}
    acceptance = str(truth.get("opus55_acceptance") or "")
    if acceptance != "4/19_PASS__15/19_OPEN" or truth.get("achieved") is not False:
        errors.append("TERMINAL_AUTHORITY_ACCEPTANCE_DRIFT")

    sched_status = str(scheduling_authority.get("status") or "")
    if not sched_status.startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V12_CURRENT"):
        errors.append("SCHEDULING_AUTHORITY_NOT_CURRENT_V12_INDEPENDENT_PASS")
    if scheduling_authority.get("fresh_reality_authority") is not False:
        errors.append("SCHEDULING_AUTHORITY_FRESH_REALITY_LEAK")
    sched_live = scheduling_authority.get("live_world") or {}
    if (
        sched_live.get("proved_predicates"),
        sched_live.get("unresolved_predicates"),
        sched_live.get("active_zero_reality_requirements"),
        sched_live.get("active_nondominated_certificates"),
        sched_live.get("zero_reality_covered_predicates"),
        sched_live.get("primitive_zero_reality_work_units"),
    ) != (11, 27, 17, 14, 25, 31):
        errors.append("SCHEDULING_AUTHORITY_LIVE_WORLD_DRIFT")
    if sched_live.get("direct_reality_blocked_predicates") != DIRECT_REALITY_BLOCKED:
        errors.append("SCHEDULING_AUTHORITY_DIRECT_REALITY_SET_DRIFT")

    retrieval = scheduling_authority.get("mandatory_tool_discovery_retrieval") or {}
    if retrieval.get("authority") != "V4_OVER_VERIFIED_V3_OVER_VERIFIED_V2_BASE":
        errors.append("TOOL_DISCOVERY_NOT_V4_OVER_V3_V2")
    for key in ("mandatory", "diversity_preserving_federation_required",
                "one_router_attempt_receipt_per_selected_cell_required"):
        if retrieval.get(key) is not True:
            errors.append("TOOL_DISCOVERY_REQUIRED_TRUE:" + key)
    for key in ("direct_bypass_allowed", "stale_authority_allowed",
                "pre_v4_epoch_exhaustion_allowed",
                "consumed_source_epoch_replay_allowed",
                "no_result_means_nonexistence"):
        if retrieval.get(key) is not False:
            errors.append("TOOL_DISCOVERY_REQUIRED_FALSE:" + key)

    zstatus = str(zero_frontier_verification.get("status") or "")
    if not zstatus.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("ZERO_FRONTIER_NOT_INDEPENDENT_PASS")
    zlive = zero_frontier.get("live_world") or {}
    if (
        zlive.get("active_zero_reality_requirements"),
        zlive.get("active_nondominated_certificates"),
        zlive.get("proved_predicates"),
        zlive.get("unresolved_predicates"),
    ) != (17, 14, 11, 27):
        errors.append("ZERO_FRONTIER_COUNTS_DRIFT")

    pstatus = str(post_dual_verification.get("status") or "")
    pv = post_dual_verification.get("verified") or {}
    if not pstatus.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("POST_DUAL_NOT_INDEPENDENT_PASS")
    if (
        pv.get("current_zero_reality_requirements"),
        pv.get("current_nondominated_zero_reality_certificates"),
        pv.get("zero_reality_covered_predicates"),
        pv.get("primitive_zero_reality_work_units"),
        pv.get("matched_priority_child_facts"),
    ) != (17, 14, 25, 31, 16):
        errors.append("POST_DUAL_VERIFIED_COUNTS_DRIFT")
    if pv.get("direct_reality_blocked_predicates") != DIRECT_REALITY_BLOCKED:
        errors.append("POST_DUAL_DIRECT_REALITY_SET_DRIFT")
    if pv.get("current_global_fresh_reality_authority") is not False:
        errors.append("POST_DUAL_FRESH_REALITY_LEAK")

    active_requirements = zero_frontier.get("active_required_propositions")
    active_cert_ids = zero_frontier.get("active_nondominated_certificate_ids")
    if not isinstance(active_requirements, list) or len(active_requirements) != 17:
        errors.append("ACTIVE_REQUIREMENT_SET_INVALID")
        active_requirements = []
    if not isinstance(active_cert_ids, list) or len(active_cert_ids) != 14:
        errors.append("ACTIVE_CERTIFICATE_SET_INVALID")
        active_cert_ids = []

    req_targets: dict[str, set[str]] = defaultdict(set)
    req_certs: dict[str, set[str]] = defaultdict(set)
    active_cert_set = set(active_cert_ids)
    for cert in certs:
        if not isinstance(cert, Mapping) or cert.get("id") not in active_cert_set:
            continue
        targets = [
            str(pid) for pid in (cert.get("target_predicates") or [])
            if str(pid) in unresolved_set
        ]
        for req in cert.get("requires") or []:
            if isinstance(req, str):
                req_targets[req].update(targets)
                req_certs[req].add(str(cert.get("id")))

    if set(active_requirements) - set(req_targets):
        errors.append("ACTIVE_REQUIREMENT_WITHOUT_LIVE_CERTIFICATE")

    mstatus = str(matched_verification.get("status") or "")
    mr = matched_verification.get("result") or {}
    if not mstatus.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("MATCHED_RESIDUAL_NOT_INDEPENDENT_PASS")
    targets = matched.get("targets")
    implications = matched.get("implications")
    if not isinstance(targets, list) or not isinstance(implications, list):
        errors.append("MATCHED_RESIDUAL_SHAPE_INVALID")
        targets, implications = [], []
    if (len(targets), len(implications), mr.get("primitive_residual_fact_count"),
        mr.get("shared_residual_group_count")) != (8, 8, 16, 0):
        errors.append("MATCHED_RESIDUAL_COUNTS_DRIFT")

    matched_children: list[tuple[str, str]] = []
    for edge in implications:
        if not isinstance(edge, Mapping) or edge.get("verified") is not True or edge.get("independent") is not True:
            errors.append("MATCHED_EDGE_NOT_INDEPENDENT")
            continue
        then = edge.get("then")
        reqs = edge.get("if_all")
        if not isinstance(then, list) or len(then) != 1 or then[0] not in unresolved_set:
            errors.append("MATCHED_EDGE_TARGET_INVALID")
            continue
        target = str(then[0])
        if not isinstance(reqs, list) or len(reqs) != 2:
            errors.append("MATCHED_EDGE_REQUIREMENTS_INVALID:" + target)
            continue
        for req in reqs:
            if not isinstance(req, str) or not req.startswith(target + "::WITNESS_TARGET_"):
                errors.append("MATCHED_CHILD_NOT_TARGET_SPECIFIC:" + target)
            else:
                matched_children.append((req, target))
    if len(matched_children) != 16 or len({x[0] for x in matched_children}) != 16:
        errors.append("MATCHED_CHILD_SET_NOT_16_UNIQUE")

    direct_requirements = sorted(set(active_requirements) - MATCHED_PARENT_REQUIREMENTS)
    if len(direct_requirements) != 15:
        errors.append("DIRECT_ZERO_REALITY_REQUIREMENTS_NOT_15")

    history = attempt_history if isinstance(attempt_history, Mapping) else {}
    family_open_counts: dict[str, int] = defaultdict(int)
    for pid in unresolved:
        family_open_counts[str(by_pred[pid].get("family") or "UNKNOWN")] += 1

    work_units: list[dict[str, Any]] = []
    for req, target in sorted(matched_children):
        family = str(by_pred[target].get("family") or "UNKNOWN")
        work_units.append({
            "work_unit_id": req,
            "lane": "MATCHED_TARGET_PROOF",
            "requirement": req,
            "target_predicates": [target],
            "target_families": [family],
            "certificate_ids": ["MATCHED_TARGET_CERTIFICATE::" + target],
            "priority_tier": 0,
            "first_resource_priority": True,
            "parallelizable": True,
            "source_hints": _source_hints("MATCHED_TARGET_PROOF"),
            "empirical_posterior": _posterior(history.get(req)),
            "requires_fixed_point_recompute_on_verified_delta": True,
            "fresh_reality_authority": False,
            "promotion_authority": False,
        })

    for req in direct_requirements:
        target_ids = sorted(req_targets.get(req, set()))
        families = sorted({
            str(by_pred[x].get("family") or "UNKNOWN") for x in target_ids
        })
        lane = _classify(req)
        td = TOOL_DISCOVERY_TARGET in target_ids
        work_units.append({
            "work_unit_id": req,
            "lane": lane,
            "requirement": req,
            "target_predicates": target_ids,
            "target_families": families,
            "certificate_ids": sorted(req_certs.get(req, set())),
            "priority_tier": 1,
            "first_resource_priority": False,
            "parallelizable": True,
            "source_hints": _source_hints(lane, tool_discovery=td),
            "mandatory_tool_discovery_v4_gate": td,
            "empirical_posterior": _posterior(history.get(req)),
            "requires_fixed_point_recompute_on_verified_delta": True,
            "fresh_reality_authority": False,
            "promotion_authority": False,
        })

    if len(work_units) != 31:
        errors.append("PRIMITIVE_WORK_UNIT_COUNT_NOT_31")
    if len([x for x in work_units if x["first_resource_priority"]]) != 16:
        errors.append("FIRST_RESOURCE_PRIORITY_COUNT_NOT_16")

    td_rows = [
        x for x in work_units if TOOL_DISCOVERY_TARGET in x.get("target_predicates", [])
    ]
    if len(td_rows) != 1 or td_rows[0].get("mandatory_tool_discovery_v4_gate") is not True:
        errors.append("TOOL_DISCOVERY_V4_WORK_UNIT_INVALID")

    ownership_rows = ownership.get("rows")
    if not isinstance(ownership_rows, list):
        errors.append("OWNERSHIP_ROWS_NOT_LIST")
        ownership_rows = []
    ownership_reconcile = []
    for row in ownership_rows:
        if not isinstance(row, Mapping):
            continue
        acc = str(row.get("postwave_opus55_acceptance_status") or "")
        accepted = acc.startswith("PASS") or row.get("status") == "VERIFIED_OWNED_EQUAL_OR_BETTER"
        owned = row.get("status") == "VERIFIED_OWNED_EQUAL_OR_BETTER"
        if accepted and not owned:
            ownership_reconcile.append({
                "family": str(row.get("family")),
                "current_status": str(row.get("status")),
                "parallelizable": True,
                "promotion_authority": False,
            })
    if {x["family"] for x in ownership_reconcile} != {
        "SUBAGENT_DELEGATION_AND_COORDINATION",
        "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
    }:
        errors.append("OWNERSHIP_RECONCILIATION_SET_DRIFT")

    empirical_count = sum(
        1 for x in work_units if x.get("empirical_posterior") is not None
    )
    ok = not errors
    if not ok:
        return _fail(*errors)

    return {
        "schema": SCHEMA,
        "status": "PASS__CURRENT_V12_V4_POST_DUAL_ADAPTIVE_ZERO_REALITY_SCHEDULER__ZERO_CREDIT",
        "pass": True,
        "live_world": {
            "proved_predicates": 11,
            "unresolved_predicates": 27,
            "opus55_acceptance": acceptance,
            "nondominated_certificates": 14,
            "verified_zero_reality_requirements": 17,
            "zero_reality_covered_predicates": 25,
            "direct_reality_blocked_predicates": DIRECT_REALITY_BLOCKED,
            "matched_live_targets": 8,
            "matched_primitive_child_facts": 16,
            "matched_shared_residual_groups": 0,
        },
        "action_refinement": {
            "coarse_zero_reality_requirements": 17,
            "matched_parent_requirements_replaced_by_verified_children": 2,
            "matched_child_work_units": 16,
            "direct_nonmatched_work_units": 15,
            "primitive_acceptance_work_units": 31,
        },
        "acceptance_work_units": work_units,
        "first_resource_priority_work_unit_ids": [
            x["work_unit_id"] for x in work_units if x["first_resource_priority"]
        ],
        "direct_reality_blocked_work_units": [
            {
                "predicate_id": pid,
                "globally_authorized": False,
                "reason": "ZERO_REALITY_FIXED_POINT_REQUIRED_FIRST",
            }
            for pid in DIRECT_REALITY_BLOCKED
        ],
        "ownership_reconciliation_work_units": ownership_reconcile,
        "probability_policy": {
            "unknown_success_probability_may_be_invented": False,
            "empirically_scored_work_unit_count": empirical_count,
            "posterior_model_when_history_exists": "Beta(1+s,1+f)",
            "posterior_may_grant_acceptance_or_promotion": False,
        },
        "execution_policy": {
            "all_zero_reality_work_parallelizable": True,
            "matched_children_get_first_resource_priority_without_serializing_siblings": True,
            "ownership_reconciliation_runs_in_parallel": True,
            "fixed_point_after_every_independently_verified_delta": True,
            "recompute_frontier_after_every_verified_delta": True,
            "cancel_branch_when_newly_dominated": True,
            "fresh_reality_before_zero_reality_fixed_point": False,
            "tool_discovery_v4_over_v3_v2_gate_mandatory": True,
        },
        "hard_rules": [
            "SCHEDULING_ONLY_ZERO_CREDIT",
            "NO_INVENTED_SUCCESS_PROBABILITY_OR_PROOF_COST",
            "NO_MATCHED_PARENT_FLAG_SUBSTITUTION_FOR_TARGET_SPECIFIC_CHILD_FACTS",
            "NO_CROSS_TARGET_MATCHED_SCOPE_INHERITANCE",
            "NO_REPEAT_OF_CONSUMED_TOOL_DISCOVERY_SOURCE_EPOCH",
            "NO_RESULT_IS_NOT_NONEXISTENCE",
            "NO_FRESH_REALITY_UNTIL_CURRENT_ZERO_REALITY_FRONTIER_REACHES_VERIFIED_FIXED_POINT",
            "DIRECT_FINANCE_AND_UNKNOWN_DOMAIN_REALITY_REMAINS_GLOBALLY_BLOCKED",
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
        load("canonical/governance/CURRENT_27_ZERO_REALITY_FRONTIER_V2.json"),
        load("canonical/verification/CURRENT_27_ZERO_REALITY_FRONTIER_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
        load("canonical/governance/POST_DUAL_JUDGMENT_ZERO_REALITY_FRONTIER_V1.json"),
        load("canonical/verification/POST_DUAL_JUDGMENT_ZERO_REALITY_FRONTIER_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"),
        load("canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"),
        load("canonical/verification/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json"),
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
