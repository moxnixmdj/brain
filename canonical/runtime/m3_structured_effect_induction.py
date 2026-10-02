"""Exact bounded effect-model induction from structured before/after probe receipts.

Given repeated observations of one action with flat scalar arguments and state maps,
infer only effect classes that are exactly supported across every observation:
- DELETE(key)
- SET_FROM_ARG(key,arg)
- SET_CONSTANT(key,value)
- COPY_BEFORE(key,source_key)
- ADD_CONSTANT(key,delta)

Ambiguous or unsupported changed fields remain unresolved rather than guessed.
This is a bounded structured-state induction primitive, not semantic or terminal
authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence, Any

MAX_OBSERVATIONS=64
MAX_FIELDS=128

Scalar=str|int|float|bool|None

@dataclass(frozen=True)
class Observation:
    args: Mapping[str,Scalar]
    before: Mapping[str,Scalar]
    after: Mapping[str,Scalar]

def _valid_scalar(v:Any)->bool:
    if v is None or isinstance(v,(str,bool,int)):
        return True
    return isinstance(v,float) and math.isfinite(v)

def _valid_map(m:Mapping[str,Scalar])->bool:
    return isinstance(m,Mapping) and all(
        isinstance(k,str) and bool(k.strip()) and _valid_scalar(v)
        for k,v in m.items()
    )

def _state(m:Mapping[str,Scalar],key:str):
    return (key in m,m.get(key))

def induce_effect_model(observations:Sequence[Observation])->dict:
    if not isinstance(observations,Sequence) or len(observations)<2 or len(observations)>MAX_OBSERVATIONS:
        return {"status":"FAIL_CLOSED","reason":"OBSERVATION_COUNT_INVALID","terminal_authority":False}
    for i,o in enumerate(observations):
        if not isinstance(o,Observation) or not _valid_map(o.args) or not _valid_map(o.before) or not _valid_map(o.after):
            return {"status":"FAIL_CLOSED","reason":f"OBSERVATION_INVALID:{i}","terminal_authority":False}

    fields=sorted(set().union(*(set(o.before)|set(o.after) for o in observations)))
    if len(fields)>MAX_FIELDS:
        return {"status":"FAIL_CLOSED","reason":"FIELD_UNIVERSE_TOO_LARGE","terminal_authority":False}

    changed=[]
    unchanged=[]
    for key in fields:
        if any(_state(o.before,key)!=_state(o.after,key) for o in observations):
            changed.append(key)
        else:
            unchanged.append(key)

    effects=[]
    unresolved=[]
    for key in changed:
        before_states=[_state(o.before,key) for o in observations]
        after_states=[_state(o.after,key) for o in observations]

        if all(not present for present,_ in after_states):
            effects.append({"kind":"DELETE","key":key})
            continue
        if not all(present for present,_ in after_states):
            unresolved.append(key); continue

        after_vals=[value for _,value in after_states]

        # SET_FROM_ARG requires variation so it is distinguishable from a constant.
        arg_candidates=[]
        common_args=set(observations[0].args)
        for o in observations[1:]:
            common_args &= set(o.args)
        for arg in sorted(common_args):
            vals=[o.args[arg] for o in observations]
            if len({repr(v) for v in vals})<2:
                continue
            if all(after_vals[i]==vals[i] for i in range(len(observations))):
                arg_candidates.append(arg)
        if len(arg_candidates)==1:
            effects.append({"kind":"SET_FROM_ARG","key":key,"arg":arg_candidates[0]})
            continue
        if len(arg_candidates)>1:
            unresolved.append(key); continue

        # COPY_BEFORE also requires source variation to avoid confusing it with a constant.
        source_candidates=[]
        common_before=set(observations[0].before)
        for o in observations[1:]:
            common_before &= set(o.before)
        for source in sorted(common_before):
            vals=[o.before[source] for o in observations]
            if len({repr(v) for v in vals})<2:
                continue
            if all(after_vals[i]==vals[i] for i in range(len(observations))):
                source_candidates.append(source)
        if len(source_candidates)==1:
            effects.append({"kind":"COPY_BEFORE","key":key,"source":source_candidates[0]})
            continue
        if len(source_candidates)>1:
            unresolved.append(key); continue

        # Numeric fixed delta requires target to exist before every time and vary.
        if all(p for p,_ in before_states):
            before_vals=[v for _,v in before_states]
            if all(isinstance(v,(int,float)) and not isinstance(v,bool) for v in before_vals+after_vals):
                if all(math.isfinite(float(v)) for v in before_vals+after_vals):
                    deltas=[float(a)-float(b) for a,b in zip(after_vals,before_vals)]
                    if len({float(v) for v in before_vals})>=2 and max(deltas)-min(deltas)==0 and deltas[0]!=0:
                        effects.append({"kind":"ADD_CONSTANT","key":key,"delta":deltas[0]})
                        continue

        # Constant assignment is safe only when every after value is identical.
        if all(v==after_vals[0] for v in after_vals[1:]):
            effects.append({"kind":"SET_CONSTANT","key":key,"value":after_vals[0]})
            continue

        unresolved.append(key)

    return {
        "status":"PASS",
        "effects":effects,
        "unresolved_changed_keys":sorted(unresolved),
        "unchanged_keys":unchanged,
        "complete_supported_model":not unresolved,
        "scope":"FLAT_SCALAR_STATE__UNCONDITIONAL_DETERMINISTIC_SUPPORTED_EFFECT_CLASSES_ONLY",
        "semantic_authority":False,
        "terminal_authority":False,
    }
