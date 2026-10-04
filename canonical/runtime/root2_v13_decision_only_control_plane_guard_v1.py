from __future__ import annotations
import json
from pathlib import Path

ROOT=Path("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
CURRENT=Path("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
V13=Path("canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V13.json")
V13_VERIFY=Path("canonical/verification/ROOT2_FRONTIER_V13_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
V13_ACT=Path("canonical/governance/ROOT2_FRONTIER_V13_FINAL_ACTIVATION_V1.json")
DECISION_FINAL=Path("canonical/governance/ROOT2_DECISION_ONLY_EVALUATION_FINAL_ACTIVATION_V1.json")
DECISION_PRIOR_ROOT_VERIFY=Path("canonical/verification/ROOT2_DECISION_ONLY_ROOT_PROJECTION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json")
ARENA=Path("canonical/governance/ARENA_PUBLIC_SEMANTICS_TRUTH_REPAIR_V1.json")
RECEIPT_PATH="canonical/verification/ROOT2_V13_DECISION_ONLY_CONTROL_PLANE_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json"

EXPECTED={
 "root":"aff9dd642ce05f174374b2c9e2c7d0b282f257a2",
 "current":"2ac73aee0efd81fca9a66413ecf1097b7b049d97",
 "v13":"bb631b80eea5a183728fb27e2aff99bbe63f1757",
 "v13_verify":"dd810106cf30f101453da07e2ef37cb81d7faddd",
 "v13_act":"08c84d8f0a46ff0f13943388306195fea79ca6d7",
 "decision_final":"2f8690507a16840f085bcf34da90df1593dd0226",
 "decision_prior_root_verify":"432d15b62b70dd6f7e030aafd7239bd1a381b5ee",
 "arena":"a76391c98767a0fa688adc32f5ac23f9caaea624",
}

def load(p:Path)->dict:
    return json.loads(p.read_text(encoding="utf-8"))

def verify()->dict:
    root=load(ROOT); cur=load(CURRENT); v13=load(V13); vv=load(V13_VERIFY); va=load(V13_ACT)
    df=load(DECISION_FINAL); dp=load(DECISION_PRIOR_ROOT_VERIFY); arena=load(ARENA)

    c=root["current_acceptance"]
    assert c["accepted_families"]==5 and c["open_families"]==14
    assert c["proved_atomic"]==12 and c["unresolved_atomic"]==26
    assert c["total_families"]==19 and c["total_atomic"]==38 and c["terminal"] is False
    assert cur["atomic_acceptance_frontier"]["proved"]==12
    assert cur["atomic_acceptance_frontier"]["unresolved"]==26
    assert cur["ownership_state"]["verified_owned_families"]==5
    assert cur["ownership_state"]["terminal_goal_achieved"] is False

    sp=root["scheduler_policy"]
    assert sp["root2_active_controller"]=="ROOT2_CLOSURE_CONTROLLER_V2"
    assert sp["root2_current_frontier"]=="canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V13.json"
    assert sp["root2_effective_scheduling_authority"] is True

    proj=sp["root2_v13_control_plane_projection"]
    assert proj["frontier_git_blob_sha"]==EXPECTED["v13"]
    assert proj["frontier_verification_git_blob_sha"]==EXPECTED["v13_verify"]
    assert proj["staged_activation_git_blob_sha"]==EXPECTED["v13_act"]
    assert proj["control_plane_verification_path"]==RECEIPT_PATH
    assert proj["scheduling_authority"] is True
    assert proj["execution_authority"] is False
    assert proj["promotion_authority"] is False
    assert proj["fresh_reality_authority"] is False
    assert "V14_THROUGH_V18" in proj["higher_frontiers_v14_through_v18"]

    assert va["frontier"]["git_blob_sha"]==EXPECTED["v13"]
    assert va["verification"]["git_blob_sha"]==EXPECTED["v13_verify"]
    assert va["authority"]["scheduling"] is True
    assert va["authority"]["execution"] is False
    assert va["authority"]["fresh_reality"] is False
    assert vv["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")
    assert v13["exact_state"]["accepted_families"]==5
    assert v13["exact_state"]["proved_atomic"]==12
    assert v13["exact_state"]["unresolved_atomic"]==26

    decision=sp["root2_decision_only_evaluation"]
    assert decision["root_projection_verification_path"]==RECEIPT_PATH
    assert decision["scheduling_authority"] is True
    assert decision["decision_certificate_compilation"] is True
    assert decision["execution_authority"] is False
    assert decision["fresh_reality_authority"] is False
    assert decision["route_precedence"]==[
      "AUTHENTICATED_ONE_BIT_THRESHOLD_RECEIPT_WHEN_SUFFICIENT",
      "OUTPUT_ONLY_THRESHOLD_DAG_MINIMUM_ZERO_REALITY_CERTIFICATE_CUT",
      "MINIMUM_AUTHORIZED_EMPIRICAL_RESIDUAL",
      "FULL_BENCHMARK_ONLY_IF_IRREDUCIBLE",
    ]
    assert df["status"].startswith("ACTIVE__INDEPENDENT_PUBLIC_RUNNER_PASS")
    assert df["effective_authority"]["scheduling"] is True
    assert df["effective_authority"]["benchmark_execution"] is False
    assert dp["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")

    assert cur["root2_frontier_authority"]==proj
    assert cur["root2_decision_only_evaluation"]==decision
    assert "ROOT2_V13" in cur["next_terminal_action"]
    assert "DECISION_ONLY" in cur["next_terminal_action"]
    assert "V10" not in cur["next_terminal_action"]
    assert "V12" not in cur["next_terminal_action"]
    assert "FULL_BENCHMARK_ONLY_IF_IRREDUCIBLE" in cur["next_terminal_action"]
    assert "NO_FRESH_REALITY_WITHOUT_SEPARATE_EXPLICIT_AUTHORITY" in cur["next_terminal_action"]

    ar=sp["arena_public_semantics_truth_repair"]
    assert ar["git_blob_sha"]==EXPECTED["arena"]
    assert cur["arena_public_semantics_truth_repair"]["git_blob_sha"]==EXPECTED["arena"]
    assert arena["observed_now"]["endpoint_and_routing_semantics_unauthenticated_publicly_reproducible"] is False
    gated=set(arena["corrected_classification"]["login_gated_or_account_specific"])
    for x in ("GET_V1_MODELS_ENDPOINT_SEMANTICS","DIRECT_MODEL_PARAMETER_ROUTING_SEMANTICS","FALLBACK_CONTROL_SEMANTICS","RESOLVED_MODEL_RESPONSE_HEADER_SEMANTICS"):
        assert x in gated

    return {
      "schema":"PROJECT_BRAIN_ROOT2_V13_DECISION_ONLY_CONTROL_PLANE_GUARD_V1",
      "status":"PASS",
      "counts_preserved_5_12_26":True,
      "root2_v13_projection_exact":True,
      "decision_only_projection_exact":True,
      "stale_v10_instruction_deleted":True,
      "v14_through_v18_not_promoted":True,
      "arena_truth_repair_preserved":True,
      "execution_authority":False,
      "promotion_authority":False,
      "fresh_reality_authority":False,
      "acceptance_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(verify(),sort_keys=True))
