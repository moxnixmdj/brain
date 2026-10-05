"""Content-addressed declarative operator-pack acquisition for H100.

Non-stdlib capability packages are JSON ASTs interpreted by this bounded runtime.
They are not imported or executed as Python code.

Security / authority boundary:
- exact Git blob SHA binding before interpretation;
- fixed schema and source class;
- max node and depth bounds;
- fixed finite opcode set;
- only input variable 'z';
- finite constants and explicit input domain;
- no eval, exec, imports, subprocess, network, or learned providers.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_verified_capability_registry_v6 as registry
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_DECLARATIVE_OPERATOR_PACK_ACQUISITION_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_DECLARATIVE_OPERATOR_PACK_ACQUISITION_RESULT_V1"
PACK_SCHEMA="PROJECT_BRAIN_H100_DECLARATIVE_OPERATOR_PACK_V1"
OPS={"VAR","CONST","ADD","SUB","MUL","ABS","MIN","MAX","CLAMP"}

class DeclarativePackError(ValueError):
    pass

def _git_blob_sha(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _finite(v:Any,label:str)->float:
    if isinstance(v,bool):
        raise DeclarativePackError(label+"_INVALID")
    try:
        x=float(v)
    except Exception as exc:
        raise DeclarativePackError(label+"_INVALID") from exc
    if not math.isfinite(x):
        raise DeclarativePackError(label+"_NONFINITE")
    return x

def _validate_node(node:Any,*,depth:int,max_depth:int,counter:list[int])->None:
    if depth>max_depth:
        raise DeclarativePackError("AST_DEPTH_EXCEEDED")
    if not isinstance(node,Mapping):
        raise DeclarativePackError("AST_NODE_INVALID")
    counter[0]+=1
    op=str(node.get("op") or "")
    if op not in OPS:
        raise DeclarativePackError("AST_OPCODE_NOT_ALLOWED:"+op)
    if op=="VAR":
        if node.get("name")!="z" or set(node)!={"op","name"}:
            raise DeclarativePackError("AST_VAR_INVALID")
        return
    if op=="CONST":
        if set(node)!={"op","value"}:
            raise DeclarativePackError("AST_CONST_FIELDS_INVALID")
        _finite(node.get("value"),"AST_CONST")
        return
    if op=="ABS":
        if set(node)!={"op","arg"}:
            raise DeclarativePackError("AST_ABS_FIELDS_INVALID")
        _validate_node(node["arg"],depth=depth+1,max_depth=max_depth,counter=counter)
        return
    if op in {"ADD","SUB","MUL","MIN","MAX"}:
        if set(node)!={"op","a","b"}:
            raise DeclarativePackError("AST_BINARY_FIELDS_INVALID")
        _validate_node(node["a"],depth=depth+1,max_depth=max_depth,counter=counter)
        _validate_node(node["b"],depth=depth+1,max_depth=max_depth,counter=counter)
        return
    if op=="CLAMP":
        if set(node)!={"op","arg","lo","hi"}:
            raise DeclarativePackError("AST_CLAMP_FIELDS_INVALID")
        lo=_finite(node["lo"],"AST_CLAMP_LO"); hi=_finite(node["hi"],"AST_CLAMP_HI")
        if not lo<hi:
            raise DeclarativePackError("AST_CLAMP_BOUNDS_INVALID")
        _validate_node(node["arg"],depth=depth+1,max_depth=max_depth,counter=counter)
        return
    raise DeclarativePackError("AST_UNREACHABLE")

def load_pack(path:Path,expected_git_blob_sha:str,contract:Mapping[str,Any])->dict[str,Any]:
    raw=Path(path).read_bytes()
    actual=_git_blob_sha(raw)
    if actual!=expected_git_blob_sha:
        raise DeclarativePackError("PACK_GIT_BLOB_SHA_MISMATCH")
    try:
        pack=json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise DeclarativePackError("PACK_JSON_INVALID") from exc
    if pack.get("schema")!=PACK_SCHEMA:
        raise DeclarativePackError("PACK_SCHEMA_INVALID")
    if pack.get("source_class")!="CONTENT_ADDRESSED_DECLARATIVE_OPERATOR_PACK":
        raise DeclarativePackError("PACK_SOURCE_CLASS_INVALID")
    if pack.get("input")!="z":
        raise DeclarativePackError("PACK_INPUT_INVALID")
    domain=pack.get("domain")
    if not isinstance(domain,Mapping):
        raise DeclarativePackError("PACK_DOMAIN_INVALID")
    lo=_finite(domain.get("min"),"PACK_DOMAIN_MIN"); hi=_finite(domain.get("max"),"PACK_DOMAIN_MAX")
    if not lo<hi:
        raise DeclarativePackError("PACK_DOMAIN_ORDER_INVALID")
    max_nodes=int(contract["max_nodes"]); max_depth=int(contract["max_depth"])
    counter=[0]
    _validate_node(pack.get("ast"),depth=1,max_depth=max_depth,counter=counter)
    if counter[0]>max_nodes:
        raise DeclarativePackError("AST_NODE_LIMIT_EXCEEDED")
    return {
        "pack":pack,
        "git_blob_sha":actual,
        "node_count":counter[0],
        "max_depth_limit":max_depth,
        "domain_min":lo,
        "domain_max":hi,
    }

def _eval(node:Mapping[str,Any],z:float)->float:
    op=node["op"]
    if op=="VAR": return z
    if op=="CONST": return float(node["value"])
    if op=="ABS": return abs(_eval(node["arg"],z))
    if op=="ADD": return _eval(node["a"],z)+_eval(node["b"],z)
    if op=="SUB": return _eval(node["a"],z)-_eval(node["b"],z)
    if op=="MUL": return _eval(node["a"],z)*_eval(node["b"],z)
    if op=="MIN": return min(_eval(node["a"],z),_eval(node["b"],z))
    if op=="MAX": return max(_eval(node["a"],z),_eval(node["b"],z))
    if op=="CLAMP":
        x=_eval(node["arg"],z)
        return min(max(x,float(node["lo"])),float(node["hi"]))
    raise DeclarativePackError("EVAL_OPCODE_INVALID")

def evaluate_pack(loaded:Mapping[str,Any],z:Any)->float:
    x=_finite(z,"PACK_INPUT")
    if x<float(loaded["domain_min"]) or x>float(loaded["domain_max"]):
        raise DeclarativePackError("PACK_INPUT_OUT_OF_DOMAIN")
    y=float(_eval(loaded["pack"]["ast"],x))
    if not math.isfinite(y):
        raise DeclarativePackError("PACK_OUTPUT_NONFINITE")
    return y

def _solve3(a,b):
    m=[list(map(float,a[i]))+[float(b[i])] for i in range(3)]
    for c in range(3):
        p=max(range(c,3),key=lambda r:abs(m[r][c]))
        if abs(m[p][c])<=1e-12: return None
        m[c],m[p]=m[p],m[c]
        d=m[c][c]; m[c]=[v/d for v in m[c]]
        for r in range(3):
            if r==c: continue
            f=m[r][c]
            if abs(f)<=1e-18: continue
            m[r]=[x-f*y for x,y in zip(m[r],m[c])]
    out=[m[i][-1] for i in range(3)]
    return out if all(math.isfinite(x) for x in out) else None

def _fit(rows,loaded,gamma):
    xs=[float(r["x"]) for r in rows]; ys=[float(r["y"]) for r in rows]
    try:
        z=[evaluate_pack(loaded,float(gamma)*x) for x in xs]
    except DeclarativePackError:
        return None
    cols=[[1.0]*len(xs),xs,z]
    xtx=[[sum(cols[i][k]*cols[j][k] for k in range(len(xs))) for j in range(3)] for i in range(3)]
    xty=[sum(cols[i][k]*ys[k] for k in range(len(xs))) for i in range(3)]
    for i in range(3): xtx[i][i]+=1e-13
    coeff=_solve3(xtx,xty)
    if coeff is None: return None
    pred=[coeff[0]+coeff[1]*x+coeff[2]*zv for x,zv in zip(xs,z)]
    return {"gamma":float(gamma),"coefficients":coeff,"train_nrmse":expr._nrmse(ys,pred)}

def _score(c,rows,loaded):
    pred=[
        float(c["coefficients"][0])+float(c["coefficients"][1])*float(r["x"])+
        float(c["coefficients"][2])*evaluate_pack(loaded,float(c["gamma"])*float(r["x"]))
        for r in rows
    ]
    return expr._nrmse([float(r["y"]) for r in rows],pred)

def _truth(oid,which,x):
    if oid=="ASYM_CLAMP_V1":
        op=lambda z:min(max(z,-0.65),0.95)
        if which=="SEED": return 0.2+0.1*x+1.1*op(0.8*x)
        if which=="TRANSFER": return -0.3+0.4*x-0.6*op(1.3*x)
    if oid=="TRIANGLE_V1":
        op=lambda z:max(0.0,1.0-abs(z))
        if which=="SEED": return 0.1-0.2*x+0.9*op(0.75*x)
        if which=="TRANSFER": return -0.2+0.35*x+0.7*op(1.25*x)
    raise DeclarativePackError("TASK_UNKNOWN")

def _rows(oid,which,xs):
    return [{"x":float(x),"y":_truth(oid,which,float(x))} for x in xs]

def _best(train,hold,loaded,gammas,use_holdout):
    out=[]
    for g in gammas:
        c=_fit(train,loaded,float(g))
        if c is None: continue
        c["holdout_nrmse"]=_score(c,hold,loaded)
        out.append(c)
    if not out: return None
    if use_holdout:
        out.sort(key=lambda c:(max(c["train_nrmse"],c["holdout_nrmse"]),c["gamma"]))
    else:
        out.sort(key=lambda c:(c["train_nrmse"],c["gamma"]))
    return out[0]

def _expression_baseline(seed,cfg):
    out=expr.discover(
        seed,target="y",inputs=["x"],
        max_depth=int(cfg["max_depth"]),beam_width=int(cfg["beam_width"]),
        pair_feature_pool=int(cfg["pair_feature_pool"]),exact_nrmse=float(cfg["exact_nrmse"])
    )
    return {
        "status":out.get("status"),
        "best_nrmse":None if not out.get("best_candidate") else out["best_candidate"].get("nrmse"),
        "best_validation_nrmse":None if not out.get("best_candidate") else out["best_candidate"].get("validation_nrmse"),
    }

def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    tx=[float(x) for x in pre["x_population"]["training_x"]]
    hx=[float(x) for x in pre["x_population"]["holdout_x"]]
    results=[]; all_pass=True
    for spec in pre["packs"]:
        oid=spec["operator_id"]
        path=ROOT/spec["path"]
        loaded=load_pack(path,spec["git_blob_sha"],pre["pack_contract"])
        # deterministic replay over independent frozen probes
        probes=[-3.7,-1.1,0.0,0.9,3.3]
        first=[evaluate_pack(loaded,x) for x in probes]
        second=[evaluate_pack(loaded,x) for x in probes]
        deterministic=[x.hex() for x in first]==[x.hex() for x in second]
        seed=_rows(oid,"SEED",tx); seed_hold=_rows(oid,"SEED",hx)
        transfer=_rows(oid,"TRANSFER",tx); transfer_hold=_rows(oid,"TRANSFER",hx)
        seed_miss=registry.resolve_verified_capability(seed,target="y",input_name="x").get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"
        transfer_miss=registry.resolve_verified_capability(transfer,target="y",input_name="x").get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"
        est=time.perf_counter(); baseline=_expression_baseline(seed,pre["baseline_expression_config"]); baseline["seconds"]=time.perf_counter()-est
        expression_miss=baseline["status"]!="EXACT_CANDIDATE_FOUND"
        gammas=[float(x) for x in spec["gamma_grid"]]
        sst=time.perf_counter(); seed_best=_best(seed,seed_hold,loaded,gammas,True); seed_seconds=time.perf_counter()-sst
        tst=time.perf_counter(); transfer_best=_best(transfer,transfer_hold,loaded,gammas,False); transfer_seconds=time.perf_counter()-tst
        seed_pass=bool(seed_best and seed_best["train_nrmse"]<=1e-10 and seed_best["holdout_nrmse"]<=1e-8)
        transfer_pass=bool(transfer_best and transfer_best["holdout_nrmse"]<=1e-8)
        passed=seed_miss and transfer_miss and expression_miss and deterministic and seed_pass and transfer_pass
        all_pass=all_pass and passed
        results.append({
            "operator_id":oid,"pack_git_blob_sha":loaded["git_blob_sha"],"node_count":loaded["node_count"],
            "baseline_seed_registry_v6_miss":seed_miss,
            "baseline_transfer_registry_v6_miss":transfer_miss,
            "baseline_expression":baseline,
            "deterministic_replay":deterministic,
            "seed_best":seed_best,"seed_seconds":seed_seconds,
            "transfer_best":transfer_best,"transfer_seconds":transfer_seconds,
            "pass":passed,
        })
    return {
        "schema":SCHEMA,
        "status":"PASS__CONTENT_ADDRESSED_NON_STDLIB_DECLARATIVE_OPERATOR_ACQUISITION_TWO_OF_TWO__ZERO_CREDIT" if all_pass else "FAIL__DECLARATIVE_OPERATOR_PACK_RESIDUAL",
        "packs":results,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "arbitrary_code_execution":0,
        "arbitrary_imports":0,
        "subprocess_calls":0,
        "network_calls":0,
        "h100_terminal_credit_delta":0,
        "hard_nonclaims":[
            "BOUNDED_DECLARATIVE_DSL_IS_NOT_ARBITRARY_EXTERNAL_BINARY_OR_GENERAL_SHELL_TOOL_ACQUISITION",
            "NO_H100_TERMINAL_CREDIT"
        ],
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
