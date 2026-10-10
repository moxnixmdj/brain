from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from canonical.runtime import professional_quality_scoped_evidence_overlay_v1 as scoped
from canonical.runtime import professional_quality_leaf_coverage_projection_v1 as old
ROOT=old.ROOT
MANIFEST=old.MANIFEST
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_COVERAGE_PROJECTION_V2"

def _load(p:Path)->dict[str,Any]:return json.loads(p.read_text())

def project(*,manifest_path:Path=MANIFEST,scoped_registry_path:Path=scoped.REGISTRY,repo_root:Path=ROOT)->dict[str,Any]:
 m=_load(manifest_path);s=scoped.evaluate(registry_path=scoped_registry_path,repo_root=repo_root);errs=[]
 roots=m.get("roots");roots=roots if isinstance(roots,list) else [];meta={}
 for r in roots:
  if not isinstance(r,dict):continue
  rid=str(r.get("root_id"))
  for kind,key in (("SEMANTIC","semantic_leaf"),("EXECUTION","execution_leaf")):
   x=r.get(key);lid=x.get("id") if isinstance(x,dict) else None
   if isinstance(lid,str) and lid and lid not in meta:meta[lid]={"root_id":rid,"kind":kind}
 if len(meta)!=24:errs.append("EXPECTED_24_LEAVES")
 if s.get("pass") is not True:errs.append("SCOPED_EVIDENCE_NOT_ADMITTED")
 c={x:[] for x in meta}
 for r in s.get("admitted_scopes") or []:
  for lid in r.get("contributes_to_leaf_ids") or []:
   if lid not in c:errs.append("UNKNOWN_CONTRIBUTION_LEAF");continue
   c[lid].append({"scope_id":r.get("scope_id"),"root_id":r.get("root_id"),"claim_kind":r.get("claim_kind"),"claim_scope":r.get("claim_scope"),"scope_relation_to_global_leaf":"BOUNDED_SUBSET_ONLY","leaf_closure_credit":False,"terminal_credit_delta":0})
 partial=sorted(x for x,v in c.items() if v);none=sorted(x for x,v in c.items() if not v)
 sem=sorted(x for x in partial if meta[x]["kind"]=="SEMANTIC");exe=sorted(x for x in partial if meta[x]["kind"]=="EXECUTION")
 return {"schema":SCHEMA,"status":"PASS__BOUNDED_SCOPE_COVERAGE_PROJECTED__ZERO_GLOBAL_LEAF_CREDIT" if not errs else "FAIL_CLOSED__COVERAGE_PROJECTION_INVALID","pass":not errs,"structural_errors":sorted(set(errs)),"expected_leaf_count":len(meta),"admitted_scoped_capability_count":s.get("admitted_scope_count",0),"partial_coverage_leaf_count":len(partial),"semantic_partial_coverage_leaf_count":len(sem),"execution_partial_coverage_leaf_count":len(exe),"no_scoped_evidence_leaf_count":len(none),"partial_coverage_leaf_ids":partial,"semantic_partial_coverage_leaf_ids":sem,"execution_partial_coverage_leaf_ids":exe,"no_scoped_evidence_leaf_ids":none,"contributions_by_leaf":c,"verified_global_leaf_count":0,"open_global_leaf_count":len(meta),"global_leaf_closure":False,"domain_semantic_closure":False,"domain_execution_closure":False,"terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}
