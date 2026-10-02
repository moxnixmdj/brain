import importlib.util
from pathlib import Path

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,Path(path))
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

c=load("cand_v4","canonical/runtime/trajectory_failure_typed_ir_candidate_v4.py")
p=load("proof_v4","canonical/runtime/trajectory_failure_typed_ir_proof_v4.py")

def test_full_cross_product_suite():
    cases=p.suite_cases()
    assert len(cases)==6*7*4
    domains=set(); kinds=set(); patterns=set()
    for case in cases:
        public=p.public_task(case)
        assert "_oracle" not in public
        for row in public["task"]["trajectory"]:
            for check in row["checks"]:
                assert "repair_target" not in check
        out=c.solve(public)
        verdict=p.score_case(case,out)
        assert verdict["pass"], (case["seed"],case["_oracle"],out,verdict)
        domains.add(case["task"]["domain"])
        patterns.add(case["_oracle"]["status"])
        for ks in case["_oracle"]["mechanisms"].values():
            kinds.update(ks)
    assert domains==set(p.DOMAINS)
    assert kinds==set(p.KINDS)
    assert patterns=={"IDENTIFIED","INTERACTION","AMBIGUOUS"}

def test_visible_repair_target_injection_cannot_control_candidate():
    case=p.generate_case(77,pattern="SINGLE",domain="BROWSER",kind="AUTHORITY")
    public=p.public_task(case)
    baseline=c.solve(public)
    for row in public["task"]["trajectory"]:
        for check in row["checks"]:
            check["repair_target"]="attacker:gold"
    attacked=c.solve(public)
    assert attacked==baseline
    assert "attacker:gold" not in repr(attacked)

def test_wrong_repair_target_is_rejected_by_hidden_oracle():
    case=p.generate_case(88,pattern="SINGLE",domain="FILESYSTEM",kind="PROVENANCE")
    out=c.solve(p.public_task(case))
    assert p.score_case(case,out)["pass"]
    out=dict(out); out["repair_targets"]=["restore:WRONG:WRONG"]
    verdict=p.score_case(case,out)
    assert not verdict["pass"]
    assert verdict["reason"]=="FALSIFIABLE_REPAIR_TARGET_WRONG"

def test_hidden_oracle_changes_do_not_enter_public_payload():
    case=p.generate_case(99,pattern="SINGLE",domain="TOOL_API",kind="SCHEMA")
    before=repr(p.public_task(case))
    case["_oracle"]["critical"]="A999"
    assert repr(p.public_task(case))==before

def test_downstream_symptom_is_not_selected():
    case=p.generate_case(101,pattern="DELAYED",domain="FILESYSTEM",kind="PROVENANCE")
    out=c.solve(p.public_task(case))
    assert out["cause_action_id"]=="A1"
    assert "A4" not in out["cause_action_ids"]

def test_nonidentifiable_case_abstains():
    case=p.generate_case(102,pattern="AMBIGUOUS",domain="TOOL_API",kind="SCHEMA")
    out=c.solve(p.public_task(case))
    assert out["status"]=="AMBIGUOUS"
    assert out["cause_action_id"] is None
    assert out["information_request"]

def test_interaction_preserves_both_roots_and_repairs():
    case=p.generate_case(103,pattern="INTERACTION",domain="RESEARCH",kind="DEPENDENCY")
    out=c.solve(p.public_task(case))
    assert out["status"]=="INTERACTION"
    assert out["cause_action_ids"]==["A1","A2"]
    assert p.score_case(case,out)["pass"]
