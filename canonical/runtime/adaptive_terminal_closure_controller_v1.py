"""Adaptive zero-reality terminal-closure scheduler.

Scheduling only. This module cannot grant acceptance, capability, family,
ownership, execution, promotion, or fresh-reality authority.

Unknown proof difficulty and success probability are never invented. Optional
empirical attempt history can produce a Beta-Binomial scheduling posterior, but
that posterior is scheduling evidence only.
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
TOOL_DISCOVERY_TARGET = "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"


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


def _classify_requirement(req: str) -> str:
    if "::WITNESS_TARGET_" in req:
        return "MATCHED_TARGET_PROOF"
    if req == (
        "INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_"
        "SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL"
    ):
        return "TOOL_DISCOVERY_SCOPE_PROOF"
    if "STRONGER_PROOF" in req or "STRONGER_WITNESS" in req:
        return "STRONGER_PROOF"
    if req.startswith("BRAIN_OWNED_OR_PERMISSIVELY_INTERNALIZED_"):
        return "INTERNALIZATION"
    if req == "MACHINE_VERIFIED_TB4_ROUTE_UPPER_BOUND_GE_220":
        return "ATTAINABILITY"
    if req == (
        "TWELVE_LITERAL_INTERFACES_BOUND_TO_INDEPENDENT_CONTAMINATION_CLEAN_"
        "ACCEPTANCE_SCOPED_RECEIPTS"
    ):
        return "COMPOSITION_RECEIPT_BINDING"
    if any(
        token in req
        for token in (
            "ROUTE_BOUND",
            "DATASET_SCORER_ROUTE",
            "COMPARABLE_SCORE_PRODUCING_ROUTE",
            "CANONICAL_ROUTE",
        )
    ):
        return "PUBLIC_ROUTE_BINDING"
    return "ZERO_REALITY_PROOF"


def _source_hints(lane: str, *, tool_discovery: bool = False) -> list[str]:
    if tool_discovery:
        return [
            "MANDATORY_TOOL_DISCOVERY_V2_RETRIEVAL_GATE",
            "NEW_ORTHOGONAL_SOURCE_EPOCH_ONLY",
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
    if lane == "INTERNALIZATION":
        return [
            "CANONICAL_CAPABILITY_REGISTRY",
            "PERMISSIVELY_LICENSED_CODE_AND_PACKAGE_REGISTRIES",
            "SOFTWARE_ARCHIVE",
            "SCHOLARLY_METHOD_SOURCES",
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


def _empirical_posterior(history: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(history, Mapping):
        return None
    successes = history.get("verified_successes")
    failures = history.get("verified_failures")
    total_seconds = history.get("total_wall_seconds")
    if (
        isinstance(successes, bool)
        or isinstance(failures, bool)
        or not isinstance(successes, int)
        or not isinstance(failures, int)
        or successes < 0
        or failures < 0
        or successes + failures <= 0
    ):
        return None
    observations = successes + failures
    alpha = 1 + successes
    beta = 1 + failures
    mean_seconds = None
    if (
        isinstance(total_seconds, (int, float))
        and not isinstance(total_seconds, bool)
        and total_seconds > 0
    ):
        mean_seconds = float(total_seconds) / observations
    return {
        "model": "BETA_BINOMIAL_UNIFORM_PRIOR_WITH_EMPIRICAL_HISTORY",
        "alpha": alpha,
        "beta": beta,
        "posterior_mean_verified_discharge_probability": alpha / (alpha + beta),
        "observations": observations,
        "mean_wall_seconds": mean_seconds,
        "promotion_use_forbidden": True,
    }


def evaluate(
    registry: Mapping[str, Any],
    evidence: Mapping[str, Any],
    frontier: Mapping[str, Any],
    dominance: Mapping[str, Any],
    dominance_verification: Mapping[str, Any],
    matched_residual: Mapping[str, Any],
    matched_verification: Mapping[str, Any],
    ownership_matrix: Mapping[str, Any],
    authority: Mapping[str, Any],
    *,
    attempt_history: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    predicates = registry.get("predicates")
    claims = evidence.get("claims")
    certificates = frontier.get("certificates")
    if not isinstance(predicates, list):
        return _fail("PREDICATE_REGISTRY_NOT_LIST")
    if not isinstance(claims, list):
        return _fail("EVIDENCE_CLAIMS_NOT_LIST")
    if not isinstance(certificates, list):
        return _fail("FRONTIER_CERTIFICATES_NOT_LIST")

    by_predicate: dict[str, Mapping[str, Any]] = {}
    for row in predicates:
        if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
            errors.append("INVALID_PREDICATE_ROW")
            continue
        pid = str(row["id"])
        if pid in by_predicate:
            errors.append("DUPLICATE_PREDICATE:" + pid)
        by_predicate[pid] = row

    states: dict[str, str] = {}
    proved: set[str] = set()
    for row in claims:
        if not isinstance(row, Mapping):
            errors.append("INVALID_EVIDENCE_ROW")
            continue
        pid = row.get("predicate_id")
        state = row.get("state")
        if not isinstance(pid, str) or pid not in by_predicate:
            errors.append("UNKNOWN_EVIDENCE_PREDICATE:" + str(pid))
            continue
        if pid in states:
            errors.append("DUPLICATE_EVIDENCE_PREDICATE:" + pid)
            continue
        states[pid] = str(state)
        if state == "PROVED":
            proved.add(pid)

    unresolved = [
        pid
        for pid in by_predicate
        if pid not in proved and states.get(pid) != "REFUTED"
    ]
    unresolved_set = set(unresolved)
    if len(by_predicate) != 38:
        errors.append(f"REGISTRY_COUNT_NOT_38:{len(by_predicate)}")
    if len(proved) != 11:
        errors.append(f"PROVED_COUNT_NOT_11:{len(proved)}")
    if len(unresolved) != 27:
        errors.append(f"UNRESOLVED_COUNT_NOT_27:{len(unresolved)}")

    truth = authority.get("truth")
    if not isinstance(truth, Mapping):
        errors.append("AUTHORITY_TRUTH_NOT_OBJECT")
        truth = {}
    if truth.get("opus55_acceptance") != "4/19_PASS__15/19_OPEN":
        errors.append("AUTHORITY_ACCEPTANCE_NOT_4_OF_19")
    if truth.get("achieved") is not False:
        errors.append("AUTHORITY_TERMINAL_MUST_BE_FALSE")

    dv_status = str(dominance_verification.get("status") or "")
    verified_dom = dominance_verification.get("verified")
    if not dv_status.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS") or not isinstance(
        verified_dom, Mapping
    ):
        errors.append("DOMINANCE_NOT_INDEPENDENTLY_VERIFIED")
        verified_dom = {}
    if (
        verified_dom.get("frozen_predicates"),
        verified_dom.get("proved_predicates"),
        verified_dom.get("unresolved_predicates"),
        verified_dom.get("nondominated_certificate_count"),
        verified_dom.get("unique_zero_reality_requirements"),
    ) != (38, 11, 27, 16, 19):
        errors.append("DOMINANCE_VERIFIED_COUNTS_MISMATCH")

    live_world = dominance.get("live_world")
    if not isinstance(live_world, Mapping):
        errors.append("DOMINANCE_LIVE_WORLD_MISSING")
        live_world = {}
    if (
        live_world.get("frozen_predicates"),
        live_world.get("proved_predicates"),
        live_world.get("unresolved_predicates"),
        live_world.get("nondominated_certificate_count"),
        live_world.get("unique_zero_reality_requirements"),
    ) != (38, 11, 27, 16, 19):
        errors.append("DOMINANCE_CANDIDATE_COUNTS_MISMATCH")

    nondominated = dominance.get("nondominated_certificate_ids")
    required = dominance.get("required_propositions")
    if (
        not isinstance(nondominated, list)
        or len(nondominated) != 16
        or len(set(nondominated)) != 16
    ):
        errors.append("NONDOMINATED_CERTIFICATE_SET_INVALID")
        nondominated = []
    if (
        not isinstance(required, list)
        or len(required) != 19
        or len(set(required)) != 19
    ):
        errors.append("ZERO_REALITY_REQUIREMENT_SET_INVALID")
        required = []

    mv_status = str(matched_verification.get("status") or "")
    mv_result = matched_verification.get("result")
    if not mv_status.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS") or not isinstance(
        mv_result, Mapping
    ):
        errors.append("MATCHED_RESIDUAL_NOT_INDEPENDENTLY_VERIFIED")
        mv_result = {}
    if (
        mv_result.get("target_count"),
        mv_result.get("primitive_residual_fact_count"),
        mv_result.get("shared_residual_group_count"),
    ) != (8, 16, 0):
        errors.append("MATCHED_RESIDUAL_VERIFIED_COUNTS_MISMATCH")

    matched_targets = matched_residual.get("targets")
    implications = matched_residual.get("implications")
    if (
        not isinstance(matched_targets, list)
        or len(matched_targets) != 8
        or len(set(matched_targets)) != 8
    ):
        errors.append("MATCHED_TARGET_SET_INVALID")
    if not isinstance(implications, list) or len(implications) != 8:
        errors.append("MATCHED_IMPLICATION_SET_INVALID")
        implications = []

    matched_children: list[tuple[str, str]] = []
    for edge in implications:
        if (
            not isinstance(edge, Mapping)
            or edge.get("verified") is not True
            or edge.get("independent") is not True
        ):
            errors.append("MATCHED_EDGE_NOT_VERIFIED")
            continue
        targets = edge.get("then")
        reqs = edge.get("if_all")
        if (
            not isinstance(targets, list)
            or len(targets) != 1
            or targets[0] not in unresolved_set
        ):
            errors.append("MATCHED_EDGE_TARGET_INVALID")
            continue
        target = str(targets[0])
        if not isinstance(reqs, list) or len(reqs) != 2:
            errors.append("MATCHED_EDGE_REQUIREMENTS_INVALID:" + target)
            continue
        for req in reqs:
            if not isinstance(req, str) or not req.startswith(
                target + "::WITNESS_TARGET_"
            ):
                errors.append("MATCHED_CHILD_REQUIREMENT_NOT_TARGET_SPECIFIC:" + target)
                continue
            matched_children.append((req, target))
    if len(matched_children) != 16 or len({r for r, _ in matched_children}) != 16:
        errors.append("MATCHED_CHILD_FACT_COUNT_NOT_16")

    req_targets: dict[str, set[str]] = defaultdict(set)
    req_certificates: dict[str, set[str]] = defaultdict(set)
    nondominated_set = {str(x) for x in nondominated}
    for cert in certificates:
        if not isinstance(cert, Mapping):
            continue
        cid = cert.get("id")
        if not isinstance(cid, str) or cid not in nondominated_set:
            continue
        targets = cert.get("target_predicates")
        reqs = cert.get("requires")
        if not isinstance(targets, list) or not isinstance(reqs, list):
            continue
        live_targets = {str(pid) for pid in targets if pid in unresolved_set}
        for req in reqs:
            if isinstance(req, str):
                req_targets[req].update(live_targets)
                req_certificates[req].add(cid)

    required_set = {str(x) for x in required}
    missing = sorted(required_set - set(req_targets))
    if missing:
        errors.append("REQUIREMENTS_WITHOUT_LIVE_CERTIFICATE:" + ",".join(missing))
    if not MATCHED_PARENT_REQUIREMENTS.issubset(required_set):
        errors.append("MATCHED_PARENT_REQUIREMENTS_NOT_BOTH_PRESENT")
    direct_requirements = sorted(required_set - MATCHED_PARENT_REQUIREMENTS)

    family_open_counts: dict[str, int] = defaultdict(int)
    for pid in unresolved:
        family_open_counts[str(by_predicate[pid].get("family") or "UNKNOWN")] += 1

    history = attempt_history if isinstance(attempt_history, Mapping) else {}
    work_units: list[dict[str, Any]] = []

    for req, target in sorted(matched_children):
        family = str(by_predicate[target].get("family") or "UNKNOWN")
        work_units.append(
            {
                "work_unit_id": req,
                "kind": "ZERO_REALITY_ACCEPTANCE_REQUIREMENT",
                "lane": "MATCHED_TARGET_PROOF",
                "requirement": req,
                "target_predicates": [target],
                "target_families": [family],
                "certificate_ids": ["MATCHED_TARGET_CERTIFICATE::" + target],
                "structural_target_fraction": 1 / 27,
                "family_open_predicate_counts": {
                    family: family_open_counts[family]
                },
                "priority_tier": 0,
                "first_resource_priority": True,
                "parallelizable": True,
                "source_hints": _source_hints("MATCHED_TARGET_PROOF"),
                "empirical_posterior": _empirical_posterior(history.get(req)),
                "requires_fixed_point_recompute_on_verified_delta": True,
                "fresh_reality_authority": False,
                "promotion_authority": False,
            }
        )

    for req in direct_requirements:
        targets = sorted(req_targets.get(req, set()))
        families = sorted(
            {str(by_predicate[p].get("family") or "UNKNOWN") for p in targets}
        )
        lane = _classify_requirement(req)
        tool_discovery = TOOL_DISCOVERY_TARGET in targets
        work_units.append(
            {
                "work_unit_id": req,
                "kind": "ZERO_REALITY_ACCEPTANCE_REQUIREMENT",
                "lane": lane,
                "requirement": req,
                "target_predicates": targets,
                "target_families": families,
                "certificate_ids": sorted(req_certificates.get(req, set())),
                "structural_target_fraction": len(targets) / 27 if targets else 0,
                "family_open_predicate_counts": {
                    f: family_open_counts[f] for f in families
                },
                "priority_tier": 1 if tool_discovery else 2,
                "first_resource_priority": False,
                "parallelizable": True,
                "source_hints": _source_hints(
                    lane, tool_discovery=tool_discovery
                ),
                "mandatory_tool_discovery_v2_gate": tool_discovery,
                "empirical_posterior": _empirical_posterior(history.get(req)),
                "requires_fixed_point_recompute_on_verified_delta": True,
                "fresh_reality_authority": False,
                "promotion_authority": False,
            }
        )

    rows = ownership_matrix.get("rows")
    if not isinstance(rows, list):
        errors.append("OWNERSHIP_MATRIX_ROWS_NOT_LIST")
        rows = []

    ownership_reconcile: list[dict[str, Any]] = []
    ownership_prework: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        family = row.get("family")
        if not isinstance(family, str):
            continue
        acceptance = str(row.get("postwave_opus55_acceptance_status") or "")
        owned = (
            row.get("status") == "VERIFIED_OWNED_EQUAL_OR_BETTER"
            or row.get("postwave_ownership_credit")
            == "VERIFIED_OWNED_EQUAL_OR_BETTER"
        )
        accepted = acceptance.startswith("PASS") or (
            row.get("status") == "VERIFIED_OWNED_EQUAL_OR_BETTER"
        )
        if accepted and not owned:
            ownership_reconcile.append(
                {
                    "work_unit_id": "OWNERSHIP_RECONCILE::" + family,
                    "kind": "OWNERSHIP_RECONCILIATION",
                    "family": family,
                    "priority_tier": 1,
                    "parallelizable": True,
                    "acceptance_already_closed": True,
                    "ownership_credit_current": row.get("postwave_ownership_credit"),
                    "next_required_action": row.get("next_required_action"),
                    "fresh_reality_authority": False,
                    "promotion_authority": False,
                }
            )
        elif not accepted and row.get("internalization_required") is True:
            ownership_prework.append(
                {
                    "work_unit_id": "OWNERSHIP_PREWORK::" + family,
                    "kind": "OWNERSHIP_PREWORK",
                    "family": family,
                    "priority_tier": 3,
                    "parallelizable": True,
                    "acceptance_already_closed": False,
                    "candidate_internalization_routes": row.get(
                        "candidate_internalization_routes"
                    )
                    or [],
                    "campaign_next_action": row.get("campaign_next_action"),
                    "fresh_reality_authority": False,
                    "promotion_authority": False,
                }
            )

    def sort_key(unit: Mapping[str, Any]) -> tuple[Any, ...]:
        posterior = unit.get("empirical_posterior")
        posterior_score = -1.0
        latency_score = float("inf")
        if isinstance(posterior, Mapping):
            probability = posterior.get(
                "posterior_mean_verified_discharge_probability"
            )
            latency = posterior.get("mean_wall_seconds")
            if isinstance(probability, (int, float)):
                posterior_score = float(probability)
            if isinstance(latency, (int, float)) and latency > 0:
                latency_score = float(latency)
        return (
            int(unit.get("priority_tier", 9)),
            -posterior_score,
            latency_score,
            -float(unit.get("structural_target_fraction", 0.0)),
            str(unit.get("work_unit_id")),
        )

    work_units.sort(key=sort_key)
    ownership_reconcile.sort(key=lambda x: str(x["family"]))
    ownership_prework.sort(key=lambda x: str(x["family"]))

    if errors:
        return _fail(*errors)

    empirical_count = sum(
        1 for row in work_units if row.get("empirical_posterior") is not None
    )
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__ADAPTIVE_PARALLEL_ZERO_REALITY_AND_OWNERSHIP_FRONTIER_"
            "COMPILED__ZERO_CREDIT"
        ),
        "pass": True,
        "live_world": {
            "frozen_predicates": 38,
            "proved_predicates": 11,
            "unresolved_predicates": 27,
            "acceptance": "4/19_PASS__15/19_OPEN",
            "nondominated_certificates": 16,
            "verified_zero_reality_requirements": 19,
            "matched_live_targets": 8,
            "matched_primitive_child_facts": 16,
            "matched_shared_residual_groups": 0,
        },
        "action_refinement": {
            "coarse_zero_reality_requirements": 19,
            "matched_parent_requirements_replaced_by_verified_children": 2,
            "matched_child_work_units": 16,
            "direct_nonmatched_work_units": len(direct_requirements),
            "primitive_acceptance_work_units": len(work_units),
            "rule": (
                "THE_19_REQUIREMENTS_ARE_PROOF_OBLIGATIONS_NOT_19_SERIAL_ACTIONS"
            ),
        },
        "acceptance_work_units": work_units,
        "first_resource_priority_work_unit_ids": [
            row["work_unit_id"]
            for row in work_units
            if row["first_resource_priority"]
        ],
        "ownership_reconciliation_work_units": ownership_reconcile,
        "ownership_prework_units": ownership_prework,
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
            "recompute_information_dominance_after_every_acceptance_delta": True,
            "cancel_branch_when_newly_dominated": True,
            "fresh_reality_before_zero_reality_fixed_point": False,
            "tool_discovery_v2_gate_mandatory": True,
        },
        "hard_rules": [
            "SCHEDULING_ONLY_ZERO_CREDIT",
            "NO_INVENTED_SUCCESS_PROBABILITY_OR_PROOF_COST",
            "NO_MATCHED_PARENT_FLAG_SUBSTITUTION_FOR_16_TARGET_SPECIFIC_CHILD_FACTS",
            "NO_CROSS_TARGET_MATCHED_SCOPE_INHERITANCE",
            "NO_REPEAT_OF_CONSUMED_TOOL_DISCOVERY_SOURCE_EPOCH",
            "NO_RESULT_IS_NOT_NONEXISTENCE",
            "NO_FRESH_REALITY_UNTIL_CURRENT_ZERO_REALITY_FRONTIER_REACHES_VERIFIED_FIXED_POINT",
            "ACCEPTANCE_AND_OWNERSHIP_ACCOUNTING_REMAIN_SEPARATE",
            "OWNERSHIP_MAY_PREPARE_IN_PARALLEL_BUT_CANNOT_SELF_PROMOTE",
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
        load(
            "canonical/verification/"
            "CURRENT_27_INFORMATION_DOMINANCE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
        ),
        load("canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"),
        load(
            "canonical/verification/"
            "MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_EXECUTION_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json"
        ),
        load(
            "canonical/capabilities/opus55/"
            "OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json"
        ),
        load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
    )


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    out = evaluate_repository(root)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
