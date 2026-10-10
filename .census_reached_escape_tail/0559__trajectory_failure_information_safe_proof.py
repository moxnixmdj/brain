"""Information-safe terminal proof population for trajectory causal localization.

Development/preflight machinery only. Terminal seeds must be supplied only after
candidate freeze and execution authority. Candidate-visible data contains the
normalized trajectory, explicit step contracts, and falsifiable repair actions,
but never the hidden causal identity or rescue verdict.

The population deliberately includes:
- multiple local contract violations where early violations cancel,
- a later terminally material violation,
- ambiguity cases where multiple repairs are observationally equivalent.
"""
from __future__ import annotations

import random
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TRAJECTORY_FAILURE_INFORMATION_SAFE_PROOF_V1"


class ProofError(ValueError):
    pass


def generate_case(seed:int, *, ambiguous:bool|None=None)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool):
        raise ProofError("SEED_MUST_BE_INTEGER")
    r=random.Random(seed)
    n=r.randint(6,9)
    initial=r.randint(-5,5)
    contract=[r.randint(-4,5) or 1 for _ in range(n)]
    observed=list(contract)

    idx=sorted(r.sample(range(1,n-1),3))
    a,b,c=idx
    # First two visible deviations cancel. This kills the "first violated
    # invariant is the root cause" shortcut.
    observed[a]+=2
    observed[b]-=2

    if ambiguous is None:
        ambiguous=(seed%5==0)

    if ambiguous:
        # Net error +2. Correcting either a or c independently rescues the
        # terminal state, so unique-cause selection is unjustified.
        observed[c]+=2
    else:
        # Net error +3. Only correction of c rescues terminal state.
        observed[c]+=3

    target=initial+sum(contract)
    observed_terminal=initial+sum(observed)
    steps=[]
    value=initial
    for i,(exp,got) in enumerate(zip(contract,observed)):
        before=value
        value+=got
        steps.append({
            "step":i,
            "action_id":f"A{i}",
            "state_before":before,
            "contract_delta":exp,
            "observed_delta":got,
            "state_after":value,
            "contract_pass":got==exp,
        })

    repairs=[]
    for i in idx:
        repairs.append({
            "repair_id":f"R{i}",
            "action_id":f"A{i}",
            "replacement_delta":contract[i],
        })
    r.shuffle(repairs)

    rescuers=[]
    for repair in repairs:
        repaired=list(observed)
        j=int(repair["action_id"][1:])
        repaired[j]=int(repair["replacement_delta"])
        if initial+sum(repaired)==target:
            rescuers.append(repair)

    if not rescuers:
        raise AssertionError("generator produced no rescue")

    oracle={
        "rescue_repair_ids":sorted(x["repair_id"] for x in rescuers),
        "rescue_action_ids":sorted(x["action_id"] for x in rescuers),
        "identified":len(rescuers)==1,
    }
    return {
        "schema":SCHEMA,
        "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "seed":seed,
        "task":{
            "initial_state":initial,
            "terminal_target":target,
            "observed_terminal_state":observed_terminal,
            "trajectory":steps,
            "repair_candidates":repairs,
            "rule":"CAUSE_CLAIM_REQUIRES_COUNTERFACTUAL_TERMINAL_RESCUE__MULTIPLE_RESCUERS_REQUIRE_AMBIGUITY",
        },
        "_oracle":oracle,
    }


def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return {k:v for k,v in case.items() if k!="_oracle"}


def _simulate(task:Mapping[str,Any], repair:Mapping[str,Any])->int:
    deltas=[int(x["observed_delta"]) for x in task["trajectory"]]
    action_id=repair.get("action_id")
    positions={x["action_id"]:i for i,x in enumerate(task["trajectory"])}
    if action_id not in positions:
        raise ProofError("REPAIR_ACTION_UNKNOWN")
    deltas[positions[action_id]]=int(repair["replacement_delta"])
    return int(task["initial_state"])+sum(deltas)


def score_case(case:Mapping[str,Any], candidate:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(candidate,Mapping):
        return {"pass":False,"reason":"CANDIDATE_NOT_OBJECT"}
    oracle=case["_oracle"]
    status=candidate.get("status")
    if oracle["identified"]:
        expected_r=oracle["rescue_repair_ids"][0]
        expected_a=oracle["rescue_action_ids"][0]
        ok=(
            status=="IDENTIFIED"
            and candidate.get("repair_id")==expected_r
            and candidate.get("cause_action_id")==expected_a
            and expected_a in (candidate.get("evidence_action_ids") or [])
        )
        return {
            "pass":bool(ok),
            "reason":"PASS" if ok else "IDENTIFIED_CAUSE_OR_REPAIR_WRONG",
            "rescue_verified":bool(ok),
        }
    got=sorted(candidate.get("repair_ids") or [])
    expected=oracle["rescue_repair_ids"]
    forced=candidate.get("cause_action_id") is not None
    ok=status=="AMBIGUOUS" and got==expected and not forced
    return {
        "pass":bool(ok),
        "reason":"PASS" if ok else "NONIDENTIFIABILITY_NOT_PRESERVED",
        "equivalence_class_size":len(expected),
    }


def verify_candidate_rescue(case:Mapping[str,Any], candidate:Mapping[str,Any])->bool:
    task=case["task"]
    repairs={x["repair_id"]:x for x in task["repair_candidates"]}
    ids=[candidate.get("repair_id")] if candidate.get("status")=="IDENTIFIED" else list(candidate.get("repair_ids") or [])
    if not ids or any(x not in repairs for x in ids):
        return False
    return all(_simulate(task,repairs[x])==task["terminal_target"] for x in ids)
