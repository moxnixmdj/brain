"""Typed, benchmark-independent scientific capability controller.

Routes only from structured problem fields. No benchmark identifiers, model calls,
network calls, dynamic code, or task-specific answer material are used.
"""
from __future__ import annotations
import math
from typing import Any, Mapping, Sequence

from canonical.runtime import capability_planner
from canonical.runtime import h100_expression_tree_symbolic_regression_v1 as symbolic
from canonical.runtime import g0_finite_typed_rule_synthesis as rules
from canonical.runtime import abductive_residual_theorem_v1 as abduction
from canonical.runtime import tb_science_zero_model_scientific_kernel_v1 as periodic
from canonical.runtime.explicit_recovery_planner import RepairAction, plan_recovery

SCHEMA="PROJECT_BRAIN_GENERAL_SCIENTIFIC_CAPABILITY_CONTROLLER_V1"
MODEL_DEPENDENCY_COUNT=0
EXTERNAL_MODEL_RUNTIME_CALLS=0
NETWORK_DEPENDENCY_COUNT=0
SYMBOLIC="SYMBOLIC_REGRESSION"
RULE="FINITE_RULE_SYNTHESIS"
ABDUCTION="ABDUCTIVE_RESIDUAL_ANALYSIS"
PERIODIC="SHARED_PERIOD_FITTING"

def _fail(reason,details=None):
    out={"schema":SCHEMA,"status":"FAIL_CLOSED","reason":reason,"verified":False,
         "model_dependency_count":0,"external_model_runtime_calls":0,
         "network_dependency_count":0,"terminal_authority":False}
    if details: out["details"]=dict(details)
    return out

def infer_signature(problem:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(problem,Mapping): return _fail("PROBLEM_NOT_MAPPING")
    hits=[]
    rows=problem.get("rows")
    if isinstance(rows,Sequence) and not isinstance(rows,(str,bytes)) and isinstance(problem.get("target"),str):
        hits.append(SYMBOLIC)
    if all(k in problem for k in ("predicates","examples","emit")): hits.append(RULE)
    if isinstance(problem.get("abduction"),Mapping): hits.append(ABDUCTION)
    series=problem.get("series")
    if isinstance(series,Sequence) and not isinstance(series,(str,bytes)) and series: hits.append(PERIODIC)
    if not hits: return _fail("NO_TYPED_SCIENTIFIC_SIGNATURE")
    if len(hits)!=1: return _fail("AMBIGUOUS_TYPED_SCIENTIFIC_SIGNATURE",{"matches":sorted(hits)})
    return {"schema":"PROJECT_BRAIN_SCIENTIFIC_PROBLEM_SIGNATURE_V1",
            "status":"TYPED_SCIENTIFIC_SIGNATURE_IDENTIFIED","family":hits[0],
            "routing_basis":"STRUCTURED_PROBLEM_FIELDS_ONLY","terminal_authority":False}

def _caps(family:str):
    solver={SYMBOLIC:"CAP_SCI_SYMBOLIC",RULE:"CAP_SCI_RULE",ABDUCTION:"CAP_SCI_ABDUCTION",
            PERIODIC:"CAP_SCI_PERIODIC"}[family]
    return [
      {"id":solver,"requires":["TYPED_PROBLEM"],"provides":["CANDIDATE"],"cost":1,
       "action":{"type":"invoke","args":{"family":family}},"result_fields":["result"]},
      {"id":"CAP_SCI_VERIFY","requires":["CANDIDATE"],"provides":["VERIFIED"],"cost":0.25,
       "action":{"type":"verify","args":{"family":family,"candidate":{"$effect_result":{"effect":"CANDIDATE","field":"result"}}}},
       "result_fields":["verified"]},
    ]

def derive_plan(family:str):
    return capability_planner.plan_actions({
      "initial_facts":["TYPED_PROBLEM"],"target_effects":["VERIFIED"],
      "capabilities":_caps(family),"finish_summary":"SCIENTIFIC_RESULT_VERIFIED","max_expansions":64})

def _symbolic(problem,trace):
    depth=int(problem.get("max_depth",1))
    if not 1<=depth<=4: raise ValueError("SYMBOLIC_MAX_DEPTH_INVALID")
    kw={"target":str(problem["target"]),"inputs":problem.get("inputs"),"max_depth":depth,
        "beam_width":int(problem.get("beam_width",24)),
        "pair_feature_pool":int(problem.get("pair_feature_pool",20)),
        "exact_nrmse":float(problem.get("exact_nrmse",1e-8))}
    out=symbolic.discover(problem["rows"],**kw)
    trace.append({"event":"SYMBOLIC_SEARCH","depth":depth,"status":out.get("status")})
    if out.get("status")!="EXACT_CANDIDATE_FOUND" and depth<4:
        rec=plan_recovery({"SEARCH_DEPTH_BUDGET_EXHAUSTED"},{"SYMBOLIC_GRAMMAR_VERIFIED"},[
          RepairAction("EXPAND_SYMBOLIC_SEARCH_DEPTH",frozenset({"SEARCH_DEPTH_BUDGET_EXHAUSTED"}),
                       frozenset({"SYMBOLIC_GRAMMAR_VERIFIED"}),1.0,0.0,True,True)])
        trace.append({"event":"RECOVERY_PLAN","result":rec})
        if rec.get("status")=="SELECT":
            kw["max_depth"]=min(4,max(2,depth+1))
            out=symbolic.discover(problem["rows"],**kw)
            trace.append({"event":"SYMBOLIC_SEARCH_AFTER_RECOVERY","depth":kw["max_depth"],"status":out.get("status")})
    return out

def _rule(problem):
    ps=[rules.PredicateSpec(str(x.get("predicate_id") or ""),str(x.get("predicate_type") or ""),
                            dict(x.get("source") or {}),float(x.get("cost",1)))
        for x in problem["predicates"]]
    es=[rules.RuleExample(str(x.get("example_id") or ""),frozenset(str(v) for v in x.get("facts",[])),
                          bool(x.get("positive")),dict(x.get("source") or {}))
        for x in problem["examples"]]
    return rules.synthesize_minimal_conjunctive_rule(predicates=ps,examples=es,emit=dict(problem["emit"]))

def _periodic(problem):
    ss=[]
    for i,row in enumerate(problem["series"]):
        pts=[]
        for j,pair in enumerate(row["points"]):
            t,y=float(pair[0]),float(pair[1])
            if not math.isfinite(t) or not math.isfinite(y): raise ValueError("SERIES_POINT_NONFINITE")
            pts.append((t,y,j))
        ss.append({"source":str(row.get("name") or f"series_{i}"),"time_key":"time","value_key":"value","points":pts})
    return periodic.fit_shared_period(ss)

def _invoke(family,problem,trace):
    if family==SYMBOLIC: return _symbolic(problem,trace)
    if family==RULE: return _rule(problem)
    if family==ABDUCTION: return abduction.evaluate(problem["abduction"])
    if family==PERIODIC: return _periodic(problem)
    raise ValueError("UNSUPPORTED_FAMILY")

def _verify(family,result,problem):
    if family==SYMBOLIC:
        b=result.get("best_candidate")
        lim=float(result.get("exact_nrmse_threshold",0))
        ok=result.get("status")=="EXACT_CANDIDATE_FOUND" and isinstance(b,Mapping) and float(b.get("nrmse",math.inf))<=lim and float(b.get("validation_nrmse",math.inf))<=lim
    elif family==RULE:
        ok=str(result.get("status") or "").startswith("SYNTHESIZED_") and bool(result.get("rules"))
    elif family==ABDUCTION:
        ok=result.get("status")=="EXACT_WEAKEST_SUFFICIENT_RESIDUALS_COMPUTED" and result.get("all_targets_reachable") is True
    elif family==PERIODIC:
        fits=result.get("fits"); p=result.get("period")
        min_r2=float(problem.get("acceptance",{}).get("min_r2",0)) if isinstance(problem.get("acceptance"),Mapping) else 0
        ok=isinstance(p,(int,float)) and math.isfinite(float(p)) and float(p)>0 and isinstance(fits,list) and bool(fits) and all(float(x.get("r2",-math.inf))>=min_r2 for x in fits)
    else: ok=False
    return {"pass":bool(ok)}

def solve(problem:Mapping[str,Any])->dict[str,Any]:
    sig=infer_signature(problem)
    if sig.get("status")!="TYPED_SCIENTIFIC_SIGNATURE_IDENTIFIED": return sig
    family=sig["family"]; trace=[]
    try:
        plan=derive_plan(family)
        trace.append({"event":"CAPABILITY_PLAN_DERIVED","plan":list(plan["planning"]["plan"])})
        result=_invoke(family,problem,trace)
        verify=_verify(family,result,problem)
    except Exception as exc:
        return _fail("SCIENTIFIC_CAPABILITY_EXECUTION_EXCEPTION",
                     {"family":family,"exception_type":type(exc).__name__,"exception":str(exc)[:200]})
    trace.append({"event":"RESULT_VERIFICATION","verification":verify})
    status="PASS__VERIFIED_BENCHMARK_INDEPENDENT_SCIENTIFIC_RESULT" if verify["pass"] else "SCIENTIFIC_RESULT_NOT_VERIFIED"
    return {"schema":SCHEMA,"status":status,"family":family,"signature":sig,"plan":plan,
            "trace":trace,"result":result,"verification":verify,"verified":verify["pass"],
            "model_dependency_count":0,"external_model_runtime_calls":0,"network_dependency_count":0,
            "dynamic_code_execution":False,"benchmark_identifier_used_for_routing":False,
            "terminal_authority":False}
