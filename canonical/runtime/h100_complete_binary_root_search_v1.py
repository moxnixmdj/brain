from __future__ import annotations
import itertools,json,time
from pathlib import Path
from typing import Any,Mapping,Sequence
import numpy as np
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr
from canonical.runtime import h100_verified_capability_registry_v8 as registry

ROOT=Path(__file__).resolve().parents[2]
REPAIR=ROOT/"canonical/governance/H100_COMPLETE_BINARY_ROOT_SEARCH_PRECOMMIT_V1.json"
TASKS=ROOT/"canonical/governance/H100_FRESH_BINARY_TREE_SEARCH_PRECOMMIT_V1.json"

def _seqs(ops,max_depth):
    out=[()]
    for d in range(1,max_depth+1):
        out.extend(itertools.product(tuple(ops),repeat=d))
    return out

def _apply_seq(x,seq):
    v=np.asarray(x,dtype=np.float64)
    for op in seq:
        if op=="neg": v=-v
        elif op=="abs": v=np.abs(v)
        elif op=="square": v=v*v
        elif op=="sqrt_abs": v=np.sqrt(np.abs(v))
        elif op=="log1p_abs": v=np.log1p(np.abs(v))
        elif op=="sat": v=v/(1.0+np.abs(v))
        else: raise ValueError("UNARY_UNKNOWN")
    return v

def _apply_binary(op,left,right):
    if op=="add": return left+right
    if op=="sub": return left-right
    if op=="mul": return left*right
    if op=="stable_div": return left/(1.0+np.abs(right))
    raise ValueError("BINARY_UNKNOWN")

def _make_rows(task,phase,xs):
    a,b,c=map(float,task[phase])
    rows=[]
    for x in xs:
        point={"x":float(x)}
        f=expr.evaluate_tree(task["tree"],point)
        rows.append({"x":float(x),"y":a+b*float(x)+c*f})
    return rows

def _scale(y):
    y=np.asarray(y,dtype=np.float64)
    spread=float(np.sqrt(np.mean((y-y.mean())**2)))
    return max(spread,float(np.max(np.abs(y)))*1e-9,1e-12)

def _fit_batch(Ft,Fh,xt,xh,yt,yh):
    Bt=np.column_stack([np.ones_like(xt),xt])
    Bh=np.column_stack([np.ones_like(xh),xh])
    gram=Bt.T@Bt + np.eye(2)*1e-12
    pinv=np.linalg.solve(gram,Bt.T)
    beta_y=pinv@yt
    yr=yt-Bt@beta_y
    beta_f=Ft@pinv.T
    fr=Ft-beta_f@Bt.T
    denom=np.sum(fr*fr,axis=1)
    numer=fr@yr
    good=denom>1e-20
    c=np.zeros(len(Ft),dtype=np.float64)
    c[good]=numer[good]/denom[good]
    beta=beta_y[None,:]-c[:,None]*beta_f
    pt=beta@Bt.T+c[:,None]*Ft
    ph=beta@Bh.T+c[:,None]*Fh
    tr=np.sqrt(np.mean((pt-yt[None,:])**2,axis=1))/_scale(yt)
    hr=np.sqrt(np.mean((ph-yh[None,:])**2,axis=1))/_scale(yh)
    tr[~good]=np.inf; hr[~good]=np.inf
    coeff=np.column_stack([beta,c])
    return tr,hr,coeff

def _sig(seq):
    s="v0"
    for op in seq: s=f"{op}({s})"
    return s

def search_rows(train,hold,pre):
    ops=list(pre["unary_operator_order"])
    seqs=_seqs(ops,int(pre["branch_max_unary_depth"]))
    xt=np.asarray([r["x"] for r in train],dtype=np.float64)
    xh=np.asarray([r["x"] for r in hold],dtype=np.float64)
    yt=np.asarray([r["y"] for r in train],dtype=np.float64)
    yh=np.asarray([r["y"] for r in hold],dtype=np.float64)
    Bt=np.stack([_apply_seq(xt,s) for s in seqs])
    Bh=np.stack([_apply_seq(xh,s) for s in seqs])
    n=len(seqs); exact=[]; considered=0
    start=time.perf_counter()
    for op in pre["binary_operator_order"]:
        if op in ("add","mul"):
            ii,jj=np.triu_indices(n)
        else:
            ii=np.repeat(np.arange(n),n)
            jj=np.tile(np.arange(n),n)
        for start_idx in range(0,len(ii),4096):
            a=ii[start_idx:start_idx+4096]; b=jj[start_idx:start_idx+4096]
            Ft=_apply_binary(op,Bt[a],Bt[b]); Fh=_apply_binary(op,Bh[a],Bh[b])
            tr,hr,co=_fit_batch(Ft,Fh,xt,xh,yt,yh)
            considered+=len(a)
            mask=np.flatnonzero((tr<=float(pre["exact_gate"]["train_nrmse"]))&(hr<=float(pre["exact_gate"]["holdout_nrmse"])))
            for k in mask:
                i=int(a[k]); j=int(b[k])
                ls=_sig(seqs[i]); rs=_sig(seqs[j])
                if op in ("add","mul") and rs<ls: ls,rs=rs,ls
                exact.append({
                  "op":op,"left_sequence":list(seqs[i]),"right_sequence":list(seqs[j]),
                  "signature":f"{op}({ls},{rs})",
                  "complexity":3+len(seqs[i])+len(seqs[j]),
                  "train_nrmse":float(tr[k]),"holdout_nrmse":float(hr[k]),
                  "coefficients":[float(v) for v in co[k]]
                })
    exact.sort(key=lambda r:(r["complexity"],r["signature"]))
    return {
      "candidate_count":considered,
      "exact_count":len(exact),
      "selected":exact[0] if exact else None,
      "wall_clock_seconds":time.perf_counter()-start
    }

def _feature_from_selected(xs,sel):
    l=_apply_seq(np.asarray(xs,dtype=np.float64),tuple(sel["left_sequence"]))
    r=_apply_seq(np.asarray(xs,dtype=np.float64),tuple(sel["right_sequence"]))
    return _apply_binary(sel["op"],l,r)

def transfer_selected(task,sel,taskpre,repair):
    tr=_make_rows(task,"transfer",taskpre["training_x"])
    ho=_make_rows(task,"transfer",taskpre["holdout_x"])
    xt=np.asarray([r["x"] for r in tr]); xh=np.asarray([r["x"] for r in ho])
    yt=np.asarray([r["y"] for r in tr]); yh=np.asarray([r["y"] for r in ho])
    Ft=_feature_from_selected(xt,sel)[None,:]
    Fh=_feature_from_selected(xh,sel)[None,:]
    tn,hn,co=_fit_batch(Ft,Fh,xt,xh,yt,yh)
    return {"train_nrmse":float(tn[0]),"holdout_nrmse":float(hn[0]),"coefficients":[float(v) for v in co[0]]}

def run():
    repair=json.loads(REPAIR.read_text()); taskpre=json.loads(TASKS.read_text())
    rows=[]
    for task in taskpre["tasks"]:
        train=_make_rows(task,"seed",taskpre["training_x"])
        hold=_make_rows(task,"seed",taskpre["holdout_x"])
        base=registry.resolve_verified_capability(train,target="y",input_name="x")
        s=search_rows(train,hold,repair)
        transfer=None if s["selected"] is None else transfer_selected(task,s["selected"],taskpre,repair)
        rows.append({
          "id":task["id"],
          "baseline_registry_v8_miss":base.get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",
          **s,
          "transfer":transfer
        })
    passed=all(
      r["baseline_registry_v8_miss"]
      and r["candidate_count"]==int(repair["candidate_count_per_task"])
      and r["selected"] is not None
      and r["selected"]["train_nrmse"]<=float(repair["exact_gate"]["train_nrmse"])
      and r["selected"]["holdout_nrmse"]<=float(repair["exact_gate"]["holdout_nrmse"])
      and r["transfer"] is not None
      and r["transfer"]["holdout_nrmse"]<=float(repair["exact_gate"]["transfer_holdout_nrmse"])
      for r in rows
    )
    return {
      "status":"PASS__COMPLETE_BINARY_ROOT_SEARCH_AND_TRANSFER__ZERO_LEARNED" if passed else "FAIL__COMPLETE_BINARY_ROOT_RESIDUAL",
      "tasks":rows,"task_count":len(rows),
      "persistent_learned_bytes":0,"external_learned_capability_calls":0,"h100_terminal_credit_delta":0
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
