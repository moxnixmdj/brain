import json,pathlib,tempfile,hashlib
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime import goal_dependency_delta_v4 as delta
from canonical.runtime.p3_real_context_v3_admission_v7 import evaluate
from canonical.runtime.synthesis_certified_visible_support_policy_v3 import INPUT_SCHEMA
from canonical.tests.test_p3_membership_frontdoor_v6 import base,req,ev

def dep_case(root):
 claims=[{"claim_id":"REQ","text":"Company revenue is 10.","required":True},{"claim_id":"OPT_REL","text":"Company margin is 20.","required":False},{"claim_id":"OPT_IRR","text":"Office wall color is blue.","required":False}]
 evidence=[{"evidence_id":"E1","text":"Report states Company revenue is 10.","verified":True,"provenance":[{"source_id":"E1","locator":"p"}]},{"evidence_id":"E2","text":"Report states Company margin is 20.","verified":True,"provenance":[{"source_id":"E2","locator":"p"}]},{"evidence_id":"E3","text":"Report states Office wall color is blue.","verified":True,"provenance":[{"source_id":"E3","locator":"p"}]}]
 public={"schema":INPUT_SCHEMA,"task":{"claims":claims,"evidence":evidence,"audience_profile":{"profile_id":"EXPLICIT","constraints":{"output_format":"BULLETS","citation_mode":"INLINE_SOURCE_IDS","style":"VERBATIM_GROUNDED","required_sections":[],"allowed_sections":None,"max_items":5,"max_chars":5000,"heading_level":2,"require_title":False}},"required_uncertainty_units":[]}}
 deps={"GOAL":["REQ","OPT_REL"],"REQ":[],"OPT_REL":[],"OPT_IRR":[]}
 ids=[x["claim_id"] for x in claims]
 rec={"receipt_id":"dep","independent_verified":True,"exact_byte_bound":True,"conclusion":"success","decision_relevant_dependency_graph_complete":True,"environment_id":"p3","goal_id":"summarize","dependency_graph_sha256":delta.dependency_digest(goals=["GOAL"],dependencies=deps),"claim_id_set_sha256":"sha256:"+hashlib.sha256(json.dumps(sorted(ids),separators=(",",":")).encode()).hexdigest()}
 p=root/"canonical/verification/r.json";p.parent.mkdir(parents=True);raw=json.dumps(rec,sort_keys=True,separators=(",",":")).encode();p.write_bytes(raw)
 return {"v3_input":public,"decision_dependency_contract":{"environment_id":"p3","goal_id":"summarize","goal_nodes":["GOAL"],"dependencies":deps,"dependency_verification_ref":{"path":"canonical/verification/r.json","git_blob_sha":git_blob_id(raw,object_format="sha1")}}}

def test_dependency_fallback():
 with tempfile.TemporaryDirectory() as td:
  out=evaluate(dep_case(pathlib.Path(td)),repo_root=td)
  assert out["pass"],out
  assert out["route"]=="EXACT_COMPLETE_DECISION_DEPENDENCY_RELEVANCE_CELL_V1"
  assert out["relevance_bits"]=={"OPT_REL":"RELEVANT","OPT_IRR":"IRRELEVANT"}

def test_v6_membership_route_preserved():
 out=evaluate({"context_id":"x","v3_input":base([req("A","Asset category is in {equity, bond}.")],[ev("E","Report states Asset category is equity.")])})
 assert out["pass"],out
 assert out["v6_preserved_positive_route"] is True

def test_authority_zero():
 with tempfile.TemporaryDirectory() as td:
  out=evaluate(dep_case(pathlib.Path(td)),repo_root=td)
  assert out["pass"] and out["terminal_authority"] is False and out["u_subtraction_authority"] is False and out["terminal_credit_delta"]==0
