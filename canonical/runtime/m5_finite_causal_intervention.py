"""Bounded finite causal intervention control for M5.

This module reuses Brain's independently verified finite hypothesis/probe solver.
It does not infer arbitrary causal models. Given:
- a frozen finite set of falsifiable cause/effect hypotheses,
- authorized interventions with predeclared observable outcomes per hypothesis,
it selects the most discriminating intervention and updates the surviving model.

An unmodeled outcome falsifies the frozen causal model instead of being forced into
one of its hypotheses. Relative identification inside the frozen model is not a
claim of universal causality.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Sequence

from canonical.runtime.finite_capability_diagnosis import (
    Hypothesis, Probe, select_probe, update_version_space
)

SCHEMA="BRAIN_M5_FINITE_CAUSAL_INTERVENTION_V1"

@dataclass(frozen=True)
class CauseHypothesis:
    hypothesis_id:str
    candidate_event_id:str
    repair_action_id:str|None=None

@dataclass(frozen=True)
class Intervention:
    intervention_id:str
    outcomes:Mapping[str,str]
    cost:float=1.0
    authorized:bool=True
    reversible:bool=True

def _hypotheses(rows:Sequence[CauseHypothesis])->tuple[list[Hypothesis],dict[str,CauseHypothesis],str|None]:
    ids=[x.hypothesis_id for x in rows]
    if not ids or any(not isinstance(x,str) or not x.strip() for x in ids) or len(ids)!=len(set(ids)):
        return [],{},"HYPOTHESIS_IDENTITIES_INVALID_OR_DUPLICATE"
    if any(not isinstance(x.candidate_event_id,str) or not x.candidate_event_id.strip() for x in rows):
        return [],{},"CANDIDATE_EVENT_ID_INVALID"
    return [Hypothesis(x.hypothesis_id,frozenset()) for x in rows],{x.hypothesis_id:x for x in rows},None

def select_intervention(
    hypotheses:Sequence[CauseHypothesis],
    interventions:Sequence[Intervention],
)->dict:
    hs,by_id,error=_hypotheses(hypotheses)
    if error:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":error,"terminal_authority":False}
    ids=[x.intervention_id for x in interventions]
    if any(not isinstance(x,str) or not x.strip() for x in ids) or len(ids)!=len(set(ids)):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"INTERVENTION_IDENTITIES_INVALID_OR_DUPLICATE","terminal_authority":False}
    admissible=[
        x for x in interventions
        if x.authorized and x.reversible
    ]
    probes=[Probe(x.intervention_id,x.outcomes,x.cost) for x in admissible]
    result=select_probe(hs,probes)
    if result.get("status")!="SELECT":
        return {
            "schema":SCHEMA,
            "status":"ESCALATE",
            "reason":result.get("reason","NO_VALID_CAUSAL_INTERVENTION"),
            "terminal_authority":False,
            "causal_authority":False,
        }
    return {
        "schema":SCHEMA,
        "status":"SELECT",
        "intervention_id":result["probe_id"],
        "worst_case_remaining":result["worst_case_remaining"],
        "expected_remaining_uniform":result["expected_remaining_uniform"],
        "reason":"FINITE_FROZEN_CAUSAL_VERSION_SPACE_DISCRIMINATION__"+result["reason"],
        "terminal_authority":False,
        "causal_authority":False,
    }

def update_after_intervention(
    hypotheses:Sequence[CauseHypothesis],
    intervention:Intervention,
    observed_outcome:str,
)->dict:
    hs,by_id,error=_hypotheses(hypotheses)
    if error:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":error,"terminal_authority":False}
    if not intervention.authorized or not intervention.reversible:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"INTERVENTION_NOT_AUTHORIZED_REVERSIBLE","terminal_authority":False}
    if not isinstance(observed_outcome,str) or not observed_outcome:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","reason":"OBSERVED_OUTCOME_INVALID","terminal_authority":False}
    out=update_version_space(hs,Probe(intervention.intervention_id,intervention.outcomes,intervention.cost),observed_outcome)
    status=out.get("status")
    if status=="MODEL_FALSIFIED":
        return {
            "schema":SCHEMA,
            "status":"MODEL_FALSIFIED",
            "reason":"OBSERVED_OUTCOME_OUTSIDE_FROZEN_CAUSAL_MODEL",
            "remaining_hypotheses":[],
            "terminal_authority":False,
            "causal_authority":False,
        }
    if status=="FAIL_CLOSED":
        return {"schema":SCHEMA,**out,"terminal_authority":False,"causal_authority":False}
    remaining=out["remaining_hypotheses"]
    payload={
        "schema":SCHEMA,
        "status":"RELATIVE_CAUSE_IDENTIFIED" if len(remaining)==1 else "CAUSAL_VERSION_SPACE_REDUCED",
        "remaining_hypotheses":remaining,
        "terminal_authority":False,
        "causal_authority":"RELATIVE_TO_FROZEN_FINITE_MODEL_ONLY",
    }
    if len(remaining)==1:
        h=by_id[remaining[0]]
        payload["candidate_event_id"]=h.candidate_event_id
        payload["repair_action_id"]=h.repair_action_id
    return payload
