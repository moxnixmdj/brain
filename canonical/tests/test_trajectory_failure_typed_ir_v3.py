import importlib.util
from pathlib import Path

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,Path(path))
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

c=load("cand","canonical/runtime/trajectory_failure_typed_ir_candidate_v3.py")
p=load("proof","canonical/runtime/trajectory_failure_typed_ir_proof_v3.py")

def test_full_cross_product_suite():
    cases=p.suite_cases()
    assert len(cases)==6*7*4
    domains=set(); kinds=set(); patterns=set()
    for case in cases:
        public=p.public_task(case)
        assert "_oracle" not in public
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

def test_hidden_oracle_changes_do_not_enter_public_payload():
    case=p.generate_case(77,pattern="SINGLE",domain="BROWSER",kind="AUTHORITY")
    pub=p.public_task(case)
    before=repr(pub)
    case["_oracle"]["critical"]="A999"
    assert repr(p.public_task(case))==before

def test_downstream_symptom_is_not_selected():
    case=p.generate_case(88,pattern="DELAYED",domain="FILESYSTEM",kind="PROVENANCE")
    out=c.solve(p.public_task(case))
    assert out["cause_action_id"]=="A1"
    assert "A4" not in out["cause_action_ids"]

def test_nonidentifiable_case_abstains():
    case=p.generate_case(99,pattern="AMBIGUOUS",domain="TOOL_API",kind="SCHEMA")
    out=c.solve(p.public_task(case))
    assert out["status"]=="AMBIGUOUS"
    assert out["cause_action_id"] is None
    assert out["information_request"]

def test_interaction_preserves_both_roots():
    case=p.generate_case(101,pattern="INTERACTION",domain="RESEARCH",kind="DEPENDENCY")
    out=c.solve(p.public_task(case))
    assert out["status"]=="INTERACTION"
    assert out["cause_action_ids"]==["A1","A2"]
    assert out["critical_action_id"]=="A1"
