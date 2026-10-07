from canonical.runtime.honesty_selected_cover_locality_verifier_v1 import selected_honesty, verify

def test_unused_bypass_is_not_terminally_load_bearing():
    assert selected_honesty({"A":True,"Z":False},{"A"},[]) is True

def test_causal_upstream_bypass_reopens():
    assert selected_honesty({"A":True,"Z":False},{"A"},[("Z","A")]) is False

def test_selected_route_must_be_guarded():
    assert selected_honesty({"A":False},{"A"},[]) is False

def test_source_bound_theorem_verifies():
    assert verify()["pass"] is True
