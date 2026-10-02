import importlib.util
from pathlib import Path

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,Path(path))
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

c=load("cand_v5","canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py")
p=load("proof_v5","canonical/runtime/trajectory_failure_typed_ir_proof_v5.py")

def test_full_cross_product_suite_and_intervention_rescue():
    cases=p.suite_cases()
    assert len(cases)==6*8*4
    domains=set(); kinds=set(); statuses=set(); rescue_count=0
    for case in cases:
        public=p.public_task(case)
        assert "_oracle" not in public
        out=c.solve(public)
        verdict=p.score_case(case,out)
        assert verdict["pass"], (case["seed"],case["_oracle"],out,verdict)
        domains.add(case["task"]["domain"])
        statuses.add(case["_oracle"]["status"])
        for ks in case["_oracle"]["mechanisms"].values():
            kinds.update(ks)
        if case["_oracle"]["status"]!="AMBIGUOUS":
            rescue=p.intervention_rescue(case,out["repair_targets"])
            assert rescue["applicable"] is True
            assert rescue["rescued"] is True, (case["seed"],rescue,out)
            rescue_count+=1
    assert domains==set(p.DOMAINS)
    assert kinds==set(p.KINDS)
    assert "SCOPE" in kinds
    assert statuses=={"IDENTIFIED","INTERACTION","AMBIGUOUS"}
    assert rescue_count==6*8*3

def test_scope_is_first_class_not_authority_alias():
    case=p.generate_case(7001,pattern="SINGLE",domain="TOOL_API",kind="SCOPE")
    out=c.solve(p.public_task(case))
    assert out["status"]=="IDENTIFIED"
    assert out["mechanism_classes"]==["SCOPE"]
    assert out["repair_targets"]==["restore:A1:SCOPE"]
    assert "AUTHORITY" not in out["mechanism_classes"]
    assert p.score_case(case,out)["pass"]
    assert p.intervention_rescue(case,out["repair_targets"])["rescued"]

def test_delayed_scope_failure_rescue_survives_long_chain():
    case=p.generate_case(7002,pattern="DELAYED",domain="BROWSER",kind="SCOPE")
    out=c.solve(p.public_task(case))
    assert out["cause_action_id"]=="A1"
    rescue=p.intervention_rescue(case,out["repair_targets"])
    assert rescue["rescued"] is True
    assert rescue["poisoned_action_count"]==0

def test_interaction_requires_complete_root_repair_set():
    case=p.generate_case(7003,pattern="INTERACTION",domain="RESEARCH",kind="SCOPE")
    out=c.solve(p.public_task(case))
    assert out["status"]=="INTERACTION"
    assert len(out["repair_targets"])==2
    assert p.intervention_rescue(case,out["repair_targets"])["rescued"] is True
    partial=out["repair_targets"][:1]
    rescue=p.intervention_rescue(case,partial)
    assert rescue["rescued"] is False
    assert rescue["unrepaired_hidden_root_defect_count"]==1

def test_repair_target_naming_without_causal_rescue_is_rejected():
    case=p.generate_case(7004,pattern="SINGLE",domain="FILESYSTEM",kind="PROVENANCE")
    out=c.solve(p.public_task(case))
    assert p.score_case(case,out)["pass"]
    wrong=dict(out)
    wrong["repair_targets"]=["restore:A1:AUTHORITY"]
    verdict=p.score_case(case,wrong)
    assert not verdict["pass"]

def test_hidden_oracle_and_intervention_truth_never_enter_candidate_payload():
    case=p.generate_case(7005,pattern="DELAYED",domain="CODE",kind="SCOPE")
    public=p.public_task(case)
    assert "_oracle" not in public
    assert "rescued" not in repr(public)
    assert "hidden_root" not in repr(public).lower()
    baseline=c.solve(public)
    case["_oracle"]["critical"]="A999"
    assert c.solve(public)==baseline

def test_ambiguous_case_still_abstains_instead_of_faking_rescue():
    case=p.generate_case(7006,pattern="AMBIGUOUS",domain="ARTIFACT",kind="SCOPE")
    out=c.solve(p.public_task(case))
    assert out["status"]=="AMBIGUOUS"
    assert out["cause_action_id"] is None
    assert out["information_request"]
    rescue=p.intervention_rescue(case,[])
    assert rescue["applicable"] is False
    assert rescue["rescued"] is False

def test_invalid_mechanism_fails_closed():
    case=p.generate_case(7007,pattern="SINGLE",domain="CODE",kind="SCOPE")
    public=p.public_task(case)
    public["task"]["trajectory"][1]["checks"][1]["kind"]="NOT_A_REAL_KIND"
    out=c.solve(public)
    assert out["status"]=="FAIL_CLOSED"
