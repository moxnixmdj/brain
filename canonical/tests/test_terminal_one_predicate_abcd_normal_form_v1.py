from canonical.runtime.terminal_one_predicate_abcd_normal_form_verifier_v1 import verify,terminal_cover

def route(**kw):
    base={"A":True,"B":True,"C":True,"D":True,"current":True}
    base.update(kw)
    return base

def test_current_theorem_verifies():
    x=verify()
    assert x["pass"] is True,x
    assert x["independent_terminal_predicate_count"]==1
    assert x["independent_terminal_predicate"]=="COMPLETE_SELECTED_CONTEXT_ABCD_COVER"
    assert x["terminal_credit_delta"]==0

def test_missing_d_fails():
    x=terminal_cover({"c"},{"c":[route(D=False)]})
    assert x["pass"] is False
    assert x["missing_contexts"]==["c"]

def test_uncovered_context_fails():
    x=terminal_cover({"c0","c1"},{"c0":[route()]})
    assert x["pass"] is False
    assert x["missing_contexts"]==["c1"]

def test_route_drift_invalidates_credit():
    x=terminal_cover({"c"},{"c":[route(current=False)]})
    assert x["pass"] is False

def test_unsafe_unused_route_irrelevant():
    x=terminal_cover({"c"},{"c":[route(),route(D=False,current=True)]})
    assert x["pass"] is True
