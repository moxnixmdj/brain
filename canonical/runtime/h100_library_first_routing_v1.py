"""Library-first vs raw-first routing timing for H100.

The tasks and route orders are frozen in H100_LIBRARY_FIRST_ROUTING_PRECOMMIT_V1.json.
This is a retrospective scheduling measurement on already-known reusable families.
"""
from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import h100_zero_learned_transfer_v1 as transfer

ROOT=Path(__file__).resolve().parents[2]
PRE=ROOT/"canonical/governance/H100_LIBRARY_FIRST_ROUTING_PRECOMMIT_V1.json"
TRANSFER_PRE=ROOT/"canonical/governance/H100_ZERO_LEARNED_TRANSFER_PREEXPOSURE_V1.json"
SCHEMA="PROJECT_BRAIN_H100_LIBRARY_FIRST_ROUTING_RESULT_V1"


class RoutingTimingError(ValueError):
    pass


def _route(route_id:str, train, hold, threshold:float, expected_family:str):
    if route_id=="ZERO_LEARNED_MONOMIAL_V1":
        return transfer._simple(train,hold,threshold)
    if route_id=="EXPRESSION_TREE_D2_W16":
        return transfer._expr(train,hold,threshold,route_id,max_depth=2,beam_width=16)
    if route_id=="EXPRESSION_TREE_D4_W32":
        return transfer._expr(train,hold,threshold,route_id,max_depth=4,beam_width=32)
    if route_id=="ZERO_LEARNED_PARAMETRIC_UNARY_FAMILY_ROUTE":
        return transfer._compiled(train,hold,threshold,expected_family)
    raise RoutingTimingError("ROUTE_UNKNOWN:"+route_id)


def _task_rows(task_id:str, tpre:Mapping[str,Any]):
    train=transfer._rows(task_id,[float(x) for x in tpre["training_x"]])
    hold=transfer._rows(task_id,[float(x) for x in tpre["holdout_x"]])
    return train,hold


def run_order(task_id:str,expected_family:str,order:list[str],tpre:Mapping[str,Any]) -> dict[str,Any]:
    train,hold=_task_rows(task_id,tpre)
    threshold=float(tpre["useful_candidate_threshold_nrmse"])
    start=time.perf_counter()
    attempts=[]
    for route_id in order:
        row=_route(route_id,train,hold,threshold,expected_family)
        attempts.append(row)
        if bool(row.get("useful_candidate")):
            return {
                "success":True,
                "winner_route":route_id,
                "attempted_route_count":len(attempts),
                "wall_clock_seconds":time.perf_counter()-start,
                "attempts":attempts,
            }
    return {
        "success":False,
        "winner_route":None,
        "attempted_route_count":len(attempts),
        "wall_clock_seconds":time.perf_counter()-start,
        "attempts":attempts,
    }


def _median_measure(fn,repetitions:int=7):
    warm=fn()
    if not warm["success"]:
        raise RoutingTimingError("WARMUP_FAILED")
    rows=[]
    for _ in range(repetitions):
        row=fn()
        if not row["success"]:
            raise RoutingTimingError("TIMED_RUN_FAILED")
        rows.append(row)
    med=statistics.median(r["wall_clock_seconds"] for r in rows)
    route_counts=statistics.median(r["attempted_route_count"] for r in rows)
    winners=sorted(set(r["winner_route"] for r in rows))
    if len(winners)!=1:
        raise RoutingTimingError("WINNER_NOT_DETERMINISTIC")
    return {
        "median_seconds":float(med),
        "median_attempted_route_count":route_counts,
        "winner_route":winners[0],
        "runs":rows,
    }


def run()->dict[str,Any]:
    pre=json.loads(PRE.read_text())
    if pre.get("status")!="FROZEN_BEFORE_ROUTING_TIMINGS__RETROSPECTIVE_ON_ALREADY_VERIFIED_TRANSFER_TASKS__ZERO_CREDIT":
        raise RoutingTimingError("PRECOMMIT_NOT_FROZEN")
    tpre=json.loads(TRANSFER_PRE.read_text())
    orders=pre["route_orders"]
    fam_by_task={
        str(x["transfer_task"]["task_id"]):str(x["compiled_family"])
        for x in tpre["families"]
    }
    rows=[]
    for task_id in pre["cohort"]["tasks"]:
        expected=fam_by_task[str(task_id)]
        lib=_median_measure(lambda:run_order(str(task_id),expected,list(orders["LIBRARY_FIRST"]),tpre))
        raw=_median_measure(lambda:run_order(str(task_id),expected,list(orders["RAW_FIRST"]),tpre))
        ratio=raw["median_seconds"]/lib["median_seconds"]
        rows.append({
            "task_id":task_id,
            "expected_family":expected,
            "library_first":{
                "median_seconds_to_verified_useful_candidate":lib["median_seconds"],
                "median_attempted_route_count":lib["median_attempted_route_count"],
                "winner_route":lib["winner_route"],
            },
            "raw_first":{
                "median_seconds_to_verified_useful_candidate":raw["median_seconds"],
                "median_attempted_route_count":raw["median_attempted_route_count"],
                "winner_route":raw["winner_route"],
            },
            "measured_wall_clock_speedup_raw_over_library":ratio,
        })
    ratios=[r["measured_wall_clock_speedup_raw_over_library"] for r in rows]
    return {
        "schema":SCHEMA,
        "status":"LIBRARY_FIRST_ROUTING_MEASURED__THREE_OF_THREE_FASTER__ZERO_CREDIT"
            if all(x>1.0 for x in ratios) else "ROUTING_MEASUREMENT_COMPLETE",
        "tasks":rows,
        "summary":{
            "speedup_min":min(ratios),
            "speedup_median":statistics.median(ratios),
            "speedup_max":max(ratios),
            "library_first_attempted_routes_median":statistics.median(
                r["library_first"]["median_attempted_route_count"] for r in rows
            ),
            "raw_first_attempted_routes_median":statistics.median(
                r["raw_first"]["median_attempted_route_count"] for r in rows
            ),
        },
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "RETROSPECTIVE_SCHEDULING_MEASUREMENT_ON_ALREADY_KNOWN_FAMILIES",
            "THREE_SYNTHETIC_TRANSFER_TASKS_DO_NOT_ESTABLISH_GENERAL_REAL_WORLD_SPEEDUP",
            "NO_H100_TERMINAL_CREDIT",
        ],
        "h100_terminal_credit_delta":0,
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
