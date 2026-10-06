"""Provenance-invariant learned-information accounting for H100 research.

Core rule:
A persistent capability state does not become "nonlearned" merely because it is
losslessly re-encoded into deterministic source text, literals, generated code,
or another container.

We separate:
- Shannon information carried by a data-dependent state under an explicit
  finite ensemble;
- fixed-length selection capacity relative to a frozen K-way grammar;
- causal provenance classification of the persisted state.

This module does NOT claim an exact mutual-information value for a single
real-world training run without an explicit distribution over training data.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Any, Hashable, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_H100_PROVENANCE_INVARIANT_LEARNED_INFORMATION_V1"


class ProvenanceAccountingError(ValueError):
    pass


def shannon_entropy_uniform_ensemble(selected_states:Sequence[Hashable])->float:
    """Entropy H(Z) when each ensemble member is equally likely.

    selected_states[d] is the persistent state selected by dataset/world d.
    Because selection is deterministic in this finite model, I(D;Z)=H(Z).
    """
    vals=list(selected_states)
    if not vals:
        raise ProvenanceAccountingError("ENSEMBLE_EMPTY")
    counts=Counter(vals)
    n=len(vals)
    return -sum((c/n)*math.log2(c/n) for c in counts.values())


def validate_bijection(states:Sequence[Hashable], mapping:Mapping[Hashable,Hashable])->None:
    support=set(states)
    if set(mapping.keys()) != support:
        raise ProvenanceAccountingError("MAPPING_DOMAIN_MISMATCH")
    images=[mapping[x] for x in support]
    if len(images)!=len(set(images)):
        raise ProvenanceAccountingError("MAPPING_NOT_INJECTIVE")


def bijective_recode_entropy(
    selected_states:Sequence[Hashable],
    mapping:Mapping[Hashable,Hashable],
)->dict[str,Any]:
    validate_bijection(selected_states,mapping)
    before=shannon_entropy_uniform_ensemble(selected_states)
    after_states=[mapping[x] for x in selected_states]
    after=shannon_entropy_uniform_ensemble(after_states)
    return {
        "entropy_before_bits":before,
        "entropy_after_bits":after,
        "preserved":math.isclose(before,after,rel_tol=0.0,abs_tol=1e-12),
    }


def selection_capacity_bits(candidate_count:int)->dict[str,Any]:
    if not isinstance(candidate_count,int) or isinstance(candidate_count,bool) or candidate_count<1:
        raise ProvenanceAccountingError("CANDIDATE_COUNT_INVALID")
    return {
        "candidate_count":candidate_count,
        "max_selection_entropy_bits":math.log2(candidate_count),
        "fixed_length_selection_index_bits":0 if candidate_count==1 else (candidate_count-1).bit_length(),
        "interpretation":"CAPACITY_OR_INDEX_LENGTH_NOT_A_MUTUAL_INFORMATION_LOWER_BOUND_FOR_ONE_OBSERVED_RUN",
    }


def learned_origin_classification(
    *,
    data_dependent_value:bool,
    persisted_for_future_use:bool,
    container:str,
    losslessly_recovers_prior_learned_state:bool=False,
)->dict[str,Any]:
    c=str(container).strip()
    if not c:
        raise ProvenanceAccountingError("CONTAINER_EMPTY")
    learned_origin=bool(
        persisted_for_future_use
        and (data_dependent_value or losslessly_recovers_prior_learned_state)
    )
    reason=(
        "PERSISTED_DATA_DEPENDENT_CAPABILITY_STATE"
        if persisted_for_future_use and data_dependent_value
        else (
            "LOSSLESS_REENCODING_OF_PRIOR_LEARNED_STATE"
            if persisted_for_future_use and losslessly_recovers_prior_learned_state
            else "NO_PERSISTENT_DATA_DEPENDENT_CAPABILITY_STATE_ESTABLISHED"
        )
    )
    return {
        "schema":SCHEMA,
        "container":c,
        "data_dependent_value":bool(data_dependent_value),
        "persisted_for_future_use":bool(persisted_for_future_use),
        "losslessly_recovers_prior_learned_state":bool(losslessly_recovers_prior_learned_state),
        "learned_origin_state":learned_origin,
        "reason":reason,
    }


def audit_compiled_selection(
    *,
    capability_id:str,
    candidate_count:int,
    selected_after_observing_development_data:bool,
    persisted_in_registry:bool,
    container:str="DETERMINISTIC_REGISTRY_CODE",
)->dict[str,Any]:
    cap=selection_capacity_bits(candidate_count)
    cls=learned_origin_classification(
        data_dependent_value=selected_after_observing_development_data,
        persisted_for_future_use=persisted_in_registry,
        container=container,
    )
    return {
        "schema":SCHEMA,
        "capability_id":str(capability_id),
        "selection_capacity":cap,
        "provenance":cls,
        "hard_nonclaim":"FIXED_LENGTH_SELECTION_INDEX_BITS_IS_NOT_CLAIMED_AS_EXACT_SHANNON_MUTUAL_INFORMATION_OF_THE_REAL_DISCOVERY_PROCESS",
    }


def certificate()->dict[str,Any]:
    demo=bijective_recode_entropy(
        ["A","B","C","A","B","C"],
        {"A":"source_literal_17","B":"generated_fn_2","C":"blob_9"},
    )
    weight_recode=learned_origin_classification(
        data_dependent_value=False,
        persisted_for_future_use=True,
        container="SOURCE_LITERAL_BYTES",
        losslessly_recovers_prior_learned_state=True,
    )
    fixed_code=learned_origin_classification(
        data_dependent_value=False,
        persisted_for_future_use=True,
        container="PREEXPOSURE_DETERMINISTIC_ALGORITHM",
        losslessly_recovers_prior_learned_state=False,
    )
    return {
        "schema":SCHEMA,
        "status":"PROVENANCE_INVARIANT_LEARNED_INFORMATION_CERTIFICATE",
        "bijective_recode_demo":demo,
        "losslessly_embedded_weights":weight_recode,
        "preexposure_fixed_code":fixed_code,
        "deduction":[
            "LOSSLESS_CONTAINER_CHANGE_PRESERVES_DATA_DEPENDENT_INFORMATION_IN_AN_EXPLICIT_ENSEMBLE",
            "PERSISTED_DATA_DEPENDENT_SYMBOLIC_STRUCTURE_REMAINS_LEARNED_ORIGIN_UNDER_PROVENANCE_V1_EVEN_IF_EXECUTION_IS_DETERMINISTIC",
            "WORLD_INDEPENDENT_CODE_FIXED_WITHOUT_DATA_DEPENDENCE_NEED_NOT_BE_LEARNED_ORIGIN",
        ],
        "hard_nonclaims":[
            "NO_EXACT_REAL_WORLD_MUTUAL_INFORMATION_WITHOUT_A_DATA_DISTRIBUTION",
            "NO_CLAIM_ALL_POSTEXPOSURE_CODE_IS_DATA_DEPENDENT",
            "NO_TERMINAL_CREDIT",
        ],
        "h100_terminal_credit_delta":0,
    }
