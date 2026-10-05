from canonical.runtime import structured_method_universal_correctness_certificate_v1 as cert


def test_fail_closed_if_any_universal_premise_is_missing():
    facts = {name: True for name in cert.REQUIRED_FACTS}
    facts["READY_PREDICATE_IDENTICAL"] = False
    out = cert.prove_from_facts(facts)
    assert out["universal_correctness_proved_candidate"] is False
    assert out["objective_ceiling_candidate"] is False
    assert "READY_PREDICATE_IDENTICAL" in out["missing"]
    assert out["acceptance_credit_delta"] == 0


def test_all_required_facts_are_jointly_sufficient_for_candidate_theorem():
    facts = {name: True for name in cert.REQUIRED_FACTS}
    out = cert.prove_from_facts(facts)
    assert out["universal_correctness_proved_candidate"] is True
    assert out["objective_ceiling_candidate"] is True
    assert out["brain_value"] == 1
    assert out["theoretical_upper_bound"] == 1
    assert out["uses_empirical_generalization"] is False
    assert out["acceptance_credit_delta"] == 0


def test_exact_current_sources_satisfy_the_bound_theorem():
    out = cert.verify()
    assert out["universal_correctness_proved_candidate"] is True
    assert out["scope_complete"] is True
    assert out["objective_ceiling_candidate"] is True
    assert out["basis_kind"] == "ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS"
    assert out["terminal_wave_load_bearing"] is False
    assert out["new_reality_units_consumed"] == 0
    assert out["terminal_cases_consumed"] == 0
