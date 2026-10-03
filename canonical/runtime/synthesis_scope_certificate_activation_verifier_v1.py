"""Verify synthesis scope-certificate activation and Root3->Root2-only reclassification."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime.universal_scope_closure_compiler_v1 import evaluate as eval_scope

ROOT=Path(__file__).resolve().parents[2]
CERT="canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json"
ACT="canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_ACTIVATION_V1.json"
ROOTS="canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json"
PID="SYNTHESIS_MATCHED_QUALITY_COVERAGE_NONINFERIOR"

def load(p:str)->dict[str,Any]:
 x=json.loads((ROOT/p).read_text(encoding="utf-8"))
 if not isinstance(x,dict): raise ValueError(p)
 return x

def evaluate()->dict[str,Any]:
 e=[]
 cert=load(CERT); act=load(ACT); roots=load(ROOTS)
 v=eval_scope(cert)
 if v.get("scope_complete") is not True: e.append("GENERIC_SCOPE_COMPILER_REJECTED")
 if v.get("basis")!="LOSSLESS_DECOMPOSITION": e.append("GENERIC_BASIS_DRIFT")
 if cert.get("consequence",{}).get("root3_scope_relation_closed") is not True: e.append("CERT_SCOPE_CONSEQUENCE")
 if cert.get("consequence",{}).get("predicate_remains_open_for_root2") is not True: e.append("CERT_ROOT2_RESIDUAL_MISSING")
 part=roots.get("current_residual_root_partition")
 if not isinstance(part,Mapping):
  e.append("ROOT_PARTITION_MISSING")
  part={}
 r2=list(part.get("root2_only") or [])
 r3=list(part.get("root3_only") or [])
 mixed=list(part.get("root2_and_root3") or [])
 if PID not in mixed: e.append("SYNTHESIS_NOT_CURRENTLY_MIXED")
 if PID in r2: e.append("SYNTHESIS_ALREADY_ROOT2_ONLY")
 if part.get("unresolved_total")!=26: e.append("UNRESOLVED_TOTAL_DRIFT")
 if part.get("root2_only_count")!=15 or part.get("root3_only_count")!=7 or part.get("root2_and_root3_count")!=4:
  e.append("CURRENT_ROOT_COUNTS_DRIFT")
 after=(act.get("after_if_verified") or {})
 expected={"root2_only_count":16,"root3_only_count":7,"root2_and_root3_count":3,"unresolved_total":26,"root2_involved_count":19,"root3_involved_count":10}
 for k,val in expected.items():
  if after.get(k)!=val: e.append("AFTER_COUNT_DRIFT:"+k)
 residuals=act.get("remaining_root2_residuals")
 if set(residuals or [])!={"metric:matched_quality","matched_quality_noninferiority","required_claim_coverage_noninferiority"}:
  e.append("ROOT2_RESIDUAL_SET_DRIFT")
 if act.get("acceptance_credit_delta")!=0: e.append("ACCEPTANCE_CREDIT_OVERCLAIM")
 if act.get("fresh_reality_authority") is not False: e.append("FRESH_REALITY_OVERCLAIM")
 ok=not e
 return {
  "schema":"PROJECT_BRAIN_SYNTHESIS_SCOPE_CERTIFICATE_ACTIVATION_VERIFIER_V1",
  "status":"PASS__SYNTHESIS_SCOPE_CERTIFICATE_ADMISSIBLE__RECLASSIFY_ROOT2_AND_ROOT3_TO_ROOT2_ONLY__ROOT3_11_TO_10__ZERO_ACCEPTANCE_CREDIT" if ok else "FAIL_CLOSED",
  "pass":ok,"errors":sorted(set(e)),
  "predicate_id":PID,
  "scope_complete":bool(v.get("scope_complete")) if ok else False,
  "before_root_class":"ROOT2_AND_ROOT3" if ok else None,
  "after_root_class":"ROOT2_ONLY" if ok else None,
  "before_root3_involved_count":11 if ok else None,
  "after_root3_involved_count":10 if ok else None,
  "root2_involved_count":19 if ok else None,
  "unresolved_total":26 if ok else None,
  "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,
  "new_reality_units_consumed":0,"incremental_spend_usd":0,
  "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False,
 }
if __name__=="__main__":
 out=evaluate(); print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if out["pass"] else 1)
