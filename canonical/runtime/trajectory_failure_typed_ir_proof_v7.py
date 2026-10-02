"""Failure-semantics-aware P1 proof extensions for candidate V7."""
from __future__ import annotations
import copy
from typing import Any, Mapping
from canonical.runtime import trajectory_failure_typed_ir_proof_v6 as v6

SCHEMA="PROJECT_BRAIN_TRAJECTORY_CAUSAL_IR_PROOF_V7"
DOMAINS=v6.DOMAINS
KINDS=v6.KINDS
PATTERNS=v6.PATTERNS
suite_cases=v6.suite_cases
public_task=v6.public_task
execute_intervention=v6.execute_intervention
score_case=v6.score_case


def _check(kind:str,aid:str,passed:bool,semantics:str="DIRECT_CONTRACT")->dict[str,Any]:
    return {
        "kind":kind,
        "id":f"{aid}:{kind}",
        "pass":passed,
        "evidence":[f"receipt:{aid}",f"check:{aid}:{kind}"],
        "failure_semantics":semantics,
    }


def derived_only_case(domain:str,kind:str)->dict[str,Any]:
    if domain not in DOMAINS or kind not in KINDS:
        raise ValueError("DOMAIN_OR_KIND")
    p=f"{domain.lower()}:"
    return {
        "schema":SCHEMA,
        "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "task":{
            "domain":domain,
            "trajectory":[
                {"step":0,"action_id":"A0","domain":domain,"reads":[],"writes":[p+"upstream"],
                 "depends_on":[],"dependency_composition":"SEQUENTIAL",
                 "checks":[_check("INVARIANT","A0",True)]},
                {"step":1,"action_id":"A1","domain":domain,"reads":[p+"upstream"],"writes":[p+"symptom"],
                 "depends_on":["A0"],"dependency_composition":"SEQUENTIAL",
                 "checks":[_check("INVARIANT","A1",True),_check(kind,"A1",False,"DERIVED_UPSTREAM")]},
                {"step":2,"action_id":"A2","domain":domain,"reads":[p+"symptom"],"writes":[p+"terminal"],
                 "depends_on":["A1"],"dependency_composition":"SEQUENTIAL",
                 "checks":[_check("INVARIANT","A2",True)]},
            ],
            "terminal_failed_resources":[p+"terminal"],
            "goal":"ABSTAIN_WHEN_ONLY_DERIVED_FAILURES_ARE_VISIBLE",
        },
    }


def direct_plus_derived_case(domain:str,kind:str)->dict[str,Any]:
    if domain not in DOMAINS or kind not in KINDS:
        raise ValueError("DOMAIN_OR_KIND")
    p=f"{domain.lower()}:"
    return {
        "schema":SCHEMA,
        "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "task":{
            "domain":domain,
            "trajectory":[
                {"step":0,"action_id":"A0","domain":domain,"reads":[],"writes":[p+"seed"],
                 "depends_on":[],"dependency_composition":"SEQUENTIAL",
                 "checks":[_check("INVARIANT","A0",True)]},
                {"step":1,"action_id":"A1","domain":domain,"reads":[p+"seed"],"writes":[p+"root"],
                 "depends_on":["A0"],"dependency_composition":"SEQUENTIAL",
                 "checks":[_check("INVARIANT","A1",True),_check(kind,"A1",False,"DIRECT_CONTRACT")]},
                {"step":2,"action_id":"A2","domain":domain,"reads":[p+"root"],"writes":[p+"symptom"],
                 "depends_on":["A1"],"dependency_composition":"SEQUENTIAL",
                 "checks":[_check("INVARIANT","A2",False,"DERIVED_UPSTREAM")]},
                {"step":3,"action_id":"A3","domain":domain,"reads":[p+"symptom"],"writes":[p+"terminal"],
                 "depends_on":["A2"],"dependency_composition":"SEQUENTIAL",
                 "checks":[_check("INVARIANT","A3",True)]},
            ],
            "terminal_failed_resources":[p+"terminal"],
            "goal":"LOCALIZE_DIRECT_ROOT_WHILE_REJECTING_DERIVED_SYMPTOM",
        },
    }


def score_derived_only(candidate:Mapping[str,Any])->dict[str,Any]:
    ok=(
        candidate.get("status")=="AMBIGUOUS"
        and candidate.get("cause_action_id") is None
        and candidate.get("cause_action_ids")==[]
        and candidate.get("critical_action_id") is None
        and candidate.get("candidates")==[]
        and not candidate.get("repair_targets")
        and bool(candidate.get("information_request"))
    )
    return {"pass":ok,"reason":"PASS" if ok else "DERIVED_ONLY_MUST_ABSTAIN_WITHOUT_REPAIR"}


def score_direct_plus_derived(public:Mapping[str,Any],candidate:Mapping[str,Any],kind:str)->dict[str,Any]:
    expected_repair=f"restore:A1:{kind}"
    iv=execute_intervention(public,candidate)
    ok=(
        candidate.get("status")=="IDENTIFIED"
        and candidate.get("cause_action_id")=="A1"
        and candidate.get("cause_action_ids")==["A1"]
        and candidate.get("critical_action_id")=="A1"
        and candidate.get("mechanism_classes")==[kind]
        and candidate.get("repair_targets")==[expected_repair]
        and iv.get("terminal_rescued") is True
    )
    return {"pass":ok,"reason":"PASS" if ok else "DIRECT_ROOT_OR_RESCUE_WRONG","intervention":iv}


def adversarial_cases()->list[dict[str,Any]]:
    out=[]
    for domain in DOMAINS:
        for kind in KINDS:
            out.append({"class":"DERIVED_ONLY","domain":domain,"kind":kind,"public":derived_only_case(domain,kind)})
            out.append({"class":"DIRECT_PLUS_DERIVED","domain":domain,"kind":kind,"public":direct_plus_derived_case(domain,kind)})
    return out
