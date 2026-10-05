"""Generic zero-learned multi-family patch search and transfer for H100."""
from __future__ import annotations
import json, math, time, statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_verified_capability_registry_v2 as registry

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_GENERIC_PATCH_SEARCH_TRANSFER_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_GENERIC_PATCH_SEARCH_TRANSFER_RESULT_V1"

class GenericPatchError(ValueError): pass

def _solve3(a,b):
    m=[list(map(float,a[i]))+[float(b[i])] for i in range(3)]
    for c in range(3):
        p=max(range(c,3),key=lambda r:abs(m[r][c]))
        if abs(m[p][c])<=1e-12: return None
        m[c],m[p]=m[p],m[c]
        div=m[c][c]; m[c]=[v/div for v in m[c]]
        for r in range(3):
            if r==c: continue
            f=m[r][c]
            if abs(f)<=1e-18: continue
            m[r]=[x-f*y for x,y in zip(m[r],m[c])]
    out=[m[i][-1] for i in range(3)]
    return out if all(math.isfinite(x) for x in out) else None

def _fit_linear3(xs,ys,feature):
    cols=[[1.0]*len(xs),list(xs),[feature(x) for x in xs]]
    xtx=[[sum(cols[i][k]*cols[j][k] for k in range(len(xs))) for j in range(3)] for i in range(3)]
    xty=[sum(cols[i][k]*ys[k] for k in range(len(xs))) for i in range(3)]
    for i in range(3): xtx[i][i]+=1e-13
    return _solve3(xtx,xty)

def _nrmse(a,p):
    mean=sum(a)/len(a)
    spread=math.sqrt(sum((x-mean)**2 for x in a)/len(a))
    scale=max(spread,max(abs(x) for x in a)*1e-9,1e-12)
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,p))/len(a))/scale

def _truth(task,phase,x):
    if task=="POWER5":
        return 0.2-0.4*x+0.07*x**5 if phase=="seed" else -1.1+0.3*x-0.02*x**5
    if task=="HINGE":
        return -0.4+0.2*x+1.1*max(0.0,x-0.6) if phase=="seed" else 0.8-0.1*x-0.6*max(0.0,x+0.8)
    if task=="GAUSSIAN":
        return 0.3+0.05*x+1.4*math.exp(-0.6*x*x) if phase=="seed" else -0.2-0.03*x+0.9*math.exp(-1.3*x*x)
    if task=="TANH":
        return 0.1+0.2*x+1.2*math.tanh(0.8*x) if phase=="seed" else -0.5+0.15*x-0.7*math.tanh(1.6*x)
    raise GenericPatchError("TASK_UNKNOWN:"+str(task))

def _rows(task,phase,xs):
    return [{"x":float(x),"y":_truth(task,phase,float(x))} for x in xs]

def _hinge_grid(xs):
    s=sorted(set(float(x) for x in xs))
    mids=[(a+b)/2.0 for a,b in zip(s,s[1:])]
    return sorted(set(s+mids))

def _specs(pre, family=None, train_x=None):
    rows=[]
    def add(fid,param,rank,feat):
        if family is None or family==fid:
            rows.append((fid,param,rank,feat))
    for p in [2,3,4,5,6]:
        add("POWER",p,1,lambda x,p=p:x**p)
    for t in _hinge_grid(train_x or []):
        add("HINGE",t,2,lambda x,t=t:max(0.0,x-t))
    for g in [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0,1.1,1.2,1.3,1.4,1.5,1.6,1.7,1.8,1.9,2.0]:
        add("GAUSSIAN",g,3,lambda x,g=g:math.exp(-g*x*x))
    for g in [0.2,0.4,0.6,0.8,1.0,1.2,1.4,1.6,1.8,2.0]:
        add("TANH",g,4,lambda x,g=g:math.tanh(g*x))
    add("RATIONAL_1PX2",None,5,lambda x:1.0/(1.0+x*x))
    add("ABS",None,6,lambda x:abs(x))
    return rows

def _fit_candidate(train,hold,fid,param,rank,feature):
    xs=[r["x"] for r in train]; ys=[r["y"] for r in train]
    c=_fit_linear3(xs,ys,feature)
    if c is None: return None
    pred_train=[c[0]+c[1]*r["x"]+c[2]*feature(r["x"]) for r in train]
    pred_hold=[c[0]+c[1]*r["x"]+c[2]*feature(r["x"]) for r in hold]
    return {
      "family_id":fid,"shape_parameter":param,"complexity_rank":rank,
      "coefficients":c,
      "train_nrmse":_nrmse(ys,pred_train),
      "holdout_nrmse":_nrmse([r["y"] for r in hold],pred_hold)
    }

def search_seed(task,pre):
    tx=[float(x) for x in pre["x_population"]["training_x"]]
    hx=[float(x) for x in pre["x_population"]["holdout_x"]]
    train=_rows(task,"seed",tx); hold=_rows(task,"seed",hx)
    cand=[_fit_candidate(train,hold,*s) for s in _specs(pre,train_x=tx)]
    cand=[x for x in cand if x is not None]
    passing=[x for x in cand if x["train_nrmse"]<=1e-10 and x["holdout_nrmse"]<=1e-8]
    passing.sort(key=lambda x:(x["holdout_nrmse"],x["complexity_rank"],x["family_id"],str(x["shape_parameter"])))
    return train,hold,cand,(passing[0] if passing else None)

def transfer_family(task,family,pre):
    tx=[float(x) for x in pre["x_population"]["training_x"]]
    hx=[float(x) for x in pre["x_population"]["holdout_x"]]
    train=_rows(task,"transfer",tx); hold=_rows(task,"transfer",hx)
    cand=[_fit_candidate(train,hold,*s) for s in _specs(pre,family=family,train_x=tx)]
    cand=[x for x in cand if x is not None]
    cand.sort(key=lambda x:(x["train_nrmse"],str(x["shape_parameter"])))
    return train,hold,(cand[0] if cand else None)

def _miss(rows):
    return registry.resolve_verified_capability(rows,target="y",input_name="x").get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"

def run():
    pre=json.loads(PRE.read_text())
    if "FROZEN_BEFORE_GENERIC_PATCH_SEARCH_OUTCOMES" not in pre.get("status",""):
        raise GenericPatchError("PRECOMMIT_NOT_FROZEN")
    results=[]
    times=[]
    for row in pre["tasks"]:
        task=row["id"]
        seed_train,_,_,selected=search_seed(task,pre)
        transfer_train,_,transfer=transfer_family(task,selected["family_id"] if selected else "",pre)
        st=time.perf_counter(); search_seed(task,pre); times.append(time.perf_counter()-st)
        results.append({
          "task_id":task,
          "expected_family_for_audit_only":row["expected_family_for_audit_only"],
          "baseline_seed_registry_miss":_miss(seed_train),
          "baseline_transfer_registry_miss":_miss(transfer_train),
          "selected_family":None if selected is None else selected["family_id"],
          "selected_shape_parameter":None if selected is None else selected["shape_parameter"],
          "seed_train_nrmse":None if selected is None else selected["train_nrmse"],
          "seed_holdout_nrmse":None if selected is None else selected["holdout_nrmse"],
          "transfer_shape_parameter":None if transfer is None else transfer["shape_parameter"],
          "transfer_train_nrmse":None if transfer is None else transfer["train_nrmse"],
          "transfer_holdout_nrmse":None if transfer is None else transfer["holdout_nrmse"],
        })
    passed=all(
      x["baseline_seed_registry_miss"] and x["baseline_transfer_registry_miss"] and
      x["selected_family"]==x["expected_family_for_audit_only"] and
      x["seed_holdout_nrmse"] is not None and x["seed_holdout_nrmse"]<=1e-8 and
      x["transfer_holdout_nrmse"] is not None and x["transfer_holdout_nrmse"]<=1e-8
      for x in results
    )
    return {
      "schema":SCHEMA,
      "status":"PASS__FOUR_OF_FOUR_MULTI_FAMILY_PATCH_TRANSFER__ZERO_CREDIT" if passed else "FAIL__GENERIC_PATCH_RESIDUAL",
      "tasks":results,
      "task_count":len(results),
      "tasks_passed":sum(
        1 for x in results if x["baseline_seed_registry_miss"] and x["baseline_transfer_registry_miss"] and
        x["selected_family"]==x["expected_family_for_audit_only"] and
        x["seed_holdout_nrmse"] is not None and x["seed_holdout_nrmse"]<=1e-8 and
        x["transfer_holdout_nrmse"] is not None and x["transfer_holdout_nrmse"]<=1e-8
      ),
      "patch_search_median_seconds":statistics.median(times),
      "persistent_learned_bytes":0,
      "external_learned_capability_calls":0,
      "hard_nonclaims":["SYNTHETIC_BOUNDED_MULTI_FAMILY_EVIDENCE_ONLY","PREDECLARED_GRAMMAR_IS_NOT_UNIVERSAL","NO_H100_TERMINAL_CREDIT"],
      "h100_terminal_credit_delta":0
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
