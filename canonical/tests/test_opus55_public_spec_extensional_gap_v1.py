from canonical.runtime.opus55_public_spec_extensional_gap_v1 import canonical_witness

def test_public_spec_gap_witness():
    out=canonical_witness()
    assert out["same_public_interface_and_observations"]
    assert out["brain_dominates_observed"]
    assert out["brain_dominates_world_1"]
    assert not out["brain_dominates_world_2"]
    assert out["different_terminal_truth"]
    assert out["terminal_credit_delta"]==0
