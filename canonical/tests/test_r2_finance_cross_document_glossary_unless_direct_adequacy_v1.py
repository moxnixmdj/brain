from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from canonical.runtime import (
    r2_finance_cross_document_glossary_unless_direct_adequacy_v1 as direct,
)
from canonical.runtime import finance_cross_document_glossary_unless_branch_v1 as producer
from canonical.runtime import finance_cross_document_glossary_unless_verify_v1 as verifier
from canonical.runtime import r2_direct_end_to_end_adequacy_v6 as v6
from canonical.runtime import r2_direct_end_to_end_adequacy_v5 as v5
from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256


def _raw_sha(path:Path)->str:
    return sha256(path.read_bytes()).hexdigest()


def _write(path:Path,obj)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,sort_keys=True),encoding="utf-8")


def _goal()->str:
    return (
        "Using the cross-document glossary finance UNLESS case at "
        "canonical/tmp/case.json, select and independently verify the applicable "
        "branch and save it to canonical/tmp/out.json."
    )


def _fixture(root:Path,*,value=True,term="Exception B",definition="breach is true"):
    base=root/"canonical/tmp"
    rule={
        "schema":"PROJECT_BRAIN_FINANCE_RULE_DOCUMENT_V1",
        "document_id":"rule-doc-1",
        "rule_text":f"Apply Rule A unless {term}.",
    }
    glossary={
        "schema":"PROJECT_BRAIN_FINANCE_GLOSSARY_DOCUMENT_V1",
        "document_id":"glossary-doc-1",
        "entries":[{"term":term,"definition":definition}],
    }
    ctx={
        "schema_id":"FINANCE_TYPED_CONTEXT_V1",
        "fields":{"breach":{"type":"BOOL","value":value}},
    }
    rp=base/"rule.json"; gp=base/"glossary.json"
    _write(rp,rule); _write(gp,glossary)
    case={
        "schema":"PROJECT_BRAIN_FINANCE_CROSS_DOCUMENT_GLOSSARY_UNLESS_CASE_V1",
        "source_id":"finance-cross-glossary-case",
        "rule_document_path":"canonical/tmp/rule.json",
        "rule_document_sha256":_raw_sha(rp),
        "rule_document_id":"rule-doc-1",
        "glossary_document_path":"canonical/tmp/glossary.json",
        "glossary_document_sha256":_raw_sha(gp),
        "glossary_document_id":"glossary-doc-1",
        "typed_context":ctx,
        "typed_context_sha256":typed_context_sha256(ctx),
    }
    cp=base/"case.json"; _write(cp,case)
    return case,rule,glossary


def test_true_condition_selects_exception_branch(tmp_path:Path):
    _fixture(tmp_path,value=True)
    out=direct.run({"task_id":"g1","goal":_goal()},repo_root=tmp_path)
    assert out["pass"] is True,out
    assert out["selected_branch"]=="EXCEPTION_BRANCH"
    assert out["glossary_term"]=="Exception B"
    assert out["acceptance_receipt"]["producer_independent"] is True
    assert out["actual_goal_satisfaction_verified"] is True


def test_false_condition_selects_ordinary_branch(tmp_path:Path):
    _fixture(tmp_path,value=False)
    out=direct.run({"task_id":"g2","goal":_goal()},repo_root=tmp_path)
    assert out["pass"] is True,out
    assert out["selected_branch"]=="ORDINARY_BRANCH"


def test_rule_reference_must_match_glossary_term(tmp_path:Path):
    case,rule,glossary=_fixture(tmp_path)
    rule["rule_text"]="Apply Rule A unless Exception C."
    _write(tmp_path/"canonical/tmp/rule.json",rule)
    case["rule_document_sha256"]=_raw_sha(tmp_path/"canonical/tmp/rule.json")
    _write(tmp_path/"canonical/tmp/case.json",case)
    out=direct.preflight({"task_id":"g3","goal":_goal()},repo_root=tmp_path)
    assert out["status"]=="FAIL_CLOSED"
    assert "GLOSSARY_TERM_REFERENCE_MISMATCH" in out["reason"]


def test_rule_content_address_drift_fails_closed(tmp_path:Path):
    _fixture(tmp_path)
    rp=tmp_path/"canonical/tmp/rule.json"
    row=json.loads(rp.read_text())
    row["rule_text"]="Apply Rule X unless Exception B."
    _write(rp,row)
    out=direct.preflight({"task_id":"g4","goal":_goal()},repo_root=tmp_path)
    assert out["status"]=="FAIL_CLOSED"
    assert "RULE_DOCUMENT_CONTENT_ADDRESS_MISMATCH" in out["reason"]


def test_glossary_content_address_drift_fails_closed(tmp_path:Path):
    _fixture(tmp_path)
    gp=tmp_path/"canonical/tmp/glossary.json"
    row=json.loads(gp.read_text())
    row["entries"][0]["definition"]="breach is false"
    _write(gp,row)
    out=direct.preflight({"task_id":"g5","goal":_goal()},repo_root=tmp_path)
    assert out["status"]=="FAIL_CLOSED"
    assert "GLOSSARY_DOCUMENT_CONTENT_ADDRESS_MISMATCH" in out["reason"]


def test_unsupported_glossary_definition_fails_closed(tmp_path:Path):
    _fixture(tmp_path,definition="breach probably applies")
    out=direct.preflight({"task_id":"g6","goal":_goal()},repo_root=tmp_path)
    assert out["status"]=="FAIL_CLOSED"
    assert "GLOSSARY_CONDITION_NOT_PROVED" in out["reason"] or "OUTSIDE_TYPED_GRAMMAR" in out["reason"]


def test_exactly_one_glossary_entry_required(tmp_path:Path):
    case,rule,glossary=_fixture(tmp_path)
    glossary["entries"].append({"term":"Exception C","definition":"breach is false"})
    _write(tmp_path/"canonical/tmp/glossary.json",glossary)
    case["glossary_document_sha256"]=_raw_sha(tmp_path/"canonical/tmp/glossary.json")
    _write(tmp_path/"canonical/tmp/case.json",case)
    out=direct.preflight({"task_id":"g7","goal":_goal()},repo_root=tmp_path)
    assert out["status"]=="FAIL_CLOSED"
    assert "EXACTLY_ONE_GLOSSARY_ENTRY_REQUIRED" in out["reason"]


def test_preflight_is_side_effect_free(tmp_path:Path):
    _fixture(tmp_path)
    out=direct.preflight({"task_id":"g8","goal":_goal()},repo_root=tmp_path)
    assert out["status"]=="DIRECT_ADEQUACY_ROUTE_MATCHED",out
    assert not (tmp_path/"canonical/tmp/out.json").exists()


def test_independent_verifier_detects_branch_tamper(tmp_path:Path):
    case,rule,glossary=_fixture(tmp_path,value=True)
    result=producer.compute(case,rule,glossary)
    result["selected_branch"]="ORDINARY_BRANCH"
    checked=verifier.verify(case,rule,glossary,result)
    assert checked["verified"] is False
    assert "MISMATCH:selected_branch" in checked["errors"]


def test_output_rollback_on_postwrite_verifier_failure(monkeypatch,tmp_path:Path):
    _fixture(tmp_path)
    op=tmp_path/"canonical/tmp/out.json"
    op.write_text('{"old":true}\n',encoding="utf-8")
    old=op.read_bytes()
    original=direct.verifier.verify
    calls={"n":0}
    def injected(case,rule_doc,glossary_doc,result):
        calls["n"]+=1
        if calls["n"]<3:
            return original(case,rule_doc,glossary_doc,result)
        return {
            "verified":False,"errors":["forced"],"producer_independent":True,
            "model_dependency_count":0,
        }
    monkeypatch.setattr(direct.verifier,"verify",injected)
    out=direct.run({"task_id":"g9","goal":_goal()},repo_root=tmp_path)
    assert out["pass"] is False,out
    assert out["rollback_complete"] is True
    assert op.read_bytes()==old


def test_nonmatching_goal_claims_no_scope(tmp_path:Path):
    out=direct.preflight(
        {"task_id":"g10","goal":"Analyze this finance glossary."},
        repo_root=tmp_path,
    )
    assert out["matched"] is False
    assert out["pass"] is False


def test_v6_nonmatching_preflight_delegates_exactly_to_v5(tmp_path:Path):
    req={"task_id":"fallback","goal":"Analyze this finance glossary."}
    assert v6.preflight(req,repo_root=tmp_path)==v5.preflight(req,repo_root=tmp_path)


def test_v6_nonmatching_run_delegates_exactly_to_v5(tmp_path:Path):
    req={"task_id":"fallback-run","goal":"Analyze this finance glossary."}
    assert v6.run(req,repo_root=tmp_path)==v5.run(req,repo_root=tmp_path)


def test_v6_new_route_executes(tmp_path:Path):
    _fixture(tmp_path)
    out=v6.run({"task_id":"g11","goal":_goal()},repo_root=tmp_path)
    assert out["pass"] is True,out
    assert out["route_id"]==direct.ROUTE_ID
