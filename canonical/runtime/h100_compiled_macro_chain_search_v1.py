"""Compiled macro-chain search experiment for H100.

Uses three independently verified depth-4 unary-chain capabilities as fixed
macro-operators. Searches all macro sequences of length 1..2 (12 candidates)
without target-score prefix pruning.

This is a bounded compiled-capability search demonstration, not universal search.
"""
from __future__ import annotations

import itertools
import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr
from canonical.runtime import h100_verified_capability_registry_v8 as registry

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_COMPILED_MACRO_CHAIN_SEARCH_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_COMPILED_MACRO_CHAIN_SEARCH_RESULT_V1"


class MacroChainSearchError(ValueError):
    pass


def _macro_map(pre:Mapping[str,Any])->dict[str,tuple[str,...]]:
    out={}
    for row in pre["verified_macros"]:
        out[str(row["macro_id"])]=tuple(str(x) for x in row["primitive_sequence"])
    return out


def _apply_macro_chain(x:float, macros:Sequence[str], table:Mapping[str,Sequence[str]])->float:
    value=float(x)
    for macro in macros:
        if macro not in table:
            raise MacroChainSearchError("MACRO_UNKNOWN:"+str(macro))
        value=registry._apply_sequence(value,table[macro])
    return float(value)


def _task_feature(task:Mapping[str,Any], x:float, table:Mapping[str,Sequence[str]])->float:
    return _apply_macro_chain(float(x),task["macro_sequence_inner_to_outer"],table)


def _truth(task:Mapping[str,Any], phase:str, x:float, table:Mapping[str,Sequence[str]])->float:
    coeff=task["seed_coefficients"] if phase=="seed" else task["transfer_coefficients"]
    f=_task_feature(task,float(x),table)
    return float(coeff[0])+float(coeff[1])*float(x)+float(coeff[2])*f


def _rows(task:Mapping[str,Any], phase:str, xs:Sequence[float], table:Mapping[str,Sequence[str]]):
    return [{"x":float(x),"y":_truth(task,phase,float(x),table)} for x in xs]


def _signature(macros:Sequence[str])->str:
    return "->".join(str(x) for x in macros)


def _fit(
    train:Sequence[Mapping[str,float]],
    hold:Sequence[Mapping[str,float]],
    macros:Sequence[str],
    table:Mapping[str,Sequence[str]],
)->dict[str,Any] | None:
    try:
        train_f=[_apply_macro_chain(float(r["x"]),macros,table) for r in train]
        hold_f=[_apply_macro_chain(float(r["x"]),macros,table) for r in hold]
    except (MacroChainSearchError,ValueError,TypeError):
        return None
    tx=[float(r["x"]) for r in train]
    hx=[float(r["x"]) for r in hold]
    ty=[float(r["y"]) for r in train]
    hy=[float(r["y"]) for r in hold]
    coeff=expr._fit_linear_features([tx,train_f],ty)
    if coeff is None:
        return None
    pt=[coeff[0]+coeff[1]*x+coeff[2]*f for x,f in zip(tx,train_f)]
    ph=[coeff[0]+coeff[1]*x+coeff[2]*f for x,f in zip(hx,hold_f)]
    return {
        "macro_sequence":[str(x) for x in macros],
        "signature":_signature(macros),
        "macro_depth":len(macros),
        "coefficients":[float(x) for x in coeff],
        "train_nrmse":expr._nrmse(ty,pt),
        "holdout_nrmse":expr._nrmse(hy,ph),
    }


def _registry_miss(rows)->bool:
    out=registry.resolve_verified_capability(rows,target="y",input_name="x")
    return out.get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"


def search_task(task:Mapping[str,Any],pre:Mapping[str,Any])->dict[str,Any]:
    table=_macro_map(pre)
    macro_ids=tuple(str(x["macro_id"]) for x in pre["verified_macros"])
    train=_rows(task,"seed",pre["x_population"]["training_x"],table)
    hold=_rows(task,"seed",pre["x_population"]["holdout_x"],table)
    exact_by_depth={}
    best_by_depth={}
    count_by_depth={}
    start=time.perf_counter()
    for depth in (1,2):
        candidates=[]
        count=0
        for macros in itertools.product(macro_ids,repeat=depth):
            count+=1
            fit=_fit(train,hold,macros,table)
            if fit is not None:
                candidates.append(fit)
        count_by_depth[depth]=count
        candidates.sort(key=lambda r:(max(float(r["train_nrmse"]),float(r["holdout_nrmse"])),r["signature"]))
        best_by_depth[depth]=candidates[0] if candidates else None
        exact=[r for r in candidates if float(r["train_nrmse"])<=1e-10 and float(r["holdout_nrmse"])<=1e-8]
        exact.sort(key=lambda r:r["signature"])
        exact_by_depth[depth]=exact
    elapsed=time.perf_counter()-start
    first=next((d for d in (1,2) if exact_by_depth[d]),None)
    selected=None if first is None else exact_by_depth[first][0]
    return {
        "train":train,
        "count_by_depth":{str(k):v for k,v in count_by_depth.items()},
        "candidate_count":sum(count_by_depth.values()),
        "exact_count_by_depth":{str(k):len(v) for k,v in exact_by_depth.items()},
        "best_by_depth":{str(k):v for k,v in best_by_depth.items()},
        "first_exact_macro_depth":first,
        "selected":selected,
        "wall_clock_seconds":elapsed,
    }


def _transfer(task:Mapping[str,Any],selected:Mapping[str,Any],pre:Mapping[str,Any])->dict[str,Any]:
    table=_macro_map(pre)
    train=_rows(task,"transfer",pre["x_population"]["training_x"],table)
    hold=_rows(task,"transfer",pre["x_population"]["holdout_x"],table)
    fit=_fit(train,hold,selected["macro_sequence"],table)
    if fit is None:
        return {"status":"TRANSFER_REFIT_FAILED","holdout_nrmse":None}
    return {
        "status":"TRANSFER_REFIT_OK",
        "macro_sequence":fit["macro_sequence"],
        "signature":fit["signature"],
        "coefficients":fit["coefficients"],
        "train_nrmse":fit["train_nrmse"],
        "holdout_nrmse":fit["holdout_nrmse"],
    }


def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    table=_macro_map(pre)
    tasks=[]
    for task in pre["fresh_tasks"]:
        search=search_task(task,pre)
        transfer=None if search["selected"] is None else _transfer(task,search["selected"],pre)
        seed=_rows(task,"seed",pre["x_population"]["training_x"],table)
        tasks.append({
            "task_id":task["id"],
            "baseline_registry_v8_miss":_registry_miss(seed),
            "primitive_sequence_length":len(task["primitive_sequence_inner_to_outer"]),
            "candidate_count":search["candidate_count"],
            "count_by_depth":search["count_by_depth"],
            "exact_count_by_depth":search["exact_count_by_depth"],
            "first_exact_macro_depth":search["first_exact_macro_depth"],
            "selected":search["selected"],
            "search_wall_clock_seconds":search["wall_clock_seconds"],
            "transfer":transfer,
        })

    ratio=float(pre["primitive_complete_chain_count_through_depth8"])/12.0
    passed=all(
        row["baseline_registry_v8_miss"]
        and row["primitive_sequence_length"]==8
        and row["candidate_count"]==12
        and row["count_by_depth"]=={"1":3,"2":9}
        and int(row["exact_count_by_depth"]["1"])==0
        and row["first_exact_macro_depth"]==2
        and row["selected"] is not None
        and float(row["selected"]["holdout_nrmse"])<=1e-8
        and row["transfer"] is not None
        and row["transfer"]["status"]=="TRANSFER_REFIT_OK"
        and float(row["transfer"]["holdout_nrmse"])<=1e-8
        for row in tasks
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__THREE_OF_THREE_DEPTH8_MACRO_COMPOSITIONS__TWELVE_CANDIDATE_SEARCH__ZERO_CREDIT" if passed else "FAIL__MACRO_CHAIN_SEARCH_RESIDUAL",
        "task_count":len(tasks),
        "tasks":tasks,
        "macro_candidate_count_per_task":12,
        "primitive_depth8_complete_chain_count":int(pre["primitive_complete_chain_count_through_depth8"]),
        "search_space_cardinality_ratio_primitive_over_macro":ratio,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "PRIMITIVE_SEARCH_SPACE_RATIO_IS_CARDINALITY_NOT_MEASURED_PRIMITIVE_WALL_CLOCK",
            "SYNTACTIC_DEPTH8_IS_NOT_MINIMAL_SEMANTIC_COMPLEXITY",
            "MACRO_SEARCH_IS_FINITE_AND_USES_THREE_VERIFIED_MACROS",
            "NO_H100_TERMINAL_CREDIT",
        ],
        "h100_terminal_credit_delta":0,
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
