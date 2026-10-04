"""Universal Learning V6 safe adaptive experiment synthesizer.

Computes an exact finite adaptive probe tree over the currently declared mechanism
class while preserving an open-world boundary:
- every probe must be independently proved safe under all admissible worlds,
- every load-bearing within-class outcome model is exact-byte receipt bound,
- exact optimality is only over the declared finite model class,
- without an independent hypothesis-coverage proof, the tree may guide safe
  learning but can never prove the world model exhaustive or authorize a terminal
  decision merely because declared candidates agree.
"""
from __future__ import annotations
from fractions import Fraction
from functools import lru_cache
import hashlib, json
from typing import Any, Mapping, Sequence

from canonical.runtime import mechanism_discovery_v6 as mech
from canonical.runtime import open_world_hypothesis_guard_v4 as guard4

SCHEMA="PROJECT_BRAIN_SAFE_ADAPTIVE_EXPERIMENT_SYNTHESIZER_V6"

class ExperimentSynthesisError(ValueError):
    pass

def _f(x:Any,name:str)->Fraction:
    if isinstance(x,bool):
        raise ExperimentSynthesisError(name.upper()+"_INVALID")
    try:
        out=x if isinstance(x,Fraction) else Fraction(str(x))
    except Exception as exc:
        raise ExperimentSynthesisError(name.upper()+"_INVALID") from exc
    if out<0:
        raise ExperimentSynthesisError(name.upper()+"_NEGATIVE")
    return out

def outcome_digest(*,probe_id:str,outcomes:Mapping[str,Any])->str:
    pid=str(probe_id or "").strip()
    if not pid:
        raise ExperimentSynthesisError("PROBE_ID_REQUIRED")
    rows=sorted((str(k),str(v)) for k,v in outcomes.items())
    body=json.dumps({"probe_id":pid,"outcomes":rows},sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def _candidate_digest(candidates:Sequence[Mapping[str,Any]])->str:
    rows=[]
    for c in mech.normalize_candidates(candidates):
        rows.append({"id":c["id"],"digest":c["digest"],"best_action":c["best_action"]})
    body=json.dumps(rows,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def admit_probe(*,environment_id:str,goal_id:str,candidates:Sequence[Mapping[str,Any]],probe:Mapping[str,Any])->dict[str,Any]:
    env=str(environment_id or "").strip(); goal=str(goal_id or "").strip()
    pid=str(probe.get("id") or "").strip()
    if not env or not goal or not pid:
        raise ExperimentSynthesisError("ENVIRONMENT_GOAL_PROBE_REQUIRED")
    if _f(probe.get("incremental_spend_usd_ub",0),"incremental_spend_usd_ub")>0:
        raise ExperimentSynthesisError("POSITIVE_INCREMENTAL_SPEND_FORBIDDEN")
    cs=mech.normalize_candidates(candidates)
    ids={c["id"] for c in cs}
    outcomes=probe.get("outcome_by_mechanism")
    if not isinstance(outcomes,Mapping):
        raise ExperimentSynthesisError("OUTCOME_MAP_REQUIRED")
    if ids-set(map(str,outcomes.keys())):
        raise ExperimentSynthesisError("OUTCOME_MAP_INCOMPLETE")
    normalized_outcomes={str(k):str(v) for k,v in outcomes.items()}
    for c in cs:
        predicted=c["predictions"].get(pid)
        if predicted is not None and predicted!=normalized_outcomes[c["id"]]:
            raise ExperimentSynthesisError("MECHANISM_AND_OUTCOME_MODEL_DISAGREE:"+c["id"])

    safety=probe.get("safety_receipt")
    if not isinstance(safety,Mapping):
        raise ExperimentSynthesisError("SAFETY_RECEIPT_REQUIRED")
    if safety.get("independent_verified") is not True or safety.get("exact_byte_bound") is not True or safety.get("conclusion")!="success":
        raise ExperimentSynthesisError("SAFETY_RECEIPT_INVALID")
    if safety.get("safe_under_all_admissible_worlds") is not True:
        raise ExperimentSynthesisError("OPEN_WORLD_SAFETY_NOT_PROVED")
    if str(safety.get("environment_id") or "").strip()!=env or str(safety.get("goal_id") or "").strip()!=goal or str(safety.get("probe_id") or "").strip()!=pid:
        raise ExperimentSynthesisError("SAFETY_SCOPE_MISMATCH")

    model=probe.get("outcome_model_receipt")
    if not isinstance(model,Mapping):
        raise ExperimentSynthesisError("OUTCOME_MODEL_RECEIPT_REQUIRED")
    if model.get("independent_verified") is not True or model.get("exact_byte_bound") is not True or model.get("conclusion")!="success":
        raise ExperimentSynthesisError("OUTCOME_MODEL_RECEIPT_INVALID")
    if model.get("deterministic_within_bound_mechanism_class") is not True:
        raise ExperimentSynthesisError("DETERMINISTIC_MODEL_NOT_PROVED")
    if model.get("decision_relevant_outcome_partition_complete_within_class") is not True:
        raise ExperimentSynthesisError("OUTCOME_PARTITION_NOT_PROVED")
    if model.get("observation_only_or_state_restored") is not True:
        raise ExperimentSynthesisError("STATE_RESTORATION_NOT_PROVED")
    epoch=str(model.get("experiment_epoch") or "").strip()
    state=str(model.get("state_fingerprint") or "").strip()
    if not epoch or not state:
        raise ExperimentSynthesisError("EXPERIMENT_EPOCH_AND_STATE_REQUIRED")
    if str(safety.get("experiment_epoch") or "").strip()!=epoch or str(safety.get("state_fingerprint") or "").strip()!=state:
        raise ExperimentSynthesisError("SAFETY_MODEL_STATE_MISMATCH")
    if str(model.get("environment_id") or "").strip()!=env or str(model.get("goal_id") or "").strip()!=goal or str(model.get("probe_id") or "").strip()!=pid:
        raise ExperimentSynthesisError("OUTCOME_MODEL_SCOPE_MISMATCH")
    if model.get("mechanism_class_sha256")!=_candidate_digest(cs):
        raise ExperimentSynthesisError("MECHANISM_CLASS_DIGEST_MISMATCH")
    if model.get("outcome_map_sha256")!=outcome_digest(probe_id=pid,outcomes=normalized_outcomes):
        raise ExperimentSynthesisError("OUTCOME_MAP_DIGEST_MISMATCH")

    srid=str(safety.get("receipt_id") or "").strip()
    mrid=str(model.get("receipt_id") or "").strip()
    if not srid or not mrid:
        raise ExperimentSynthesisError("RECEIPT_ID_REQUIRED")
    return {
        "id":pid,
        "outcome_by_mechanism":normalized_outcomes,
        "wall_clock":_f(probe.get("wall_clock",0),"wall_clock"),
        "resource_cost":_f(probe.get("resource_cost",0),"resource_cost"),
        "residual_risk":_f(probe.get("residual_risk",0),"residual_risk"),
        "safety_receipt":srid,
        "outcome_model_receipt":mrid,
        "experiment_epoch":epoch,
        "state_fingerprint":state,
    }

def synthesize(*,environment_id:str,goal_id:str,candidates:Sequence[Mapping[str,Any]],probes:Sequence[Mapping[str,Any]],hypothesis_coverage_receipt:Mapping[str,Any]|None=None)->dict[str,Any]:
    cs=mech.normalize_candidates(candidates)
    if not cs:
        raise ExperimentSynthesisError("CANDIDATES_REQUIRED")
    ids=[c["id"] for c in cs]
    best={c["id"]:c["best_action"] for c in cs}

    # Reuse V4's exact open-world coverage contract by adapting mechanisms to hypotheses.
    hypotheses=[{"id":c["id"],"plausible":True,"best_action":c["best_action"]} for c in cs]
    coverage=guard4.close_space(
        environment_id=environment_id,
        goal_id=goal_id,
        hypotheses=hypotheses,
        coverage_receipt=hypothesis_coverage_receipt,
    )

    admitted=[];seen=set()
    for raw in probes:
        p=admit_probe(environment_id=environment_id,goal_id=goal_id,candidates=cs,probe=raw)
        if p["id"] in seen:
            raise ExperimentSynthesisError("PROBE_ID_DUPLICATE")
        seen.add(p["id"]);admitted.append(p)
    if not admitted:
        return {
            "schema":SCHEMA,"status":"NO_ADMISSIBLE_SAFE_PROBES","plan":None,
            "hypothesis_space_closed":coverage["closed"],"open_world_terminal_decision_authorized":False,
            "acceptance_credit_delta":0,"ownership_credit_delta":0,
        }
    epochs={p["experiment_epoch"] for p in admitted}
    states={p["state_fingerprint"] for p in admitted}
    if len(epochs)!=1 or len(states)!=1:
        raise ExperimentSynthesisError("PROBE_EPOCH_OR_STATE_MISMATCH")
    by={p["id"]:p for p in admitted}

    def solved(state:frozenset[str])->str|None:
        acts={best[x] for x in state}
        return next(iter(acts)) if len(acts)==1 else None

    @lru_cache(maxsize=None)
    def dp(state:frozenset[str],remaining:tuple[str,...]):
        action=solved(state)
        if action is not None:
            return (Fraction(0),Fraction(0),Fraction(0),0,{"type":"DECISION_CLASS_COLLAPSED","action":action,"mechanisms":sorted(state)})
        winner=None
        for pid in remaining:
            p=by[pid]
            groups={}
            for mid in state:
                outcome=p["outcome_by_mechanism"][mid]
                groups.setdefault(outcome,set()).add(mid)
            if len(groups)<=1:
                continue
            rest=tuple(x for x in remaining if x!=pid)
            children={};vectors=[];feasible=True
            for outcome,group in sorted(groups.items()):
                child=dp(frozenset(group),rest)
                if child is None:
                    feasible=False;break
                wt,wc,wr,ws,tree=child
                vectors.append((wt,wc,wr,ws))
                children[outcome]=tree
            if not feasible:
                continue
            worst=max(vectors)
            vector=(p["wall_clock"]+worst[0],p["resource_cost"]+worst[1],p["residual_risk"]+worst[2],1+worst[3])
            tree={
                "type":"SAFE_PROBE","probe_id":pid,
                "branches":children,
                "safety_receipt":p["safety_receipt"],
                "outcome_model_receipt":p["outcome_model_receipt"],
            }
            cand=(vector,pid,tree)
            if winner is None or (cand[0],cand[1])<(winner[0],winner[1]):
                winner=cand
        if winner is None:
            return None
        v=winner[0]
        return (v[0],v[1],v[2],v[3],winner[2])

    result=dp(frozenset(ids),tuple(sorted(by)))
    if result is None:
        return {
            "schema":SCHEMA,"status":"NO_FINITE_SAFE_RESOLUTION_PLAN","plan":None,
            "hypothesis_space_closed":coverage["closed"],"open_world_terminal_decision_authorized":False,
            "acceptance_credit_delta":0,"ownership_credit_delta":0,
        }
    wall,cost,risk,steps,tree=result
    return {
        "schema":SCHEMA,
        "status":"OPEN_WORLD_EXACT_ADAPTIVE_PLAN" if coverage["closed"] else "CONDITIONAL_EXACT_PLAN_OVER_DECLARED_MECHANISM_CLASS",
        "optimization":"EXACT_FINITE_LEXICOGRAPHIC_MINIMUM_WORST_CASE__WALL_CLOCK_THEN_RESOURCE_COST_THEN_RESIDUAL_RISK_THEN_STEPS",
        "hypothesis_space_closed":coverage["closed"],
        "open_world_terminal_decision_authorized":coverage["closed"],
        "recommended_probe":tree.get("probe_id") if tree.get("type")=="SAFE_PROBE" else None,
        "worst_case_wall_clock":str(wall),
        "worst_case_resource_cost":str(cost),
        "worst_case_residual_risk":str(risk),
        "worst_case_steps":steps,
        "experiment_epoch":next(iter(epochs)),
        "state_fingerprint":next(iter(states)),
        "plan":tree,
        "unexpected_outcome_rule":"FALSIFY_DECLARED_MECHANISM_CLASS_AND_EXPAND_HYPOTHESIS_LANGUAGE",
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "fresh_reality_authority":False,
    }
