from canonical.runtime.terminal_dominance_normal_form_collapse_v1 import verify


def test_normal_form_sources_and_guards():
    out = verify()
    assert out["pass"], out
    assert out["normal_form"] == "B_star_AND_D_star"
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0


def test_A_is_absorbed_not_claimed_closed():
    out = verify()
    assert out["A_independent_set_enumeration_required"] is False
    assert out["B_star_proved"] is False


def test_C_is_absorbed_only_as_composition_enumeration():
    out = verify()
    assert out["C_arbitrary_composition_enumeration_required"] is False
    assert out["B_star_proved"] is False


def test_D_remains_independent():
    out = verify()
    assert out["D_independent_ownership_effect_closure_required"] is True
