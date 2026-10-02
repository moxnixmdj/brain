"""Information-safe trajectory causal-localization proof V2.

V2 removes the predeclared repair-candidate list. The candidate receives only the
normalized execution trajectory, explicit per-step contract transitions, and the
terminal goal. It must generate falsifiable repair targets itself, test them
counterfactually, and preserve non-identifiability when multiple generated repairs
rescue the terminal result.

Development/preflight only. No terminal seed is consumed here.
"""
from __future__ import annotations

import random
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_TRAJECTORY_FAILURE_INFORMATION_SAFE_PROOF_V2"


def generate_case(seed:int, *, ambiguous:bool|None=None)->dict[str,Any]:
    if not isinstance(seed,int) or isinstance(seed,bool):
        raise ValueError("SEED_MUST_BE_INTEGER")
    r=random.Random(seed)
    n=r.randint(7,10)
    initial=r.randint(-7,7)
    contract=[r.choice([-5,-4,-3,-2,-1,1,2,3,4,5]) for _ in range(n)]
    observed=list(contract)

    # Three visible contract deviations. The first two cancel, defeating
    # "first invariant violation == root cause".
    a,b,c=sorted(r.sample(range(1,n-1),3))
    observed[a]+=2
    observed[b]-=2
    if ambiguous is None:
        ambiguous=(seed%5==0)

    if ambiguous:
        # Create two distinct single-step repairs that each restore the terminal
        # goal. One is c; another earlier/later deviation is made equivalent.
        observed[c]+=2
        # Net error is +2, so repairing either +2 deviation rescues while the
        # cancelling -2 deviation remains paired with the other +2.
        # a is already +2.
    else:
        # Net error +3, making only c's contract restoration rescuing.
        observed[c]+=3

    target=initial+sum(contract)
    value=initial
    trajectory=[]
    for i,(expected,got) in enumerate(zip(contract,observed)):
        before=value
        value+=got
        trajectory.append({
            "step":i,
            "action_id":f"A{i}",
            "state_before":before,
            "contract_delta":expected,
            "observed_delta":got,
            "state_after":value,
            "contract_pass":got==expected,
        })

    rescuers=[]
    for row in trajectory:
        if row["contract_pass"]:
            continue
        repaired=list(observed)
        repaired[row["step"]]=row["contract_delta"]
        if initial+sum(repaired)==target:
            rescuers.append({
                "action_id":row["action_id"],
                "replacement_delta":row["contract_delta"],
            })
    if not rescuers:
        raise AssertionError("NO_RESCUER")

    return {
        "schema":SCHEMA,
        "behavior_id":"TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001",
        "seed":seed,
        "task":{
            "initial_state":initial,
            "terminal_target":target,
            "observed_terminal_state":initial+sum(observed),
            "trajectory":trajectory,
            "repair_language":{
                "operation":"REPLACE_OBSERVED_STEP_DELTA_WITH_DECLARED_CONTRACT_DELTA",
                "scope":"ONE_STEP_PER_CAUSAL_HYPOTHESIS",
            },
            "rule":"GENERATE_FALSIFIABLE_REPAIR_FROM_VISIBLE_CONTRACT__CAUSE_CLAIM_REQUIRES_COUNTERFACTUAL_TERMINAL_RESCUE__MULTIPLE_RESCUERS_REQUIRE_AMBIGUITY",
        },
        "_oracle":{
            "identified":len(rescuers)==1,
            "rescuers":sorted(rescuers,key=lambda x:(x["action_id"],x["replacement_delta"])),
        },
    }


def public_task(case:Mapping[str,Any])->dict[str,Any]:
    return {k:v for k,v in case.items() if k!="_oracle"}


def _canon(rows):
    return sorted(
        [
            {"action_id":str(x.get("action_id")),"replacement_delta":int(x.get("replacement_delta"))}
            for x in rows or []
            if isinstance(x,Mapping)
            and isinstance(x.get("action_id"),str)
            and isinstance(x.get("replacement_delta"),int)
            and not isinstance(x.get("replacement_delta"),bool)
        ],
        key=lambda x:(x["action_id"],x["replacement_delta"]),
    )


def score_case(case:Mapping[str,Any],candidate:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(candidate,Mapping):
        return {"pass":False,"reason":"CANDIDATE_NOT_OBJECT"}
    oracle=case["_oracle"]
    expected=oracle["rescuers"]
    status=candidate.get("status")

    if oracle["identified"]:
        got=_canon([candidate.get("repair")])
        evidence=candidate.get("evidence_action_ids") or []
        ok=(
            status=="IDENTIFIED"
            and got==expected
            and expected[0]["action_id"] in evidence
            and candidate.get("cause_action_id")==expected[0]["action_id"]
        )
        return {"pass":bool(ok),"reason":"PASS" if ok else "UNIQUE_GENERATED_REPAIR_OR_CAUSE_WRONG"}

    got=_canon(candidate.get("repairs"))
    forced=candidate.get("cause_action_id") is not None
    ok=status=="AMBIGUOUS" and got==expected and not forced
    return {
        "pass":bool(ok),
        "reason":"PASS" if ok else "NONIDENTIFIABILITY_OR_GENERATED_REPAIR_SET_WRONG",
        "equivalence_class_size":len(expected),
    }


def anti_shortcut_mutations(case:Mapping[str,Any])->list[dict[str,Any]]:
    """Return mutation descriptors; no oracle answers enter public payload."""
    return [
        {"id":"MOVE_FIRST_VIOLATION","property":"EARLIEST_VIOLATION_CHANGES_BUT_TRUE_RESCUER_SET_DOES_NOT_FOLLOW_POSITION"},
        {"id":"PERMUTE_ACTION_IDS","property":"LEXICAL_ACTION_ORDER_CANNOT_DEFINE_CAUSE"},
        {"id":"AMBIGUITY_PAIR","property":"TWO_DISTINCT_GENERATED_SINGLE_STEP_REPAIRS_CAN_RESCUE__UNIQUE_CAUSE_MUST_NOT_BE_FORCED"},
    ]
