"""Fail-closed causal-soundness veto for P1 V5.

This counterexample separates a visible failed check from a causally necessary
failure. An early SCOPE violation sits on one arm of an ALTERNATIVE dependency;
the other arm is healthy, so repairing the SCOPE violation cannot rescue the
terminal outcome. A later STATE_TRANSITION defect is the unique executable
rescuer. V5 currently chooses the early failed ancestor.
"""
from __future__ import annotations
import json
from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as v5

SCHEMA="PROJECT_BRAIN_P1_V5_CAUSAL_SOUNDNESS_VETO_V1"

def _check(aid,kind,passed):
    return {"id":f"{aid}:{kind}","kind":kind,"pass":passed,"evidence":[f"receipt:{aid}:{kind}"]}

def counterexample():
    rows=[
        {"action_id":"A0","depends_on":[],"reads":[],"writes":["code:seed"],"dependency_composition":"SEQUENTIAL","checks":[_check("A0","INVARIANT",True)]},
        {"action_id":"A1","depends_on":["A0"],"reads":["code:seed"],"writes":["code:left"],"dependency_composition":"SEQUENTIAL","checks":[_check("A1","SCOPE",False)]},
        {"action_id":"A2","depends_on":["A0"],"reads":["code:seed"],"writes":["code:right"],"dependency_composition":"SEQUENTIAL","checks":[_check("A2","INVARIANT",True)]},
        {"action_id":"A3","depends_on":["A1","A2"],"reads":["code:left","code:right"],"writes":["code:merged"],"dependency_composition":"ALTERNATIVE","checks":[_check("A3","INVARIANT",True)]},
        {"action_id":"A4","depends_on":["A3"],"reads":["code:merged"],"writes":["code:terminal"],"dependency_composition":"SEQUENTIAL","checks":[_check("A4","STATE_TRANSITION",False)]},
    ]
    return {
        "task":{
            "domain":"CODE",
            "trajectory":rows,
            "terminal_failed_resources":["code:terminal"],
            "declared_effect_semantics":{
                "repair_atoms":[
                    {"check_id":"A1:SCOPE","effect":"RESTORE_LOCAL_CHECK"},
                    {"check_id":"A4:STATE_TRANSITION","effect":"RESTORE_LOCAL_CHECK"}
                ],
                "dependency_composition":{
                    "SEQUENTIAL":"ALL_DEPENDENCIES_REQUIRED",
                    "CONJUNCTIVE":"ALL_DEPENDENCIES_REQUIRED",
                    "ALTERNATIVE":"ANY_DEPENDENCY_SUFFICIENT"
                }
            }
        }
    }

def _exec_success(case,repaired):
    rows=case["task"]["trajectory"]
    available={}
    for row in rows:
        local=all(c["pass"] or c["id"] in repaired for c in row["checks"])
        deps=row["depends_on"]
        comp=row["dependency_composition"]
        if not deps:
            depok=True
        elif comp=="ALTERNATIVE":
            depok=any(available[d] for d in deps)
        else:
            depok=all(available[d] for d in deps)
        available[row["action_id"]]=local and depok
    return available["A4"]

def evaluate():
    case=counterexample()
    out=v5.solve(case)
    baseline=_exec_success(case,set())
    early=_exec_success(case,{"A1:SCOPE"})
    later=_exec_success(case,{"A4:STATE_TRANSITION"})
    reproduced=(
        baseline is False and early is False and later is True
        and out.get("status")=="IDENTIFIED"
        and out.get("cause_action_ids")==["A1"]
        and out.get("mechanism_classes")==["SCOPE"]
    )
    return {
        "schema":SCHEMA,
        "status":"FAIL_CLOSED__V5_FALSE_EARLIEST_CAUSAL_COUNTEREXAMPLE_REPRODUCED" if reproduced else "COUNTEREXAMPLE_NOT_REPRODUCED",
        "route_falsified":reproduced,
        "v5_output":out,
        "executable_outcomes":{
            "baseline_success":baseline,
            "repair_early_scope_success":early,
            "repair_later_state_transition_success":later
        },
        "required_true_cause_action":"A4",
        "required_true_mechanism":"STATE_TRANSITION",
        "p1_v5_scope_superset_admissible":False if reproduced else None,
        "terminal_results_replayed":0,
        "new_reality_units_consumed":0,
        "incremental_spend_usd":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
