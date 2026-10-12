from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct
from canonical.runtime import r2_typed_decision_direct_adequacy_v1 as typed

def _problem():
    return {
        "schema":"PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
        "decision_id":"d1","question":"Which option?",
        "alternatives":[{"id":"A","label":"A"},{"id":"B","label":"B"}],
        "constraints":[],
        "evidence":[{"id":"e1","alternative":"A","relation":"SUPPORTS","confidence":1.0,"strength":1.0,
                     "independence_group":"g1","claim":"A supported","provenance":[{"source":"test","ref":"1"}]}],
        "policy":{"minimum_support_ratio":0.6,"maximum_conflict_ratio":0.5,
                  "minimum_independent_support_groups":1,"minimum_net_margin":0.1},
    }

def test_typed_decision_route_is_live_eighth_route(monkeypatch, tmp_path:Path):
    inp=tmp_path/"canonical/tmp/decision.json"
    inp.parent.mkdir(parents=True)
    inp.write_text(json.dumps(_problem()),encoding="utf-8")
    monkeypatch.setattr(typed,"ROOT",tmp_path)
    goal=("Using the typed decision problem at canonical/tmp/decision.json, "
          "synthesize the verified decision and save it to canonical/tmp/result.json.")
    req={"task_id":"typed-decision-integration","goal":goal}
    assert len(direct.ROUTES)>=8
    pf=direct.preflight(req)
    assert pf["matched"] is True
    assert pf["route_id"]==direct.TYPED_DECISION_ROUTE_ID
    out=direct.run(req)
    assert out["pass"] is True
    assert out["route_id"]==direct.TYPED_DECISION_ROUTE_ID
    assert out["semantic_acceptance_complete"] is True
    assert out["actual_goal_satisfaction_verified"] is True
    assert out["retry_by_other_route_authorized"] is False
