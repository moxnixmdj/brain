"""Zero-learned paired transfer stress for H100.

The population and both A/B tasks are pre-exposed before outcomes.  Proposal
probability is defined exactly over a frozen finite proposal distribution:
uniform sampling with replacement from the proposal catalog.  Because the
catalog is finite and all proposal generators are exhaustively evaluated, p is
the exact success mass of that distribution, not an estimate from repeated
deterministic reruns.

This is finite synthetic transfer evidence only and creates no acceptance credit.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import h100_zero_learned_mechanism_synthesizer_v1 as simple
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as expr
from canonical.runtime import h100_zero_learned_parametric_unary_v1 as param

ROOT = Path(__file__).resolve().parents[2]
PRE = ROOT / "canonical/governance/H100_ZERO_LEARNED_TRANSFER_PREEXPOSURE_V1.json"
SCHEMA = "PROJECT_BRAIN_H100_ZERO_LEARNED_TRANSFER_RESULT_V1"


class TransferStressError(ValueError):
    pass


def _truth(task_id: str, x: float) -> float:
    if task_id == "SIN_A":
        return 0.4 + 0.15*x + 1.3*math.sin(1.73*x + 0.4)
    if task_id == "SIN_B":
        return -0.7 + 0.25*x + 0.8*math.sin(2.41*x - 0.6)
    if task_id == "EXP_A":
        return 1.2*math.exp(0.31*abs(x))
    if task_id == "EXP_B":
        return 0.7*math.exp(0.47*abs(x))
    if task_id == "STEP_A":
        return 0.3 + 1.4*(1.0 if x >= -0.6 else -1.0)
    if task_id == "STEP_B":
        return -0.2 + 0.9*(1.0 if x >= 0.8 else -1.0)
    raise TransferStressError("TASK_UNKNOWN:" + task_id)


def _rows(task_id: str, xs: list[float]) -> list[dict[str, float]]:
    return [{"x": float(x), "y": _truth(task_id, float(x))} for x in xs]


def _nrmse(actual: list[float], predicted: list[float]) -> float:
    mean = sum(actual)/len(actual)
    spread = math.sqrt(sum((v-mean)**2 for v in actual)/len(actual))
    scale = max(spread, max(abs(v) for v in actual)*1e-9, 1e-12)
    return math.sqrt(sum((a-b)**2 for a,b in zip(actual,predicted))/len(actual))/scale


def _simple(train, hold, threshold):
    start=time.perf_counter()
    out=simple.discover(train,target="y",inputs=["x"],max_active_variables=3,top_k=16)
    best=math.inf
    for c in out.get("candidates",[]):
        try:
            pred=[simple.predict(c,row) for row in hold]
            err=_nrmse([r["y"] for r in hold],pred)
        except Exception:
            continue
        internal=max(float(c.get("nrmse",math.inf)),float(c.get("validation_nrmse",math.inf)))
        if internal <= 1e-8:
            best=min(best,err)
    return {
        "route_id":"ZERO_LEARNED_MONOMIAL_V1",
        "useful_candidate":best <= threshold,
        "holdout_nrmse":None if not math.isfinite(best) else best,
        "wall_clock_seconds":time.perf_counter()-start,
    }


def _expr(train, hold, threshold, route_id, *, max_depth, beam_width):
    start=time.perf_counter()
    out=expr.discover(train,target="y",inputs=["x"],max_depth=max_depth,beam_width=beam_width)
    c=out.get("best_candidate")
    err=math.inf
    if c is not None:
        try:
            pred=[expr.predict(c,row) for row in hold]
            err=_nrmse([r["y"] for r in hold],pred)
        except Exception:
            pass
    internal=math.inf if c is None else max(float(c.get("nrmse",math.inf)),float(c.get("validation_nrmse",math.inf)))
    return {
        "route_id":route_id,
        "useful_candidate":err <= threshold and internal <= 1e-8,
        "holdout_nrmse":None if not math.isfinite(err) else err,
        "wall_clock_seconds":time.perf_counter()-start,
    }


def _compiled(train, hold, threshold, expected_family):
    start=time.perf_counter()
    out=param.discover(train,target="y",input_name="x",exact_nrmse=1e-8)
    c=out.get("best_candidate")
    err=math.inf
    family=None if c is None else c.get("family")
    if c is not None and family == expected_family:
        try:
            pred=[param.predict(c,row) for row in hold]
            err=_nrmse([r["y"] for r in hold],pred)
        except Exception:
            pass
    return {
        "route_id":"ZERO_LEARNED_PARAMETRIC_UNARY_FAMILY_ROUTE",
        "useful_candidate":family == expected_family and err <= threshold and float(c.get("nrmse",math.inf)) <= 1e-8 if c is not None else False,
        "candidate_family":family,
        "holdout_nrmse":None if not math.isfinite(err) else err,
        "wall_clock_seconds":time.perf_counter()-start,
    }


def _t95(p: float) -> int | None:
    if p <= 0.0:
        return None
    if p >= 1.0:
        return 1
    return int(math.ceil(math.log(0.05)/math.log1p(-p)))


def _evaluate_catalog(task_id: str, expected_family: str, include_compiled: bool, pre: Mapping[str,Any]):
    train=_rows(task_id,[float(x) for x in pre["training_x"]])
    hold=_rows(task_id,[float(x) for x in pre["holdout_x"]])
    threshold=float(pre["useful_candidate_threshold_nrmse"])
    rows=[
        _simple(train,hold,threshold),
        _expr(train,hold,threshold,"EXPRESSION_TREE_D2_W16",max_depth=2,beam_width=16),
        _expr(train,hold,threshold,"EXPRESSION_TREE_D4_W32",max_depth=4,beam_width=32),
    ]
    if include_compiled:
        rows.append(_compiled(train,hold,threshold,expected_family))
    successes=sum(bool(r["useful_candidate"]) for r in rows)
    p=successes/len(rows)
    mean_cost=sum(float(r["wall_clock_seconds"]) for r in rows)/len(rows)
    n95=_t95(p)
    return {
        "task_id":task_id,
        "proposal_catalog_size":len(rows),
        "successful_proposals":successes,
        "p_exact":p,
        "n95_proposals":n95,
        "mean_proposal_wall_clock_seconds":mean_cost,
        "t95_expected_wall_clock_seconds":None if n95 is None else mean_cost*n95,
        "routes":rows,
    }


def run() -> dict[str,Any]:
    pre=json.loads(PRE.read_text())
    if pre.get("status")!="FROZEN_BEFORE_OUTCOMES__PUBLIC_SYNTHETIC_NONTERMINAL__ZERO_CREDIT":
        raise TransferStressError("PREEXPOSURE_NOT_FROZEN")
    families=[]
    all_pass=True
    for family in pre["families"]:
        expected=str(family["compiled_family"])
        a=str(family["compile_seed"]["task_id"])
        b=str(family["transfer_task"]["task_id"])
        a_baseline=_evaluate_catalog(a,expected,False,pre)
        a_compiled=_evaluate_catalog(a,expected,True,pre)
        b_baseline=_evaluate_catalog(b,expected,False,pre)
        b_compiled=_evaluate_catalog(b,expected,True,pre)
        transfer_pass=(
            a_compiled["p_exact"] > a_baseline["p_exact"]
            and b_compiled["p_exact"] > b_baseline["p_exact"]
            and b_compiled["n95_proposals"] is not None
            and b_baseline["n95_proposals"] is None
        )
        all_pass=all_pass and transfer_pass
        families.append({
            "family_id":family["id"],
            "compiled_family":expected,
            "compile_seed":{"baseline":a_baseline,"post_compile":a_compiled},
            "transfer_task":{"baseline":b_baseline,"post_compile":b_compiled},
            "transfer_pass":transfer_pass,
            "reuse_effect":"UNBOUNDED_TO_FINITE_T95" if transfer_pass else "NO_VERIFIED_TRANSFER_GAIN",
        })
    return {
        "schema":SCHEMA,
        "status":"FINITE_ZERO_LEARNED_TRANSFER_PASS" if all_pass else "TRANSFER_RESIDUAL_REMAINS",
        "family_count":len(families),
        "families":families,
        "all_families_transfer_pass":all_pass,
        "persistent_learned_bytes":0,
        "external_frontier_model_calls":0,
        "external_learned_capability_calls":0,
        "hard_nonclaims":[
            "FINITE_SYNTHETIC_TRANSFER_IS_NOT_OPEN_WORLD_PROPOSAL_PROBABILITY",
            "FINITE_TRANSFER_IS_NOT_UNKNOWN_DOMAIN_ACCEPTANCE",
            "NO_H100_TERMINAL_CREDIT",
        ],
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
