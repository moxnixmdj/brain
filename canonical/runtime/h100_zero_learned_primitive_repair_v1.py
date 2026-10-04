"""Phase-2 replay of the three frozen H100 zero-learned primitive residuals.

The phase-1 task definitions, observations, holdouts and success threshold are
reused unchanged. Only the newly pre-exposed zero-learned parametric unary route
is evaluated.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from canonical.runtime import h100_zero_learned_novelty_stress_v1 as phase1
from canonical.runtime import h100_zero_learned_parametric_unary_v1 as route

ROOT=Path(__file__).resolve().parents[2]
PHASE2=ROOT/"canonical/governance/H100_ZERO_LEARNED_PRIMITIVE_REPAIR_PREEXPOSURE_V1.json"
SCHEMA="PROJECT_BRAIN_H100_ZERO_LEARNED_PRIMITIVE_REPAIR_RESULT_V1"


class PrimitiveRepairError(ValueError):
    pass


def evaluate_task(task_id:str)->dict[str,Any]:
    p2=json.loads(PHASE2.read_text())
    allowed=[row["task_id"] for row in p2["tasks"]]
    if task_id not in allowed:
        raise PrimitiveRepairError("TASK_NOT_FROZEN_PHASE2:"+task_id)
    p1=json.loads(phase1.PREEXPOSURE.read_text())
    tasks={row["id"]:row for row in p1["population"]["tasks"]}
    task=tasks[task_id]
    if int(task["arity"])!=1:
        raise PrimitiveRepairError("PHASE2_TASK_NOT_UNARY:"+task_id)
    train=phase1._rows(task,p1,holdout=False)
    hold=phase1._rows(task,p1,holdout=True)
    out=route.discover(train,target="y",input_name="x",exact_nrmse=1e-8)
    candidate=out.get("best_candidate")
    holdout_nrmse=None
    if candidate is not None:
        try:
            pred=[route.predict(candidate,row) for row in hold]
            holdout_nrmse=phase1._nrmse([row["y"] for row in hold],pred)
        except Exception:
            holdout_nrmse=None
    internal_nrmse=None if candidate is None else float(candidate.get("nrmse",math.inf))
    useful=bool(
        out.get("status")=="EXACT_CANDIDATE_FOUND"
        and internal_nrmse is not None
        and internal_nrmse<=1e-8
        and holdout_nrmse is not None
        and holdout_nrmse<=1e-7
    )
    return {
        "task_id":task_id,
        "route_id":"ZERO_LEARNED_PARAMETRIC_UNARY_V1",
        "useful_candidate":useful,
        "solver_status":out.get("status"),
        "candidate_family":None if candidate is None else candidate.get("family"),
        "internal_nrmse":internal_nrmse,
        "holdout_nrmse":holdout_nrmse,
        "persistent_learned_bytes":int(out.get("persistent_learned_bytes",0)),
        "external_frontier_model_calls":int(out.get("external_frontier_model_calls",0)),
        "external_learned_capability_calls":int(out.get("external_learned_capability_calls",0)),
        "random_search":bool(out.get("random_search",False)),
        "dynamic_code_execution":bool(out.get("dynamic_code_execution",False)),
    }


def run()->dict[str,Any]:
    p2=json.loads(PHASE2.read_text())
    rows=[evaluate_task(row["task_id"]) for row in p2["tasks"]]
    solved=sum(row["useful_candidate"] for row in rows)
    max_learned=max(row["persistent_learned_bytes"] for row in rows)
    external=sum(row["external_learned_capability_calls"] for row in rows)
    return {
        "schema":SCHEMA,
        "status":"PHASE2_3_OF_3_REPAIRED" if solved==3 else "PHASE2_RESIDUAL_REMAINS",
        "tasks_solved":solved,
        "task_count":3,
        "all_three_repaired":solved==3,
        "max_persistent_learned_bytes":max_learned,
        "external_learned_capability_calls":external,
        "tasks":rows,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_terminal_reality_authority":False,
        "hard_nonclaims":[
            "PHASE2_REPAIR_IS_NOT_OPEN_WORLD_PROOF",
            "PHASE2_REPAIR_IS_NOT_UNKNOWN_DOMAIN_ACCEPTANCE",
            "PHASE2_REPAIR_IS_NOT_H100_TERMINAL_CREDIT",
        ],
    }


def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--task",choices=["PERIODIC_SINE","EXPONENTIAL","SIGN_STEP"])
    parser.add_argument("--require-useful",action="store_true")
    args=parser.parse_args()
    out=evaluate_task(args.task) if args.task else run()
    print(json.dumps(out,indent=2,sort_keys=True))
    if args.require_useful:
        useful=bool(out.get("useful_candidate")) if args.task else bool(out.get("all_three_repaired"))
        if not useful:
            raise SystemExit(3)


if __name__=="__main__":
    main()
