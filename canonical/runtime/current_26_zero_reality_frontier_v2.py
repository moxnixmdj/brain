from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_CURRENT_26_ZERO_REALITY_FRONTIER_REDUCER_V2"
REG="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
EVID="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
OLD="canonical/governance/CURRENT_27_ZERO_REALITY_FRONTIER_V2.json"
CERT="canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"
MATCHED="canonical/governance/MATCHED_SCOPE_ABDUCTIVE_RESIDUAL_INPUT_V2.json"
TD="canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_PROMOTION_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
TN="canonical/verification/OPUS55_MATCHED_TARGET_NORMALIZATION_V3_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
WN="canonical/verification/OPUS55_BRAIN_WITNESS_NORMALIZATION_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
SG="canonical/verification/DUAL_JUDGMENT_SOURCE_GATE_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
EXPECTED={
REG:"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",EVID:"bc420c6d1a6caaab7a6d5c257640d3f5797170f5",
OLD:"bab3876a1c4bd6a065d20d42b320df4b4b3fa519",CERT:"4b5517dbd12978f8ffe481fb775e85592c7790c8",
MATCHED:"438e2775b64bee5ed6e792522ab35ebd0d6e1771",TD:"bed23f2e69d4bc8937d792b07b5812364cf26a85",
TN:"b5192b1903dc603e75efe92b9a00ced0b2722f8c",WN:"0488df0f1c13ace2b25695c48ff65d4654f9c3e2",
SG:"6ec5f6d808c88bf9ea728fb7f259edc3b4ae5a51"}
MATCHED_PARENT={"MATCHED_BRAIN_WITNESS_TARGET_ATOM_METRIC_BINDINGS_INDEPENDENT_PASS","MATCHED_BRAIN_WITNESS_SCOPE_RELATIONS_INDEPENDENT_PASS"}
DIRECT={"FINANCE_UNCOVERED_SCOPE_AUDIT","UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"}

def blob(p):
 b=(ROOT/p).read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((ROOT/p).read_text())
def evaluate():
 drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
 if drift:return {"schema":SCHEMA,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","pass":False,"errors":["SOURCE_BLOB_DRIFT"],"drift":drift,"execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False}
 reg,evid,old,cert,matched,td,tn,wn,sg=map(load,[REG,EVID,OLD,CERT,MATCHED,TD,TN,WN,SG])
 errors=[]
 proved={x.get("predicate_id") for x in evid.get("claims",[]) if isinstance(x,Mapping) and x.get("state")=="PROVED"}
 predicates=[x.get("id") for x in reg.get("predicates",[]) if isinstance(x,Mapping) and isinstance(x.get("id"),str)]
 unresolved=set(predicates)-proved
 if (len(predicates),len(proved),len(unresolved))!=(38,12,26):errors.append("ATOMIC_COUNTS_DRIFT")
 if "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR" not in proved:errors.append("TOOL_DISCOVERY_NOT_PROVED")
 for name,doc in [("TD",td),("TN",tn),("WN",wn),("SG",sg)]:
  if not str(doc.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):errors.append(name+"_NOT_INDEPENDENT_PASS")
 if (tn.get("verified") or {}).get("live_target_count")!=8:errors.append("TARGET_NORMALIZATION_COUNT_NOT_8")
 if (wn.get("verified") or {}).get("witness_count")!=12:errors.append("WITNESS_NORMALIZATION_COUNT_NOT_12")
 sgver=sg.get("verified") or {}
 if sgver.get("finance_source_admitted") is not True or sgver.get("unknown_domain_source_admitted") is not True:errors.append("DIRECT_SOURCE_GATE_NOT_ADMITTED")
 if sgver.get("global_fresh_reality_authority") is not False:errors.append("FRESH_REALITY_OVERCLAIM")
 oldids=set(old.get("active_nondominated_certificate_ids") or [])
 active=[x for x in cert.get("certificates",[]) if isinstance(x,Mapping) and x.get("id") in oldids and any(t in unresolved for t in x.get("target_predicates",[]))]
 ids=sorted(x["id"] for x in active)
 reqs=sorted({r for x in active for r in x.get("requires",[]) if isinstance(r,str)})
 covered=sorted({t for x in active for t in x.get("target_predicates",[]) if t in unresolved})
 if (len(ids),len(reqs),len(covered))!=(13,16,24):errors.append("ZERO_REALITY_FRONTIER_COUNTS_DRIFT")
 if set(unresolved)-set(covered)!=DIRECT:errors.append("DIRECT_RESIDUAL_SET_DRIFT")
 tdreq="INDEPENDENT_EXACT_COMPLETE_TARGET_CASE_UNIVERSE_OR_EXHAUSTIVE_FINITE_SUPERSET_OR_UNIVERSAL_FORMAL_SCOPE_PROOF_FOR_TOOL_DISCOVERY_PROTOCOL"
 if "TOOL_DISCOVERY_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE" in ids or tdreq in reqs:errors.append("STALE_TOOL_DISCOVERY_WORK_RETAINED")
 implications=[x for x in matched.get("implications",[]) if isinstance(x,Mapping) and x.get("verified") is True and x.get("independent") is True]
 child=sorted({f for x in implications for f in x.get("if_all",[]) if isinstance(f,str)})
 targets=sorted({t for x in implications for t in x.get("then",[]) if isinstance(t,str)})
 if (len(child),len(targets))!=(16,8):errors.append("MATCHED_RESIDUAL_COUNTS_DRIFT")
 if not MATCHED_PARENT.issubset(reqs):errors.append("MATCHED_PARENT_REQUIREMENTS_MISSING")
 primitive=len(reqs)-2+len(child)
 if primitive!=30:errors.append("PRIMITIVE_COUNT_NOT_30")
 ok=not errors
 return {"schema":SCHEMA,"status":"PASS__CURRENT_26__16_ZERO_REALITY_REQUIREMENTS__13_CERTIFICATES__30_PRIMITIVE_UNITS__2_DIRECT_ELIGIBLE_UNAUTHORIZED__ZERO_CREDIT" if ok else "FAIL_CLOSED","pass":ok,"errors":sorted(set(errors)),
 "live_world":{"registry_predicates":38,"proved_predicates":12,"unresolved_predicates":26,"opus55_acceptance":"5/19_PASS__14/19_OPEN","active_zero_reality_requirements":16,"active_nondominated_certificates":13,"zero_reality_covered_predicates":24,"primitive_zero_reality_work_units":30,"matched_priority_child_facts":16,"current_normalized_targets":8,"current_normalized_witnesses":12,"direct_reality_eligible_predicates":sorted(DIRECT),"direct_reality_execution_authorized_now":False},
 "active_nondominated_certificate_ids":ids,"active_required_propositions":reqs,"zero_reality_covered_predicate_ids":covered,"matched_child_fact_ids":child,
 "next":"PARALLEL_DISCHARGE_30_PRIMITIVE_ZERO_REALITY_UNITS__FIRST_PRIORITY_16_MATCHED_CHILD_FACTS__RECOMPUTE_AFTER_EACH_VERIFIED_DELTA__NO_FRESH_REALITY",
 "new_reality_units_consumed":0,"incremental_spend_usd":0,"acceptance_credit_delta":0,"capability_credit_delta":0,"family_credit_delta":0,"ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False}
if __name__=="__main__":print(json.dumps(evaluate(),indent=2,sort_keys=True))
