from __future__ import annotations
import json
from pathlib import Path
from canonical.runtime import r2_finance_normalized_source_universe_direct_adequacy_v1 as d

def _dump(p:Path,x):
 p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def _e(i,alt="APPLY"):
 return {"id":i,"alternative":alt,"relation":"SUPPORTS","confidence":1.0,"strength":1.0,"independence_group":i,"claim":i,"provenance":[{"source":"normalized-package","ref":i}]}

def _problem(ids):
 return {"schema":"PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1","decision_id":"f1","question":"Which policy?","alternatives":[{"id":"APPLY","label":"Apply"},{"id":"ABSTAIN","label":"Abstain"}],"constraints":[],"evidence":[_e(x) for x in ids],"policy":{"minimum_support_ratio":0.6,"maximum_conflict_ratio":0.5,"minimum_independent_support_groups":1,"minimum_net_margin":0.1}}

def _goal():
 return "Using the complete normalized finance decision package at canonical/tmp/pkg.json, synthesize and independently verify the finance decision and save it to canonical/tmp/out.json."

def _sup():
 return {"schema":d.PACKAGE_SCHEMA,"package_id":"sup1","leaf_id":d.SUP,"decision_problem":_problem(["rule","exception","escalation","disclosure"]),"role_evidence_ids":{"RULE":["rule"],"EXCEPTION":["exception"],"ESCALATION":["escalation"],"DISCLOSURE":["disclosure"]},"reconciliation_checks":[]}

def _doc():
 p=_problem(["fact","xref","contradiction","exception","recon"])
 return {"schema":d.PACKAGE_SCHEMA,"package_id":"doc1","leaf_id":d.DOC,"decision_problem":p,"role_evidence_ids":{"FACT":["fact"],"CROSS_REFERENCE":["xref"],"CONTRADICTION":["contradiction"],"EXCEPTION":["exception"],"RECONCILIATION":["recon"]},"reconciliation_checks":[{"id":"calc1","evidence_id":"recon","lhs":"10.00","rhs":"10","tolerance":"0"}]}

def test_supervisory_package_passes(tmp_path:Path):
 _dump(tmp_path/"canonical/tmp/pkg.json",_sup()); x=d.run({"task_id":"s","goal":_goal()},repo_root=tmp_path)
 assert x["pass"] is True,x
 assert x["finance_role_partition_complete"] is True and x["decision_evidence_coverage_complete"] is True and x["leaf_id"]==d.SUP

def test_document_package_and_reconciliation_pass(tmp_path:Path):
 _dump(tmp_path/"canonical/tmp/pkg.json",_doc()); x=d.run({"task_id":"d","goal":_goal()},repo_root=tmp_path)
 assert x["pass"] is True,x
 assert x["reconciliation_ids"]==["calc1"] and x["leaf_id"]==d.DOC

def test_incomplete_role_partition_fails_closed(tmp_path:Path):
 p=_sup(); p["role_evidence_ids"]["DISCLOSURE"]=[]; _dump(tmp_path/"canonical/tmp/pkg.json",p)
 x=d.preflight({"task_id":"s","goal":_goal()},repo_root=tmp_path); assert x["pass"] is False and "FINANCE_ROLE_PARTITION_NOT_COMPLETE" in x["reason"]

def test_unknown_package_field_fails_closed(tmp_path:Path):
 p=_sup(); p["unmodeled"]="surprise"; _dump(tmp_path/"canonical/tmp/pkg.json",p)
 x=d.preflight({"task_id":"s","goal":_goal()},repo_root=tmp_path); assert x["pass"] is False and "PACKAGE_FIELD_SET_NOT_EXACT" in x["reason"]

def test_failed_reconciliation_fails_closed(tmp_path:Path):
 p=_doc(); p["reconciliation_checks"][0]["rhs"]="11"; _dump(tmp_path/"canonical/tmp/pkg.json",p)
 x=d.preflight({"task_id":"d","goal":_goal()},repo_root=tmp_path); assert x["pass"] is False and "RECONCILIATION_FAILED" in x["reason"]

def test_output_restored_on_post_synthesis_failure(monkeypatch,tmp_path:Path):
 _dump(tmp_path/"canonical/tmp/pkg.json",_sup()); out=tmp_path/"canonical/tmp/out.json"; out.write_text('{"old":true}\n'); old=out.read_bytes()
 monkeypatch.setattr(d.verifier,"verify",lambda problem,result:(False,"forced"))
 x=d.run({"task_id":"s","goal":_goal()},repo_root=tmp_path); assert x["pass"] is False and x["rollback_complete"] is True and out.read_bytes()==old

def test_nonmatching_goal_claims_no_scope(tmp_path:Path):
 x=d.preflight({"task_id":"x","goal":"Analyze finance."},repo_root=tmp_path); assert x["matched"] is False and x["pass"] is False
