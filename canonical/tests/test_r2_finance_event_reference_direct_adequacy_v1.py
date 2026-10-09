from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime import finance_event_reference_resolve_v1 as p
from canonical.runtime import finance_event_reference_verify_v1 as v
from canonical.runtime import r2_finance_event_reference_direct_adequacy_v1 as d


def _case(text):
    return {"schema":p.INPUT_SCHEMA,"domain":"FINANCE","source_id":"event","source_text":text}


def _goal(inp="canonical/tmp/event.json",out="canonical/tmp/result.json"):
    return (
        "Using the bounded finance event-reference case at "+inp+
        ", resolve and independently verify the demonstrative event reference and save it to "+out+"."
    )


def _write(root:Path,text):
    q=root/"canonical/tmp/event.json"; q.parent.mkdir(parents=True,exist_ok=True)
    q.write_text(json.dumps(_case(text)),encoding="utf-8"); return q


def test_three_lexical_bridges(tmp_path:Path):
    q=_write(tmp_path,"The verifier shall validate the manifest. This validation must precede promotion.")
    assert d.run({"task_id":"v","goal":_goal()},repo_root=tmp_path)["pass"] is True
    q.write_text(json.dumps(_case("The service shall operate the ledger. That operation must remain read-only.")))
    assert d.run({"task_id":"o","goal":_goal()},repo_root=tmp_path)["pass"] is True
    q.write_text(json.dumps(_case("The engine must process the filing. This process shall emit a receipt.")))
    assert d.run({"task_id":"p","goal":_goal()},repo_root=tmp_path)["pass"] is True


def test_event_type_mismatch_fails(tmp_path:Path):
    _write(tmp_path,"The verifier shall validate the manifest. This operation must precede promotion.")
    assert d.preflight({"task_id":"x","goal":_goal()},repo_root=tmp_path)["status"]=="FAIL_CLOSED"


def test_unsupported_event_noun_fails(tmp_path:Path):
    _write(tmp_path,"The verifier shall validate the manifest. This action must precede promotion.")
    assert d.preflight({"task_id":"x","goal":_goal()},repo_root=tmp_path)["status"]=="FAIL_CLOSED"


def test_malformed_antecedent_fails(tmp_path:Path):
    _write(tmp_path,"The verifier checks the manifest. This validation must precede promotion.")
    assert d.preflight({"task_id":"x","goal":_goal()},repo_root=tmp_path)["status"]=="FAIL_CLOSED"


def test_tamper_and_rollback(monkeypatch,tmp_path:Path):
    text="The verifier shall validate the manifest. This validation must precede promotion."
    case=_case(text); result=p.compute(case); tam=json.loads(json.dumps(result))
    tam["event_type"]="operation"
    assert v.verify(case,tam)["verified"] is False

    _write(tmp_path,text)
    op=tmp_path/"canonical/tmp/result.json"; op.write_text('{"old":true}\n'); old=op.read_bytes()
    original=d.verifier.verify; calls={"n":0}
    def injected(c,r):
        calls["n"]+=1
        return original(c,r) if calls["n"]==1 else {"verified":False,"producer_independent":True,"errors":["forced"]}
    monkeypatch.setattr(d.verifier,"verify",injected)
    o=d.run({"task_id":"r","goal":_goal()},repo_root=tmp_path)
    assert o["pass"] is False and o["rollback_complete"] is True and op.read_bytes()==old
