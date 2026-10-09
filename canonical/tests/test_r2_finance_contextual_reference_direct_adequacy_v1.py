from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime import finance_contextual_reference_resolve_v1 as p
from canonical.runtime import finance_contextual_reference_verify_v1 as v
from canonical.runtime import r2_finance_contextual_reference_direct_adequacy_v1 as d


def _case(text):
    return {
        "schema":p.INPUT_SCHEMA,
        "domain":"FINANCE",
        "source_id":"finance-ref",
        "source_text":text,
    }


def _goal(inp="canonical/tmp/ref_case.json",out="canonical/tmp/ref_result.json"):
    return (
        "Using the bounded contextual finance reference case at "+inp+
        ", resolve and independently verify the contextual references and save them to "+out+"."
    )


def _write(root:Path,text):
    q=root/"canonical/tmp/ref_case.json"; q.parent.mkdir(parents=True,exist_ok=True)
    q.write_text(json.dumps(_case(text)),encoding="utf-8"); return q


def test_singular_and_plural_pronoun(tmp_path:Path):
    q=_write(tmp_path,"The reserve model shall publish the ratio. It shall archive the result.")
    o=d.run({"task_id":"s","goal":_goal()},repo_root=tmp_path)
    assert o["pass"] is True
    q.write_text(json.dumps(_case("The parser and verifier shall record versions. They shall reject incompatible schemas.")))
    o=d.run({"task_id":"p","goal":_goal()},repo_root=tmp_path)
    assert o["pass"] is True


def test_mode_anaphora(tmp_path:Path):
    _write(tmp_path,"If stress mode is enabled, the process shall reject writes. In that mode, reads may continue.")
    o=d.run({"task_id":"m","goal":_goal()},repo_root=tmp_path)
    assert o["pass"] is True


def test_ellipsis_and_respectively(tmp_path:Path):
    q=_write(tmp_path,"The primary ledger must retain the evidence. The secondary ledger must, too.")
    assert d.run({"task_id":"e","goal":_goal()},repo_root=tmp_path)["pass"] is True
    q.write_text(json.dumps(_case("The producer and verifier shall write candidate.json and verdict.json, respectively.")))
    assert d.run({"task_id":"r","goal":_goal()},repo_root=tmp_path)["pass"] is True


def test_ambiguous_forms_fail_closed(tmp_path:Path):
    q=_write(tmp_path,"The parser shall publish the value. They shall archive it.")
    assert d.preflight({"task_id":"n","goal":_goal()},repo_root=tmp_path)["status"]=="FAIL_CLOSED"
    q.write_text(json.dumps(_case("The producer writes candidate.json and the verifier writes verdict.json. The former must not overwrite the latter.")))
    assert d.preflight({"task_id":"f","goal":_goal()},repo_root=tmp_path)["status"]=="FAIL_CLOSED"
    q.write_text(json.dumps(_case("The verifier shall recompute the hash. This validation must occur before promotion.")))
    assert d.preflight({"task_id":"d","goal":_goal()},repo_root=tmp_path)["status"]=="FAIL_CLOSED"


def test_verifier_tamper_and_rollback(monkeypatch,tmp_path:Path):
    text="The reserve model shall publish the ratio. It shall archive the result."
    case=_case(text)
    produced=p.compute(case)
    tam=json.loads(json.dumps(produced))
    tam["proposal"]["bindings"][0]["target_span"]=[0,1]
    assert v.verify(case,tam)["verified"] is False

    _write(tmp_path,text)
    op=tmp_path/"canonical/tmp/ref_result.json"; op.write_text('{"old":true}\n'); old=op.read_bytes()
    original=d.verifier.verify; calls={"n":0}
    def injected(c,r):
        calls["n"]+=1
        if calls["n"]==1:return original(c,r)
        return {"verified":False,"producer_independent":True,"errors":["forced"]}
    monkeypatch.setattr(d.verifier,"verify",injected)
    o=d.run({"task_id":"x","goal":_goal()},repo_root=tmp_path)
    assert o["pass"] is False and o["rollback_complete"] is True
    assert op.read_bytes()==old


def test_nonmatching_goal_no_claim(tmp_path:Path):
    o=d.preflight({"task_id":"z","goal":"Resolve references."},repo_root=tmp_path)
    assert o["matched"] is False and o["pass"] is False
