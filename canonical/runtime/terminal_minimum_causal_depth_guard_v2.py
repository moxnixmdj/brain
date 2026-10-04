from __future__ import annotations
import json
from pathlib import Path

PLAN = Path("canonical/governance/TERMINAL_MINIMUM_CAUSAL_DEPTH_PLAN_V2.json")
ARENA = Path("canonical/governance/ARENA_COMPARATOR_PUBLIC_SEMANTICS_RECONCILIATION_V1.json")
BLIND = Path("canonical/governance/ROOT2_BLIND_THRESHOLD_RECEIPT_ACTIVATION_V1.json")
V1_ACTIVATION = Path("canonical/governance/TERMINAL_MINIMUM_CAUSAL_DEPTH_ACTIVATION_V1.json")

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
    v1 = load(V1_ACTIVATION)

    assert plan["schema"] == "PROJECT_BRAIN_TERMINAL_MINIMUM_CAUSAL_DEPTH_PLAN_V2"
    assert plan["terminal_state"]["accepted_families"] == 5
    assert plan["terminal_state"]["proved_atomic"] == 12
    assert plan["terminal_state"]["unresolved_atomic"] == 26
    assert plan["fresh_reality_authority"] is False
    assert plan["execution_authority"] is False
    assert plan["promotion_authority"] is False
    assert plan["inherited_v1_binding"]["preserve_v1_immutability"] is True
    assert plan["inherited_v1_binding"]["git_blob_sha"] == "c184c1aed33c06f6b4307ace79a959c21de96958"
    assert v1["plan"]["git_blob_sha"] == "3c203a1c2060b333a2e13417ab3a3a2880c94f2c"

    evidence = plan["macro_actions"][0]
    special = evidence["relative_elo_special_case"]
    assert set(special["predicates"]) == REL_ELO
    assert set(special["inadmissible_as_sufficient_without_bridge"]) == REL_ELO_FORBIDDEN_WITHOUT_BRIDGE
    assert "VERIFIED_RELATIVE_SCORE_BRIDGE" in special["surviving_route_classes"]
    assert "AUTHENTICATED_OWNER_RELATIVE_THRESHOLD_RECEIPT" in special["surviving_route_classes"]

    blind_special = evidence["blind_threshold_special_case"]
    assert "AUTHENTICATED_ONE_BIT_THRESHOLD_RECEIPT_RACE" in evidence["parallel_lanes"]
    assert set(blind_special["predicates"]) == BLIND_ELIGIBLE
    assert blind_special["activation_git_blob_sha"] == "324a7a762a3a2e7116372414afa6b52343673a3d"
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
    assert arena["execution_authority"] is False
    assert arena["fresh_reality_authority"] is False

    return {
        "schema": "PROJECT_BRAIN_TERMINAL_MINIMUM_CAUSAL_DEPTH_GUARD_V2",
        "status": "PASS",
        "v1_verified_subject_immutability_preserved": True,
        "terminal_counts_preserved": True,
        "relative_elo_transport_fail_closed": True,
        "blind_threshold_minimum_information_bound": True,
        "arena_account_inference_fail_closed": True,
        "isolation_authority_fail_closed": True,
        "acceptance_credit_delta": 0,
    }

if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
