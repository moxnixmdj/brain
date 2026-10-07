from canonical.runtime.selected_discriminator_policy_cover_bridge_verifier_v1 import verify

def test_selected_discriminator_bridge_is_bound():
    out=verify()
    assert out["pass"] is True, out
    assert out["abc_closed"] is False
    assert out["terminal"] is False
    assert out["terminal_credit_delta"] == 0
