"""Route-specific terminal executor for the frozen CAD T0 geometry population.

Preterminal tests may exercise a small deterministic prefix. Only execute_terminal()
may consume the 128 post-freeze cases, and only after canonical all-route launch
authority is true.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Iterable

from canonical.runtime import cad_t0_geometry_population as population
from canonical.runtime import cad_t0_oracle_adapter as oracle
from canonical.runtime import cad_t0_multiplex_scorer as scorer
from canonical.runtime import cad_t0_route_specific_candidate_v1 as candidate

SCHEMA="PROJECT_BRAIN_CAD_T0_ROUTE_SPECIFIC_TERMINAL_EXECUTOR_V1"
BEHAVIOR_ID="CAD_DRAWING_TO_GLOBAL_SOLID_TOPOLOGY_AND_ENVELOPE_001"
ROUTE_POPULATION_VERSION="CAD_T0_GEOMETRY_V1"
SAMPLE_COUNT=128
ROUTE=Path("canonical/governance/CAD_ACTIVE_CONTRACT_END_TO_END_PROOF_ROUTE_V1.json")
AUTHORITY=Path("canonical/governance/TERMINAL_WAVE_EXECUTION_AUTHORITY_V1.json")
MANIFEST=Path("canonical/governance/TERMINAL_ROUTE_SPECIFIC_EXECUTOR_MANIFEST_V1.json")

def case_id(index:int)->str:
    if not isinstance(index,int) or isinstance(index,bool) or not 0<=index<SAMPLE_COUNT:
        raise ValueError("INDEX_OUT_OF_RANGE")
    return f"{ROUTE_POPULATION_VERSION}::slot::{index}"

def derive_seed(commitment:str,beacon:str,cid:str)->int:
    return population.derive_seed(commitment,beacon,cid)

def static_preflight(root:Path=Path("."))->dict[str,Any]:
    errors=[]
    try:
        route=json.loads((root/ROUTE).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema":SCHEMA,"pass":False,"errors":["ROUTE_READ:"+type(exc).__name__]}
    if route.get("behavior_id")!=BEHAVIOR_ID: errors.append("BEHAVIOR_ID_MISMATCH")
    if route.get("terminal_population",{}).get("terminal_result_observed") is not False:
        errors.append("TERMINAL_RESULT_ALREADY_OBSERVED")
    if route.get("fresh_terminal_evidence_consumed")!=0:
        errors.append("FRESH_EVIDENCE_ALREADY_CONSUMED")
    if population.SLOT_COUNT!=SAMPLE_COUNT:
        errors.append("SAMPLE_COUNT_MISMATCH")
    if tuple(population.FAMILIES)!=(
        "BOX_EXTRUDE","CIRCLE_EXTRUDE","BOX_THROUGH_HOLE","REVOLVED_STEPS",
        "SPLINE_REVOLVE","CIRCLE_LOFT","POLYGON_LOFT","NONIDENTIFIABLE_DEPTH"
    ):
        errors.append("FAMILY_SET_DRIFT")
    return {"schema":SCHEMA,"pass":not errors,"errors":sorted(set(errors)),
            "behavior_id":BEHAVIOR_ID,"sample_count":SAMPLE_COUNT,"terminal_authority":False}

def _evaluate_indices(commitment:str,beacon:str,indices:Iterable[int])->dict[str,Any]:
    rows=[]
    for i in indices:
        cid=case_id(i)
        seed=derive_seed(commitment,beacon,cid)
        try:
            hidden=population.generate_case(seed,i)
            public=population.public_case(hidden)
            answer,result=candidate.solve_with_result(public)
            prepared=oracle.prepare_hidden_case(hidden)
            observation=oracle.observe_candidate(prepared,answer,result)
            verdict=scorer.score_case(prepared,answer,observation)
            passed=verdict.get("pass") is True
            errors=verdict.get("errors",[])
        except Exception as exc:
            passed=False
            errors=["EXECUTION_EXCEPTION:"+type(exc).__name__+":"+str(exc)]
        rows.append({"index":i,"case_id":cid,"seed":seed,"pass":passed,"errors":errors})
    return {"schema":SCHEMA,"behavior_id":BEHAVIOR_ID,"case_count":len(rows),
            "pass_count":sum(int(x["pass"]) for x in rows),
            "all_pass":all(x["pass"] for x in rows),
            "failures":[x for x in rows if not x["pass"]],"rows":rows,
            "terminal_authority":False}

def dev_self_check(commitment:str="DEV_COMMITMENT",beacon:str="DEV_NONTERMINAL_BEACON")->dict[str,Any]:
    return _evaluate_indices(commitment,beacon,range(16))

def execute_terminal(*,candidate_package_commitment:str,post_freeze_beacon:str,root:Path=Path("."))->dict[str,Any]:
    pre=static_preflight(root)
    if pre.get("pass") is not True:
        raise ValueError("STATIC_PREFLIGHT_FAILED:"+",".join(pre.get("errors",[])))
    authority=json.loads((root/AUTHORITY).read_text(encoding="utf-8"))
    manifest=json.loads((root/MANIFEST).read_text(encoding="utf-8"))
    if authority.get("execution_authority") is not True:
        raise ValueError("TERMINAL_WAVE_NOT_AUTHORIZED")
    if authority.get("terminal_results_observed")!=0 or authority.get("fresh_terminal_evidence_consumed")!=0:
        raise ValueError("TERMINAL_WAVE_ALREADY_CONSUMED_OR_STATE_DRIFTED")
    if manifest.get("launch_authority") is not True or manifest.get("bound_executor_count")!=12:
        raise ValueError("ALL_ROUTE_EXECUTORS_NOT_BOUND")
    out=_evaluate_indices(candidate_package_commitment,post_freeze_beacon,range(SAMPLE_COUNT))
    out.update({
        "status":"PASS" if out["all_pass"] and out["case_count"]==SAMPLE_COUNT else "FAIL",
        "terminal_authority":True,
        "fresh_terminal_evidence_consumed":SAMPLE_COUNT,
        "case_replacement":False,
        "tuning_replay":False,
        "acceptance_rule":"ALL_128_CASES_PASS",
        "capability_credit_delta":"DEFER_TO_TERMINAL_REDUCER",
        "family_credit_delta":"DEFER_TO_TERMINAL_REDUCER",
    })
    return out
