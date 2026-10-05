"""Complete bounded unary-chain search repair for H100.

Enumerates every unary operator sequence of depth 1..4 over the frozen expression
operator set. Unlike the score-pruned beam search, candidate reachability does
not depend on whether intermediate prefixes are predictive.

This is complete only for the frozen unary-chain slice, not general programs.
"""
from __future__ import annotations

import itertools
import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr
from canonical.runtime import h100_verified_capability_registry_v7 as registry

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_COMPLETE_UNARY_CHAIN_SEARCH_PRECOMMIT_V1.json"
SCHEMA="PROJECT_BRAIN_H100_COMPLETE_UNARY_CHAIN_SEARCH_RESULT_V1"


class CompleteUnaryChainError(ValueError):
    pass


def _apply_sequence(x: float, sequence: Sequence[str]) -> float:
    value=float(x)
    for op in sequence:
        nxt=expr._apply_unary(str(op),value)
        if nxt is None:
            raise CompleteUnaryChainError("CHAIN_NONFINITE:"+str(op))
        value=float(nxt)
    return value


def _tree(sequence: Sequence[str]) -> dict[str,Any]:
    tree:dict[str,Any]={"op":"var","name":"x"}
    for op in sequence:
        tree={"op":str(op),"arg":tree}
    return tree


def _signature(sequence: Sequence[str]) -> str:
    return expr._structural_signature(_tree(sequence),("x",))


def _truth(task: Mapping[str,Any], phase: str, x: float) -> float:
    seq=task["operator_sequence_inner_to_outer"]
    f=_apply_sequence(x,seq)
    tid=str(task["id"])
    if tid=="CHAIN_A":
        return (0.45-0.18*x+1.25*f) if phase=="seed" else (-0.7+0.31*x-0.85*f)
    if tid=="CHAIN_B":
        return (-0.2+0.11*x+0.95*f) if phase=="seed" else (0.9-0.22*x+1.4*f)
    if tid=="CHAIN_C":
        return (0.15+0.27*x-1.1*f) if phase=="seed" else (-0.35-0.08*x+0.72*f)
    raise CompleteUnaryChainError("TASK_UNKNOWN:"+tid)


def _rows(task: Mapping[str,Any], phase: str, xs: Sequence[float]) -> list[dict[str,float]]:
    return [{"x":float(x),"y":_truth(task,phase,float(x))} for x in xs]


def _fit_sequence(
    train: Sequence[Mapping[str,float]],
    hold: Sequence[Mapping[str,float]],
    sequence: Sequence[str],
) -> dict[str,Any] | None:
    try:
        train_chain=[_apply_sequence(float(r["x"]),sequence) for r in train]
        hold_chain=[_apply_sequence(float(r["x"]),sequence) for r in hold]
    except CompleteUnaryChainError:
        return None
    train_x=[float(r["x"]) for r in train]
    hold_x=[float(r["x"]) for r in hold]
    train_y=[float(r["y"]) for r in train]
    hold_y=[float(r["y"]) for r in hold]
    coeff=expr._fit_linear_features([train_x,train_chain],train_y)
    if coeff is None:
        return None
    pred_train=[coeff[0]+coeff[1]*x+coeff[2]*f for x,f in zip(train_x,train_chain)]
    pred_hold=[coeff[0]+coeff[1]*x+coeff[2]*f for x,f in zip(hold_x,hold_chain)]
    return {
        "sequence":list(sequence),
        "signature":_signature(sequence),
        "depth":len(sequence),
        "coefficients":[float(x) for x in coeff],
        "train_nrmse":expr._nrmse(train_y,pred_train),
        "holdout_nrmse":expr._nrmse(hold_y,pred_hold),
    }


def search_task(task: Mapping[str,Any], pre: Mapping[str,Any]) -> dict[str,Any]:
    ops=tuple(str(x) for x in pre["frozen_unary_operator_order"])
    max_depth=int(pre["max_depth"])
    train=_rows(task,"seed",[float(x) for x in pre["x_population"]["training_x"]])
    hold=_rows(task,"seed",[float(x) for x in pre["x_population"]["holdout_x"]])
    exact_train=1e-10
    exact_hold=1e-8

    counts:dict[int,int]={}
    exact_by_depth:dict[int,list[dict[str,Any]]]={}
    best_by_depth:dict[int,dict[str,Any]|None]={}
    start=time.perf_counter()

    for depth in range(1,max_depth+1):
        count=0
        rows=[]
        for sequence in itertools.product(ops,repeat=depth):
            count+=1
            fit=_fit_sequence(train,hold,sequence)
            if fit is not None:
                rows.append(fit)
        counts[depth]=count
        rows.sort(key=lambda r:(max(float(r["train_nrmse"]),float(r["holdout_nrmse"])),r["signature"]))
        best_by_depth[depth]=rows[0] if rows else None
        exact=[r for r in rows if float(r["train_nrmse"])<=exact_train and float(r["holdout_nrmse"])<=exact_hold]
        exact.sort(key=lambda r:r["signature"])
        exact_by_depth[depth]=exact

    elapsed=time.perf_counter()-start
    first_exact_depth=next((d for d in range(1,max_depth+1) if exact_by_depth[d]),None)
    selected=None if first_exact_depth is None else exact_by_depth[first_exact_depth][0]
    return {
        "train":train,
        "hold":hold,
        "counts_by_depth":{str(k):v for k,v in counts.items()},
        "cumulative_count":sum(counts.values()),
        "best_by_depth":{str(k):v for k,v in best_by_depth.items()},
        "exact_count_by_depth":{str(k):len(v) for k,v in exact_by_depth.items()},
        "first_exact_depth":first_exact_depth,
        "selected":selected,
        "wall_clock_seconds":elapsed,
    }


def _transfer(task: Mapping[str,Any], selected: Mapping[str,Any], pre: Mapping[str,Any]) -> dict[str,Any]:
    train=_rows(task,"transfer",[float(x) for x in pre["x_population"]["training_x"]])
    hold=_rows(task,"transfer",[float(x) for x in pre["x_population"]["holdout_x"]])
    fit=_fit_sequence(train,hold,selected["sequence"])
    if fit is None:
        return {"status":"TRANSFER_REFIT_FAILED","holdout_nrmse":None}
    return {
        "status":"TRANSFER_REFIT_OK",
        "sequence":fit["sequence"],
        "signature":fit["signature"],
        "train_nrmse":fit["train_nrmse"],
        "holdout_nrmse":fit["holdout_nrmse"],
        "coefficients":fit["coefficients"],
    }


def _registry_miss(rows: Sequence[Mapping[str,float]]) -> bool:
    out=registry.resolve_verified_capability(rows,target="y",input_name="x")
    return out.get("status")=="LIBRARY_MISS__RAW_SYNTHESIS_ALLOWED"


def run() -> dict[str,Any]:
    pre=json.loads(PRE.read_text())
    if "FROZEN_AFTER_BEAM_PRUNING_FAILURE" not in str(pre.get("status","")):
        raise CompleteUnaryChainError("PRECOMMIT_NOT_FROZEN")
    tasks=[]
    expected_counts={str(k):int(v) for k,v in [(1,6),(2,36),(3,216),(4,1296)]}

    for task in pre["fresh_tasks"]:
        search=search_task(task,pre)
        selected=search["selected"]
        transfer=None if selected is None else _transfer(task,selected,pre)
        seed_train=_rows(task,"seed",[float(x) for x in pre["x_population"]["training_x"]])
        tasks.append({
            "task_id":task["id"],
            "expected_depth_for_audit_only":task["expected_depth_for_audit_only"],
            "baseline_registry_v7_miss":_registry_miss(seed_train),
            "counts_by_depth":search["counts_by_depth"],
            "cumulative_count":search["cumulative_count"],
            "exact_count_by_depth":search["exact_count_by_depth"],
            "first_exact_depth":search["first_exact_depth"],
            "selected":selected,
            "search_wall_clock_seconds":search["wall_clock_seconds"],
            "transfer":transfer,
        })

    passed=all(
        row["baseline_registry_v7_miss"]
        and row["counts_by_depth"]==expected_counts
        and row["cumulative_count"]==1554
        and row["first_exact_depth"]==4
        and all(int(row["exact_count_by_depth"][str(d)])==0 for d in (1,2,3))
        and row["selected"] is not None
        and float(row["selected"]["train_nrmse"])<=1e-10
        and float(row["selected"]["holdout_nrmse"])<=1e-8
        and row["transfer"] is not None
        and row["transfer"]["status"]=="TRANSFER_REFIT_OK"
        and float(row["transfer"]["holdout_nrmse"])<=1e-8
        for row in tasks
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__THREE_OF_THREE_COMPLETE_DEPTH4_UNARY_CHAIN_SEARCH_AND_TRANSFER__ZERO_CREDIT" if passed else "FAIL__COMPLETE_UNARY_CHAIN_RESIDUAL",
        "task_count":len(tasks),
        "tasks":tasks,
        "enumeration_count_per_task":1554,
        "total_chains_evaluated":1554*len(tasks),
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "COMPLETE_UNARY_CHAIN_ENUMERATION_IS_NOT_COMPLETE_GENERAL_PROGRAM_SEARCH",
            "BINARY_TREE_SEARCH_REMAINS_SEPARATE",
            "DEPTH4_IS_FINITE",
            "NO_H100_TERMINAL_CREDIT",
        ],
        "h100_terminal_credit_delta":0,
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
