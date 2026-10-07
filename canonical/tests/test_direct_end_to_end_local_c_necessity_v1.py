from canonical.runtime.direct_end_to_end_local_c_necessity_verifier_v1 import verify,bypass_decision

def good():
    return {
      "exact_final_route_bound":True,
      "scope_complete":True,
      "evaluator_complete":True,
      "hard_constraint_complete":True,
      "independent_or_objective":True,
      "final_route_noninferior":True,
      "upstream_only":False,
    }

def test_current_theorem():
    x=verify();assert x["pass"],x;assert x["terminal_credit_delta"]==0

def test_good_direct_e2e_bypasses():
    x=bypass_decision(good())
    assert x["pass"] and x["separate_local_C_required"] is False

def test_missing_scope_fails():
    c=good();c["scope_complete"]=False
    x=bypass_decision(c);assert not x["pass"] and x["separate_local_C_required"] is True

def test_missing_evaluator_fails():
    c=good();c["evaluator_complete"]=False
    assert not bypass_decision(c)["pass"]

def test_missing_hard_constraint_fails():
    c=good();c["hard_constraint_complete"]=False
    assert not bypass_decision(c)["pass"]

def test_wrong_route_fails():
    c=good();c["exact_final_route_bound"]=False
    assert not bypass_decision(c)["pass"]

def test_upstream_only_fails():
    c=good();c["upstream_only"]=True
    assert not bypass_decision(c)["pass"]
