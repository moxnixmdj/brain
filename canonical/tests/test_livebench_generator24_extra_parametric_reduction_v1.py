from canonical.runtime import livebench_generator24_extra_parametric_reduction_v1 as r

def test_reduction_self_verifies():
    out=r.verify()
    assert out["status"].startswith("PASS__GENERATOR24_EXTRA_RAW_PARAMETER_AXES_REDUCED")
    assert out["raw_single_family_parameter_states"]==9722
    assert out["word_lt_reduction"]["below_public_word_lt_min"] is True
    assert out["acceptance_credit"] is False

def test_counter_scalar_theorem():
    for n in range(1,21):
        assert r.counter_decision(0,n,"at least").deficit==n
        assert r.counter_decision(n-1,n,"less than").satisfiable
        assert r.counter_decision(n,n,"less than").mandatory_loss

def test_no_comma_repeat_is_one_bit():
    assert r.no_comma_repeat_decision(True,True)["mandatory_loss_count_if_both_required"]==1
    assert r.no_comma_repeat_decision(True,False)["satisfiable_together"] is True

def test_case_section_residue():
    assert r.english_case_section_decision(r.EN_CAP,"SECTION")["satisfiable_together"] is True
    assert r.english_case_section_decision(r.EN_CAP,"Section")["mandatory_loss_count"]==1
    assert r.english_case_section_decision(r.EN_LOW,"SECTION")["mandatory_loss_count"]==1
    assert r.english_case_section_decision(r.EN_LOW,"Section")["mandatory_loss_count"]==1
