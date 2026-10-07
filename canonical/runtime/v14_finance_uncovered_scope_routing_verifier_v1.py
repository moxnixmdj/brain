from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
GOV="canonical/governance/V14_FINANCE_UNCOVERED_SCOPE_ROUTING_TRUTH_REPAIR_20261007_V1.json"
SOURCES={
"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json":"d9bd211b2557ac45331f6fe0c4347392f4cd7a95",
"canonical/governance/MAXIMAL_CONTEXT_LAW_SPACE_COMPLETENESS_THEOREM_20261007_V1.json":"54f5495fc7a6990400bc9195b15be895b75c62d0",
"canonical/runtime/terminal_frontier_factorizer_v6_candidate.py":"325113ade6a21cd271c9a279f1cdad4a4f7697f7",
"canonical/governance/FINANCE_UNCOVERED_SCOPE_DIRECT_PROOF_PROTOCOL_V1.json":"84973ca473cbb8f6160b45c025567c56f8a3d4ba",
"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json":"62394e5b7d221ec9f69c3458f669e40e253a9d09"}
FIN="FINANCE_UNCOVERED_SCOPE_AUDIT"
LEGACY_STRUCTURAL={"AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION","VISION_DENSE_NONCHART_SCOPE","AGENCY_MATCHED_SUCCESS_NONINFERIOR","IF_SCOPE_BOUNDARY_NONINFERIOR"}

def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def route_sets():
 ns={}; exec((ROOT/"canonical/runtime/terminal_frontier_factorizer_v6_candidate.py").read_text(),ns)
 atomic=set(ns["ATOMIC"]); ext=set(ns["EXTERNAL_RESULT_ATOMS"])
 targetlike=ext-{FIN}; objective=atomic-targetlike
 return atomic,ext,targetlike,objective

def verify():
 e=[]
 for p,w in SOURCES.items():
  q=ROOT/p
  if not q.is_file(): e.append("SOURCE_MISSING:"+p)
  elif blob(q.read_bytes())!=w: e.append("SOURCE_DRIFT:"+p)
 v14=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json")
 maxk=load("canonical/governance/MAXIMAL_CONTEXT_LAW_SPACE_COMPLETENESS_THEOREM_20261007_V1.json")
 fin=load("canonical/governance/FINANCE_UNCOVERED_SCOPE_DIRECT_PROOF_PROTOCOL_V1.json")
 protocols=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
 gov=load(GOV)
 atomic,ext,targetlike,objective=route_sets()
 if len(atomic)!=19 or len(ext)!=15: e.append("LEGACY_COUNT_DRIFT")
 if FIN not in ext or FIN in targetlike: e.append("FINANCE_ROUTING_NOT_REPAIRED")
 if len(targetlike)!=14 or len(objective)!=5 or objective!=LEGACY_STRUCTURAL|{FIN}: e.append("REPAIRED_SET_DRIFT")
 if (v14.get("abc_normal_form") or {}).get("context_law_coverage",{}).get("default")!="K_c_EQUALS_L_c": e.append("V14_MAXIMAL_LAW_DEFAULT_DRIFT")
 qrule=(v14.get("abc_normal_form") or {}).get("target_law_information",{}).get("query_rule","")
 if "LAST" not in (v14.get("abc_normal_form") or {}).get("target_law_information",{}).get("state",""): e.append("V14_TARGET_INFO_NOT_LAST_RESORT")
 if "SURVIVING_UNDOMINATED_LAW" not in qrule: e.append("V14_QUERY_RULE_DRIFT")
 sched=set(maxk.get("scheduler_effect") or [])
 if "FIRST_TEST_OR_PROVE_TOP_ELEMENT_BRAIN_DOMINANCE_ON_L_c." not in sched: e.append("TOP_FIRST_RULE_MISSING")
 adm=fin.get("candidate_admission") or {}
 if "BRAIN_OWNED" not in str(adm.get("rule","")) or "OPAQUE_EXTERNAL_FINANCIAL_ANALYSIS_PROVIDER_IS_SPECIMEN_ONLY" not in str(adm.get("rule","")): e.append("FINANCE_OWNERSHIP_RULE_DRIFT")
 leaves=fin.get("leaves") or []
 if {x.get("id") for x in leaves}!={"SUPERVISORY_AND_COMPLIANCE_NUANCE_OUTSIDE_PUBLIC_BAR_SCOPE","DOCUMENT_SPECIFIC_ANALYSIS_LEAVES_OUTSIDE_PUBLIC_BAR_SCOPE"}: e.append("FINANCE_LEAF_SET_DRIFT")
 if any("OPUS" in json.dumps(x).upper() for x in leaves): e.append("FINANCE_LEAF_OPUS_DEPENDENCY")
 fp=[p for p in protocols.get("protocols",[]) if p.get("family")=="FINANCIAL_ANALYSIS"]
 if len(fp)!=1 or not any("structured quantitative-method" in str(x) for x in fp[0].get("acceptance",[])): e.append("FINANCE_TERMINAL_PROTOCOL_DRIFT")
 rr=gov.get("routing_repair") or {}
 if (rr.get("repaired_minimum_counts") or {}).get("benchmark_or_target_relative_result_interfaces")!=14: e.append("GOV_TARGETLIKE_COUNT")
 if (rr.get("repaired_minimum_counts") or {}).get("objective_or_structural_abc_interfaces")!=5: e.append("GOV_OBJECTIVE_COUNT")
 return {"status":"PASS__V14_FINANCE_UNCOVERED_SCOPE_OBJECTIVE_ABC_ROUTE__TARGETLIKE_14_OBJECTIVE_5__ZERO_CREDIT" if not e else "FAIL_CLOSED","pass":not e,"errors":e,"benchmark_or_target_relative_count":len(targetlike),"objective_or_structural_count":len(objective),"terminal_credit_delta":0}
if __name__=="__main__":
 x=verify(); print(json.dumps(x,indent=2,sort_keys=True)); raise SystemExit(0 if x["pass"] else 1)
