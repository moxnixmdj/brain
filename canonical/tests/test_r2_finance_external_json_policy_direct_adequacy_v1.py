from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from canonical.runtime import r2_finance_external_json_policy_direct_adequacy_v1 as d


def _goal():
    return (
        "Using the authenticated finance external JSON case at canonical/tmp/case.json, "
        "fetch and independently verify the external observation, select the action, "
        "and save it to canonical/tmp/result.json."
    )


def _case(operator="DECIMAL_GTE",literal="5.0"):
    return {
        "schema":"PROJECT_BRAIN_FINANCE_EXTERNAL_JSON_POLICY_CASE_V1",
        "case_id":"ext-1",
        "state_path":"canonical/tmp/state.json",
        "url_key":"finance_api",
        "observation_output_path":"canonical/tmp/observation.json",
        "fact_json_path":["data","ratio"],
        "operator":operator,
        "literal":literal,
        "action_if_true":"ACCEPT",
        "action_if_false":"ESCALATE",
    }


def _setup(root:Path,case=None):
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True)
    (p/"state.json").write_text(json.dumps({"finance_api":"https://example.test/fact"}))
    (p/"case.json").write_text(json.dumps(case or _case()))


def _preflight_stub(request,repo_root=None):
    return {
        "matched":True,
        "status":"DIRECT_ADEQUACY_ROUTE_MATCHED",
        "route_id":"DIRECT_ADEQUACY::STATE_KEYED_HTTPS_JSON_OBSERVATION_FAMILY_V1",
        "requested_url":"https://example.test/fact",
        "output_path":"canonical/tmp/observation.json",
    }


def _runner(observation):
    def run(request,repo_root=None):
        root=Path(repo_root)
        out=root/"canonical/tmp/observation.json"
        out.write_text(json.dumps(observation))
        return {
            "pass":True,
            "status":"PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",
            "output_path":"canonical/tmp/observation.json",
            "acceptance_receipt":{
                "verified":True,
                "producer_independent":True,
                "semantic_json_equal":True,
                "verifier":"curl",
            },
        }
    return run


def test_decimal_true_selects_accept(monkeypatch,tmp_path:Path):
    _setup(tmp_path)
    monkeypatch.setattr(d.http_observation,"preflight",_preflight_stub)
    out=d.run({"task_id":"a","goal":_goal()},repo_root=tmp_path,
              http_runner=_runner({"data":{"ratio":"5.25"}}))
    assert out["pass"] is True,out
    assert out["predicate_holds"] is True and out["selected_action"]=="ACCEPT"
    assert out["external_observation_receipt"]["producer_independent"] is True


def test_decimal_false_selects_escalate(monkeypatch,tmp_path:Path):
    _setup(tmp_path)
    monkeypatch.setattr(d.http_observation,"preflight",_preflight_stub)
    out=d.run({"task_id":"b","goal":_goal()},repo_root=tmp_path,
              http_runner=_runner({"data":{"ratio":"4.99"}}))
    assert out["pass"] is True,out
    assert out["predicate_holds"] is False and out["selected_action"]=="ESCALATE"


def test_boolean_policy(monkeypatch,tmp_path:Path):
    c=_case("BOOL_EQ",True); c["fact_json_path"]=["flags","approved"]
    _setup(tmp_path,c)
    monkeypatch.setattr(d.http_observation,"preflight",_preflight_stub)
    out=d.run({"task_id":"c","goal":_goal()},repo_root=tmp_path,
              http_runner=_runner({"flags":{"approved":True}}))
    assert out["pass"] is True and out["selected_action"]=="ACCEPT"


def test_missing_independent_http_receipt_rolls_back(monkeypatch,tmp_path:Path):
    _setup(tmp_path)
    outp=tmp_path/"canonical/tmp/result.json"; outp.write_text('{"old":true}\n'); old=outp.read_bytes()
    obsp=tmp_path/"canonical/tmp/observation.json"; obsp.write_text('{"old_obs":true}\n'); oldobs=obsp.read_bytes()
    monkeypatch.setattr(d.http_observation,"preflight",_preflight_stub)
    def bad(request,repo_root=None):
        (Path(repo_root)/"canonical/tmp/observation.json").write_text(json.dumps({"data":{"ratio":"5.25"}}))
        return {"pass":True,"output_path":"canonical/tmp/observation.json","acceptance_receipt":{"verified":True,"producer_independent":False,"semantic_json_equal":True}}
    out=d.run({"task_id":"bad","goal":_goal()},repo_root=tmp_path,http_runner=bad)
    assert out["pass"] is False and out["rollback_complete"] is True
    assert outp.read_bytes()==old and obsp.read_bytes()==oldobs


def test_observed_type_mismatch_fails_closed(monkeypatch,tmp_path:Path):
    _setup(tmp_path)
    monkeypatch.setattr(d.http_observation,"preflight",_preflight_stub)
    out=d.run({"task_id":"type","goal":_goal()},repo_root=tmp_path,
              http_runner=_runner({"data":{"ratio":5.25}}))
    assert out["pass"] is False and "DECIMAL_STRING_INVALID" in out["reason"]


def test_preflight_is_side_effect_free(monkeypatch,tmp_path:Path):
    _setup(tmp_path)
    monkeypatch.setattr(d.http_observation,"preflight",_preflight_stub)
    out=d.preflight({"task_id":"pf","goal":_goal()},repo_root=tmp_path)
    assert out["matched"] is True and out["status"]=="DIRECT_ADEQUACY_ROUTE_MATCHED"
    assert not (tmp_path/"canonical/tmp/observation.json").exists()
    assert not (tmp_path/"canonical/tmp/result.json").exists()


def test_nonmatching_goal_claims_no_scope(tmp_path:Path):
    out=d.preflight({"task_id":"x","goal":"Analyze the external fact."},repo_root=tmp_path)
    assert out["matched"] is False and out["pass"] is False
