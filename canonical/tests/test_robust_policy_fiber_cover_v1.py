from canonical.runtime.robust_policy_fiber_cover_v1 import fiber_cover,common_policy,verifier_bypass

def test_common_policy_and_required_split():
    W={"w0","w1"}
    A={("w0","p"),("w1","p")}
    assert common_policy(W,{"p"},A)==["p"]
    assert fiber_cover(W,{"p"},A,{"all":W})["pass"]
    B={("w0","p0"),("w1","p1")}
    assert not fiber_cover(W,{"p0","p1"},B,{"all":W})["pass"]
    assert fiber_cover(W,{"p0","p1"},B,{"a":{"w0"},"b":{"w1"}})["pass"]

def test_verifier_bypass():
    x=verifier_bypass(pass_implies_adequate=True,portfolio_guaranteed_pass=True,owned=True,resource_safe=True)
    assert x["pass"] and x["semantic_discriminator_required"] is False

def test_fail_closed_and_zero_credit():
    x=verifier_bypass(pass_implies_adequate=False,portfolio_guaranteed_pass=True,owned=True,resource_safe=True)
    assert not x["pass"] and x["semantic_discriminator_required"] is None
    assert x["terminal_credit_delta"]==0
