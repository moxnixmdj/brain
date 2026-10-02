"""Fail-closed compiler for the TB4 minimum carrier recovery cut v1."""
from __future__ import annotations
import math
from typing import Any, Mapping
SCHEMA="PROJECT_BRAIN_TB4_MINIMUM_CARRIER_RECOVERY_CUT_VERDICT_V1"

def evaluate(spec: Mapping[str, Any]) -> dict[str, Any]:
    errors=[]
    score=spec.get("frozen_score_math")
    rows=spec.get("resource_exceed_tasks")
    chosen=spec.get("minimum_recovery_set")
    env=spec.get("minimum_carrier_envelope")
    if not isinstance(score,Mapping): errors.append("SCORE_MATH_MISSING")
    if not isinstance(rows,list) or not all(isinstance(x,Mapping) for x in rows): errors.append("RESOURCE_ROWS_INVALID")
    if not isinstance(chosen,list) or not all(isinstance(x,str) for x in chosen): errors.append("RECOVERY_SET_INVALID")
    if not isinstance(env,Mapping): errors.append("CARRIER_ENVELOPE_INVALID")
    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":errors,"execution_authority":False}
    trials=score.get("trials_per_task")
    required=score.get("required_successes")
    current=score.get("current_remaining_creditable_tasks")
    for name,val in (("trials_per_task",trials),("required_successes",required),("current_remaining_creditable_tasks",current)):
        if isinstance(val,bool) or not isinstance(val,int) or val<0: errors.append("INVALID_"+name.upper())
    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":errors,"execution_authority":False}
    needed=max(0,math.ceil((required-current*trials)/trials))
    if score.get("additional_creditable_tasks_needed")!=needed: errors.append("RECOVERY_COUNT_MATH_MISMATCH")
    if score.get("current_upper_bound_successes")!=current*trials: errors.append("CURRENT_UPPER_BOUND_MISMATCH")
    if score.get("reopened_creditable_task_count")!=current+needed: errors.append("REOPENED_TASK_COUNT_MISMATCH")
    if score.get("reopened_upper_bound_successes")!=(current+needed)*trials: errors.append("REOPENED_UPPER_BOUND_MISMATCH")
    if len(rows)!=12 or len({x.get("task") for x in rows})!=12: errors.append("RESOURCE_ROW_SET_NOT_EXACT_TWELVE")
    rowmap={x.get("task"):x for x in rows if isinstance(x.get("task"),str)}
    if len(chosen)!=needed or len(set(chosen))!=needed: errors.append("RECOVERY_SET_NOT_MINIMUM_CARDINALITY")
    if any(x not in rowmap for x in chosen): errors.append("RECOVERY_TASK_NOT_IN_RESOURCE_EXCEED_SET")
    admissible=[]
    for task,row in rowmap.items():
        nums=(row.get("cpus"),row.get("memory_mb"),row.get("storage_mb"),row.get("gpus"))
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or v<0 for v in nums):
            errors.append("INVALID_RESOURCE_ROW:"+str(task)); continue
        if row.get("gpus")==0 and row.get("cpus")<=8 and row.get("memory_mb")<=16384 and row.get("storage_mb")<=51200:
            admissible.append(task)
    if sorted(chosen)!=sorted(admissible) or len(admissible)!=8: errors.append("RECOVERY_SET_NOT_EXACT_MINIMUM_ENVELOPE_SET")
    maxima={
        "cpus_at_least":max(rowmap[t]["cpus"] for t in chosen) if chosen else 0,
        "usable_memory_mb_at_least":max(rowmap[t]["memory_mb"] for t in chosen) if chosen else 0,
        "free_storage_mb_at_least":max(rowmap[t]["storage_mb"] for t in chosen) if chosen else 0,
        "gpus_required":max(rowmap[t]["gpus"] for t in chosen) if chosen else 0,
    }
    for k,v in maxima.items():
        if env.get(k)!=v: errors.append("ENVELOPE_MISMATCH:"+k)
    if env.get("docker_required") is not True or env.get("docker_compose_required") is not True:
        errors.append("CONTAINER_RUNTIME_REQUIREMENTS_MUST_STAY_TRUE")
    state=spec.get("verification_state")
    if not isinstance(state,Mapping) or state.get("concrete_zero_cost_carrier_bound") is not False or state.get("protocol_equivalence_bound") is not False or state.get("attainability_recompiled") is not False:
        errors.append("CANDIDATE_MUST_NOT_SELF_AUTHORIZE")
    if spec.get("execution_authority") is not False or spec.get("promotion_authority") is not False:
        errors.append("CANDIDATE_AUTHORITY_MUST_BE_FALSE")
    return {
        "schema":SCHEMA,
        "status":"PASS__MINIMUM_EIGHT_TASK_RESOURCE_RECOVERY_CUT__CARRIER_STILL_UNBOUND__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
        "pass":not errors,
        "errors":sorted(set(errors)),
        "minimum_additional_creditable_tasks":needed,
        "selected_task_count":len(chosen) if not errors else 0,
        "minimum_carrier_envelope":maxima if not errors else None,
        "projected_creditable_task_count":current+needed if not errors else None,
        "projected_upper_bound_successes":(current+needed)*trials if not errors else None,
        "required_successes":required,
        "attainability_would_reopen_at_boundary":(current+needed)*trials>=required if not errors else False,
        "concrete_carrier_bound":False,
        "protocol_equivalence_bound":False,
        "execution_authority":False,
        "promotion_authority":False,
        "new_reality_units_consumed":0,
        "capability_credit_delta":0,
        "family_credit_delta":0
    }
