"""Information-theoretic falsifier for P1 V5 full-scope semantic transport.

Constructs one public normalized trajectory and two hidden intervention worlds with
identical candidate-visible bytes but different causal roots. Any deterministic
candidate that forces a unique cause from the public payload is wrong in at least
one admissible world. This consumes no terminal replay and no new external reality.
"""
from __future__ import annotations
import copy
import hashlib
import json
from typing import Any, Mapping

from canonical.runtime import trajectory_failure_typed_ir_candidate_v5 as candidate

SCHEMA="PROJECT_BRAIN_P1_V5_CAUSAL_IDENTIFIABILITY_FALSIFIER_V1"

def public_case()->dict[str,Any]:
    domain="CODE"
    p="code:"
    def check(kind:str, aid:str, passed:bool)->dict[str,Any]:
        return {
            "kind":kind,
            "id":f"{aid}:{kind}",
            "pass":passed,
            "evidence":[f"receipt:{aid}",f"check:{aid}:{kind}"],
        }
    return {
        "schema":"PROJECT_BRAIN_P1_IDENTIFIABILITY_TWIN_WORLD_V1",
        "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "task":{
            "domain":domain,
            "goal":"LOCALIZE_CAUSAL_ROOT_OR_ABSTAIN_WHEN_VISIBLE_EVIDENCE_CANNOT_DISCRIMINATE",
            "terminal_failed_resources":[p+"terminal"],
            "trajectory":[
                {
                    "step":0,"action_id":"A0","domain":domain,
                    "reads":[],"writes":[p+"seed"],"depends_on":[],
                    "dependency_composition":"SEQUENTIAL",
                    "checks":[check("INVARIANT","A0",True)],
                },
                {
                    "step":1,"action_id":"A1","domain":domain,
                    "reads":[p+"seed"],"writes":[p+"mid"],"depends_on":["A0"],
                    "dependency_composition":"SEQUENTIAL",
                    "checks":[check("INVARIANT","A1",True),check("AUTHORITY","A1",False)],
                },
                {
                    "step":2,"action_id":"A2","domain":domain,
                    "reads":[p+"mid"],"writes":[p+"damaged"],"depends_on":["A1"],
                    "dependency_composition":"SEQUENTIAL",
                    "checks":[check("INVARIANT","A2",True),check("STATE_TRANSITION","A2",False)],
                },
                {
                    "step":3,"action_id":"A3","domain":domain,
                    "reads":[p+"damaged"],"writes":[p+"terminal"],"depends_on":["A2"],
                    "dependency_composition":"SEQUENTIAL",
                    "checks":[check("INVARIANT","A3",True)],
                },
            ],
        },
    }

def hidden_worlds()->list[dict[str,Any]]:
    # Both worlds are observationally identical to the candidate. They differ
    # only in hidden intervention outcomes, which the frozen P1 binding declares
    # evaluator-only until earned.
    return [
        {
            "world_id":"EARLY_AUTHORITY_CAUSAL",
            "true_cause_action_id":"A1",
            "rescuing_repairs":["restore:A1:AUTHORITY"],
            "nonrescuing_repairs":["restore:A2:STATE_TRANSITION"],
        },
        {
            "world_id":"LATE_STATE_CAUSAL",
            "true_cause_action_id":"A2",
            "rescuing_repairs":["restore:A2:STATE_TRANSITION"],
            "nonrescuing_repairs":["restore:A1:AUTHORITY"],
        },
    ]

def _canonical_sha256(value:Mapping[str,Any])->str:
    raw=json.dumps(value,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(raw).hexdigest()

def _forced_unique(out:Mapping[str,Any])->bool:
    return (
        out.get("status") in {"IDENTIFIED","INTERACTION"}
        and isinstance(out.get("cause_action_ids"),list)
        and len(out.get("cause_action_ids") or [])>=1
    )

def _world_pass(world:Mapping[str,Any],out:Mapping[str,Any])->bool:
    # Because identical public bytes admit two incompatible hidden worlds,
    # abstention is the only universally sound answer before a discriminator is
    # earned. If the candidate nevertheless forces a unique answer, score the
    # hidden world directly by root identity and rescue.
    if out.get("status")=="AMBIGUOUS":
        return bool(out.get("information_request"))
    if out.get("status")!="IDENTIFIED":
        return False
    if out.get("cause_action_id")!=world["true_cause_action_id"]:
        return False
    got=sorted(str(x) for x in (out.get("repair_targets") or []))
    required=sorted(str(x) for x in world["rescuing_repairs"])
    return got==required

def evaluate()->dict[str,Any]:
    public=public_case()
    worlds=hidden_worlds()
    # Explicitly clone the exact same public object for each hidden world.
    public_hashes=[_canonical_sha256(copy.deepcopy(public)) for _ in worlds]
    out=candidate.solve(copy.deepcopy(public))
    world_results=[
        {
            "world_id":w["world_id"],
            "true_cause_action_id":w["true_cause_action_id"],
            "candidate_pass":_world_pass(w,out),
        }
        for w in worlds
    ]
    all_worlds_pass=all(x["candidate_pass"] for x in world_results)
    unique_overclaim=_forced_unique(out) and len({w["true_cause_action_id"] for w in worlds})>1
    return {
        "schema":SCHEMA,
        "status":(
            "FALSIFIED__V5_FORCES_UNIQUE_CAUSE_ACROSS_OBSERVATIONALLY_IDENTICAL_HIDDEN_INTERVENTION_WORLDS"
            if (unique_overclaim and not all_worlds_pass)
            else "NOT_FALSIFIED"
        ),
        "falsified":bool(unique_overclaim and not all_worlds_pass),
        "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "public_payload_sha256":public_hashes[0],
        "identical_public_payload_across_hidden_worlds":len(set(public_hashes))==1,
        "hidden_world_count":len(worlds),
        "hidden_cause_count":len({w["true_cause_action_id"] for w in worlds}),
        "candidate_output":out,
        "candidate_forces_unique_cause":unique_overclaim,
        "world_results":world_results,
        "violated_frozen_semantics":[
            "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE",
            "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE",
            "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
        ],
        "deduction":"VISIBLE_TRAJECTORY_PLUS_FAILED_CHECKS_DO_NOT_IN_GENERAL_IDENTIFY_CAUSAL_ROOT__A_VALID_P1_ROUTE_MUST_ABSTAIN_OR_ACQUIRE_A_CAUSAL_DISCRIMINATOR_WHEN_MULTIPLE_HIDDEN_INTERVENTION_WORLDS_SHARE_THE_SAME_PUBLIC_PAYLOAD",
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
