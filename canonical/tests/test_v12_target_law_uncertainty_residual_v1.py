from canonical.runtime.v12_target_law_uncertainty_residual_verifier_v1 import residual,comparator_free_ok,verify

def test_empty_residual_closes_information_need():
    assert residual({"a","b"},{"a","b"})==set()
    assert comparator_free_ok({"a","b"},{"a","b"}) is True

def test_one_undominated_law_reopens():
    assert residual({"a","b"},{"a"})=={"b"}
    assert comparator_free_ok({"a","b"},{"a"}) is False

def test_wrong_dominance_set_does_not_help():
    assert comparator_free_ok({"a"},{"b"}) is False

def test_current_sources_verify():
    x=verify()
    assert x["pass"] is True,x
    assert x["abc_closed"] is False
    assert x["terminal_credit_delta"]==0
