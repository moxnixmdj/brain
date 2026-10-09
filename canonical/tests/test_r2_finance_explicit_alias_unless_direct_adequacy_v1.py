from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime import r2_finance_explicit_alias_unless_direct_adequacy_v1 as d
from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256

def _ctx(value=True):
 c={"schema_id":"FINANCE_TYPED_CONTEXT_V1","fields":{"breach":{"type":"BOOL","value":value}}}
 return c,typed_context_sha256(c)

def _case(op="refers to",value=True):
 c,h=_ctx(value)
 return {"schema":"PROJECT_BRAIN_FINANCE_EXPLICIT_ALIAS_UNLESS_CASE_V1",
 "source_id":"alias-case","source_text":f"Exception B {op} breach is true. Apply Rule A unless Exception B.",
 "typed_context":c,"typed_context_sha256":h}

def _goal():
 return "Using the explicit-alias typed finance UNLESS case at canonical/tmp/alias.json, select and independently verify the applicable branch and save it to canonical/tmp/out.json."

def _write(root,case):
 p=root/"canonical/tmp/alias.json";p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(case));return p

def test_refers_to_true(tmp_path:Path):
 _write(tmp_path,_case("refers to",True)); out=d.run({"task_id":"a1","goal":_goal()},repo_root=tmp_path)
 assert out["pass"] is True,out
 assert out["definition_operator"]=="REFERS_TO"
 assert out["selected_branch"]=="EXCEPTION_BRANCH"
 assert out["acceptance_receipt"]["producer_independent"] is True

def test_is_defined_as_false(tmp_path:Path):
 _write(tmp_path,_case("is defined as",False)); out=d.run({"task_id":"a2","goal":_goal()},repo_root=tmp_path)
 assert out["pass"] is True,out
 assert out["definition_operator"]=="IS_DEFINED_AS"
 assert out["selected_branch"]=="ORDINARY_BRANCH"

def test_means_is_disjoint_and_fails_closed(tmp_path:Path):
 _write(tmp_path,_case("means",True)); out=d.preflight({"task_id":"a3","goal":_goal()},repo_root=tmp_path)
 assert out["matched"] is True and out["status"]=="FAIL_CLOSED"

def test_implicit_synonym_not_admitted(tmp_path:Path):
 case=_case("refers to",True);case["source_text"]="Exception B concerns breach. Apply Rule A unless Exception B."
 _write(tmp_path,case);out=d.preflight({"task_id":"a4","goal":_goal()},repo_root=tmp_path)
 assert out["matched"] is True and out["status"]=="FAIL_CLOSED"

def test_reference_mismatch_fails_closed(tmp_path:Path):
 case=_case();case["source_text"]="Exception B refers to breach is true. Apply Rule A unless Exception C."
 _write(tmp_path,case);out=d.preflight({"task_id":"a5","goal":_goal()},repo_root=tmp_path)
 assert out["status"]=="FAIL_CLOSED"

def test_preflight_side_effect_free(tmp_path:Path):
 _write(tmp_path,_case());out=d.preflight({"task_id":"a6","goal":_goal()},repo_root=tmp_path)
 assert out["status"]=="DIRECT_ADEQUACY_ROUTE_MATCHED"
 assert not (tmp_path/"canonical/tmp/out.json").exists()

def test_typed_context_digest_mismatch_fails_closed(tmp_path:Path):
 case=_case();case["typed_context_sha256"]="0"*64;_write(tmp_path,case)
 assert d.preflight({"task_id":"a7","goal":_goal()},repo_root=tmp_path)["status"]=="FAIL_CLOSED"

def test_extra_sentence_fails_closed(tmp_path:Path):
 case=_case();case["source_text"]="Exception B refers to breach is true. Background. Apply Rule A unless Exception B."
 _write(tmp_path,case)
 assert d.preflight({"task_id":"a8","goal":_goal()},repo_root=tmp_path)["status"]=="FAIL_CLOSED"

def test_verifier_tamper_detected(tmp_path:Path):
 from canonical.runtime import finance_explicit_alias_unless_branch_v1 as p
 from canonical.runtime import finance_explicit_alias_unless_verify_v1 as v
 case=_case();res=p.compute(case);res["selected_branch"]="ORDINARY_BRANCH"
 assert v.verify(case,res)["verified"] is False

def test_nonmatching_goal_claims_no_scope(tmp_path:Path):
 out=d.preflight({"task_id":"a10","goal":"Analyze this finance alias."},repo_root=tmp_path)
 assert out["matched"] is False and out["pass"] is False
