"""Counterexample to P1 V6 terminal-scope transport.

V6's proof semantics expose failure_semantics=DERIVED_UPSTREAM to the candidate,
but the candidate root-localizer ignores that field. A trace whose only visible
failed check is explicitly derived therefore gets overclaimed as a causal root.
V6's own forward intervention executor then rejects the nominated repair as
non-rescuing.
"""
from __future__ import annotations
import json
from typing import Any
from canonical.runtime import trajectory_failure_typed_ir_candidate_v6 as candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as proof

SCHEMA="PROJECT_BRAIN_P1_V6_DERIVED_ONLY_COUNTEREXAMPLE_V1"

def public_counterexample()->dict[str,Any]:
    return {
        "schema":"PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_PROOF_V6",
        "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "task":{
            "domain":"CODE",
            "trajectory":[
                {
                    "step":0,
                    "action_id":"A0",
                    "domain":"CODE",
                    "reads":[],
                    "writes":["code:upstream"],
                    "depends_on":[],
                    "dependency_composition":"SEQUENTIAL",
                    "checks":[{
                        "kind":"INVARIANT",
                        "id":"A0:INVARIANT",
                        "pass":True,
                        "evidence":["receipt:A0","check:A0:INVARIANT"],
                        "failure_semantics":"DIRECT_CONTRACT",
                    }],
                },
                {
                    "step":1,
                    "action_id":"A1",
                    "domain":"CODE",
                    "reads":["code:upstream"],
                    "writes":["code:symptom"],
                    "depends_on":["A0"],
                    "dependency_composition":"SEQUENTIAL",
                    "checks":[
                        {
                            "kind":"INVARIANT",
                            "id":"A1:INVARIANT:baseline",
                            "pass":True,
                            "evidence":["receipt:A1","check:A1:INVARIANT:baseline"],
                            "failure_semantics":"DIRECT_CONTRACT",
                        },
                        {
                            "kind":"SCOPE",
                            "id":"A1:SCOPE",
                            "pass":False,
                            "evidence":["receipt:A1","check:A1:SCOPE"],
                            "failure_semantics":"DERIVED_UPSTREAM",
                        },
                    ],
                },
                {
                    "step":2,
                    "action_id":"A2",
                    "domain":"CODE",
                    "reads":["code:symptom"],
                    "writes":["code:terminal"],
                    "depends_on":["A1"],
                    "dependency_composition":"SEQUENTIAL",
                    "checks":[{
                        "kind":"INVARIANT",
                        "id":"A2:INVARIANT",
                        "pass":True,
                        "evidence":["receipt:A2","check:A2:INVARIANT"],
                        "failure_semantics":"DIRECT_CONTRACT",
                    }],
                },
            ],
            "terminal_failed_resources":["code:terminal"],
            "goal":"LOCALIZE_CAUSAL_ROOT_AND_NOMINATE_CONTRACT_REPAIR_WITH_MACHINE_VERIFIED_TERMINAL_RESCUE",
        },
    }

def evaluate()->dict[str,Any]:
    public=public_counterexample()
    out=candidate.solve(public)
    intervention=proof.execute_intervention(public,out)
    derived_only=all(
        check.get("failure_semantics")=="DERIVED_UPSTREAM"
        for row in public["task"]["trajectory"]
        for check in row["checks"]
        if check.get("pass") is False
    )
    falsified=(
        derived_only
        and out.get("status")=="IDENTIFIED"
        and out.get("cause_action_id")=="A1"
        and out.get("repair_targets")==["restore:A1:SCOPE"]
        and intervention.get("terminal_rescued") is False
    )
    return {
        "schema":SCHEMA,
        "status":"PASS__V6_DERIVED_ONLY_SCOPE_COUNTEREXAMPLE_CONFIRMED" if falsified else "FAIL_CLOSED__COUNTEREXAMPLE_NOT_REPRODUCED",
        "derived_only_visible_failure":derived_only,
        "candidate_output":out,
        "forward_intervention":intervention,
        "finding":"V6_IDENTIFIES_AN_EXPLICITLY_DERIVED_UPSTREAM_FAILURE_AS_THE_UNIQUE_ROOT_AND_NOMINATES_A_REPAIR_THAT_ITS_OWN_FORWARD_EXECUTOR_DOES_NOT_ACCEPT_AS_RESCUING" if falsified else None,
        "v6_scope_transport_falsified":falsified,
        "v6_finite_verified_envelope_preserved":True,
        "terminal_results_replayed":0,
        "new_reality_units_consumed":0,
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
