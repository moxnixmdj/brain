"""Fail-closed verifier for P1 minimum-reality cut V1."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from canonical.runtime.minimum_reality_cut_v2 import solve

ROOT=Path(__file__).resolve().parents[2]
INPUT=ROOT/"canonical/governance/P1_MINIMUM_REALITY_CUT_INPUT_V1.json"
SCHEMA="PROJECT_BRAIN_P1_MINIMUM_REALITY_CUT_VERIFICATION_V1"

def evaluate(data:dict[str,Any]|None=None)->dict[str,Any]:
    d=data if data is not None else json.loads(INPUT.read_text())
    errors=[]
    if d.get("behavior_id")!="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
        errors.append("BEHAVIOR_ID_DRIFT")
    if d.get("execution_authority") is not False:
        errors.append("INPUT_PREMATURE_EXECUTION_AUTHORITY")
    if d.get("fresh_reality_units_consumed_so_far")!=0:
        errors.append("REALITY_ALREADY_CONSUMED")
    if d.get("incremental_spend_usd")!=0:
        errors.append("NONZERO_SPEND")
    obs=d.get("observations") or []
    by={x.get("id"):x for x in obs if isinstance(x,dict)}
    shared=by.get("P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH")
    if not isinstance(shared,dict):
        errors.append("SHARED_BATCH_MISSING")
    else:
        if set(shared.get("covers") or [])!=set(d.get("requirements") or []):
            errors.append("SHARED_BATCH_NOT_FULL_COVER")
        required=set(shared.get("admissibility") or [])
        for x in (
          "CANDIDATE_VISIBLE_FAILURE_SEMANTICS_BOUND_AT_NORMALIZATION_OR_INSTRUMENTATION_TIME",
          "DIRECT_CONTRACT_AND_DERIVED_UPSTREAM_BOTH_PRESENT",
          "NONEMPTY_CAUSALLY_RELEVANT_SUPPORTING_RECEIPTS_REQUIRED_FOR_FAILED_CHECKS",
          "ALL_THREE_FROZEN_P1_DIRECT_SURFACE_IDENTITIES_INCLUDED",
          "V7_INTERVENTION_RESCUE_SCORER_USED_UNCHANGED",
          "NO_TERMINAL_V3_CASE_REPLAY",
          "ZERO_INCREMENTAL_SPEND",
        ):
            if x not in required: errors.append("SHARED_BATCH_ADMISSIBILITY_MISSING:"+x)
    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":sorted(set(errors)),
                "execution_authority":False,"capability_credit_delta":0,"family_credit_delta":0}
    solver_input={
      "requirements":d["requirements"],
      "already_resolved":d.get("already_resolved",[]),
      "observations":[{"id":x["id"],"covers":x["covers"],"cost":x["cost"]} for x in obs],
    }
    result=solve(solver_input)
    ok=(result.get("exact_minimum") is True
        and result.get("selected_observations")==["P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH"]
        and result.get("total_cost")==1.0
        and result.get("observation_count")==1)
    return {
      "schema":SCHEMA,
      "status":"PASS__EXACT_ONE_BATCH_MINIMUM_REALITY_CUT__CONDITIONAL_EXECUTION_AUTHORITY_PENDING_PROVENANCE_CLOSURE_AND_INDEPENDENT_VERIFICATION" if ok else "FAIL_CLOSED",
      "pass":ok,
      "errors":[] if ok else ["EXACT_SOLVER_RESULT_UNEXPECTED"],
      "solver_result":result,
      "selected_observation":"P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH" if ok else None,
      "minimum_new_reality_units":1 if ok else None,
      "terminal_v3_replay_required":False,
      "incremental_spend_usd":0,
      "execution_authority":False,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "rule":"THIS_VERIFIES_THE_CUT_ONLY__IT_DOES_NOT_AUTHORIZE_EXECUTION_UNTIL_THE_V7_PROVENANCE_MUTATION_CLOSURE_IS_INDEPENDENTLY_VERIFIED_AND_THE_SHARED_BATCH_ITSELF_IS_FROZEN"
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
