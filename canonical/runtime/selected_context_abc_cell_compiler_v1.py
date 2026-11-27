from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_SELECTED_CONTEXT_ABC_CELL_INPUT_V1"

class ABCCellError(ValueError): pass

def _blob(path:str)->str:
    cp=subprocess.run(["git","-C",str(ROOT),"rev-parse",f"HEAD:{path}"],text=True,capture_output=True,check=False)
    return cp.stdout.strip() if cp.returncode==0 else ""

def _load(path:str):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def _get(obj:Any,pointer:list[str]):
    cur=obj
    for k in pointer:
        if not isinstance(cur,Mapping) or k not in cur: raise ABCCellError("JSON_POINTER_MISSING:"+"/".join(pointer))
        cur=cur[k]
    return cur

def _bind(spec:Mapping[str,Any],label:str):
    if not isinstance(spec,Mapping) or set(spec)!={"path","git_blob_sha"}: raise ABCCellError(label+"_BINDING_INVALID")
    p=str(spec["path"]); h=str(spec["git_blob_sha"])
    if _blob(p)!=h: raise ABCCellError(label+"_BLOB_DRIFT:"+p)
    return {"path":p,"git_blob_sha":h}

def compile_cell(doc:Mapping[str,Any])->dict[str,Any]:
    try:
        if not isinstance(doc,Mapping) or doc.get("schema")!=SCHEMA: raise ABCCellError("SCHEMA_INVALID")
        for k in ("cell_id","target_scope","selected_route","adequacy_or_dominance","local_c","route_local_d","accounting"):
            if k not in doc: raise ABCCellError("MISSING:"+k)
        authority=_bind(doc["authority"],"AUTHORITY")
        if authority["path"]!="canonical/governance/CURRENT_TERMINAL_AUTHORITY_V9.json":
            raise ABCCellError("AUTHORITY_NOT_V9")
        route=doc["selected_route"]
        if not isinstance(route,Mapping) or not route.get("operative_files"): raise ABCCellError("ROUTE_INVALID")
        route_files=[_bind(x,"ROUTE") for x in route["operative_files"]]
        if len({x["path"] for x in route_files})!=len(route_files): raise ABCCellError("ROUTE_DUPLICATE_PATH")
        checks=[]
        for section in ("target_scope","adequacy_or_dominance","local_c","route_local_d"):
            sec=doc[section]
            if not isinstance(sec,Mapping): raise ABCCellError(section.upper()+"_INVALID")
            evidence=_bind(sec["evidence"],section.upper())
            payload=_load(evidence["path"])
            for c in sec.get("checks",[]):
                if not isinstance(c,Mapping) or set(c)!={"pointer","equals"}: raise ABCCellError(section.upper()+"_CHECK_INVALID")
                ptr=c["pointer"]
                if not isinstance(ptr,list) or not ptr or any(not isinstance(x,str) or not x for x in ptr): raise ABCCellError(section.upper()+"_POINTER_INVALID")
                actual=_get(payload,ptr)
                if actual!=c["equals"]: raise ABCCellError(section.upper()+"_CHECK_FAIL:"+"/".join(ptr))
                checks.append({"section":section,"pointer":ptr,"value":actual})
        acct=doc["accounting"]
        if acct.get("terminal_credit_delta")!=0 or acct.get("incremental_spend_usd")!=0:
            raise ABCCellError("NONZERO_CREDIT_OR_SPEND")
        core={"cell_id":str(doc["cell_id"]),"authority":authority,"route_files":route_files,"verified_checks":checks}
        fp=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        return {"schema":"PROJECT_BRAIN_SELECTED_CONTEXT_ABC_CELL_OUTPUT_V1","status":"PASS__STRUCTURAL_PROOF_CARRYING_ABC_CELL","pass":True,"cell_id":core["cell_id"],"route_file_count":len(route_files),"verified_check_count":len(checks),"cell_fingerprint_sha256":fp,"terminal_credit_delta":0}
    except (ABCCellError,KeyError,TypeError,FileNotFoundError,json.JSONDecodeError) as e:
        return {"schema":"PROJECT_BRAIN_SELECTED_CONTEXT_ABC_CELL_OUTPUT_V1","status":"FAIL_CLOSED","pass":False,"errors":[str(e)],"terminal_credit_delta":0}
