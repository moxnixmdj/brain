"""Generic finite identifiability and minimum-discriminator kernel.

This is the domain-neutral generalization of finite capability diagnosis.
It owns only finite, frozen hypothesis spaces with predeclared experiment outcomes.

Use cases:
- M3: tool/worker capability hypotheses and safe probes,
- M5: candidate causal/repair-effect hypotheses and interventions,
- any other lane after upstream semantics have produced a finite explicit model.

It never invents hypotheses, predictions, causal semantics, or source truth.
If the supplied experiments cannot distinguish surviving hypotheses, it returns an
explicit non-identifiability witness instead of guessing.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
import math

SCHEMA="BRAIN_FINITE_IDENTIFIABILITY_V1"

@dataclass(frozen=True)
class Hypothesis:
    hypothesis_id:str
    payload:Mapping[str,Any]|None=None

@dataclass(frozen=True)
class Experiment:
    experiment_id:str
    outcomes:Mapping[str,str]
    cost:float=1.0

def _validate_hypotheses(hypotheses:Sequence[Hypothesis])->tuple[list[str],list[str]]:
    errors=[]
    ids=[]
    if not isinstance(hypotheses,Sequence) or isinstance(hypotheses,(str,bytes)) or not hypotheses:
        return [],["HYPOTHESES_INVALID_OR_EMPTY"]
    for i,h in enumerate(hypotheses):
        if not isinstance(h,Hypothesis) or not isinstance(h.hypothesis_id,str) or not h.hypothesis_id:
            errors.append(f"HYPOTHESIS_INVALID:{i}")
            continue
        ids.append(h.hypothesis_id)
    if len(ids)!=len(set(ids)):
        errors.append("HYPOTHESIS_ID_DUPLICATE")
    return ids,errors

def _validate_experiments(experiments:Sequence[Experiment],ids:set[str])->list[str]:
    errors=[]
    seen=set()
    if not isinstance(experiments,Sequence) or isinstance(experiments,(str,bytes)):
        return ["EXPERIMENTS_INVALID"]
    for i,e in enumerate(experiments):
        if not isinstance(e,Experiment) or not isinstance(e.experiment_id,str) or not e.experiment_id:
            errors.append(f"EXPERIMENT_INVALID:{i}")
            continue
        if e.experiment_id in seen:
            errors.append(f"EXPERIMENT_ID_DUPLICATE:{e.experiment_id}")
        seen.add(e.experiment_id)
        if not isinstance(e.cost,(int,float)) or isinstance(e.cost,bool) or not math.isfinite(float(e.cost)) or e.cost<=0:
            errors.append(f"EXPERIMENT_COST_INVALID:{e.experiment_id}")
        if set(e.outcomes)!=ids:
            errors.append(f"EXPERIMENT_OUTCOME_MODEL_INCOMPLETE:{e.experiment_id}")
        if any(not isinstance(v,str) or not v for v in e.outcomes.values()):
            errors.append(f"EXPERIMENT_OUTCOME_INVALID:{e.experiment_id}")
    return errors

def filter_version_space(
    hypotheses:Sequence[Hypothesis],
    experiments:Sequence[Experiment],
    observations:Mapping[str,str],
)->dict[str,Any]:
    ids,errors=_validate_hypotheses(hypotheses)
    by_exp={e.experiment_id:e for e in experiments if isinstance(e,Experiment)}
    errors.extend(_validate_experiments(experiments,set(ids)))
    if not isinstance(observations,Mapping):
        errors.append("OBSERVATIONS_INVALID")
        observations={}
    unknown=sorted(set(observations)-set(by_exp))
    errors.extend(f"OBSERVATION_UNKNOWN_EXPERIMENT:{x}" for x in unknown)
    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),"remaining_hypotheses":[],"terminal_authority":False}

    kept=set(ids)
    for eid,observed in observations.items():
        if not isinstance(observed,str) or not observed:
            return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":[f"OBSERVED_OUTCOME_INVALID:{eid}"],"remaining_hypotheses":[],"terminal_authority":False}
        e=by_exp[eid]
        matches={hid for hid in kept if e.outcomes[hid]==observed}
        if not matches:
            return {
                "schema":SCHEMA,"status":"MODEL_FALSIFIED",
                "reason":f"UNMODELED_OUTCOME_OR_INCONSISTENT_EVIDENCE:{eid}:{observed}",
                "remaining_hypotheses":[],"terminal_authority":False,
            }
        kept=matches
    ordered=sorted(kept)
    return {
        "schema":SCHEMA,
        "status":"RESOLVED" if len(ordered)==1 else "REDUCED",
        "remaining_hypotheses":ordered,
        "terminal_authority":False,
    }

def equivalence_classes(
    hypothesis_ids:Sequence[str],
    experiments:Sequence[Experiment],
)->list[list[str]]:
    ids=sorted(set(hypothesis_ids))
    signatures={}
    for hid in ids:
        signature=tuple((e.experiment_id,e.outcomes[hid]) for e in sorted(experiments,key=lambda x:x.experiment_id))
        signatures.setdefault(signature,[]).append(hid)
    return sorted((sorted(v) for v in signatures.values()),key=lambda x:(len(x),x))

def select_discriminator(
    hypotheses:Sequence[Hypothesis],
    experiments:Sequence[Experiment],
    observations:Mapping[str,str]|None=None,
)->dict[str,Any]:
    ids,errors=_validate_hypotheses(hypotheses)
    errors.extend(_validate_experiments(experiments,set(ids)))
    if errors:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","errors":sorted(set(errors)),"terminal_authority":False}

    filtered=filter_version_space(hypotheses,experiments,observations or {})
    if filtered["status"] in {"FAIL_CLOSED","MODEL_FALSIFIED"}:
        return filtered
    remaining=filtered["remaining_hypotheses"]
    if len(remaining)==1:
        return {
            "schema":SCHEMA,"status":"RESOLVED","remaining_hypotheses":remaining,
            "terminal_authority":False,
        }

    used=set((observations or {}).keys())
    scored=[]
    for e in experiments:
        if e.experiment_id in used:
            continue
        buckets={}
        for hid in remaining:
            buckets.setdefault(e.outcomes[hid],set()).add(hid)
        if len(buckets)<2:
            continue
        worst=max(len(v) for v in buckets.values())
        expected=sum(len(v)*len(v) for v in buckets.values())/len(remaining)
        scored.append((worst,expected,float(e.cost),e.experiment_id))
    if not scored:
        classes=equivalence_classes(remaining,[e for e in experiments if e.experiment_id not in used])
        return {
            "schema":SCHEMA,
            "status":"NONIDENTIFIABLE_UNDER_AUTHORIZED_EXPERIMENTS",
            "remaining_hypotheses":remaining,
            "equivalence_classes":classes,
            "reason":"NO_UNUSED_AUTHORIZED_EXPERIMENT_PARTITIONS_SURVIVING_VERSION_SPACE",
            "terminal_authority":False,
        }
    scored.sort(key=lambda x:(x[0],x[1],x[2],x[3]))
    worst,expected,cost,eid=scored[0]
    return {
        "schema":SCHEMA,
        "status":"SELECT_EXPERIMENT",
        "experiment_id":eid,
        "remaining_hypotheses":remaining,
        "worst_case_remaining":worst,
        "expected_remaining_uniform":expected,
        "experiment_cost":cost,
        "objective":"MIN_WORST_CASE_REMAINING__THEN_EXPECTED_REMAINING__THEN_COST__THEN_ID",
        "terminal_authority":False,
    }
