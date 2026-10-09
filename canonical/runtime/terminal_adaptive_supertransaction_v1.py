"""Current adaptive terminal-closure supertransaction candidate.

This compiler binds only already-canonical, content-addressed facts. It compresses
the live 26-predicate terminal residual into the smallest justified causal phase
structure without granting execution or acceptance credit.

The key distinction is between *actions* and *causal barriers*: all independent
zero-reality work is parallelized inside phase Z. Fresh reality remains forbidden
until the verified zero-reality fixed point. If anything survives, all authorized
minimum-reality work is parallelized inside phase R. Acceptance backpropagation
and finality are automatic after every receipt, so "finality" is not a third
manual phase.

This file is scheduling evidence only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_TERMINAL_ADAPTIVE_SUPERTRANSACTION_V1"

PATHS = {
    "root_state": "canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json",
    "root2": "canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V5.json",
    "root3": "canonical/governance/ROOT3_MINIMUM_ACTION_CUT_V2.json",
    "retrieval": "canonical/governance/GLOBAL_RETRIEVAL_CURRENT_AUTHORITY_V1.json",
    "tb4_attainability": "canonical/verification/TB4_ATTAINABILITY_CUT_VERDICT_20261002_V1.json",
    "finance_direct": "canonical/governance/FINANCE_INDEX_DIRECT_THRESHOLD_ACTIVATION_V1.json",
    "finance_agent_zero_cost": "canonical/governance/FINANCE_AGENT_V2_ZERO_COST_TOOL_BOUNDARY_20261004_V1.json",
    "osworld": "canonical/governance/OSWORLD_OPUS55_METHODOLOGY_PUBLIC_CORROBORATION_20261004_V1.json",
}

PINNED = {
    PATHS["root_state"]: "d2e1827a40e1e547f17b61913f7c66f1ebce634c",
    PATHS["root2"]: "e948022f0a4e8d91b949a5155d850d56aa137c87",
    PATHS["root3"]: "4d8ce78ebe312100bbfc524062199961c0c6479d",
    PATHS["retrieval"]: "55b1d411561f720fcd9d66c127cecd63ef0b5f5e",
    PATHS["tb4_attainability"]: "a7b0c692251b92819007c581b9fe84b75960cab7",
    PATHS["finance_direct"]: "9b9d4a41d19a5e58e8967027e1d1837790287dc2",
    PATHS["finance_agent_zero_cost"]: "032caa374280983945321f0a5706c0c665c097a6",
    PATHS["osworld"]: "259a6fa8f7daf744e6e06902d43925419cdd4d9b",
}


def _blob(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value


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
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
    }


def evaluate() -> dict[str, Any]:
    drift = {
        rel: {"expected": expected, "actual": _blob(rel)}
        for rel, expected in PINNED.items()
        if _blob(rel) != expected
    }
    if drift:
        return {**_fail("PINNED_SOURCE_BLOB_DRIFT"), "drift": drift}

    root = _load(PATHS["root_state"])
    r2 = _load(PATHS["root2"])
    r3 = _load(PATHS["root3"])
    retrieval = _load(PATHS["retrieval"])
    tb4 = _load(PATHS["tb4_attainability"])
    finance_direct = _load(PATHS["finance_direct"])
    finance_agent = _load(PATHS["finance_agent_zero_cost"])
    osworld = _load(PATHS["osworld"])

    errors: list[str] = []

    a = root.get("current_acceptance") or {}
    expected_acceptance = {
        "accepted_families": 5,
        "open_families": 14,
        "proved_atomic": 12,
        "unresolved_atomic": 26,
        "total_families": 19,
        "total_atomic": 38,
        "terminal": False,
    }
    if any(a.get(k) != v for k, v in expected_acceptance.items()):
        errors.append("CURRENT_ACCEPTANCE_COUNTS_DRIFT")

    part = root.get("current_residual_root_partition") or {}
    if (
        part.get("root1_positive_gap_count"),
        part.get("root2_only_count"),
        part.get("root3_only_count"),
        part.get("root2_and_root3_count"),
        part.get("unresolved_total"),
    ) != (0, 16, 7, 3, 26):
        errors.append("ROOT_PARTITION_DRIFT")

    r2_ctrl = ((root.get("roots") or {}).get("root_2_measurement_or_comparator") or {}).get(
        "active_closure_controller"
    ) or {}
    if r2_ctrl.get("effective_scheduling_authority") is not True:
        errors.append("ROOT2_V5_NOT_EFFECTIVE_SCHEDULING_AUTHORITY")
    if r2_ctrl.get("fresh_reality_authority") is not False:
        errors.append("ROOT2_FRESH_REALITY_OVERCLAIM")

    r3_state = root.get("root3_current_execution_state") or {}
    if (
        r3_state.get("live_root3_predicates"),
        r3_state.get("matched_scope_targets"),
        r3_state.get("currently_runnable_event_count"),
    ) != (10, 7, 0):
        errors.append("ROOT3_CURRENT_STATE_DRIFT")
    if r3_state.get("fresh_reality_authority") is not False:
        errors.append("ROOT3_FRESH_REALITY_OVERCLAIM")

    vrp = retrieval.get("v19_verified_route_portfolio") or {}
    if vrp.get("mandatory_for_authorized_global_retrieval_plan_compilation") is not True:
        errors.append("RETRIEVAL_V19_NOT_MANDATORY")
    if not str(retrieval.get("status") or "").startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("RETRIEVAL_CURRENT_AUTHORITY_NOT_VERIFIED")

    tb4_result = tb4.get("result") or {}
    if tb4_result.get("attainability_state") != "IMPOSSIBLE":
        errors.append("TB4_FROZEN_ROUTE_NOT_IMPOSSIBLE")
    if not (
        isinstance(tb4_result.get("upper_bound_successes"), int)
        and isinstance(tb4_result.get("required_successes"), int)
        and tb4_result["upper_bound_successes"] < tb4_result["required_successes"]
    ):
        errors.append("TB4_IMPOSSIBILITY_INEQUALITY_NOT_PROVED")

    if not str(finance_direct.get("status") or "").startswith(
        "CANDIDATE__INDEPENDENT_THEOREM_PASS"
    ):
        errors.append("FINANCE_DIRECT_THRESHOLD_THEOREM_NOT_INDEPENDENT_PASS")
    if (finance_direct.get("authority") or {}).get("scheduling_authority") is not False:
        errors.append("FINANCE_DIRECT_THRESHOLD_PREMATURE_AUTHORITY")

    if "TOOL_STACK_IS_NOT_INHERENTLY_PAID" not in (finance_agent.get("deductions") or []):
        errors.append("FINANCE_AGENT_ZERO_COST_TOOL_BOUNDARY_NOT_NARROWED")

    if "BRAIN_SCORE_GE_81_8_PARTIAL" not in (osworld.get("still_open") or []):
        errors.append("OSWORLD_SCORE_RESIDUAL_DRIFT")

    exhausted = {
        row.get("route"): row
        for row in (r2.get("exhausted_or_deleted") or [])
        if isinstance(row, dict) and isinstance(row.get("route"), str)
    }
    for required in (
        "TB4_CIRCLECI_FREE_XLARGE_GEN2",
        "CURSORBENCH_OWNER_ACCESS_SEARCH",
        "AUTOMATIONBENCH_PUBLIC600_EQUIVALENCE_SEARCH",
        "GENERIC_ROOT3_SEARCH",
    ):
        if required not in exhausted:
            errors.append("MISSING_DELETED_OR_EXHAUSTED_ROUTE:" + required)

    if errors:
        return _fail(*errors)

    zero_probability_routes = [
        {
            "route": "TB4_FROZEN_CURRENT_NO_REPLAY_THRESHOLD_ROUTE",
            "probability_upper": 0.0,
            "basis": (
                f"VERIFIED_UPPER_BOUND_{tb4_result['upper_bound_successes']}_LT_"
                f"REQUIRED_{tb4_result['required_successes']}"
            ),
            "reopen": "CREDITABILITY_ROUTE_OR_CARRIER_ASSUMPTION_MATERIALLY_CHANGES",
        },
        {
            "route": "TB4_CIRCLECI_FREE_XLARGE_GEN2",
            "probability_upper": 0.0,
            "basis": "CURRENT_FREE_PLAN_RESOURCE_TABLE_EXCLUDES_REQUIRED_XLARGE",
            "reopen": exhausted["TB4_CIRCLECI_FREE_XLARGE_GEN2"].get("resume"),
        },
        {
            "route": "CURSORBENCH_OWNER_ACCESS_SEARCH",
            "probability_upper": 0.0,
            "basis": "DIRECT_OWNER_REPLY_CLOSED_EXTERNAL_EVALUATION_ROUTE",
            "reopen": exhausted["CURSORBENCH_OWNER_ACCESS_SEARCH"].get("resume"),
        },
        {
            "route": "AUTOMATIONBENCH_PUBLIC600_EQUIVALENCE_SEARCH",
            "probability_upper": 0.0,
            "basis": "PUBLIC_600_NOT_EXACT_PRIVATE_LEADERBOARD_POPULATION",
            "reopen": exhausted["AUTOMATIONBENCH_PUBLIC600_EQUIVALENCE_SEARCH"].get("resume"),
        },
    ]

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CURRENT_26_ADAPTIVE_SUPERTRANSACTION__"
            "ZERO_REALITY_THEN_CONDITIONAL_MINIMUM_REALITY__ZERO_CREDIT"
        ),
        "pass": True,
        "errors": [],
        "terminal_state": {
            "accepted_families": 5,
            "open_families": 14,
            "proved_predicates": 12,
            "unresolved_predicates": 26,
            "root1_positive_gaps": 0,
            "root2_touching_predicates": 19,
            "root3_touching_predicates": 10,
        },
        "causal_phase_lower_bound": 1,
        "causal_phase_upper_bound": 2,
        "phase_count_interpretation": (
            "ONE_ZERO_REALITY_PHASE_IS_UNAVOIDABLE_WHILE_26_PREDICATES_ARE_OPEN__"
            "SECOND_PHASE_EXISTS_IFF_VERIFIED_ZERO_REALITY_FIXED_POINT_LEAVES_"
            "IRREDUCIBLE_EMPIRICAL_RESIDUAL"
        ),
        "phases": [
            {
                "id": "Z",
                "name": "ZERO_REALITY_SUPERTRANSACTION",
                "fresh_reality_allowed": False,
                "parallel_actions": [
                    "USE_RETRIEVAL_V19_ONLY_FOR_LOAD_BEARING_NEW_OR_UNSATURATED_FACTS",
                    "BIND_EXACT_COMPARATOR_IDENTITY_TUPLES_BEFORE_ANY_SCORE",
                    "APPLY_OBJECTIVE_CEILING_FORMAL_DOMINANCE_AND_STRONGER_SCOPE_PROOFS",
                    "BIND_INFORMATION_POSITIVE_OWNER_OR_ACCESS_RECEIPTS_ON_ARRIVAL",
                    "RUN_ONLY_NAMED_ZERO_CASE_ACCOUNT_PROTOCOL_AND_QUOTA_PREFLIGHTS",
                    "BIND_VERIFIED_FINANCE_DIRECT_WEIGHTED_THRESHOLD_ROUTE_TO_CURRENT_ROOT2_AUTHORITY",
                    "RECOMPUTE_ROOT2_ROOT3_FIXED_POINT_AFTER_EVERY_VERIFIED_DELTA",
                ],
                "stop": "VERIFIED_ZERO_REALITY_FIXED_POINT",
            },
            {
                "id": "R",
                "name": "MINIMUM_REALITY_SUPERTRANSACTION",
                "conditional": True,
                "gate": (
                    "ONLY_IF_PHASE_Z_FIXED_POINT_LEAVES_UNRESOLVED_PREDICATES_AND_"
                    "EXPLICIT_FRESH_REALITY_AUTHORITY_IS_GRANTED"
                ),
                "parallel_actions": [
                    "EXECUTE_ONLY_MINIMUM_FIXED_BAR_SCORE_RESIDUALS_WITH_PASS_FAIL_LOCKS",
                    "EXECUTE_ONE_SHARED_ROOT3_MATCHED_SUPERPORTFOLIO_WAVE",
                    "EXECUTE_SURVIVING_FOUR_DIRECT_ORACLE_LEAVES_AS_ONE_PARALLEL_MICROBATCH",
                ],
                "receipt_rule": "EVERY_RECEIPT_TRIGGERS_IMMEDIATE_ACCEPTANCE_BACKPROP_AND_RESCHEDULING",
            },
        ],
        "automatic_finality": {
            "separate_manual_phase_required": False,
            "rule": (
                "AFTER_EVERY_VERIFIED_RECEIPT_RECOMPUTE_ALL_38_ATOMIC_PREDICATES__"
                "WHEN_UNRESOLVED_ZERO_RUN_FAMILY_REDUCER_OWNERSHIP_PROMOTION_"
                "CLEANROOM_AND_FINAL_PROOF_BUNDLE_ATOMICALLY"
            ),
        },
        "zero_probability_deleted_routes": zero_probability_routes,
        "external_waits_run_in_parallel": list(r2.get("waiting_external_facts") or []),
        "root3_event_classes": list(r3.get("minimum_event_classes") or []),
        "finance_direct_threshold_delta": {
            "state": "VERIFIED_THEOREM_CANDIDATE_REQUIRES_CURRENT_AUTHORITY_BINDING",
            "old_route": (finance_direct.get("scheduling_effect") or {}).get("old_required_route"),
            "new_route": (finance_direct.get("scheduling_effect") or {}).get("new_primary_route"),
            "separate_index_run_required": (finance_direct.get("scheduling_effect") or {}).get(
                "separate_index_run_required"
            ),
        },
        "probability_policy": {
            "deterministic_proof_or_exact_contradiction": "P_IN_{0,1}_AS_PROVED",
            "uncalibrated_owner_or_access_event": "P_INTERVAL_UNKNOWN__NO_POINT_ESTIMATE",
            "repeated_bernoulli_route": "JEFFREYS_BETA_POSTERIOR_ONLY",
            "correlation": "DO_NOT_SUM_CORRELATED_ROUTE_PROBABILITIES",
        },
        "search_policy": {
            "current_authority": "GLOBAL_RETRIEVAL_ENTRYPOINT_V4",
            "single_search_engine": "REJECTED_AS_STRUCTURALLY_INSUFFICIENT",
            "full_web_index_rebuild": "REJECTED_AS_DOMINATED",
            "open_world_miss": "UNKNOWN_NOT_NONEXISTENT",
            "stop": "FIRST_INDEPENDENTLY_VERIFIED_SUFFICIENT_WITNESS",
        },
        "hard_rules": [
            "ZERO_INCREMENTAL_SPEND",
            "NO_FRESH_REALITY_BEFORE_VERIFIED_ZERO_REALITY_FIXED_POINT",
            "NO_PUBLIC_PRIVATE_SUBSTITUTION_WITHOUT_EXACT_OR_SUPERSET_PROOF",
            "NO_REEXECUTION_OF_ZERO_PROBABILITY_ROUTE_WITHOUT_DECLARED_REOPEN_EVENT",
            "NO_POINT_PROBABILITY_WITHOUT_CALIBRATION_OR_DEDUCTIVE_CERTAINTY",
            "FINALITY_IS_AUTOMATIC_BACKPROP_NOT_A_SEPARATE_MANUAL_ACTION",
            "COMPILATION_GRANTS_ZERO_ACCEPTANCE_CAPABILITY_FAMILY_OR_OWNERSHIP_CREDIT",
        ],
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "acceptance_credit_delta": 0,
        "family_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
