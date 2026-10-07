from canonical.runtime.abc_residual_trichotomy_v1 import classify

def test_robust_zero_information():
    out=classify(["m0","m1"],["p"],{("p","m0"):True,("p","m1"):True},[["m0","m1"]])
    assert out["closed_under_current_information"]
    assert out["robust_policies"] == ["p"]
    assert out["singleton_capability_region"] == []

def test_discriminator_gap_not_singleton_capability_gap():
    dom={("p0","m0"):True,("p1","m1"):True}
    coarse=classify(["m0","m1"],["p0","p1"],dom,[["m0","m1"]])
    assert not coarse["closed_under_current_information"]
    assert coarse["singleton_capability_region"] == []
    refined=classify(["m0","m1"],["p0","p1"],dom,[["m0"],["m1"]])
    assert refined["closed_under_current_information"]

def test_singleton_capability_region():
    out=classify(["m0","m1"],["p0"],{("p0","m0"):True},[["m0"],["m1"]])
    assert out["singleton_capability_region"] == ["m1"]
    assert out["capability_gap_proved"] is False
