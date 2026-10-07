from canonical.runtime.terminal_one_predicate_abcd_normal_form_verifier_v1 import verify,terminal_cover

def route(**kw):
    base={
      "A":True,"B":True,"C":True,"D":True,"current":True,
      "brain_owned":True,"donor_independent":True,
      "external_capability_provider":False,"incremental_spend_usd":0,
    }
    base.update(kw)
    return base

def test_current_theorem_verifies_under_mission_v8():
    x=verify()
    assert x["pass"] is True,x
    assert x["independent_terminal_predicate_count"]==1
    assert x["independent_terminal_predicate"]=="COMPLETE_SELECTED_CONTEXT_ABCD_COVER"
    assert x["mission_lock"]=="V8"
    assert x["terminal_credit_delta"]==0

def test_missing_d_fails():
    assert terminal_cover({"c"},{"c":[route(D=False)]})["pass"] is False

def test_uncovered_context_fails():
    x=terminal_cover({"c0","c1"},{"c0":[route()]})
    assert x["pass"] is False and x["missing_contexts"]==["c1"]

def test_route_drift_fails():
    assert terminal_cover({"c"},{"c":[route(current=False)]})["pass"] is False

def test_external_capability_provider_is_not_owned():
    assert terminal_cover({"c"},{"c":[route(external_capability_provider=True)]})["pass"] is False

def test_donor_dependent_route_is_not_owned():
    assert terminal_cover({"c"},{"c":[route(donor_independent=False)]})["pass"] is False

def test_nonzero_incremental_spend_fails():
    assert terminal_cover({"c"},{"c":[route(incremental_spend_usd=1)]})["pass"] is False

def test_unsafe_unused_route_irrelevant():
    x=terminal_cover({"c"},{"c":[route(),route(D=False,brain_owned=False,external_capability_provider=True)]})
    assert x["pass"] is True
