from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

FILES={
 "overlay":"canonical/governance/ROOT2_SYNTHESIS_RESIDUAL_RECONCILIATION_V1.json",
 "activation":"canonical/governance/ROOT2_CLOSURE_CONTROLLER_V2_ACTIVATION_V1.json",
 "controller_verification":"canonical/verification/ROOT2_CLOSURE_CONTROLLER_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json",
 "frontier":"canonical/governance/ROOT2_CLOSURE_V2_CURRENT_FRONTIER_V1.json",
 "root_state":"canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json",
 "ceiling":"canonical/governance/OPUS55_SYNTHESIS_REQUIRED_CLAIM_COVERAGE_CEILING_LIFT_V2.json",
}
EXPECTED={
 "activation":"4cbc1b9f478654b2dc671a8b54f91b5c4b91c019",
 "controller_verification":"430b5918cb455304bf9227f4ada8dd686f615f78",
 "frontier":"c194e038cba8d819a088f985e68ba6d0078fc73f",
 "root_state":"8b8721e0f9b65ab86f193fcf7d19b8a8d286b0a4",
 "ceiling":"f2ef80facb39264b1e12b81e451eb4499a3b987f",
}

def blob_sha(path: Path) -> str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(name):
    return json.loads((ROOT/FILES[name]).read_text())

def main():
    for name,sha in EXPECTED.items():
        got=blob_sha(ROOT/FILES[name])
        assert got==sha,(name,got,sha)

    o=load("overlay")
    a=load("activation")
    cv=load("controller_verification")
    f=load("frontier")
    r=load("root_state")
    c=load("ceiling")

    assert a["authority"]["scheduling_authority"] is True
    assert a["hard_rules"].count("PRESERVE_NEWER_CURRENT_AUTHORITY_OVER_STALE_CONTROLLER_METADATA")==1
    assert cv["verifier"]["conclusion"]=="success"
    assert cv["verified"][-1]=="SYNTHESIS_SCOPE_SIDE_NOT_REOPENED"

    part=r["current_residual_root_partition"]
    assert part["root2_only_count"]==16
    assert part["root3_only_count"]==7
    assert part["root2_and_root3_count"]==3
    assert part["unresolved_total"]==26
    assert "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR" in part["root2_only"]

    synth=[x for x in f["zero_reality_parallel"] if x["id"]=="SYNTHESIS_METRIC_NONINFERIORITY_PROOF"]
    assert len(synth)==1

    proof=c["proof_composition"]
    assert proof["verified_source_to_target_relation"]=="SUPERSET"
    assert proof["relation_independent"] is True
    assert proof["brain_required_claim_coverage_lower_bound"]==1
    assert proof["admissible_metric_upper_bound"]==1
    assert proof["brain_minus_comparator_lower_bound"]==0
    assert c["derived_metric_bounds"]["required_claim_coverage_noninferiority"]["lower"]==0
    assert set(c["explicitly_not_proved"])=={"metric:matched_quality","matched_quality_noninferiority"}
    assert c["expected_residual_after_verification"]=={
      "missing_atoms":["metric:matched_quality"],
      "missing_metric_bounds":["matched_quality_noninferiority"],
    }

    assert o["old_stale_residual_projection"]==[
      "metric:matched_quality",
      "matched_quality_noninferiority",
      "required_claim_coverage_noninferiority",
    ]
    assert o["current_residual"]==["metric:matched_quality","matched_quality_noninferiority"]
    assert o["discharged"]["item"]=="required_claim_coverage_noninferiority"
    assert o["discharged"]["brain_minus_comparator_lower_bound"]==0
    assert o["independent_coverage_ceiling_verification"]["conclusion"]=="success"
    assert o["independent_coverage_ceiling_verification"]["workflow_run_id"]==37164910933
    assert o["independent_coverage_ceiling_verification"]["workflow_job_id"]==111325748211

    for k in ("incremental_spend_usd","new_reality_units_consumed","terminal_cases_consumed","acceptance_credit_delta","family_credit_delta","capability_credit_delta","ownership_credit_delta"):
        assert o["accounting"][k]==0
    assert o["execution_authority"] is False
    assert o["promotion_authority"] is False
    assert o["fresh_reality_authority"] is False

    print(json.dumps({
      "schema":"PROJECT_BRAIN_ROOT2_SYNTHESIS_RESIDUAL_RECONCILIATION_V1_VERDICT",
      "status":"PASS__SYNTHESIS_CURRENT_RESIDUAL_EXACTLY_MATCHED_QUALITY_ATOM_PLUS_NONINFERIORITY_BOUND__COVERAGE_BOUND_DISCHARGED__ZERO_CREDIT",
      "pass":True
    },sort_keys=True))

if __name__=="__main__":
    main()
