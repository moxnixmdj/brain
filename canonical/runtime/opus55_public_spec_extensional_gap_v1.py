from __future__ import annotations

from typing import Any, Mapping, Sequence


class PublicSpecGapError(ValueError):
    pass


def two_kernel_countermodel(
    *,
    observed_contexts: Sequence[str],
    candidate_hidden_context: str,
    brain_value: float,
    observed_target_values: Mapping[str, float],
    hidden_world_1_value: float,
    hidden_world_2_value: float,
) -> dict[str, Any]:
    observed=tuple(str(x) for x in observed_contexts)
    hidden=str(candidate_hidden_context)
    if not observed or len(set(observed))!=len(observed):
        raise PublicSpecGapError("OBSERVED_CONTEXTS_INVALID")
    if not hidden or hidden in observed:
        raise PublicSpecGapError("HIDDEN_CONTEXT_MUST_BE_UNOBSERVED")
    if set(observed_target_values)!=set(observed):
        raise PublicSpecGapError("OBSERVED_VALUES_DOMAIN_MISMATCH")

    public_world_1={k:float(observed_target_values[k]) for k in observed}
    public_world_2=dict(public_world_1)
    full_1={**public_world_1,hidden:float(hidden_world_1_value)}
    full_2={**public_world_2,hidden:float(hidden_world_2_value)}

    brain=float(brain_value)
    observed_brain_dominates=all(brain>=v for v in public_world_1.values())
    terminal_1=observed_brain_dominates and brain>=full_1[hidden]
    terminal_2=observed_brain_dominates and brain>=full_2[hidden]

    return {
        "same_public_interface_and_observations": public_world_1==public_world_2,
        "observed_contexts":list(observed),
        "hidden_context":hidden,
        "brain_value":brain,
        "world_1":full_1,
        "world_2":full_2,
        "brain_dominates_observed":observed_brain_dominates,
        "brain_dominates_world_1":terminal_1,
        "brain_dominates_world_2":terminal_2,
        "different_terminal_truth":terminal_1!=terminal_2,
        "public_spec_extensional_completeness_proved":False,
        "required_repair":[
            "COMPLETE_TARGET_SPECIFICATION_OR_WHITEBOX_SEMANTIC_BOUND",
            "PROVED_STRUCTURAL_IDENTIFIABILITY",
            "SOUND_TARGET_SUPERDOMAIN_WITH_BRAIN_DOMINANCE",
            "EXHAUSTIVE_FINITE_DOMAIN_ENUMERATION_IF_THE_TERMINAL_DOMAIN_IS_PROVED_FINITE",
        ],
        "terminal_credit_delta":0,
    }


def canonical_witness()->dict[str,Any]:
    return two_kernel_countermodel(
        observed_contexts=("published_case_a","published_case_b"),
        candidate_hidden_context="within_interface_unpublished_context",
        brain_value=1.0,
        observed_target_values={"published_case_a":0.8,"published_case_b":1.0},
        hidden_world_1_value=0.9,
        hidden_world_2_value=1.1,
    )


if __name__=="__main__":
    import json
    print(json.dumps(canonical_witness(),indent=2,sort_keys=True))
