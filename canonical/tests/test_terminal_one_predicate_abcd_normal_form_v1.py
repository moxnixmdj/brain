from canonical.runtime.terminal_one_predicate_abcd_normal_form_verifier_v1 import verify,terminal_cover

def route(**kw):
    x={
      "A":True,"B":True,"C":True,"D":True,"current":True,"credited":True,
      "brain_owned":True,"donor_independent":True,
      "external_capability_provider":False,"incremental_spend_usd":0,
    }
    x.update(kw);return x

def finality(**kw):
    x={
      "route_set_content_addressed":True,
      "route_set_fixed":True,
      "D_recomputed_for_final_route_set":True,
      "donor_removal_cleanroom_pass":True,
    }
    x.update(kw);return x

def test_current_theorem_verifies():
    x=verify()
    assert x["pass"] is True,x
    assert x["independent_terminal_predicate_count"]==1
    assert x["final_route_set_cleanroom_required"] is True
    assert x["current_accepted_five_D_effect_residual_count"]==0
    assert x["terminal_credit_delta"]==0

def test_missing_route_d_fails():
    assert terminal_cover({"c"},{"c":[route(D=False)]},finality())["pass"] is False

def test_uncovered_context_fails():
    x=terminal_cover({"c0","c1"},{"c0":[route()]},finality())
    assert x["pass"] is False and x["missing_contexts"]==["c1"]

def test_route_drift_fails():
    assert terminal_cover({"c"},{"c":[route(current=False)]},finality())["pass"] is False

def test_external_provider_and_donor_dependence_fail():
    assert terminal_cover({"c"},{"c":[route(external_capability_provider=True)]},finality())["pass"] is False
    assert terminal_cover({"c"},{"c":[route(donor_independent=False)]},finality())["pass"] is False

def test_nonzero_incremental_spend_fails():
    assert terminal_cover({"c"},{"c":[route(incremental_spend_usd=1)]},finality())["pass"] is False

def test_final_route_set_cleanroom_is_mandatory():
    assert terminal_cover({"c"},{"c":[route()]},finality(donor_removal_cleanroom_pass=False))["pass"] is False
    assert terminal_cover({"c"},{"c":[route()]},finality(D_recomputed_for_final_route_set=False))["pass"] is False
    assert terminal_cover({"c"},{"c":[route()]},finality(route_set_fixed=False))["pass"] is False

def test_unsafe_uncredited_route_irrelevant():
    bad=route(credited=False,D=False,brain_owned=False,external_capability_provider=True)
    assert terminal_cover({"c"},{"c":[route(),bad]},finality())["pass"] is True

def test_unsafe_credited_route_invalidates_even_with_good_alternate():
    bad=route(credited=True,D=False)
    x=terminal_cover({"c"},{"c":[route(),bad]},finality())
    assert x["pass"] is False
    assert x["invalid_credited_routes"]==["c:1"]
