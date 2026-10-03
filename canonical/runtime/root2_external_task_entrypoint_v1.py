#!/usr/bin/env python3
from __future__ import annotations
import hashlib, importlib.util, json, sys
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
REGISTRY=ROOT/"canonical/governance/ROOT2_EXTERNAL_TASK_ADAPTER_REGISTRY_V1.json"
SCHEMA="PROJECT_BRAIN_ROOT2_EXTERNAL_TASK_ENTRYPOINT_V1"

class ExternalTaskBlocked(RuntimeError): pass

def git_blob_sha(path:Path)->str:
    b=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load_registry()->dict[str,Any]:
    x=json.loads(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(x,dict): raise ExternalTaskBlocked("REGISTRY_OBJECT_REQUIRED")
    return x

def _row(benchmark_id:str, registry:Mapping[str,Any])->Mapping[str,Any]:
    rows=[x for x in registry.get("adapters",[]) if isinstance(x,Mapping) and x.get("benchmark_id")==benchmark_id]
    if len(rows)!=1: raise ExternalTaskBlocked("EXACTLY_ONE_ADAPTER_REQUIRED:"+benchmark_id)
    return rows[0]

def preflight(benchmark_id:str)->dict[str,Any]:
    reg=load_registry()
    try:
        row=_row(benchmark_id,reg)
    except Exception as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","benchmark_id":benchmark_id,"reason":str(exc),"inference_ready":False}
    path=str(row.get("adapter_path") or "")
    expected=str(row.get("adapter_blob_sha") or "")
    callable_name=str(row.get("callable") or "")
    errors=[]
    if not path.startswith("canonical/runtime/") or ".." in Path(path).parts: errors.append("ADAPTER_PATH_NOT_CANONICAL")
    p=ROOT/path
    if not p.is_file(): errors.append("ADAPTER_MISSING")
    elif git_blob_sha(p)!=expected: errors.append("ADAPTER_BLOB_DRIFT")
    if not callable_name: errors.append("CALLABLE_MISSING")
    if row.get("inference_capable") is not True: errors.append("ADAPTER_NOT_INFERENCE_CAPABLE")
    if row.get("mode")!="INFERENCE": errors.append("ADAPTER_MODE_NOT_INFERENCE")
    return {
      "schema":SCHEMA,
      "status":"PASS__INFERENCE_ADAPTER_BOUND" if not errors else "FAIL_CLOSED",
      "benchmark_id":benchmark_id,
      "adapter_path":path or None,
      "adapter_blob_sha":expected or None,
      "callable":callable_name or None,
      "inference_ready":not errors,
      "errors":errors,
      "incremental_spend_usd":0,
      "acceptance_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
    }

def invoke(request:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(request,Mapping): raise ExternalTaskBlocked("REQUEST_MAPPING_REQUIRED")
    benchmark_id=str(request.get("benchmark_id") or "").strip()
    if not benchmark_id: raise ExternalTaskBlocked("BENCHMARK_ID_REQUIRED")
    pf=preflight(benchmark_id)
    if pf.get("inference_ready") is not True:
        raise ExternalTaskBlocked("INFERENCE_ADAPTER_UNAVAILABLE:"+benchmark_id+":"+",".join(pf.get("errors") or []))
    row=_row(benchmark_id,load_registry())
    p=ROOT/str(row["adapter_path"])
    spec=importlib.util.spec_from_file_location("project_brain_root2_external_adapter",p)
    if spec is None or spec.loader is None: raise ExternalTaskBlocked("ADAPTER_IMPORT_SPEC_FAILED")
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    fn=getattr(module,str(row["callable"]),None)
    if not callable(fn): raise ExternalTaskBlocked("ADAPTER_CALLABLE_INVALID")
    result=fn(dict(request))
    return {
      "schema":SCHEMA,
      "status":"PASS__ADAPTER_RESULT",
      "benchmark_id":benchmark_id,
      "result":result,
      "adapter_blob_sha":row["adapter_blob_sha"],
      "incremental_spend_usd":0,
      "acceptance_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
    }

def main()->int:
    raw=sys.stdin.read().strip()
    if not raw:
        reg=load_registry()
        out={x["benchmark_id"]:preflight(x["benchmark_id"]) for x in reg.get("adapters",[]) if isinstance(x,dict) and x.get("benchmark_id")}
        print(json.dumps({"schema":SCHEMA,"status":"PREFLIGHT_ONLY","benchmarks":out},indent=2,sort_keys=True)); return 0
    try:
        req=json.loads(raw); out=invoke(req)
        print(json.dumps(out,indent=2,sort_keys=True)); return 0
    except Exception as exc:
        print(json.dumps({"schema":SCHEMA,"status":"FAIL_CLOSED","error":type(exc).__name__+":"+str(exc)},indent=2,sort_keys=True))
        return 2

if __name__=="__main__": raise SystemExit(main())
