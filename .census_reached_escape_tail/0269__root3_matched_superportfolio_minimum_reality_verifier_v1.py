"""Verify Root3 matched-scope minimum-reality binding to the frozen superportfolio."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_ROOT3_MATCHED_SUPERPORTFOLIO_MINIMUM_REALITY_VERIFIER_V1"
CAND="canonical/governance/ROOT3_MATCHED_SUPERPORTFOLIO_MINIMUM_REALITY_BINDING_V1.json"
SUPER="canonical/governance/OPUS55_MATCHED_COMPARATOR_SUPERPORTFOLIO_V1.json"
REG="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
R3="canonical/governance/ROOT3_RESIDUAL_COMPRESSION_V1.json"
EXPECTED={SUPER:"d9ac894594ebcd2883520f7b7977a3548420541c",REG:"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",R3:"f6e264a0f7a63e1076be4bc4af7986f9aed07544"}
TARGETS={
 "AGENCY_MATCHED_SUCCESS_NONINFERIOR","AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION",
 "SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR",
 "COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR","COMPOSITION_ZERO_CRITICAL_INVARIANT_FAILURES",
 "IF_SCOPE_BOUNDARY_NONINFERIOR","IF_ZERO_CRITICAL_AUTHORITY_VIOLATIONS","VISION_DENSE_NONCHART_SCOPE",
}
CORE={"COMPLEX_MULTI_TOOL_AGENCY","COMMUNICATION_AND_SYNTHESIS","MULTI_CAPABILITY_COMPOSITION"}
OPTIONAL={"INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT","VISION_AND_DENSE_DOCUMENT_UNDERSTANDING"}

def blob(p:str)->str:
 b=(ROOT/p).read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p:str)->dict[str,Any]:
 x=json.loads((ROOT/p).read_text()); assert isinstance(x,dict); return x

def evaluate()->dict[str,Any]:
 e=[]
 for p,h in EXPECTED.items():
  if blob(p)!=h: e.append("SOURCE_BLOB_DRIFT:"+p)
 c=load(CAND); s=load(SUPER); r=load(REG); r3=load(R3)
 reg={x.get("id"):x for x in r.get("predicates",[]) if isinstance(x,Mapping)}
 core={x.get("family"):x for x in s.get("core_families",[]) if isinstance(x,Mapping)}
 opt={x.get("family"):x for x in s.get("optional_scope_extensions",[]) if isinstance(x,Mapping)}
 rows=c.get("matched_scope_targets")
 if not isinstance(rows,list) or len(rows)!=8: e.append("TARGET_ROW_COUNT"); rows=[]
 ids=set(); roles={}
 for x in rows:
  if not isinstance(x,Mapping): e.append("TARGET_ROW_INVALID"); continue
  pid=x.get("predicate_id"); fam=x.get("family"); role=x.get("superportfolio_role")
  if pid in ids: e.append("DUPLICATE_TARGET:"+str(pid))
  ids.add(pid); roles[pid]=role
  if not isinstance(reg.get(pid),Mapping) or reg[pid].get("family")!=fam: e.append("REGISTRY_FAMILY_MISMATCH:"+str(pid))
  if role=="CORE":
   if fam not in core: e.append("CORE_FAMILY_NOT_BOUND:"+str(fam))
  elif role=="OPTIONAL_SCOPE_EXTENSION":
   if fam not in opt: e.append("OPTIONAL_FAMILY_NOT_BOUND:"+str(fam))
  else: e.append("ROLE_INVALID:"+str(pid))
 if ids!=TARGETS: e.append("TARGET_SET_DRIFT")
 if {reg[x]["family"] for x in ids if x in reg and roles.get(x)=="CORE"}!=CORE: e.append("CORE_SET_DRIFT")
 if {reg[x]["family"] for x in ids if x in reg and roles.get(x)=="OPTIONAL_SCOPE_EXTENSION"}!=OPTIONAL: e.append("OPTIONAL_SET_DRIFT")

 live=set(r3.get("remaining_root3_targets_without_a_current_positive_pair_overlay_bound_here") or [])
 for row in r3.get("compressed_residuals") or []:
  if isinstance(row,Mapping) and row.get("predicate_id")=="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR": live.add(row["predicate_id"])
 if not TARGETS.issubset(live): e.append("CURRENT_ROOT3_TARGET_NOT_LIVE")

 cg=s.get("case_generation") or {}
 if cg.get("generated_now") is not False or cg.get("exposed_now") is not False or cg.get("beacon_known_now") is not False:
  e.append("CASE_GENERATION_STATE_DRIFT")
 ca=s.get("comparator_admissibility") or {}
 if ca.get("current_state")!="BLOCKED": e.append("COMPARATOR_STATE_DRIFT")
 sem=set(s.get("execution_semantics") or [])
 required={
  "GENERATE_SHARED_CASES_ONLY_AFTER_EXACT_OPUS55_COMPARATOR_ADMISSIBILITY_IS_PROVED",
  "RUN_BRAIN_AND_EXACT_OPUS55_ON_IDENTICAL_CASE_PAYLOADS_AND_TOOL_BOUNDARIES",
  "EACH_FAMILY_HAS_AN_INDEPENDENT_VERDICT__NO_PASS_INHERITANCE_ACROSS_FAMILIES",
  "SHARED_CASE_EXECUTION_MAY_BE_DEDUPLICATED_BUT_ACCEPTANCE_METRICS_MAY_NOT",
 }
 if not required.issubset(sem): e.append("SUPERPORTFOLIO_EXECUTION_SEMANTICS_DRIFT")

 comp=c.get("execution_compression") or {}
 if comp.get("matched_scope_target_count")!=8 or comp.get("shared_future_superportfolio_wave_count")!=1: e.append("EXECUTION_COMPRESSION_DRIFT")
 if comp.get("per_family_verdicts_remain_independent") is not True: e.append("PASS_INHERITANCE_RISK")
 fb=c.get("root3_reality_fallback") or {}
 if fb.get("batch_class_count")!=2: e.append("FALLBACK_BATCH_COUNT_DRIFT")
 if c.get("fresh_reality_authority") is not False: e.append("FRESH_REALITY_OVERCLAIM")
 ok=not e
 return {
  "schema":SCHEMA,
  "status":"PASS__8_MATCHED_SCOPE_ROOT3_TARGETS_BOUND_TO_ONE_FUTURE_SUPERPORTFOLIO_WAVE__TWO_ROOT3_REALITY_BATCH_CLASSES__ZERO_CREDIT" if ok else "FAIL_CLOSED",
  "pass":ok,"errors":sorted(set(e)),
  "matched_scope_target_count":8 if ok else None,
  "superportfolio_wave_count":1 if ok else None,
  "root3_empirical_batch_class_count":2 if ok else None,
  "core_family_count":3 if ok else None,"optional_scope_extension_family_count":2 if ok else None,
  "case_generation_now":False,"comparator_currently_admissible":False,
  "scope_predicates_closed":0,"acceptance_credit_delta":0,"family_credit_delta":0,
  "capability_credit_delta":0,"ownership_credit_delta":0,
  "new_reality_units_consumed":0,"incremental_spend_usd":0,
  "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
  "rule":"SHARE_CASE_GENERATION_AND_IDENTICAL_COMPARATOR_EXECUTION_ONLY__PRESERVE_PER_FAMILY_METRICS_AND_VERDICTS__NO_CASES_BEFORE_FIXED_POINT_AND_COMPARATOR_ADMISSIBILITY"
 }
if __name__=="__main__":
 out=evaluate(); print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if out["pass"] else 1)
