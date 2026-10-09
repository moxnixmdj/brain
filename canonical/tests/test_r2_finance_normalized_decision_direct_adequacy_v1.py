from __future__ import annotations
import hashlib,json
from pathlib import Path
from canonical.runtime import r2_finance_normalized_decision_direct_adequacy_v1 as d

def _dump(p:Path,x):
 raw=(json.dumps(x,indent=2,sort_keys=True)+"\n").encode(); p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(raw); return raw

def _blob(raw): return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _problem(extra=False):
 e=[
  {"id":"rule","alternative":"APPLY","relation":"SUPPORTS","confidence":1.0,"strength":1.0,"independence_group":"g1","claim":"rule","provenance":[{"source":"pkg","ref":"r"}]},
  {"id":"exception","alternative":"APPLY","relation":"SUPPORTS","confidence":1.0,"strength":1.0,"independence_group":"g2","claim":"exception","provenance":[{"source":"pkg","ref":"e"}]},
 ]
 if extra:e.append({"id":"extra","alternative":"APPLY","relation":"SUPPORTS","confidence":1.0,"strength":1.0,"independence_group":"g3","claim":"extra","provenance":[{"source":"bad","ref":"x"}]})
 return {"schema":"PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1","decision_id":"f1","question":"Which policy?","alternatives":[{"id":"APPLY","label":"Apply"},{"id":"ABSTAIN","label":"Abstain"}],"constraints":[],"evidence":e,"policy":{"minimum_support_ratio":0.6,"maximum_conflict_ratio":0.5,"minimum_independent_support_groups":1,"minimum_net_margin":0.1}}

def _goal():
 return "Using the authorized normalized finance decision package at canonical/tmp/pkg.json, synthesize the verified finance decision and save it to canonical/tmp/out.json."

def _fixture(root:Path,extra=False):
 dp="canonical/tmp/decision.json"; pp="canonical/tmp/pkg.json"; ap="canonical/tmp/auth.json"; vp="canonical/tmp/verify.json"
 draw=_dump(root/dp,_problem(extra))
 pkg={"schema":d.PACKAGE_SCHEMA,"package_id":"p1","leaf_id":d.SUP,"decision_problem_path":dp,"decision_problem_sha256":hashlib.sha256(draw).hexdigest(),"source_items":[{"id":"r","role":"RULE","evidence_ids":["rule"]},{"id":"e","role":"EXCEPTION","evidence_ids":["exception"]}],"reconciliation_checks":[{"id":"r1","lhs":"10.00","rhs":"10.0","tolerance":"0"}],"authorization_binding":{"authority_path":ap,"verification_path":vp}}
 praw=_dump(root/pp,pkg); psha=hashlib.sha256(praw).hexdigest()
 auth={"schema":d.AUTHORITY_SCHEMA,"status":"ACTIVE","package_path":pp,"package_sha256":psha,"leaf_ids":[d.SUP],"complete_source_universe":True,"normalized_semantics_authoritative":True}
 araw=_dump(root/ap,auth)
 ver={"schema":d.VERIFY_SCHEMA,"pass":True,"subject_git_blob_sha":_blob(araw),"package_sha256":psha,"verified_leaf_ids":[d.SUP],"complete_source_universe_verified":True,"normalized_semantics_authoritative_verified":True}
 _dump(root/vp,ver)

def test_preflight_binds_authorized_complete_package(tmp_path:Path):
 _fixture(tmp_path); x=d.preflight({"task_id":"t","goal":_goal()},repo_root=tmp_path)
 assert x["matched"] is True and x["status"]=="DIRECT_ADEQUACY_ROUTE_MATCHED",x
 assert x["source_evidence_ids"]==["exception","rule"]

def test_run_verifies_decision_and_complete_source_contribution(tmp_path:Path):
 _fixture(tmp_path); x=d.run({"task_id":"t","goal":_goal()},repo_root=tmp_path)
 assert x["pass"] is True,x
 assert x["semantic_acceptance_complete"] is True
 assert x["complete_source_to_contributing_evidence_coverage"] is True
 out=json.loads((tmp_path/"canonical/tmp/out.json").read_text())
 assert out["status"]=="DECIDED" and out["selected_alternative"]=="APPLY"

def test_unbound_decision_evidence_fails_closed(tmp_path:Path):
 _fixture(tmp_path,extra=True); x=d.preflight({"task_id":"t","goal":_goal()},repo_root=tmp_path)
 assert x["pass"] is False and "SOURCE_TO_DECISION_EVIDENCE_DOMAIN_MISMATCH" in x["reason"]

def test_authority_tamper_fails_closed(tmp_path:Path):
 _fixture(tmp_path); p=tmp_path/"canonical/tmp/auth.json"; x=json.loads(p.read_text()); x["complete_source_universe"]=False; _dump(p,x)
 out=d.preflight({"task_id":"t","goal":_goal()},repo_root=tmp_path)
 assert out["pass"] is False

def test_nonmatching_goal_claims_no_scope(tmp_path:Path):
 x=d.preflight({"task_id":"t","goal":"Analyze finance."},repo_root=tmp_path)
 assert x["matched"] is False and x["pass"] is False
