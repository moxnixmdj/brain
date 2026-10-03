"""Zero-reality audit: does current P1 V7 kill DROP_PROVENANCE_OR_DEPENDENCY_EDGE?

This does not restore P1 or grant credit. It only checks whether the specific
independently reproduced V4 counterexample still survives under the current V7
candidate/proof pair.
"""
from __future__ import annotations
import copy, json
from typing import Any
from canonical.runtime import trajectory_failure_typed_ir_candidate_v7 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as proof

SCHEMA="PROJECT_BRAIN_P1_V7_PROVENANCE_MUTATION_CLOSURE_V1"

def evaluate()->dict[str,Any]:
    case=proof.generate_case(71001,pattern="SINGLE",domain="RESEARCH",kind="PROVENANCE")
    public=proof.public_task(case)
    erased=0
    for row in public["task"]["trajectory"]:
        for check in row["checks"]:
            if check.get("pass") is False:
                check["evidence"]=[]
                erased+=1
    out=candidate.solve(copy.deepcopy(public))
    verdict=proof.score_case(case,out)
    killed=erased>0 and out.get("status")=="FAIL_CLOSED" and verdict.get("pass") is False
    return {
      "schema":SCHEMA,
      "status":"PASS__CURRENT_V7_KILLS_DROP_PROVENANCE_MUTATION__ZERO_CREDIT" if killed else "FAIL_CLOSED",
      "pass":killed,
      "failed_check_evidence_lists_erased":erased,
      "candidate_status":out.get("status"),
      "candidate_reason":out.get("reason"),
      "scorer_pass_after_mutation":verdict.get("pass") is True,
      "mutation":"DROP_PROVENANCE_OR_DEPENDENCY_EDGE",
      "consequence":"OLD_V4_PROVENANCE_COUNTEREXAMPLE_DOES_NOT_SURVIVE_CURRENT_V7_MECHANISM" if killed else "PROVENANCE_COUNTEREXAMPLE_REMAINS",
      "p1_quarantine_resolved":False,
      "remaining_blocker":"FAILURE_SEMANTICS_TRANSPORT_TO_FROZEN_DIRECT_SURFACES" if killed else "PROVENANCE_AND_FAILURE_SEMANTICS",
      "terminal_results_replayed":0,
      "new_reality_units_consumed":0,
      "incremental_spend_usd":0,
      "capability_credit_delta":0,
      "family_credit_delta":0,
      "execution_authority":False,
      "promotion_authority":False,
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
