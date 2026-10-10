"""Deterministic failure-hypothesis generation from normalized nonreplayable trajectories.

This module does NOT infer causality from text. It converts structured observable state
transitions into falsifiable candidate loci: first invariant violations, explicit errors,
and first unexpected state changes. Causal support remains a separate gate.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import FrozenSet,Sequence

@dataclass(frozen=True)
class Event:
    event_id:str
    step_index:int
    violated_invariants:FrozenSet[str]=frozenset()
    explicit_error:str|None=None
    unexpected_changes:FrozenSet[str]=frozenset()

def generate_failure_hypotheses(events:Sequence[Event])->dict:
    ids=[e.event_id for e in events]
    if any(not isinstance(x,str) or not x for x in ids) or len(ids)!=len(set(ids)):
        return {"status":"FAIL_CLOSED","reason":"EVENT_IDENTITIES_INVALID_OR_DUPLICATE"}
    if any(not isinstance(e.step_index,int) or isinstance(e.step_index,bool) or e.step_index<0 for e in events):
        return {"status":"FAIL_CLOSED","reason":"STEP_INDEX_INVALID"}
    ordered=sorted(events,key=lambda e:(e.step_index,e.event_id))
    seen_invariants=set()
    seen_changes=set()
    candidates=[]
    for e in ordered:
        new_inv=sorted(set(e.violated_invariants)-seen_invariants)
        new_changes=sorted(set(e.unexpected_changes)-seen_changes)
        if new_inv or e.explicit_error or new_changes:
            candidates.append({
                "candidate_id":f"failure@{e.event_id}",
                "event_id":e.event_id,
                "step_index":e.step_index,
                "first_new_invariant_violations":new_inv,
                "explicit_error":e.explicit_error,
                "first_unexpected_changes":new_changes,
                "causal_supported":False,
                "falsifiable":True,
            })
        seen_invariants.update(e.violated_invariants)
        seen_changes.update(e.unexpected_changes)
    if not candidates:
        return {"status":"NO_OBSERVABLE_FAILURE_LOCUS","candidates":[],"terminal_authority":False}
    return {
        "status":"CANDIDATES",
        "candidates":candidates,
        "earliest_candidate_id":candidates[0]["candidate_id"],
        "rule":"GENERATE_OBSERVABLE_FIRST-CHANGE_HYPOTHESES_ONLY__DO_NOT_CALL_CAUSAL_WITHOUT_SEPARATE_SUPPORT",
        "terminal_authority":False,
    }
