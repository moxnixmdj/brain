from canonical.runtime.robust_policy_fiber_cover_v1 import fiber_cover,common_policy,verifier_bypass

def test_common_policy_deletes_discriminator():
    W={"w0","w1","w2"}
    P={"p"}
    A={(w,"p") for w in W}
    assert common_policy(W,P,A)==["p"]
    out=fiber_cover(W,P,A,{"all":W})
    assert out["pass"] and out["selected_policy_count"]==1

def test_fiber_split_only_when_policy_must_change():
    W={"w0","w1"}
    P={"p0","p1"}
    A={("w0","p0"),("w1","p1")}
    assert not fiber_cover(W,P,A,{"all":W})["pass"]
    out=fiber_cover(W,P,A,{"o0":{"w0"},"o1":{"w1"}})
    assert out["pass"] and out["selected_policy_count"]==2

def test_unused_semantic_distinction_is_irrelevant():
    W={"d0u0","d0u1","d1u0","d1u1"}
    P={"p0","p1"}
    A={("d0u0","p0"),("d0u1","p0"),("d1u0","p1"),("d1u1","p1")}
    out=fiber_cover(W,P,A,{"d0":{"d0u0","d0u1"},"d1":{"d1u0","d1u1"}})
    assert out["pass"]

def test_verifier_bypass():
    out=verifier_bypass(pass_implies_adequate=True,portfolio_guaranteed_pass=True,owned=True,resource_safe=True)
    assert out["pass"] and out["semantic_discriminator_required"] is False

def test_verifier_bypass_fails_closed():
    out=verifier_bypass(pass_implies_adequate=False,portfolio_guaranteed_pass=True,owned=True,resource_safe=True)
    assert not out["pass"] and out["semantic_discriminator_required"] is None

def test_zero_credit():
    assert verifier_bypass(pass_implies_adequate=True,portfolio_guaranteed_pass=True,owned=True,resource_safe=True)["terminal_credit_delta"]==0
