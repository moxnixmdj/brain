from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime import finance_former_latter_resolve_v1 as p
from canonical.runtime import finance_former_latter_verify_v1 as v
from canonical.runtime import r2_finance_former_latter_direct_adequacy_v1 as d


def _case(text):
    return {"schema":p.INPUT_SCHEMA,"domain":"FINANCE","source_id":"pair","source_text":text}


def _goal(inp="canonical/tmp/pair.json",out="canonical/tmp/result.json"):
    return (
        "Using the explicit ordered-pair finance reference case at "+inp+
        ", resolve and independently verify former/latter references and save them to "+out+"."
    )


def _write(root:Path,text):
    q=root/"canonical/tmp/pair.json"; q.parent.mkdir(parents=True,exist_ok=True)
    q.write_text(json.dumps(_case(text)),encoding="utf-8"); return q


def test_both_former_and_latter(tmp_path:Path):
    _write(tmp_path,"The producer and the verifier form the ordered pair. The former must not overwrite the latter.")
    o=d.run({"task_id":"both","goal":_goal()},repo_root=tmp_path)
    assert o["pass"] is True and o["binding_count"]==2


def test_single_reference_each(tmp_path:Path):
    q=_write(tmp_path,"The reserve model and the stress model form the ordered pair. The former must publish first.")
    assert d.run({"task_id":"f","goal":_goal()},repo_root=tmp_path)["pass"] is True
    q.write_text(json.dumps(_case("The reserve model and the stress model form the ordered pair. The latter must publish second.")))
    assert d.run({"task_id":"l","goal":_goal()},repo_root=tmp_path)["pass"] is True


def test_missing_explicit_pair_fails(tmp_path:Path):
    _write(tmp_path,"The producer writes candidate.json and the verifier writes verdict.json. The former must not overwrite the latter.")
    assert d.preflight({"task_id":"x","goal":_goal()},repo_root=tmp_path)["status"]=="FAIL_CLOSED"


def test_duplicate_pair_entity_fails(tmp_path:Path):
    _write(tmp_path,"The verifier and the verifier form the ordered pair. The former must precede the latter.")
    assert d.preflight({"task_id":"x","goal":_goal()},repo_root=tmp_path)["status"]=="FAIL_CLOSED"


def test_no_reference_fails(tmp_path:Path):
    _write(tmp_path,"The producer and the verifier form the ordered pair. Both must persist evidence.")
    assert d.preflight({"task_id":"x","goal":_goal()},repo_root=tmp_path)["status"]=="FAIL_CLOSED"


def test_tamper_rejected_and_rollback(monkeypatch,tmp_path:Path):
    text="The producer and the verifier form the ordered pair. The former must not overwrite the latter."
    case=_case(text); result=p.compute(case); tam=json.loads(json.dumps(result))
    tam["bindings"][0]["target"]="SECOND"
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
