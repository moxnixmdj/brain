#!/usr/bin/env python3
"""Check that explicit current deployment contracts are live and invocable."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import r2_direct_route_dynamic_admission_v1 as r2
from canonical.runtime import live_capability_ownership_v1 as own
from canonical.runtime import live_capability_invoker_v1 as inv
from canonical.runtime import certificate_gated_selected_route_runtime_entrypoint_v5 as cert
ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_VERIFIED_TO_LIVE_COMPLETENESS_V1"

def _rel(root,p):return p.resolve().relative_to(root.resolve()).as_posix()

def _scan(root):
    candidates=[];receipts=[];needles=(r2.CANDIDATE_SCHEMA,r2.RECEIPT_SCHEMA)
    for base_rel in ("canonical/governance","canonical/verification"):
        base=root/base_rel
        if not base.exists():continue
        for p in sorted(base.rglob("*.json")):
            try:s=p.read_text(encoding="utf-8")
            except (OSError,UnicodeError):continue
            if not any(x in s for x in needles):continue
            d=json.loads(s)
            if not isinstance(d,Mapping):continue
            if d.get("schema")==r2.CANDIDATE_SCHEMA:candidates.append((_rel(root,p),dict(d)))
            elif d.get("schema")==r2.RECEIPT_SCHEMA:receipts.append((_rel(root,p),dict(d)))
    return candidates,receipts

def audit_r2(repo_root=ROOT):
    root=Path(repo_root).resolve();current=r2.load_current_admissions(repo_root=root)
    candidates,receipts=_scan(root);by={}
    for rp,rd in receipts:by.setdefault(str(rd.get("candidate_path") or ""),[]).append((rp,rd))
    deployable={};pending=[];invalid=[];stale=[]
    for cp,cd in candidates:
        cb=r2.git_blob_sha(root/cp)
        try:c=r2.validate_candidate(root,cd)
        except Exception as e:
            invalid.append({"candidate_path":cp,"reason":type(e).__name__+":"+str(e)});continue
        valid=0
        for rp,rd in by.get(cp,[]):
            try:r2.validate_receipt(root,rd,candidate_path=cp,candidate_blob_sha=cb,candidate=c)
            except Exception as e:
                stale.append({"candidate_path":cp,"receipt_path":rp,"reason":type(e).__name__+":"+str(e)});continue
            valid+=1;deployable[(str(c["route_id"]),cb)]=rp
        if valid==0:pending.append(cp)
    live={(str(x["route_id"]),str(x["candidate_git_blob_sha"])):x["independent_receipt_path"] for x in current["admissions"]}
    d=set(deployable);l=set(live);missing=sorted(d-l);unauth=sorted(l-d)
    passed=not invalid and not missing and not unauth
    return {"pass":passed,"status":"PASS__R2_VERIFIED_DEPLOYABLE_EQUALS_LIVE_DYNAMIC" if passed else "FAIL_CLOSED__R2_DEPLOYMENT_COMPLETENESS_GAP",
      "candidate_contract_count":len(candidates),"receipt_contract_count":len(receipts),
      "verified_deployable_count":len(d),"live_dynamic_count":len(l),
      "pending_unverified_candidates":sorted(pending),"invalid_candidates":invalid,
      "stale_or_invalid_receipts":stale,
      "missing_promotion":[{"route_id":a,"candidate_git_blob_sha":b} for a,b in missing],
      "unauthorized_live":[{"route_id":a,"candidate_git_blob_sha":b} for a,b in unauth]}

def run(repo_root=ROOT):
    root=Path(repo_root).resolve()
    from canonical.runtime import unified_cognitive_fabric_v1 as fabric
    o=own.evaluate(fabric.ENGINE_DESCRIPTORS);i=inv.coverage(o["live_owned_capability_ids"])
    cp=cert.preflight();certified={"certified_route:"+x for x in cert.verified_route_ids()}
    missing_cert=sorted(certified-set(o["live_owned_capability_ids"]));ra=audit_r2(root)
    gaps=[]
    if o.get("pass") is not True:gaps.append("LIVE_OWNED_NOT_FABRIC_REACHABLE")
    if i.get("pass") is not True:gaps.append("LIVE_OWNED_NOT_UNIVERSALLY_INVOKABLE")
    if cp.get("pass") is not True:gaps.append("CERTIFIED_ROUTE_PREFLIGHT_FAIL")
    if missing_cert:gaps.append("CERTIFIED_ROUTE_NOT_LIVE_OWNED")
    passed=ra["pass"] and not gaps
    return {"schema":SCHEMA,"pass":passed,
      "status":"PASS__EXPLICIT_VERIFIED_DEPLOYABLE_EQUALS_LIVE_AND_FABRIC_INVOKABLE" if passed else "FAIL_CLOSED__VERIFIED_TO_LIVE_COMPLETENESS_GAP",
      "scope":"CURRENT_EXPLICIT_DEPLOYMENT_CONTRACTS_ONLY","r2_dynamic_deployment":ra,
      "live_capability_ownership":{"pass":o.get("pass") is True,"live_owned_count":o.get("live_owned_capability_count"),"fabric_reachable_count":o.get("fabric_reachable_capability_count")},
      "universal_invocation":{"pass":i.get("pass") is True,"capability_count":i.get("capability_count"),"missing_capability_count":i.get("missing_capability_count")},
      "certified_routes":{"preflight_pass":cp.get("pass") is True,"verified_route_count":len(certified),"missing_live_ownership":missing_cert},
      "gaps":gaps,"historical_repository_capability_completeness_proved":False,
      "arbitrary_raw_language_route_selection_proved":False,"terminal_authority":False,"terminal_credit_delta":0}

if __name__=="__main__":
    out=run();print(json.dumps(out,indent=2,sort_keys=True));raise SystemExit(0 if out["pass"] else 1)
