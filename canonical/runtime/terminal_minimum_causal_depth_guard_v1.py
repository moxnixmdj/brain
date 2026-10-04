from __future__ import annotations
import json
from pathlib import Path

PLAN = Path("canonical/governance/TERMINAL_MINIMUM_CAUSAL_DEPTH_PLAN_V1.json")
ARENA = Path("canonical/governance/ARENA_COMPARATOR_PUBLIC_SEMANTICS_RECONCILIATION_V1.json")
BLIND = Path("canonical/governance/ROOT2_BLIND_THRESHOLD_RECEIPT_ACTIVATION_V1.json")

REL_ELO = {
    "PROWORK_GDPVAL_GE_1846",
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
}

BLIND_ELIGIBLE = {
    "CODING_FRONTIERCODE_GE_54_4",
    "CODING_CURSORBENCH_GE_57_8",
    "PROWORK_GDPVAL_GE_1846",
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "FINANCE_AGENT_V2_GE_58_59",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
    "MYSTERYMECHANISM_GE_49_55",
}

BLIND_ACTIVATION_BLOB = "324a7a762a3a2e7116372414afa6b52343673a3d"

REL_ELO_FORBIDDEN_WITHOUT_BRIDGE = {
    "PURE_ABSOLUTE_BEHAVIORAL_DOMINANCE",
    "OBJECTIVE_CEILING_OR_FLOOR_ON_NONRELATIVE_METRICS",
    "EXHAUSTIVE_TASK_UNIVERSE_PROOF_WITHOUT_RELATIVE_SCORE_BRIDGE",
    "SCOPE_SAFE_BEHAVIORAL_DOMINANCE_WITHOUT_RELATIVE_SCORE_BRIDGE",
}

def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def verify() -> dict:
    plan = load(PLAN)
    arena = load(ARENA)
    blind = load(BLIND)
    assert plan["terminal_state"]["unresolved_atomic"] == 26
    assert plan["terminal_state"]["proved_atomic"] == 12
    assert plan["terminal_state"]["accepted_families"] == 5
    assert plan["fresh_reality_authority"] is False
    assert plan["execution_authority"] is False
    assert plan["promotion_authority"] is False

    evidence = plan["macro_actions"][0]
    special = evidence["relative_elo_special_case"]
    assert set(special["predicates"]) == REL_ELO
    assert set(special["inadmissible_as_sufficient_without_bridge"]) == REL_ELO_FORBIDDEN_WITHOUT_BRIDGE
    assert "VERIFIED_RELATIVE_SCORE_BRIDGE" in special["surviving_route_classes"]
    assert "AUTHENTICATED_OWNER_RELATIVE_THRESHOLD_RECEIPT" in special["surviving_route_classes"]

    blind_special = evidence["blind_threshold_special_case"]
    assert "AUTHENTICATED_ONE_BIT_THRESHOLD_RECEIPT_RACE" in evidence["parallel_lanes"]
    assert set(blind_special["predicates"]) == BLIND_ELIGIBLE
    assert blind_special["activation_git_blob_sha"] == BLIND_ACTIVATION_BLOB
    assert blind_special["preferred_information"] == "AUTHENTICATED_PASS_FAIL_AT_EXACT_FROZEN_THRESHOLD"
    assert blind_special["exact_score_required"] is False
    assert blind_special["private_dataset_required"] is False
    assert blind_special["matched_noninferiority_excluded"] is True
    assert blind_special["source_authenticity_rule"] == "SEPARATE_CONTENT_ADDRESSED_VERIFICATION_REQUIRED"
    assert blind_special["relative_rating_rule"] == "OFFICIAL_RELATIVE_RATING_THRESHOLD_VERDICT_ONLY"
    assert set(blind["eligible_root2_routes"]) == BLIND_ELIGIBLE
    assert blind["status"].startswith("ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS")
    assert blind["authority"]["receipt_structural_validation"] is True
    assert blind["authority"]["fresh_reality"] is False
    assert blind["authority"]["acceptance_reduction"] is False

    isolation = plan["macro_actions"][1]
    assert len(isolation["generic_antecedents"]) >= 5
    assert set(isolation["benchmark_interface"]) == {
        "POPULATION_IDENTITY", "SCORER_IDENTITY", "EFFORT_SEMANTICS",
        "TOOL_BOUNDARY", "ENVIRONMENT_IDENTITY", "COMPARATOR_IDENTITY",
    }

    assert arena["public_semantics"]["model_enumeration_endpoint_documented"] is True
    assert arena["public_semantics"]["direct_model_parameter_routing_documented"] is True
    assert arena["public_semantics"]["fallback_control_documented"] is True
    assert arena["public_semantics"]["resolved_model_header_documented"] is True
    assert "AUTHENTICATED_ACCOUNT_V1_MODELS_INCLUDES_EXACT_REQUIRED_OPUS55_VARIANT" in arena["remaining_load_bearing_unknowns"]
    assert "ZERO_INCREMENTAL_SPEND_ENTITLEMENT_OR_PREEXISTING_CREDIT_SUFFICIENT_FOR_MATCHED_WAVE" in arena["remaining_load_bearing_unknowns"]
    assert arena["execution_authority"] is False
    assert arena["fresh_reality_authority"] is False

    return {
        "schema": "PROJECT_BRAIN_TERMINAL_MINIMUM_CAUSAL_DEPTH_GUARD_V1",
        "status": "PASS",
        "terminal_counts_preserved": True,
        "relative_elo_transport_fail_closed": True,
        "arena_account_inference_fail_closed": True,
        "isolation_authority_fail_closed": True,
        "blind_threshold_minimum_information_bound": True,
        "acceptance_credit_delta": 0,
    }

if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
