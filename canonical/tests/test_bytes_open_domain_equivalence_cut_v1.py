from canonical.runtime.bytes_open_domain_equivalence_cut_v1 import (
    finite_countermodel,
    future_domain_free_completion_condition,
    fair_search_trace,
)

def test_finite_observations_do_not_imply_global_equivalence():
    out=finite_countermodel([0,1],[0,1],[0,1],2,2,99)
    assert out["finite_observations_insufficient_for_global_equivalence"] is True

def test_complete_equivalence_decider_closes_totality_cut():
    out=future_domain_free_completion_condition(
        complete_equivalence_decider=True,
        finite_characteristic_test_set_proved=False,
        accepts_possible_nontermination=False,
    )
    assert out["total_future_domain_free_completion_certified"] is True

def test_characteristic_set_also_closes_totality_cut():
    out=future_domain_free_completion_condition(
        complete_equivalence_decider=False,
        finite_characteristic_test_set_proved=True,
        accepts_possible_nontermination=False,
    )
    assert out["total_future_domain_free_completion_certified"] is True

def test_fair_search_is_semidecision_without_equivalence_certificate():
    out=future_domain_free_completion_condition(
        complete_equivalence_decider=False,
        finite_characteristic_test_set_proved=False,
        accepts_possible_nontermination=True,
    )
    assert out["fair_separator_enumeration_is_only_semidecision"] is True

def test_total_claim_is_unsupported_without_certificate_or_nontermination():
    out=future_domain_free_completion_condition(
        complete_equivalence_decider=False,
        finite_characteristic_test_set_proved=False,
        accepts_possible_nontermination=False,
    )
    assert out["unsupported_total_completion_claim"] is True

def test_fair_prefix_finds_separator_when_reached():
    p=lambda x:x
    q=lambda x:x if x<5 else x+1
    out=fair_search_trace(p,q,range(20),20)
    assert out=={"status":"SEPARATOR_FOUND","steps":6,"input":5}

def test_equivalent_programs_produce_no_separator_in_any_finite_prefix():
    p=lambda x:x*x
    q=lambda x:x**2
    out=fair_search_trace(p,q,range(100),100)
    assert out["status"]=="NO_SEPARATOR_IN_PREFIX"
