from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime import r2_typed_decision_direct_adequacy_v1 as d
def _problem():
    return {"schema":"PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1","decision_id":"d1","question":"Which option?","alternatives":[{"id":"A","label":"A"},{"id":"B","label":"B"}],"constraints":[],"evidence":[{"id":"e1","alternative":"A","relation":"SUPPORTS","confidence":1.0,"strength":1.0,"independence_group":"g1","claim":"A supported","provenance":[{"source":"test","ref":"1"}]}],"policy":{"minimum_support_ratio":0.6,"maximum_conflict_ratio":0.5,"minimum_independent_support_groups":1,"minimum_net_margin":0.1}}
def _goal(inp="canonical/tmp/decision.json",out="canonical/tmp/result.json"):
    return f"Using the typed decision problem at {inp}, synthesize the verified decision and save it to {out}."
def test_preflight_is_exact_and_side_effect_free(tmp_path:Path):
    p=tmp_path/"canonical/tmp/decision.json"; p.parent.mkdir(parents=True); p.write_text(json.dumps(_problem()),encoding="utf-8")
    out=d.preflight({"task_id":"t1","goal":_goal()},repo_root=tmp_path)
    assert out["matched"] is True and out["status"]=="DIRECT_ADEQUACY_ROUTE_MATCHED" and out["preflight_execution_authority"] is False
    assert not (tmp_path/"canonical/tmp/result.json").exists()
def test_run_produces_and_independently_verifies_full_raw_goal(tmp_path:Path):
    p=tmp_path/"canonical/tmp/decision.json"; p.parent.mkdir(parents=True); p.write_text(json.dumps(_problem()),encoding="utf-8")
    out=d.run({"task_id":"t1","goal":_goal()},repo_root=tmp_path)
    assert out["pass"] is True and out["semantic_acceptance_complete"] is True and out["actual_goal_satisfaction_verified"] is True
    assert out["direct_adequacy_authority"] is True and out["source_immutability_verified"] is True
    assert out["raw_acceptance_obligation_count"]==len(out["accepted_raw_obligation_ids"])
    result=json.loads((tmp_path/"canonical/tmp/result.json").read_text()); assert result["status"]=="DECIDED" and result["selected_alternative"]=="A"
def test_verifier_failure_rolls_back(monkeypatch,tmp_path:Path):
    inp=tmp_path/"canonical/tmp/decision.json"; outp=tmp_path/"canonical/tmp/result.json"; inp.parent.mkdir(parents=True)
    inp.write_text(json.dumps(_problem()),encoding="utf-8"); outp.write_text('{"old":true}\n',encoding="utf-8"); old=outp.read_bytes()
    monkeypatch.setattr(d.verifier,"run",lambda args,root:{"verified":False,"reason":"forced","producer_independent":True,"model_dependency_count":0})
    out=d.run({"task_id":"t1","goal":_goal()},repo_root=tmp_path)
    assert out["pass"] is False and out["rollback_complete"] is True and outp.read_bytes()==old
def test_nonmatching_goal_does_not_claim_scope(tmp_path:Path):
    out=d.preflight({"task_id":"t1","goal":"Decide something."},repo_root=tmp_path)
    assert out["matched"] is False and out["pass"] is False
