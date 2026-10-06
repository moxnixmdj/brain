from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PersistentArtifact:
    bits:int
    persists_across_tasks:bool
    value_depends_on_training_or_experience:bool
    available_preexposure:bool
    representation:str

def causal_learned_bits(a:PersistentArtifact)->int:
    if a.bits<0:
        raise ValueError("BITS_INVALID")
    if not a.persists_across_tasks:
        return 0
    if a.value_depends_on_training_or_experience and not a.available_preexposure:
        return a.bits
    return 0

def classify(a:PersistentArtifact)->str:
    b=causal_learned_bits(a)
    if b>0:
        return "PERSISTENT_CAUSALLY_LEARNED"
    if not a.persists_across_tasks:
        return "EPHEMERAL_RUNTIME_STATE"
    return "PERSISTENT_NONLEARNED"

def representation_relabel_invariant(bits:int)->dict:
    w=PersistentArtifact(bits,True,True,False,"weights")
    c=PersistentArtifact(bits,True,True,False,"source_constants")
    t=PersistentArtifact(bits,True,True,False,"lookup_table")
    return {
        "weights":causal_learned_bits(w),
        "source_constants":causal_learned_bits(c),
        "lookup_table":causal_learned_bits(t),
        "invariant":len({causal_learned_bits(w),causal_learned_bits(c),causal_learned_bits(t)})==1
    }

def runtime_fit_not_persisted(bits:int)->int:
    return causal_learned_bits(PersistentArtifact(bits,False,True,False,"runtime_fit"))

def generic_preexposure_code(bits:int)->int:
    return causal_learned_bits(PersistentArtifact(bits,True,False,True,"deterministic_code"))
