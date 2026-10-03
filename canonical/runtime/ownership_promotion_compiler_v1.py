"""Compile already-accepted Brain routes into zero-reality ownership candidates."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any, Mapping

OWNED="VERIFIED_OWNED_EQUAL_OR_BETTER"

def load(p:Path)->dict[str,Any]:
    x=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ValueError("JSON_OBJECT_REQUIRED:"+str(p))
    return x

def git_blob(p:Path)->str:
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def lookup(d:Mapping[str,Any],ptr:str)->Any:
    parts=([x.replace("~1","/").replace("~0","~") for x in ptr.split("/")[1:]]
           if ptr.startswith("/") else ptr.split("."))
    cur:Any=d
    for k in parts:
        if not isinstance(cur,Mapping) or k not in cur: raise KeyError(ptr)
        cur=cur[k]
    return cur

def independent_pass(d:Mapping[str,Any])->bool:
    s=d.get("status")
    return isinstance(s,str) and s.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS")

def rows(doc:Mapping[str,Any], key:str, idkey:str)->dict[str,Mapping[str,Any]]:
    out={}
    for x in doc.get(key,[]):
        if isinstance(x,Mapping) and isinstance(x.get(idkey),str): out[x[idkey]]=x
    return out

def global_ok(g:Mapping[str,Any])->tuple[bool,list[str]]:
    e=[]
    if not independent_pass(g): e.append("GLOBAL_NOT_INDEPENDENT_PASS")
    r=g.get("result",{}); c=r.get("counters",{}) if isinstance(r,Mapping) else {}
    p=r.get("terminal_predicates",{}) if isinstance(r,Mapping) else {}
    for k in ("donor_dependent_required_behaviors","unresolved_verifier_mutations","unresolved_composition_failures"):
        if c.get(k)!=0: e.append("GLOBAL_COUNTER_NONZERO:"+k)
    for k in ("donor_dependent_required_behaviors_zero","unresolved_verifier_mutations_zero",
              "unresolved_composition_failures_zero","final_donor_deletion_cleanroom_pass"):
        if p.get(k) is not True: e.append("GLOBAL_PREDICATE_FALSE:"+k)
    return not e,e

def evaluate(root:Path,batch:Mapping[str,Any])->dict[str,Any]:
    closure=load(root/batch["closure_manifest"])
    matrix=load(root/batch["ownership_matrix"])
    gp=load(root/batch["global_postconditions"])
    cr=rows(closure,"families","id"); mr=rows(matrix,"rows","family")
    gok,gerr=global_ok(gp)
    out=[]
    for s in batch.get("families",[]):
        fam=s.get("family"); e=[]
        c=cr.get(fam,{}); m=mr.get(fam,{})
        if m.get("status")==OWNED:
            out.append({"family":fam,"status":"ALREADY_OWNED","errors":[]}); continue
        if not (c.get("opus55_acceptance_state")=="PASS" and
                c.get("opus55_acceptance_calibrated") is True and c.get("unresolved")==[]):
            e.append("STRICT_ACCEPTANCE_NOT_PASS")
        for rp in s.get("acceptance_receipts",[]):
            try: rd=load(root/rp)
            except Exception: e.append("RECEIPT_UNAVAILABLE:"+str(rp)); continue
            if not independent_pass(rd): e.append("RECEIPT_NOT_INDEPENDENT_PASS:"+rp)
        a=s.get("artifact",{}); ap=a.get("path"); sha=a.get("git_blob_sha")
        if not isinstance(ap,str) or not ap.startswith("canonical/") or ".." in Path(ap).parts:
            e.append("OPERATIVE_ARTIFACT_NOT_BRAIN_OWNED")
        else:
            try:
                if git_blob(root/ap)!=sha: e.append("OPERATIVE_ARTIFACT_HASH_MISMATCH")
            except Exception: e.append("OPERATIVE_ARTIFACT_UNAVAILABLE")
        bp=a.get("binding_receipt"); ptr=a.get("binding_pointer")
        try:
            bd=load(root/bp)
            if not independent_pass(bd): e.append("BINDING_RECEIPT_NOT_INDEPENDENT_PASS")
            if lookup(bd,ptr)!=sha: e.append("ARTIFACT_NOT_BOUND_TO_ACCEPTANCE_EVIDENCE")
        except Exception:
            e.append("ARTIFACT_BINDING_UNRESOLVED")
        if not gok: e.extend(gerr)
        e=sorted(set(e))
        out.append({"family":fam,"status":"PROMOTION_ELIGIBLE_ZERO_REALITY" if not e else "BLOCKED","errors":e})
    eligible=[x["family"] for x in out if x["status"]=="PROMOTION_ELIGIBLE_ZERO_REALITY"]
    blocked=[x["family"] for x in out if x["status"]=="BLOCKED"]
    return {
      "schema":"PROJECT_BRAIN_OWNERSHIP_PROMOTION_COMPILER_V1",
      "status":"PASS" if not blocked else "FAIL_CLOSED",
      "families":out,
      "promotion_eligible_families":eligible,
      "blocked_families":blocked,
      "counts":{"eligible":len(eligible),"blocked":len(blocked)},
      "new_reality_units_consumed":0,
      "incremental_spend_usd":0,
      "rule":"ACCEPTANCE_PASS_AND_CONTENT_BOUND_BRAIN_OPERATIVE_ARTIFACT_AND_INDEPENDENT_RECEIPTS_AND_GLOBAL_DONOR_INDEPENDENCE"
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=Path("."))
    ap.add_argument("--batch",type=Path,default=Path("canonical/governance/OWNERSHIP_PROMOTION_BATCH_V1.json"))
    a=ap.parse_args(); root=a.root.resolve()
    b=a.batch if a.batch.is_absolute() else root/a.batch
    result=evaluate(root,load(b))
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result["status"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
