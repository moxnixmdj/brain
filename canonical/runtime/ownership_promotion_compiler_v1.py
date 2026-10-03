"""Compile already-accepted Brain routes into fail-closed ownership candidates."""
from __future__ import annotations
import argparse, ast, hashlib, json, sys
from pathlib import Path
from typing import Any, Mapping

OWNED="VERIFIED_OWNED_EQUAL_OR_BETTER"
STDLIB=set(getattr(sys,"stdlib_module_names",()))|{"__future__","typing"}
FORBIDDEN_CALLS={"__import__","eval","exec","compile","importlib.import_module",
                 "subprocess.run","subprocess.call","subprocess.Popen",
                 "os.system","requests.get","requests.post","httpx.get","httpx.post"}

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

def rows(doc:Mapping[str,Any],key:str,idkey:str)->dict[str,Mapping[str,Any]]:
    return {x[idkey]:x for x in doc.get(key,[])
            if isinstance(x,Mapping) and isinstance(x.get(idkey),str)}

def call_name(n:ast.Call)->str:
    f=n.func; parts=[]
    while isinstance(f,ast.Attribute):
        parts.append(f.attr); f=f.value
    if isinstance(f,ast.Name): parts.append(f.id)
    return ".".join(reversed(parts))

def audit_source(source:str)->list[str]:
    """Prove the exact operative artifact has no hidden provider/runtime escape."""
    e=[]
    try: tree=ast.parse(source)
    except SyntaxError as exc: return ["ARTIFACT_SYNTAX_ERROR:"+str(exc.lineno)]
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):
            for a in n.names:
                top=a.name.split(".",1)[0]
                if top not in STDLIB: e.append("NON_STDLIB_IMPORT:"+a.name)
        elif isinstance(n,ast.ImportFrom) and n.level==0:
            top=(n.module or "").split(".",1)[0]
            if top and top not in STDLIB: e.append("NON_STDLIB_IMPORT:"+(n.module or ""))
        elif isinstance(n,ast.Call):
            name=call_name(n)
            if name in FORBIDDEN_CALLS: e.append("FORBIDDEN_DYNAMIC_OR_PROVIDER_CALL:"+name)
    return sorted(set(e))

def evaluate(root:Path,batch:Mapping[str,Any])->dict[str,Any]:
    closure=load(root/batch["closure_manifest"])
    matrix=load(root/batch["ownership_matrix"])
    cr=rows(closure,"families","id"); mr=rows(matrix,"rows","family")
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
                path=root/ap
                if git_blob(path)!=sha: e.append("OPERATIVE_ARTIFACT_HASH_MISMATCH")
                e.extend(audit_source(path.read_text(encoding="utf-8")))
            except Exception: e.append("OPERATIVE_ARTIFACT_UNAVAILABLE")
        bp=a.get("binding_receipt"); ptr=a.get("binding_pointer")
        try:
            bd=load(root/bp)
            if not independent_pass(bd): e.append("BINDING_RECEIPT_NOT_INDEPENDENT_PASS")
            if lookup(bd,ptr)!=sha: e.append("ARTIFACT_NOT_BOUND_TO_ACCEPTANCE_EVIDENCE")
        except Exception: e.append("ARTIFACT_BINDING_UNRESOLVED")
        if s.get("future_use_requires_capability_rediscovery") is not False:
            e.append("CAPABILITY_REDISCOVERY_REQUIRED_OR_UNKNOWN")
        if s.get("incremental_spend_usd")!=0: e.append("INCREMENTAL_SPEND_NOT_ZERO")
        e=sorted(set(e))
        out.append({"family":fam,
                    "status":"PROMOTION_ELIGIBLE_ZERO_REALITY" if not e else "BLOCKED",
                    "provider_audit":"SELF_CONTAINED_STDLIB_ONLY" if not any("IMPORT" in x or "CALL" in x for x in e) else "FAIL",
                    "errors":e})
    eligible=[x["family"] for x in out if x["status"]=="PROMOTION_ELIGIBLE_ZERO_REALITY"]
    blocked=[x["family"] for x in out if x["status"]=="BLOCKED"]
    return {
      "schema":"PROJECT_BRAIN_OWNERSHIP_PROMOTION_COMPILER_V2",
      "status":"PASS" if not blocked else "FAIL_CLOSED",
      "families":out,"promotion_eligible_families":eligible,"blocked_families":blocked,
      "counts":{"eligible":len(eligible),"blocked":len(blocked)},
      "new_reality_units_consumed":0,"incremental_spend_usd":0,
      "rule":"STRICT_ACCEPTANCE_AND_EXACT_CONTENT_BOUND_BRAIN_ARTIFACT_AND_INDEPENDENT_RECEIPTS_AND_CURRENT_SELF_CONTAINED_PROVIDER_AUDIT"
    }

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--root",type=Path,default=Path("."))
    ap.add_argument("--batch",type=Path,default=Path("canonical/governance/OWNERSHIP_PROMOTION_BATCH_V1.json"))
    a=ap.parse_args(); root=a.root.resolve(); b=a.batch if a.batch.is_absolute() else root/a.batch
    result=evaluate(root,load(b)); print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result["status"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())
