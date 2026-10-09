from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from canonical.runtime import r2_finance_cross_document_json_direct_adequacy_v1 as d


def _canon_sha(x):
    return sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()


def _goal():
    return ("Using the cross-document finance JSON case at canonical/tmp/case.json, "
            "select and independently verify the action and save it to canonical/tmp/out.json.")


def _fixture(root:Path,source_value="10.00",target_value="10.0",target_id="note-7"):
    source={"document_id":"statement-1","supporting_document_id":"note-7","net_income":source_value}
    target={"document_id":target_id,"net_income":target_value}
    case={
      "schema":"PROJECT_BRAIN_FINANCE_CROSS_DOCUMENT_JSON_CASE_V1",
      "case_id":"crossdoc-1",
      "source_document_path":"canonical/tmp/source.json",
      "source_document_sha256":_canon_sha(source),
      "target_document_path":"canonical/tmp/target.json",
      "target_document_sha256":_canon_sha(target),
      "source_reference_path":["supporting_document_id"],
      "target_identity_path":["document_id"],
      "source_value_path":["net_income"],
      "target_value_path":["net_income"],
      "action_if_equal":"ACCEPT",
      "action_if_not_equal":"ESCALATE"
    }
    p=root/"canonical/tmp"; p.mkdir(parents=True,exist_ok=True)
    (p/"source.json").write_text(json.dumps(source))
    (p/"target.json").write_text(json.dumps(target))
    (p/"case.json").write_text(json.dumps(case))
    return case


def test_equal_values_select_accept(tmp_path:Path):
    _fixture(tmp_path)
    out=d.run({"task_id":"eq","goal":_goal()},repo_root=tmp_path)
    assert out["pass"] is True,out
    assert out["values_equal"] is True and out["selected_action"]=="ACCEPT"
    assert out["actual_goal_satisfaction_verified"] is True


def test_unequal_values_select_escalate(tmp_path:Path):
    _fixture(tmp_path,target_value="11.00")
    out=d.run({"task_id":"neq","goal":_goal()},repo_root=tmp_path)
    assert out["pass"] is True,out
    assert out["values_equal"] is False and out["selected_action"]=="ESCALATE"


def test_wrong_reference_id_fails_closed(tmp_path:Path):
    _fixture(tmp_path,target_id="note-8")
    out=d.preflight({"task_id":"badref","goal":_goal()},repo_root=tmp_path)
    assert out["status"]=="FAIL_CLOSED"
    assert "CROSS_DOCUMENT_REFERENCE_ID_MISMATCH" in out["reason"]


def test_content_address_drift_fails_closed(tmp_path:Path):
    _fixture(tmp_path)
    p=tmp_path/"canonical/tmp/target.json"
    row=json.loads(p.read_text()); row["net_income"]="99.00"; p.write_text(json.dumps(row))
    out=d.preflight({"task_id":"drift","goal":_goal()},repo_root=tmp_path)
    assert out["status"]=="FAIL_CLOSED"
    assert "TARGET_DOCUMENT_CONTENT_ADDRESS_MISMATCH" in out["reason"]


def test_invalid_decimal_fails_closed(tmp_path:Path):
    _fixture(tmp_path,target_value="10 USD")
    out=d.preflight({"task_id":"decimal","goal":_goal()},repo_root=tmp_path)
    assert out["status"]=="FAIL_CLOSED"
    assert "DECIMAL_STRING_INVALID" in out["reason"]


def test_missing_path_fails_closed(tmp_path:Path):
    case=_fixture(tmp_path)
    case["target_value_path"]=["missing"]
    (tmp_path/"canonical/tmp/case.json").write_text(json.dumps(case))
    out=d.preflight({"task_id":"missing","goal":_goal()},repo_root=tmp_path)
    assert out["status"]=="FAIL_CLOSED"
    assert "JSON_PATH_NOT_FOUND" in out["reason"] or "PATH_NOT_FOUND" in out["reason"]


def test_output_rollback_on_postwrite_verifier_failure(monkeypatch,tmp_path:Path):
    _fixture(tmp_path)
    op=tmp_path/"canonical/tmp/out.json"; op.write_text('{"old":true}\n'); old=op.read_bytes()
    original=d.verifier.verify
    calls={"n":0}
    def injected(case,sd,td,result):
        calls["n"]+=1
        if calls["n"]<3:
            return original(case,sd,td,result)
        return {"verified":False,"errors":["forced"],"producer_independent":True,"model_dependency_count":0}
    monkeypatch.setattr(d.verifier,"verify",injected)
    out=d.run({"task_id":"rollback","goal":_goal()},repo_root=tmp_path)
    assert out["pass"] is False and out["rollback_complete"] is True
    assert op.read_bytes()==old


def test_nonmatching_goal_no_scope(tmp_path:Path):
    out=d.preflight({"task_id":"none","goal":"Analyze these documents."},repo_root=tmp_path)
    assert out["matched"] is False and out["pass"] is False
