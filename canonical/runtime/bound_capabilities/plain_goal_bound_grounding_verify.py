#!/usr/bin/env python3
"""Independent structural verifier for plain-goal bound-capability grounding."""
from __future__ import annotations
import hashlib,json,pathlib,re

def _safe(root,raw):
    root=pathlib.Path(root).resolve()
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    return p

def verify(goal,result,registry):
    canonical=" ".join(str(goal or "").strip().split())
    if result.get("schema")!="PROJECT_BRAIN_PLAIN_GOAL_BOUND_GROUNDING_V1":
        return False,"SCHEMA_INVALID"
    if result.get("goal_sha256")!=hashlib.sha256(canonical.encode("utf-8")).hexdigest():
        return False,"GOAL_HASH_MISMATCH"
    if result.get("model_dependency_count")!=0:
        return False,"MODEL_DEPENDENCY_NONZERO"
    clauses=result.get("clauses")
    if not isinstance(clauses,list) or not clauses:
        return False,"CLAUSES_INVALID"
    seen=set()
    grounded=0
    for index,clause in enumerate(clauses):
        if not isinstance(clause,dict) or clause.get("index")!=index:
            return False,"CLAUSE_INDEX_INVALID"
        candidates=clause.get("candidates")
        if not isinstance(candidates,list):
            return False,"CANDIDATES_INVALID"
        status=clause.get("status")
        if status not in {"UNRESOLVED","GROUNDED","AMBIGUOUS_BOUNDED"}:
            return False,"STATUS_INVALID"
        if status=="UNRESOLVED" and candidates:
            return False,"UNRESOLVED_HAS_CANDIDATES"
        if status=="GROUNDED" and len(candidates)!=1:
            return False,"GROUNDED_CARDINALITY_INVALID"
        if status=="AMBIGUOUS_BOUNDED" and len(candidates)<2:
            return False,"AMBIGUOUS_CARDINALITY_INVALID"
        if candidates:
            grounded+=1
        clause_tokens=set(re.findall(r"[a-z0-9]+",str(clause.get("text") or "").lower()))
        for item in candidates:
            cid=str(item.get("capability_id") or "")
            entry=registry.get(cid)
            if not isinstance(entry,dict) or entry.get("status")!="VERIFIED_BOUND_CAPABILITY":
                return False,"CANDIDATE_NOT_VERIFIED:"+cid
            try:
                if float(entry.get("incremental_spend_usd",0) or 0)!=0:
                    return False,"CANDIDATE_NONZERO_SPEND:"+cid
            except Exception:
                return False,"CANDIDATE_SPEND_INVALID:"+cid
            matched=item.get("matched_distinctive_tokens")
            if not isinstance(matched,list) or not matched:
                return False,"CANDIDATE_MATCH_EVIDENCE_MISSING:"+cid
            if any(str(x).lower() not in clause_tokens and not any(
                str(x).lower().startswith(t) or t.startswith(str(x).lower())
                for t in clause_tokens if len(t)>=5
            ) for x in matched):
                return False,"MATCH_EVIDENCE_NOT_IN_CLAUSE:"+cid
            seen.add(cid)
    if result.get("grounded_clause_count")!=grounded:
        return False,"GROUNDED_COUNT_MISMATCH"
    if sorted(result.get("candidate_capability_ids") or [])!=sorted(seen):
        return False,"CANDIDATE_SET_MISMATCH"
    if bool(grounded)!=bool(result.get("whole_goal_external_discovery_forbidden_if_any_bound_grounding")):
        return False,"DISCOVERY_POLICY_MISMATCH"
    return True,"VERIFIED"

def run(args,root):
    root=pathlib.Path(root).resolve()
    result_path=_safe(root,args.get("result_path"))
    registry_path=root/"canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    result=json.loads(result_path.read_text(encoding="utf-8"))
    raw=json.loads(registry_path.read_text(encoding="utf-8"))
    registry=raw.get("capabilities") if isinstance(raw,dict) else {}
    ok,reason=verify(args.get("goal"),result,registry)
    return {"verified":bool(ok),"reason":reason,"producer_independent":True,"model_dependency_count":0}
