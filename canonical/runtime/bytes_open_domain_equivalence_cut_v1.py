"""Open-domain equivalence cut for zero-marginal capability bytes.

Finite observations can refute equivalence by finding a separator, but cannot in
general certify global extensional equivalence over an unknown/unbounded domain
without an independently complete equivalence mechanism or characteristic test
set.

A fair enumerable input search semi-decides inequivalence: if two total programs
differ somewhere, the first differing input is eventually reached. If they are
globally equivalent, the search need not terminate.
"""
from __future__ import annotations

SCHEMA="PROJECT_BRAIN_BYTES_OPEN_DOMAIN_EQUIVALENCE_CUT_V1"

class EquivalenceCutError(ValueError):
    pass

def finite_countermodel(
    observed_inputs,
    p_observed,
    q_observed,
    unseen_input,
    p_unseen,
    q_unseen,
):
    if len(observed_inputs)!=len(p_observed) or len(observed_inputs)!=len(q_observed):
        raise EquivalenceCutError("OBSERVATION_LENGTH_MISMATCH")
    observed_equal=all(a==b for a,b in zip(p_observed,q_observed))
    unseen_diff=p_unseen!=q_unseen
    return {
        "schema":SCHEMA,
        "observed_equal":observed_equal,
        "unseen_differs":unseen_diff,
        "finite_observations_insufficient_for_global_equivalence":
            observed_equal and unseen_diff,
        "unseen_input":unseen_input,
    }

def future_domain_free_completion_condition(
    *,
    complete_equivalence_decider: bool,
    finite_characteristic_test_set_proved: bool,
    accepts_possible_nontermination: bool,
):
    for x,n in (
        (complete_equivalence_decider,"COMPLETE_EQUIVALENCE_DECIDER"),
        (finite_characteristic_test_set_proved,"FINITE_CHARACTERISTIC_TEST_SET"),
        (accepts_possible_nontermination,"ACCEPTS_NONTERMINATION"),
    ):
        if not isinstance(x,bool):
            raise EquivalenceCutError(n+"_FLAG_INVALID")
    total_certified=complete_equivalence_decider or finite_characteristic_test_set_proved
    semidecision_only=(not total_certified) and accepts_possible_nontermination
    impossible_total_claim=(not total_certified) and (not accepts_possible_nontermination)
    return {
        "schema":SCHEMA,
        "total_future_domain_free_completion_certified":total_certified,
        "fair_separator_enumeration_is_only_semidecision":semidecision_only,
        "unsupported_total_completion_claim":impossible_total_claim,
    }

def fair_search_trace(p,q,enumerated_inputs,max_steps):
    if not isinstance(max_steps,int) or isinstance(max_steps,bool) or max_steps<0:
        raise EquivalenceCutError("MAX_STEPS_INVALID")
    for i,x in enumerate(enumerated_inputs):
        if i>=max_steps:
            break
        if p(x)!=q(x):
            return {"status":"SEPARATOR_FOUND","steps":i+1,"input":x}
    return {"status":"NO_SEPARATOR_IN_PREFIX","steps":max_steps}
