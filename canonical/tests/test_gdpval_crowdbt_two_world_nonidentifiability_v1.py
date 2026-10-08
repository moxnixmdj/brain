from canonical.runtime.gdpval_crowdbt_two_world_nonidentifiability_v1 import run

def test_two_world_reversal():
    out=run()
    assert out["status"]=="PASS__TWO_PUBLIC_COMPATIBLE_EXTENSIONS_REVERSE_BRAIN_VS_OPUS"
    assert out["worlds"]["ALL_BRAIN_WIN"]["brain_ge_opus"] is True
    assert out["worlds"]["ALL_OPUS_WIN"]["brain_ge_opus"] is False
    assert abs(out["base_fit_opus_elo"]-1866.0) < 3.0
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
