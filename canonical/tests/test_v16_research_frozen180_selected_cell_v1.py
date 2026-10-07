from canonical.runtime.v16_research_frozen180_selected_cell_verifier_v1 import verify

def test_research_frozen_180_and_negative_canary():
    x=verify()
    assert x["pass"] is True,x
    assert x["frozen_180_cell_closed"] is True
    assert x["universal_generator_claim_allowed"] is False
    assert x["counterexample"]=={"seed":7647,"ordinal":2,"reason":"ACTION_BUDGET_EXHAUSTED"}
    assert x["known_sound_region_certificate_count"]==14
    assert x["abc_closed"] is False
    assert x["d_finality_closed"] is False
    assert x["terminal"] is False
    assert x["terminal_credit_delta"]==0
