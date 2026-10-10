from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from canonical.runtime import professional_quality_scoped_evidence_v1 as b
from canonical.runtime import professional_candidate_search_semantic_certificate_v1 as c
ROOT=b.ROOT
REGISTRY=b.REGISTRY
SCHEMA="PROJECT_BRAIN_PQ_SCOPED_EVIDENCE_OVERLAY_V1"
K=c.CLAIM_KIND
L={"PQ::R2_CANDIDATE_SEARCH::SEMANTIC"}
SS="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R2_SEARCH_SEMANTIC_VERIFY_V1"
GS="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R2_SEARCH_SEMANTIC_SCOPE_V1"
ST="PASS__PINNED_EXACT_BYTES__PYCOMPILE__8_OF_8__BOUNDED_R2_SEARCH_SEMANTICS__ZERO_GLOBAL_LEAF_CREDIT"
GT="ACTIVE_SCOPED_FINITE_SCOPE_COMPLETE_CANDIDATE_SEARCH_SEMANTICS__8_OF_8_INDEPENDENT_REPLAY__ZERO_GLOBAL_LEAF_CREDIT"

def _r(e:dict[str,Any],root:Path)->dict[str,Any]:
    x=b._common_checks(e,c.ROOT_ID,L)
    s,z=b._read_bound(root,e.get("source_receipt"),"SOURCE");x+=z
    g,z=b._read_bound(root,e.get("scope_governance"),"SCOPE");x+=z
    q=e.get("reusable_compiler");p=b._resolve(root,q.get("path") if isinstance(q,dict) else None);h=q.get("git_blob_sha") if isinstance(q,dict) else None
    if p is None or not p.exists() or b.git_blob_sha(p)!=h:x.append("COMPILER_INVALID")
    if s is None or s.get("schema")!=SS or s.get("status")!=ST:x.append("SOURCE_INVALID")
    elif (s.get("exact_blobs") or {}).get("runtime")!=h or (s.get("replay") or {}).get("tests_passed")!=8:x.append("SOURCE_BINDING_INVALID")
    sem=None
    if g is None or g.get("schema")!=GS or g.get("status")!=GT:x.append("SCOPE_INVALID")
    else:
        d=g.get("exact_components") or {}
        a,z=b._read_bound(root,d.get("source_scope"),"SOURCE_SCOPE");x+=z
        v,z=b._read_bound(root,d.get("source_execution_verification"),"SOURCE_VERIFY");x+=z
        if a is not None and v is not None:
            m={"root_id":c.ROOT_ID,"claim_kind":c.CLAIM_KIND,"scope_sha256":c.digest(a),"verification_sha256":c.digest(v),"semantic_roles":dict(c.SEMANTIC_ROLES),"boundaries":{"global_candidate_search_complete":False,"escape_progress_totality":False,"open_world_hypothesis_complete":False,"policy_generation_complete":False,"discriminator_plan_authorizes_u_subtraction":False,"unresolved_outside_bound_scope_stays_open":True}}
            sem=c.certify(a,v,m)
            if sem.get("pass") is not True:x.append("SEMANTIC_REPLAY_FAILED")
            if s is not None and s.get("claim_scope")!=sem.get("claim_scope"):x.append("CLAIM_SCOPE_MISMATCH")
    return {"scope_id":e.get("scope_id"),"root_id":e.get("root_id"),"claim_kind":e.get("claim_kind"),"admitted":not x,"errors":sorted(set(x)),"claim_scope":sem.get("claim_scope") if isinstance(sem,dict) else None,"contributes_to_leaf_ids":sorted(e.get("contributes_to_leaf_ids") or []),"global_leaf_credit":False,"global_root_credit":False,"semantic_leaf_credit":False,"execution_leaf_credit":False,"terminal_credit_delta":0}

def validate_entry(e:dict[str,Any],*,repo_root:Path=ROOT)->dict[str,Any]:
    return _r(e,repo_root) if isinstance(e,dict) and e.get("claim_kind")==K else b.validate_entry(e,repo_root=repo_root)

def evaluate(*,registry_path:Path=REGISTRY,repo_root:Path=ROOT)->dict[str,Any]:
    d=json.loads(registry_path.read_text());e=d.get("entries") if isinstance(d.get("entries"),list) else [];r=[validate_entry(x,repo_root=repo_root) for x in e if isinstance(x,dict)];ids=[x.get("scope_id") for x in r];bad=[] if len(ids)==len(set(ids)) else ["DUPLICATE_SCOPE_ID"];rej=[x for x in r if not x.get("admitted")]
    return {"schema":SCHEMA,"pass":not bad and not rej,"status":"PASS__SCOPED_CAPABILITIES_ADMITTED_WITH_ZERO_GLOBAL_LEAF_CREDIT" if not bad and not rej else "OPEN__SCOPED_EVIDENCE_REGISTRY_ERRORS","structural_errors":bad,"admitted_scope_count":sum(x.get("admitted") is True for x in r),"rejected_scope_count":len(rej),"admitted_scopes":[x for x in r if x.get("admitted") is True],"rejected_scopes":rej,"global_leaf_closure":False,"global_root_closure":False,"domain_semantic_closure":False,"domain_execution_closure":False,"terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}
