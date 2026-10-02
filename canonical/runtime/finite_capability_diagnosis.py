"""Exact finite-hypothesis capability diagnosis and probe selection.

When a tool/worker capability uncertainty can be represented as a finite frozen version
space with predeclared probe outcomes, choose the probe lexicographically by diagnostic
power first (worst-case then expected remaining hypotheses), then probe cost. Unknown/open-ended capability inference remains out
of scope and fails closed.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping,Sequence
import math

@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id:str
    capabilities:frozenset[str]

@dataclass(frozen=True)
class Probe:
    probe_id:str
    outcomes:Mapping[str,str]
    cost:float=1.0

def select_probe(hypotheses:Sequence[Hypothesis],probes:Sequence[Probe])->dict:
    hids=[h.hypothesis_id for h in hypotheses]
    if not hids or any(not isinstance(x,str) or not x for x in hids) or len(hids)!=len(set(hids)):
        return {"status":"FAIL_CLOSED","reason":"HYPOTHESIS_IDENTITIES_INVALID_OR_DUPLICATE"}
    pids=[p.probe_id for p in probes]
    if any(not isinstance(x,str) or not x for x in pids) or len(pids)!=len(set(pids)):
        return {"status":"FAIL_CLOSED","reason":"PROBE_IDENTITIES_INVALID_OR_DUPLICATE"}
    scored=[]
    current=set(hids)
    for p in probes:
        if not isinstance(p.cost,(int,float)) or isinstance(p.cost,bool) or not math.isfinite(float(p.cost)) or p.cost<=0:
            continue
        if set(p.outcomes)!=current or any(not isinstance(v,str) or not v for v in p.outcomes.values()):
            continue
        buckets={}
        for hid,outcome in p.outcomes.items():
            buckets.setdefault(outcome,set()).add(hid)
        if len(buckets)<2:
            continue
        worst=max(len(v) for v in buckets.values())
        expected_numerator=sum(len(v)*len(v) for v in buckets.values())
        expected=expected_numerator/len(hids)
        scored.append((worst,expected,float(p.cost),p.probe_id))
    if not scored:
        return {"status":"ESCALATE","reason":"NO_VALID_DISCRIMINATING_PROBE"}
    scored.sort(key=lambda x:(x[0],x[1],x[2],x[3]))
    worst,expected,cost,probe_id=scored[0]
    return {
        "status":"SELECT",
        "probe_id":probe_id,
        "worst_case_remaining":worst,
        "expected_remaining_uniform":expected,
        "probe_cost":cost,
        "reason":"MIN_WORST_CASE_REMAINING__THEN_EXPECTED_REMAINING__THEN_COST__THEN_ID",
        "terminal_authority":False,
    }

def update_version_space(hypotheses:Sequence[Hypothesis],probe:Probe,observed_outcome:str)->dict:
    ids={h.hypothesis_id for h in hypotheses}
    if set(probe.outcomes)!=ids:
        return {"status":"FAIL_CLOSED","reason":"PROBE_OUTCOME_MODEL_INCOMPLETE"}
    kept=sorted(h.hypothesis_id for h in hypotheses if probe.outcomes[h.hypothesis_id]==observed_outcome)
    if not kept:
        return {"status":"MODEL_FALSIFIED","remaining_hypotheses":[],"terminal_authority":False}
    return {
        "status":"RESOLVED" if len(kept)==1 else "REDUCED",
        "remaining_hypotheses":kept,
        "terminal_authority":False,
    }
