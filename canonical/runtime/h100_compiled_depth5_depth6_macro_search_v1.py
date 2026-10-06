from __future__ import annotations
import itertools,json,time
from pathlib import Path
from typing import Any,Mapping,Sequence
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr
from canonical.runtime import h100_verified_capability_registry_v8 as registry

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_COMPILED_DEPTH5_DEPTH6_MACRO_SEARCH_PRECOMMIT_V1.json"

class MacroSearchError(ValueError): pass

def macro_table(pre):
    return {str(m["macro_id"]):tuple(str(x) for x in m["sequence"]) for m in pre["verified_macros"]}

def apply_macro_chain(x:float,macros:Sequence[str],table)->float:
    v=float(x)
    for m in macros:
        if m not in table: raise MacroSearchError("MACRO_UNKNOWN")
        v=registry._apply_sequence(v,table[m])
    return float(v)

def make_rows(task,phase,xs,table):
    a,b,c=[float(v) for v in task[phase]]
    hidden=list(task["macro_sequence"])
    return [{"x":float(x),"y":a+b*float(x)+c*apply_macro_chain(float(x),hidden,table)} for x in xs]

def fit_rows(train,hold,macros,table):
    try:
        ft=[apply_macro_chain(r["x"],macros,table) for r in train]
        fh=[apply_macro_chain(r["x"],macros,table) for r in hold]
    except MacroSearchError:
        return None
    xt=[float(r["x"]) for r in train]; xh=[float(r["x"]) for r in hold]
    yt=[float(r["y"]) for r in train]; yh=[float(r["y"]) for r in hold]
    co=expr._fit_linear_features([xt,ft],yt)
    if co is None:return None
    pt=[co[0]+co[1]*x+co[2]*f for x,f in zip(xt,ft)]
    ph=[co[0]+co[1]*x+co[2]*f for x,f in zip(xh,fh)]
    return {
      "macro_sequence":list(macros),
      "coefficients":[float(v) for v in co],
      "train_nrmse":expr._nrmse(yt,pt),
      "holdout_nrmse":expr._nrmse(yh,ph)
    }

def search_rows(train,hold,macro_ids):
    exacts={}; counts={}; start=time.perf_counter()
    for d in (1,2):
        rows=[]
        for seq in itertools.product(tuple(macro_ids),repeat=d):
            f=fit_rows(train,hold,seq,SEARCH_TABLE)
            if f is not None: rows.append(f)
        counts[d]=len(tuple(itertools.product(tuple(macro_ids),repeat=d)))
        rows.sort(key=lambda r:(max(r["train_nrmse"],r["holdout_nrmse"]),tuple(r["macro_sequence"])))
        exacts[d]=[r for r in rows if r["train_nrmse"]<=1e-10 and r["holdout_nrmse"]<=1e-8]
        exacts[d].sort(key=lambda r:tuple(r["macro_sequence"]))
    first=next((d for d in (1,2) if exacts[d]),None)
    return {
      "counts":counts,
      "candidate_count":sum(counts.values()),
      "exact_counts":{d:len(exacts[d]) for d in exacts},
      "first_exact_depth":first,
      "selected":None if first is None else exacts[first][0],
      "wall_clock_seconds":time.perf_counter()-start
    }

SEARCH_TABLE={}

def run():
    global SEARCH_TABLE
    pre=json.loads(PRE.read_text())
    SEARCH_TABLE=macro_table(pre)
    macro_ids=[str(m["macro_id"]) for m in pre["verified_macros"]]
    rows=[]
    for task in pre["fresh_tasks"]:
        train=make_rows(task,"seed",pre["training_x"],SEARCH_TABLE)
        hold=make_rows(task,"seed",pre["holdout_x"],SEARCH_TABLE)
        baseline=registry.resolve_verified_capability(train,target="y",input_name="x")
        s=search_rows(train,hold,macro_ids)
        sel=s["selected"]
        transfer=None
        if sel is not None:
            tt=make_rows(task,"transfer",pre["training_x"],SEARCH_TABLE)
            th=make_rows(task,"transfer",pre["holdout_x"],SEARCH_TABLE)
            transfer=fit_rows(tt,th,sel["macro_sequence"],SEARCH_TABLE)
        rows.append({
          "id":task["id"],
          "primitive_depth":int(task["primitive_depth"]),
          "primitive_complete_count":int(task["primitive_complete_count"]),
          "baseline_registry_v8_miss":baseline.get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED",
          "candidate_count":s["candidate_count"],
          "counts":{str(k):v for k,v in s["counts"].items()},
          "exact_counts":{str(k):v for k,v in s["exact_counts"].items()},
          "first_exact_macro_depth":s["first_exact_depth"],
          "selected":sel,
          "transfer":transfer,
          "wall_clock_seconds":s["wall_clock_seconds"]
        })
    passed=all(
      r["baseline_registry_v8_miss"]
      and r["candidate_count"]==int(pre["macro_candidate_count"])
      and r["counts"]=={"1":6,"2":36}
      and r["exact_counts"]["1"]==0
      and r["first_exact_macro_depth"]==2
      and r["selected"] is not None
      and r["selected"]["holdout_nrmse"]<=1e-8
      and r["transfer"] is not None
      and r["transfer"]["holdout_nrmse"]<=1e-8
      for r in rows
    )
    return {
      "status":"PASS__DEPTH10_12_MACRO_SEARCH_AND_TRANSFER__ZERO_LEARNED" if passed else "FAIL__MACRO_RESIDUAL",
      "tasks":rows,
      "task_count":len(rows),
      "persistent_learned_bytes":0,
      "external_learned_capability_calls":0,
      "h100_terminal_credit_delta":0
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
