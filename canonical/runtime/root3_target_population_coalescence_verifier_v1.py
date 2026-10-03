"""Verify Root3 target-population coalescence against frozen protocol literals."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_ROOT3_TARGET_POPULATION_COALESCENCE_VERIFIER_V1"
CAND="canonical/governance/ROOT3_TARGET_POPULATION_COALESCENCE_V1.json"
PROT="canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
REG="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
EXPECTED={
 PROT:"62394e5b7d221ec9f69c3458f669e40e253a9d09",
 REG:"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
}
EXPECTED_TARGETS={
 "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
 "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
 "IF_SCOPE_BOUNDARY_NONINFERIOR",
 "IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS",
 "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR",
 "COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
 "VISION_DENSE_NONCHART_SCOPE",
}

def blob(p:str)->str:
 b=(ROOT/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p:str)->dict[str,Any]:
 x=json.loads((ROOT/p).read_text(encoding="utf-8"))
 if not isinstance(x,dict): raise ValueError(p)
 return x
def protocol_literal_present(row:Mapping[str,Any], literal:str)->bool:
 a=row.get("acceptance")
 if isinstance(a,str): return literal==a
 if isinstance(a,list): return literal in a
 return False

def evaluate()->dict[str,Any]:
 errors=[]
 for p,h in EXPECTED.items():
  if blob(p)!=h: errors.append("SOURCE_BLOB_DRIFT:"+p)
 c=load(CAND); protocols=load(PROT); registry=load(REG)
 ps={x.get("family"):x for x in protocols.get("protocols",[]) if isinstance(x,Mapping)}
 rs={x.get("id"):x for x in registry.get("predicates",[]) if isinstance(x,Mapping)}
 groups=c.get("population_groups")
 if not isinstance(groups,list) or len(groups)!=4:
  errors.append("POPULATION_GROUP_COUNT")
  groups=[]
 seen=set(); shared=[]
 for g in groups:
  if not isinstance(g,Mapping):
   errors.append("GROUP_NOT_MAPPING"); continue
  fam=g.get("family"); pids=g.get("predicate_ids"); lit=g.get("protocol_literal")
  if not isinstance(fam,str) or not isinstance(pids,list) or not pids or not isinstance(lit,str):
   errors.append("GROUP_FIELDS_INVALID"); continue
  if g.get("sharing_scope")!="TARGET_POPULATION_IDENTITY_ONLY":
   errors.append("SHARING_SCOPE_OVERCLAIM:"+str(fam))
  prow=ps.get(fam)
  if not isinstance(prow,Mapping) or not protocol_literal_present(prow,lit):
   errors.append("PROTOCOL_LITERAL_NOT_EXACT:"+str(fam))
  for pid in pids:
   if pid in seen: errors.append("DUPLICATE_TARGET:"+str(pid))
   seen.add(pid)
   rr=rs.get(pid)
   if not isinstance(rr,Mapping) or rr.get("family")!=fam:
    errors.append("PREDICATE_FAMILY_MISMATCH:"+str(pid))
  if len(pids)>1: shared.append({"family":fam,"predicate_count":len(pids),"predicate_ids":sorted(pids)})
 if seen!=EXPECTED_TARGETS: errors.append("TARGET_SET_DRIFT")
 acc=c.get("accounting") or {}
 if acc.get("formal_root3_target_count")!=7: errors.append("TARGET_COUNT_DRIFT")
 if acc.get("population_group_count")!=4: errors.append("GROUP_ACCOUNTING_DRIFT")
 if acc.get("duplicate_population_definitions_eliminated")!=3: errors.append("DEDUPE_ACCOUNTING_DRIFT")
 for k in ("semantic_binding_facts_closed","scope_completeness_predicates_closed","acceptance_predicates_closed"):
  if acc.get(k)!=0: errors.append("CREDIT_OVERCLAIM:"+k)
 ok=not errors
 return {
  "schema":SCHEMA,
  "status":"PASS__7_FORMAL_ROOT3_TARGETS_COALESCED_TO_4_PROTOCOL_BOUND_POPULATION_IDENTITIES__ZERO_CREDIT" if ok else "FAIL_CLOSED",
  "pass":ok,"errors":sorted(set(errors)),
  "formal_root3_target_count":7 if ok else None,
  "population_group_count":4 if ok else None,
  "shared_multi_predicate_population_group_count":len(shared) if ok else None,
  "shared_groups":shared if ok else [],
  "duplicate_population_definitions_eliminated":3 if ok else 0,
  "semantic_binding_facts_closed":0,
  "scope_completeness_predicates_closed":0,
  "acceptance_credit_delta":0,"family_credit_delta":0,
  "capability_credit_delta":0,"ownership_credit_delta":0,
  "new_reality_units_consumed":0,"incremental_spend_usd":0,
  "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
  "rule":"POPULATION_IDENTITY_MAY_BE_SHARED_ONLY_WHEN_EXACT_FROZEN_PROTOCOL_LITERAL_COUPLES_MEMBER_PREDICATES_IN_THE_SAME_FAMILY_PORTFOLIO__SEMANTIC_AND_PERFORMANCE_PROOFS_REMAIN_TARGET_SPECIFIC"
 }
if __name__=="__main__":
 print(json.dumps(evaluate(),indent=2,sort_keys=True))
 raise SystemExit(0 if evaluate()["pass"] else 1)
