from __future__ import annotations
import itertools,json,time
from pathlib import Path
from typing import Any,Mapping,Sequence
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr
from canonical.runtime import h100_verified_capability_registry_v8 as registry

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_COMPLETE_UNARY_CHAIN_SEARCH_DEPTH6_PRECOMMIT_V1.json"

class Depth5SearchError(ValueError): pass

def apply_sequence(x:float,seq:Sequence[str])->float:
    v=float(x)
    for op in seq:
        z=expr._apply_unary(str(op),v)
        if z is None: raise Depth5SearchError("NONFINITE")
        v=float(z)
    return v

def make_rows(task:Mapping[str,Any],phase:str,xs:Sequence[float]):
    a,b,c=[float(v) for v in task[phase]]
    seq=list(task["sequence"])
    return [{"x":float(x),"y":a+b*float(x)+c*apply_sequence(float(x),seq)} for x in xs]

def fit_rows(train,hold,seq):
    try:
        ft=[apply_sequence(r["x"],seq) for r in train]
        fh=[apply_sequence(r["x"],seq) for r in hold]
    except Depth5SearchError:
        return None
    xt=[float(r["x"]) for r in train]; xh=[float(r["x"]) for r in hold]
    yt=[float(r["y"]) for r in train]; yh=[float(r["y"]) for r in hold]
    co=expr._fit_linear_features([xt,ft],yt)
    if co is None:return None
    pt=[co[0]+co[1]*x+co[2]*f for x,f in zip(xt,ft)]
    ph=[co[0]+co[1]*x+co[2]*f for x,f in zip(xh,fh)]
    return {
      "sequence":list(seq),
      "train_nrmse":expr._nrmse(yt,pt),
      "holdout_nrmse":expr._nrmse(yh,ph),
      "coefficients":[float(v) for v in co]
    }

def search_rows(train,hold,ops,max_depth):
    counts={}; exacts={}; best={}
    start=time.perf_counter()
    for d in range(1,max_depth+1):
        rows=[]
        for seq in itertools.product(tuple(ops),repeat=d):
            f=fit_rows(train,hold,seq)
            if f is not None: rows.append(f)
        counts[d]=len(tuple(itertools.product(tuple(ops),repeat=d)))
        rows.sort(key=lambda r:(max(r["train_nrmse"],r["holdout_nrmse"]),tuple(r["sequence"])))
        best[d]=rows[0] if rows else None
        exacts[d]=[r for r in rows if r["train_nrmse"]<=1e-10 and r["holdout_nrmse"]<=1e-8]
        exacts[d].sort(key=lambda r:tuple(r["sequence"]))
    first=next((d for d in range(1,max_depth+1) if exacts[d]),None)
    return {
      "counts":counts,
      "cumulative":sum(counts.values()),
      "exact_counts":{d:len(exacts[d]) for d in exacts},
      "first_exact_depth":first,
      "selected":None if first is None else exacts[first][0],
      "wall_clock_seconds":time.perf_counter()-start,
      "best":best
    }

def run():
    pre=json.loads(PRE.read_text())
    rows=[]
    for task in pre["fresh_tasks"]:
        train=make_rows(task,"seed",pre["training_x"])
        hold=make_rows(task,"seed",pre["holdout_x"])
        baseline=registry.resolve_verified_capability(train,target="y",input_name="x")
        s=search_rows(train,hold,pre["operator_order"],int(pre["max_depth"]))
        sel=s["selected"]
        transfer=None
        if sel is not None:
            ttrain=make_rows(task,"transfer",pre["training_x"])
            thold=make_rows(task,"transfer",pre["holdout_x"])
            transfer=fit_rows(ttrain,thold,sel["sequence"])
        rows.append({
          "id":task["id"],
          "baseline_registry_v8_miss":baseline.get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",
          "counts":{str(k):v for k,v in s["counts"].items()},
          "cumulative":s["cumulative"],
          "exact_counts":{str(k):v for k,v in s["exact_counts"].items()},
          "first_exact_depth":s["first_exact_depth"],
          "selected":sel,
          "transfer":transfer,
          "wall_clock_seconds":s["wall_clock_seconds"]
        })
    expected={str(k):int(v) for k,v in pre["expected_counts"].items()}
    max_depth=int(pre["max_depth"])
    passed=all(
      r["baseline_registry_v8_miss"]
      and r["counts"]==expected
      and r["cumulative"]==int(pre["expected_cumulative_count"])
      and r["first_exact_depth"]==max_depth
      and all(int(r["exact_counts"][str(d)])==0 for d in range(1,max_depth))
      and r["selected"] is not None
      and r["selected"]["train_nrmse"]<=1e-10
      and r["selected"]["holdout_nrmse"]<=1e-8
      and r["transfer"] is not None
      and r["transfer"]["holdout_nrmse"]<=1e-8
      for r in rows
    )
    return {
      "status":f"PASS__DEPTH{max_depth}_COMPLETE_SEARCH_AND_TRANSFER__ZERO_LEARNED" if passed else f"FAIL__DEPTH{max_depth}_RESIDUAL",
      "tasks":rows,
      "task_count":len(rows),
      "persistent_learned_bytes":0,
      "external_learned_capability_calls":0,
      "h100_terminal_credit_delta":0
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
