from __future__ import annotations
import json
from pathlib import Path

PLAN=Path("canonical/governance/TERMINAL_MINIMUM_CAUSAL_DEPTH_PLAN_V2.json")
V1=Path("canonical/governance/TERMINAL_MINIMUM_CAUSAL_DEPTH_ACTIVATION_V1.json")
BLIND=Path("canonical/governance/ROOT2_BLIND_THRESHOLD_RECEIPT_ACTIVATION_V1.json")
ARENA=Path("canonical/governance/ARENA_PUBLIC_SEMANTICS_TRUTH_REPAIR_V1.json")
ROOT=Path("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
CURRENT=Path("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")

BLIND_ELIGIBLE=set([
  "ARTIFACT_AA_BRIEFCASE_GE_1822",
  "CODING_CURSORBENCH_GE_57_8",
  "CODING_FRONTIERCODE_GE_54_4",
  "FINANCE_AGENT_V2_GE_58_59",
  "MYSTERYMECHANISM_GE_49_55",
  "PROWORK_AA_BRIEFCASE_GE_1822",
  "PROWORK_GDPVAL_GE_1846"
])
ARENA_LOGIN_GATED=set([
  "ACCOUNT_MODEL_LIST_INCLUDES_EXACT_REQUIRED_OPUS55_VARIANT",
  "DIRECT_MODEL_PARAMETER_ROUTING_SEMANTICS",
  "FALLBACK_CONTROL_SEMANTICS",
  "FROZEN_HARNESS_AND_EFFORT_COMPARABILITY",
  "GET_V1_MODELS_ENDPOINT_SEMANTICS",
  "RESOLVED_MODEL_RESPONSE_HEADER_SEMANTICS",
  "ZERO_INCREMENTAL_SPEND_ENTITLEMENT_OR_PREEXISTING_CREDIT"
])
REL_ELO={
    "PROWORK_GDPVAL_GE_1846",
    "PROWORK_AA_BRIEFCASE_GE_1822",
    "ARTIFACT_AA_BRIEFCASE_GE_1822",
}

def load(path: Path)->dict:
    return json.loads(path.read_text(encoding="utf-8"))

def verify()->dict:
    p=load(PLAN); v1=load(V1); blind=load(BLIND); arena=load(ARENA); root=load(ROOT); cur=load(CURRENT)
    assert p["schema"]=="PROJECT_BRAIN_TERMINAL_MINIMUM_CAUSAL_DEPTH_PLAN_V2"
    assert p["source_main"]=="5a184fb53c5915c8a322fdf8857631162e4b36c1"
    assert p["inherited_v1_binding"]["activation_git_blob_sha"]=="c184c1aed33c06f6b4307ace79a959c21de96958"
    assert p["inherited_v1_binding"]["plan_git_blob_sha"]=="3c203a1c2060b333a2e13417ab3a3a2880c94f2c"
    assert p["inherited_v1_binding"]["preserve_v1_immutability"] is True
    assert v1["plan"]["git_blob_sha"]=="3c203a1c2060b333a2e13417ab3a3a2880c94f2c"

    for key in ("accepted_families","open_families","proved_atomic","unresolved_atomic","total_families","total_atomic","terminal"):
        assert root["current_acceptance"][key]==p["terminal_state"][key]
    assert root["current_acceptance"]["accepted_families"]==5
    assert root["current_acceptance"]["proved_atomic"]==12
    assert root["current_acceptance"]["unresolved_atomic"]==26
    assert root["current_acceptance"]["terminal"] is False
    partition=root["current_residual_root_partition"]
    assert p["terminal_state"]["root1_positive_gaps"]==partition["root1_positive_gap_count"]
    assert p["terminal_state"]["root2_only"]==partition["root2_only_count"]
    assert p["terminal_state"]["root3_only"]==partition["root3_only_count"]
    assert p["terminal_state"]["root2_and_root3"]==partition["root2_and_root3_count"]
    assert cur["atomic_acceptance_frontier"]["proved"]==12
    assert cur["atomic_acceptance_frontier"]["unresolved"]==26
    assert cur["ownership_state"]["verified_owned_families"]==5
    assert cur["ownership_state"]["terminal_goal_achieved"] is False

    assert root["scheduler_policy"]["terminal_minimum_causal_depth"]["activation_git_blob_sha"]=="c184c1aed33c06f6b4307ace79a959c21de96958"
    assert cur["terminal_minimum_causal_depth_authority"]["activation_git_blob_sha"]=="c184c1aed33c06f6b4307ace79a959c21de96958"
    assert root["scheduler_policy"]["terminal_minimum_causal_depth"]["scheduling_authority"] is True
    assert cur["terminal_minimum_causal_depth_authority"]["scheduling_authority"] is True

    evidence=p["macro_actions"][0]
    assert "AUTHENTICATED_ONE_BIT_THRESHOLD_RECEIPT_RACE" in evidence["parallel_lanes"]
    bs=evidence["blind_threshold_special_case"]
    assert set(bs["predicates"])==BLIND_ELIGIBLE
    assert bs["activation_git_blob_sha"]=="324a7a762a3a2e7116372414afa6b52343673a3d"
    assert bs["exact_score_required"] is False
    assert bs["private_dataset_required"] is False
    assert bs["matched_noninferiority_excluded"] is True
    assert set(blind["eligible_root2_routes"])==BLIND_ELIGIBLE
    assert blind["authority"]["receipt_structural_validation"] is True
    assert blind["authority"]["fresh_reality"] is False
    special=evidence["relative_elo_special_case"]
    assert set(special["predicates"])==REL_ELO
    assert "AUTHENTICATED_OWNER_RELATIVE_THRESHOLD_RECEIPT" in special["surviving_route_classes"]
    assert "VERIFIED_RELATIVE_SCORE_BRIDGE" in special["surviving_route_classes"]

    ar=p["arena_public_semantics_truth_repair"]
    assert ar["git_blob_sha"]=="a76391c98767a0fa688adc32f5ac23f9caaea624"
    assert set(ar["login_gated_or_account_specific"])==ARENA_LOGIN_GATED
    assert arena["observed_now"]["endpoint_and_routing_semantics_unauthenticated_publicly_reproducible"] is False
    assert set(arena["corrected_classification"]["login_gated_or_account_specific"])==ARENA_LOGIN_GATED
    assert root["scheduler_policy"]["arena_public_semantics_truth_repair"]["git_blob_sha"]=="a76391c98767a0fa688adc32f5ac23f9caaea624"
    assert cur["arena_public_semantics_truth_repair"]["git_blob_sha"]=="a76391c98767a0fa688adc32f5ac23f9caaea624"
    for forbidden in (
        "GET_V1_MODELS_ENDPOINT_SEMANTICS",
        "DIRECT_MODEL_PARAMETER_ROUTING_SEMANTICS",
        "FALLBACK_CONTROL_SEMANTICS",
        "RESOLVED_MODEL_RESPONSE_HEADER_SEMANTICS",
    ):
        assert forbidden in ARENA_LOGIN_GATED

    assert p["execution_authority"] is False
    assert p["promotion_authority"] is False
    assert p["fresh_reality_authority"] is False
    assert root["scheduler_policy"]["arena_public_semantics_truth_repair"]["fresh_reality_authority"] is False
    assert cur["arena_public_semantics_truth_repair"]["fresh_reality_authority"] is False
    return {
      "schema":"PROJECT_BRAIN_TERMINAL_MINIMUM_CAUSAL_DEPTH_GUARD_V2",
      "status":"PASS",
      "current_acceptance_preserved":True,
      "v1_immutability_preserved":True,
      "blind_threshold_minimum_information_bound":True,
      "relative_elo_nontransport_preserved":True,
      "arena_truth_repair_preserved":True,
      "human_readable_next_action_not_trusted_as_authority":True,
      "acceptance_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
      "fresh_reality_authority":False,
    }

if __name__=="__main__":
    print(json.dumps(verify(),sort_keys=True))
