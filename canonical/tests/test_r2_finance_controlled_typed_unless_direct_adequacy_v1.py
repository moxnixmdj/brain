from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime import r2_finance_controlled_typed_unless_direct_adequacy_v1 as d
from canonical.runtime import finance_controlled_typed_unless_branch_v1 as p
from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256


def _case(text="Apply Rule A unless exception_holds is true.", value=True):
    ctx={"schema_id":"FINANCE_TYPED_CONTEXT_V1","fields":{
        "exception_holds":{"type":"BOOL","value":value}
    }}
    return {"schema":p.INPUT_SCHEMA,"source_id":"finance-controlled","source_text":text,
            "typed_context":ctx,"typed_context_sha256":typed_context_sha256(ctx)}


def _goal(inp="canonical/tmp/case.json",out="canonical/tmp/result.json"):
    return ("Using the controlled typed finance UNLESS case at "+inp+
            ", select and independently verify the applicable branch and save it to "+out+".")


def _write(root:Path,case):
    q=root/"canonical/tmp/case.json"; q.parent.mkdir(parents=True,exist_ok=True)
    q.write_text(json.dumps(case),encoding="utf-8"); return q


def test_bool_true_and_false(tmp_path:Path):
    q=_write(tmp_path,_case(value=True))
    o=d.run({"task_id":"t","goal":_goal()},repo_root=tmp_path)
    assert o["pass"] is True and o["condition_holds"] is True and o["selected_branch"]=="EXCEPTION_BRANCH"
    q.write_text(json.dumps(_case(value=False)))
    o=d.run({"task_id":"f","goal":_goal()},repo_root=tmp_path)
    assert o["pass"] is True and o["condition_holds"] is False and o["selected_branch"]=="ORDINARY_BRANCH"


def test_decimal_minimum_boundary_and_below(tmp_path:Path):
    ctx={"schema_id":"FINANCE_TYPED_CONTEXT_V1","fields":{"exposure":{"type":"DECIMAL_STRING","value":"125.50"}}}
    c={"schema":p.INPUT_SCHEMA,"source_id":"s","source_text":"Apply Rule A unless exposure is at least 125.50.",
       "typed_context":ctx,"typed_context_sha256":typed_context_sha256(ctx)}
    q=_write(tmp_path,c)
    o=d.run({"task_id":"eq","goal":_goal()},repo_root=tmp_path)
    assert o["pass"] is True and o["condition_holds"] is True and o["operator"]=="DECIMAL_GE"
    ctx["fields"]["exposure"]["value"]="125.49"; c["typed_context_sha256"]=typed_context_sha256(ctx)
    q.write_text(json.dumps(c))
    o=d.run({"task_id":"lo","goal":_goal()},repo_root=tmp_path)
    assert o["pass"] is True and o["condition_holds"] is False


def test_wrong_digest_and_missing_field_fail_closed(tmp_path:Path):
    c=_case(); c["typed_context_sha256"]="0"*64
    _write(tmp_path,c)
    assert d.preflight({"task_id":"x","goal":_goal()},repo_root=tmp_path)["status"]=="FAIL_CLOSED"
    c=_case(); c["typed_context"]["fields"]={"other":{"type":"BOOL","value":True}}
    c["typed_context_sha256"]=typed_context_sha256(c["typed_context"])
    _write(tmp_path,c)
    assert d.preflight({"task_id":"y","goal":_goal()},repo_root=tmp_path)["status"]=="FAIL_CLOSED"


def test_uncontrolled_language_not_admitted(tmp_path:Path):
    c=_case(text="Apply Rule A unless the customer qualifies under the material exception.")
    _write(tmp_path,c)
    assert d.preflight({"task_id":"u","goal":_goal()},repo_root=tmp_path)["status"]=="FAIL_CLOSED"


def test_postwrite_verifier_failure_rolls_back(monkeypatch,tmp_path:Path):
    _write(tmp_path,_case())
    op=tmp_path/"canonical/tmp/result.json"; op.write_text('{"old":true}\n'); old=op.read_bytes()
    original=d.verifier.verify; calls={"n":0}
    def injected(c,r):
        calls["n"]+=1
        if calls["n"]==1: return original(c,r)
        return {"verified":False,"producer_independent":True,"model_dependency_count":0,"errors":["forced"]}
    monkeypatch.setattr(d.verifier,"verify",injected)
    o=d.run({"task_id":"r","goal":_goal()},repo_root=tmp_path)
    assert o["pass"] is False and o["rollback_complete"] is True and op.read_bytes()==old


def test_nonmatching_goal_no_claim(tmp_path:Path):
    o=d.preflight({"task_id":"n","goal":"Analyze finance."},repo_root=tmp_path)
    assert o["matched"] is False and o["pass"] is False
