from __future__ import annotations
from itertools import product

CAPS=("CHAIN_A","CHAIN_B","CHAIN_C")

def compile_registry_extension(pass_vector):
    if len(pass_vector)!=len(CAPS):
        raise ValueError("VECTOR_LENGTH_INVALID")
    return tuple(cid for cid,ok in zip(CAPS,pass_vector) if bool(ok))

def possible_persistent_states():
    return {compile_registry_extension(v) for v in product((False,True),repeat=len(CAPS))}

def causal_capacity_bits():
    return (len(possible_persistent_states())-1).bit_length()

def behaviorally_distinct(a,b):
    return compile_registry_extension(a)!=compile_registry_extension(b)

def audit_observed_all_pass():
    observed=(True,True,True)
    counterfactual=(False,False,False)
    distinct=behaviorally_distinct(observed,counterfactual)
    return {
      "possible_persistent_extension_states":len(possible_persistent_states()),
      "outcome_dependent_persistent_capacity_bits":causal_capacity_bits(),
      "counterfactual_behaviorally_distinct":distinct,
      "zero_causal_learned_bits_claim_survives":not distinct
    }
