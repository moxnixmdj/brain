import json,pathlib,tempfile,hashlib
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime import goal_dependency_delta_v4 as delta
from canonical.runtime.p3_exact_dependency_relevance_cell_v1 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA
ENV="p3"; GOAL="summarize"
def c(): return {"output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS","style":"VERBATIM_GROUNDED","required_sections":[],"allowed_sections":None,"max_items":5,"max_chars":5000,"heading_level":2,"require_title":False}
def e(i,t): return {"evidence_id":i,"text":t,"verified":True,"provenance":[{"source_id":i,"locator":"p"}]}
def public():
 return {"schema":INPUT_SCHEMA,"task":{"claims":[{"claim_id":"REQ","text":"Company revenue is 10.","required":True},{"claim_id":"OPT_REL","text":"Company margin is 20.","required":False},{"claim_id":"OPT_IRR","text":"Office wall color is blue.","required":False}],"evidence":[e("E1","Report states Company revenue is 10."),e("E2","Report states Company margin is 20."),e("E3","Report states Office wall color is blue.")],"audience_profile":{"profile_id":"EXPLICIT","constraints":c()},"required_uncertainty_units":[]}}
def deps(): return {"GOAL":["REQ","OPT_REL"],"REQ":[],"OPT_REL":[],"OPT_IRR":[]}
def run(change=None):
 with tempfile.TemporaryDirectory() as td:
  root=pathlib.Path(td); p=root/"canonical/verification/r.json"; p.parent.mkdir(parents=True)
  ids=["REQ","OPT_REL","OPT_IRR"]
  rec={"receipt_id":"dep","independent_verified":True,"exact_byte_bound":True,"conclusion":"success","decision_relevant_dependency_graph_complete":True,"environment_id":ENV,"goal_id":GOAL,"dependency_graph_sha256":delta.dependency_digest(goals=["GOAL"],dependencies=deps()),"claim_id_set_sha256":"sha256:"+hashlib.sha256(json.dumps(sorted(ids),separators=(",",":")).encode()).hexdigest()}
  if change: change(rec)
  raw=json.dumps(rec,sort_keys=True,separators=(",",":")).encode(); p.write_bytes(raw)
  ref={"path":"canonical/verification/r.json","git_blob_sha":git_blob_id(raw,object_format="sha1")}
  return evaluate({"v3_input":public(),"decision_dependency_contract":{"environment_id":ENV,"goal_id":GOAL,"goal_nodes":["GOAL"],"dependencies":deps(),"dependency_verification_ref":ref}},repo_root=root)
def test_split():
 o=run(); assert o["pass"]; assert o["relevance_bits"]=={"OPT_REL":"RELEVANT","OPT_IRR":"IRRELEVANT"}; assert "Office wall color is blue." not in o["rendered_text"]
def test_incomplete():
 o=run(lambda r:r.__setitem__("decision_relevant_dependency_graph_complete",False)); assert o["reason"]=="DECISION_RELEVANT_GRAPH_COMPLETENESS_UNPROVED"
def test_digest():
 o=run(lambda r:r.__setitem__("dependency_graph_sha256","bad")); assert o["reason"]=="DEPENDENCY_GRAPH_DIGEST_MISMATCH"
def test_authority():
 o=run(); assert o["pass"]; assert not o["terminal_authority"] and not o["u_subtraction_authority"] and o["terminal_credit_delta"]==0
